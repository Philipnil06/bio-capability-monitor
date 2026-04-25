# Paper-Ready Final Clean Scope Metrics

We evaluate a scope-aware postcondition layer on a fresh clean run. The augmented monitor improves detection of residual boundary violations while preserving false-positive behavior on clean negatives in this artifact.

Hard-label original monitor: TP/TN/FP/FN=202/197/0/9, F1=0.978.
Hard-label augmented monitor: TP/TN/FP/FN=211/197/0/0, F1=1.000.
All-valid original monitor: TP/TN/FP/FN=253/197/0/60, F1=0.894.
All-valid augmented monitor: TP/TN/FP/FN=262/197/0/51, F1=0.911.

Holdout validation uses fresh original-monitor false negatives from this run, without tuning the scope rules after observing them.
Fresh original-monitor FNs: 9; recovered by scope defense: 9 (1.000); new FPs on clean TNs: 0/197.

Recommended wording: The scope-aware check is rule-based and targeted at the failure patterns identified in this benchmark; broader generalization requires additional task families and external validation.
