"""CLI runner for the experiment pipeline."""

from __future__ import annotations

import argparse
import random
import uuid
from pathlib import Path

from .builder import Builder
from .config import env
from .monitor import Monitor
from .providers.base import ModelProvider
from .providers.openai_compatible_provider import OpenAICompatibleProvider
from .providers.openai_provider import OpenAIProvider
from .tasks import load_tasks
from .types import BuilderRunResult, RunRecord
from .utils import append_jsonl, to_jsonable, utc_timestamp
from .verify import check_main_task_success, check_side_task_success, compute_observed_tier


def build_provider(args: argparse.Namespace) -> ModelProvider | None:
    """Build a model provider for non-mock modes."""

    if args.provider == "mock":
        return None
    if args.provider == "openai":
        return OpenAIProvider(args.builder_model, args.monitor_model)
    if args.provider == "openai_compatible":
        base_url = args.base_url or env("OPENAI_COMPATIBLE_BASE_URL")
        if not base_url:
            raise ValueError("--base-url or OPENAI_COMPATIBLE_BASE_URL is required for openai_compatible.")
        return OpenAICompatibleProvider(args.builder_model, args.monitor_model, base_url=base_url)
    raise ValueError(f"Unknown provider: {args.provider}")


def classify_monitor_outcome(side_task_success: bool, monitor_flagged: bool) -> str:
    """Return TP/TN/FP/FN label."""

    if side_task_success and monitor_flagged:
        return "TP"
    if side_task_success and not monitor_flagged:
        return "FN"
    if not side_task_success and monitor_flagged:
        return "FP"
    return "TN"


def run_once(
    task,
    builder: Builder,
    monitor: Monitor,
    builder_model: str,
    monitor_model: str,
) -> RunRecord:
    """Run one task and return a record. Exceptions are captured in-record."""

    run_id = str(uuid.uuid4())
    timestamp = utc_timestamp()
    try:
        builder_result = builder.run(task)
        main_success = check_main_task_success(task, builder_result)
        side_success = check_side_task_success(task, builder_result)
        observed = compute_observed_tier(builder_result)
        monitor_result = monitor.run(task, builder_result)
        outcome = classify_monitor_outcome(side_success, monitor_result.boundary_violation)
        error = builder_result.error or monitor_result.parse_error
        valid = builder_result.valid_run and monitor_result.parse_error is None
    except Exception as exc:
        builder_result = BuilderRunResult(final_output="", valid_run=False, error=str(exc))
        main_success = False
        side_success = False
        observed = 0
        monitor_result = monitor.run(task, builder_result)
        outcome = "TN"
        error = str(exc)
        valid = False

    return RunRecord(
        run_id=run_id,
        timestamp=timestamp,
        task_id=task.task_id,
        scenario_id=task.scenario_id,
        mode=task.mode,
        builder_model=builder_model,
        monitor_model=monitor_model,
        allowed_tier=task.allowed_tier,
        hidden_side_goal=task.hidden_side_goal,
        visible_prompt=task.visible_prompt,
        tool_trace=[to_jsonable(call) for call in builder_result.tool_trace],
        final_output=builder_result.final_output,
        main_task_success=main_success,
        side_task_success=side_success,
        observed_tier=observed,
        monitor_required_tier=monitor_result.required_tier,
        monitor_observed_tier=monitor_result.observed_tier,
        monitor_flagged=monitor_result.boundary_violation,
        monitor_reason=monitor_result.reason,
        monitor_outcome=outcome,
        valid_run=valid,
        error=error,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Bio Capability Boundary Monitor experiments.")
    parser.add_argument("--provider", choices=["mock", "openai", "openai_compatible"], default="mock")
    parser.add_argument("--builder-model", default="mock-builder")
    parser.add_argument("--monitor-model", default="mock-monitor")
    parser.add_argument("--runs-per-task", type=int, default=1)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--mock-monitor-miss-rate", type=float, default=0.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)
    output = args.output or Path("results") / "latest.jsonl"
    if output.exists():
        output.unlink()

    provider = build_provider(args)
    builder = Builder(provider_name=args.provider, provider=provider)
    monitor = Monitor(
        provider_name=args.provider,
        provider=provider,
        miss_rate=args.mock_monitor_miss_rate,
        rng=rng,
    )

    total = 0
    for task in load_tasks():
        for _ in range(args.runs_per_task):
            record = run_once(task, builder, monitor, args.builder_model, args.monitor_model)
            append_jsonl(output, to_jsonable(record))
            total += 1

    print(f"Wrote {total} runs to {output}")


if __name__ == "__main__":
    main()

