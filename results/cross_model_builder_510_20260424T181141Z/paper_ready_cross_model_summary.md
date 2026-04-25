# Paper-Ready Cross-Model Summary

## Main-Paper Paragraph If Results Are Strong

As a cross-model robustness check, we reran the clean scope-defense evaluation for 510 rows using Qwen/Qwen2.5-7B-Instruct as both builder and monitor, because the local provider could only serve one model at a time. The qualitative pattern replicated: main-task success was 86.3%, useful-but-unsafe behavior was 46.3%, and the scope-aware postcondition reduced strict hard-label false allows from 4.3% to 0.0%, recovering 9 original-monitor false negatives with 0 new false positives. This supports the claim that the observed boundary-monitor failure mode and the targeted scope-defense improvement are not specific to the original Llama-3.1-8B-Instruct system run.

## Appendix Paragraph If Results Are Mixed

In a 510-row cross-model system replication with Qwen/Qwen2.5-7B-Instruct used for both builder and monitor, the benchmark preserved the same task definitions, verifier labels, monitor prompt, and rule-based scope-defense payload. The augmented monitor reduced strict hard-label false allows from 4.3% to 0.0%, recovering 9 original-monitor misses; however, because this run changed both builder and monitor rather than the builder alone, it should be interpreted as system-level replication rather than isolated builder-model robustness.

## Exact Safe Claims

- This was a cross-model system replication, not the canonical final run.
- The run used the same benchmark task definitions, verifier logic, monitor logic, and scope-defense rules as the canonical clean-scope run.
- The run completed 510/510 expected rows with 0 invalid rows.
- Under strict hard-label evaluation, the augmented monitor recovered 9 original false negatives and introduced 0 new false positives.
- Strict hard-label false allow rate changed from 4.3% original to 0.0% augmented.
- Same-tier FN recovery was 0 in this run, unlike the canonical final run, so the same-tier recovery claim should remain tied to the canonical artifact.

## Claims To Avoid

- Do not call this a builder-only replication, since the original Llama monitor could not be kept active with Qwen locally.
- Do not describe it as a new tuning pass or use it to justify any post hoc rule changes.
- Do not claim broad model-family generalization beyond this one additional small/medium instruct model.
- Do not merge these numbers into the canonical 1500-row final run.

## Recommendation

Appendix robustness check. The false-allow reduction and zero-new-FP pattern replicated, but this run changed both builder and monitor and did not reproduce same-tier FN recovery.
