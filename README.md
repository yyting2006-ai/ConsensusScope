# ConsensusScope

**ConsensusScope: An Interactive Review-Routing Tool for Safe AI Feedback on ESL Writing**

ConsensusScope is a teacher-in-the-loop review-routing tool for AI-generated
ESL writing feedback. It helps teachers decide which feedback can be safely
shown to students and which feedback should be reviewed, edited, or rejected
before release.

It is not an automatic essay scorer, not a teacher replacement, and not a truth
oracle.

## Main Direction

AI writing feedback can be fluent but unsafe. A feedback model may fix a local
grammar error, but it may also change a student's intended meaning, rewrite the
thesis, add unsupported content, or overcorrect a reasonable draft. ConsensusScope
makes those risks visible through:

- multi-model feedback candidates normalized into one feedback schema;
- deploy-time routing signals such as agreement, issue type, meaning-change
  warnings, unsupported-claim warnings, harsh-tone warnings, evidence status,
  and parse errors;
- transparent low/medium/high risk routing;
- item-level AI review scores, confidence estimates, evidence signals, review
  priorities, and short explanations for why an item is blocked or released;
- a teacher queue for feedback that needs human judgment;
- writing rubric and report pages for inspection and auditability.

The packaged demo runs without external API calls. Live OpenAI-compatible API
reviewers are optional and should be configured through local environment
variables, Streamlit Secrets, or user-provided keys.

## Current Practical Workflow

The Streamlit app now contains operational teacher-facing windows:

- **Language switch**: the main demo can switch between English and Chinese
  from the sidebar without changing exported CSV schemas.
- **Single Essay Review**: paste one ESL essay, generate no-API AI-style
  feedback candidates, route each feedback item, and export a report.
- **Batch Review**: upload a CSV or use packaged demo essays, process multiple
  drafts, and export routed feedback.
- **AI Feedback Comparison**: compare feedback candidates by target span,
  reviewer, issue type, risk level, and consensus state.
- **Teacher Queue**: inspect medium/high-risk items and record local teacher
  actions such as accept, edit, reject, or needs more evidence.
- **Effectiveness Evaluation**: run synthetic expectation-label and AI-review
  stress-test checks for routing behavior.
- **Reports**: export routed feedback tables and teacher-readable reports.

The packaged practical workflow runs without external API calls. It is suitable
for demo and interface validation, but it is not yet validated as a classroom
deployment.

The designer-facing static prototype remains available as a visual reference:

```text
ui_prototype/index.html
```

Streamlit app pages:

1. Review Workspace
2. Single Essay Review
3. Batch Review
4. AI Feedback Comparison
5. Teacher Queue
6. Effectiveness Evaluation
7. Reports
8. Settings / Diagnostics
9. Design Reference

Operational teacher workflow:

```text
Single Essay Review -> Batch Review -> AI Feedback Comparison -> Teacher Queue -> Effectiveness Evaluation -> Reports
```

## Quick Start

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

Run the Streamlit technical demo:

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

## ESL Writing Data And Interface

New ESL writing review-routing assets:

- `profiles/esl_writing.yaml`: issue types, risk labels, teacher safety labels,
  and recommended actions for ESL writing feedback.
- `data/esl_writing_demo/essays.csv`: three anonymized synthetic ESL writing
  drafts.
- `data/esl_writing_demo/feedback_items.csv`: synthetic AI feedback candidates
  with unified fields.
- `data/esl_writing_demo/review_evidence.csv`: rubric and safety-rule evidence
  used by the router.
- `data/esl_writing_demo/routing_results.csv`: deterministic routing output for
  the packaged demo.
- `data/esl_writing_demo/expected_routing_labels.csv`: synthetic expectation
  labels for implementation-level routing evaluation.
- `data/esl_writing_demo/ai_review_stress_cases.csv`: synthetic stress cases
  for dangerous AI feedback, including thesis reversal, whole-essay rewriting,
  unsupported factual claims, harsh student-facing language, low agreement, and
  parse failures.
- `src/esl_writing_feedback.py`: main rule-based routing interface.
- `src/prompts/esl_feedback_prompt.py`: structured feedback-generation prompt
  template.
- `scripts/evaluate_esl_routing_demo.py`: synthetic routing evaluation script.
- `scripts/analyze_esl_feedback_experiment.py`: offline analysis script for
  future teacher annotations.

The current ESL writing demo contains 3 synthetic essays, 15 packaged synthetic
feedback items, and 16 AI-review stress cases. These are demonstration and
implementation-test records, not classroom evaluation results.

## Routing Output Schema

The ESL routing layer returns:

- `feedback_item_id`
- `risk_level`: `low`, `medium`, or `high`
- `recommended_action`: `auto_accept`, `teacher_review`, `reject`, or
  `needs_more_evidence`
- `risk_reasons`: semicolon-separated deploy-time risk reasons
- `meaning_preservation_predicted`: `preserves_meaning`, `changes_meaning`, or
  `unclear`
- `status`: `auto_accepted` or `needs_teacher_review`
- `risk_score`: deploy-time risk score in `[0, 1]`
- `review_confidence`: confidence in the route, not in the correctness of the
  feedback itself
- `evidence_signal`: `supported`, `missing`, `conflict`, or `none`
- `review_priority`: `low`, `normal`, `high`, or `urgent`
- `review_explanation`: short human-readable explanation of the route

Deploy-time signals are separated from offline diagnostic labels. Teacher
annotations, if collected later, should be analyzed as offline evaluation data,
not as information available to the live router.

## Current Effectiveness Evidence

The current evaluation is an implementation-level synthetic sanity check:

```bash
PYTHONPATH=. python3 scripts/evaluate_esl_routing_demo.py
```

On the packaged 15 feedback-item synthetic expectation set and the 16-item AI
review stress-test set, the router currently matches the expected action and
risk labels exactly:

| Metric | Value |
|---|---:|
| Items | 31 |
| Action accuracy | 1.000 |
| Risk accuracy | 1.000 |
| High-risk recall | 1.000 |
| Review recall | 1.000 |
| Auto-accept precision | 1.000 |

This supports the claim that the demo routing logic behaves as designed on the
synthetic demo and stress-test sets. It does **not** prove classroom
effectiveness, teacher acceptability, student learning gains, or real LLM
feedback quality. Those claims require instructor annotations and real
anonymized classroom data.

## API Configuration

The app supports two modes:

- **Mode A**: built-in keys loaded from local `.env` or Streamlit Secrets for
  controlled live demos.
- **Mode B**: user-provided keys for the current request in public deployments.

Do not commit real API keys, put API keys in the paper, or hard-code them in the
source code. For a password-protected live demo, set
`CONSENSUS_SCOPE_DEMO_PASSWORD` in local `.env` or Streamlit Secrets.

## Reproducibility

Run tests:

```bash
PYTHONPATH=. pytest -q
```

Run a Python syntax check:

```bash
find src scripts app tests -name '._*' -prune -o -name '*.py' -print0 | xargs -0 python3 -m py_compile
```

Run synthetic ESL routing evaluation:

```bash
PYTHONPATH=. python3 scripts/evaluate_esl_routing_demo.py
```

Analyze future teacher annotations:

```bash
PYTHONPATH=. python3 scripts/analyze_esl_feedback_experiment.py \
  --annotations-dir path/to/teacher_annotations \
  --routing data/esl_writing_demo/routing_results.csv
```

Expected annotation file name:

```text
feedback_decisions.csv
```

Expected annotation columns include `feedback_item_id`, `teacher_safety_label`,
`feedback_correctness`, `meaning_preservation`, and `teacher_final_action`.

## Legacy / Auxiliary Modules

Earlier domain-specific feedback modules and multi-model QA reliability files
are retained for historical inspection and auxiliary experiments. They are not
the current main EMNLP 2026 demo claim.

Legacy examples include:

- `src/literary_feedback.py`
- `legacy/literary_feedback_scripts/run_literary_feedback_benchmark.py`
- `data/literary_feedback/`
- `data/knowledge/literary_kg_triples.csv`
- saved auxiliary QA traces under `data/results/`

The main fixed-judge baseline for the auxiliary QA module is implemented in
`src/decision/baselines.py` as `fixed_judge_decision`, with saved results in
`data/results/fixed_judge_results.csv`. Historical placeholders are isolated
under `legacy/`.

## Submission Materials

- EMNLP demo paper draft: `paper/consensusscope_emnlp_demo.tex`
- Demo video script: `docs/demo_video_script.md`
- Narration script Word file:
  `docs/ConsensusScope_EMNLP_demo_script_2min30_en.docx`
- Public release notes: `docs/public_release_notes.md`
- Release checklist: `docs/release_checklist.md`
- Ethics and limitations: `docs/ethics_limitations.md`
- UI designer reference: `ui_prototype/README.md` and `ui_prototype/index.html`

## Privacy And Safety

Before adding real student essays, remove names, IDs, emails, demographic
details, school identifiers, and any personally identifying information. The
packaged ESL writing demo uses synthetic examples.

ConsensusScope should support teacher judgment. Meaning-changing suggestions,
unsupported claims, thesis rewrites, overcorrections, vague advice, and harsh
feedback should remain reviewable by a qualified instructor.

## License

This project is released under the MIT License. See `LICENSE`.
