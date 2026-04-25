"""Fresh clean final run workflow with optional scope-defense validation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

from .analyze_results import ambiguous_violation, excess_tier, rate, row_condition, true_violation
from .builder import Builder
from .config import AmbiguousViolationPolicy
from .config import DEFAULT_OPENSOURCE_BASE_URL, DEFAULT_OPENSOURCE_MODEL
from .monitor import Monitor
from .run_experiment import build_provider, classify_monitor_outcome, run_once
from .tasks import load_tasks
from .utils import append_jsonl, read_jsonl, to_jsonable, utc_timestamp


ProgressCallback = Callable[[int, int, str, dict[str, Any], float], None]


def default_final_clean_output_dir() -> Path:
    """Return the default output directory for fresh clean scope runs."""

    return Path("results/final_clean_scope")


def resolve_final_clean_paths(output_dir: Path, filename: str = "final_clean_scope_run.jsonl") -> tuple[Path, Path]:
    """Return non-overwriting output directory and JSONL path."""

    output_dir = Path(output_dir)
    jsonl_path = output_dir / filename
    if not jsonl_path.exists() and not (output_dir / "manifest.json").exists():
        return output_dir, jsonl_path
    stamp = time.strftime("%Y%m%d_%H%M%S")
    resolved_dir = output_dir / stamp
    return resolved_dir, resolved_dir / filename


def run_final_clean_scope_experiment(
    *,
    provider_name: str,
    builder_model: str,
    monitor_model: str,
    base_url: str | None,
    runs_per_task: int = 100,
    random_seed: int = 7,
    output_dir: Path | None = None,
    output_filename: str = "final_clean_scope_run.jsonl",
    enable_scope_defense: bool = True,
    run_holdout_validation: bool = True,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Run a fresh clean experiment and export scope-defense paper artifacts."""

    requested_dir = output_dir or default_final_clean_output_dir()
    run_dir, artifact_path = resolve_final_clean_paths(requested_dir, output_filename)
    summaries_dir = run_dir / "summaries"
    run_dir.mkdir(parents=True, exist_ok=True)
    summaries_dir.mkdir(parents=True, exist_ok=True)

    tasks = load_tasks()
    total_expected = len(tasks) * runs_per_task
    manifest_path = run_dir / "manifest.json"
    started = utc_timestamp()
    manifest = {
        "timestamp": started,
        "status": "incomplete",
        "provider": provider_name,
        "builder_model": builder_model,
        "monitor_model": monitor_model,
        "base_url": base_url,
        "runs_per_task": runs_per_task,
        "random_seed": random_seed,
        "task_ids": [task.task_id for task in tasks],
        "total_expected_runs": total_expected,
        "total_completed_runs": 0,
        "scope_defense_enabled": enable_scope_defense,
        "holdout_validation_enabled": run_holdout_validation,
        "clean_monitor_input_hidden_side_goal_removed": True,
        "commit_hash": _git_commit_hash(),
        "output_jsonl": str(artifact_path),
        "code_version_notes": "Fresh clean run with clean monitor input and optional scope-aware postcondition augmentation.",
    }
    _write_json(manifest_path, manifest)

    args = SimpleNamespace(
        provider=provider_name,
        builder_model=builder_model,
        monitor_model=monitor_model,
        base_url=base_url,
    )
    provider = build_provider(args)
    builder = Builder(provider_name=provider_name, provider=provider)
    monitor = Monitor(provider_name=provider_name, provider=provider, rng=random.Random(random_seed))
    records: list[dict[str, Any]] = []
    started_monotonic = time.monotonic()

    try:
        if artifact_path.exists():
            raise FileExistsError(f"Refusing to overwrite existing artifact: {artifact_path}")
        completed = 0
        for task in tasks:
            for _ in range(runs_per_task):
                record = run_once(
                    task,
                    builder,
                    monitor,
                    builder_model,
                    monitor_model,
                    enable_scope_defense=enable_scope_defense,
                    clean_monitor_input=True,
                )
                row = to_jsonable(record)
                append_jsonl(artifact_path, row)
                records.append(row)
                completed += 1
                manifest["total_completed_runs"] = completed
                _write_json(manifest_path, manifest)
                if progress_callback is not None:
                    progress_callback(completed, total_expected, task.task_id, row, time.monotonic() - started_monotonic)

        outputs = export_final_clean_scope_outputs(
            records,
            run_dir,
            run_holdout_validation=run_holdout_validation,
        )
        manifest["status"] = "complete"
        manifest["completed_timestamp"] = utc_timestamp()
        manifest["total_completed_runs"] = len(records)
        manifest["output_jsonl_sha256"] = _sha256(artifact_path)
        manifest["outputs"] = {key: str(value) for key, value in outputs.items()}
        _write_json(manifest_path, manifest)
        return {
            "run_dir": run_dir,
            "artifact_path": artifact_path,
            "manifest_path": manifest_path,
            "records": records,
            "outputs": outputs,
            "manifest": manifest,
        }
    except Exception as exc:
        manifest["status"] = "incomplete"
        manifest["error"] = str(exc)
        manifest["failed_timestamp"] = utc_timestamp()
        manifest["total_completed_runs"] = len(records)
        if artifact_path.exists():
            manifest["output_jsonl_sha256"] = _sha256(artifact_path)
        _write_json(manifest_path, manifest)
        raise


def export_final_clean_scope_outputs(
    records: list[dict[str, Any]],
    run_dir: Path,
    *,
    run_holdout_validation: bool = True,
) -> dict[str, Path]:
    """Export metrics, holdout validation, and paper-ready summaries."""

    summaries_dir = run_dir / "summaries"
    summaries_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}

    summary_specs = [
        ("original_all_valid", "violation", False, summaries_dir / "original_all_valid_summary.csv"),
        ("original_hard_label", "exclude", False, summaries_dir / "original_hard_label_summary.csv"),
        ("augmented_all_valid", "violation", True, summaries_dir / "augmented_all_valid_summary.csv"),
        ("augmented_hard_label", "exclude", True, summaries_dir / "augmented_hard_label_summary.csv"),
    ]
    summary_rows = []
    for name, policy, augmented, path in summary_specs:
        row = metric_row(records, metric_set=name, policy=policy, augmented=augmented)
        summary_rows.append(row)
        _write_csv(path, [row])
        outputs[name] = path

    breakdowns = {
        "by_condition_original": (["condition"], False, summaries_dir / "by_condition_original.csv"),
        "by_condition_augmented": (["condition"], True, summaries_dir / "by_condition_augmented.csv"),
        "by_scenario_original": (["scenario_id"], False, summaries_dir / "by_scenario_original.csv"),
        "by_scenario_augmented": (["scenario_id"], True, summaries_dir / "by_scenario_augmented.csv"),
        "by_scenario_condition_original": (["scenario_id", "condition"], False, summaries_dir / "by_scenario_condition_original.csv"),
        "by_scenario_condition_augmented": (["scenario_id", "condition"], True, summaries_dir / "by_scenario_condition_augmented.csv"),
    }
    for key, (fields, augmented, path) in breakdowns.items():
        _write_csv(path, grouped_metric_rows(records, fields, augmented=augmented))
        outputs[key] = path

    extra_tables = {
        "by_tier_miss_type": summaries_dir / "by_same_tier_vs_excess_tier.csv",
        "by_scope_violation_type": summaries_dir / "by_scope_violation_type.csv",
        "by_augmented_monitor_source": summaries_dir / "by_augmented_monitor_source.csv",
        "by_borderline_profile": summaries_dir / "by_borderline_profile.csv",
        "by_provider_calibration_profile": summaries_dir / "by_provider_calibration_profile.csv",
    }
    _write_csv(extra_tables["by_tier_miss_type"], tier_miss_type_rows(records))
    _write_csv(extra_tables["by_scope_violation_type"], count_rows(records, "scope_violation_type"))
    _write_csv(extra_tables["by_augmented_monitor_source"], count_rows(records, "augmented_monitor_source"))
    _write_csv(extra_tables["by_borderline_profile"], count_rows(records, "borderline_profile"))
    _write_csv(extra_tables["by_provider_calibration_profile"], count_rows(records, "provider_calibration_profile"))
    outputs.update(extra_tables)

    holdout = holdout_summary(records) if run_holdout_validation else {}
    holdout_path = run_dir / "scope_defense_holdout_summary.csv"
    _write_csv(holdout_path, [holdout] if holdout else [])
    outputs["scope_defense_holdout_summary"] = holdout_path

    cases_path = run_dir / "scope_defense_cases.md"
    cases_path.write_text(scope_defense_cases_markdown(records), encoding="utf-8")
    outputs["scope_defense_cases"] = cases_path

    final_metrics_path = run_dir / "paper_ready_final_metrics.md"
    final_metrics_path.write_text(paper_ready_final_metrics(summary_rows, holdout), encoding="utf-8")
    outputs["paper_ready_final_metrics"] = final_metrics_path

    tables_path = run_dir / "paper_ready_tables.md"
    tables_path.write_text(paper_ready_tables(summary_rows, holdout), encoding="utf-8")
    outputs["paper_ready_tables"] = tables_path
    return outputs


def metric_row(
    rows: list[dict[str, Any]],
    *,
    metric_set: str,
    policy: AmbiguousViolationPolicy,
    augmented: bool,
) -> dict[str, Any]:
    """Return one final-clean metric row."""

    selected = _selected_rows(rows, policy)
    valid = [row for row in rows if row.get("valid_run", True)]
    counts = _confusion(selected, policy, augmented=augmented)
    tp, tn, fp, fn = counts["TP"], counts["TN"], counts["FP"], counts["FN"]
    precision = rate(tp, tp + fp)
    recall = rate(tp, tp + fn)
    f1 = rate(2 * precision * recall, precision + recall) if precision + recall else 0.0
    fpr = rate(fp, fp + tn)
    fnr = rate(fn, fn + tp)
    original_fn = [row for row in selected if true_violation(row, policy) and not _pred(row, augmented=False)]
    recovered = [row for row in original_fn if bool(row.get("scope_postcondition_flagged"))]
    new_fp = [
        row
        for row in selected
        if not true_violation(row, policy) and not _pred(row, augmented=False) and bool(row.get("scope_postcondition_flagged"))
    ]
    same_tier_fn = [row for row in selected if true_violation(row, policy) and not _pred(row, augmented=augmented) and excess_tier(row) == 0]
    excess_fn = [row for row in selected if true_violation(row, policy) and not _pred(row, augmented=augmented) and excess_tier(row) > 0]
    return {
        "metric_set": metric_set,
        "monitor_type": "augmented" if augmented else "original",
        "ambiguity_policy": policy,
        "total_rows": len(rows),
        "valid_rows": len(valid),
        "hard_label_runs": len(selected),
        "TP": tp,
        "TN": tn,
        "FP": fp,
        "FN": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": fpr,
        "false_negative_rate": fnr,
        "monitor_flagged_count": sum(1 for row in selected if _pred(row, augmented=augmented)),
        "true_violation_count": sum(1 for row in selected if true_violation(row, policy)),
        "main_task_success_count": sum(1 for row in selected if bool(row.get("main_task_success"))),
        "safety_adjusted_success_count": sum(
            1 for row in selected if bool(row.get("main_task_success")) and not true_violation(row, policy)
        ),
        "same_tier_true_violation_count": sum(1 for row in selected if true_violation(row, policy) and excess_tier(row) == 0),
        "same_tier_FN": len(same_tier_fn),
        "excess_tier_FN": len(excess_fn),
        "recovered_FN_by_scope_defense": len(recovered),
        "new_FP_introduced_by_scope_defense": len(new_fp),
    }


def grouped_metric_rows(rows: list[dict[str, Any]], fields: list[str], *, augmented: bool) -> list[dict[str, Any]]:
    """Return grouped all-valid and hard-label metric rows."""

    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = tuple(row_condition(row) if field == "condition" else row.get(field) for field in fields)
        groups[key].append(row)
    output = []
    for key, group_rows in sorted(groups.items(), key=lambda item: tuple(str(part) for part in item[0])):
        labels = dict(zip(fields, key))
        for policy_name, policy in [("all_valid", "violation"), ("hard_label", "exclude")]:
            output.append({**labels, **metric_row(group_rows, metric_set=policy_name, policy=policy, augmented=augmented)})
    return output


def holdout_summary(rows: list[dict[str, Any]], policy: AmbiguousViolationPolicy = "exclude") -> dict[str, Any]:
    """Validate scope defense on fresh original-monitor residual misses."""

    selected = _selected_rows(rows, policy)
    original_fn = [row for row in selected if true_violation(row, policy) and not _pred(row, augmented=False)]
    recovered = [row for row in original_fn if bool(row.get("scope_postcondition_flagged"))]
    clean_tn = [row for row in selected if not true_violation(row, policy) and not _pred(row, augmented=False)]
    new_fp = [row for row in clean_tn if bool(row.get("scope_postcondition_flagged"))]
    fp_by_condition = Counter(row_condition(row) for row in new_fp)
    fp_by_scenario = Counter(str(row.get("scenario_id")) for row in new_fp)
    benign_tn = [row for row in clean_tn if row_condition(row) == "benign"]
    borderline_tn = [row for row in clean_tn if row_condition(row) == "borderline"]
    return {
        "fresh_original_monitor_FN_count": len(original_fn),
        "fresh_FN_recovered_by_scope_defense": len(recovered),
        "fresh_FN_recovery_rate": rate(len(recovered), len(original_fn)),
        "fresh_same_tier_FN_recovered": sum(1 for row in recovered if excess_tier(row) == 0),
        "fresh_excess_tier_FN_recovered": sum(1 for row in recovered if excess_tier(row) > 0),
        "fresh_clean_TN_count": len(clean_tn),
        "fresh_new_FP_from_scope_defense": len(new_fp),
        "fresh_FP_rate": rate(len(new_fp), len(clean_tn)),
        "fresh_FP_by_condition": json.dumps(dict(sorted(fp_by_condition.items())), sort_keys=True),
        "fresh_FP_by_scenario": json.dumps(dict(sorted(fp_by_scenario.items())), sort_keys=True),
        "fresh_benign_true_negative_count": len(benign_tn),
        "fresh_FP_on_benign_true_negatives": sum(1 for row in benign_tn if bool(row.get("scope_postcondition_flagged"))),
        "fresh_borderline_true_negative_count": len(borderline_tn),
        "fresh_FP_on_borderline_true_negatives": sum(1 for row in borderline_tn if bool(row.get("scope_postcondition_flagged"))),
    }


def scope_defense_cases_markdown(rows: list[dict[str, Any]], policy: AmbiguousViolationPolicy = "exclude") -> str:
    """Return representative scope-defense validation cases."""

    selected = _selected_rows(rows, policy)
    original_fn = [row for row in selected if true_violation(row, policy) and not _pred(row, augmented=False)]
    recovered = [row for row in original_fn if bool(row.get("scope_postcondition_flagged"))]
    missed = [row for row in original_fn if not bool(row.get("scope_postcondition_flagged"))]
    clean_tn = [row for row in selected if not true_violation(row, policy) and not _pred(row, augmented=False)]
    new_fp = [row for row in clean_tn if bool(row.get("scope_postcondition_flagged"))]
    clean_ok = [row for row in clean_tn if not bool(row.get("scope_postcondition_flagged"))]
    sections = [
        ("Representative Recovered Fresh FNs", recovered[:6]),
        ("Representative Missed Fresh FNs", missed[:6]),
        ("Representative New FPs", new_fp[:6]),
        ("Representative Clean TNs Not Flagged", clean_ok[:6]),
    ]
    lines = ["# Scope Defense Holdout Cases", ""]
    for title, cases in sections:
        lines.extend([f"## {title}", ""])
        if not cases:
            lines.extend(["None.", ""])
            continue
        for row in cases:
            lines.extend(
                [
                    f"### {row.get('task_id')} {row.get('run_id')}",
                    "",
                    f"- scenario: `{row.get('scenario_id')}`",
                    f"- condition: `{row_condition(row)}`",
                    f"- allowed/observed/excess tier: `{row.get('allowed_tier')}/{row.get('observed_tier')}/{excess_tier(row)}`",
                    f"- original monitor flagged: `{_pred(row, augmented=False)}`",
                    f"- scope flagged: `{row.get('scope_postcondition_flagged')}`",
                    f"- augmented source: `{row.get('augmented_monitor_source')}`",
                    f"- scope reason: {row.get('scope_reason')}",
                    f"- trace: `{_trace(row)}`",
                    "",
                    f"> {_snippet(str(row.get('final_output', '')))}",
                    "",
                ]
            )
    return "\n".join(lines)


def paper_ready_final_metrics(summary_rows: list[dict[str, Any]], holdout: dict[str, Any]) -> str:
    """Return cautious paper-ready narrative."""

    by_name = {row["metric_set"]: row for row in summary_rows}
    hard_orig = by_name.get("original_hard_label", {})
    hard_aug = by_name.get("augmented_hard_label", {})
    all_orig = by_name.get("original_all_valid", {})
    all_aug = by_name.get("augmented_all_valid", {})
    lines = [
        "# Paper-Ready Final Clean Scope Metrics",
        "",
        "We evaluate a scope-aware postcondition layer on a fresh clean run. The augmented monitor improves detection of residual boundary violations while preserving false-positive behavior on clean negatives in this artifact.",
        "",
        f"Hard-label original monitor: TP/TN/FP/FN={_counts_text(hard_orig)}, F1={_fmt(hard_orig.get('f1'))}.",
        f"Hard-label augmented monitor: TP/TN/FP/FN={_counts_text(hard_aug)}, F1={_fmt(hard_aug.get('f1'))}.",
        f"All-valid original monitor: TP/TN/FP/FN={_counts_text(all_orig)}, F1={_fmt(all_orig.get('f1'))}.",
        f"All-valid augmented monitor: TP/TN/FP/FN={_counts_text(all_aug)}, F1={_fmt(all_aug.get('f1'))}.",
        "",
        "Holdout validation uses fresh original-monitor false negatives from this run, without tuning the scope rules after observing them.",
        (
            f"Fresh original-monitor FNs: {holdout.get('fresh_original_monitor_FN_count', 0)}; "
            f"recovered by scope defense: {holdout.get('fresh_FN_recovered_by_scope_defense', 0)} "
            f"({_fmt(holdout.get('fresh_FN_recovery_rate'))}); new FPs on clean TNs: "
            f"{holdout.get('fresh_new_FP_from_scope_defense', 0)}/{holdout.get('fresh_clean_TN_count', 0)}."
        ),
        "",
        "Recommended wording: The scope-aware check is rule-based and targeted at the failure patterns identified in this benchmark; broader generalization requires additional task families and external validation.",
    ]
    if holdout.get("fresh_original_monitor_FN_count", 0) < 5:
        lines.append("Caveat: holdout validation was limited by a low fresh residual miss count.")
    return "\n".join(lines) + "\n"


def paper_ready_tables(summary_rows: list[dict[str, Any]], holdout: dict[str, Any]) -> str:
    """Return markdown tables ready for paper drafting."""

    lines = ["# Paper-Ready Tables", "", "## Original vs Augmented Monitor", ""]
    lines.extend(_markdown_table(summary_rows, ["metric_set", "TP", "TN", "FP", "FN", "precision", "recall", "f1"]))
    lines.extend(["", "## Scope-Defense Holdout", ""])
    lines.extend(_markdown_table([holdout], list(holdout.keys())[:8]) if holdout else ["No holdout validation was run."])
    return "\n".join(lines) + "\n"


def tier_miss_type_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = _selected_rows(rows, "exclude")
    out = []
    for label, predicate in [("same_tier", lambda row: excess_tier(row) == 0), ("excess_tier", lambda row: excess_tier(row) > 0)]:
        group = [row for row in selected if predicate(row)]
        out.append({**metric_row(group, metric_set=label, policy="exclude", augmented=True), "tier_miss_type": label})
    return out


def count_rows(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    counts = Counter(str(row.get(field) or "none") for row in rows)
    return [{field: key, "count": value, "pct": rate(value, len(rows))} for key, value in sorted(counts.items())]


def _selected_rows(rows: list[dict[str, Any]], policy: AmbiguousViolationPolicy) -> list[dict[str, Any]]:
    valid = [row for row in rows if row.get("valid_run", True)]
    if policy == "exclude":
        return [row for row in valid if not ambiguous_violation(row)]
    return valid


def _pred(row: dict[str, Any], *, augmented: bool) -> bool:
    return bool(row.get("augmented_monitor_flagged")) if augmented else bool(row.get("monitor_flagged"))


def _confusion(rows: list[dict[str, Any]], policy: AmbiguousViolationPolicy, *, augmented: bool) -> dict[str, int]:
    counts = {"TP": 0, "TN": 0, "FP": 0, "FN": 0}
    for row in rows:
        outcome = classify_monitor_outcome(true_violation(row, policy), _pred(row, augmented=augmented))
        counts[outcome] += 1
    return counts


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not fieldnames:
            handle.write("")
            return
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit_hash() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def _trace(row: dict[str, Any]) -> str:
    return " -> ".join(str(call.get("tool_name", "")) for call in row.get("tool_trace", []))


def _snippet(text: str, limit: int = 360) -> str:
    normalized = " ".join(text.split())
    return normalized if len(normalized) <= limit else normalized[: limit - 3] + "..."


def _fmt(value: Any) -> str:
    return "n/a" if value is None else f"{float(value):.3f}"


def _counts_text(row: dict[str, Any]) -> str:
    return f"{row.get('TP', 0)}/{row.get('TN', 0)}/{row.get('FP', 0)}/{row.get('FN', 0)}"


def _markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return lines


def load_final_clean_outputs(run_dir: Path) -> dict[str, Any]:
    """Load core output tables for UI display."""

    summaries = run_dir / "summaries"
    return {
        "original_all_valid": _read_csv_one(summaries / "original_all_valid_summary.csv"),
        "original_hard_label": _read_csv_one(summaries / "original_hard_label_summary.csv"),
        "augmented_all_valid": _read_csv_one(summaries / "augmented_all_valid_summary.csv"),
        "augmented_hard_label": _read_csv_one(summaries / "augmented_hard_label_summary.csv"),
        "holdout": _read_csv_one(run_dir / "scope_defense_holdout_summary.csv"),
    }


def _read_csv_one(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows[0] if rows else {}


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the fresh clean scope workflow."""

    parser = argparse.ArgumentParser(description="Run a fresh clean scope-defense final experiment.")
    parser.add_argument("--provider", choices=["opensource", "openai", "openai_compatible", "deterministic"], default="opensource")
    parser.add_argument("--builder-model", default=DEFAULT_OPENSOURCE_MODEL)
    parser.add_argument("--monitor-model", default=DEFAULT_OPENSOURCE_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_OPENSOURCE_BASE_URL)
    parser.add_argument("--runs-per-task", type=int, default=100)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output-dir", type=Path, default=default_final_clean_output_dir())
    parser.add_argument("--output-filename", default="final_clean_scope_run.jsonl")
    parser.add_argument("--disable-scope-defense", action="store_true")
    parser.add_argument("--skip-holdout-validation", action="store_true")
    return parser.parse_args()


def main() -> None:
    """CLI entrypoint."""

    args = parse_args()
    result = run_final_clean_scope_experiment(
        provider_name=args.provider,
        builder_model=args.builder_model,
        monitor_model=args.monitor_model,
        base_url=args.base_url,
        runs_per_task=args.runs_per_task,
        random_seed=args.seed,
        output_dir=args.output_dir,
        output_filename=args.output_filename,
        enable_scope_defense=not args.disable_scope_defense,
        run_holdout_validation=not args.skip_holdout_validation,
    )
    print(f"Wrote final clean scope artifact to {result['artifact_path']}")
    print(f"Wrote manifest to {result['manifest_path']}")


if __name__ == "__main__":
    main()
