# ConsensusScope: EMNLP Demo Brief

## One-Line Pitch

ConsensusScope is an interactive Feedback Safety Graph system for safe AI
feedback on ESL writing. Its core mechanism turns each AI
feedback item into an auditable object linking the student target span, AI
suggestion, evidence status, active safety dimensions, and routing decision.
The system shows how multi-model feedback candidates can be normalized,
screened for meaning-change and safety risks, and routed into teacher review
before students see unsafe or meaning-changing suggestions.

## Target Users

- NLP researchers studying LLM reliability, feedback generation, and
  human-in-the-loop review.
- Educational NLP developers building AI writing feedback tools for ESL
  learners.
- Writing teachers who need to inspect AI-generated feedback rather than accept
  a single model revision.

## Demo Workflow

1. Open the review workspace.
2. Load a synthetic anonymized ESL writing draft.
3. Inspect AI feedback candidates in a unified schema.
4. Inspect the Feedback Safety Graph path for selected items.
5. Compare low-risk auto-accepted local edits with teacher-review items.
6. Open a feedback detail page and inspect routing reasons.
7. Review the teacher queue by risk level and issue type.
8. Export a teacher-readable report.

## Current Optimized Demo Path

- The default synthetic essay contains local grammar/vocabulary edits, medium
  organization/development advice, and high-risk meaning-change suggestions.
- The teacher view separates low-risk local edits from items that may change
  stance, add unsupported claims, or overcorrect the student's draft.
- The AI review layer reports active Feedback Safety Graph dimensions, graph
  paths, risk scores, evidence signals, route confidence, review priorities,
  and short explanations for each routed item.
- The Writing Rubric page shows deploy-time routing rules rather than hidden
  gold labels.
- The report page exports an audit trail with explicit limitations.

## Required Pages For The Submission Video

- Review Workspace.
- Essay Review.
- Feedback Detail.
- Teacher Queue.
- Writing Rubric.
- Reports.

## Evaluation Status

The current ESL writing package contains synthetic demo data, deterministic
routing output, AI-review stress cases, and public learner-corpus routing
benchmarks. The public benchmark covers JFLEG, CoNLL-2014 official annotated
test data, FCE, and W&I+LOCNESS train/dev splits with gold correction labels.
Across 349,782 feedback candidates generated from public correction data, the
default policy auto-routes about 32.9% of candidates and routes all constructed
incorrect or unsafe candidates to review.

This is evidence for the review-routing layer, not classroom effectiveness.
The high auto-accuracy is expected because correct candidates are derived from
public gold corrections and compared with constructed risk distractors.

We have also collected a small blind two-teacher 1-5 Likert diagnostic pilot
over 30 AI feedback items. The pilot is used only as offline evaluation: it
identified teacher-dependent wording, semantic drift in wording edits, and
wrong modal-verb corrections as borderline auto-release patterns. After adding
deploy-time signals for these cases, review-needed recall is 1.000, unsafe
reviewed recall is 1.000, and auto precision against teacher-safe items is
0.857. This is still preliminary and should not be framed as classroom
effectiveness.

## Submission Gaps

- Record a video under 2.5 minutes.
- Add a real screencast upload or submit the video as supplementary material.
- Regenerate the final LaTeX PDF/package after the paper text is updated.
- Future work: expand beyond the current two-teacher, 30-item diagnostic pilot
  with authentic anonymized classroom data and more instructor ratings.
