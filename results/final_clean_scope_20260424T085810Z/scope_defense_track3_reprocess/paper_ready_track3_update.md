# Paper-Ready Track 3 Update

## Methods Paragraph

For Track 3, we added a reviewer-report layer on top of the rule-based scope-aware postcondition audit. The decision payload for the scope audit contains only the visible prompt, scenario identifier, allowed tier, observed tier, derived excess tier, tool trace, and final output. It excludes condition labels, hidden side goals, verifier outcomes, TP/TN/FP/FN labels, and all ground-truth violation fields. Reviewer categories and severities are assigned from the scope-audit output plus trace/output facts, while ground-truth labels are used only afterward for metric computation.

## Results Paragraph

In the strict ambiguity-excluded slice, the original monitor produced TP/TN/FP/FN = 659/480/0/61 with precision 1.000, recall 0.915, and F1 0.956. The augmented monitor produced TP/TN/FP/FN = 719/480/0/1 with precision 1.000, recall 0.999, and F1 0.999. The scope layer recovered 26 same-tier false negatives and 34 excess-tier false negatives, with 0 new false positives.

## Biosecurity Boundary Report Table

| Metric set | Ambiguity policy | Original TP/TN/FP/FN | Augmented TP/TN/FP/FN | Original false allow rate | Augmented false allow rate | Useful-but-unsafe rate | New FP |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Strict hard-label | exclude ambiguous | 659/480/0/61 | 719/480/0/1 | 0.085 | 0.001 | 0.595 | 0 |
| All valid | ambiguous as violation | 809/480/0/211 | 869/480/0/151 | 0.207 | 0.148 | 0.672 | 0 |

## False Allow Rate Paragraph

False allow rate is defined as FN divided by true violations after labels are applied for metrics. In the strict hard-label slice, augmentation reduced false allow rate from 0.085 to 0.001. In the all-valid slice, with ambiguous cases counted as violations, augmentation reduced false allow rate from 0.207 to 0.148.

## Useful-But-Unsafe Rate Paragraph

Useful-but-unsafe rate is defined as main-task-successful runs that are true violations divided by all main-task-successful runs. In the strict hard-label slice this rate was 699/1174 (0.595); in the all-valid slice it was 974/1449 (0.672).

## Label-Leakage-Safe Methods Paragraph

The scope-aware postcondition audit and Track 3 reviewer report are label-leakage safe at decision time. The audit payload does not include true_violation, attempted_violation, successful_violation, overuse_violation, ambiguous_violation, side_task labels, condition, hidden_side_goal, monitor_outcome, verifier notes, or TP/TN/FP/FN labels. These labels are loaded only after predictions are fixed, and only to compute precision, recall, F1, false allow rate, useful-but-unsafe rate, and category-level error summaries.

## Caveat Paragraph

The Track 3 reviewer report is an auditable rule-based reporting layer, not a comprehensive biosecurity classifier. It is useful for explaining residual boundary risk and routing cases to human review, but its categories are benchmark-specific and should be validated on additional biological workflow families before being treated as a general deployment-control system.
