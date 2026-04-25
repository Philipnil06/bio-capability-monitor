# Paper-Ready Tables

## Original vs Augmented Monitor

| metric_set | TP | TN | FP | FN | precision | recall | f1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| original_all_valid | 4 | 5 | 0 | 6 | 1.0 | 0.4 | 0.5714285714285715 |
| original_hard_label | 4 | 5 | 0 | 3 | 1.0 | 0.5714285714285714 | 0.7272727272727273 |
| augmented_all_valid | 9 | 5 | 0 | 1 | 1.0 | 0.9 | 0.9473684210526316 |
| augmented_hard_label | 7 | 5 | 0 | 0 | 1.0 | 1.0 | 1.0 |

## Scope-Defense Holdout

| fresh_original_monitor_FN_count | fresh_FN_recovered_by_scope_defense | fresh_FN_recovery_rate | fresh_same_tier_FN_recovered | fresh_excess_tier_FN_recovered | fresh_clean_TN_count | fresh_new_FP_from_scope_defense | fresh_FP_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | 3 | 1.0 | 0 | 3 | 5 | 0 | 0.0 |
