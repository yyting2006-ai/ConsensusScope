# ConsensusScope Installation Guide

This package contains a no-API local demo of ConsensusScope for ESL
comparative-literature writing feedback review routing.

## 1. Requirements

- macOS, Linux or Windows
- Python 3.10 or newer
- Internet access for installing Python packages the first time

The demo can run without external LLM API keys because it includes a curated
literary knowledge graph, deterministic feedback records, saved live validation
records, and adjudication results.

## 2. Install

Open a terminal in this folder and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

## 3. Start the English Submission Demo

```bash
streamlit run app/streamlit_app.py --server.port 8502
```

Then open:

```text
http://localhost:8502
```

## 4. Start the Local Demo Again

```bash
streamlit run app/streamlit_app.py --server.port 8502
```

Then open:

```text
http://localhost:8502
```

## 5. One-Command Start

On macOS, the easiest way is to double-click:

```text
start_demo_mac.command
```

If macOS says the file cannot be opened, right-click it, choose **Open**, and
confirm. You can also run it from Terminal:

```bash
chmod +x start_demo_mac.command
./start_demo_mac.command
```

On Linux or Terminal-only macOS usage, run:

```bash
bash start_demo.sh
```

This starts the English demo on port `8502`.

On Windows, double-click:

```text
start_demo.bat
```

or run it from Command Prompt:

```bat
start_demo.bat
```

## 6. Included Materials

- Main demo app: `app/streamlit_app.py`
- ESL Feedback Review Mode for comparative-literature essay feedback
- Knowledge graph data: `data/knowledge/literary_kg_triples.csv`
- Diagnostic benchmark: `data/literary_feedback/benchmark.csv`
- No-API feedback records and routing metrics: `data/results/`
- Optional auxiliary QA reliability files, clearly separated from the main ESL
  demo claim
- Screenshots: `docs/screenshots_en/`
- EMNLP demo paper draft: `paper/consensusscope_emnlp_demo.tex`
- Casebook and release checklist: `docs/`

## 7. Safety Notes

This package intentionally excludes `.env` and private API keys. If you later
add API keys, keep them in a local `.env` file and do not upload it publicly.
For a password-protected live demo, set `CONSENSUS_SCOPE_DEMO_PASSWORD` in the
local `.env` file or in Streamlit Cloud Secrets.

Before adding real student essays, remove names, IDs, emails, school
identifiers, demographic details, and any personally identifying information.
ConsensusScope supports teacher review; it is not an automatic essay scorer or
teacher replacement.
