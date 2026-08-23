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
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    display_name TEXT NOT NULL DEFAULT '',
                    email TEXT UNIQUE,
                    privacy_acknowledged_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_login_at TEXT
                );

                CREATE TABLE IF NOT EXISTS auth_sessions (
                    session_token_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS review_sessions (
                    session_id TEXT PRIMARY KEY,
                    owner_user_id TEXT,
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
                    owner_user_id TEXT,
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

                CREATE TABLE IF NOT EXISTS product_feedback (
                    feedback_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    page TEXT,
                    allow_contact INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'new',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_feedback_session
                    ON feedback_items(session_id);
                CREATE INDEX IF NOT EXISTS idx_decisions_session
                    ON teacher_decisions(session_id);
                CREATE INDEX IF NOT EXISTS idx_logs_session
                    ON audit_logs(session_id);
                CREATE INDEX IF NOT EXISTS idx_auth_sessions_user
                    ON auth_sessions(user_id, expires_at);
                CREATE INDEX IF NOT EXISTS idx_product_feedback_user
                    ON product_feedback(user_id, created_at);
                """
            )
            self._ensure_column(conn, "review_sessions", "owner_user_id", "TEXT")
            self._ensure_column(conn, "teacher_decisions", "owner_user_id", "TEXT")
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sessions_owner
                ON review_sessions(owner_user_id, created_at)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_decisions_owner
                ON teacher_decisions(owner_user_id, updated_at)
                """
            )

    @staticmethod
    def _ensure_column(
        conn: sqlite3.Connection,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        existing = {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def create_user(
        self,
        *,
        username: str,
        password_hash: str,
        display_name: str,
        email: Optional[str],
    ) -> Dict[str, Any]:
        now = utc_now()
        user_id = f"usr-{uuid.uuid4().hex}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO users (
                    user_id, username, password_hash, display_name, email,
                    privacy_acknowledged_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, username, password_hash, display_name, email, now, now, now),
            )
        return self.get_user(user_id) or {}

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        return dict(row) if row else None

    def update_user_profile(
        self,
        *,
        user_id: str,
        display_name: str,
        email: Optional[str],
    ) -> Dict[str, Any]:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET display_name = ?, email = ?, updated_at = ?
                WHERE user_id = ?
                """,
                (display_name, email, now, user_id),
            )
        return self.get_user(user_id) or {}

    def update_password(self, *, user_id: str, password_hash: str) -> None:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE users SET password_hash = ?, updated_at = ? WHERE user_id = ?
                """,
                (password_hash, now, user_id),
            )
            conn.execute("DELETE FROM auth_sessions WHERE user_id = ?", (user_id,))

    def mark_user_login(self, user_id: str) -> None:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                "UPDATE users SET last_login_at = ?, updated_at = ? WHERE user_id = ?",
                (now, now, user_id),
            )

    def create_auth_session(
        self,
        *,
        user_id: str,
        token_hash: str,
        expires_at: str,
    ) -> None:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO auth_sessions (
                    session_token_hash, user_id, expires_at, created_at, last_seen_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (token_hash, user_id, expires_at, now, now),
            )

    def get_user_for_session(self, token_hash: str) -> Optional[Dict[str, Any]]:
        now = utc_now()
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT users.*
                FROM auth_sessions
                JOIN users ON users.user_id = auth_sessions.user_id
                WHERE auth_sessions.session_token_hash = ?
                  AND auth_sessions.expires_at > ?
                """,
                (token_hash, now),
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE auth_sessions SET last_seen_at = ? WHERE session_token_hash = ?",
                    (now, token_hash),
                )
        return dict(row) if row else None

    def delete_auth_session(self, token_hash: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM auth_sessions WHERE session_token_hash = ?",
                (token_hash,),
            )

    def delete_expired_auth_sessions(self) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (utc_now(),))

    def save_review_session(
        self,
        *,
        owner_user_id: str,
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
                    session_id, owner_user_id, batch_id, essay_id, assignment_prompt, student_level,
                    essay_text, include_stress_tests, summary_json, comparison_json,
                    report_text, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(
                    (SELECT created_at FROM review_sessions WHERE session_id = ?), ?
                ), ?)
                """,
                (
                    session_id,
                    owner_user_id,
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
        owner_user_id: str,
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
                    decision_id, owner_user_id, session_id, feedback_item_id, teacher_id,
                    teacher_action, teacher_corrected_feedback, teacher_reason,
                    metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(
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
                    owner_user_id,
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
        return self.get_teacher_decision(decision_id, owner_user_id=owner_user_id) or {}

    def get_session(self, session_id: str, *, owner_user_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM review_sessions
                WHERE session_id = ? AND owner_user_id = ?
                """,
                (session_id, owner_user_id),
            ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["include_stress_tests"] = bool(data["include_stress_tests"])
        data["summary"] = loads_json(data.pop("summary_json"))
        data["comparison"] = loads_json(data.pop("comparison_json"))
        return data

    def list_sessions(self, *, owner_user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT session_id, batch_id, essay_id, assignment_prompt, student_level,
                       include_stress_tests, summary_json, created_at, updated_at
                FROM review_sessions
                WHERE owner_user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (owner_user_id, limit),
            ).fetchall()
        sessions = []
        for row in rows:
            data = dict(row)
            data["include_stress_tests"] = bool(data["include_stress_tests"])
            data["summary"] = loads_json(data.pop("summary_json"))
            sessions.append(data)
        return sessions

    def get_feedback_items(self, session_id: str, *, owner_user_id: str) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT feedback_items.payload_json
                FROM feedback_items
                JOIN review_sessions
                  ON review_sessions.session_id = feedback_items.session_id
                WHERE feedback_items.session_id = ?
                  AND review_sessions.owner_user_id = ?
                ORDER BY feedback_items.feedback_item_id
                """,
                (session_id, owner_user_id),
            ).fetchall()
        return [loads_json(row["payload_json"]) for row in rows]

    def delete_session(self, session_id: str, *, owner_user_id: str) -> bool:
        with self.connect() as conn:
            owned = conn.execute(
                """
                SELECT 1 FROM review_sessions
                WHERE session_id = ? AND owner_user_id = ?
                """,
                (session_id, owner_user_id),
            ).fetchone()
            if not owned:
                return False
            conn.execute(
                "DELETE FROM teacher_decisions WHERE session_id = ? AND owner_user_id = ?",
                (session_id, owner_user_id),
            )
            conn.execute("DELETE FROM audit_logs WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM feedback_items WHERE session_id = ?", (session_id,))
            conn.execute(
                "DELETE FROM review_sessions WHERE session_id = ? AND owner_user_id = ?",
                (session_id, owner_user_id),
            )
        return True

    def list_teacher_decisions(
        self,
        *,
        owner_user_id: str,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM teacher_decisions WHERE owner_user_id = ?"
        params: tuple[Any, ...] = (owner_user_id,)
        if session_id:
            query += " AND session_id = ?"
            params = (owner_user_id, session_id)
        query += " ORDER BY updated_at DESC"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        decisions = []
        for row in rows:
            data = dict(row)
            data["metadata"] = loads_json(data.pop("metadata_json")) or {}
            decisions.append(data)
        return decisions

    def get_teacher_decision(
        self,
        decision_id: str,
        *,
        owner_user_id: str,
    ) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM teacher_decisions
                WHERE decision_id = ? AND owner_user_id = ?
                """,
                (decision_id, owner_user_id),
            ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["metadata"] = loads_json(data.pop("metadata_json")) or {}
        return data

    def list_audit_logs(
        self,
        *,
        owner_user_id: str,
        session_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        query = (
            "SELECT audit_logs.* FROM audit_logs "
            "JOIN review_sessions ON review_sessions.session_id = audit_logs.session_id "
            "WHERE review_sessions.owner_user_id = ?"
        )
        params: tuple[Any, ...]
        if session_id:
            query += " AND audit_logs.session_id = ?"
            params = (owner_user_id, session_id, limit)
        else:
            params = (owner_user_id, limit)
        query += " ORDER BY audit_logs.created_at DESC LIMIT ?"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        logs = []
        for row in rows:
            data = dict(row)
            data["payload"] = loads_json(data.pop("payload_json")) or {}
            logs.append(data)
        return logs

    def account_summary(self, *, owner_user_id: str) -> Dict[str, int]:
        with self.connect() as conn:
            session_count = conn.execute(
                "SELECT COUNT(*) FROM review_sessions WHERE owner_user_id = ?",
                (owner_user_id,),
            ).fetchone()[0]
            feedback_count = conn.execute(
                """
                SELECT COUNT(*)
                FROM feedback_items
                JOIN review_sessions
                  ON review_sessions.session_id = feedback_items.session_id
                WHERE review_sessions.owner_user_id = ?
                """,
                (owner_user_id,),
            ).fetchone()[0]
            auto_accepted = conn.execute(
                """
                SELECT COUNT(*)
                FROM feedback_items
                JOIN review_sessions
                  ON review_sessions.session_id = feedback_items.session_id
                WHERE review_sessions.owner_user_id = ?
                  AND feedback_items.recommended_action = 'auto_accept'
                """,
                (owner_user_id,),
            ).fetchone()[0]
            review_routed = conn.execute(
                """
                SELECT COUNT(*)
                FROM feedback_items
                JOIN review_sessions
                  ON review_sessions.session_id = feedback_items.session_id
                WHERE review_sessions.owner_user_id = ?
                  AND feedback_items.recommended_action != 'auto_accept'
                """,
                (owner_user_id,),
            ).fetchone()[0]
            decision_count = conn.execute(
                "SELECT COUNT(*) FROM teacher_decisions WHERE owner_user_id = ?",
                (owner_user_id,),
            ).fetchone()[0]
        return {
            "review_sessions": int(session_count),
            "feedback_items": int(feedback_count),
            "auto_accepted": int(auto_accepted),
            "review_routed": int(review_routed),
            "teacher_decisions": int(decision_count),
        }

    def save_product_feedback(
        self,
        *,
        user_id: str,
        category: str,
        rating: int,
        message: str,
        page: Optional[str],
        allow_contact: bool,
    ) -> Dict[str, Any]:
        now = utc_now()
        feedback_id = f"fbk-{uuid.uuid4().hex}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO product_feedback (
                    feedback_id, user_id, category, rating, message, page,
                    allow_contact, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'new', ?, ?)
                """,
                (
                    feedback_id,
                    user_id,
                    category,
                    rating,
                    message,
                    page,
                    int(allow_contact),
                    now,
                    now,
                ),
            )
        rows = self.list_product_feedback(user_id=user_id, feedback_id=feedback_id)
        return rows[0] if rows else {}

    def list_product_feedback(
        self,
        *,
        user_id: Optional[str] = None,
        feedback_id: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        query = (
            "SELECT product_feedback.*, users.username, users.display_name, users.email "
            "FROM product_feedback JOIN users ON users.user_id = product_feedback.user_id "
            "WHERE 1 = 1"
        )
        params: List[Any] = []
        if user_id:
            query += " AND product_feedback.user_id = ?"
            params.append(user_id)
        if feedback_id:
            query += " AND product_feedback.feedback_id = ?"
            params.append(feedback_id)
        query += " ORDER BY product_feedback.created_at DESC LIMIT ?"
        params.append(limit)
        with self.connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        feedback = []
        for row in rows:
            data = dict(row)
            data["allow_contact"] = bool(data["allow_contact"])
            feedback.append(data)
        return feedback

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
