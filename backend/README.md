# ConsensusScope Backend API

This backend is an independent FastAPI service for the ConsensusScope ESL
writing feedback demo. It keeps the Streamlit interface separate from review
logic, persistence, teacher decisions, and audit export.

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
- `POST /api/review/single`: review one ESL essay and store the review session.
- `POST /api/review/batch`: review multiple essays and store a batch of sessions.
- `GET /api/sessions`: list recent review sessions.
- `GET /api/sessions/{session_id}`: retrieve one stored session.
- `GET /api/sessions/{session_id}/feedback`: retrieve feedback items for a session.
- `POST /api/teacher/decision`: save or update a teacher decision for one feedback item.
- `GET /api/teacher/decisions`: list teacher decisions.
- `GET /api/export/report/{session_id}`: export the generated text report.
- `GET /api/audit/logs`: inspect backend audit events.

This backend does not store API keys. If model providers are added later, keys
must be supplied through deployment secrets or environment variables.
