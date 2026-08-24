from __future__ import annotations

import os
import sqlite3
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.auth import (
    hash_password,
    hash_session_token,
    issue_one_time_token,
    issue_session_token,
    verify_password,
)
from backend.database import BackendStore, default_db_path
from backend.notifications import (
    account_action_url,
    email_delivery_configured,
    exposed_test_token,
    send_transactional_email,
)
from backend.privacy import pii_check
from backend.rate_limit import SlidingWindowRateLimiter
from backend.schemas import (
    AccountDeleteRequest,
    AssignmentCreateRequest,
    BatchReviewRequest,
    CourseCreateRequest,
    EssayBatchCreateRequest,
    EssayCreateRequest,
    EssayReviewRequest,
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PIICheckRequest,
    ProductFeedbackRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    ReviewJobBatchRequest,
    ReviewJobCreateRequest,
    TeacherDecisionRequest,
)
from src.esl_live_generation import configured_esl_providers, generate_live_esl_feedback_candidates
from src.esl_writing_feedback import review_esl_essay, review_esl_feedback_candidates


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
        "email_verified": bool(user.get("email_verified_at")),
        "is_admin": is_admin,
    }


def create_app(
    db_path: Optional[str | Path] = None,
    admin_usernames: Optional[List[str]] = None,
) -> FastAPI:
    store = BackendStore(Path(db_path) if db_path else get_configured_db_path())
    store.delete_expired_auth_sessions()
    store.fail_interrupted_review_jobs()
    rate_limiter = SlidingWindowRateLimiter()
    review_executor = ThreadPoolExecutor(
        max_workers=max(1, min(8, int(os.environ.get("CONSENSUS_SCOPE_REVIEW_WORKERS", "4"))))
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            review_executor.shutdown(wait=True, cancel_futures=False)
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
        version="1.1.0",
        description=(
            "Backend API for ESL writing feedback review, risk-aware routing, "
            "teacher decisions, and audit export."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.review_executor = review_executor

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

    def enforce_rate_limit(
        request: Request,
        *,
        bucket: str,
        limit: int,
        window_seconds: int,
        identity: str = "",
    ) -> None:
        client_host = request.client.host if request.client else "unknown"
        keys = [f"{bucket}:ip:{client_host}"]
        if identity:
            keys.append(f"{bucket}:identity:{identity.strip().lower()}")
        for key in keys:
            allowed, retry_after = rate_limiter.allow(
                key,
                limit=limit,
                window_seconds=window_seconds,
            )
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail="too many requests; try again later",
                    headers={"Retry-After": str(retry_after)},
                )

    def validate_review_request(
        review_request: EssayReviewRequest,
        *,
        current_user: Dict[str, Any],
        backend_store: BackendStore,
    ) -> List[str]:
        privacy = pii_check(review_request.essay_text)
        if not privacy["safe_to_submit"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "identifiable student information must be removed before review",
                    "findings": privacy["findings"],
                },
            )
        if review_request.assignment_id and not backend_store.get_assignment(
            review_request.assignment_id,
            owner_user_id=current_user["user_id"],
        ):
            raise HTTPException(status_code=404, detail="assignment not found")
        if review_request.essay_record_id and not backend_store.get_essay(
            review_request.essay_record_id,
            owner_user_id=current_user["user_id"],
        ):
            raise HTTPException(status_code=404, detail="essay not found")
        if review_request.generation_mode == "local":
            return []
        configured = {item["provider"] for item in configured_esl_providers()}
        selected = [item for item in review_request.providers if item in configured]
        if not selected:
            raise HTTPException(
                status_code=503,
                detail="no selected live feedback provider is configured on the server",
            )
        return selected

    @app.get("/health")
    def health() -> Dict[str, Any]:
        live_providers = configured_esl_providers()
        return {
            "status": "ok",
            "service": "ConsensusScope Backend API",
            "authentication": "enabled",
            "version": "1.1.0",
            "capabilities": {
                "courses": True,
                "assignments": True,
                "async_review_jobs": True,
                "pii_screening": True,
                "account_export": True,
                "email_delivery": email_delivery_configured(),
                "live_feedback": bool(live_providers),
            },
            "live_providers": live_providers,
        }

    @app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
    def register(
        request: RegisterRequest,
        http_request: Request,
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        enforce_rate_limit(
            http_request,
            bucket="register",
            limit=8,
            window_seconds=3600,
            identity=request.username,
        )
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
        http_request: Request,
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        enforce_rate_limit(
            http_request,
            bucket="login",
            limit=20,
            window_seconds=900,
            identity=request.username,
        )
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

    @app.post("/api/auth/password-reset/request")
    def request_password_reset(
        request: PasswordResetRequest,
        http_request: Request,
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        enforce_rate_limit(
            http_request,
            bucket="password-reset",
            limit=5,
            window_seconds=3600,
            identity=request.email,
        )
        response: Dict[str, Any] = {
            "accepted": True,
            "message": "If the address is registered, password-reset instructions will be sent.",
            "email_delivery": email_delivery_configured(),
        }
        user = backend_store.get_user_by_email(request.email)
        if not user:
            return response
        token, token_hash, expires_at = issue_one_time_token(minutes=30)
        backend_store.create_password_reset_token(
            user_id=user["user_id"],
            token_hash=token_hash,
            expires_at=expires_at,
        )
        link = account_action_url("?action=reset_password", token)
        try:
            send_transactional_email(
                recipient=request.email,
                subject="Reset your ConsensusScope password",
                body=(
                    "A password reset was requested for your ConsensusScope account.\n\n"
                    f"Open this link within 30 minutes:\n{link}\n\n"
                    "If you did not request this, you can ignore this message."
                ),
            )
        except Exception:
            pass
        test_token = exposed_test_token(token)
        if test_token:
            response["reset_token"] = test_token
        return response

    @app.post("/api/auth/password-reset/confirm")
    def confirm_password_reset(
        request: PasswordResetConfirmRequest,
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        user = backend_store.consume_password_reset_token(hash_session_token(request.token))
        if not user:
            raise HTTPException(status_code=400, detail="reset token is invalid or expired")
        backend_store.update_password(
            user_id=user["user_id"],
            password_hash=hash_password(request.new_password),
        )
        return {"status": "password_reset", "reauthentication_required": True}

    @app.post("/api/account/email-verification/request")
    def request_email_verification(
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        email = str(current_user.get("email") or "").strip()
        if not email:
            raise HTTPException(status_code=400, detail="add an email address before verification")
        if current_user.get("email_verified_at"):
            return {"status": "already_verified", "email_delivery": email_delivery_configured()}
        token, token_hash, expires_at = issue_one_time_token(minutes=60)
        backend_store.create_email_verification_token(
            user_id=current_user["user_id"],
            token_hash=token_hash,
            expires_at=expires_at,
        )
        link = account_action_url("?action=verify_email", token)
        try:
            send_transactional_email(
                recipient=email,
                subject="Verify your ConsensusScope email",
                body=f"Verify your ConsensusScope email within 60 minutes:\n{link}",
            )
        except Exception:
            pass
        response: Dict[str, Any] = {
            "status": "verification_requested",
            "email_delivery": email_delivery_configured(),
        }
        test_token = exposed_test_token(token)
        if test_token:
            response["verification_token"] = test_token
        return response

    @app.post("/api/auth/email-verification/confirm")
    def confirm_email_verification(
        token: str,
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        user = backend_store.consume_email_verification_token(hash_session_token(token))
        if not user:
            raise HTTPException(status_code=400, detail="verification token is invalid or expired")
        backend_store.mark_email_verified(user["user_id"])
        return {"status": "email_verified"}

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

    @app.get("/api/account/export")
    def export_account_data(
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        return {"account_data": backend_store.export_account_data(owner_user_id=current_user["user_id"])}

    @app.delete("/api/account")
    def delete_account(
        request: AccountDeleteRequest,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        if not verify_password(request.password, current_user["password_hash"]):
            raise HTTPException(status_code=400, detail="current password is incorrect")
        deleted = backend_store.delete_account(owner_user_id=current_user["user_id"])
        if not deleted:
            raise HTTPException(status_code=404, detail="account not found")
        return {"status": "account_deleted"}

    @app.post("/api/privacy/check")
    def check_privacy(
        request: PIICheckRequest,
        current_user: Dict[str, Any] = Depends(get_current_user),
    ) -> Dict[str, Any]:
        del current_user
        return pii_check(request.text)

    @app.post("/api/courses", status_code=status.HTTP_201_CREATED)
    def create_course(
        request: CourseCreateRequest,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        course = backend_store.create_course(
            owner_user_id=current_user["user_id"],
            name=request.name,
            term=request.term,
            description=request.description,
        )
        return {"course": course}

    @app.get("/api/courses")
    def list_courses(
        include_archived: bool = False,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        return {
            "courses": backend_store.list_courses(
                owner_user_id=current_user["user_id"],
                include_archived=include_archived,
            )
        }

    @app.post("/api/assignments", status_code=status.HTTP_201_CREATED)
    def create_assignment(
        request: AssignmentCreateRequest,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        try:
            assignment = backend_store.create_assignment(
                owner_user_id=current_user["user_id"],
                course_id=request.course_id,
                title=request.title,
                prompt=request.prompt,
                student_level=request.student_level,
                due_date=request.due_date,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"assignment": assignment}

    @app.get("/api/assignments")
    def list_assignments(
        course_id: Optional[str] = None,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        return {
            "assignments": backend_store.list_assignments(
                owner_user_id=current_user["user_id"],
                course_id=course_id,
            )
        }

    @app.post("/api/essays", status_code=status.HTTP_201_CREATED)
    def create_essay(
        request: EssayCreateRequest,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        privacy = pii_check(request.essay_text)
        if not privacy["safe_to_submit"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "identifiable student information must be removed before upload",
                    "findings": privacy["findings"],
                },
            )
        assignment = backend_store.get_assignment(
            request.assignment_id,
            owner_user_id=current_user["user_id"],
        )
        if not assignment:
            raise HTTPException(status_code=404, detail="assignment not found")
        try:
            essay = backend_store.create_essay(
                owner_user_id=current_user["user_id"],
                assignment_id=request.assignment_id,
                external_id=request.external_id,
                essay_text=request.essay_text,
                student_level=request.student_level or assignment["student_level"],
                draft_stage=request.draft_stage,
                pii_status="clear",
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"essay": essay}

    @app.post("/api/essays/batch", status_code=status.HTTP_201_CREATED)
    def create_essay_batch(
        request: EssayBatchCreateRequest,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        created = []
        for essay_request in request.essays:
            privacy = pii_check(essay_request.essay_text)
            if not privacy["safe_to_submit"]:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": f"PII detected in essay {essay_request.external_id}",
                        "findings": privacy["findings"],
                    },
                )
            assignment = backend_store.get_assignment(
                essay_request.assignment_id,
                owner_user_id=current_user["user_id"],
            )
            if not assignment:
                raise HTTPException(status_code=404, detail="assignment not found")
            created.append(
                backend_store.create_essay(
                    owner_user_id=current_user["user_id"],
                    assignment_id=essay_request.assignment_id,
                    external_id=essay_request.external_id,
                    essay_text=essay_request.essay_text,
                    student_level=essay_request.student_level or assignment["student_level"],
                    draft_stage=essay_request.draft_stage,
                    pii_status="clear",
                )
            )
        return {"essays": created, "count": len(created)}

    @app.get("/api/essays")
    def list_essays(
        assignment_id: Optional[str] = None,
        include_text: bool = False,
        limit: int = Query(default=500, ge=1, le=2000),
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        return {
            "essays": backend_store.list_essays(
                owner_user_id=current_user["user_id"],
                assignment_id=assignment_id,
                limit=limit,
                include_text=include_text,
            )
        }

    @app.get("/api/essays/{essay_record_id}")
    def get_essay(
        essay_record_id: str,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        essay = backend_store.get_essay(essay_record_id, owner_user_id=current_user["user_id"])
        if not essay:
            raise HTTPException(status_code=404, detail="essay not found")
        return {"essay": essay}

    @app.get("/api/providers")
    def list_feedback_providers(
        current_user: Dict[str, Any] = Depends(get_current_user),
    ) -> Dict[str, Any]:
        del current_user
        return {
            "providers": configured_esl_providers(),
            "local_available": True,
        }

    @app.post("/api/review/jobs", status_code=status.HTTP_202_ACCEPTED)
    def create_review_job(
        request: ReviewJobCreateRequest,
        http_request: Request,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        enforce_rate_limit(
            http_request,
            bucket="review-job",
            limit=30,
            window_seconds=3600,
            identity=current_user["user_id"],
        )
        selected_providers = validate_review_request(
            request,
            current_user=current_user,
            backend_store=backend_store,
        )
        request_payload = request.model_dump()
        request_payload["providers"] = selected_providers
        job = backend_store.create_review_job(
            owner_user_id=current_user["user_id"],
            request_payload=request_payload,
            generation_mode=request.generation_mode,
            providers=selected_providers,
            assignment_id=request.assignment_id,
            essay_record_id=request.essay_record_id,
        )
        review_executor.submit(
            _execute_review_job,
            backend_store=backend_store,
            owner_user_id=current_user["user_id"],
            job_id=job["job_id"],
            request_payload=request_payload,
        )
        return {"job": job}

    @app.post("/api/review/jobs/batch", status_code=status.HTTP_202_ACCEPTED)
    def create_review_job_batch(
        request: ReviewJobBatchRequest,
        http_request: Request,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        enforce_rate_limit(
            http_request,
            bucket="review-job-batch",
            limit=10,
            window_seconds=3600,
            identity=current_user["user_id"],
        )
        jobs = []
        for essay_request in request.essays:
            normalized = essay_request.model_copy(
                update={
                    "generation_mode": request.generation_mode,
                    "providers": request.providers,
                }
            )
            selected_providers = validate_review_request(
                normalized,
                current_user=current_user,
                backend_store=backend_store,
            )
            request_payload = normalized.model_dump()
            request_payload["providers"] = selected_providers
            job = backend_store.create_review_job(
                owner_user_id=current_user["user_id"],
                request_payload=request_payload,
                generation_mode=normalized.generation_mode,
                providers=selected_providers,
                assignment_id=normalized.assignment_id,
                essay_record_id=normalized.essay_record_id,
            )
            jobs.append(job)
            review_executor.submit(
                _execute_review_job,
                backend_store=backend_store,
                owner_user_id=current_user["user_id"],
                job_id=job["job_id"],
                request_payload=request_payload,
            )
        return {"jobs": jobs, "count": len(jobs)}

    @app.get("/api/review/jobs")
    def list_review_jobs(
        limit: int = Query(default=100, ge=1, le=1000),
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        return {
            "jobs": backend_store.list_review_jobs(
                owner_user_id=current_user["user_id"],
                limit=limit,
            )
        }

    @app.get("/api/review/jobs/{job_id}")
    def get_review_job(
        job_id: str,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        job = backend_store.get_review_job(job_id, owner_user_id=current_user["user_id"])
        if not job:
            raise HTTPException(status_code=404, detail="review job not found")
        return {"job": job}

    @app.post("/api/review/single")
    def review_single(
        request: EssayReviewRequest,
        http_request: Request,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        enforce_rate_limit(
            http_request,
            bucket="review-sync",
            limit=20,
            window_seconds=3600,
            identity=current_user["user_id"],
        )
        selected_providers = validate_review_request(
            request,
            current_user=current_user,
            backend_store=backend_store,
        )
        session_id = f"rev-{uuid.uuid4().hex[:12]}"
        response = _run_and_store_review(
            backend_store=backend_store,
            owner_user_id=current_user["user_id"],
            request=request,
            session_id=session_id,
            batch_id=None,
            include_stress_tests=request.include_stress_tests,
            generation_mode=request.generation_mode,
            providers=selected_providers,
        )
        return response

    @app.post("/api/review/batch")
    def review_batch(
        request: BatchReviewRequest,
        http_request: Request,
        current_user: Dict[str, Any] = Depends(get_current_user),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        enforce_rate_limit(
            http_request,
            bucket="review-batch-sync",
            limit=10,
            window_seconds=3600,
            identity=current_user["user_id"],
        )
        batch_id = f"batch-{uuid.uuid4().hex[:12]}"
        sessions = []
        all_feedback = []
        all_summary = []
        all_comparison = []
        reports = []
        for essay in request.essays:
            essay_request = essay.model_copy(update={"include_stress_tests": request.include_stress_tests})
            selected_providers = validate_review_request(
                essay_request,
                current_user=current_user,
                backend_store=backend_store,
            )
            session_id = f"rev-{uuid.uuid4().hex[:12]}"
            response = _run_and_store_review(
                backend_store=backend_store,
                owner_user_id=current_user["user_id"],
                request=essay_request,
                session_id=session_id,
                batch_id=batch_id,
                include_stress_tests=request.include_stress_tests,
                generation_mode=essay_request.generation_mode,
                providers=selected_providers,
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
        backend_store.save_report_export(
            owner_user_id=current_user["user_id"],
            session_id=session_id,
            report_type="audit_markdown",
        )
        return session["report_text"]

    @app.get("/api/export/student-report/{session_id}", response_class=PlainTextResponse)
    def export_student_report(
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
        feedback = backend_store.get_feedback_items(
            session_id,
            owner_user_id=current_user["user_id"],
        )
        decisions = backend_store.list_teacher_decisions(
            owner_user_id=current_user["user_id"],
            session_id=session_id,
        )
        report = _build_student_report(session, feedback, decisions)
        backend_store.save_report_export(
            owner_user_id=current_user["user_id"],
            session_id=session_id,
            report_type="student_markdown",
        )
        return report

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
    generation_mode: str = "local",
    providers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    started = time.perf_counter()
    selected_providers = providers or []
    if generation_mode == "live":
        live_feedback, model_metadata = generate_live_esl_feedback_candidates(
            essay_text=request.essay_text,
            essay_id=request.essay_id,
            assignment_prompt=request.assignment_prompt,
            student_level=request.student_level,
            providers=selected_providers,
        )
        result = review_esl_feedback_candidates(
            live_feedback,
            essay_text=request.essay_text,
            essay_id=request.essay_id,
            assignment_prompt=request.assignment_prompt,
            student_level=request.student_level,
        )
    else:
        result = review_esl_essay(
            essay_text=request.essay_text,
            essay_id=request.essay_id,
            assignment_prompt=request.assignment_prompt,
            student_level=request.student_level,
            include_stress_tests=include_stress_tests,
        )
        model_metadata = {
            "generation_mode": "local",
            "providers_requested": [],
            "providers_succeeded": ["local_deterministic_reviewers"],
            "calls": [],
        }
    model_metadata["total_duration_ms"] = round((time.perf_counter() - started) * 1000)
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
        assignment_id=request.assignment_id,
        essay_record_id=request.essay_record_id,
        generation_mode=generation_mode,
        providers=selected_providers,
        model_metadata=model_metadata,
    )
    return {
        "session_id": session_id,
        "batch_id": batch_id,
        "essay_id": request.essay_id,
        "summary": summary,
        "feedback_items": feedback_items,
        "comparison": comparison,
        "report": result["report"],
        "generation_mode": generation_mode,
        "providers": selected_providers,
        "model_metadata": model_metadata,
    }


def _execute_review_job(
    *,
    backend_store: BackendStore,
    owner_user_id: str,
    job_id: str,
    request_payload: Dict[str, Any],
) -> None:
    backend_store.update_review_job(
        job_id=job_id,
        owner_user_id=owner_user_id,
        status="running",
        progress=10,
    )
    try:
        request = EssayReviewRequest.model_validate(request_payload)
        session_id = f"rev-{uuid.uuid4().hex[:12]}"
        response = _run_and_store_review(
            backend_store=backend_store,
            owner_user_id=owner_user_id,
            request=request,
            session_id=session_id,
            batch_id=None,
            include_stress_tests=request.include_stress_tests,
            generation_mode=request.generation_mode,
            providers=request.providers,
        )
        backend_store.update_review_job(
            job_id=job_id,
            owner_user_id=owner_user_id,
            status="completed",
            progress=100,
            session_id=session_id,
            result_metadata={
                "essay_id": response["essay_id"],
                "summary": response["summary"],
                "model_metadata": response["model_metadata"],
            },
        )
    except Exception as exc:
        backend_store.update_review_job(
            job_id=job_id,
            owner_user_id=owner_user_id,
            status="failed",
            progress=0,
            error_message=str(exc),
        )


def _build_student_report(
    session: Dict[str, Any],
    feedback_items: List[Dict[str, Any]],
    decisions: List[Dict[str, Any]],
) -> str:
    decision_map = {
        str(item.get("feedback_item_id")): item
        for item in decisions
    }
    released: List[Dict[str, str]] = []
    withheld = 0
    for item in feedback_items:
        item_id = str(item.get("feedback_item_id") or "")
        decision = decision_map.get(item_id, {})
        action = str(decision.get("teacher_action") or "")
        recommended = str(item.get("recommended_action") or "")
        suggestion = str(item.get("ai_suggestion") or "").strip()
        if action == "edit":
            suggestion = str(decision.get("teacher_corrected_feedback") or "").strip()
        if action in {"accept", "edit"} or (not action and recommended == "auto_accept"):
            released.append(
                {
                    "target_span": str(item.get("target_span") or "Overall draft"),
                    "suggestion": suggestion,
                    "issue_type": str(item.get("issue_type_predicted") or "writing feedback"),
                }
            )
        elif action not in {"reject"}:
            withheld += 1

    lines = [
        "# Writing Feedback",
        "",
        f"**Essay ID:** {session.get('essay_id', '')}",
        f"**Assignment:** {session.get('assignment_prompt', '')}",
        f"**Student level:** {session.get('student_level', '')}",
        "",
        "## Feedback selected for release",
        "",
    ]
    if not released:
        lines.append("No feedback items have been approved for student release yet.")
    else:
        for index, item in enumerate(released, start=1):
            lines.extend(
                [
                    f"### {index}. {item['target_span']}",
                    f"- **Focus:** {item['issue_type'].replace('_', ' ')}",
                    f"- **Feedback:** {item['suggestion']}",
                    "",
                ]
            )
    if withheld:
        lines.extend(
            [
                "## Teacher review status",
                "",
                f"{withheld} feedback item(s) remain withheld from student release pending a teacher decision.",
                "",
            ]
        )
    lines.extend(
        [
            "---",
            "This report contains only automatically released local edits and feedback explicitly approved or edited by a teacher.",
        ]
    )
    return "\n".join(lines)


app = create_app()
