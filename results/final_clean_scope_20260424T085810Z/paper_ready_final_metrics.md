# Paper-Ready Final Clean Scope Metrics

We evaluate a scope-aware postcondition layer on a fresh clean run. The augmented monitor improves detection of residual boundary violations while preserving false-positive behavior on clean negatives in this artifact.

Hard-label original monitor: TP/TN/FP/FN=659/480/0/61, F1=0.956.
Hard-label augmented monitor: TP/TN/FP/FN=719/480/0/1, F1=0.999.
All-valid original monitor: TP/TN/FP/FN=809/480/0/211, F1=0.885.
All-valid augmented monitor: TP/TN/FP/FN=869/480/0/151, F1=0.920.

Holdout validation uses fresh original-monitor false negatives from this run, without tuning the scope rules after observing them.
Fresh original-monitor FNs: 61; recovered by scope defense: 60 (0.984); new FPs on clean TNs: 0/480.

Recommended wording: The scope-aware check is rule-based and targeted at the failure patterns identified in this benchmark; broader generalization requires additional task families and external validation.
