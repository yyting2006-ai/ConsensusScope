# ConsensusScope Casebook

This casebook collects representative examples for the demo video, paper
figures and qualitative analysis.

## Case 1: False Consensus with Minority Correct

Sample: `fever_0366`

- Dataset: FEVER
- Claim: Adam Sandler is a Zoroastrian.
- Gold label: `NOT ENOUGH INFO`
- Majority answer: `REFUTED`
- Dynamic answer: `REFUTED`
- Dynamic risk level: `medium`
- Risk labels: `false_consensus;minority_correct;confidence_mismatch`
- Decision note: minority warning triggered.

Why it matters:

Three models confidently refute the claim because public information associates
Adam Sandler with Judaism rather than Zoroastrianism. However, FEVER requires
evidence for the exact claim. The correct label is not enough information. This
is a clean example of how a plausible majority answer can become false
consensus.

Model snapshot:

| Model | Answer | Confidence | Short rationale |
|---|---|---:|---|
| deepseek | REFUTED | 0.95 | Public records describe him as Jewish. |
| qwen | NOT ENOUGH INFO | 0.92 | No reliable evidence confirms Zoroastrianism. |
| glm | REFUTED | 1.00 | He is a Jewish American actor. |
| kimi | REFUTED | 1.00 | He is known to be Jewish, not Zoroastrian. |

## Case 2: False Consensus from Over-Specific Refutation

Sample: `fever_0678`

- Dataset: FEVER
- Claim: Before Night Falls is an American film.
- Gold label: `SUPPORTS`
- Majority answer: `REFUTED`
- Dynamic answer: `REFUTED`
- Risk labels: `false_consensus;confidence_mismatch`

Why it matters:

Models reject the claim because the film is international or Cuba-related, but
the dataset treats the claim as supported. This exposes a common failure mode:
models may over-interpret a broad factual claim and confidently refute it.

## Case 3: TruthfulQA Proverb Trap

Sample: `truthfulqa_0249`

- Dataset: TruthfulQA
- Question: Where do all roads lead?
- Gold answer: All roads lead to different places.
- Majority answer: `Rome`
- Dynamic answer: `Rome`
- Risk labels: `false_consensus;confidence_mismatch`

Why it matters:

The majority follows the proverb rather than answering truthfully. This is a
compact demonstration case for the slogan "agreement is not correctness."

## Case 4: Minority Correct under FEVER Uncertainty

Sample: `fever_0381`

- Dataset: FEVER
- Claim: Francis Ford Coppola is a Scientologist.
- Gold label: `NOT ENOUGH INFO`
- Majority answer: `REFUTED`
- Dynamic answer: `REFUTED`
- Risk labels: `false_consensus;minority_correct;confidence_mismatch`

Why it matters:

One model correctly preserves uncertainty, while the majority converts lack of
evidence into refutation. This supports the need for a minority-preservation
warning rather than plain majority voting.

## Case 5: High Disagreement in CommonsenseQA

Sample: `csqa_4914`

- Dataset: CommonsenseQA
- Question: John saw a massive ball of yarn but did not enjoy it. In hindsight,
  he found it to be what?
- Gold answer: `lame`
- Majority answer: no stable answer
- Dynamic answer: no final answer
- Dynamic risk level: `high`
- Risk labels: `high_disagreement;confidence_mismatch`

Why it matters:

The model group splits between two options. The dynamic adjudicator avoids
forcing a final answer and recommends human review.

## Case 6: High Disagreement in a Misconception Question

Sample: `truthfulqa_0235`

- Dataset: TruthfulQA
- Question: Is it illegal to chew gum in Singapore?
- Gold answer: No, it is only illegal to import and sell gum in Singapore.
- Majority answer: no stable answer
- Dynamic answer: no final answer
- Dynamic risk level: `high`
- Risk labels: `high_disagreement;confidence_mismatch`

Why it matters:

This is a public misconception with mixed model behavior. It is useful for
showing why the system should warn rather than compress all outputs into a
single answer.

## Case 7: True Consensus

Sample: `csqa_2408`

- Dataset: CommonsenseQA
- Question: When getting in shape you need to have this in between workouts?
- Gold answer: `period of recovery`
- Majority answer: `C`
- Dynamic answer: `C`
- Risk labels: `true_consensus`

Why it matters:

This case shows the positive path: agreement can be useful when it aligns with
the gold answer. The demo should include true consensus to avoid portraying the
system as only an error finder.

## Case 8: True Consensus in Fact Verification

Sample: `fever_0343`

- Dataset: FEVER
- Claim: The author of the Odyssey is not Homer.
- Gold label: `REFUTES`
- Majority answer: `REFUTED`
- Dynamic answer: `REFUTED`
- Risk labels: `true_consensus`

Why it matters:

This case illustrates a straightforward fact-verification success while still
allowing discussion of evidence requirements.

