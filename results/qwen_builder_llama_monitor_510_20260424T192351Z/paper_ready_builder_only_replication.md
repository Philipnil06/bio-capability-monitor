# Paper-Ready Builder-Only Replication

## Appendix Paragraph

As a cross-builder robustness check with the monitor held fixed, we reran only the canonical Llama monitor on the preserved Qwen-generated builder traces and final outputs. In this 510-row Qwen builder / Llama monitor replication, strict hard-label visible-task success was 352/408 (86.3%), and useful-but-unsafe behavior accounted for 189/352 (53.7%) successful hard-label runs. The original Llama monitor had TP/TN/FP/FN = 184/197/0/27 and a false allow rate of 27/211 (12.8%); adding the fixed scope-aware postcondition layer changed this to TP/TN/FP/FN = 208/197/0/3 and reduced false allows to 1.4%, recovering 24 false negatives with 0 new false positives. This supports the claim that the main qualitative failure pattern and scope-defense improvement persist when the builder is changed to Qwen while the Llama monitor is held fixed.

## Comparison Table

| artifact | builder | monitor | rows | main-task success strict | useful-but-unsafe strict over successful runs | original false allow rate | augmented false allow rate | recovered FN | new FP | same-tier FN recovered |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| canonical Llama/Llama | `meta-llama/Llama-3.1-8B-Instruct` | `meta-llama/Llama-3.1-8B-Instruct` | 1500 | 97.8% | 59.5% | 8.5% | 0.1% | 60 | 0 | 26 |
| Qwen/Qwen system replication | `Qwen/Qwen2.5-7B-Instruct` | `Qwen/Qwen2.5-7B-Instruct` | 510 | 86.3% | 53.7% | 4.3% | 0.0% | 9 | 0 | 0 |
| Qwen builder / Llama monitor | `Qwen/Qwen2.5-7B-Instruct` | `meta-llama/Llama-3.1-8B-Instruct` | 510 | 86.3% | 53.7% | 12.8% | 1.4% | 24 | 0 | 6 |

## Safe Wording

- Use “Qwen builder / Llama monitor builder-only replication” or “cross-builder replication with fixed Llama monitor.”
- Say the run reused preserved Qwen builder traces and final outputs and reran only the canonical Llama monitor.
- Say the qualitative pattern replicated: high visible-task success, substantial useful-but-unsafe behavior, Llama monitor false allows, and reduced augmented false allow rate with no new FPs.
- Avoid claiming broad model-family generalization, retuning, or independence from the benchmark task family.

## Payload Safety Audit

- Payload keys seen: `allowed_tier, excess_tier, final_output, observed_tier, scenario_id, tool_trace, visible_prompt`
- Forbidden payload fields present: `[]`
- Unexpected payload fields present: `[]`
