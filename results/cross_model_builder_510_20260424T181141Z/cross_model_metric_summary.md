# Cross-Model Metric Summary

Experiment label: cross-model system replication. Builder and monitor both used `Qwen/Qwen2.5-7B-Instruct` because the local vLLM provider exposed only one model at a time and the GPU could not host both Qwen and Llama concurrently.

## Main Benchmark

| metric | value |
| --- | --- |
| total_runs | 510 |
| valid_runs | 510 |
| invalid_rows | 0 |
| metric_rows | 408 |
| main_task_success_count | 352 |
| main_task_success_pct | 86.3% |
| true_violation_count | 211 |
| true_violation_pct | 51.7% |
| safety_adjusted_success_count | 163 |
| safety_adjusted_success_pct | 40.0% |
| useful_but_unsafe_count | 189 |
| useful_but_unsafe_rate | 46.3% |
| same_tier_true_violations | 23 |
| mean_excess_tier | 0.605 |

## Monitor Metrics

Strict hard-label policy excludes ambiguous rows. All-valid policy treats ambiguous rows as violations.

| policy | monitor | TP | TN | FP | FN | precision | recall | F1 | false allow | false positive | recovered FN | new FP | same-tier FN recovered | excess-tier FN recovered |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| exclude | original | 202 | 197 | 0 | 9 | 100.0% | 95.7% | 97.8% | 4.3% | 0.0% |  |  |  |  |
| exclude | augmented | 211 | 197 | 0 | 0 | 100.0% | 100.0% | 100.0% | 0.0% | 0.0% | 9 | 0 | 0 | 9 |
| violation | original | 253 | 197 | 0 | 60 | 100.0% | 80.8% | 89.4% | 19.2% | 0.0% |  |  |  |  |
| violation | augmented | 262 | 197 | 0 | 51 | 100.0% | 83.7% | 91.1% | 16.3% | 0.0% | 9 | 0 | 0 | 9 |

## Comparison To Canonical Final Run

| run | rows | main-task success | useful-but-unsafe rate | original false allow | augmented false allow | new FP | same-tier FN recovery |
| --- | --- | --- | --- | --- | --- | --- | --- |
| canonical_final_clean_1500 | 1500 | 97.8% | 58.2% | 8.5% | 0.1% | 0 | 26 |
| cross_model_system_replication_510 | 510 | 86.3% | 46.3% | 4.3% | 0.0% | 0 | 0 |

## Breakdowns

See `cross_model_by_condition.csv`, `cross_model_by_scenario.csv`, and `cross_model_remaining_misses.md`.
