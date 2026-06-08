# ConsensusScope

**ConsensusScope: An Interactive Review-Routing Tool for Safe AI Feedback on ESL Writing**

ConsensusScope helps teachers review AI-generated ESL writing feedback before it
is shown to students. It separates low-risk local language edits from feedback
that may change meaning, add unsupported content, overcorrect a draft, or require
teacher judgment. The AI review layer now reports item-level risk scores,
evidence signals, review priorities, and short explanations for teacher review.

The canonical English README is `README.md`; this file is kept as a short
compatibility entry point.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
streamlit run app/streamlit_app.py --server.port 8502
```

Then open `http://localhost:8502`.

## Current Main Assets

- `app/streamlit_app.py`: practical teacher workspace with single-essay review,
  batch review, AI feedback comparison, teacher queue, evaluation, and reports.
- `ui_prototype/index.html`: designer-facing product prototype.
- `profiles/esl_writing.yaml`: ESL writing feedback profile.
- `data/esl_writing_demo/`: synthetic ESL essays, feedback items, evidence,
  routing output, and AI-review stress cases.
- `src/esl_writing_feedback.py`: rule-based review-routing interface.
- `src/prompts/esl_feedback_prompt.py`: structured feedback prompt template.
- `scripts/evaluate_esl_routing_demo.py`: synthetic routing sanity-check
  evaluation script.
- `scripts/run_public_gec_benchmark.py`: public learner-corpus benchmark runner
  for JFLEG-style files, `.m2` GEC files, and source/reference CSV files.
- `reports/public_gec_summary_20260608.md`: aggregate public-corpus benchmark
  results without redistributed corpus text.
- `scripts/analyze_esl_feedback_experiment.py`: offline analysis script for
  future teacher annotations.

## Main App Pages

1. Review Workspace
2. Single Essay Review
3. Batch Review
4. AI Feedback Comparison
5. Teacher Queue
6. Effectiveness Evaluation
7. Reports
8. Settings / Diagnostics
9. Design Reference

## Boundary

ConsensusScope is not an automatic essay scorer, not a teacher replacement, and
not a truth oracle. Earlier domain-specific feedback and QA reliability modules
remain in the repository only as legacy or auxiliary materials and are not the
current main demo claim. The packaged evaluation includes synthetic stress
checks and an offline public learner-corpus routing benchmark. It validates the
review-routing layer, not classroom effectiveness, student learning gains, or
real LLM feedback quality.
