# Screenshot Plan

The English screenshots in `docs/screenshots_en/` should follow the ESL
comparative-literature feedback storyline.

Recommended figures:

1. `home_system_overview.png`: system purpose and ESL review-routing workflow.
2. `esl_feedback_review.png`: essay input, no-API reviewer mode, and adjudicated
   feedback.
3. `knowledge_teacher_queue.png`: KG evidence and teacher-review queue.
4. `risk_dashboard.png`: ESL routing risk summary plus auxiliary QA diagnostics.
5. `report_export.png`: downloadable feedback report and reproducibility files.

Generation command:

```bash
node scripts/capture_screenshots_en.mjs
```

The Streamlit app must be running at `http://localhost:8502` before executing
the command.
