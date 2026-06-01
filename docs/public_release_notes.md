# Public Release Notes

Use this document when preparing the public ConsensusScope repository and
Streamlit deployment for the EMNLP 2026 System Demonstrations submission.

## Suggested Repository Name

`ConsensusScope`

## Suggested Short Description

Knowledge-grounded multi-LLM review routing for ESL comparative-literature
writing feedback.

## Suggested Tags

`llm-feedback`, `educational-nlp`, `writing-feedback`, `esl-writing`,
`literary-analysis`, `comparative-literature`, `multi-llm`,
`human-in-the-loop`, `streamlit`, `knowledge-graph`

## Keep

- `README.md`
- `README_EN.md`
- `README_ZH.md`
- `LICENSE`
- `requirements.txt`
- `config.yaml`
- `app/`
- `src/`
- `scripts/`
- `tests/`
- `docs/`
- `paper/`
- `data/knowledge/literary_kg_triples.csv`
- `data/literary_feedback/benchmark.csv`
- `data/results/literary_feedback_records.json`
- `data/results/literary_feedback_routing_metrics.csv`
- `data/results/literary_feedback_live_multimodel_records.json`
- `data/results/literary_feedback_live_multimodel_metrics.csv`
- auxiliary QA data only if it is clearly documented as an auxiliary reliability
  module rather than the main ESL submission claim

## Remove Or Replace Before Public Release

- `.env`
- API keys or copied secrets
- private student data
- raw classroom writing samples
- personal contact information not intended for publication
- operating-system files such as `._*` and `.DS_Store`
- cache directories such as `__pycache__/` and `.pytest_cache/`
- draft screenshots or videos that tell the old QA-centered story

## Release Positioning

The main public-facing story should be:

> ConsensusScope helps teachers audit AI-generated feedback for ESL
> comparative-literature essays by routing low-risk local edits separately from
> feedback involving literary facts, character relations, themes, or
> interpretation.

Do not present the system as an automatic essay scorer, teacher replacement, or
truth oracle. Do not present the auxiliary QA reliability pages as the main
system claim.

## Privacy Reminder

Before adding real student essays, remove names, IDs, emails, demographic
details, school identifiers, and any personally identifying information. The
packaged demo uses anonymized or synthetic examples.
