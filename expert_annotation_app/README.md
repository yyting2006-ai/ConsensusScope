# ConsensusScope Expert Annotation App

This is an independent research annotation tool for collecting expert gold
labels on AI-generated ESL writing feedback. It is separate from the main
ConsensusScope demo and is not part of the paper UI.

## Purpose

English teachers can read anonymized ESL essays and item-level AI feedback, then
label whether the feedback is correct, preserves the student's intended meaning,
is safe to show to students, and should be accepted, edited, rejected, or marked
as uncertain.

The first version prioritizes **Blind Annotation Mode**. In blind mode, the app
hides system `risk_level`, `recommended_action`, model agreement, model name,
and ConsensusScope routing decisions.

The interface supports English and Chinese switching from the sidebar. Exported
CSV/JSON field names and label values remain in English canonical form for
analysis.

## Run

From this folder:

```bash
streamlit run app.py --server.port 8503
```

Then open:

```text
http://localhost:8503
```

For a dedicated teacher-facing website, deploy this as a separate Streamlit app
with main file path:

```text
expert_annotation_app/app.py
```

Optional password protection:

```toml
EXPERT_ANNOTATION_PASSWORD = "replace-with-a-private-password"
```

Set this value in Streamlit Secrets or a local environment variable. Do not
hard-code it in the source code.

## Pages

1. Expert Session
2. Essay Annotation
3. Feedback Annotation
4. Feedback Safety Check
5. Progress
6. Export

## Data Inputs

Sample CSV files are stored in `sample_data/`:

- `essays.csv`
- `feedback_items.csv`
- `routing_results.csv` optional, used only in Assisted Review Mode

Use only anonymized ESL writing data. Do not upload names, student IDs, email
addresses, class names, school identifiers, demographic details, or any other
personally identifying information.

## Storage

Annotations are saved locally to:

```text
annotation_data/expert_annotations.sqlite3
```

The app creates these SQLite tables:

- `expert_sessions`
- `essay_annotations`
- `feedback_decisions`
- `feedback_safety_checks`
- `annotation_logs`

Each annotation record stores `expert_id`, `batch_id`, `created_at`,
`updated_at`, and `duration_seconds`.

## Export

The Export page provides:

- `essay_annotations.csv`
- `feedback_decisions.csv`
- `feedback_safety_checks.csv`
- `annotation_logs.csv`
- `combined_annotations.json`

You can download files in the browser or write them to the local `exports/`
folder.

## Research And Privacy Boundary

This tool is only for research annotation. It is not an automatic essay scorer,
not a teacher replacement, and not a student-facing grading system.

Only anonymized student writing should be used. Do not store or upload PII.
