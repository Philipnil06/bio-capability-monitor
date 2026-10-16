# Bio Capability Boundary Monitor

**Can an AI monitor distinguish completing a task from quietly expanding its scope?**

This Python research harness evaluates agents on harmless, abstract workflow
fixtures. It separates what the agent was asked to do, what its tool trace and
answer show, and whether a monitor detects an unauthorised capability or scope
expansion. It is an **AI safety evaluation prototype**, not a production
security detector. Tools return local fixture data.

## One example

An agent is asked to summarise an internal note. It retrieves the note and
answers the question, then adds an unrequested follow-up workflow. The task
may be complete while the answer still exceeds the allowed scope. That can
happen without crossing into a higher tool tier.

The harness records visible-task success, tool tiers, side-task attempt and
success, verifier labels, and the monitor's judgment separately.

```text
Visible task + scope -> builder -> saved tool trace + final output
                                    |-> verifier: evaluation labels
                                    |-> model monitor: flag + explanation
                                    `-> optional rules: extra scope signal
```

## Three distinct components

| Component | Purpose | Interpretation |
| --- | --- | --- |
| Controlled benchmark / deterministic runner | Designed tasks, conditions, and calibrated variation | Repeatable pipeline fixtures, not independently sampled real-world behaviour |
| Model monitor | An LLM inspects the visible task, allowed tier, trace, and output | A model decision compared with verifier labels; corrected input excludes the hidden side goal |
| Scope-aware postcondition check | Explicit rules detect selected patterns of unrequested follow-up scope | A targeted addition; the augmented decision is model flag **OR** rule flag |

Provider-backed runs also include documented task/repeat calibration. That
steering is part of benchmark construction and matters when interpreting model
performance. Deterministic-demo scores are not LLM results.

## Recorded results

The headline snapshot is the **1,500-run fresh clean experiment completed
24 April 2026**, with Llama-3.1-8B-Instruct as builder and monitor. These are
**saved artifact results**, not a new model run during repository cleanup.
See its [manifest](results/final_clean_scope_20260424T085810Z/manifest.json).

| Slice | Monitor | TP | TN | FP | FN | F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Hard labels; ambiguous rows excluded (1,200 rows) | Original model | 659 | 480 | 0 | 61 | 0.956 |
| Same hard-label rows | Model + rules | 719 | 480 | 0 | 1 | 0.999 |
| All valid rows (1,500 rows) | Original model | 809 | 480 | 0 | 211 | 0.885 |
| Same all-valid rows | Model + rules | 869 | 480 | 0 | 151 | 0.920 |

TP/TN are correctly flagged violations/correctly accepted negatives; FP/FN are
false alarms/missed violations. Rules recovered **60 of 61** original-monitor
misses in the hard-label slice and added **0 false alarms among 480 clean
negatives** in this artifact. Keeping ambiguous cases gives materially
different results, as the all-valid rows show.

Rules were developed around this benchmark's failure patterns. The fresh run
has new traces from the same task families; it is **not a held-out test on new
domains or task families**. Zero observed false alarms does not imply a zero
deployment false-positive rate. These results do not establish general
biosecurity, phishing, or cybersecurity detection accuracy.

[Metric notes](results/final_clean_scope_20260424T085810Z/paper_ready_final_metrics.md)
and [tables](results/final_clean_scope_20260424T085810Z/paper_ready_tables.md)
contain the saved evidence. Older `results/final/` artifacts hold the original
benchmark and corrected monitor-only rerun: separate snapshots that should not
be mixed with this table.

## Quick start: no model server or API key

Use Python 3.12. Run from the repository root:

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
python -m src.run_experiment --provider deterministic --runs-per-task 2 --output work/demo.jsonl
python -m src.analyze_results work/demo.jsonl --output-dir work/demo-summary
```

This produces **30 deterministic fixture runs** (15 tasks × 2 repeats). It
checks the workflow; it does not reproduce the saved model benchmark.

For a new model-backed run, start a compatible local endpoint, then:

```bash
python -m src.run_experiment --provider opensource --base-url http://localhost:8000/v1 --builder-model meta-llama/Llama-3.1-8B-Instruct --monitor-model meta-llama/Llama-3.1-8B-Instruct --runs-per-task 2 --output work/model-run.jsonl
```

Model weights, hardware requirements, and server setup are external to this
repository. Hosted-provider runs require credentials and may incur API costs.
The quick start above does not use them.

## Explore

- [Detailed experiment guide](docs/EXPERIMENT_GUIDE.md): task conditions, calibration, providers, reruns, and analysis.
- [`src/monitor.py`](src/monitor.py): deterministic and model-backed monitoring.
- [`src/scope_postcondition.py`](src/scope_postcondition.py): targeted rules and their restricted input payload.
- [`src/verify.py`](src/verify.py): separate evaluation labels.
- [`tests/test_pipeline.py`](tests/test_pipeline.py): regression coverage, including monitor-input boundaries.
- [Human audit rubric](human_audit/reviewer_rubric.md): reviewing saved cases.

An optional UI is available with `streamlit run src/debug_ui.py`. For technical
review, start with one trace and its labels before inspecting aggregate metrics.
