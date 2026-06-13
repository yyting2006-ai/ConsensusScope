# Two-Teacher Likert Pilot Summary

## Purpose

This note summarizes a small blind diagnostic pilot used to stress-test
ConsensusScope's review-routing behavior for AI-generated ESL writing feedback.
It is not a classroom effectiveness study and should not be reported as evidence
for student learning outcomes.

## Setup

- Annotators: two English teachers, anonymized as Teacher 1 and Teacher 2.
- Items: 30 synthetic/anonymized AI feedback items from the expert annotation
  app.
- Mode: Blind Annotation Mode.
- Scale: 1-5 Likert ratings for correctness, meaning preservation, student
  readiness, usefulness, clarity, and direct-release suitability.
- Use of labels: offline diagnostics only; ratings are not visible to the
  deploy-time router.

## Main Finding

The pilot identified three borderline auto-release patterns that should remain
reviewable even when they look like local language edits: teacher-dependent
advice such as "if the teacher wants", semantic drift such as "remember" to
"learned", and wrong modal-verb correction such as "can make" to "makes".
ConsensusScope therefore adds deploy-time `teacher_dependent`, semantic-drift,
and wrong-correction signals and routes such feedback to teacher review.

## Representative Cases

- `FB-002`: safe local phrase improvement; both teachers rated it safe and it
  remains auto-accepted.
- `FB-003`: thesis-reversing suggestion; the graph activates meaning
  preservation risk and routes it to teacher review.
- `FB-008`: unsupported exam-score claim; the graph activates content
  grounding risk and routes it to teacher review.
- `FB-009`: teacher-dependent punctuation advice; the pilot exposed it as a
  borderline auto-release case, so the optimized router sends it to review.
- `FB-014`: vocabulary edit changes "remember" to "learned"; the graph now
  activates meaning-preservation risk.
- `FB-005`: grammar edit changes "can make" to "makes"; the graph now marks it
  as a wrong local correction.

## Teacher-Aligned Routing Results

| Metric | Value |
|---|---:|
| Feedback items | 30 |
| Rating rows | 60 |
| Auto share | 0.233 |
| Review share | 0.767 |
| Review-needed recall | 1.000 |
| Unsafe reviewed recall | 1.000 |
| Auto precision vs. teacher-safe items | 0.857 |
| Any-teacher unsafe reviewed recall | 1.000 |

## Inter-Teacher Agreement

Across the 30 items, the mean within-one-point agreement over the six rating
dimensions is 0.694. Agreement is strongest for correctness and weaker for
direct-release suitability and clarity, suggesting that release decisions are
more subjective than correctness judgments.

## Reporting Boundary

In the paper, these results should be described as a preliminary teacher-aligned
diagnostic pilot. They support the claim that teacher ratings can reveal
borderline auto-release cases and guide conservative rule updates. They do not
support claims about classroom effectiveness, teacher satisfaction, time saving,
or student learning gains.
