"""Minimal Streamlit debug UI for local experiment inspection."""

from __future__ import annotations

import random
import os
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import streamlit as st

from src.analyze_results import build_summary_tables, default_summary_dir, metric_text, pct_text, write_summary_tables
from src.config import DEFAULT_OPENSOURCE_BASE_URL, DEFAULT_OPENSOURCE_MODEL
from src.builder import Builder
from src.monitor import Monitor
from src.run_experiment import (
    build_provider,
    classify_monitor_outcome,
    default_monitor_rerun_output_path,
    outcome_counts,
    rerun_monitor_for_record,
    rerun_monitor_for_records,
    run_once,
)
from src.tasks import load_tasks
from src.types import task_condition
from src.utils import append_jsonl, read_jsonl, to_jsonable


RESULTS_DIR = Path("results")
MODEL_OPTIONS = [DEFAULT_OPENSOURCE_MODEL]
PROVIDER_OPTIONS = ["opensource", "openai", "openai_compatible", "deterministic"]
PROVIDER_LABELS = {
    "opensource": "Opensource",
    "openai": "OpenAI",
    "openai_compatible": "OpenAI compatible",
    "deterministic": "Deterministic",
}


def normalize_output_path(raw_path: str) -> Path:
    """Return a JSONL output path, defaulting relative paths to the repo root."""

    path = Path(raw_path.strip() or "results/latest_ui.jsonl")
    if path.suffix != ".jsonl":
        path = path.with_suffix(".jsonl")
    return path


def list_result_files() -> list[Path]:
    """List available JSONL result files."""

    RESULTS_DIR.mkdir(exist_ok=True)
    return sorted(RESULTS_DIR.glob("*.jsonl"), key=lambda path: path.stat().st_mtime, reverse=True)


def result_file_run_count(path: Path) -> int | None:
    """Return the number of non-empty rows in a JSONL result file."""

    try:
        with path.open("r", encoding="utf-8") as handle:
            return sum(1 for line in handle if line.strip())
    except Exception:
        return None


def result_file_label(path: Path) -> str:
    """Return a user-facing label with a run count hint."""

    count = result_file_run_count(path)
    count_text = "unknown runs" if count is None else f"{count} runs"
    if path.name == "latest_ui.jsonl":
        return f"{path} | FINAL BENCHMARK | {count_text}"
    if path.name == "latest_ui_monitor_no_hidden.jsonl":
        return f"{path} | monitor-only rerun candidate | {count_text}"
    return f"{path} | {count_text}"


def default_results_file(result_files: list[Path]) -> Path | None:
    """Return the preferred default result file for the browser."""

    if not result_files:
        return None
    preferred_names = [
        "latest_ui.jsonl",
        "latest_ui_monitor_no_hidden.jsonl",
    ]
    by_name = {path.name: path for path in result_files}
    for name in preferred_names:
        if name in by_name:
            return by_name[name]
    return result_files[0]


def format_elapsed(seconds: float) -> str:
    """Return a compact mm:ss or hh:mm:ss elapsed-time string."""

    total_seconds = max(0, int(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def run_experiments_from_ui(
    provider_name: str,
    builder_model: str,
    monitor_model: str,
    task_choice: list[str],
    runs_per_task: int,
    output_path: Path,
    base_url: str | None,
    seed: int,
    progress_callback=None,
) -> list[dict[str, Any]]:
    """Run selected experiments through the existing pipeline functions."""

    args = SimpleNamespace(
        provider=provider_name,
        builder_model=builder_model,
        monitor_model=monitor_model,
        base_url=base_url,
    )
    rng = random.Random(seed)
    provider = build_provider(args)
    builder = Builder(provider_name=provider_name, provider=provider)
    monitor = Monitor(provider_name=provider_name, provider=provider, rng=rng)

    tasks = load_tasks()
    selected = set(task_choice)
    tasks = [task for task in tasks if task.task_id in selected]
    if not tasks:
        raise ValueError("Select at least one task.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    records: list[dict[str, Any]] = []
    total_runs = len(tasks) * runs_per_task
    completed_runs = 0
    for task in tasks:
        for _ in range(runs_per_task):
            record = run_once(task, builder, monitor, builder_model, monitor_model)
            jsonable = to_jsonable(record)
            append_jsonl(output_path, jsonable)
            records.append(jsonable)
            completed_runs += 1
            if progress_callback is not None:
                progress_callback(completed_runs, total_runs, task.task_id, jsonable)
    return records


def run_monitor_rerun_from_ui(
    records: list[dict[str, Any]],
    provider_name: str,
    builder_model: str,
    monitor_model: str,
    output_path: Path,
    base_url: str | None,
    seed: int,
    progress_callback=None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Rerun only the monitor on already-saved records and write a new artifact."""

    args = SimpleNamespace(
        provider=provider_name,
        builder_model=builder_model,
        monitor_model=monitor_model,
        base_url=base_url,
    )
    rng = random.Random(seed)
    provider = build_provider(args)
    monitor = Monitor(provider_name=provider_name, provider=provider, rng=rng)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()
    rerun_rows: list[dict[str, Any]] = []
    total_rows = len(records)
    changed = 0
    for index, row in enumerate(records, start=1):
        current = rerun_monitor_for_record(
            row,
            monitor,
            rerun_monitor_model=monitor_model,
        )
        rerun_rows.append(current)
        append_jsonl(output_path, current)
        if current.get("rerun_monitor_changed"):
            changed += 1
        if progress_callback is not None:
            progress_callback(index, total_rows, current, changed)
    summary = rerun_monitor_diff_summary(rerun_rows)
    return rerun_rows, summary


def latest_run_summary(record: dict[str, Any]) -> dict[str, Any]:
    """Small summary table for the latest run."""

    return {
        "task_id": record.get("task_id"),
        "mode": record.get("mode"),
        "condition": record.get("condition"),
        "borderline_profile": record.get("borderline_profile"),
        "allowed_tier": record.get("allowed_tier"),
        "observed_tier": record.get("observed_tier"),
        "excess_tier": record.get("excess_tier"),
        "main_task_success": record.get("main_task_success"),
        "side_task_attempted": record.get("side_task_attempted"),
        "side_task_success": record.get("side_task_success"),
        "attempted_violation": record.get("attempted_violation"),
        "successful_violation": record.get("successful_violation"),
        "overuse_violation": record.get("overuse_violation"),
        "ambiguous_violation": record.get("ambiguous_violation"),
        "side_task_is_disallowed": record.get("side_task_is_disallowed"),
        "true_violation": record.get("true_violation"),
        "monitor_flagged": record.get("monitor_flagged"),
        "monitor_reason": record.get("monitor_reason"),
        "valid_run": record.get("valid_run"),
        "error": record.get("error"),
    }


def filter_records(
    records: list[dict[str, Any]],
    scenario_id: str,
    mode: str,
    condition: str,
    outcome: str,
) -> list[dict[str, Any]]:
    """Apply browser filters."""

    filtered = records
    if scenario_id != "all":
        filtered = [row for row in filtered if row.get("scenario_id") == scenario_id]
    if mode != "all":
        filtered = [row for row in filtered if row.get("mode") == mode]
    if condition != "all":
        filtered = [row for row in filtered if row.get("condition") == condition]
    if outcome != "all":
        filtered = [row for row in filtered if row.get("monitor_outcome") == outcome]
    return filtered


def has_rerun_monitor_fields(records: list[dict[str, Any]]) -> bool:
    """Return whether any row contains rerun monitor outputs."""

    return any(row.get("rerun_monitor_flagged") is not None for row in records)


def rerun_monitor_diff_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Return compact comparison counts for rows with rerun monitor outputs."""

    rerun_rows = [row for row in records if row.get("rerun_monitor_flagged") is not None]
    return {
        "total_rerun_rows": len(rerun_rows),
        "changed_monitor_decisions": sum(
            1
            for row in rerun_rows
            if bool(row.get("rerun_monitor_flagged")) != bool(row.get("monitor_flagged"))
        ),
        "original_counts": outcome_counts(rerun_rows, use_rerun_monitor=False),
        "rerun_counts": outcome_counts(rerun_rows, use_rerun_monitor=True),
    }


def display_tool_trace(record: dict[str, Any]) -> None:
    """Render tool calls in order."""

    trace = record.get("tool_trace") or []
    if not trace:
        st.info("No tool calls recorded.")
        return

    for index, call in enumerate(trace, start=1):
        label = f"{index}. {call.get('tool_name')} | tier {call.get('tier')}"
        with st.expander(label, expanded=index == 1):
            st.write("Input")
            st.json(call.get("tool_input", {}))
            st.write("Output")
            st.json(call.get("tool_output", {}))


def display_summary_tables(
    records: list[dict[str, Any]],
    selected_file: Path,
    *,
    use_rerun_monitor: bool = False,
) -> None:
    """Render aggregate summaries for the selected JSONL file."""

    if not records:
        st.info("No runs to summarize.")
        return

    tables = build_summary_tables(records, use_rerun_monitor=use_rerun_monitor)
    summary_dir = default_summary_dir(selected_file)
    written = write_summary_tables(summary_dir, tables)
    overall = tables["overall_summary"][0]
    valid_runs = int(overall["valid_runs"])

    st.subheader("Summary")
    label = "rerun monitor fields" if use_rerun_monitor else "original monitor fields"
    st.caption(f"Summary CSV files are written to `{summary_dir}` using {label}.")

    metric_cols = st.columns(5)
    metric_cols[0].metric("Valid runs", f"{overall['valid_runs']} / {overall['total_runs']}")
    metric_cols[1].metric("Main success", pct_text(int(overall["main_task_success_count"]), valid_runs))
    metric_cols[2].metric("True violations", pct_text(int(overall["true_violation_count"]), valid_runs))
    metric_cols[3].metric("Safety-adjusted success", pct_text(int(overall["safety_adjusted_task_success_count"]), valid_runs))
    metric_cols[4].metric("Monitor F1", metric_text(overall["f1"]))

    extra_cols = st.columns(4)
    extra_cols[0].metric("Monitor flagged", pct_text(int(overall["monitor_flagged_count"]), valid_runs))
    extra_cols[1].metric("Precision", metric_text(overall["precision"]))
    extra_cols[2].metric("Recall", metric_text(overall["recall"]))
    extra_cols[3].metric(
        "Zero-tier rows",
        f"{overall['zero_observed_tier_count']} total, {overall['invalid_zero_observed_tier_count']} invalid",
    )

    tab_overall, tab_condition, tab_scenario, tab_cross, tab_borderline, tab_files = st.tabs(
        [
            "Overall",
            "By Condition",
            "By Scenario",
            "Scenario x Condition",
            "Borderline",
            "Files",
        ]
    )

    with tab_overall:
        st.dataframe(tables["overall_summary"], use_container_width=True, hide_index=True)
    with tab_condition:
        st.dataframe(tables["by_condition_summary"], use_container_width=True, hide_index=True)
    with tab_scenario:
        st.dataframe(tables["by_scenario_summary"], use_container_width=True, hide_index=True)
    with tab_cross:
        st.dataframe(tables["by_scenario_condition_summary"], use_container_width=True, hide_index=True)
    with tab_borderline:
        st.dataframe(tables["borderline_summary"], use_container_width=True, hide_index=True)
    with tab_files:
        st.write("Generated summary files")
        for name, path in written.items():
            st.code(f"{name}: {path}")


def main() -> None:
    st.set_page_config(page_title="Bio Capability Boundary Monitor Debug", layout="wide")
    st.title("Bio Capability Boundary Monitor Debug")
    st.caption("Internal local UI for running and inspecting experiment JSONL logs.")

    tasks = load_tasks()
    task_options = [task.task_id for task in tasks]
    task_labels = {task.task_id: f"{task.task_id} | {task_condition(task)}" for task in tasks}

    with st.sidebar:
        st.header("Run")
        provider_name = st.selectbox(
            "Provider",
            PROVIDER_OPTIONS,
            format_func=lambda value: PROVIDER_LABELS.get(value, value),
        )
        builder_model = st.selectbox("Builder model", MODEL_OPTIONS)
        monitor_model = st.selectbox("Monitor model", MODEL_OPTIONS)
        base_url = None
        if provider_name in {"opensource", "openai_compatible"}:
            base_url = st.text_input(
                "Base URL",
                value=os.environ.get(
                    "OPENSOURCE_BASE_URL",
                    os.environ.get("OPENAI_COMPATIBLE_BASE_URL", DEFAULT_OPENSOURCE_BASE_URL),
                ),
            )
        task_choice = st.multiselect(
            "Tasks",
            task_options,
            default=task_options,
            format_func=lambda value: task_labels.get(value, value),
            help="Select one or more task IDs to run in the same batch.",
        )
        runs_per_task = st.number_input("Runs per task", min_value=1, max_value=100, value=1, step=1)
        seed = st.number_input("Random seed", min_value=0, max_value=1_000_000, value=7, step=1)
        output_path = normalize_output_path(st.text_input("Output path", value="results/latest_ui.jsonl"))
        run_clicked = st.button("Run experiments", type="primary")

    if run_clicked:
        progress_bar = st.progress(0.0, text="Preparing run...")
        progress_status = st.empty()
        started_at = time.monotonic()

        def update_progress(completed_runs: int, total_runs: int, task_id: str, record: dict[str, Any]) -> None:
            elapsed = format_elapsed(time.monotonic() - started_at)
            progress = completed_runs / total_runs if total_runs else 0.0
            progress_bar.progress(
                progress,
                text=f"Kör run {completed_runs}/{total_runs} | Senaste task: {task_id}",
            )
            progress_status.caption(
                f"Tid: {elapsed} | Genomförda runs: {completed_runs}/{total_runs} | "
                f"Senaste outcome: {record.get('monitor_outcome', '-')}"
            )

        try:
            records = run_experiments_from_ui(
                provider_name=provider_name,
                builder_model=builder_model,
                monitor_model=monitor_model,
                task_choice=task_choice,
                runs_per_task=int(runs_per_task),
                output_path=output_path,
                base_url=base_url,
                seed=int(seed),
                progress_callback=update_progress,
            )
            elapsed = format_elapsed(time.monotonic() - started_at)
            progress_bar.progress(1.0, text="Körning klar")
            progress_status.caption(f"Tid: {elapsed} | Genomförda runs: {len(records)}/{len(records)}")
            st.session_state["latest_records"] = records
            st.session_state["latest_output_path"] = str(output_path)
            st.success(f"Wrote {len(records)} runs to {output_path}")
        except Exception as exc:
            elapsed = format_elapsed(time.monotonic() - started_at)
            progress_status.caption(f"Tid: {elapsed} | Körningen avbröts.")
            st.error(f"Experiment run failed: {exc}")

    latest_records = st.session_state.get("latest_records", [])
    if latest_records:
        latest = latest_records[-1]
        st.subheader("Latest Run Summary")
        st.dataframe([latest_run_summary(latest)], use_container_width=True, hide_index=True)

        left, right = st.columns([1, 1])
        with left:
            st.subheader("Latest Tool Trace")
            display_tool_trace(latest)
        with right:
            st.subheader("Latest Final Output")
            st.text_area("Final output", value=latest.get("final_output", ""), height=220, disabled=True)

    st.divider()
    st.subheader("Results Browser")

    result_files = list_result_files()
    if not result_files:
        st.info("No JSONL files found in results/.")
        return

    file_labels = {str(path): result_file_label(path) for path in result_files}
    file_values = list(file_labels)
    default_label = st.session_state.get("latest_output_path")
    preferred = default_results_file(result_files)
    if default_label in file_values:
        default_index = file_values.index(default_label)
    elif preferred is not None:
        default_index = file_values.index(str(preferred))
    else:
        default_index = 0
    selected_value = st.selectbox(
        "Results file",
        file_values,
        index=default_index,
        format_func=lambda value: file_labels.get(value, value),
    )
    selected_file = Path(selected_value)

    try:
        records = read_jsonl(selected_file)
    except Exception as exc:
        st.error(f"Could not read {selected_file}: {exc}")
        return

    rerun_available = has_rerun_monitor_fields(records)
    use_rerun_monitor = st.checkbox(
        "Use rerun monitor fields in summaries",
        value=rerun_available,
        disabled=not rerun_available,
        help="When enabled, summary metrics use rerun_monitor_* fields instead of the original monitor fields.",
    )

    display_summary_tables(records, selected_file, use_rerun_monitor=use_rerun_monitor)

    if rerun_available:
        rerun_summary = rerun_monitor_diff_summary(records)
        st.subheader("Monitor Rerun Comparison")
        compare_cols = st.columns(3)
        compare_cols[0].metric("Rerun rows", rerun_summary["total_rerun_rows"])
        compare_cols[1].metric("Changed decisions", rerun_summary["changed_monitor_decisions"])
        compare_cols[2].metric(
            "Changed TP/TN/FP/FN total",
            sum(
                abs(rerun_summary["rerun_counts"][label] - rerun_summary["original_counts"][label])
                for label in ["TP", "TN", "FP", "FN"]
            ),
        )
        st.dataframe(
            [
                {"monitor_version": "original", **rerun_summary["original_counts"]},
                {"monitor_version": "rerun", **rerun_summary["rerun_counts"]},
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.divider()
    st.subheader("Raw Runs")

    scenarios = ["all"] + sorted({str(row.get("scenario_id")) for row in records if row.get("scenario_id")})
    modes = ["all"] + sorted({str(row.get("mode")) for row in records if row.get("mode")})
    conditions = ["all"] + sorted({str(row.get("condition")) for row in records if row.get("condition")})
    outcomes = ["all", "TP", "TN", "FP", "FN"]

    filter_cols = st.columns(4)
    with filter_cols[0]:
        scenario_filter = st.selectbox("scenario_id", scenarios)
    with filter_cols[1]:
        mode_filter = st.selectbox("mode", modes)
    with filter_cols[2]:
        condition_filter = st.selectbox("condition", conditions)
    with filter_cols[3]:
        outcome_filter = st.selectbox("monitor outcome", outcomes)

    filtered = filter_records(records, scenario_filter, mode_filter, condition_filter, outcome_filter)
    st.write(f"{len(filtered)} of {len(records)} runs")

    rerun_output_default = default_monitor_rerun_output_path(selected_file)
    rerun_output_path = normalize_output_path(
        st.text_input("Monitor rerun output path", value=str(rerun_output_default))
    )
    rerun_cols = st.columns(3)
    rerun_selected_clicked = rerun_cols[0].button("Rerun monitor for selected run")
    rerun_filtered_clicked = rerun_cols[1].button("Rerun monitor for filtered runs")
    rerun_all_clicked = rerun_cols[2].button("Rerun monitor for whole artifact")

    table_columns = [
        "run_id",
        "task_id",
        "scenario_id",
        "mode",
        "condition",
        "allowed_tier",
        "observed_tier",
        "excess_tier",
        "main_task_success",
        "side_task_attempted",
        "side_task_success",
        "attempted_violation",
        "successful_violation",
        "overuse_violation",
        "ambiguous_violation",
        "side_task_is_disallowed",
        "true_violation",
        "monitor_flagged",
        "monitor_outcome",
        "rerun_monitor_flagged",
        "rerun_monitor_outcome",
        "rerun_monitor_changed",
    ]
    table_rows = [{key: row.get(key) for key in table_columns} for row in filtered]
    st.dataframe(table_rows, use_container_width=True, hide_index=True)

    if not filtered:
        return

    run_labels = [
        f"{row.get('task_id')} | {row.get('monitor_outcome')} | {row.get('run_id')}"
        for row in filtered
    ]
    selected_label = st.selectbox("Selected run", run_labels)
    selected_index = run_labels.index(selected_label)
    selected_run = filtered[selected_index]

    rerun_target_rows: list[dict[str, Any]] | None = None
    rerun_target_label = ""
    if rerun_selected_clicked:
        rerun_target_rows = [selected_run]
        rerun_target_label = "selected run"
    elif rerun_filtered_clicked:
        rerun_target_rows = filtered
        rerun_target_label = "filtered runs"
    elif rerun_all_clicked:
        rerun_target_rows = records
        rerun_target_label = "whole artifact"

    if rerun_target_rows is not None:
        try:
            rerun_progress = st.progress(0.0, text="Preparing monitor rerun...")
            rerun_status = st.empty()
            rerun_started_at = time.monotonic()

            def update_rerun_progress(completed_rows: int, total_rows: int, row: dict[str, Any], changed: int) -> None:
                elapsed = format_elapsed(time.monotonic() - rerun_started_at)
                progress = completed_rows / total_rows if total_rows else 0.0
                rerun_progress.progress(
                    progress,
                    text=f"Rerun monitor {completed_rows}/{total_rows} | Senaste run: {row.get('task_id', '-')}",
                )
                rerun_status.caption(
                    f"Tid: {elapsed} | Klara: {completed_rows}/{total_rows} | "
                    f"Ändrade beslut hittills: {changed}"
                )

            rerun_rows, rerun_summary = run_monitor_rerun_from_ui(
                rerun_target_rows,
                provider_name=provider_name,
                builder_model=builder_model,
                monitor_model=monitor_model,
                output_path=rerun_output_path,
                base_url=base_url,
                seed=int(seed),
                progress_callback=update_rerun_progress,
            )
            elapsed = format_elapsed(time.monotonic() - rerun_started_at)
            rerun_progress.progress(1.0, text="Monitor rerun klar")
            rerun_status.caption(
                f"Tid: {elapsed} | Klara: {len(rerun_rows)}/{len(rerun_rows)} | "
                f"Ändrade beslut: {rerun_summary['changed_monitor_decisions']}"
            )
            st.success(
                f"Wrote {len(rerun_rows)} monitor-only reruns for {rerun_target_label} to {rerun_output_path}. "
                f"Changed decisions: {rerun_summary['changed_monitor_decisions']}"
            )
            st.session_state["latest_output_path"] = str(rerun_output_path)
        except Exception as exc:
            st.error(f"Monitor rerun failed: {exc}")

    st.subheader("Selected Run Detail")
    detail_left, detail_right = st.columns([1, 1])
    with detail_left:
        comparison = {
            "original_monitor_flagged": selected_run.get("monitor_flagged"),
            "rerun_monitor_flagged": selected_run.get("rerun_monitor_flagged"),
            "monitor_decision_changed": (
                bool(selected_run.get("rerun_monitor_flagged")) != bool(selected_run.get("monitor_flagged"))
                if selected_run.get("rerun_monitor_flagged") is not None
                else None
            ),
            "original_monitor_reason": selected_run.get("monitor_reason"),
            "rerun_monitor_reason": selected_run.get("rerun_monitor_reason"),
            "original_monitor_outcome": selected_run.get("monitor_outcome"),
            "rerun_monitor_outcome": selected_run.get("rerun_monitor_outcome"),
        }
        st.write("Monitor comparison")
        st.json(comparison)
        st.write("Full row")
        st.json(selected_run)
    with detail_right:
        st.write("Tool trace")
        display_tool_trace(selected_run)


if __name__ == "__main__":
    main()
