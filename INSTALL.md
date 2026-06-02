# ConsensusScope Installation Guide

This package contains a no-API local demo of ConsensusScope for ESL writing
feedback review routing.

## 1. Requirements

- macOS, Linux, or Windows
- Python 3.10 or newer
- Internet access for installing Python packages the first time

The packaged ESL writing demo can run without external LLM API keys because it
includes synthetic essays, synthetic feedback items, review evidence, and saved
routing output.

## 2. Install

Open a terminal in this folder and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

## 3. Start The Streamlit Demo

```bash
streamlit run app/streamlit_app.py --server.port 8502
```

Then open:

```text
http://localhost:8502
```

## 4. Open The Product UI Prototype

Open this file directly in a browser:

```text
ui_prototype/index.html
```

Or run a static server:

```bash
cd ui_prototype
python3 -m http.server 8080
```

Then open:

```text
http://localhost:8080
```

## 5. One-Command Start

On macOS, double-click:

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

On Windows, double-click:

```text
start_demo.bat
```

or run it from Command Prompt:

```bat
start_demo.bat
```

## 6. Included Main Materials

- Main Streamlit app: `app/streamlit_app.py`
- Product UI prototype: `ui_prototype/index.html`
- ESL writing profile: `profiles/esl_writing.yaml`
- Synthetic ESL writing demo data: `data/esl_writing_demo/`
- Review-routing interface: `src/esl_writing_feedback.py`
- Prompt template: `src/prompts/esl_feedback_prompt.py`
- Offline analysis script: `scripts/analyze_esl_feedback_experiment.py`
- EMNLP demo paper draft: `paper/consensusscope_emnlp_demo.tex`
- Release checklist and ethics notes: `docs/`

## 7. Safety Notes

This package intentionally excludes private API keys. If you later add API keys,
keep them in a local `.env` file or Streamlit Secrets and do not upload them
publicly. For a password-protected live demo, set
`CONSENSUS_SCOPE_DEMO_PASSWORD` in local `.env` or Streamlit Cloud Secrets.

Before adding real student essays, remove names, IDs, emails, school
identifiers, demographic details, and any personally identifying information.
ConsensusScope supports teacher review; it is not an automatic essay scorer or
teacher replacement.

