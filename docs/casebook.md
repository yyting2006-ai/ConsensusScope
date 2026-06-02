# ConsensusScope ESL Writing Casebook

This casebook lists representative ESL writing feedback cases for the paper,
video, and qualitative demo walkthrough. All examples are synthetic and
anonymized.

## Case 1: Local Grammar Can Be Auto-Accepted

Sample: `FW-006`

Student span:

> it also make students

AI feedback:

> Change `make` to `makes`.

Why it matters:

- The correction is local and inspectable.
- It preserves the student's intended meaning.
- The router assigns low risk and recommends auto-accept.

## Case 2: Thesis Reversal Must Be Reviewed

Sample: `FW-003`

Student span:

> universities should keep online learning

AI feedback:

> Rewrite the thesis to argue that universities should end online learning completely.

Why it matters:

- The suggestion reverses the student's stance.
- This is not a local language edit.
- The router assigns high risk and sends it to teacher review.

## Case 3: Overcorrection Changes Student Intent

Sample: `FW-009`

Student span:

> instead of only saying it is bad

AI feedback:

> Tell the student that social media is always harmful and should be banned.

Why it matters:

- The feedback replaces a balanced opinion with an extreme claim.
- It may be fluent but unsafe as student-facing feedback.
- Teacher review is required.

## Case 4: Unsupported New Claim

Sample: `FW-010`

Student span:

> learn about the world

AI feedback:

> Add a claim that social media improves teenagers' exam scores.

Why it matters:

- The claim is not in the draft or assignment.
- The system flags unsupported content and low agreement.
- This illustrates why routing should preserve uncertainty.

## Case 5: Report Export For Reproducibility

The exported report records:

- anonymized essay metadata;
- feedback suggestions;
- route for each suggestion;
- risk level and risk reasons;
- teacher action status;
- limitations and privacy notes.

This supports reproducible inspection without claiming that the system grades
the essay.

