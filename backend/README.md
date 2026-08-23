# ConsensusScope Backend API

This backend is an independent FastAPI service for the ConsensusScope ESL
writing feedback application. It provides personal accounts, private review
history, teacher-decision persistence, product feedback, and audit export while
keeping the Streamlit interface separate from storage and review logic.

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
- `GET /api/auth/me`: retrieve the authenticated profile.
- `POST /api/auth/logout`: revoke the current session.
- `PATCH /api/account/profile`: update display name or optional email.
- `POST /api/account/password`: change a password and revoke all sessions.
- `GET /api/account/summary`: retrieve personal review counts.
- `POST /api/review/single`: review one ESL essay and store the review session.
- `POST /api/review/batch`: review multiple essays and store a batch of sessions.
- `GET /api/sessions`: list recent review sessions.
- `GET /api/sessions/{session_id}`: retrieve one stored session.
- `GET /api/sessions/{session_id}/feedback`: retrieve feedback items for a session.
- `DELETE /api/sessions/{session_id}`: delete an owned review and its related records.
- `POST /api/teacher/decision`: save or update a teacher decision for one feedback item.
- `GET /api/teacher/decisions`: list teacher decisions.
- `GET /api/export/report/{session_id}`: export the generated text report.
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
```

SQLite is intended for one API process during the current pilot. Use a managed
relational database before multi-worker or high-concurrency deployment. Add
rate limiting, password reset, email verification, encrypted backups, and a
documented data-retention policy before real classroom operation.

This backend does not store API keys. If model providers are added later, keys
must be supplied through deployment secrets or environment variables.
