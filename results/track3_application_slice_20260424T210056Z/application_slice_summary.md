# Track 3 Application Slice Summary

To address Track 3 external validity more directly, we added a small non-operational application slice modeled on two safe review settings: public-health signal triage and redacted screening-policy review. The slice uses synthetic metadata, fictional labels, and redacted fields only. It does not include real biological sequences, organism names, operational protocols, experimental plans, or lab-execution guidance. The purpose is not to simulate deployment end-to-end, but to test whether the capability-boundary framing transfers to workflows closer to practical biosecurity review.

## Paper-Ready Table

| Application slice | Rows | Main-task success | Useful-but-unsafe rate | Original false allow rate | Augmented false allow rate | Recovered FN | New FP | Rule transfer result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Public-health signal triage proxy | 50 | 100.0% | 75.0% | 33.3% | 0.0% | 10 | 0 | transferred cleanly |
| Redacted screening-policy review proxy | 50 | 100.0% | 75.0% | 0.0% | 0.0% | 0 | 0 | transferred cleanly |
| Overall | 100 | 100.0% | 75.0% | 16.7% | 0.0% | 10 | 0 | transferred cleanly |

## Metrics

- JSONL SHA256: `32cf0d2e09f0228ebcf5fe8dbc983ea37abd206886137ff06beff919708a4ecf`
- Total rows: `100`
- Main-task success: `80/80` (100.0%)
- True violation rate: `60/80` (75.0%)
- Useful-but-unsafe rate: `60/80` (75.0%)
- Original monitor TP/TN/FP/FN: `50/20/0/10`
- Augmented monitor TP/TN/FP/FN: `60/20/0/0`
- Recovered false negatives: `10`
- New false positives: `0`
- Same-tier FNs recovered: `10/10`

## Existing Rule Transfer

Rule transfer result: **transferred cleanly**.
The existing scope-aware postcondition rules transferred cleanly on this slice.
