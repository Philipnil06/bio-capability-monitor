# Human Audit Package

This directory contains blinded human-audit samples for the Bio Capability Boundary Monitor Track 3 paper.

Give the human reviewer only:

- `audit_sample_100_for_reviewer.csv`
- or `audit_sample_50_for_reviewer.csv`
- `reviewer_rubric.md`

Do not give the reviewer either internal key CSV. The key files contain ground-truth labels, monitor predictions, scope-defense predictions, and reviewer-report outputs for post-hoc scoring only.

## Files

- `audit_sample_100_for_reviewer.csv`: blinded 100-run reviewer sample.
- `audit_sample_100_key_internal.csv`: internal key for the 100-run sample.
- `audit_sample_50_for_reviewer.csv`: blinded 50-run fallback sample.
- `audit_sample_50_key_internal.csv`: internal key for the fallback sample.
- `reviewer_rubric.md`: reviewer instructions and scoring rubric.
- `score_human_audit.py`: scoring script for completed reviewer files.

## Scoring

After the reviewer fills the human columns, run:

```bash
python human_audit/score_human_audit.py \
  --reviewer-csv human_audit/audit_sample_100_for_reviewer.csv \
  --key-csv human_audit/audit_sample_100_key_internal.csv \
  --summary-md human_audit/audit_sample_100_score_summary.md \
  --disagreements-csv human_audit/audit_sample_100_disagreements.csv
```

The script computes agreement with verifier labels and, when available, agreement with the Track 3 reviewer-report category, severity, and decision fields.
