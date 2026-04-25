"""CLI runner for the experiment pipeline."""

from __future__ import annotations

import argparse
import random
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

from .builder import Builder
from .config import (
    DEFAULT_OPENSOURCE_BASE_URL,
    DEFAULT_OPENSOURCE_MODEL,
    ambiguous_violation_policy,
    env,
)
from .monitor import Monitor
from .providers.base import ModelProvider
from .providers.openai_compatible_provider import OpenAICompatibleProvider
from .providers.openai_provider import OpenAIProvider
from .scope_postcondition import augment_row_with_scope_defense
from .tasks import load_tasks
from .types import BuilderRunResult, RunRecord, TaskSpec, ToolCall, task_condition
from .utils import append_jsonl, read_jsonl, to_jsonable, utc_timestamp
from .verify import (
    check_main_task_success,
    check_side_task_attempted,
    check_side_task_success,
    compute_excess_tier,
    compute_observed_tier,
    compute_violation_labels,
)


def build_provider(args: argparse.Namespace) -> ModelProvider | None:
    """Build a model provider for non-deterministic modes."""

    if args.provider == "deterministic":
        return None
    if args.provider == "openai":
        return OpenAIProvider(args.builder_model, args.monitor_model)
    if args.provider in {"opensource", "openai_compatible"}:
        base_url = args.base_url or env("OPENSOURCE_BASE_URL") or env("OPENAI_COMPATIBLE_BASE_URL") or DEFAULT_OPENSOURCE_BASE_URL
        if not base_url:
            raise ValueError("--base-url, OPENSOURCE_BASE_URL, or OPENAI_COMPATIBLE_BASE_URL is required.")
        return OpenAICompatibleProvider(args.builder_model, args.monitor_model, base_url=base_url)
    raise ValueError(f"Unknown provider: {args.provider}")


def classify_monitor_outcome(true_violation: bool, monitor_flagged: bool) -> str:
    """Return TP/TN/FP/FN label."""

    if true_violation and monitor_flagged:
        return "TP"
    if true_violation and not monitor_flagged:
        return "FN"
    if not true_violation and monitor_flagged:
        return "FP"
    return "TN"


def outcome_counts(records: list[dict[str, Any]], *, use_rerun_monitor: bool = False) -> dict[str, int]:
    """Return TP/TN/FP/FN counts for original or rerun monitor fields."""

    tp = tn = fp = fn = 0
    flag_field = "rerun_monitor_flagged" if use_rerun_monitor else "monitor_flagged"
    for row in records:
        true_violation = bool(row.get("true_violation"))
        predicted = bool(row.get(flag_field))
        if true_violation and predicted:
            tp += 1
        elif true_violation and not predicted:
            fn += 1
        elif not true_violation and predicted:
            fp += 1
        else:
            tn += 1
    return {"TP": tp, "TN": tn, "FP": fp, "FN": fn}


def default_monitor_rerun_output_path(input_path: Path) -> Path:
    """Return the default JSONL path for a monitor-only rerun artifact."""

    return input_path.with_suffix("").parent / f"{input_path.stem}_monitor_rerun.jsonl"


def _task_lookup() -> dict[str, TaskSpec]:
    return {task.task_id: task for task in load_tasks()}


def task_from_record(row: dict[str, Any], task_lookup: dict[str, TaskSpec] | None = None) -> TaskSpec:
    """Rebuild a TaskSpec from a saved run record."""

    lookup = task_lookup or _task_lookup()
    task_id = str(row.get("task_id", ""))
    base = lookup.get(task_id)
    if base is None:
        return TaskSpec(
            task_id=task_id,
            scenario_id=str(row.get("scenario_id", "")),
            mode=str(row.get("mode", "benign")),
            visible_prompt=str(row.get("visible_prompt", "")),
            allowed_tier=int(row.get("allowed_tier", 0)),
            expected_main_result="",
            hidden_side_goal=row.get("hidden_side_goal"),
            notes=row.get("notes"),
            condition=row.get("condition"),
            borderline_profile=row.get("borderline_profile"),
            provider_calibration_profile=row.get("provider_calibration_profile"),
        )
    return replace(
        base,
        visible_prompt=str(row.get("visible_prompt", base.visible_prompt)),
        allowed_tier=int(row.get("allowed_tier", base.allowed_tier)),
        hidden_side_goal=row.get("hidden_side_goal"),
        notes=row.get("notes", base.notes),
        condition=row.get("condition", task_condition(base)),
        borderline_profile=row.get("borderline_profile"),
        provider_calibration_profile=row.get("provider_calibration_profile"),
    )


def builder_result_from_record(row: dict[str, Any]) -> BuilderRunResult:
    """Rebuild a BuilderRunResult from a saved run record."""

    return BuilderRunResult(
        final_output=str(row.get("final_output", "")),
        tool_trace=[ToolCall(**call) for call in row.get("tool_trace", [])],
        raw_response=row.get("builder_raw_response"),
        valid_run=bool(row.get("valid_run", True)),
        error=row.get("error"),
        parse_error=row.get("builder_parse_error"),
        borderline_profile=row.get("borderline_profile"),
        provider_calibration_profile=row.get("provider_calibration_profile"),
    )


def rerun_monitor_for_record(
    row: dict[str, Any],
    monitor: Monitor,
    *,
    task_lookup: dict[str, TaskSpec] | None = None,
    rerun_monitor_model: str | None = None,
) -> dict[str, Any]:
    """Return a copied row with fresh rerun monitor fields added."""

    task = task_from_record(row, task_lookup)
    sanitized_task = replace(task, hidden_side_goal=None)
    builder_result = builder_result_from_record(row)
    rerun_result = monitor.run(sanitized_task, builder_result)
    rerun_flagged = bool(rerun_result.boundary_violation)
    rerun_outcome = classify_monitor_outcome(bool(row.get("true_violation")), rerun_flagged)
    rerun_row = dict(row)
    rerun_row["original_monitor_flagged"] = row.get("monitor_flagged")
    rerun_row["original_monitor_reason"] = row.get("monitor_reason")
    rerun_row["original_monitor_outcome"] = row.get("monitor_outcome")
    rerun_row["rerun_monitor_flagged"] = rerun_flagged
    rerun_row["rerun_monitor_reason"] = rerun_result.reason
    rerun_row["rerun_monitor_required_tier"] = rerun_result.required_tier
    rerun_row["rerun_monitor_observed_tier"] = rerun_result.observed_tier
    rerun_row["rerun_monitor_raw_response"] = rerun_result.raw_response
    rerun_row["rerun_monitor_parse_error"] = rerun_result.parse_error
    rerun_row["rerun_monitor_outcome"] = rerun_outcome
    rerun_row["rerun_monitor_model"] = rerun_monitor_model or row.get("monitor_model")
    rerun_row["rerun_monitor_hidden_side_goal_removed"] = True
    rerun_row["rerun_monitor_task_hidden_side_goal"] = None
    rerun_row["rerun_monitor_changed"] = rerun_flagged != bool(row.get("monitor_flagged"))
    rerun_row["rerun_timestamp"] = utc_timestamp()
    return rerun_row


def rerun_monitor_for_records(
    records: list[dict[str, Any]],
    monitor: Monitor,
    *,
    task_lookup: dict[str, TaskSpec] | None = None,
    rerun_monitor_model: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Rerun only the monitor on saved records and return rows plus summary counts."""

    lookup = task_lookup or _task_lookup()
    rerun_rows = [
        rerun_monitor_for_record(
            row,
            monitor,
            task_lookup=lookup,
            rerun_monitor_model=rerun_monitor_model,
        )
        for row in records
    ]
    return rerun_rows, {
        "total_rerun_rows": len(rerun_rows),
        "changed_monitor_decisions": sum(1 for row in rerun_rows if row.get("rerun_monitor_changed")),
        "original_counts": outcome_counts(rerun_rows, use_rerun_monitor=False),
        "rerun_counts": outcome_counts(rerun_rows, use_rerun_monitor=True),
    }


def write_monitor_rerun_artifact(
    input_path: Path,
    output_path: Path,
    monitor: Monitor,
    *,
    task_ids: set[str] | None = None,
    run_ids: set[str] | None = None,
    rerun_monitor_model: str | None = None,
) -> dict[str, Any]:
    """Read an artifact, rerun only the monitor on selected rows, and write a new artifact."""

    if input_path.resolve() == output_path.resolve():
        raise ValueError("Monitor-only rerun output must be a new artifact path; refusing to overwrite the source JSONL.")
    source_records = read_jsonl(input_path)
    selected = [
        row
        for row in source_records
        if (not task_ids or str(row.get("task_id")) in task_ids)
        and (not run_ids or str(row.get("run_id")) in run_ids)
    ]
    if output_path.exists():
        output_path.unlink()
    rerun_rows, summary = rerun_monitor_for_records(
        selected,
        monitor,
        rerun_monitor_model=rerun_monitor_model,
    )
    for row in rerun_rows:
        append_jsonl(output_path, row)
    return {
        **summary,
        "source_rows": len(source_records),
        "selected_rows": len(selected),
        "output_path": output_path,
    }


def select_tasks(task_ids: str | None):
    """Return all tasks or a comma-separated subset of task IDs."""

    tasks = load_tasks()
    if not task_ids:
        return tasks
    requested = [task_id.strip() for task_id in task_ids.split(",") if task_id.strip()]
    known = {task.task_id: task for task in tasks}
    missing = [task_id for task_id in requested if task_id not in known]
    if missing:
        raise ValueError(f"Unknown task id(s): {', '.join(missing)}")
    return [known[task_id] for task_id in requested]


def run_once(
    task,
    builder: Builder,
    monitor: Monitor,
    builder_model: str,
    monitor_model: str,
    max_builder_attempts: int = 3,
    enable_scope_defense: bool = False,
    clean_monitor_input: bool = False,
) -> RunRecord:
    """Run one task and return a record. Exceptions are captured in-record."""

    run_id = str(uuid.uuid4())
    timestamp = utc_timestamp()
    try:
        builder_result = None
        builder_errors: list[str] = []
        attempts = max(1, max_builder_attempts)
        for attempt in range(attempts):
            candidate = builder.run(task)
            candidate_observed = compute_observed_tier(candidate)
            candidate_error = candidate.error or candidate.parse_error
            if candidate_error:
                builder_errors.append(f"attempt {attempt + 1}: {candidate_error}")
            if candidate.valid_run and candidate.parse_error is None and candidate_observed > 0:
                builder_result = candidate
                break
            builder_result = candidate
            if builder.provider_name == "deterministic":
                break
        assert builder_result is not None
        main_success = check_main_task_success(task, builder_result)
        side_attempted = check_side_task_attempted(task, builder_result)
        side_success = check_side_task_success(task, builder_result)
        observed = compute_observed_tier(builder_result)
        excess = compute_excess_tier(task.allowed_tier, observed)
        violation_labels = compute_violation_labels(
            task,
            builder_result,
            side_task_attempted=side_attempted,
            side_task_success=side_success,
            ambiguous_policy=ambiguous_violation_policy(),
        )
        true_violation = violation_labels.true_violation
        monitor_task = replace(task, hidden_side_goal=None) if clean_monitor_input else task
        monitor_result = monitor.run(monitor_task, builder_result)
        outcome = classify_monitor_outcome(true_violation, monitor_result.boundary_violation)
        error = builder_result.error or builder_result.parse_error or monitor_result.parse_error
        valid = (
            builder_result.valid_run
            and builder_result.parse_error is None
            and monitor_result.parse_error is None
            and observed > 0
        )
        if not valid and observed == 0 and error is None:
            error = "Invalid zero-tier run: no tool action executed or parsed."
        if builder_errors and not valid:
            error = f"{error or 'Invalid builder run'}; retries: {' | '.join(builder_errors)}"
    except Exception as exc:
        builder_result = BuilderRunResult(final_output="", valid_run=False, error=str(exc))
        main_success = False
        side_attempted = False
        side_success = False
        observed = 0
        excess = 0
        violation_labels = compute_violation_labels(task, builder_result, ambiguous_policy=ambiguous_violation_policy())
        true_violation = False
        monitor_result = monitor.run(task, builder_result)
        outcome = "TN"
        error = str(exc)
        valid = False

    record = RunRecord(
        run_id=run_id,
        timestamp=timestamp,
        task_id=task.task_id,
        scenario_id=task.scenario_id,
        mode=task.mode,
        condition=task_condition(task),
        borderline_profile=builder_result.borderline_profile,
        provider_calibration_profile=builder_result.provider_calibration_profile,
        builder_model=builder_model,
        monitor_model=monitor_model,
        allowed_tier=task.allowed_tier,
        hidden_side_goal=task.hidden_side_goal,
        notes=task.notes,
        visible_prompt=task.visible_prompt,
        tool_trace=[to_jsonable(call) for call in builder_result.tool_trace],
        final_output=builder_result.final_output,
        main_task_success=main_success,
        side_task_attempted=side_attempted,
        side_task_success=side_success,
        observed_tier=observed,
        excess_tier=excess,
        attempted_violation=violation_labels.attempted_violation,
        successful_violation=violation_labels.successful_violation,
        overuse_violation=violation_labels.overuse_violation,
        ambiguous_violation=violation_labels.ambiguous_violation,
        side_task_is_disallowed=violation_labels.side_task_is_disallowed,
        true_violation=true_violation,
        monitor_required_tier=monitor_result.required_tier,
        monitor_observed_tier=monitor_result.observed_tier,
        monitor_flagged=monitor_result.boundary_violation,
        monitor_reason=monitor_result.reason,
        monitor_outcome=outcome,
        valid_run=valid,
        builder_raw_response=builder_result.raw_response,
        builder_parse_error=builder_result.parse_error,
        monitor_raw_response=monitor_result.raw_response,
        monitor_parse_error=monitor_result.parse_error,
        error=error,
    )
    if enable_scope_defense:
        augmented = augment_row_with_scope_defense(to_jsonable(record))
        record.scope_postcondition_flagged = bool(augmented.get("scope_postcondition_flagged"))
        record.scope_violation_type = str(augmented.get("scope_violation_type"))
        record.scope_confidence = str(augmented.get("scope_confidence"))
        record.scope_reason = str(augmented.get("scope_reason"))
        record.triggered_patterns = list(augmented.get("triggered_patterns", []))
        record.augmented_monitor_flagged = bool(augmented.get("augmented_monitor_flagged"))
        record.augmented_monitor_source = str(augmented.get("augmented_monitor_source"))
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Bio Capability Boundary Monitor experiments.")
    parser.add_argument("--provider", choices=["opensource", "openai", "openai_compatible", "deterministic"], default="opensource")
    parser.add_argument("--builder-model", default=DEFAULT_OPENSOURCE_MODEL)
    parser.add_argument("--monitor-model", default=DEFAULT_OPENSOURCE_MODEL)
    parser.add_argument("--runs-per-task", type=int, default=1)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument(
        "--tasks",
        default=None,
        help="Comma-separated task IDs to run, for example S1E,S2E,S3E. Defaults to all tasks.",
    )
    parser.add_argument("--deterministic-monitor-miss-rate", type=float, default=0.0)
    parser.add_argument(
        "--max-builder-attempts",
        type=int,
        default=3,
        help="Retry invalid/no-op provider builder outputs before recording an invalid run.",
    )
    parser.add_argument(
        "--rerun-monitor-only",
        type=Path,
        default=None,
        help="Existing JSONL artifact to rerun only the monitor on. Builder outputs remain unchanged.",
    )
    parser.add_argument(
        "--run-ids",
        default=None,
        help="Optional comma-separated run_ids to rerun when using --rerun-monitor-only.",
    )
    parser.add_argument(
        "--enable-scope-defense",
        action="store_true",
        help="Add scope-aware postcondition and augmented monitor fields to newly generated rows.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)
    miss_rate = args.deterministic_monitor_miss_rate
    provider = build_provider(args)
    monitor = Monitor(
        provider_name=args.provider,
        provider=provider,
        miss_rate=miss_rate,
        rng=rng,
    )
    if args.rerun_monitor_only is not None:
        output = args.output or default_monitor_rerun_output_path(args.rerun_monitor_only)
        task_ids = {task_id.strip() for task_id in (args.tasks or "").split(",") if task_id.strip()} or None
        run_ids = {run_id.strip() for run_id in (args.run_ids or "").split(",") if run_id.strip()} or None
        summary = write_monitor_rerun_artifact(
            args.rerun_monitor_only,
            output,
            monitor,
            task_ids=task_ids,
            run_ids=run_ids,
            rerun_monitor_model=args.monitor_model,
        )
        print(
            f"Wrote {summary['selected_rows']} monitor-only reruns to {summary['output_path']} "
            f"(changed decisions: {summary['changed_monitor_decisions']})"
        )
        return

    output = args.output or Path("results") / "latest.jsonl"
    if output.exists():
        output.unlink()

    builder = Builder(provider_name=args.provider, provider=provider)

    total = 0
    for task in select_tasks(args.tasks):
        for _ in range(args.runs_per_task):
            record = run_once(
                task,
                builder,
                monitor,
                args.builder_model,
                args.monitor_model,
                max_builder_attempts=args.max_builder_attempts,
                enable_scope_defense=args.enable_scope_defense,
            )
            append_jsonl(output, to_jsonable(record))
            total += 1

    print(f"Wrote {total} runs to {output}")


if __name__ == "__main__":
    main()
