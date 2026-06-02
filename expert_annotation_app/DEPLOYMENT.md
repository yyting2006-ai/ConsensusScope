# Expert Annotation Website Deployment

This app should be deployed as a dedicated expert annotation website, separate
from the main ConsensusScope demo.

## Recommended Website Setup

Use a separate Streamlit app:

```text
Main file path: expert_annotation_app/app.py
Port for local test: 8503
```

Local test:

```bash
cd expert_annotation_app
streamlit run app.py --server.port 8503
```

Public or private web deployment:

1. Push the repository to GitHub.
2. Create a separate Streamlit Community Cloud app.
3. Set the main file path to `expert_annotation_app/app.py`.
4. Set a site password in Streamlit Secrets:

```toml
EXPERT_ANNOTATION_PASSWORD = "replace-with-a-private-password"
```

5. Share the deployed URL and password only with participating teachers.

Do not hard-code the password in `app.py`, README files, the paper, screenshots,
or video recordings.

## Suggested Teacher Workflow

1. Teacher opens the expert annotation URL.
2. Teacher enters the site password.
3. Teacher creates or selects:
   - `expert_id`, for example `TCH-001`
   - `batch_id`, for example `ESL-BATCH-001`
4. Teacher uses Blind Annotation Mode.
5. Teacher completes:
   - Essay Annotation
   - Feedback Annotation
   - Feedback Safety Check
6. Researcher checks Progress.
7. Researcher exports CSV/JSON files from Export.

## Important Storage Boundary

This first version uses SQLite because it is lightweight and easy to run
locally. For a short controlled annotation round, this is acceptable if the
researcher exports data frequently.

For long-term multi-teacher data collection, a managed database is safer than a
local SQLite file inside a cloud app. Recommended next step:

- keep the same Streamlit interface;
- replace SQLite with PostgreSQL/Supabase or another managed database;
- keep Blind Annotation Mode unchanged;
- keep exports in the same CSV/JSON schema.

## Privacy Rules

Only upload anonymized ESL writing data. Do not upload:

- names
- student IDs
- email addresses
- class names
- school identifiers
- demographic details
- any other personally identifying information

This website is only for research annotation. It is not an automatic essay
scorer, not a teacher replacement, and not a student-facing grading system.
