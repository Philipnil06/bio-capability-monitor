# Deployment Gate Summary

The intended workflow is a trace-first biosecurity boundary review:

1. Collect model traces, tool calls, observed tool tiers, and final outputs.
2. Assign the allowed biological scope before evaluation using the visible task and scenario policy.
3. Run the scope-aware audit using only visible prompt, scenario, allowed tier, observed tier, derived excess tier, tool trace, and final output.
4. Review findings by severity, starting with critical and high cases, then medium trace-minimality or validation-drift cases.
5. Apply mitigations such as restricting external retrieval, requiring human review for follow-up handling advice, blocking protocol-style follow-up generation, adding a trace-minimality gate, or clarifying allowed biological scope.
6. Rerun the audit on the same traces or a new validation batch without using ground-truth labels at decision time.
7. Decide allow, review, restrict, block, or redesign_policy based on reviewer severity and residual false-allow risk.
