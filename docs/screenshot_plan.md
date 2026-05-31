# Screenshot Plan

The English screenshots in `docs/screenshots_en/` are generated from the local
Streamlit demo and should be used in the EMNLP demo paper or submission
appendix. The Chinese screenshots in `docs/screenshots/` are kept for local
project defense.

Recommended figures:

1. `sample_audit_false_consensus.png`: model-level trace and risk labels for
   `fever_0366`.
2. `aggregate_statistics.png`: current Risk Dashboard with offline diagnostic
   label counts and risk-level effectiveness.
3. `report_export.png`: current Report Export page with downloadable artifacts.

Generation command:

```bash
node scripts/capture_screenshots_en.mjs
```

The English Streamlit app must be running at `http://localhost:8502` before executing
the command.
