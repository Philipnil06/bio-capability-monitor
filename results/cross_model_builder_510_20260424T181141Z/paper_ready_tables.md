# Paper-Ready Tables

## Original vs Augmented Monitor

| metric_set | TP | TN | FP | FN | precision | recall | f1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| original_all_valid | 253 | 197 | 0 | 60 | 1.0 | 0.8083067092651757 | 0.8939929328621908 |
| original_hard_label | 202 | 197 | 0 | 9 | 1.0 | 0.957345971563981 | 0.9782082324455207 |
| augmented_all_valid | 262 | 197 | 0 | 51 | 1.0 | 0.8370607028753994 | 0.9113043478260869 |
| augmented_hard_label | 211 | 197 | 0 | 0 | 1.0 | 1.0 | 1.0 |

## Scope-Defense Holdout

| fresh_original_monitor_FN_count | fresh_FN_recovered_by_scope_defense | fresh_FN_recovery_rate | fresh_same_tier_FN_recovered | fresh_excess_tier_FN_recovered | fresh_clean_TN_count | fresh_new_FP_from_scope_defense | fresh_FP_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 9 | 9 | 1.0 | 0 | 9 | 197 | 0 | 0.0 |
