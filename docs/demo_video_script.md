# 2.5-Minute Demo Video Script

Target length: 2 minutes 30 seconds.

Local draft screen-flow recording:

- Open `ui_prototype/index.html`, or run `python3 -m http.server 8080` inside
  `ui_prototype/`.
- Regenerate the browser recording with `node scripts/record_demo_video_en.mjs`.
- Convert the generated WebM to MP4 with
  `python3 scripts/convert_video_to_mp4.py` if needed.
- The generated file is a silent screen-flow recording. For final submission,
  add English narration and submit the final screencast as supplementary
  material or replace this note with a confirmed video URL.

## 0:00-0:20 Problem

Narration:

> AI writing feedback can be fluent but unsafe. A model may fix a local grammar
> issue while also changing a student's intended meaning, adding unsupported
> content, or overcorrecting a reasonable ESL draft.

Screen:

- Open Page 1: Review Workspace.
- Point to the teacher-facing question and workflow summary.

## 0:20-0:45 System Overview

Narration:

> ConsensusScope routes AI-generated ESL writing feedback before it reaches
> students. Low-risk local edits can be accepted, while feedback that may change
> meaning or require pedagogical judgment goes to the teacher queue.

Screen:

- Click Page 2: Essay Review.
- Show the anonymized synthetic essay, assignment prompt, and routing summary.

## 0:45-1:15 Feedback Detail

Narration:

> Each feedback item has a unified schema: issue type, target span, suggestion,
> student-facing draft, risk level, routing reason, and review evidence.

Screen:

- Click Page 3: Feedback Detail.
- Show the high-risk thesis-reversal example.
- Point to the routing explanation and teacher action buttons.

## 1:15-1:45 Teacher Queue

Narration:

> The teacher queue prioritizes high-risk feedback first. Teachers can filter by
> risk, issue type, and status, so the system supports human review rather than
> hiding uncertainty behind a single automatic decision.

Screen:

- Click Page 4: Teacher Queue.
- Filter or point to high-risk meaning-change and unsupported-claim items.

## 1:45-2:10 Writing Rubric

Narration:

> The Writing Rubric page makes routing rules inspectable. The system uses
> deploy-time signals such as meaning preservation, local edit scope, task
> response, organization, tone, and parse quality. It does not use hidden gold
> labels at deployment time.

Screen:

- Click Page 5: Writing Rubric.
- Point to the low, medium, and high risk rules.

## 2:10-2:25 Report Export

Narration:

> The report exports a teacher-readable audit trail with accepted edits,
> review-routed items, routing reasons, and limitations.

Screen:

- Click Page 6: Reports.
- Show the report preview.

## 2:25-2:30 Closing

Narration:

> ConsensusScope helps teachers decide when AI feedback is safe to show and when
> it needs human review.

Screen:

- Stop on Reports or return to Review Workspace.

