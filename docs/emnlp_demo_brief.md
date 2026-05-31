# ConsensusScope: EMNLP Demo Brief

## One-line pitch

ConsensusScope is a risk-aware observability tool for multi-LLM collaborative decision-making. It shows when multi-model agreement is reliable, when it becomes false consensus, and when minority answers or human review should be preserved.

## Target users

- Researchers studying LLM reliability, hallucination, factuality, and multi-agent collaboration.
- Product teams building multi-model QA, fact-checking, education feedback, or decision-support systems.
- Teachers and evaluators who need to inspect AI-generated feedback rather than accept a single model answer.

## Demo workflow

1. Select a dataset and sample.
2. Inspect independent answers from multiple LLMs.
3. Compare majority voting and dynamic adjudication.
4. Check risk labels: true consensus, false consensus, minority correct, high disagreement, confidence mismatch.
5. Open global statistics: method accuracy, risk distribution, risk-level error rates.
6. Export a sample-level CSV for audit or annotation.

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
