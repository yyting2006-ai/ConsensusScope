# ConsensusScope

ConsensusScope is being refocused as an applied NLP demo for ESL literary
writing feedback. It uses the original multi-LLM adjudication layer to inspect
and route suggested corrections for comparative literature essays: low-risk
grammar edits can be auto-accepted, while literary facts, interpretation changes
and thesis-level revisions are checked against a small expert knowledge base and
routed to teacher review.

## Why This Matters

Many multi-agent or multi-model systems treat agreement as a proxy for
trustworthiness. ConsensusScope is built around a different assumption:

> Multi-model agreement is useful evidence, but it is not proof of correctness.

The system therefore focuses on inspecting the feedback process, not only the
final revised text.

## Main Features

- ESL Comparative Literature Essay Feedback Mode with a no-API demo path.
- Curated literary knowledge graph with 319 triples over 30 commonly taught
  literary works, covering authorship, publication date, form, genre, central
  characters, themes and title aliases.
- Knowledge-grounded routing of grammar, style, literary fact and argument
  suggestions.
- Teacher-facing review queue with priority, risk level, suggested action and
  knowledge evidence.
- Auto-accepted preview that applies only low-risk local language edits while
  keeping factual and interpretive revisions for teacher review.
- Live Question Mode for backward-compatible user-entered QA comparisons.
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
- Streamlit demo for ESL feedback auditing, sample-level adjudication and
  paper/demo preparation.

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

For a password-protected live demo, keep API keys in local `.env` or Streamlit
Secrets and set `CONSENSUS_SCOPE_DEMO_PASSWORD`. Do not commit real API keys or
password values to the repository.

Expected local output:

```text
Demo available at http://localhost:8502
```

## Demo Pages

- **Page 1: Home / System Overview**: inspect corpus, trace and adjudicator
  counts.
- **Page 2: ESL Literary Feedback Mode**: enter a comparative literature essay,
  retrieve expert literary knowledge, adjudicate multi-reviewer suggestions,
  and export a feedback report. The original live QA comparison remains
  available as a secondary mode.
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

For the ESL literary-feedback pivot, the repository also includes a small
feedback-routing benchmark in `data/literary_feedback/benchmark.csv` and a
runner:

```bash
PYTHONPATH=. python3 scripts/run_literary_feedback_benchmark.py
```

Rebuild the local literary knowledge graph:

```bash
PYTHONPATH=. python3 scripts/build_literary_kg.py
```

With local API keys, the same script can call live reviewers:

```bash
PYTHONPATH=. python3 scripts/run_literary_feedback_benchmark.py --live --providers deepseek,qwen,glm,kimi
```

The checked-in live sample records contain reviewer outputs and routing metrics
only; API keys are not stored.

Current ESL literary-feedback snapshot:

| Scope | Value |
|---|---:|
| Benchmark essays | 30 |
| Curated KG triples | 319 |
| Adjudicated feedback decisions | 59 |
| Auto-accepted low-risk edits | 14 |
| Teacher-review decisions | 45 |
| KG-supported decisions | 23 |

The ESL demo claim is not that the system fully grades an essay. It shows a
deployable review-routing pattern: local grammar edits can be accepted, while
factual and interpretation-changing suggestions remain teacher-facing.

Live API validation has also been run on the first 10 benchmark essays with
DeepSeek, Qwen, GLM and Kimi. All 40 provider calls returned without request or
parse errors; the resulting 43 live feedback decisions routed 35 items to
teacher review and marked 41 decisions as KG-supported.

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
