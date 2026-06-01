# ConsensusScope

ConsensusScope is a knowledge-grounded multi-LLM review-routing tool for ESL
comparative-literature writing feedback. It helps teachers decide which
AI-generated feedback can be safely accepted and which feedback needs human
review.

It is not an automatic essay scorer, not a teacher replacement, and not a truth
oracle.

## Purpose

AI writing feedback can be fluent but unsafe. A model may correctly fix a local
grammar error while also changing a student's literary interpretation, confusing
an author, or inventing a character relation. ConsensusScope makes that risk
visible by combining:

- multiple reviewer outputs in a unified feedback schema;
- a curated literary knowledge graph;
- transparent routing into low-risk auto-accept and teacher-review queues;
- dashboards and exports for auditability.

The packaged demo runs without external API calls. Live OpenAI-compatible API
reviewers are optional and should be configured through local environment
variables, Streamlit Secrets, or user-provided keys.

## Main Features

- ESL comparative-literature feedback review for student essay excerpts.
- Curated literary knowledge graph with 319 triples over 30 commonly taught
  literary works.
- Knowledge evidence for author, publication year, form, genre, character,
  theme, and alias relations.
- Deterministic no-API reviewers for conference/demo environments.
- Optional live reviewers through OpenAI-compatible providers.
- Unified feedback fields: span, issue type, suggestion, rationale, confidence,
  knowledge evidence, and meaning-change risk.
- Teacher Review Queue with priority, risk level, suggested action, agreement,
  and KG support.
- Report export for teacher inspection and reproducibility.
- Auxiliary QA Reliability Module for inspecting saved multi-model QA traces.
  This auxiliary module is not the main EMNLP 2026 demo claim.

## Quick Start

Install dependencies:

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

On macOS, you can also double-click:

```text
start_demo_mac.command
```

On Windows, double-click:

```text
start_demo.bat
```

## Demo Pages

- **Page 1: Home / System Overview** shows the ESL review-routing workflow and
  packaged data summary.
- **Page 2: ESL Feedback Review** runs deterministic or live multi-reviewer
  feedback on a comparative-literature essay excerpt.
- **Page 3: Knowledge Grounding & Teacher Queue** focuses on retrieved literary
  evidence, adjudicated feedback, and teacher-review decisions.
- **Page 4: Adjudication Comparison** compares majority vote, fixed judge, and
  dynamic rule-based adjudication for the auxiliary QA module and live QA mode.
- **Page 5: Risk Dashboard** reports risk distributions and review-routing
  signals.
- **Page 6: Model Reliability Dashboard** summarizes historical model behavior
  from saved traces.
- **Page 7: Auxiliary QA Case Explorer** inspects legacy/saved QA reliability
  cases without making them the main submission story.
- **Page 8: Report Export** downloads Markdown, JSON, and CSV artifacts.

## Data Description

Core ESL demo data:

- `data/knowledge/literary_kg_triples.csv`: curated literary KG.
- `data/literary_feedback/benchmark.csv`: 30 diagnostic ESL essay snippets.
- `data/results/literary_feedback_records.json`: deterministic no-API feedback
  records and adjudication decisions.
- `data/results/literary_feedback_routing_metrics.csv`: no-API routing metrics.
- `data/results/literary_feedback_live_multimodel_records.json`: saved live API
  validation records.
- `data/results/literary_feedback_live_multimodel_metrics.csv`: saved live API
  routing metrics.

Current ESL validation snapshot:

| Scope | Value |
|---|---:|
| Literary works | 30 |
| Curated KG triples | 319 |
| Benchmark essays | 30 |
| Adjudicated feedback decisions | 59 |
| Auto-accepted low-risk edits | 14 |
| Teacher-review decisions | 45 |
| High-risk decisions | 20 |
| KG-supported decisions | 23 |

Live API validation on the first 10 benchmark essays produced 40 provider
calls, 76 raw feedback items, 43 adjudicated feedback decisions, 8 auto-accepted
decisions, 35 teacher-review decisions, 14 high-risk decisions, and 41
KG-supported decisions. The saved records contain reviewer outputs and routing
metrics only; API keys are not stored.

The benchmark is intentionally small and diagnostic. It validates whether the
system separates low-risk local edits from feedback that changes literary facts,
character relations, themes, or interpretation. It is not a large classroom
study and not a state-of-the-art essay-scoring benchmark.

## API Configuration

The app supports two modes:

- **Mode A**: built-in keys loaded from local `.env` or Streamlit Secrets for
  controlled live demos.
- **Mode B**: user-provided keys for the current request in public deployments.

Do not commit real API keys, put API keys in the paper, or hard-code them in the
source code. For a password-protected live demo, set
`CONSENSUS_SCOPE_DEMO_PASSWORD` in local `.env` or Streamlit Secrets.

## Reproducibility

Check ESL paper numbers:

```bash
PYTHONPATH=. python3 scripts/check_esl_paper_numbers.py
```

Rebuild the deterministic ESL benchmark records:

```bash
PYTHONPATH=. python3 scripts/run_literary_feedback_benchmark.py
```

Run tests:

```bash
PYTHONPATH=. pytest -q
```

Run a Python syntax check:

```bash
find src scripts app tests -name '._*' -prune -o -name '*.py' -print0 | xargs -0 python3 -m py_compile
```

## Auxiliary QA Reliability Module

The repository retains saved QA traces and baseline adjudication files for
reliability inspection. They support examples of majority vote, fixed judge,
dynamic rule-based adjudication, disagreement, and offline diagnostic labels.
These labels require gold answers and are used only for offline analysis. They
are not deploy-time knowledge and are not the main claim of the ESL system demo.

The main fixed-judge baseline for this auxiliary module is implemented in
`src/decision/baselines.py` as `fixed_judge_decision`, with saved results in
`data/results/fixed_judge_results.csv`. Historical placeholders are isolated
under `legacy/` and `docs/legacy_results/`.

## Submission Materials

- EMNLP demo paper draft: `paper/consensusscope_emnlp_demo.tex`
- Demo video script: `docs/demo_video_script.md`
- Narration script Word file: `docs/ConsensusScope_EMNLP_demo_script_2min30_en.docx`
- Public release notes: `docs/public_release_notes.md`
- Release checklist: `docs/release_checklist.md`
- Ethics and limitations: `docs/ethics_limitations.md`

## Privacy And Safety

Before adding real student essays, remove names, IDs, emails, demographic
details, school identifiers, and any personally identifying information. The
packaged demo uses anonymized or synthetic examples.

ConsensusScope should support teacher judgment, not replace it. Literary facts,
interpretations, thesis revisions, and meaning-changing suggestions should
remain reviewable by a qualified instructor.

## License

This project is released under the MIT License. See `LICENSE`.
