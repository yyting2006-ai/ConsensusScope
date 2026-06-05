# ConsensusScope Deployment Guide

This guide prepares ConsensusScope for a public Streamlit Community Cloud demo.
The app entry point is:

```text
app/streamlit_app.py
```

## Recommended Demo Mode

Use the packaged no-API mode for reviewer-facing access. The current main demo
uses synthetic ESL writing drafts, synthetic AI feedback items, AI-review stress
cases, review evidence, and deterministic routing results to demonstrate
teacher review routing.

For a live conference recording, use Mode A only through local `.env` variables
or Streamlit Cloud secrets. For public deployments, use Mode B so users provide
their own API keys for the current request.

Never put real API keys in the paper, README, source code, Git history, or demo
video.

For a password-protected live demo, set `CONSENSUS_SCOPE_DEMO_PASSWORD` in
Streamlit Secrets together with the Mode A API keys. The password gate is only a
usage guard; it is not a substitute for keeping API keys out of the repository.

## Streamlit Community Cloud

1. Push this clean project to a GitHub repository.
2. Create a new Streamlit app from that repository.
3. Set the main file path to `app/streamlit_app.py`.
4. Keep Python dependencies in `requirements.txt`.
5. Optional: paste the contents of `.streamlit/secrets.toml.example` into the
   Streamlit Secrets editor and fill in only the keys needed for Mode A.
6. For a private live demo, also set `CONSENSUS_SCOPE_DEMO_PASSWORD` in
   Streamlit Secrets. Leave it blank for an open no-API reviewer demo.
7. Deploy and test the pages listed below.

## Storage Boundary

This public demo package does not use an external database. The main demo keeps
teacher-queue decisions in the current browser session. The expert annotation
app writes annotations to a local SQLite file inside the Streamlit app container
and provides CSV/JSON export buttons.

For formal data collection on Streamlit Community Cloud, export the annotation
files after each teacher session and back them up outside Streamlit Cloud. Local
container storage may be reset by the hosting platform and should not be treated
as the only copy of research data.

## Local Smoke Test

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
streamlit run app/streamlit_app.py --server.port 8502
```

## Reviewer Smoke Checklist

- The README states the ESL writing feedback review-routing purpose.
- `ui_prototype/index.html` opens and shows the 7-page product workflow.
- The Streamlit app starts from `app/streamlit_app.py`.
- Page 2 Single Essay Review can generate and route feedback without API keys.
- Page 3 Batch Review can process the packaged synthetic CSV.
- Page 4 AI Feedback Comparison shows reviewer/risk comparison rows.
- Page 5 Teacher Queue shows review-routed items and local teacher actions.
- Page 6 Effectiveness Evaluation reports synthetic expectation-label and
  AI-review stress-test metrics.
- Page 7 Reports exports routed feedback and Markdown report artifacts.
- Mode A and Mode B API configuration text is visible and does not expose keys.
- The auxiliary QA and earlier feedback modules are clearly separated from the
  current main demo claim.

## Fixed Judge Protocol

The fixed judge is an optional baseline in live mode and an offline saved result
in bundled auxiliary QA files. By default it uses the `judge` provider
configuration:

```text
JUDGE_MODEL=deepseek-chat
JUDGE_BASE_URL=https://api.deepseek.com
```

The fixed judge prompt receives the sample id, dataset, task type, question,
options, and model outputs. It does not receive the gold answer or gold label.
It sees the other models' answers, rationales/reasons, confidence values,
evidence fields, and parser metadata. Saved offline results are reproducible as
artifacts, while exact reruns can vary with provider-side model/API changes.

## Privacy

Before adding real student essays, remove names, IDs, emails, demographic
details, school identifiers, and any personally identifying information. The
packaged ESL writing demo uses synthetic examples.
