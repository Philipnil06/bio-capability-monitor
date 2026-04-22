from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path


def copy_required(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(f"Missing required file: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def dedupe_latest_rerun_rows(src: Path, dst: Path) -> dict[str, int]:
    if not src.exists():
        raise FileNotFoundError(f"Missing required file: {src}")

    latest_by_run_id: dict[str, dict] = {}
    duplicate_rows = 0
    total_rows = 0

    with src.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            total_rows += 1
            run_id = str(row["run_id"])
            rerun_timestamp = str(row.get("rerun_timestamp", ""))
            previous = latest_by_run_id.get(run_id)
            if previous is not None:
                duplicate_rows += 1
            if previous is None or rerun_timestamp > str(previous.get("rerun_timestamp", "")):
                latest_by_run_id[run_id] = row

    ordered_rows = sorted(
        latest_by_run_id.values(),
        key=lambda row: (str(row.get("timestamp", "")), str(row.get("run_id", ""))),
    )
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8") as handle:
        for row in ordered_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    return {
        "source_rows": total_rows,
        "deduped_rows": len(ordered_rows),
        "duplicate_rows": duplicate_rows,
    }


def extract_overall_metrics(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8", newline="") as handle:
        return next(csv.DictReader(handle))


def write_manifest(path: Path, entries: dict[str, object]) -> None:
    path.write_text(json.dumps(entries, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Freeze final paper-facing benchmark artifacts.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    results_dir = repo_root / "results"
    final_dir = results_dir / "final"

    original_src = results_dir / "latest_ui.jsonl"
    rerun_raw_src = results_dir / "latest_ui_monitor_rerun.jsonl"
    original_summary_src = results_dir / "latest_ui_summaries"
    original_audit_src = results_dir / "latest_ui_audit_15.md"

    original_dst = final_dir / "original" / "final_1500_original.jsonl"
    rerun_raw_dst = final_dir / "monitor_rerun" / "final_1500_monitor_rerun_raw_3000rows.jsonl"
    rerun_clean_dst = final_dir / "monitor_rerun" / "final_1500_monitor_rerun.jsonl"
    audit_dst = final_dir / "audit" / "final_audit_15.md"

    copy_required(original_src, original_dst)
    copy_required(rerun_raw_src, rerun_raw_dst)
    if original_audit_src.exists():
        copy_required(original_audit_src, audit_dst)

    dedupe_summary = dedupe_latest_rerun_rows(rerun_raw_src, rerun_clean_dst)

    for name in [
        "overall_summary.csv",
        "by_condition_summary.csv",
        "by_scenario_summary.csv",
        "by_scenario_condition_summary.csv",
        "borderline_summary.csv",
        "overall_summary.json",
    ]:
        copy_required(original_summary_src / name, final_dir / "summaries" / "original" / f"original_{name}")

    manifest = {
        "final_original_artifact": str(original_dst.relative_to(repo_root)),
        "final_monitor_rerun_artifact": str(rerun_clean_dst.relative_to(repo_root)),
        "raw_monitor_rerun_source": str(rerun_raw_dst.relative_to(repo_root)),
        "copied_original_audit_sample": str(audit_dst.relative_to(repo_root)) if audit_dst.exists() else None,
        "monitor_rerun_dedupe": dedupe_summary,
    }
    write_manifest(final_dir / "freeze_manifest.json", manifest)

    original_overall = extract_overall_metrics(final_dir / "summaries" / "original" / "original_overall_summary.csv")
    print(
        json.dumps(
            {
                "manifest_path": str((final_dir / "freeze_manifest.json").relative_to(repo_root)),
                "original_total_runs": original_overall["total_runs"],
                "original_true_violation_count": original_overall["true_violation_count"],
                **dedupe_summary,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
