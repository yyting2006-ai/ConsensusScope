# ConsensusScope Deployment Guide

This guide prepares ConsensusScope for a public Streamlit Community Cloud demo.
The app entry point is:

```text
app/streamlit_app.py
```

## Recommended Demo Mode

Use the app without live API calls for reviewer-facing access. The bundled ESL
literary feedback demo, curated knowledge graph, deterministic feedback records,
saved live validation records, and routing metrics are enough to demonstrate
the main ESL workflow.

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

## Local Smoke Test

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
streamlit run app/streamlit_app.py --server.port 8502
```

## Reviewer Smoke Checklist

- Page 1: overview metrics load and state the ESL review-routing purpose.
- Page 2: ESL Feedback Review retrieves the local knowledge base and produces
  adjudicated feedback without requiring API keys.
- Page 3: Knowledge Grounding & Teacher Queue shows KG evidence and
  teacher-review decisions.
- Page 4: comparison table excludes experimental learned-meta results and
  presents auxiliary QA adjudication as auxiliary.
- Page 5: risk dashboard loads and does not present old QA metrics as the main
  submission result.
- Page 6: model reliability table loads from precomputed outputs.
- Page 7: auxiliary QA case explorer opens error cases and is labeled
  auxiliary.
- Page 8: report export downloads JSON/CSV/Markdown artifacts.

## Fixed Judge Protocol

The fixed judge is an optional baseline in live mode and an offline saved result
in the bundled experiment files. By default it uses the `judge` provider
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
packaged demo uses anonymized or synthetic examples.
