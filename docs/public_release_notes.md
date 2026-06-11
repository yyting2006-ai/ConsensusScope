# Public Release Notes

Use this document when preparing the public ConsensusScope repository and
Streamlit deployment for the EMNLP 2026 System Demonstrations submission.

## Suggested Repository Name

`ConsensusScope`

## Suggested Short Description

Feedback Safety Graphs for teacher review routing of AI feedback on ESL writing.

## Suggested Tags

`llm-feedback`, `educational-nlp`, `writing-feedback`, `esl-writing`,
`human-in-the-loop`, `teacher-support`, `multi-llm`, `streamlit`,
`review-routing`, `feedback-safety-graph`

## Keep

- `README.md`
- `README_EN.md`
- `README_ZH.md`
- `INSTALL.md`
- `DEPLOYMENT.md`
- `LICENSE`
- `requirements.txt`
- `config.yaml`
- `app/`
- `src/`
- `scripts/`
- `tests/`
- `docs/`
- `paper/`
- `profiles/esl_writing.yaml`
- `data/esl_writing_demo/`
- `ui_prototype/`
- auxiliary QA and earlier demo data only if clearly documented as legacy or
  auxiliary material rather than the main ESL writing submission claim

## Remove Or Replace Before Public Release

- `.env`
- API keys or copied secrets
- private student data
- raw classroom writing samples
- personal contact information not intended for publication
- operating-system files such as `._*` and `.DS_Store`
- cache directories such as `__pycache__/` and `.pytest_cache/`
- draft screenshots or videos that tell the old story

## Release Positioning

The main public-facing story should be:

> ConsensusScope helps teachers review AI-generated ESL writing feedback by
> constructing a Feedback Safety Graph for each suggestion, then routing
> low-risk local edits separately from feedback that may change meaning,
> introduce unsupported content, overcorrect a draft, or require teacher
> judgment.

The public demo should show the practical Streamlit workflow: single essay
review, batch review, AI feedback comparison, teacher queue, synthetic
effectiveness evaluation, and report export.

Do not present the system as an automatic essay scorer, teacher replacement, or
truth oracle. Do not present auxiliary QA reliability pages or earlier feedback
modules as the main system claim.

## Privacy Reminder

Before adding real student essays, remove names, IDs, emails, demographic
details, school identifiers, and any personally identifying information. The
packaged ESL writing demo uses synthetic examples.
