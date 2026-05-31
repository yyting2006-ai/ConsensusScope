# 2.5-Minute Demo Video Script

Target length: 2 minutes 25 seconds.

Local draft screen-flow recording:

- Regenerate the browser recording with `node scripts/record_demo_video_en.mjs`.
- Convert the generated WebM to MP4 with `python3 scripts/convert_video_to_mp4.py` if needed.
- The generated file is a silent screen-flow recording. For final submission, add
  narration using this script and upload the final video to an accessible URL.

## 0:00-0:15 Opening

Narration:

> ConsensusScope is a risk-aware observability tool for multi-LLM collaborative decision-making. It starts from a simple premise: multi-model agreement is useful, but agreement alone is not proof of correctness.

Screen:

- Show the app title.
- Show the sidebar with the three pages.

## 0:15-0:45 False Consensus Case

Narration:

> In this FEVER example, three models agree that the claim should be refuted, but the gold label is not enough information. A simple majority vote produces a confident but wrong decision.

Screen:

- Open `Single Sample Analysis`.
- Select `fever` and sample `fever_0366`.
- Point to the gold answer, model cards and risk labels.

Key line:

> The system marks this as false consensus, minority correct and confidence mismatch.

## 0:45-1:15 High Disagreement Case

Narration:

> ConsensusScope also catches cases where the model group splits. Here the system avoids forcing a brittle final answer and recommends human review.

Screen:

- Select `commonsenseqa` and sample `csqa_4914`.
- Show majority voting and dynamic adjudication.

Key line:

> Dynamic adjudication turns disagreement into a decision state, not only a final answer.

## 1:15-1:50 Aggregate View

Narration:

> At the dataset level, the prototype compares majority voting, fixed judging and dynamic decision-making. The current pilot contains 1000 adjudicated samples and 4000 structured model-output rows.

Screen:

- Open `Overview Statistics`.
- Show method accuracy table and risk type distribution.
- Show risk-level error-rate chart.

Key line:

> The most important result is risk stratification: low-risk dynamic decisions are much more accurate, while high-risk decisions concentrate errors.

## 1:50-2:15 Publication Readiness

Narration:

> The final page packages the system for a demo submission. It lists the EMNLP requirements, a video plan, and journal routes for a longer paper.

Screen:

- Open `Publication Readiness`.
- Show the checklist and venue table.

## 2:15-2:25 Closing

Narration:

> ConsensusScope is not a new LLM and not a truth oracle. It is a reliability layer that helps researchers and practitioners inspect when multi-LLM collaboration should answer, warn, re-check or stop.

Screen:

- End on the `Publication Readiness` page.
