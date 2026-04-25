# Paper-Ready Final Clean Scope Metrics

We evaluate a scope-aware postcondition layer on a fresh clean run. The augmented monitor improves detection of residual boundary violations while preserving false-positive behavior on clean negatives in this artifact.

Hard-label original monitor: TP/TN/FP/FN=4/5/0/3, F1=0.727.
Hard-label augmented monitor: TP/TN/FP/FN=7/5/0/0, F1=1.000.
All-valid original monitor: TP/TN/FP/FN=4/5/0/6, F1=0.571.
All-valid augmented monitor: TP/TN/FP/FN=9/5/0/1, F1=0.947.

Holdout validation uses fresh original-monitor false negatives from this run, without tuning the scope rules after observing them.
Fresh original-monitor FNs: 3; recovered by scope defense: 3 (1.000); new FPs on clean TNs: 0/5.

Recommended wording: The scope-aware check is rule-based and targeted at the failure patterns identified in this benchmark; broader generalization requires additional task families and external validation.
Caveat: holdout validation was limited by a low fresh residual miss count.
