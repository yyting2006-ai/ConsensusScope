# 2.5-Minute Demo Video Script

Target length: 2 minutes 30 seconds.

Local recording:

- Start the app with `streamlit run app/streamlit_app.py --server.port 8502`.
- Use the practical Streamlit workflow rather than only the static UI prototype.
- The final narrated video should be in English and at or below 2 minutes 30
  seconds.

## 0:00-0:20 Problem

Narration:

> AI writing feedback can be fluent but unsafe. A model may fix a local grammar
> issue while also changing a student's intended meaning, adding unsupported
> content, or overcorrecting a reasonable ESL draft.

Screen:

- Open Page 1: Review Workspace.
- Point to the workflow: single essay, batch review, comparison, queue,
  evaluation, and reports.

## 0:20-0:50 Single Essay Review

Narration:

> In the single essay window, a teacher can paste an ESL draft, provide the
> assignment prompt, and generate AI-style feedback candidates. The system then
> routes each feedback item before it reaches the student. Each item receives a
> risk score, evidence signal, review priority, and short explanation for the
> teacher.

Screen:

- Click Page 2: Single Essay Review.
- Load a demo essay.
- Click Generate and route AI feedback.
- Point to auto-accepted local edits and teacher-review items.
- Point to risk score, evidence signal, and review explanation columns.

## 0:50-1:10 Batch Review

Narration:

> The batch window supports the practical classroom workflow: multiple essays
> can be processed from a CSV, then exported as routed feedback for teacher
> triage.

Screen:

- Click Page 3: Batch Review.
- Use the packaged synthetic CSV.
- Click Run batch AI feedback review.
- Show the summary table and routed feedback export.

## 1:10-1:30 AI Feedback Comparison

Narration:

> The comparison page makes model disagreement visible. Feedback is grouped by
> target span and issue type, with reviewers, suggestions, risk levels, and
> consensus state shown together.

Screen:

- Click Page 4: AI Feedback Comparison.
- Point to aligned feedback and risk-preserved-for-teacher rows.

## 1:30-2:00 Teacher Queue And Cases

Narration:

> The teacher queue prioritizes high-risk feedback first. Here are four cases:
> a safe local phrase edit can be accepted; a thesis-reversing suggestion is
> routed to review; an unsupported exam-score claim is blocked; and a
> teacher-dependent punctuation suggestion is now reviewable after our
> two-teacher diagnostic pilot.

Screen:

- Click Page 5: Teacher Queue.
- Open a high-risk item.
- Point to the Feedback Safety Graph path, review confidence, evidence signal,
  priority, and explanation.
- Mention the four case labels: local edit, meaning change, unsupported claim,
  teacher-dependent wording.
- Select one teacher action.

## 2:00-2:20 Effectiveness And Reports

Narration:

> The evaluation page separates two kinds of evidence. The synthetic checks
> verify implementation behavior, while the public learner-corpus benchmark
> evaluates routing on JFLEG, CoNLL-2014, FCE, and W&I plus LOCNESS correction
> data. We also ran a small two-teacher blind Likert pilot over 30 feedback
> items. After adding deploy-time signals for teacher-dependent wording,
> semantic drift, and wrong local corrections, review-needed and unsafe-item
> recall both reach 1.000. These results validate graph-backed review routing,
> not classroom learning outcomes.

Screen:

- Click Page 6: Effectiveness Evaluation.
- Show action accuracy, risk accuracy, high-risk recall, review recall, and
  auto-accept precision.
- Scroll to the public learner-corpus benchmark table and point to auto share,
  review share, and errors reviewed.
- Click Page 7: Reports and show export buttons.

## 2:20-2:30 Closing

Narration:

> ConsensusScope turns AI writing feedback into a teacher-review workflow:
> generate, compare, route, review, and export.

Screen:

- Stop on Reports or return to Review Workspace.
