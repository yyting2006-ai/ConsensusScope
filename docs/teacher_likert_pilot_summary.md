# Two-Teacher Likert Pilot Summary

## Purpose

This note summarizes a small blind diagnostic pilot used to stress-test
ConsensusScope's review-routing behavior for AI-generated ESL writing feedback.
It is not a classroom effectiveness study and should not be reported as evidence
for student learning outcomes.

## Setup

- Annotators: two English teachers, anonymized as Teacher 1 and Teacher 2.
- Items: 12 synthetic/anonymized AI feedback items from the expert annotation
  app.
- Mode: Blind Annotation Mode.
- Scale: 1-5 Likert ratings for correctness, meaning preservation, student
  readiness, usefulness, clarity, and direct-release suitability.
- Use of labels: offline diagnostics only; ratings are not visible to the
  deploy-time router.

## Main Finding

The pilot identified a borderline auto-release pattern: feedback phrased as
teacher-dependent advice, such as "if the teacher wants", should remain
reviewable even when it appears to be a local grammar or punctuation edit.
ConsensusScope therefore adds a deploy-time `teacher_dependent` signal and
routes such feedback to teacher review.

## Representative Cases

- `FB-002`: safe local phrase improvement; both teachers rated it safe and it
  remains auto-accepted.
- `FB-003`: thesis-reversing suggestion; the graph activates meaning
  preservation risk and routes it to teacher review.
- `FB-008`: unsupported exam-score claim; the graph activates content
  grounding risk and routes it to teacher review.
- `FB-009`: teacher-dependent punctuation advice; the pilot exposed it as a
  borderline auto-release case, so the optimized router sends it to review.

## Teacher-Aligned Routing Results

| Metric | Before | After |
|---|---:|---:|
| Auto share | 0.417 | 0.333 |
| Review share | 0.583 | 0.667 |
| Review-needed recall | 0.714 | 0.857 |
| Unsafe reviewed recall | 1.000 | 1.000 |
| Auto precision vs. teacher-safe items | 0.400 | 0.500 |
| Any-teacher unsafe reviewed recall | 0.714 | 0.857 |

## Inter-Teacher Agreement

Across the 12 items, the mean within-one-point agreement over the six rating
dimensions is 0.639. Agreement is strongest for correctness and weaker for
direct-release suitability and clarity, suggesting that release decisions are
more subjective than correctness judgments.

## Reporting Boundary

In the paper, these results should be described as a preliminary teacher-aligned
diagnostic pilot. They support the claim that teacher ratings can reveal
borderline auto-release cases and guide conservative rule updates. They do not
support claims about classroom effectiveness, teacher satisfaction, time saving,
or student learning gains.
