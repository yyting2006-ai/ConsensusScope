# Ethics and Limitations

ConsensusScope is designed as a teacher-support and audit tool for AI-generated
ESL writing feedback. It should not be presented as an automatic essay scorer,
teacher replacement, truth oracle, or final decision maker.

## Intended Use

- Inspect AI-generated feedback before it changes a student's draft.
- Separate low-risk local grammar/vocabulary edits from feedback that may change
  meaning, add unsupported content, overcorrect a draft, or require teacher
  judgment.
- Use the Feedback Safety Graph as an audit aid that explains why a feedback
  item was routed to auto-accept or teacher review.
- Route uncertain or meaning-changing suggestions to teacher review.
- Support research on educational NLP, feedback reliability, human-in-the-loop
  review, and multi-LLM adjudication.

## Out-Of-Scope Use

- Fully automated grading or student ranking.
- Replacing teachers, writing instructors, reviewers, or domain experts.
- Treating model rationales as verified evidence.
- Treating review-routing labels as final truth.
- Treating Feedback Safety Graph nodes as verified facts rather than
  deploy-time warning signals.
- Applying feedback to real student essays without privacy review.

## Data Privacy

The packaged ESL writing demo uses synthetic examples. If educational writing
data is added later:

- Remove names, student IDs, emails, school identifiers, demographic details,
  and rare personal details.
- Store teacher annotations separately from identifiable student records.
- Report aggregate results unless explicit consent permits case-level excerpts.
- Avoid uploading private classroom data to third-party model providers without
  institutional approval.

## Current Limitations

- The current ESL writing data is synthetic and demonstration-oriented.
- The deterministic routing function is transparent but simple; it should be
  validated with teacher annotations before being presented as a measured
  classroom tool.
- Saved live validation records, if used, show API connectivity and schema
  compliance, not a classroom user study.
- Future validation should include instructor-annotated ESL essays and teacher
  review-priority judgments.
