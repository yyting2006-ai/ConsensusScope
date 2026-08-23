from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.auth import hash_password, hash_session_token, issue_session_token, verify_password
from backend.database import BackendStore, default_db_path
from backend.schemas import (
    BatchReviewRequest,
    EssayReviewRequest,
    LoginRequest,
    PasswordChangeRequest,
    ProductFeedbackRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    TeacherDecisionRequest,
)
from src.esl_writing_feedback import review_esl_essay


VALID_TEACHER_ACTIONS = {"accept", "edit", "reject", "needs_more_evidence", "uncertain"}


def dataframe_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df.empty:
        return []
    clean = df.astype(object).where(pd.notnull(df), None)
    return clean.to_dict(orient="records")


def get_configured_db_path() -> Path:
    return Path(os.environ.get("CONSENSUS_SCOPE_BACKEND_DB", default_db_path()))


def public_user(user: Dict[str, Any], *, is_admin: bool = False) -> Dict[str, Any]:
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "display_name": user.get("display_name", ""),
        "email": user.get("email"),
        "created_at": user.get("created_at"),
        "last_login_at": user.get("last_login_at"),
        "is_admin": is_admin,
    }


def create_app(
    db_path: Optional[str | Path] = None,
    admin_usernames: Optional[List[str]] = None,
) -> FastAPI:
    store = BackendStore(Path(db_path) if db_path else get_configured_db_path())
    store.delete_expired_auth_sessions()
    configured_admins = admin_usernames
    if configured_admins is None:
        configured_admins = os.environ.get("CONSENSUS_SCOPE_ADMIN_USERNAMES", "").split(",")
    admin_names = {item.strip().lower() for item in configured_admins if item.strip()}
    cors_origins = [
        item.strip()
        for item in os.environ.get(
            "CONSENSUS_SCOPE_CORS_ORIGINS",
            "https://demo.consensusscope.cn,http://localhost:8502,http://127.0.0.1:8502",
        ).split(",")
        if item.strip()
    ]
    bearer = HTTPBearer(auto_error=False)

    app = FastAPI(
        title="ConsensusScope Backend API",
        version="1.0.0",
        description=(
            "Backend API for ESL writing feedback review, risk-aware routing, "
            "teacher decisions, and audit export."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_store() -> BackendStore:
        return store

    def is_admin_user(user: Dict[str, Any]) -> bool:
        return str(user.get("username", "")).lower() in admin_names

    def get_current_user(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="authentication required",
            )
        user = backend_store.get_user_for_session(hash_session_token(credentials.credentials))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="session is invalid or expired",
            )
        return user

    def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if not is_admin_user(current_user):
            raise HTTPException(status_code=403, detail="administrator access required")
        return current_user

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {
            "status": "ok",
            "service": "ConsensusScope Backend API",
            "authentication": "enabled",
        }

    @app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
    def register(
        request: RegisterRequest,
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        if not request.privacy_acknowledged:
            raise HTTPException(
                status_code=400,
                detail="privacy acknowledgement is required",
            )
        try:
            user = backend_store.create_user(
                username=request.username,
                password_hash=hash_password(request.password),
                display_name=request.display_name,
                email=request.email,
            )
        except sqlite3.IntegrityError as exc:
            detail = "username or email is already registered"
            raise HTTPException(status_code=409, detail=detail) from exc
        token, token_hash, expires_at = issue_session_token()
        backend_store.create_auth_session(
            user_id=user["user_id"],
            token_hash=token_hash,
            expires_at=expires_at,
        )
        backend_store.mark_user_login(user["user_id"])
        current = backend_store.get_user(user["user_id"]) or user
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_at": expires_at,
            "user": public_user(current, is_admin=is_admin_user(current)),
        }

    @app.post("/api/auth/login")
    def login(
        request: LoginRequest,
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        user = backend_store.get_user_by_username(request.username)
        if not user or not verify_password(request.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="invalid username or password")
        token, token_hash, expires_at = issue_session_token()
        backend_store.create_auth_session(
            user_id=user["user_id"],
            token_hash=token_hash,
            expires_at=expires_at,
        )
        backend_store.mark_user_login(user["user_id"])
        current = backend_store.get_user(user["user_id"]) or user
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_at": expires_at,
            "user": public_user(current, is_admin=is_admin_user(current)),
        }

    @app.get("/api/auth/me")
    def me(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        return {"user": public_user(current_user, is_admin=is_admin_user(current_user))}

    @app.post("/api/auth/logout")
    def logout(
        credentials: HTTPAuthorizationCredentials = Depends(bearer),
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        del current_user
        backend_store.delete_auth_session(hash_session_token(credentials.credentials))
        return {"status": "logged_out"}

    @app.patch("/api/account/profile")
    def update_profile(
        request: ProfileUpdateRequest,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        try:
            updated = backend_store.update_user_profile(
                user_id=current_user["user_id"],
                display_name=request.display_name,
                email=request.email,
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="email is already registered") from exc
        return {"user": public_user(updated, is_admin=is_admin_user(updated))}

    @app.post("/api/account/password")
    def change_password(
        request: PasswordChangeRequest,
        credentials: HTTPAuthorizationCredentials = Depends(bearer),
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        if not verify_password(request.current_password, current_user["password_hash"]):
            raise HTTPException(status_code=400, detail="current password is incorrect")
        if request.current_password == request.new_password:
            raise HTTPException(status_code=400, detail="new password must be different")
        backend_store.update_password(
            user_id=current_user["user_id"],
            password_hash=hash_password(request.new_password),
        )
        # Password changes revoke every active device session, including this one.
        backend_store.delete_auth_session(hash_session_token(credentials.credentials))
        return {"status": "password_changed", "reauthentication_required": True}

    @app.get("/api/account/summary")
    def account_summary(
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        return {"summary": backend_store.account_summary(owner_user_id=current_user["user_id"])}

    @app.post("/api/review/single")
    def review_single(
        request: EssayReviewRequest,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        session_id = f"rev-{uuid.uuid4().hex[:12]}"
        response = _run_and_store_review(
            backend_store=backend_store,
            owner_user_id=current_user["user_id"],
            request=request,
            session_id=session_id,
            batch_id=None,
            include_stress_tests=request.include_stress_tests,
        )
        return response

    @app.post("/api/review/batch")
    def review_batch(
        request: BatchReviewRequest,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        batch_id = f"batch-{uuid.uuid4().hex[:12]}"
        sessions = []
        all_feedback = []
        all_summary = []
        all_comparison = []
        reports = []
        for essay in request.essays:
            essay_request = essay.model_copy(update={"include_stress_tests": request.include_stress_tests})
            session_id = f"rev-{uuid.uuid4().hex[:12]}"
            response = _run_and_store_review(
                backend_store=backend_store,
                owner_user_id=current_user["user_id"],
                request=essay_request,
                session_id=session_id,
                batch_id=batch_id,
                include_stress_tests=request.include_stress_tests,
            )
            sessions.append(
                {
                    "session_id": response["session_id"],
                    "essay_id": response["essay_id"],
                    "summary": response["summary"],
                }
            )
            all_feedback.extend(response["feedback_items"])
            all_comparison.extend(response["comparison"])
            all_summary.append({"essay_id": response["essay_id"], **response["summary"]})
            reports.append(response["report"])
        return {
            "batch_id": batch_id,
            "sessions": sessions,
            "summary": all_summary,
            "feedback_items": all_feedback,
            "comparison": all_comparison,
            "report": "\n\n---\n\n".join(reports),
        }

    @app.get("/api/sessions")
    def list_sessions(
        limit: int = Query(default=50, ge=1, le=500),
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        return {
            "sessions": backend_store.list_sessions(
                owner_user_id=current_user["user_id"],
                limit=limit,
            )
        }

    @app.get("/api/sessions/{session_id}")
    def get_session(
        session_id: str,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        session = backend_store.get_session(
            session_id,
            owner_user_id=current_user["user_id"],
        )
        if not session:
            raise HTTPException(status_code=404, detail="review session not found")
        return session

    @app.get("/api/sessions/{session_id}/feedback")
    def get_session_feedback(
        session_id: str,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        if not backend_store.get_session(session_id, owner_user_id=current_user["user_id"]):
            raise HTTPException(status_code=404, detail="review session not found")
        return {
            "feedback_items": backend_store.get_feedback_items(
                session_id,
                owner_user_id=current_user["user_id"],
            )
        }

    @app.delete("/api/sessions/{session_id}")
    def delete_session(
        session_id: str,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        deleted = backend_store.delete_session(
            session_id,
            owner_user_id=current_user["user_id"],
        )
        if not deleted:
            raise HTTPException(status_code=404, detail="review session not found")
        return {"status": "deleted", "session_id": session_id}

    @app.post("/api/teacher/decision")
    def save_teacher_decision(
        request: TeacherDecisionRequest,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        if request.teacher_action not in VALID_TEACHER_ACTIONS:
            raise HTTPException(status_code=400, detail="unsupported teacher_action")
        if request.teacher_action == "edit" and not (request.teacher_corrected_feedback or "").strip():
            raise HTTPException(
                status_code=400,
                detail="teacher_corrected_feedback is required when teacher_action is edit",
            )
        if not backend_store.get_session(
            request.session_id,
            owner_user_id=current_user["user_id"],
        ):
            raise HTTPException(status_code=404, detail="review session not found")
        feedback_ids = {
            str(item.get("feedback_item_id"))
            for item in backend_store.get_feedback_items(
                request.session_id,
                owner_user_id=current_user["user_id"],
            )
        }
        if request.feedback_item_id not in feedback_ids:
            raise HTTPException(status_code=404, detail="feedback item not found in session")
        decision = backend_store.save_teacher_decision(
            owner_user_id=current_user["user_id"],
            session_id=request.session_id,
            feedback_item_id=request.feedback_item_id,
            teacher_id=current_user["username"],
            teacher_action=request.teacher_action,
            teacher_corrected_feedback=request.teacher_corrected_feedback,
            teacher_reason=request.teacher_reason,
            metadata=request.metadata,
        )
        return {"decision": decision}

    @app.get("/api/teacher/decisions")
    def list_teacher_decisions(
        session_id: Optional[str] = None,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        return {
            "decisions": backend_store.list_teacher_decisions(
                owner_user_id=current_user["user_id"],
                session_id=session_id,
            )
        }

    @app.get("/api/export/report/{session_id}", response_class=PlainTextResponse)
    def export_report(
        session_id: str,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> str:
        session = backend_store.get_session(
            session_id,
            owner_user_id=current_user["user_id"],
        )
        if not session:
            raise HTTPException(status_code=404, detail="review session not found")
        return session["report_text"]

    @app.get("/api/audit/logs")
    def list_audit_logs(
        session_id: Optional[str] = None,
        limit: int = Query(default=100, ge=1, le=1000),
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        return {
            "logs": backend_store.list_audit_logs(
                owner_user_id=current_user["user_id"],
                session_id=session_id,
                limit=limit,
            )
        }

    @app.post("/api/feedback", status_code=status.HTTP_201_CREATED)
    def submit_feedback(
        request: ProductFeedbackRequest,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        feedback = backend_store.save_product_feedback(
            user_id=current_user["user_id"],
            category=request.category,
            rating=request.rating,
            message=request.message,
            page=request.page,
            allow_contact=request.allow_contact,
        )
        return {"feedback": feedback}

    @app.get("/api/feedback/mine")
    def my_feedback(
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        return {
            "feedback": backend_store.list_product_feedback(
                user_id=current_user["user_id"],
            )
        }

    @app.get("/api/admin/feedback")
    def admin_feedback(
        limit: int = Query(default=200, ge=1, le=1000),
        current_user: Dict[str, Any] = Depends(require_admin),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        del current_user
        return {"feedback": backend_store.list_product_feedback(limit=limit)}

    return app


def _run_and_store_review(
    *,
    backend_store: BackendStore,
    owner_user_id: str,
    request: EssayReviewRequest,
    session_id: str,
    batch_id: Optional[str],
    include_stress_tests: bool,
) -> Dict[str, Any]:
    result = review_esl_essay(
        essay_text=request.essay_text,
        essay_id=request.essay_id,
        assignment_prompt=request.assignment_prompt,
        student_level=request.student_level,
        include_stress_tests=include_stress_tests,
    )
    feedback_items = dataframe_records(result["merged"])
    for item in feedback_items:
        item["session_id"] = session_id
        item["batch_id"] = batch_id
    comparison = dataframe_records(result["comparison"])
    summary = dict(result["summary"])
    backend_store.save_review_session(
        owner_user_id=owner_user_id,
        session_id=session_id,
        batch_id=batch_id,
        essay_id=request.essay_id,
        assignment_prompt=request.assignment_prompt,
        student_level=request.student_level,
        essay_text=request.essay_text,
        include_stress_tests=include_stress_tests,
        summary=summary,
        comparison=comparison,
        report=result["report"],
        feedback_items=feedback_items,
    )
    return {
        "session_id": session_id,
        "batch_id": batch_id,
        "essay_id": request.essay_id,
        "summary": summary,
        "feedback_items": feedback_items,
        "comparison": comparison,
        "report": result["report"],
    }


app = create_app()
