# ConsensusScope

**ConsensusScope: An Interactive Review-Routing Tool for Safe AI Feedback on ESL Writing**

ConsensusScope helps teachers review AI-generated ESL writing feedback before it
is shown to students. It separates low-risk local language edits from feedback
that may change meaning, add unsupported content, overcorrect a draft, or require
teacher judgment.

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

- `ui_prototype/index.html`: designer-facing product prototype.
- `profiles/esl_writing.yaml`: ESL writing feedback profile.
- `data/esl_writing_demo/`: synthetic ESL essays, feedback items, evidence, and
  routing output.
- `src/esl_writing_feedback.py`: rule-based review-routing interface.
- `src/prompts/esl_feedback_prompt.py`: structured feedback prompt template.
- `scripts/analyze_esl_feedback_experiment.py`: offline analysis script for
  future teacher annotations.

## Main Prototype Pages

1. Review Workspace
2. Essay Review
3. Feedback Detail
4. Teacher Queue
5. Writing Rubric
6. Reports
7. Settings / Diagnostics

## Boundary

ConsensusScope is not an automatic essay scorer, not a teacher replacement, and
not a truth oracle. Earlier domain-specific feedback and QA reliability modules
remain in the repository only as legacy or auxiliary materials and are not the
current main demo claim.
