from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_db_path() -> Path:
    return Path.home() / ".consensusscope" / "consensusscope_backend.sqlite3"


def dumps_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def loads_json(value: Optional[str]) -> Any:
    if not value:
        return None
    return json.loads(value)


class BackendStore:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS review_sessions (
                    session_id TEXT PRIMARY KEY,
                    batch_id TEXT,
                    essay_id TEXT NOT NULL,
                    assignment_prompt TEXT NOT NULL,
                    student_level TEXT NOT NULL,
                    essay_text TEXT NOT NULL,
                    include_stress_tests INTEGER NOT NULL DEFAULT 0,
                    summary_json TEXT NOT NULL,
                    comparison_json TEXT NOT NULL,
                    report_text TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS feedback_items (
                    session_id TEXT NOT NULL,
                    feedback_item_id TEXT NOT NULL,
                    essay_id TEXT NOT NULL,
                    risk_level TEXT,
                    recommended_action TEXT,
                    risk_score REAL,
                    review_priority TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (session_id, feedback_item_id),
                    FOREIGN KEY (session_id) REFERENCES review_sessions(session_id)
                );

                CREATE TABLE IF NOT EXISTS teacher_decisions (
                    decision_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    feedback_item_id TEXT NOT NULL,
                    teacher_id TEXT NOT NULL,
                    teacher_action TEXT NOT NULL,
                    teacher_corrected_feedback TEXT,
                    teacher_reason TEXT,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES review_sessions(session_id)
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    log_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_feedback_session
                    ON feedback_items(session_id);
                CREATE INDEX IF NOT EXISTS idx_decisions_session
                    ON teacher_decisions(session_id);
                CREATE INDEX IF NOT EXISTS idx_logs_session
                    ON audit_logs(session_id);
                """
            )

    def save_review_session(
        self,
        *,
        session_id: str,
        batch_id: Optional[str],
        essay_id: str,
        assignment_prompt: str,
        student_level: str,
        essay_text: str,
        include_stress_tests: bool,
        summary: Dict[str, Any],
        comparison: List[Dict[str, Any]],
        report: str,
        feedback_items: Iterable[Dict[str, Any]],
    ) -> None:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO review_sessions (
                    session_id, batch_id, essay_id, assignment_prompt, student_level,
                    essay_text, include_stress_tests, summary_json, comparison_json,
                    report_text, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(
                    (SELECT created_at FROM review_sessions WHERE session_id = ?), ?
                ), ?)
                """,
                (
                    session_id,
                    batch_id,
                    essay_id,
                    assignment_prompt,
                    student_level,
                    essay_text,
                    int(include_stress_tests),
                    dumps_json(summary),
                    dumps_json(comparison),
                    report,
                    session_id,
                    now,
                    now,
                ),
            )
            conn.execute("DELETE FROM feedback_items WHERE session_id = ?", (session_id,))
            for item in feedback_items:
                conn.execute(
                    """
                    INSERT INTO feedback_items (
                        session_id, feedback_item_id, essay_id, risk_level,
                        recommended_action, risk_score, review_priority,
                        payload_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        str(item.get("feedback_item_id", "")),
                        essay_id,
                        item.get("risk_level"),
                        item.get("recommended_action"),
                        item.get("risk_score"),
                        item.get("review_priority"),
                        dumps_json(item),
                        now,
                    ),
                )
            self._log_with_conn(
                conn,
                session_id=session_id,
                event_type="review_session_saved",
                payload={"essay_id": essay_id, "batch_id": batch_id},
            )

    def save_teacher_decision(
        self,
        *,
        session_id: str,
        feedback_item_id: str,
        teacher_id: str,
        teacher_action: str,
        teacher_corrected_feedback: Optional[str],
        teacher_reason: Optional[str],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        now = utc_now()
        decision_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{session_id}:{feedback_item_id}:{teacher_id}"))
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO teacher_decisions (
                    decision_id, session_id, feedback_item_id, teacher_id,
                    teacher_action, teacher_corrected_feedback, teacher_reason,
                    metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE(
                    (SELECT created_at FROM teacher_decisions WHERE decision_id = ?), ?
                ), ?)
                ON CONFLICT(decision_id) DO UPDATE SET
                    teacher_action = excluded.teacher_action,
                    teacher_corrected_feedback = excluded.teacher_corrected_feedback,
                    teacher_reason = excluded.teacher_reason,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                (
                    decision_id,
                    session_id,
                    feedback_item_id,
                    teacher_id,
                    teacher_action,
                    teacher_corrected_feedback,
                    teacher_reason,
                    dumps_json(metadata),
                    decision_id,
                    now,
                    now,
                ),
            )
            self._log_with_conn(
                conn,
                session_id=session_id,
                event_type="teacher_decision_saved",
                payload={
                    "feedback_item_id": feedback_item_id,
                    "teacher_id": teacher_id,
                    "teacher_action": teacher_action,
                },
            )
        return self.get_teacher_decision(decision_id) or {}

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM review_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["include_stress_tests"] = bool(data["include_stress_tests"])
        data["summary"] = loads_json(data.pop("summary_json"))
        data["comparison"] = loads_json(data.pop("comparison_json"))
        return data

    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM review_sessions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        sessions = []
        for row in rows:
            data = dict(row)
            data["include_stress_tests"] = bool(data["include_stress_tests"])
            data["summary"] = loads_json(data.pop("summary_json"))
            data["comparison"] = loads_json(data.pop("comparison_json"))
            sessions.append(data)
        return sessions

    def get_feedback_items(self, session_id: str) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json FROM feedback_items
                WHERE session_id = ?
                ORDER BY feedback_item_id
                """,
                (session_id,),
            ).fetchall()
        return [loads_json(row["payload_json"]) for row in rows]

    def list_teacher_decisions(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM teacher_decisions"
        params: tuple[Any, ...] = ()
        if session_id:
            query += " WHERE session_id = ?"
            params = (session_id,)
        query += " ORDER BY updated_at DESC"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        decisions = []
        for row in rows:
            data = dict(row)
            data["metadata"] = loads_json(data.pop("metadata_json")) or {}
            decisions.append(data)
        return decisions

    def get_teacher_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM teacher_decisions WHERE decision_id = ?",
                (decision_id,),
            ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["metadata"] = loads_json(data.pop("metadata_json")) or {}
        return data

    def list_audit_logs(self, session_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        query = "SELECT * FROM audit_logs"
        params: tuple[Any, ...]
        if session_id:
            query += " WHERE session_id = ?"
            params = (session_id, limit)
        else:
            params = (limit,)
        query += " ORDER BY created_at DESC LIMIT ?"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        logs = []
        for row in rows:
            data = dict(row)
            data["payload"] = loads_json(data.pop("payload_json")) or {}
            logs.append(data)
        return logs

    def _log_with_conn(
        self,
        conn: sqlite3.Connection,
        *,
        session_id: Optional[str],
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        conn.execute(
            """
            INSERT INTO audit_logs (log_id, session_id, event_type, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), session_id, event_type, dumps_json(payload), utc_now()),
        )
