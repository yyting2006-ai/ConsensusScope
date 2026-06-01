# ConsensusScope ESL Casebook

This casebook lists representative ESL comparative-literature feedback cases
for the paper, video, and qualitative demo walkthrough.

## Case 1: Grammar Can Be Local, Facts Need Review

Sample: `lit_esl_001`

Student excerpt:

> Mary Shelley write Frankenstein in 1847, and Jane Austen wrote Jane Eyre.
> Both novels shows how women are trapped by society.

Why it matters:

- `write` to `wrote` and `shows` to `show` are low-risk local grammar edits.
- The publication year of *Frankenstein* and the authorship of *Jane Eyre* are
  literary-fact issues that should remain teacher-reviewable.
- KG evidence supports the review by showing *Frankenstein* as a Mary Shelley
  work conventionally dated to 1818.

## Case 2: Character Confusion With Interpretation Risk

Sample: `lit_esl_002`

Student excerpt:

> The monster is Victor Frankenstein, so the novel proves that people should
> never study knowledge.

Why it matters:

- The KG can flag central-character confusion.
- The broad interpretive rewrite changes the student's argument and should not
  be auto-applied.
- This demonstrates why ConsensusScope routes factual and interpretation-level
  feedback to teacher review.

## Case 3: Academic Style Without Overwriting Meaning

Sample: `lit_esl_003`

Student excerpt:

> In comparison, the two books are same because both main characters want
> freedom.

Why it matters:

- The sentence needs academic phrasing.
- A model may over-specify the comparison and change the student's intended
  contrast.
- The teacher queue keeps style suggestions inspectable.

## Case 4: Genre And Publication-Year Evidence

Sample: `lit_esl_012`

Why it matters:

- Genre and publication-year suggestions can be checked against KG triples.
- Knowledge support is useful evidence, but it does not automatically make a
  suggestion pedagogically appropriate.
- Teacher review remains the safer route for fact-linked feedback.

## Case 5: Report Export For Reproducibility

The exported Markdown report records:

- original student excerpt;
- retrieved KG evidence;
- feedback suggestions;
- selected decision for each suggestion group;
- auto-accept versus teacher-review routing;
- rationale for teacher review.

This supports reproducible inspection without claiming that the system grades
the essay.
