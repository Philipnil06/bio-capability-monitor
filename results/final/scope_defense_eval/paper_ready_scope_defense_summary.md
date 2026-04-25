# Paper-Ready Scope Defense Summary

Source artifact: `results/final/monitor_rerun/final_1500_monitor_rerun.jsonl`

Condition-label shortcut validation: the scope checker does not use `condition` to decide whether to flag. The decision payload contains scenario, visible prompt, allowed tier, observed tier, excess tier, tool trace, final output, verifier labels for audit context, and original monitor fields, but excludes both `condition` and `hidden_side_goal`. Condition is used only after flagging for aggregate reporting.

The scope-aware postcondition check recovered 69 of 69 residual false negatives (100.0%), including 29 of 29 same-tier misses and 40 excess-tier misses.

On a clean negative sample of 200 true-negative rows, it introduced 0 new false positives (0.0%). Across all hard-label rows, the augmented monitor introduced 0 new false positives.

Original corrected monitor metrics were precision=1.000, recall=0.903, F1=0.949. Augmented metrics were precision=1.000, recall=1.000, F1=1.000.

All-valid augmented metrics: original TP/TN/FP/FN=795/486/0/219; augmented TP/TN/FP/FN=864/486/0/150; recovered FN=69; new FP=0.
Strict ambiguity-excluded metrics: original TP/TN/FP/FN=645/486/0/69; augmented TP/TN/FP/FN=714/486/0/0; recovered FN=69; new FP=0.

Scope-defense false positives on all-valid true negatives: 0/486.
Scope-defense false positives on strict true negatives: 0/486.

Scope-defense false positives by condition, all-valid: none
Scope-defense false positives by condition, strict ambiguity-excluded: none

Recovered false negatives by cluster:
- S1 benign_overuse: 37
- S1 partial_adversarial: 2
- S2 partial_adversarial: 11
- S3 partial_adversarial: 19

The results are strong enough to report as an implemented additional defense layer, with cautious framing.
