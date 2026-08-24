# ConsensusScope Backend API

This backend is an independent FastAPI service for the ConsensusScope ESL
writing feedback application. It provides personal accounts, private review
history, course and assignment storage, anonymized essay ingestion,
asynchronous review jobs, server-side model generation, teacher-decision
persistence, product feedback, and audit export while keeping the Streamlit
interface separate from storage and review logic.

## Run Locally

```bash
uvicorn backend.app:app --host 127.0.0.1 --port 7864
```

Open the API documentation:

```text
http://127.0.0.1:7864/docs
```

By default, SQLite data is stored at:

```text
~/.consensusscope/consensusscope_backend.sqlite3
```

To use another database file:

```bash
CONSENSUS_SCOPE_BACKEND_DB=/path/to/consensusscope.sqlite3 \
uvicorn backend.app:app --host 127.0.0.1 --port 7864
```

## Main Endpoints

- `GET /health`: backend health check.
- `POST /api/auth/register`: create an account after privacy acknowledgement.
- `POST /api/auth/login`: issue a 14-day opaque Bearer session token.
- `POST /api/auth/password-reset/request`: request a one-time reset link.
- `POST /api/auth/password-reset/confirm`: consume a reset token.
- `GET /api/auth/me`: retrieve the authenticated profile.
- `POST /api/auth/logout`: revoke the current session.
- `PATCH /api/account/profile`: update display name or optional email.
- `POST /api/account/password`: change a password and revoke all sessions.
- `POST /api/account/email-verification/request`: request an email verification link.
- `POST /api/auth/email-verification/confirm`: consume a verification token.
- `GET /api/account/summary`: retrieve personal review counts.
- `GET /api/account/export`: export all records owned by the current account.
- `DELETE /api/account`: permanently delete the account and owned records.
- `GET/POST /api/courses`: list or create courses.
- `GET/POST /api/assignments`: list or create assignments.
- `GET/POST /api/essays`: list or store anonymized essays.
- `POST /api/essays/batch`: validate and store a CSV-style essay batch.
- `POST /api/privacy/check`: check text for likely PII before storage.
- `POST /api/review/jobs`: enqueue a single-essay review job.
- `POST /api/review/jobs/batch`: enqueue a batch review job.
- `GET /api/review/jobs`: list recent jobs.
- `GET /api/review/jobs/{job_id}`: retrieve job progress and output IDs.
- `POST /api/review/single`: review one ESL essay and store the review session.
- `POST /api/review/batch`: review multiple essays and store a batch of sessions.
- `GET /api/sessions`: list recent review sessions.
- `GET /api/sessions/{session_id}`: retrieve one stored session.
- `GET /api/sessions/{session_id}/feedback`: retrieve feedback items for a session.
- `DELETE /api/sessions/{session_id}`: delete an owned review and its related records.
- `POST /api/teacher/decision`: save or update a teacher decision for one feedback item.
- `GET /api/teacher/decisions`: list teacher decisions.
- `GET /api/export/report/{session_id}`: export the generated text report.
- `GET /api/export/student-report/{session_id}`: export only feedback released to students.
- `GET /api/audit/logs`: inspect backend audit events.
- `POST /api/feedback`: submit product feedback.
- `GET /api/feedback/mine`: list the current user's feedback.
- `GET /api/admin/feedback`: list all feedback for configured administrators.

Except for `/health`, registration, and login, all endpoints require:

```text
Authorization: Bearer <session-token>
```

Passwords are stored as PBKDF2-HMAC-SHA256 hashes with random salts. Raw
session tokens are returned once to the client; the database stores only their
SHA-256 hashes. Review, decision, report, and audit queries are scoped to the
authenticated user.

## Deployment Configuration

```bash
export CONSENSUS_SCOPE_BACKEND_DB=/path/to/consensusscope.sqlite3
export CONSENSUS_SCOPE_CORS_ORIGINS=https://demo.consensusscope.cn
export CONSENSUS_SCOPE_ADMIN_USERNAMES=your_admin_username
export CONSENSUS_SCOPE_PUBLIC_URL=https://demo.consensusscope.cn
export CONSENSUS_SCOPE_REVIEW_WORKERS=4
```

Optional live providers are configured with backend-only variables such as
`DEEPSEEK_API_KEY`, `QWEN_API_KEY`, `GLM_API_KEY`, `KIMI_API_KEY`, or
`OPENAI_API_KEY`. Keys are not accepted from or returned to browser clients.
Optional email delivery uses the `CONSENSUS_SCOPE_SMTP_*` variables shown in
`.env.example`; without SMTP, reset and verification requests return a neutral
response but cannot deliver a link.

SQLite uses WAL mode and is intended for one API process during the current
pilot. Use a managed relational database before multi-process or sustained
high-concurrency deployment. Public endpoints are rate limited in process;
production deployments should also enforce limits at the reverse proxy. Before
real classroom operation, add encrypted backups, a documented retention policy,
institution-approved data handling, and operational monitoring.
