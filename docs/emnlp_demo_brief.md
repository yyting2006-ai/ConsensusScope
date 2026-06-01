# ConsensusScope: EMNLP Demo Brief

## One-line pitch

ConsensusScope is a knowledge-grounded adjudication demo for ESL comparative literature essay feedback. It shows how multi-model feedback suggestions can be checked against expert literary knowledge, agreement signals, and meaning-change risk before low-risk edits are accepted or high-risk revisions are routed to teachers.

## Target users

- NLP researchers studying LLM reliability, feedback generation, hallucination, factuality, and multi-agent collaboration.
- Educational NLP developers building AI writing feedback tools for ESL learners.
- Literature and writing teachers who need to inspect AI-generated feedback rather than accept a single model revision.

## Demo workflow

1. Enter or load an ESL comparative literature essay excerpt.
2. Retrieve literary knowledge about authors, works, years, genres, and characters.
3. Inspect grammar, style, literary-fact, and argument suggestions in a unified schema.
4. Compare automatic acceptance with teacher-review routing.
5. Audit why KG-supported factual corrections and meaning-changing interpretation edits are not blindly auto-applied.
6. Export a feedback report for teacher review or annotation.

## Current optimized demo path

- The default essay contains grammar, literary-fact, style, and argument risks.
- The teacher view shows the original essay next to an auto-accepted preview.
- The review queue prioritizes meaning-changing and KG-supported suggestions.
- Knowledge evidence and raw reviewer suggestions remain inspectable in separate tabs.
- The curated literary KG currently contains 319 triples over 30 commonly taught
  works.
- The deterministic no-API benchmark covers 30 ESL comparative-literature essay
  snippets and produces 59 adjudicated feedback decisions.
- Live reviewer integration has been validated on the first 10 benchmark cases
  with DeepSeek, Qwen, GLM and Kimi: 40 provider calls, no request errors, no
  parse errors, 43 live feedback decisions.

## Required pages for the submission video

- Page 1: Home / System Overview.
- Page 2: Live Question Mode, using the ESL literary-feedback path first.
- Page 3: Sample Audit Mode.
- Page 5: Risk Dashboard.
- Page 8: Report Export.

## Evaluation already available

Current local files include:

- `data/results/method_metrics.csv`: accuracy and risk rates for majority vote, dynamic decision and fixed judge.
- `data/results/risk_labels.csv`: risk labels for 1000 evaluated samples.
- `data/results/risk_level_effectiveness.csv`: risk-level error rates.
- `reports/experiment_report.md`: generated experiment report.
- `reports/figures/`: visual figures for the paper.
- `data/results/literary_feedback_routing_metrics.csv`: ESL feedback routing
  metrics over 30 curated benchmark cases.
- `data/results/literary_feedback_records.json`: raw feedback, KG evidence and
  adjudicated decisions for the ESL benchmark.

## Submission gaps

- Add screenshots to the paper.
- Record a video under 2.5 minutes.
- Add human teacher evaluation or annotation agreement before submission.
