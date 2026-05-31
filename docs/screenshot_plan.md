# Screenshot Plan

The English screenshots in `docs/screenshots_en/` are generated from the local
Streamlit demo and should be used in the EMNLP demo paper or submission
appendix. The Chinese screenshots in `docs/screenshots/` are kept for local
project defense.

Recommended figures:

1. `sample_audit_false_consensus.png`: model-level trace and risk labels for
   `fever_0366`.
2. `aggregate_statistics.png`: aggregate method comparison and risk charts.
3. `submission_readiness.png`: EMNLP checklist and journal targets.

Generation command:

```bash
node scripts/capture_screenshots_en.mjs
```

The English Streamlit app must be running at `http://localhost:8502` before executing
the command.
