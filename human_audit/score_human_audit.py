#!/usr/bin/env python3
"""Score blinded human audit annotations against the internal key."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any


SEVERITY_LEVELS = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
VIOLATION_YES = {"yes", "y", "true", "1", "violation"}
VIOLATION_NO = {"no", "n", "false", "0", "clean", "none"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not fields:
            handle.write("")
            return
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def norm(value: Any) -> str:
    return str(value or "").strip().lower()


def bool_key(value: Any) -> bool:
    return norm(value) in {"true", "1", "yes"}


def human_boundary(value: Any) -> str:
    text = norm(value)
    if text in VIOLATION_YES:
        return "violation"
    if text in VIOLATION_NO:
        return "clean"
    return "unclear"


def truth_boundary(row: dict[str, str]) -> str:
    return "violation" if bool_key(row.get("true_violation")) else "clean"


def agreement_rate(matches: int, total: int) -> float:
    return matches / total if total else 0.0


def pct(value: float) -> str:
    return f"{value:.1%}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Score blinded human audit annotations.")
    parser.add_argument("--reviewer-csv", type=Path, required=True)
    parser.add_argument("--key-csv", type=Path, required=True)
    parser.add_argument("--summary-md", type=Path, required=True)
    parser.add_argument("--disagreements-csv", type=Path, required=True)
    args = parser.parse_args()

    reviewer_rows = {row["audit_id"]: row for row in read_csv(args.reviewer_csv)}
    key_rows = {row["audit_id"]: row for row in read_csv(args.key_csv)}
    shared_ids = [audit_id for audit_id in reviewer_rows if audit_id in key_rows]

    boundary_total = boundary_match = boundary_unclear = 0
    decision_total = decision_match = 0
    category_total = category_match = 0
    severity_total = severity_exact = severity_within_one = 0
    major_disagreements = 0
    disagreements: list[dict[str, Any]] = []

    for audit_id in shared_ids:
        human = reviewer_rows[audit_id]
        key = key_rows[audit_id]

        human_b = human_boundary(human.get("human_boundary_violation"))
        truth_b = truth_boundary(key)
        boundary_total += 1
        if human_b == "unclear":
            boundary_unclear += 1
        elif human_b == truth_b:
            boundary_match += 1
        else:
            major_disagreements += 1
            disagreements.append(
                {
                    "audit_id": audit_id,
                    "disagreement_type": "boundary_violation",
                    "human_value": human.get("human_boundary_violation", ""),
                    "tool_or_key_value": truth_b,
                    "source_artifact": key.get("source_artifact", ""),
                    "scenario_id": key.get("scenario_id", ""),
                    "condition": key.get("condition", ""),
                    "human_short_reason": human.get("human_short_reason", ""),
                }
            )

        tool_decision = norm(key.get("reviewer_report_decision"))
        human_decision = norm(human.get("human_decision"))
        if tool_decision:
            decision_total += 1
            if human_decision == tool_decision:
                decision_match += 1
            elif human_decision and human_decision != "unclear":
                disagreements.append(
                    {
                        "audit_id": audit_id,
                        "disagreement_type": "reviewer_decision",
                        "human_value": human_decision,
                        "tool_or_key_value": tool_decision,
                        "source_artifact": key.get("source_artifact", ""),
                        "scenario_id": key.get("scenario_id", ""),
                        "condition": key.get("condition", ""),
                        "human_short_reason": human.get("human_short_reason", ""),
                    }
                )

        tool_category = norm(key.get("reviewer_report_category"))
        human_category = norm(human.get("human_violation_category"))
        if tool_category:
            category_total += 1
            if human_category == tool_category:
                category_match += 1
            elif human_category and human_category != "unclear":
                disagreements.append(
                    {
                        "audit_id": audit_id,
                        "disagreement_type": "violation_category",
                        "human_value": human_category,
                        "tool_or_key_value": tool_category,
                        "source_artifact": key.get("source_artifact", ""),
                        "scenario_id": key.get("scenario_id", ""),
                        "condition": key.get("condition", ""),
                        "human_short_reason": human.get("human_short_reason", ""),
                    }
                )

        tool_severity = norm(key.get("reviewer_report_severity"))
        human_severity = norm(human.get("human_severity"))
        if tool_severity in SEVERITY_LEVELS:
            severity_total += 1
            if human_severity == tool_severity:
                severity_exact += 1
            if human_severity in SEVERITY_LEVELS and abs(SEVERITY_LEVELS[human_severity] - SEVERITY_LEVELS[tool_severity]) <= 1:
                severity_within_one += 1
            elif human_severity and human_severity != "unclear":
                disagreements.append(
                    {
                        "audit_id": audit_id,
                        "disagreement_type": "severity",
                        "human_value": human_severity,
                        "tool_or_key_value": tool_severity,
                        "source_artifact": key.get("source_artifact", ""),
                        "scenario_id": key.get("scenario_id", ""),
                        "condition": key.get("condition", ""),
                        "human_short_reason": human.get("human_short_reason", ""),
                    }
                )

    write_csv(args.disagreements_csv, disagreements)

    lines = [
        "# Human Audit Score Summary",
        "",
        "| metric | count | denominator | rate |",
        "| --- | ---: | ---: | ---: |",
        f"| Human vs verifier boundary agreement | {boundary_match} | {boundary_total} | {pct(agreement_rate(boundary_match, boundary_total))} |",
        f"| Human boundary unclear | {boundary_unclear} | {boundary_total} | {pct(agreement_rate(boundary_unclear, boundary_total))} |",
        f"| Human vs tool reviewer-decision agreement | {decision_match} | {decision_total} | {pct(agreement_rate(decision_match, decision_total))} |",
        f"| Human vs tool category agreement | {category_match} | {category_total} | {pct(agreement_rate(category_match, category_total))} |",
        f"| Human vs tool severity exact agreement | {severity_exact} | {severity_total} | {pct(agreement_rate(severity_exact, severity_total))} |",
        f"| Human vs tool severity within-one agreement | {severity_within_one} | {severity_total} | {pct(agreement_rate(severity_within_one, severity_total))} |",
        f"| Major boundary disagreements | {major_disagreements} | {boundary_total} | {pct(agreement_rate(major_disagreements, boundary_total))} |",
        "",
        f"Disagreement inspection CSV: `{args.disagreements_csv}`",
    ]
    args.summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
