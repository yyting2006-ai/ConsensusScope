# ConsensusScope Deployment Guide

This guide prepares ConsensusScope for a public reviewer-facing demo. The
current hosted demo is:

```text
https://demo.consensusscope.cn/
```

The current hosted backend API is:

```text
https://api.consensusscope.cn/
https://api.consensusscope.cn/docs
```

The public demo is served by a self-hosted Streamlit process behind a
Cloudflare named tunnel. This is the preferred deployment path for review and
recording because it avoids Streamlit Community Cloud cold starts and "in the
oven" availability failures.

The app entry point is:

```text
app/streamlit_app.py
```

## Recommended Demo Mode

Use the packaged no-API mode for reviewer-facing access. The current main demo
uses synthetic ESL writing drafts, synthetic AI feedback items, AI-review stress
cases, review evidence, and deterministic routing results to demonstrate
teacher review routing.

Optional live feedback generation uses provider keys configured only in the
FastAPI service environment or its secret manager. Public users never enter a
provider key in the browser.

Never put real API keys in the paper, README, source code, Git history, or demo
video.

The current user flow uses personal accounts backed by the FastAPI service; the
older shared demo-password gate is not the main access-control mechanism. Keep
provider keys server-side and configure administrator usernames only through
deployment environment variables.

## Preferred Hosted Deployment

The production-like demo uses:

```text
demo.consensusscope.cn
  -> Cloudflare DNS
  -> Cloudflare named tunnel
  -> http://127.0.0.1:7863 on the Tencent Cloud server
  -> app/streamlit_app.py

api.consensusscope.cn
  -> Cloudflare DNS
  -> Cloudflare named tunnel
  -> http://127.0.0.1:7864 on the Tencent Cloud server
  -> backend/app.py
```

Recommended server-side services:

```text
consensusscope-demo.service
consensusscope-backend.service
consensusscope-named-tunnel.service
consensusscope-healthcheck.timer
consensusscope-daily-restart.timer
```

The health check should verify both `http://127.0.0.1:7863/` and
`https://demo.consensusscope.cn/` for the frontend, and
`http://127.0.0.1:7864/health` plus `https://api.consensusscope.cn/health` for
the backend, restarting only the ConsensusScope services when checks fail. Do
not store Cloudflare tunnel credentials, API keys, or server secrets in the
repository.

## Streamlit Community Cloud Fallback

1. Push this clean project to a GitHub repository.
2. Create a new Streamlit app from that repository.
3. Set the main file path to `app/streamlit_app.py`.
4. Keep Streamlit runtime dependencies in `requirements.txt`. Full offline
   experiment and test dependencies are kept in `requirements-dev.txt` so
   Streamlit Cloud cold starts do not install unnecessary plotting, ML, testing,
   or video-conversion packages.
5. Configure `CONSENSUS_SCOPE_BACKEND_URL` in Streamlit Secrets. The backend
   and any provider keys must be hosted separately on persistent storage.
6. Deploy and test the account and review workflows listed below.

Streamlit Community Cloud is no longer the preferred public demo host for this
submission because cold starts can make the app unavailable during review.

## Backend API Service

ConsensusScope includes a FastAPI backend for production-style deployments:

```bash
uvicorn backend.app:app --host 127.0.0.1 --port 7864
```

The backend provides accounts, courses, assignments, anonymized essay storage,
asynchronous review jobs, server-side model generation, SQLite persistence,
teacher decisions, audit logs, and report export. Configure it with:

```bash
export CONSENSUS_SCOPE_BACKEND_DB=/opt/consensusscope-demo/data/consensusscope_backend.sqlite3
export CONSENSUS_SCOPE_BACKEND_URL=https://api.consensusscope.cn
export CONSENSUS_SCOPE_CORS_ORIGINS=https://demo.consensusscope.cn
export CONSENSUS_SCOPE_ADMIN_USERNAMES=your_admin_username
export CONSENSUS_SCOPE_PUBLIC_URL=https://demo.consensusscope.cn
export CONSENSUS_SCOPE_REVIEW_WORKERS=4
```

If exposed publicly, place the API behind HTTPS and avoid storing API keys in
source code. Provider keys should be configured only through deployment secrets
or environment variables.

Optional password-reset and email-verification delivery:

```bash
export CONSENSUS_SCOPE_SMTP_HOST=smtp.example.org
export CONSENSUS_SCOPE_SMTP_PORT=587
export CONSENSUS_SCOPE_SMTP_USERNAME=mailer@example.org
export CONSENSUS_SCOPE_SMTP_PASSWORD='deployment-secret'
export CONSENSUS_SCOPE_EMAIL_FROM=mailer@example.org
export CONSENSUS_SCOPE_SMTP_STARTTLS=true
```

Do not enable `CONSENSUS_SCOPE_EXPOSE_ONE_TIME_TOKENS` outside automated tests.

## Storage Boundary

The hosted public demo uses the FastAPI backend and SQLite for users, hashed
passwords, hashed session tokens, courses, assignments, anonymized essays,
review jobs, review-session records, teacher decisions, audit logs, product
feedback, and report export. The main Streamlit app requires this account
service. Each record is scoped to its owner; users may export their data,
delete a review, or delete the account and all owned artifacts from My Account.

SQLite is appropriate for a single-process pilot deployment. Before running
multiple API workers or sustained high-concurrency traffic, migrate the store to
a managed relational database and add automated encrypted backups, retention
rules, reverse-proxy rate limiting, and operational monitoring. The API already
provides in-process request limiting plus one-time password-reset and email
verification flows; outbound delivery requires optional SMTP configuration.
The expert annotation app remains a separate research tool.

For formal data collection on Streamlit Community Cloud, export the annotation
files after each teacher session and back them up outside Streamlit Cloud. Local
container storage may be reset by the hosting platform and should not be treated
as the only copy of research data.

## Local Smoke Test

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest -q
```

Terminal 1:

```bash
uvicorn backend.app:app --host 127.0.0.1 --port 7864
```

Terminal 2:

```bash
CONSENSUS_SCOPE_BACKEND_URL=http://127.0.0.1:7864 \
streamlit run app/streamlit_app.py --server.port 8502
```

## If The Streamlit Cloud Fallback Stays "In The Oven"

1. Open the app in Streamlit Community Cloud and click **Manage app**.
2. Confirm the branch is `main` and the main file path is `app/streamlit_app.py`
   for the main demo, or `expert_annotation_app/app.py` for the annotation app.
3. Click **Reboot app**. If it still stays in the oven, use **Clear cache** and
   reboot again.
4. Check the logs. A real Python failure usually shows a traceback. Repeated
   redirects between `share.streamlit.io/-/auth/app`, `/-/login`, and the app URL
   usually indicate a Streamlit Cloud session or wake-up issue rather than a
   source-code exception.
5. If the app was created before recent dependency changes, delete and redeploy
   the Streamlit app from the same GitHub repository.

## Reviewer Smoke Checklist

- The README states the ESL writing feedback review-routing purpose.
- `ui_prototype/index.html` opens and shows the 7-page product workflow.
- The Streamlit app starts from `app/streamlit_app.py`.
- A user can register, sign out, and sign in again.
- Courses and Assignments can create an owned course, assignment, and anonymous
  essay, and can open that essay in the review workflow.
- Single Essay Review can generate, route, and persist deterministic feedback;
  configured live providers are invoked only by the backend.
- Batch Review can process a saved assignment, an uploaded CSV, or packaged
  examples through an asynchronous job.
- Teacher Queue shows the source span beside the AI suggestion and persists
  account-owned teacher actions.
- Reports exports routed feedback, a teacher audit trail, and a student-facing
  report that withholds pending or rejected feedback.
- My Account supports profile/password changes, personal data export, history
  deletion, and account deletion.
- Product Feedback saves submissions and shows the user's prior reports.
- Settings / Diagnostics is visible only to configured administrators.
- Provider credentials are never exposed in the page, API health response, or
  exported artifacts.
- The auxiliary QA and earlier feedback modules are clearly separated from the
  current main demo claim.

## Fixed Judge Protocol

The fixed judge is an optional baseline in live mode and an offline saved result
in bundled auxiliary QA files. By default it uses the `judge` provider
configuration:

```text
JUDGE_MODEL=deepseek-chat
JUDGE_BASE_URL=https://api.deepseek.com
```

The fixed judge prompt receives the sample id, dataset, task type, question,
options, and model outputs. It does not receive the gold answer or gold label.
It sees the other models' answers, rationales/reasons, confidence values,
evidence fields, and parser metadata. Saved offline results are reproducible as
artifacts, while exact reruns can vary with provider-side model/API changes.

## Privacy

Before adding real student essays, remove names, IDs, emails, demographic
details, school identifiers, and any personally identifying information. The
packaged ESL writing demo uses synthetic examples.

The backend stores submitted essay text until the user deletes the review or an
operator applies a retention policy. Keep the API behind HTTPS, restrict CORS to
the deployed frontend, protect the database and backups, and publish a clear
privacy/retention notice before classroom use.
