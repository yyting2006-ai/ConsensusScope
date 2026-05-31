# Release Checklist

This checklist turns the local prototype into a submission-ready demo package.

## Repository

- [x] English README: `README_EN.md`
- [x] License: `LICENSE`
- [x] No-API local demo data included
- [x] Experiment report included
- [x] Casebook included
- [x] EMNLP demo paper draft included
- [x] Video script included
- [x] Ethics and limitations note included
- [x] Public release notes included
- [ ] Public or anonymous repository URL
- [ ] Remove private `.env` before public release
- [ ] Confirm no personal phone numbers, emails or student identifiers are in public files

## Demo

- [x] Streamlit app starts locally
- [x] Single-sample analysis page
- [x] Overview statistics page
- [x] Report export page
- [x] Screenshot generation script
- [x] English submission interface: `app/streamlit_app.py`
- [x] English screenshots: `docs/screenshots_en/`
- [ ] Final narrated demo video URL under 2.5 minutes

## Paper

- [x] Six-page demo-paper draft scaffold
- [x] BibTeX file
- [x] System description
- [x] Evaluation snapshot
- [x] Ethics and limitations section
- [ ] Convert to official ACL style files
- [ ] Add final screenshots to the paper
- [ ] Add anonymous demo URL if required by the submission system

## Before Public Upload

1. Delete `.env` or replace it with `.env.example`.
2. Confirm provider API keys are absent from logs.
3. Confirm educational data, if added later, is anonymized.
4. Keep only a small no-API sample package if repository size becomes too large.
5. Add a short model/data card if the dataset package is shared publicly.
