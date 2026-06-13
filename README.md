# ConsensusScope

**ConsensusScope: Feedback Safety Graphs for Teacher-in-the-Loop Review Routing of AI Feedback on ESL Writing**

ConsensusScope is a teacher-in-the-loop review-routing tool for AI-generated
ESL writing feedback. Its core mechanism is an item-level **Feedback Safety
Graph** that links a student's target span, an AI suggestion, evidence status,
active safety dimensions, and the final route. It helps teachers decide which
feedback can be safely shown to students and which feedback should be reviewed,
edited, or rejected before release.

It is not an automatic essay scorer, not a teacher replacement, and not a truth
oracle.

## Main Direction

AI writing feedback can be fluent but unsafe. A feedback model may fix a local
grammar error, but it may also change a student's intended meaning, rewrite the
thesis, add unsupported content, or overcorrect a reasonable draft. ConsensusScope
makes those risks visible through a Feedback Safety Graph rather than a single
opaque confidence score:

- multi-model feedback candidates normalized into one feedback schema;
- deploy-time graph nodes for target span, surrounding context, AI suggestion,
  predicted issue type, evidence signal, safety dimensions, and route;
- graph-level safety dimensions for local edits, meaning preservation, content
  grounding, pedagogical tone, feedback specificity, and model agreement;
- transparent low/medium/high risk routing;
- item-level AI review scores, confidence estimates, evidence signals, review
  priorities, graph paths, and short explanations for why an item is blocked or
  released;
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
  reviewer, issue type, risk level, Feedback Safety Graph dimensions, and
  consensus state.
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

## Submission Assets

For demo-track review, the repository includes:

- `paper/consensusscope_emnlp_demo.tex`: EMNLP-style demo paper source.
- `docs/screenshots_en/`: main screenshots for the system paper and video.
- `docs/demo_video_script.md`: 2.5-minute English recording script.
- `docs/demo_stability_checklist.md`: public URL, local fallback, and recording
  checks.
- `docs/teacher_likert_pilot_summary.md`: compact two-teacher diagnostic pilot
  summary.
- `expert_annotation_app/`: separate teacher annotation website for collecting
  blind 1-5 Likert ratings.

## Feedback Safety Graph

The main methodological unit is not an essay-level score. It is a feedback-item
graph:

```text
target span -> AI suggestion -> active safety dimension -> routing decision
```

Each graph is built from deploy-time fields only. It does **not** use public
corpus gold corrections, teacher labels, or classroom outcomes when routing a
new item. The exported route contains:

- `safety_graph_active_dimensions`: active graph dimensions, such as
  `meaning_preservation`, `content_grounding`, or `local_edit`.
- `safety_graph_active_signals`: concrete risk reasons that activated those
  dimensions.
- `safety_graph_path`: compact teacher-readable path, for example
  `target_span -> ai_suggestion -> meaning_preservation -> teacher_review`.
- `safety_graph_summary`: one-sentence explanation for the route.
- `safety_graph_nodes` and `safety_graph_edges`: JSON audit records for
  reproducibility and debugging.

This graph layer is the main innovation claim: ConsensusScope does not merely
show a dashboard; it turns AI writing feedback into auditable safety objects
that can be routed before reaching students.

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
- `src/esl_writing_feedback.py`: Feedback Safety Graph construction and main
  rule-based routing interface.
- `src/prompts/esl_feedback_prompt.py`: structured feedback-generation prompt
  template.
- `scripts/evaluate_esl_routing_demo.py`: synthetic routing evaluation script.
- `scripts/analyze_teacher_likert_pilot.py`: offline analysis script for a
  two-teacher 1-5 Likert pilot on AI feedback safety and usefulness.
- `scripts/run_public_gec_benchmark.py`: offline public learner-corpus
  benchmark runner for JFLEG-style parallel files, `.m2` GEC files, or a simple
  source/reference CSV.
- `src/public_gec_benchmark.py`: conversion and evaluation utilities that turn
  public learner-correction pairs into feedback-level gold labels.

The current ESL writing demo contains 3 synthetic essays, 15 packaged synthetic
feedback items, and 16 AI-review stress cases. These are demonstration and
implementation-test records, not classroom evaluation results.

## Two-Teacher Diagnostic Pilot

We also ran a small blind diagnostic pilot with two English teachers on the
expert annotation website. Each teacher rated 30 AI feedback items on six 1-5
dimensions: correctness, meaning preservation, student readiness, usefulness,
clarity, and direct-release suitability. These ratings are offline diagnostics;
they are not used by the deploy-time router.

The pilot exposed three borderline auto-release patterns: teacher-dependent
advice such as "if the teacher wants", semantic drift in wording edits such as
changing "remember" to "learned", and wrong local grammar corrections after
modal verbs such as changing "can make" to "makes". The router now includes
deploy-time signals for these cases.

On the 30-item pilot set, the final teacher-aligned routing diagnostics are:

| Metric | Value |
|---|---:|
| Feedback items | 30 |
| Rating rows | 60 |
| Auto share | 0.233 |
| Review share | 0.767 |
| Review-needed recall | 1.000 |
| Unsafe reviewed recall | 1.000 |
| Auto precision vs. teacher-safe items | 0.857 |
| Within-one-point teacher agreement | 0.694 |

This is a preliminary pilot, not a classroom effectiveness study. It is useful
for stress-testing routing behavior and identifying rule refinements before a
larger teacher study.

See `docs/teacher_likert_pilot_summary.md` for the compact reporting summary.

## Public Learner-Corpus Empirical Benchmark

If private expert annotations are unavailable, ConsensusScope can still be
evaluated against public annotated learner-writing correction corpora. This is
an offline empirical benchmark, not a classroom deployment claim.

Supported inputs:

- **JFLEG**: download the public JFLEG repository, then pass its root directory.
- **BEA-2019 W&I+LOCNESS / FCE / NUCLE / CoNLL-style GEC files**: pass `.m2`
  files directly.
- **Generic CSV**: provide columns such as `dataset`, `sample_id`, `source`, and
  `reference`.

Run the packaged smoke test:

```bash
PYTHONPATH=. python3 scripts/run_public_gec_benchmark.py
```

Run on a local JFLEG checkout:

```bash
PYTHONPATH=. python3 scripts/run_public_gec_benchmark.py \
  --jfleg-dir path/to/jfleg \
  --max-samples 200 \
  --out-dir reports/public_gec_benchmark_jfleg
```

Or let the script download JFLEG from GitHub for a local experiment:

```bash
PYTHONPATH=. python3 scripts/run_public_gec_benchmark.py \
  --download-jfleg \
  --max-samples 200 \
  --out-dir reports/public_gec_benchmark_jfleg
```

Run on an `.m2` file:

```bash
PYTHONPATH=. python3 scripts/run_public_gec_benchmark.py \
  --m2-file path/to/wi_locness.m2 \
  --m2-dataset-name WI_LOCNESS \
  --out-dir reports/public_gec_benchmark_wi
```

The benchmark writes:

- `public_gec_gold_feedback.csv`
- `public_gec_feedback_candidates.csv`
- `public_gec_review_evidence.csv`
- `public_gec_gold_labels.csv`
- `public_gec_routing_results.csv`
- `public_gec_item_analysis.csv`
- `public_gec_metrics.csv`
- `public_gec_policy_metrics.csv`
- `public_gec_report.md`

Metric definitions:

- `auto_share`: fraction of feedback candidates released without teacher review.
- `auto_acc`: correctness rate among auto-released feedback candidates.
- `review_share`: fraction of feedback candidates routed to teacher review.
- `errors_reviewed`: fraction of observed incorrect feedback candidates sent to
  review.

Public GEC corpora provide correction gold labels, not full teacher
acceptability judgments. The benchmark therefore supports claims about
feedback-level correction/routing behavior, not claims about student learning,
teacher satisfaction, or automatic essay scoring.

Completed public-corpus runs are summarized in
`reports/public_gec_summary_20260608.csv` and
`reports/public_gec_summary_20260608.md`. These files contain aggregate metrics
only, not redistributed learner-corpus text.

| Dataset run | Records | Gold edits | Candidates | Auto share | Review share | Errors reviewed |
|---|---:|---:|---:|---:|---:|---:|
| JFLEG full | 1,501 | 3,938 | 11,587 | 0.320 | 0.680 | 1.000 |
| CoNLL-2014 A0 | 1,312 | 2,102 | 6,204 | 0.322 | 0.678 | 1.000 |
| CoNLL-2014 A1 | 1,312 | 3,008 | 8,922 | 0.326 | 0.674 | 1.000 |
| FCE train | 28,350 | 38,858 | 115,757 | 0.329 | 0.671 | 1.000 |
| FCE dev | 2,191 | 3,079 | 9,173 | 0.328 | 0.672 | 1.000 |
| FCE test | 2,695 | 4,032 | 12,004 | 0.328 | 0.672 | 1.000 |
| W&I+LOCNESS train | 34,308 | 55,704 | 166,201 | 0.329 | 0.671 | 1.000 |
| W&I+LOCNESS dev | 4,384 | 6,680 | 19,934 | 0.329 | 0.671 | 1.000 |

The high auto-accuracy in this table should be read narrowly: correct feedback
candidates are derived from public gold corrections and compared with
constructed risk distractors. The result validates review-routing behavior
under controlled conditions; it does not show that real LLM feedback is always
correct.

Not run:

- Lang-8 requires an official request form.
- NUCLE training data requires the official NUS license process.
- W&I+LOCNESS test contains original test sentences but no released gold M2
  labels in the downloadable package, so it is not usable for this offline gold
  routing evaluation.

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
- `safety_graph_active_dimensions`: activated graph dimensions
- `safety_graph_active_signals`: concrete safety signals behind the route
- `safety_graph_path`: compact audit path from feedback item to route
- `safety_graph_summary`: teacher-readable graph explanation
- `safety_graph_nodes` / `safety_graph_edges`: JSON graph records for audit

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
feedback quality. The public learner-corpus benchmark extends the evidence to
offline correction-gold routing evaluation, but classroom claims still require
instructor annotations and real anonymized classroom data.

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

Run the public learner-corpus benchmark smoke test:

```bash
PYTHONPATH=. python3 scripts/run_public_gec_benchmark.py
```

Analyze future two-teacher Likert ratings:

```bash
PYTHONPATH=. python3 scripts/analyze_teacher_likert_pilot.py \
  --ratings path/to/exported_teacher_ratings \
  --routing expert_annotation_app/sample_data/routing_results.csv
```

Expected annotation file name:

```text
likert_feedback_ratings.csv
```

The current teacher pilot supports at most two teachers. Expected rating columns
include `expert_id`, `batch_id`, `feedback_item_id`, `essay_id`,
`correctness_score`, `meaning_preservation_score`, `student_readiness_score`,
`usefulness_score`, `clarity_score`, and `direct_release_score`. All score
columns must use the 1-5 scale.

For the current pilot, put all exported `likert_feedback_ratings*.csv` files
from Teacher 1/2 and Batch 1/2 into one folder; the analysis script can read
multiple exports from that folder and filters the routing table to the rated
feedback items.

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
