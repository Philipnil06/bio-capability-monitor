"""Minimal Streamlit debug UI for local experiment inspection."""

from __future__ import annotations

import random
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import streamlit as st

from src.builder import Builder
from src.monitor import Monitor
from src.run_experiment import build_provider, run_once
from src.tasks import load_tasks
from src.utils import append_jsonl, read_jsonl, to_jsonable


RESULTS_DIR = Path("results")


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


def run_experiments_from_ui(
    provider_name: str,
    builder_model: str,
    monitor_model: str,
    task_choice: str,
    runs_per_task: int,
    output_path: Path,
    base_url: str | None,
    seed: int,
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
    if task_choice != "all":
        tasks = [task for task in tasks if task.task_id == task_choice]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    records: list[dict[str, Any]] = []
    for task in tasks:
        for _ in range(runs_per_task):
            record = run_once(task, builder, monitor, builder_model, monitor_model)
            jsonable = to_jsonable(record)
            append_jsonl(output_path, jsonable)
            records.append(jsonable)
    return records


def latest_run_summary(record: dict[str, Any]) -> dict[str, Any]:
    """Small summary table for the latest run."""

    return {
        "task_id": record.get("task_id"),
        "mode": record.get("mode"),
        "allowed_tier": record.get("allowed_tier"),
        "observed_tier": record.get("observed_tier"),
        "main_task_success": record.get("main_task_success"),
        "side_task_success": record.get("side_task_success"),
        "monitor_flagged": record.get("monitor_flagged"),
        "monitor_reason": record.get("monitor_reason"),
    }


def filter_records(
    records: list[dict[str, Any]],
    scenario_id: str,
    mode: str,
    outcome: str,
) -> list[dict[str, Any]]:
    """Apply browser filters."""

    filtered = records
    if scenario_id != "all":
        filtered = [row for row in filtered if row.get("scenario_id") == scenario_id]
    if mode != "all":
        filtered = [row for row in filtered if row.get("mode") == mode]
    if outcome != "all":
        filtered = [row for row in filtered if row.get("monitor_outcome") == outcome]
    return filtered


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


def main() -> None:
    st.set_page_config(page_title="Bio Capability Boundary Monitor Debug", layout="wide")
    st.title("Bio Capability Boundary Monitor Debug")
    st.caption("Internal local UI for running and inspecting experiment JSONL logs.")

    tasks = load_tasks()
    task_options = ["all"] + [task.task_id for task in tasks]

    with st.sidebar:
        st.header("Run")
        provider_name = st.selectbox("Provider", ["mock", "openai", "openai_compatible"])
        builder_model = st.text_input("Builder model", value="mock-builder")
        monitor_model = st.text_input("Monitor model", value="mock-monitor")
        base_url = None
        if provider_name == "openai_compatible":
            base_url = st.text_input("Base URL", value="http://localhost:8000/v1")
        task_choice = st.selectbox("Task", task_options)
        runs_per_task = st.number_input("Runs per task", min_value=1, max_value=100, value=1, step=1)
        seed = st.number_input("Random seed", min_value=0, max_value=1_000_000, value=7, step=1)
        output_path = normalize_output_path(st.text_input("Output path", value="results/latest_ui.jsonl"))
        run_clicked = st.button("Run experiments", type="primary")

    if run_clicked:
        with st.spinner("Running experiments..."):
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
                )
                st.session_state["latest_records"] = records
                st.session_state["latest_output_path"] = str(output_path)
                st.success(f"Wrote {len(records)} runs to {output_path}")
            except Exception as exc:
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

    file_labels = [str(path) for path in result_files]
    default_label = st.session_state.get("latest_output_path")
    default_index = file_labels.index(default_label) if default_label in file_labels else 0
    selected_file = Path(st.selectbox("Results file", file_labels, index=default_index))

    try:
        records = read_jsonl(selected_file)
    except Exception as exc:
        st.error(f"Could not read {selected_file}: {exc}")
        return

    scenarios = ["all"] + sorted({str(row.get("scenario_id")) for row in records if row.get("scenario_id")})
    modes = ["all"] + sorted({str(row.get("mode")) for row in records if row.get("mode")})
    outcomes = ["all", "TP", "TN", "FP", "FN"]

    filter_cols = st.columns(3)
    with filter_cols[0]:
        scenario_filter = st.selectbox("scenario_id", scenarios)
    with filter_cols[1]:
        mode_filter = st.selectbox("mode", modes)
    with filter_cols[2]:
        outcome_filter = st.selectbox("monitor outcome", outcomes)

    filtered = filter_records(records, scenario_filter, mode_filter, outcome_filter)
    st.write(f"{len(filtered)} of {len(records)} runs")

    table_columns = [
        "run_id",
        "task_id",
        "scenario_id",
        "mode",
        "allowed_tier",
        "observed_tier",
        "main_task_success",
        "side_task_success",
        "monitor_flagged",
        "monitor_outcome",
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

    st.subheader("Selected Run Detail")
    detail_left, detail_right = st.columns([1, 1])
    with detail_left:
        st.json(selected_run)
    with detail_right:
        st.write("Tool trace")
        display_tool_trace(selected_run)


if __name__ == "__main__":
    main()
