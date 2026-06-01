# ConsensusScope

ConsensusScope is a knowledge-grounded multi-LLM review-routing tool for ESL
comparative-literature writing feedback. It helps teachers decide which
AI-generated feedback can be safely accepted and which feedback needs human
review.

It is not an automatic essay scorer, not a teacher replacement, and not a truth
oracle.

For the current EMNLP 2026 System Demonstrations package, the canonical English
README is `README.md`. This file is kept as a compatibility entry point and
summarizes the same ESL-focused direction.

## Run The Demo

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
streamlit run app/streamlit_app.py --server.port 8502
```

Then open `http://localhost:8502`.

## What The Demo Shows

- ESL comparative-literature feedback review.
- Curated literary KG: 319 triples over 30 works.
- No-API deterministic reviewers for reproducible demos.
- Optional live OpenAI-compatible reviewers.
- Low-risk local grammar/style edits routed to auto-accept.
- Literary facts, argument changes, and interpretation changes routed to
  teacher review.
- Exportable reports for teacher inspection.
- Auxiliary QA reliability pages, clearly separated from the main ESL claim.

## Current ESL Snapshot

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

The benchmark is diagnostic and workflow-oriented. It is not a large classroom
study and not a state-of-the-art essay-scoring benchmark.

## Privacy

Before adding real student essays, remove names, IDs, emails, demographic
details, school identifiers, and any personally identifying information. The
packaged demo uses anonymized or synthetic examples.

## License

MIT License. See `LICENSE`.
