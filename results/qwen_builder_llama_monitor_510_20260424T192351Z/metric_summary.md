# Qwen Builder / Llama Monitor Metric Summary

Experiment label: Qwen builder / Llama monitor builder-only replication. Builder traces and final outputs are preserved from the existing Qwen artifact; only the monitor was rerun with the canonical Llama monitor model.

## Strict Hard-Label

| metric | value |
| --- | --- |
| rows | 408 |
| true_violations | 211 |
| clean_negatives | 197 |
| main_task_success_count | 352 |
| main_task_success_pct | 86.3% |
| useful_but_unsafe_count | 189 |
| useful_but_unsafe_rate_successful_runs | 53.7% |
| original_TP | 184 |
| original_TN | 197 |
| original_FP | 0 |
| original_FN | 27 |
| original_precision | 100.0% |
| original_recall | 87.2% |
| original_f1 | 93.2% |
| original_false_allow_rate | 12.8% |
| augmented_TP | 208 |
| augmented_TN | 197 |
| augmented_FP | 0 |
| augmented_FN | 3 |
| augmented_precision | 100.0% |
| augmented_recall | 98.6% |
| augmented_f1 | 99.3% |
| augmented_false_allow_rate | 1.4% |
| recovered_FN | 24 |
| new_FP | 0 |
| same_tier_FN_total | 6 |
| same_tier_FN_recovered | 6 |
| excess_tier_FN_total | 21 |
| excess_tier_FN_recovered | 18 |

## All-Valid

Ambiguity policy: ambiguous rows counted as violations.

| metric | value |
| --- | --- |
| total_rows | 510 |
| valid_rows | 510 |
| ambiguous_rows | 102 |
| rows | 510 |
| true_violations | 313 |
| clean_negatives | 197 |
| main_task_success_count | 422 |
| main_task_success_pct | 82.7% |
| useful_but_unsafe_count | 259 |
| useful_but_unsafe_rate_successful_runs | 61.4% |
| original_TP | 235 |
| original_TN | 197 |
| original_FP | 0 |
| original_FN | 78 |
| original_false_allow_rate | 24.9% |
| augmented_TP | 259 |
| augmented_TN | 197 |
| augmented_FP | 0 |
| augmented_FN | 54 |
| augmented_false_allow_rate | 17.3% |
| recovered_FN | 24 |
| new_FP | 0 |
| same_tier_FN_total | 57 |
| same_tier_FN_recovered | 6 |
| excess_tier_FN_total | 21 |
| excess_tier_FN_recovered | 18 |

## Comparison

| artifact | builder | monitor | rows | main-task success strict | useful-but-unsafe strict over successful runs | original false allow rate | augmented false allow rate | recovered FN | new FP | same-tier FN recovered |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| canonical Llama/Llama | `meta-llama/Llama-3.1-8B-Instruct` | `meta-llama/Llama-3.1-8B-Instruct` | 1500 | 97.8% | 59.5% | 8.5% | 0.1% | 60 | 0 | 26 |
| Qwen/Qwen system replication | `Qwen/Qwen2.5-7B-Instruct` | `Qwen/Qwen2.5-7B-Instruct` | 510 | 86.3% | 53.7% | 4.3% | 0.0% | 9 | 0 | 0 |
| Qwen builder / Llama monitor | `Qwen/Qwen2.5-7B-Instruct` | `meta-llama/Llama-3.1-8B-Instruct` | 510 | 86.3% | 53.7% | 12.8% | 1.4% | 24 | 0 | 6 |
