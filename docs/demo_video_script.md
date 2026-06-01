# 2.5-Minute Demo Video Script

Target length: 2 minutes 30 seconds.

Local draft screen-flow recording:

- Start the app with `streamlit run app/streamlit_app.py --server.port 8502`.
- Regenerate the browser recording with `node scripts/record_demo_video_en.mjs`.
- Convert the generated WebM to MP4 with `python3 scripts/convert_video_to_mp4.py`
  if needed.
- The generated file is a silent screen-flow recording. For final submission,
  add English narration using this script and submit the final screencast as
  supplementary material or replace this note with a real confirmed video URL.

## 0:00-0:20 Problem

Narration:

> AI writing feedback can be fluent but unsafe. In ESL comparative-literature
> essays, a model may fix grammar correctly while changing literary facts,
> character relations, or the student's interpretation.

Screen:

- Open Page 1: Home / System Overview.
- Point to the title and the review-routing workflow.

## 0:20-0:45 System Overview

Narration:

> ConsensusScope compares multiple LLM feedback outputs and routes each
> suggestion into either low-risk auto-accept or teacher review. It is not an
> automatic essay scorer and it does not replace teacher judgment.

Screen:

- Click Page 2: ESL Feedback Review.
- Show the demo essay, reviewer source selector, and Run Knowledge-Grounded
  Feedback button.
- Use the no-API deterministic reviewer path for the recording.

## 0:45-1:10 Knowledge Grounding

Narration:

> The system retrieves evidence from a curated literary knowledge graph,
> including author, work, genre, central characters, themes, and publication
> year. These triples make factual feedback inspectable.

Screen:

- Run the feedback demo.
- Open the Knowledge Evidence tab.
- Point to author and publication-year rows.

## 1:10-1:40 Feedback Adjudication

Narration:

> Low-risk local grammar or style edits can be accepted, but suggestions about
> authorship, genre, character identity, thesis statements, or interpretation
> remain in the teacher-review queue.

Screen:

- Open the Teacher View and Adjudication Trace tabs.
- Point to auto-accepted preview and teacher-review decisions.

## 1:40-2:05 Teacher Review Queue

Narration:

> The teacher review queue shows risk level, priority, model agreement,
> knowledge support, and a short explanation for why human review is
> recommended.

Screen:

- Click Page 3: Knowledge Grounding & Teacher Queue.
- Show the queue and risk/priority fields.
- If the auxiliary QA mode is visible, mention it only briefly.

Key line:

> The system also includes auxiliary multi-model QA audit pages, but this demo
> focuses on ESL literary feedback.

## 2:05-2:25 Report Export

Narration:

> The final page exports a Markdown feedback report and structured JSON or CSV
> files so the decision process can be inspected and reproduced.

Screen:

- Click Page 8: Report Export.
- Show the literary feedback report download and system summary export.

## 2:25-2:30 Closing

Narration:

> ConsensusScope helps decide when AI feedback requires human review.

Screen:

- Return to Page 1 or stop on Report Export.
- Leave one second of silence before ending the recording.
