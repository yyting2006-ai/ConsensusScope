# Legacy Results

`adjudication_results_legacy.csv` was produced by the original skeleton
pipeline now archived under `legacy/`. It contains
`fixed_judge_placeholder` rows that simply reuse majority vote and are not used
in the EMNLP 2026 demo pipeline, paper tables, release metrics, or fixed-judge
baseline.

The current fixed-judge baseline is `src.decision.baselines.fixed_judge_decision`
and its saved output is `data/results/fixed_judge_results.csv`.
