from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from backend.database import BackendStore, default_db_path
from backend.schemas import BatchReviewRequest, EssayReviewRequest, TeacherDecisionRequest
from src.esl_writing_feedback import review_esl_essay


VALID_TEACHER_ACTIONS = {"accept", "edit", "reject", "needs_more_evidence", "uncertain"}


def dataframe_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df.empty:
        return []
    clean = df.astype(object).where(pd.notnull(df), None)
    return clean.to_dict(orient="records")


def get_configured_db_path() -> Path:
    return Path(os.environ.get("CONSENSUS_SCOPE_BACKEND_DB", default_db_path()))


def create_app(db_path: Optional[str | Path] = None) -> FastAPI:
    store = BackendStore(Path(db_path) if db_path else get_configured_db_path())

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
        allow_origins=os.environ.get("CONSENSUS_SCOPE_CORS_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_store() -> BackendStore:
        return store

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {
            "status": "ok",
            "service": "ConsensusScope Backend API",
            "db_path": str(store.db_path),
        }

    @app.post("/api/review/single")
    def review_single(
        request: EssayReviewRequest,
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        session_id = f"rev-{uuid.uuid4().hex[:12]}"
        response = _run_and_store_review(
            backend_store=backend_store,
            request=request,
            session_id=session_id,
            batch_id=None,
            include_stress_tests=request.include_stress_tests,
        )
        return response

    @app.post("/api/review/batch")
    def review_batch(
        request: BatchReviewRequest,
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        batch_id = f"batch-{uuid.uuid4().hex[:12]}"
        sessions = []
        all_feedback = []
        all_summary = []
        for essay in request.essays:
            essay_request = essay.model_copy(update={"include_stress_tests": request.include_stress_tests})
            session_id = f"rev-{uuid.uuid4().hex[:12]}"
            response = _run_and_store_review(
                backend_store=backend_store,
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
            all_summary.append({"essay_id": response["essay_id"], **response["summary"]})
        return {
            "batch_id": batch_id,
            "sessions": sessions,
            "summary": all_summary,
            "feedback_items": all_feedback,
        }

    @app.get("/api/sessions")
    def list_sessions(
        limit: int = Query(default=50, ge=1, le=500),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        return {"sessions": backend_store.list_sessions(limit=limit)}

    @app.get("/api/sessions/{session_id}")
    def get_session(
        session_id: str,
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        session = backend_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="review session not found")
        return session

    @app.get("/api/sessions/{session_id}/feedback")
    def get_session_feedback(
        session_id: str,
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        if not backend_store.get_session(session_id):
            raise HTTPException(status_code=404, detail="review session not found")
        return {"feedback_items": backend_store.get_feedback_items(session_id)}

    @app.post("/api/teacher/decision")
    def save_teacher_decision(
        request: TeacherDecisionRequest,
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        if request.teacher_action not in VALID_TEACHER_ACTIONS:
            raise HTTPException(status_code=400, detail="unsupported teacher_action")
        if request.teacher_action == "edit" and not (request.teacher_corrected_feedback or "").strip():
            raise HTTPException(
                status_code=400,
                detail="teacher_corrected_feedback is required when teacher_action is edit",
            )
        if not backend_store.get_session(request.session_id):
            raise HTTPException(status_code=404, detail="review session not found")
        feedback_ids = {
            str(item.get("feedback_item_id"))
            for item in backend_store.get_feedback_items(request.session_id)
        }
        if request.feedback_item_id not in feedback_ids:
            raise HTTPException(status_code=404, detail="feedback item not found in session")
        decision = backend_store.save_teacher_decision(
            session_id=request.session_id,
            feedback_item_id=request.feedback_item_id,
            teacher_id=request.teacher_id,
            teacher_action=request.teacher_action,
            teacher_corrected_feedback=request.teacher_corrected_feedback,
            teacher_reason=request.teacher_reason,
            metadata=request.metadata,
        )
        return {"decision": decision}

    @app.get("/api/teacher/decisions")
    def list_teacher_decisions(
        session_id: Optional[str] = None,
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        return {"decisions": backend_store.list_teacher_decisions(session_id=session_id)}

    @app.get("/api/export/report/{session_id}", response_class=PlainTextResponse)
    def export_report(
        session_id: str,
        backend_store: BackendStore = Depends(get_store),
    ) -> str:
        session = backend_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="review session not found")
        return session["report_text"]

    @app.get("/api/audit/logs")
    def list_audit_logs(
        session_id: Optional[str] = None,
        limit: int = Query(default=100, ge=1, le=1000),
        backend_store: BackendStore = Depends(get_store),
    ) -> Dict[str, Any]:
        return {"logs": backend_store.list_audit_logs(session_id=session_id, limit=limit)}

    return app


def _run_and_store_review(
    *,
    backend_store: BackendStore,
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
    comparison = dataframe_records(result["comparison"])
    summary = dict(result["summary"])
    backend_store.save_review_session(
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

