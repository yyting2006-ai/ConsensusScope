# ConsensusScope

**ConsensusScope: A Teacher-Controlled Safety Routing System for AI-Generated ESL Writing Feedback**

ConsensusScope helps teachers review AI-generated ESL writing feedback before it
is shown to students. It separates low-risk local language edits from feedback
that may change meaning, add unsupported content, overcorrect a draft, or require
teacher judgment. The AI review layer now builds an item-level **Feedback Safety
Graph** for every feedback candidate and reports active safety dimensions,
graph paths, risk scores, evidence signals, review priorities, and short
explanations for teacher review.

The canonical English README is `README.md`; this file is kept as a short
compatibility entry point.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
uvicorn backend.app:app --host 127.0.0.1 --port 7864
```

In a second terminal:

```bash
CONSENSUS_SCOPE_BACKEND_URL=http://127.0.0.1:7864 \
streamlit run app/streamlit_app.py --server.port 8502
```

Then open `http://localhost:8502`.

## Current Main Assets

- `app/streamlit_app.py`: bilingual teacher workspace with registration and
  sign-in, single/batch review, comparison, teacher queue, reports, personal
  history, profile/password management, and product feedback.
- `backend/`: authenticated FastAPI service with per-user SQLite persistence,
  review deletion, audit logs, and an administrator feedback inbox.
- `ui_prototype/index.html`: designer-facing product prototype.
- `profiles/esl_writing.yaml`: ESL writing feedback profile.
- `data/esl_writing_demo/`: synthetic ESL essays, feedback items, evidence,
  routing output, and AI-review stress cases.
- `src/esl_writing_feedback.py`: Feedback Safety Graph construction and
  rule-based review-routing interface.
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
6. Reports
7. My Account
8. Feedback
9. Settings / Diagnostics

## Boundary

ConsensusScope is not an automatic essay scorer, not a teacher replacement, and
not a truth oracle. Earlier domain-specific feedback and QA reliability modules
remain in the repository only as legacy or auxiliary materials and are not the
current main demo claim. The packaged evaluation includes synthetic stress
checks and an offline public learner-corpus routing benchmark. It validates the
review-routing layer, not classroom effectiveness, student learning gains, or
real LLM feedback quality.

Accounts keep review data private between users, but the backend stores essay
text until the user deletes the review or the operator applies a retention
policy. Only anonymized writing may be uploaded. The first account release does
not include email verification or password reset.
