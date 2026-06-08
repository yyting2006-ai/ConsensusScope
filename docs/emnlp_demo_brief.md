# ConsensusScope: EMNLP Demo Brief

## One-Line Pitch

ConsensusScope is an interactive review-routing tool for safe AI feedback on
ESL writing. It shows how multi-model feedback candidates can be normalized,
screened for risk with interpretable review signals, and routed into teacher
review before students see unsafe or meaning-changing suggestions.

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
4. Compare low-risk auto-accepted local edits with teacher-review items.
5. Open a feedback detail page and inspect routing reasons.
6. Review the teacher queue by risk level and issue type.
7. Export a teacher-readable report.

## Current Optimized Demo Path

- The default synthetic essay contains local grammar/vocabulary edits, medium
  organization/development advice, and high-risk meaning-change suggestions.
- The teacher view separates low-risk local edits from items that may change
  stance, add unsupported claims, or overcorrect the student's draft.
- The AI review layer reports risk scores, evidence signals, route confidence,
  review priorities, and short explanations for each routed item.
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
public gold corrections and compared with constructed risk distractors. Future
validation should add teacher annotations and report them as offline diagnostic
results, separate from deploy-time routing signals.

## Submission Gaps

- Record a video under 2.5 minutes.
- Add a real screencast upload or submit the video as supplementary material.
- Regenerate the final LaTeX PDF/package after the paper text is updated.
- Future work: collect instructor annotations for feedback safety,
  accept/edit/reject decisions, and review-priority judgments.
