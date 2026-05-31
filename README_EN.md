# ConsensusScope

ConsensusScope is a risk-aware observability and adjudication prototype for
multi-LLM collaborative decision-making. It does not train a new model. Instead,
it records independent model answers, compares majority voting, fixed judging
and rule-based dynamic adjudication, and surfaces deploy-time risk signals such
as agreement rate, answer diversity, confidence distribution, evidence
availability, minority warnings and parse errors.

## Why This Matters

Many multi-agent or multi-model systems treat agreement as a proxy for
trustworthiness. ConsensusScope is built around a different assumption:

> Multi-model agreement is useful evidence, but it is not proof of correctness.

The system therefore focuses on inspecting the decision process, not only the
final answer.

## Main Features

- Live Question Mode for new user-entered questions.
- Three live task types: open factual QA, claim true/false, and A/B/C/D multiple choice.
- In-app OpenAI-compatible API configuration and model selection.
- Unified sample format for TruthfulQA, FEVER and CommonsenseQA.
- OpenAI-compatible model clients for multiple LLM providers.
- Structured model traces containing answer, rationale, confidence and evidence.
- Majority vote, fixed judge and rule-based dynamic adjudication baselines.
- Deploy-time risk signals: agreement rate, answer diversity, confidence
  distribution, evidence availability, minority warnings and parse errors.
- Offline diagnostic labels for saved benchmark samples: true consensus, false
  consensus, minority correct and confidence mismatch. These labels use gold
  answers and are not claimed to be available during live deployment.
- Aggregate metrics and visual reports.
- Streamlit demo for sample-level auditing and paper/demo preparation.

## Quick Start

Installation:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

Run the demo:

```bash
streamlit run app/streamlit_app.py --server.port 8502
```

Then open:

```text
http://localhost:8502
```

The same command is used for the English submission-oriented interface:

```bash
streamlit run app/streamlit_app.py --server.port 8502
```

Then open:

```text
http://localhost:8502
```

On macOS, double-click:

```text
start_demo_mac.command
```

On Windows, double-click:

```text
start_demo.bat
```

The repository already contains a no-API demonstration package with processed
samples, saved model outputs, adjudication results, risk labels and figures.
You can inspect the demo without calling external LLM APIs.

Expected local output:

```text
Demo available at http://localhost:8502
```

## Demo Pages

- **Page 1: Home / System Overview**: inspect corpus, trace and adjudicator
  counts.
- **Page 2: Live Question Mode**: enter a new question, configure APIs, run
  multiple LLMs, inspect dynamic adjudication, and export a Markdown/JSON report.
- **Page 3: Sample Audit Mode**: inspect model answers, rationales, confidence,
  evidence, majority voting, fixed judging, dynamic adjudication and offline
  diagnostic labels.
- **Page 4: Adjudication Comparison**: compare majority vote, fixed judge and
  rule-based dynamic adjudication.
- **Page 5: Risk Dashboard**: view offline diagnostic label distributions and
  risk-level effectiveness.
- **Page 6: Model Reliability Dashboard**: inspect historical model reliability
  summaries from the saved traces.
- **Page 7: Case Explorer**: inspect error and risk cases.
- **Page 8: Report Export**: download summary, metric and risk-label artifacts.

## Current Evaluation Snapshot

The current local evaluation uses 1000 adjudicated samples and 4000 structured
model-output rows. Because TruthfulQA, FEVER and CommonsenseQA have different
answer spaces, the paper reports dataset-level accuracy, risk stratification
quality and review-routing utility instead of a single mixed macro-F1 score.

| Method | TruthfulQA | FEVER | CommonsenseQA |
|---|---:|---:|---:|
| Majority vote | 0.075 | 0.622 | 0.760 |
| Rule-based dynamic judge | 0.075 | 0.661 | 0.760 |
| Fixed judge | 0.087 | 0.709 | 0.796 |

| Dynamic risk level | Accuracy | Error rate |
|---|---:|---:|
| Low | 0.918 | 0.082 |
| Medium | 0.552 | 0.448 |
| High | 0.048 | 0.952 |

| Routing policy | Auto share | Auto acc. | Review share | Errors reviewed |
|---|---:|---:|---:|---:|
| Accept low; review med/high | 0.17 | 0.918 | 0.83 | 0.972 |
| Accept low/med; review high | 0.77 | 0.632 | 0.23 | 0.436 |
| Review all | 0.00 | -- | 1.00 | 1.000 |

`Errors reviewed` is the share of observed final-answer errors sent to the
human-review queue by the policy. The main evaluation claim is review-routing
utility, not state-of-the-art final-answer accuracy.

## Fixed Judge Protocol

The fixed judge uses the repository's `judge` provider:

- Default model: `deepseek-chat`.
- Default endpoint: `https://api.deepseek.com`.
- Override variables: `JUDGE_MODEL`, `JUDGE_BASE_URL`, and `JUDGE_API_KEY`.
- Temperature: `0.0`.
- Output schema: `final_answer`, `decision_reason`, `risk_level`,
  `confidence`.

The fixed-judge prompt receives the sample id, dataset, task type, question,
options and saved model-output records. These records include each model's
answer, rationale (`reason`), confidence and evidence, together with parser
metadata. The judge does **not** receive the gold answer or gold label. In the
saved pilot run, one fixed-judge call was made for each of the 1000 evaluated
samples. The saved CSV is shipped as the reproducible artifact; exact reruns may
vary if the external provider changes the model or API behavior.

The EMNLP 2026 demo pipeline uses `src.decision.baselines.fixed_judge_decision`
and `data/results/fixed_judge_results.csv` as the fixed-judge baseline. Legacy
placeholder files are kept only under `legacy/` or `docs/legacy_results/` for
historical inspection and are not part of the demo pipeline.

## Reproducibility

Run tests:

```bash
PYTHONPATH=. pytest -q
```

For a clean environment, install dependencies first:

```bash
python3 -m venv .venv-clean
source .venv-clean/bin/activate
pip install -U pip
pip install -r requirements.txt
PYTHONPATH=. pytest -q
```

Expected test output:

```text
37 passed
```

Run a syntax check that ignores macOS AppleDouble files:

```bash
find src scripts app tests -name '._*' -prune -o -name '*.py' -print0 | xargs -0 python3 -m py_compile
```

## Submission Materials

- Literature and publication strategy: `docs/literature_publication_strategy.md`
- EMNLP demo brief: `docs/emnlp_demo_brief.md`
- Casebook: `docs/casebook.md`
- Video script: `docs/demo_video_script.md`
- English screenshots: `docs/screenshots_en/`
- Ethics and limitations: `docs/ethics_limitations.md`
- Public release notes: `docs/public_release_notes.md`
- Release checklist: `docs/release_checklist.md`
- Draft EMNLP demo paper: `paper/consensusscope_emnlp_demo.tex`

## License

This project is released under the MIT License. See `LICENSE`.

## Ethics and Limitations

ConsensusScope is an audit and risk-warning tool. It should not be used as a
fully automated truth oracle, grader or high-stakes decision maker. Model
outputs may contain factual errors, biased rationales or misleading confidence
statements. Educational or user-generated data should be anonymized before use.
