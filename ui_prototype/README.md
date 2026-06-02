# ConsensusScope UI Prototype

Designer-facing static prototype for the ESL feedback review workflow.

This prototype is not a production system and does not call LLM APIs. It uses
mock data only and can be opened directly from `index.html`.

## How To Open

Double-click:

```text
ui_prototype/index.html
```

Or run a local static server:

```bash
cd ui_prototype
python3 -m http.server 8080
```

Then open:

```text
http://localhost:8080
```

No `npm install` is required.

## Purpose

This prototype shows the intended product workflow for:

> ConsensusScope: An Interactive Review-Routing Tool for Safe AI Feedback on ESL Writing

The core teacher-facing question is:

> Can this AI feedback be safely shown to the student, or should a teacher review it first?

## Pages

1. Review Workspace
2. Essay Review
3. Feedback Detail
4. Teacher Queue
5. Writing Rubric
6. Reports
7. Settings / Diagnostics

## Frozen Core Workflow

Review Workspace -> Essay Review -> Feedback Detail -> Teacher Queue -> Reports

## Frozen Data Objects

- `ReviewSession`
- `FeedbackItem`
- `ReviewEvidence`
- `TeacherAction`
- `RoutingSummary`

## Designers Should Improve

- Visual style
- Typography
- Spacing
- Component polish
- Iconography
- Figma component variants

## Designers Should Avoid Changing

- Core page structure
- Data objects
- Teacher workflow
- Risk levels
- Action states

## Notes

- Visible UI text is English for EMNLP-style demo use.
- No real student names, IDs, emails, class identifiers, or PII are included.
- Settings / Diagnostics keeps technical material secondary.
- The auxiliary QA reliability module is explicitly marked as auxiliary and is
  not the main ESL feedback workflow.
