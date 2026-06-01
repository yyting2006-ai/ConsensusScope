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
- Live reviewer integration has been smoke-tested with DeepSeek, Qwen, GLM, and
  Kimi on one benchmark essay; records are stored without API keys.

## Required pages for the submission video

- Single Sample Analysis: concrete failure case where the majority is wrong.
- Overview Statistics: aggregate risk distribution and method comparison.
- Publication Readiness: EMNLP checklist, demo script, target venues.

## Evaluation already available

Current local files include:

- `data/results/method_metrics.csv`: accuracy and risk rates for majority vote, dynamic decision and fixed judge.
- `data/results/risk_labels.csv`: risk labels for 1000 evaluated samples.
- `data/results/risk_level_effectiveness.csv`: risk-level error rates.
- `reports/experiment_report.md`: generated experiment report.
- `reports/figures/`: visual figures for the paper.

## Submission gaps

- Add English README and installation instructions.
- Add screenshots to the paper.
- Add permissive license.
- Prepare a no-API sample package.
- Record a video under 2.5 minutes.
- Add a short ethics and limitations section.
