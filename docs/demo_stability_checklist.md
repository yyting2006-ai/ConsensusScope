# Demo Stability Checklist

Use this checklist before recording the final EMNLP demo video or submitting the
system URL.

## Public URL

- Main demo URL: https://consensusscope-fzebywc3is3tducktjuvup.streamlit.app/
- Expert annotation URL: https://consensusscope-uvsncgyjiswi6f2qpjzvq3.streamlit.app/
- Confirm both apps load in a logged-in browser session.
- If Streamlit shows "Your app is in the oven" for more than 10 minutes, open
  Manage app, inspect logs, and reboot the app.

## Local Fallback

Run the main demo locally:

```bash
streamlit run app/streamlit_app.py --server.port 8502
```

Run the expert annotation app locally:

```bash
streamlit run expert_annotation_app/app.py --server.port 8503
```

Expected health check:

```text
/_stcore/health -> ok
```

## Video Path

Record the main demo path:

```text
Review Workspace -> Single Essay Review -> Feedback Detail -> Teacher Queue -> Effectiveness Evaluation -> Reports
```

Show four concrete cases:

- low-risk local edit accepted;
- meaning-changing feedback routed to review;
- unsupported claim routed to review;
- teacher-dependent borderline feedback routed to review.

## Submission Boundary

- Do not claim classroom effectiveness.
- Do not claim automatic essay scoring.
- Do not claim that teacher ratings are available at deploy time.
- Do report the two-teacher pilot as a preliminary offline diagnostic.
