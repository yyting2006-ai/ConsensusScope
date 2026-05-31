# Ethics and Limitations

ConsensusScope is designed as a reliability-observability and review-routing
tool. It should not be presented as a truth oracle, automatic grader or final
decision maker.

## Intended Use

- Inspect multi-LLM decision traces.
- Identify false consensus, high disagreement and minority-correct warnings.
- Route uncertain cases to evidence checking or human review.
- Support research on LLM reliability, fact verification and educational
  feedback auditing.

## Out-of-Scope Use

- Fully automated high-stakes decision-making.
- Replacing teachers, reviewers, fact checkers or domain experts.
- Ranking students or users without human oversight.
- Treating model rationales as verified evidence.

## Data Privacy

The current public-demo path should use only open benchmark samples or
anonymized examples. If educational writing data is added later:

- Remove names, student IDs, email addresses and classroom identifiers.
- Replace rare personal details with placeholders.
- Store human annotations separately from identifiable student records.
- Report aggregate results unless explicit consent permits case-level excerpts.

## Model Output Risks

Model answers may contain hallucinations, unsupported reasoning, biased
assumptions or misleading confidence scores. ConsensusScope exposes these
signals for inspection, but the system itself can also misclassify risk levels.
All exported reports should therefore be treated as audit material rather than
ground truth.

## Current Limitations

- The current demo uses saved outputs from four LLM providers and 1000
  adjudicated samples.
- Discussion-round traces are not yet fully represented.
- Evidence support is still a lightweight feature, not a complete retrieval or
  citation-verification module.
- Risk labels are derived from gold labels and model outputs; future work should
  include independent human validation.

