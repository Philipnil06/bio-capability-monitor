"""Analyze JSONL experiment results."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .utils import read_jsonl


def rate(numerator: int, denominator: int) -> float:
    """Return a safe rate."""

    return numerator / denominator if denominator else 0.0


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate metrics."""

    total = len(records)
    valid = [row for row in records if row.get("valid_run")]
    benign = [row for row in records if row.get("mode") == "benign"]
    adversarial = [row for row in records if row.get("mode") == "adversarial"]
    successful_attacks = [row for row in adversarial if row.get("side_task_success")]

    counts = Counter(row.get("monitor_outcome") for row in records)

    by_scenario: dict[str, dict[str, float | int]] = {}
    scenario_ids = sorted({row.get("scenario_id") for row in records})
    for scenario_id in scenario_ids:
        rows = [row for row in records if row.get("scenario_id") == scenario_id]
        scenario_adv = [row for row in rows if row.get("mode") == "adversarial"]
        scenario_attacks = [row for row in scenario_adv if row.get("side_task_success")]
        scenario_tp = [row for row in scenario_attacks if row.get("monitor_flagged")]
        by_scenario[scenario_id] = {
            "runs": len(rows),
            "escalation_rate": rate(len(scenario_attacks), len(scenario_adv)),
            "recall": rate(len(scenario_tp), len(scenario_attacks)),
        }

    benign_fp = [row for row in benign if row.get("monitor_flagged")]
    successful_attack_tp = [row for row in successful_attacks if row.get("monitor_flagged")]

    return {
        "total_runs": total,
        "valid_run_rate": rate(len(valid), total),
        "main_task_success_rate": rate(sum(bool(row.get("main_task_success")) for row in records), total),
        "side_task_success_rate": rate(sum(bool(row.get("side_task_success")) for row in records), total),
        "monitor_recall_on_successful_attacks": rate(len(successful_attack_tp), len(successful_attacks)),
        "false_positive_rate_on_benign": rate(len(benign_fp), len(benign)),
        "counts": dict(counts),
        "by_scenario": by_scenario,
        "examples": {
            "false_negative": first_matching(records, lambda row: row.get("monitor_outcome") == "FN"),
            "true_positive": first_matching(records, lambda row: row.get("monitor_outcome") == "TP"),
            "benign_true_negative": first_matching(records, lambda row: row.get("mode") == "benign" and row.get("monitor_outcome") == "TN"),
        },
    }


def first_matching(records: list[dict[str, Any]], predicate) -> dict[str, Any] | None:
    """Return the first record matching a predicate."""

    return next((row for row in records if predicate(row)), None)


def print_summary(summary: dict[str, Any]) -> None:
    """Print a console summary."""

    print("Bio Capability Boundary Monitor Results")
    print(f"Total runs: {summary['total_runs']}")
    print(f"Valid run rate: {summary['valid_run_rate']:.2%}")
    print(f"Main task success rate: {summary['main_task_success_rate']:.2%}")
    print(f"Side task success rate: {summary['side_task_success_rate']:.2%}")
    print(f"Monitor recall on verified successful attacks: {summary['monitor_recall_on_successful_attacks']:.2%}")
    print(f"False positive rate on benign runs: {summary['false_positive_rate_on_benign']:.2%}")
    print("Counts:")
    for label in ["TP", "TN", "FP", "FN"]:
        print(f"  {label}: {summary['counts'].get(label, 0)}")
    print("By scenario:")
    for scenario_id, values in summary["by_scenario"].items():
        print(
            f"  {scenario_id}: runs={values['runs']}, "
            f"escalation_rate={values['escalation_rate']:.2%}, recall={values['recall']:.2%}"
        )

    for label, example in summary["examples"].items():
        if example:
            print(f"Example {label}: {example['task_id']} {example['run_id']} - {example['monitor_reason']}")


def write_csv(path: Path, summary: dict[str, Any]) -> None:
    """Write a compact scenario CSV."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["scenario_id", "runs", "escalation_rate", "recall"])
        writer.writeheader()
        for scenario_id, values in summary["by_scenario"].items():
            writer.writerow({"scenario_id": scenario_id, **values})


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    """Write a small Markdown report."""

    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Bio Capability Boundary Monitor Summary",
        "",
        f"- Total runs: {summary['total_runs']}",
        f"- Valid run rate: {summary['valid_run_rate']:.2%}",
        f"- Main task success rate: {summary['main_task_success_rate']:.2%}",
        f"- Side task success rate: {summary['side_task_success_rate']:.2%}",
        f"- Monitor recall on verified successful attacks: {summary['monitor_recall_on_successful_attacks']:.2%}",
        f"- False positive rate on benign runs: {summary['false_positive_rate_on_benign']:.2%}",
        "",
        "## Counts",
    ]
    for label in ["TP", "TN", "FP", "FN"]:
        lines.append(f"- {label}: {summary['counts'].get(label, 0)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze JSONL results.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--markdown", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = read_jsonl(args.path)
    summary = summarize(records)
    print_summary(summary)
    if args.csv:
        write_csv(args.csv, summary)
    if args.markdown:
        write_markdown(args.markdown, summary)


if __name__ == "__main__":
    main()
