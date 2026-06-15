# Demo Stability Checklist

Use this checklist before recording the final EMNLP demo video or submitting the
system URL.

## Public URL

- Main demo URL: https://demo.consensusscope.cn/
- The main demo is self-hosted behind a Cloudflare named tunnel, not Streamlit
  Community Cloud.
- Confirm the public URL returns HTTP 200 and the Streamlit interface loads in
  a normal browser session.
- Server-side health checks should monitor both `http://127.0.0.1:7863/` and
  `https://demo.consensusscope.cn/`.

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
