# ConsensusScope Paper Reference Study

Target venue: EMNLP 2026 System Demonstrations.

## Venue Requirements

- Paper type: system demonstration paper.
- Main paper length: up to 6 pages, with unlimited references and at most 2 appendix pages. Accepted papers receive one additional content page.
- Required submission artifacts: paper, short demo video up to 2.5 minutes, and a live demo website or downloadable installation package.
- The paper should describe system design, technical details, visual aids, target audience, comparison with existing systems, license, and evaluation.
- Evaluation is expected; systems without any form of evaluation may be desk rejected.
- Review is single-blind for the demo track.
- Current official dates: submission July 10, 2026; notification August 20, 2026; camera-ready August 30, 2026; conference October 24-29, 2026 in Budapest.
- Abstract: required by ACL/EMNLP style.
- Keywords: not normally included as a paper section in ACL-style demo papers. We should prepare 5-6 OpenReview metadata keywords, but not add a visible `Keywords` block unless the official template for the year explicitly asks for it.
- Reference hygiene matters especially in 2026: EMNLP's paper-integrity note says bibliography entries may be checked for unverifiable references, so every cited item should be traceable to ACL Anthology, arXiv, official proceedings, or publisher pages.

Primary venue/style sources:

- EMNLP 2026 System Demonstrations CFP: https://2026.emnlp.org/calls/demos/
- EMNLP 2026 Paper Integrity Policy: https://2026.emnlp.org/paper-integrity-policy/
- ACLPUB formatting guidance: https://acl-org.github.io/ACLPUB/formatting.html

## Core Positioning

ConsensusScope should not be framed as another hallucination detector or a simple voting ensemble. The strongest positioning is:

> Multi-model agreement is not equivalent to reliability. ConsensusScope provides an observability and adjudication layer that turns agreement, dissent, confidence, evidence, and model-history signals into auditable risk states and decision routes.

This framing lets the paper connect four research lines:

1. Multi-agent / multi-model collaboration improves some reasoning tasks but can over-trust consensus.
2. Self-consistency and voting improve answer selection but are frequency-based and under-diagnostic.
3. LLM-as-a-judge and juries scale evaluation but may introduce judge bias or collapse risk states into a single score.
4. Factuality, hallucination, and uncertainty research motivates risk-aware abstention, review routing, and evidence-sensitive outputs.

## Reference Map

### A. Multi-Agent and Multi-Model Collaboration

1. Du et al. 2023, *Improving Factuality and Reasoning in Language Models through Multiagent Debate*.
   - Use for: motivation that multiple LLM agents can improve factuality/reasoning through debate.
   - Limitation to highlight: performance-oriented; less focused on diagnosing false consensus or preserving minority-correct signals.
   - Link: https://arxiv.org/abs/2305.14325

2. Chen et al. 2023, *ReConcile: Round-Table Conference Improves Reasoning via Consensus among Diverse LLMs*.
   - Use for: diverse-model consensus as a reasoning improvement strategy.
   - Limitation: consensus is generally treated as positive; our paper distinguishes true consensus from false consensus.
   - Link: https://arxiv.org/abs/2309.13007

3. Wang et al. 2023, *Self-Consistency Improves Chain of Thought Reasoning in Language Models*.
   - Use for: sampling-plus-voting as a strong and widely used inference-time baseline.
   - Limitation: self-consistency aggregates answers by frequency but does not explain whether agreement is trustworthy.
   - Link: https://research.google/pubs/self-consistency-improves-chain-of-thought-reasoning-in-language-models/

### B. LLM-as-a-Judge, Model Juries, and Automatic Evaluation

4. Zheng et al. 2023, *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*.
   - Use for: LLM-as-a-judge as scalable evaluation and fixed-judge baseline.
   - Important limitation: position, verbosity, self-enhancement biases and limited reasoning ability.
   - Link: https://papers.nips.cc/paper_files/paper/2023/hash/91f18a1287b398d378ef22505bf41832-Abstract-Datasets_and_Benchmarks.html

5. Liu et al. 2023, *G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment*.
   - Use for: prompt-based LLM evaluators using rubrics and form-filling.
   - Limitation: LLM-based evaluators may favor LLM-generated text; useful as background for judge bias.
   - Link: https://arxiv.org/abs/2303.16634

6. Verga et al. 2024, *Replacing Judges with Juries: Evaluating LLM Generations with a Panel of Diverse Models*.
   - Use for: multiple smaller/diverse judges can reduce dependence on a single judge.
   - Distinction: our system evaluates decision reliability states, not only generation quality scores.
   - Link: https://arxiv.org/abs/2404.18796

### C. Factuality, Hallucination, and Evidence-Sensitive Evaluation

7. Manakul et al. 2023, *SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative LLMs*.
   - Use for: sampling inconsistency as a black-box hallucination signal.
   - Distinction: our system operates across multiple models and adjudicators, with visible risk labels.
   - Link: https://arxiv.org/abs/2303.08896

8. Li et al. 2023, *HaluEval: A Large-Scale Hallucination Evaluation Benchmark for LLMs*.
   - Use for: hallucination evaluation benchmark and broad factuality motivation.
   - Link: https://arxiv.org/abs/2305.11747

9. Min et al. 2023, *FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation*.
   - Use for: evidence and factual support should be evaluated at a finer granularity than answer-level correctness.
   - Link: https://arxiv.org/abs/2305.14251

10. Huang et al. 2023, *A Survey on Hallucination in Large Language Models: Principles, Taxonomy, Challenges, and Open Questions*.
    - Use for: broad hallucination taxonomy; use sparingly in Related Work.
    - Link: https://arxiv.org/abs/2311.05232

### D. Uncertainty, Calibration, and Confidence

11. Kadavath et al. 2022, *Language Models (Mostly) Know What They Know*.
    - Use for: LMs can sometimes self-estimate correctness, but calibration is task-dependent.
    - Link: https://arxiv.org/abs/2207.05221

12. Lin et al. 2022, *Teaching Models to Express Their Uncertainty in Words*.
    - Use for: verbal uncertainty expression and calibrated uncertainty.
    - Link: https://arxiv.org/abs/2205.14334

13. Xiong et al. 2024, *Can LLMs Express Their Uncertainty?*
    - Use for: confidence elicitation and failure prediction across datasets/models.
    - Link: https://proceedings.iclr.cc/paper_files/paper/2024/hash/6733cf15e10e2cd1d59af033c3bb8507-Abstract-Conference.html

14. Kalai and Vempala 2024, *Calibrated Language Models Must Hallucinate*.
    - Use for: calibration and hallucination can coexist; supports why we need risk-aware downstream control rather than assuming calibrated confidence eliminates errors.
    - Link: https://arxiv.org/abs/2311.14648

15. Zhou et al. 2024, *Linguistic Calibration of Language Models*.
    - Use for: linguistic calibration in long-form generation and user decision-making.
    - Link: https://arxiv.org/abs/2404.00474

### E. Benchmarks and Evaluation Infrastructure

16. Lin et al. 2022, *TruthfulQA: Measuring How Models Mimic Human Falsehoods*.
    - Use for: truthfulness/factual QA benchmark in our evaluation.
    - Link: https://aclanthology.org/2022.acl-long.229/

17. Thorne et al. 2018, *FEVER: a Large-scale Dataset for Fact Extraction and VERification*.
    - Use for: claim verification dataset and evidence-grounded labels.
    - Link: https://aclanthology.org/N18-1074/

18. Talmor et al. 2019, *CommonsenseQA: A Question Answering Challenge Targeting Commonsense Knowledge*.
    - Use for: commonsense multiple-choice QA benchmark.
    - Link: https://arxiv.org/abs/1811.00937

19. Liang et al. 2023, *Holistic Evaluation of Language Models (HELM)*.
    - Use for: evaluation should consider multiple dimensions rather than one metric.
    - Link: https://nlp.stanford.edu/helm/vhelm/

20. Srivastava et al. 2022, *Beyond the Imitation Game: Quantifying and Extrapolating the Capabilities of Language Models*.
    - Use for: benchmark diversity and broad LLM capability evaluation context.
    - Link: https://arxiv.org/abs/2206.04615

## How to Use These References in the Paper

### Introduction

Use Du/ReConcile/Self-Consistency to establish that multi-output and multi-agent methods are attractive. Then pivot: these methods improve some tasks, but the reliability problem remains because agreement can be false and dissent can be useful.

Suggested claim:

> Existing multi-LLM methods often optimize for a final answer, whereas deployment-oriented systems need to expose the reliability state that precedes final answer selection.

### Related Work

Organize by function, not by paper list:

1. Multi-output aggregation and debate: self-consistency, debate, ReConcile.
2. Judge-based evaluation: MT-Bench/Chatbot Arena, G-Eval, jury-of-models.
3. Factuality and hallucination evaluation: TruthfulQA, FEVER, HaluEval, SelfCheckGPT, FActScore.
4. Confidence and uncertainty: Kadavath, Lin uncertainty words, Xiong, Kalai/Vempala.

Gap:

> These lines provide mechanisms for improving answers or evaluating generations, but they rarely expose a unified, interactive risk layer that compares majority vote, fixed judging, and rule-based dynamic adjudication on the same model traces.

### System Section

Use demo CFP language implicitly: system design, technical details, screenshots, target users, evaluation, license. Avoid marketing tone. Present modules:

1. API configuration.
2. Multi-model answer generation.
3. Unified output schema.
4. Adjudication layer.
5. Risk and reliability dashboards.
6. Case explorer and report export.

### Evaluation Section

Use current reproduced metrics:

| Method | TruthfulQA | FEVER | CommonsenseQA |
|---|---:|---:|
| Majority Vote | 0.075 | 0.622 | 0.760 |
| Dynamic Rule-Based Judge | 0.075 | 0.661 | 0.760 |
| Fixed Judge | 0.087 | 0.709 | 0.796 |

Interpretation:

- Fixed Judge is the best final selector among current methods.
- Rule-based dynamic adjudication should be framed primarily as risk stratification and review routing.
- Therefore, dynamic adjudication should be framed as a risk-routing mechanism, not merely an answer-selection algorithm.

Risk-level result:

| Method | Risk level | Accuracy |
|---|---|---:|
| Dynamic Rule-Based Judge | low | 0.918 |
| Dynamic Rule-Based Judge | medium | 0.552 |
| Dynamic Rule-Based Judge | high | 0.048 |

This is the most important result for the demo paper.

## Candidate Titles

1. ConsensusScope: An Interactive Observability Tool for Risk-Aware Multi-LLM Adjudication
2. ConsensusScope: Auditing False Consensus and Minority-Correct Signals in Multi-LLM Systems
3. ConsensusScope: An Interactive System for Risk-Aware Multi-LLM Adjudication

Recommended title: **ConsensusScope: An Interactive Observability Tool for Risk-Aware Multi-LLM Adjudication**

## Abstract Plan

ACL/EMNLP abstract should be one paragraph, around 150-200 words.

Movement:

1. Multi-LLM collaboration is increasingly used to improve reliability.
2. Agreement is not always trustworthy; it can create false consensus and suppress correct minorities.
3. Introduce ConsensusScope as an interactive observability and adjudication system.
4. Name the three adjudicators and the deploy-time risk signals.
5. Report dataset-level accuracy and the current key risk-routing numbers: dynamic low-risk subset 0.918 accuracy and high-risk subset 0.952 error rate.
6. End with what the system enables: auditable decisions, review routing, and reproducible demos.

## OpenReview Metadata Keywords

Use these as metadata keywords, not a visible paper section unless required:

- multi-LLM collaboration
- LLM evaluation
- dynamic adjudication
- LLM-as-a-judge
- factuality and hallucination
- reliability visualization
- risk-aware decision support
