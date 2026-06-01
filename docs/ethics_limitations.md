# Ethics and Limitations

ConsensusScope is designed as a teacher-support and audit tool for ESL
comparative-literature writing feedback. It should not be presented as an
automatic essay scorer, teacher replacement, truth oracle, or final decision
maker.

## Intended Use

- Inspect AI-generated feedback before it changes a student's writing.
- Separate low-risk local grammar/style edits from feedback involving literary
  facts, character relations, themes, thesis claims, or interpretation.
- Route uncertain or meaning-changing suggestions to teacher review.
- Support research on educational NLP, feedback reliability, human-in-the-loop
  review, and multi-LLM adjudication.

## Out-of-Scope Use

- Fully automated grading or student ranking.
- Replacing teachers, writing instructors, reviewers, or domain experts.
- Treating model rationales as verified evidence.
- Treating a small curated literary KG as a complete literary database.
- Applying feedback to real student essays without privacy review.

## Data Privacy

The packaged demo uses anonymized or synthetic examples. If educational writing
data is added later:

- Remove names, student IDs, emails, school identifiers, demographic details,
  and rare personal details.
- Store teacher annotations separately from identifiable student records.
- Report aggregate results unless explicit consent permits case-level excerpts.
- Avoid uploading private classroom data to third-party model providers without
  institutional approval.

## Current Limitations

- The current KG contains 319 curated triples over 30 works; it is useful for
  demonstration and diagnosis, not comprehensive literary scholarship.
- The 30-case benchmark is intentionally small and diagnostic. It validates the
  review-routing workflow, not state-of-the-art essay scoring or correction
  accuracy.
- Saved live validation records show API connectivity and schema compliance,
  but they are not a classroom user study.
- Future validation should include instructor-annotated ESL essays and teacher
  review-priority judgments.
