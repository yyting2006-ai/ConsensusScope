from __future__ import annotations

import base64
import html
import io
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

APP_VERSION = "0.4.0"
LOGO_PATH = ROOT / "ui_prototype" / "assets" / "placeholder-logo.svg"
MAX_BATCH_ESSAYS = 100

from src.evaluation.simple_correctness import is_correct
from src.esl_writing_feedback import (
    build_review_evidence,
    compare_esl_feedback,
    evaluate_routing_against_expected,
    review_esl_batch,
    review_esl_essay,
    route_feedback_dataframe,
    summarize_routing,
)
from src.live_question import (
    TASK_CHOICE,
    TASK_CLAIM,
    TASK_FACT_QA,
    LiveModelConfig,
    adjudication_comparison_live,
    build_live_report,
    default_live_model_configs,
    load_historical_reliability,
    run_live_models,
)
from src.literary_feedback import (
    DEFAULT_LITERARY_ESSAY,
    EXAMPLE_ESSAYS,
    adjudicate_literary_feedback,
    apply_auto_accepted_edits,
    build_literary_feedback_report,
    decision_summary_by_type,
    generate_demo_literary_feedback,
    literary_routing_summary,
    load_literary_kg,
    retrieve_literary_knowledge,
    review_queue,
    run_live_literary_reviewers,
)
from src.llm.clients import PROVIDER_CONFIG


DATA_PATHS = {
    "samples": ROOT / "data" / "processed" / "clean_dataset.csv",
    "outputs_csv": ROOT / "data" / "outputs" / "model_outputs.csv",
    "outputs_jsonl": ROOT / "data" / "outputs" / "model_outputs.jsonl",
    "majority": ROOT / "data" / "results" / "majority_vote_results.csv",
    "dynamic": ROOT / "data" / "results" / "dynamic_decision_results.csv",
    "fixed_judge": ROOT / "data" / "results" / "fixed_judge_results.csv",
    "risk_labels": ROOT / "data" / "results" / "risk_labels.csv",
    "method_metrics": ROOT / "data" / "results" / "method_metrics.csv",
    "risk_effectiveness": ROOT / "data" / "results" / "risk_level_effectiveness.csv",
    "error_cases": ROOT / "data" / "results" / "error_cases.csv",
    "literary_kg": ROOT / "data" / "knowledge" / "literary_kg_triples.csv",
    "literary_benchmark": ROOT / "data" / "literary_feedback" / "benchmark.csv",
    "literary_records": ROOT / "data" / "results" / "literary_feedback_records.json",
    "literary_metrics": ROOT / "data" / "results" / "literary_feedback_routing_metrics.csv",
    "literary_live_records": ROOT / "data" / "results" / "literary_feedback_live_multimodel_records.json",
    "literary_live_metrics": ROOT / "data" / "results" / "literary_feedback_live_multimodel_metrics.csv",
    "esl_essays": ROOT / "data" / "esl_writing_demo" / "essays.csv",
    "esl_feedback": ROOT / "data" / "esl_writing_demo" / "feedback_items.csv",
    "esl_evidence": ROOT / "data" / "esl_writing_demo" / "review_evidence.csv",
    "esl_routing": ROOT / "data" / "esl_writing_demo" / "routing_results.csv",
    "esl_expected": ROOT / "data" / "esl_writing_demo" / "expected_routing_labels.csv",
    "esl_stress": ROOT / "data" / "esl_writing_demo" / "ai_review_stress_cases.csv",
    "public_gec_summary": ROOT / "reports" / "public_gec_summary_20260608.csv",
    "public_gec_policy_summary": ROOT / "reports" / "public_gec_policy_summary_20260608.csv",
    "figures": ROOT / "reports" / "figures",
}

ANSWER_PROVIDERS = [p for p in PROVIDER_CONFIG if p != "judge"]
RISK_LABELS = ["true_consensus", "false_consensus", "minority_correct", "high_disagreement", "confidence_mismatch"]
PUBLIC_TEXT_PLACEHOLDER = "Non-English provider text hidden in public UI."

NOTE_TRANSLATIONS = {
    "\u65e0\u6709\u6548\u6a21\u578b\u8f93\u51fa\uff0c\u5efa\u8bae\u4eba\u5de5\u590d\u6838": "No valid model output; human review is recommended.",
    "\u65e0\u552f\u4e00\u591a\u6570\u7b54\u6848\uff0c\u5efa\u8bae\u4eba\u5de5\u590d\u6838": "No unique majority answer; human review is recommended.",
    "\u4f4e\u98ce\u9669\u91c7\u7eb3": "Low-risk adoption.",
    "\u4e00\u81f4\u4f46\u8bc1\u636e\u6216\u7f6e\u4fe1\u5ea6\u4e0d\u8db3\uff0c\u6807\u8bb0\u4e3a\u98ce\u9669\u5171\u8bc6": "Agreement exists, but evidence or confidence is insufficient; mark as risky consensus.",
    "\u4e8b\u5b9e\u6838\u67e5\u975eNEI\u5171\u8bc6\u4ecd\u9700\u8bc1\u636e\u5ba1\u67e5\uff0c\u907f\u514d\u4f4e\u98ce\u9669\u8bef\u5224": "Fact-verification consensus still needs evidence review to avoid low-risk misclassification.",
    "\u5f00\u653e\u5f0f\u771f\u5b9e\u6027\u95ee\u7b54\u8f93\u51fa\u6838\u67e5\u6807\u7b7e\uff0c\u907f\u514d\u4f4e\u98ce\u9669\u8bef\u5224": "Open truthfulness QA produced a verification label; avoid low-risk misclassification.",
    "\u89e6\u53d1\u5c11\u6570\u6d3e\u9884\u8b66": "Minority warning triggered.",
    "\u9ad8\u5206\u6b67\uff0c\u5efa\u8bae\u4eba\u5de5\u590d\u6838": "High disagreement; human review is recommended.",
    "\u4e8b\u5b9e\u6838\u67e5\u5b58\u5728\u5206\u6b67\uff0c\u907f\u514d\u4f4e\u98ce\u9669\u8bef\u5224": "Fact verification contains disagreement; avoid low-risk misclassification.",
    "\u91c7\u7eb3\u591a\u6570\u7b54\u6848\uff0c\u5e76\u6839\u636e\u53ef\u9760\u6027\u8bc4\u5206\u5206\u7ea7": "Adopt the majority answer and assign a risk level using reliability score.",
    "\u91c7\u7eb3\u552f\u4e00\u6700\u9ad8\u7968\u7b54\u6848": "Adopt the unique top-voted answer.",
    "\u6700\u9ad8\u7968\u7b54\u6848\u5e73\u7968\uff0c\u5efa\u8bae\u4eba\u5de5\u590d\u6838": "Top-voted answers are tied; human review is recommended.",
}


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


MAIN_TRANSLATIONS = {
    "en": {
        "language_label": "Language / 语言",
        "sidebar_tagline": "AI feedback review workspace",
        "topbar_subtitle": "Teacher-controlled review routing for AI-generated ESL writing feedback",
        "badge_graph": "Feedback Safety Graph",
        "badge_teacher": "Teacher-in-the-loop",
        "badge_esl": "ESL Writing Review",
        "api_configuration": "API Configuration",
        "api_mode": "Provider configuration",
        "api_caption": "Auxiliary live providers use server-side deployment secrets. Credentials are never entered in or returned to the browser.",
        "answer_models": "Answer generation models",
        "answer_models_help": "Only providers configured by the deployment operator are available here.",
        "enable_fixed_judge": "Enable Fixed Judge in Live mode",
        "fixed_judge_model": "Fixed judge model",
        "account_access": "Sign in to ConsensusScope",
        "account_access_caption": "Create a personal account to keep review history, teacher decisions, and product feedback private.",
        "backend_required": "The account service is temporarily unavailable. Please try again shortly.",
        "login_tab": "Sign in",
        "register_tab": "Create account",
        "username": "Username",
        "password": "Password",
        "confirm_password": "Confirm password",
        "display_name": "Display name",
        "email_optional": "Email (optional)",
        "sign_in": "Sign in",
        "create_account": "Create account",
        "privacy_ack": "I will upload anonymized writing only and will not include names, student IDs, email addresses, or other personal information.",
        "privacy_notice": "Accounts are for personal review history. Do not upload identifiable student information.",
        "password_mismatch": "The passwords do not match.",
        "password_rules": "Use 8 or more characters. Usernames may contain letters, numbers, dots, underscores, and hyphens.",
        "auth_error": "Account request failed: {error}",
        "account_section": "Account",
        "signed_in_as": "Signed in as {name}",
        "sign_out": "Sign out",
        "navigation": "Navigation",
        "workspace_section": "Teacher workspace",
        "account_section_label": "Account and support",
        "page_home": "Review workspace",
        "page_single": "Single essay review",
        "page_batch": "Batch review",
        "page_compare": "AI feedback comparison",
        "page_queue": "Teacher review queue",
        "page_reports": "Reports and exports",
        "page_account": "My account",
        "page_feedback": "Product feedback",
        "page_settings": "Settings and diagnostics",
        "service_online": "Services operational",
        "service_offline": "Service unavailable",
        "secure_workspace": "Private workspace",
        "account_required": "Account access",
        "page_eval": "Effectiveness Evaluation",
        "page_design": "Design Reference",
        "feedback_items": "Feedback items",
        "auto_accepted": "Auto accepted",
        "teacher_review": "Teacher review",
        "high_risk": "High risk",
        "urgent": "Urgent",
        "mean_risk": "Mean risk",
        "no_feedback": "No feedback items available.",
        "single_title": "Single essay review",
        "single_caption": "Paste one ESL writing draft, generate local AI-style feedback candidates, build a Feedback Safety Graph for each item, and inspect what needs teacher review.",
        "load_demo": "Load a demo essay or start blank",
        "blank_workspace": "Blank workspace",
        "essay_id": "Essay ID",
        "assignment_prompt": "Assignment prompt",
        "student_level": "Student level",
        "student_draft": "Student essay draft",
        "include_stress": "Include unsafe stress-test suggestions for demo",
        "generate_route": "Generate and route AI feedback",
        "what_window_does": "What this window does",
        "single_explain": "It simulates multiple AI feedback reviewers in a no-API mode, normalizes every suggestion into the same schema, then builds an item-level Feedback Safety Graph linking the target span, suggestion, evidence signal, safety dimensions, and routing decision.",
        "single_info": "For public deployment, this page can run without API keys. Live LLM providers can later write into the same feedback schema.",
        "paste_essay_error": "Please paste an essay draft before running review.",
        "review_result": "Review Result",
        "routed_feedback": "Routed feedback",
        "teacher_queue_table": "Teacher-review queue",
        "download_single_report": "Download single essay report.md",
        "batch_title": "Batch review",
        "batch_caption": "Upload or use a CSV of ESL essays, then generate feedback candidates, Feedback Safety Graphs, and teacher-review routes for every row.",
        "upload_csv": "Upload CSV",
        "upload_help": "Expected columns: essay_id, assignment_prompt, student_level, essay_text or essay_text_anonymized.",
        "include_stress_batch": "Include unsafe stress-test suggestions for demo batch",
        "using_demo_data": "Using packaged synthetic ESL writing demo data. Upload a CSV to process your own essays.",
        "no_essays": "No essays are available.",
        "run_batch": "Run batch AI feedback review",
        "csv_required": "CSV must include essay_text or essay_text_anonymized.",
        "batch_result": "Batch Result",
        "all_routed_feedback": "All routed feedback",
        "download_batch_feedback": "Download batch routed feedback.csv",
        "download_batch_summary": "Download batch summary.csv",
        "compare_title": "AI feedback comparison",
        "run_first": "Run Single Essay Review or Batch Review first, or use the packaged demo data.",
        "compare_caption": "This page compares AI feedback candidates by target span, issue type, reviewers, routed risk, safety-graph dimensions, and consensus state.",
        "no_comparison": "No comparison rows are available.",
        "consensus_states": "Consensus states",
        "queue_title": "Teacher review queue",
        "queue_empty": "No teacher-review items are currently queued.",
        "queue_caption": "Accept, edit, reject, or defer each item. Saved decisions remain in your personal account.",
        "risk_level": "Risk level",
        "issue_type": "Issue type",
        "target_span": "Target span",
        "ai_suggestion": "AI suggestion",
        "routing_reason": "Routing reason",
        "ai_review_explanation": "AI review explanation",
        "feedback_safety_graph": "Feedback Safety Graph",
        "safety_graph_summary": "Safety graph summary",
        "safety_graph_path": "Safety graph path",
        "active_safety_dimensions": "Active safety dimensions",
        "safety_graph_mechanism": "Each feedback item is represented as a deploy-time safety graph: target span -> AI suggestion -> active safety dimension -> route. The graph uses observable signals only and does not use gold labels or teacher decisions.",
        "review_confidence": "Review confidence",
        "evidence_signal": "Evidence signal",
        "priority": "Priority",
        "teacher_action": "Teacher action",
        "save_decision": "Save decision",
        "corrected_feedback": "Edited student-facing feedback",
        "teacher_reason_optional": "Teacher note (optional)",
        "edit_feedback_required": "Enter the edited feedback before saving an edit decision.",
        "select_decision": "Select an action before saving.",
        "session_not_persistent": "Run a personal single or batch review before saving teacher decisions.",
        "download_queue": "Download teacher queue.csv",
        "eval_title": "Effectiveness Evaluation",
        "eval_caption": "This page evaluates implementation behavior on synthetic expectation labels, AI-review stress cases, and public learner-correction corpora. The public-corpus results evaluate routing against offline gold corrections, not classroom impact.",
        "combined_items": "Combined items",
        "action_accuracy": "Action accuracy",
        "risk_accuracy": "Risk accuracy",
        "high_risk_recall": "High-risk recall",
        "auto_precision": "Auto precision",
        "evaluation_sets": "Evaluation sets",
        "packaged_demo": "Packaged synthetic demo",
        "stress_cases": "AI-review stress cases",
        "public_gec_results": "Public learner-corpus benchmark",
        "public_gec_caption": "Aggregate offline routing results from JFLEG, CoNLL-2014 official test annotations, FCE, and W&I+LOCNESS. The benchmark uses public correction gold labels after routing; deploy-time routing does not see these labels.",
        "public_gec_policy": "Review-routing policy comparison",
        "public_gec_note": "Interpretation note: auto accuracy is high because correct feedback candidates are derived from public gold corrections and evaluated against constructed risk distractors. These numbers validate the routing layer, not real LLM feedback quality or classroom effectiveness.",
        "validity_assessment": "Validity assessment",
        "validity_text": "Current evidence supports a graph-backed review-routing claim: the system operationalizes a teacher-review workflow, constructs deploy-time Feedback Safety Graphs, routes synthetic high-risk feedback to review, and reproduces this routing behavior on public learner-correction corpora converted into feedback-level gold labels. It does not yet support a classroom effectiveness claim because no real teacher annotations, student outcomes, or time-on-task measurements have been collected.",
        "reports_title": "Reports and exports",
        "reports_caption": "Inspect the current review record and export teacher-readable evidence for audit or follow-up.",
        "report_table": "Report table",
        "report_preview": "Report preview",
        "download_routed_csv": "Download routed feedback.csv",
        "download_report_md": "Download report.md",
        "account_title": "My account",
        "account_caption": "Manage your profile, saved review history, and account security.",
        "personal_overview": "Personal review overview",
        "review_sessions": "Review sessions",
        "saved_decisions": "Saved decisions",
        "review_routed": "Routed for review",
        "recent_reviews": "Recent reviews",
        "no_history": "No saved reviews yet.",
        "open_review": "Open selected review",
        "delete_review": "Delete selected review",
        "confirm_delete_review": "I understand this permanently deletes the stored essay, feedback items, teacher decisions, and audit events.",
        "review_deleted": "Review deleted.",
        "session_loaded": "Review loaded. Open the comparison, teacher queue, or reports page to continue.",
        "profile": "Profile",
        "save_profile": "Save profile",
        "profile_saved": "Profile updated.",
        "change_password": "Change password",
        "current_password": "Current password",
        "new_password": "New password",
        "password_changed": "Password changed. Please sign in again.",
        "feedback_title": "Product feedback",
        "feedback_caption": "Report a problem, suggest an improvement, or tell us how the review workflow performed.",
        "feedback_category": "Category",
        "feedback_rating": "Overall experience",
        "feedback_message": "Feedback",
        "feedback_page": "Related page (optional)",
        "allow_contact": "You may contact me about this feedback using my account email.",
        "submit_feedback": "Submit feedback",
        "feedback_submitted": "Thank you. Your feedback has been saved.",
        "feedback_message_required": "Enter at least 5 characters before submitting feedback.",
        "my_feedback": "My submitted feedback",
        "admin_feedback": "Feedback inbox",
        "saving_review": "Running the review and saving it to your account...",
        "saved_to_account": "Review saved to your account.",
        "persistent_storage": "Personal account storage",
        "backend_request_failed": "The server could not complete this request: {error}",
        "settings_title": "Settings and diagnostics",
        "settings_info": "API settings, evaluation artifacts, and legacy diagnostics are kept here so the main navigation stays focused on the teacher workflow.",
        "backend_api": "Backend API",
        "backend_description": "FastAPI service for review-session persistence, teacher decisions, audit logs, and report export.",
        "backend_url": "Backend URL",
        "backend_status": "Backend status",
        "backend_available": "available",
        "backend_unavailable": "unavailable",
        "backend_not_configured": "not configured",
        "api_diagnostics": "API diagnostics",
        "legacy_feedback": "Legacy feedback technical demo",
        "aux_qa_comparison": "Auxiliary QA comparison",
        "aux_qa_risk": "Auxiliary QA risk dashboard",
        "aux_qa_case": "Auxiliary QA case explorer",
        "home_title": "Review workspace",
        "home_caption": "Review AI-generated ESL writing feedback, route uncertain items to a teacher, and keep every decision auditable.",
        "welcome_back": "Welcome back, {name}",
        "quick_actions": "Quick actions",
        "new_single_review": "New single review",
        "new_batch_review": "Start batch review",
        "open_queue": "Open teacher queue",
        "open_reports": "Open reports",
        "recent_activity": "Recent activity",
        "resume_review": "Resume latest review",
        "no_recent_activity": "Your completed reviews will appear here.",
        "workflow_status": "Review workflow",
        "step_input": "1. Submit draft",
        "step_generate": "2. Generate feedback",
        "step_route": "3. Route by risk",
        "step_review": "4. Teacher decision",
        "step_export": "5. Export report",
        "reference_data": "Packaged reference data",
        "draft_check": "Draft check",
        "word_count": "Word count",
        "draft_ready": "Ready for review",
        "draft_short": "Add more draft text for a meaningful review.",
        "privacy_check": "Use anonymized writing only. Remove names, student IDs, email addresses, and class identifiers before review.",
        "advanced_options": "Advanced options",
        "download_csv_template": "Download CSV template",
        "batch_source": "Input source",
        "uploaded_file": "Uploaded file",
        "packaged_examples": "Packaged examples",
        "valid_essays": "Valid essays",
        "batch_rows": "Rows",
        "empty_essay_rows": "{count} rows have no essay text. Complete or remove them before running the batch.",
        "batch_limit": "A batch can contain at most {count} essays.",
        "pending_items": "Pending",
        "completed_items": "Completed",
        "show_pending_only": "Show pending items only",
        "review_progress": "Review progress",
        "all_queue_items_complete": "All items in this queue have a saved teacher decision.",
        "history_search": "Search by essay or session ID",
        "no_feedback_history": "No product feedback submitted yet.",
        "footer_notice": "ConsensusScope v{version} · Teacher-controlled release · Anonymized writing only",
        "synthetic_essays": "Synthetic Essays",
        "esl_demo": "ESL writing demo",
        "unified_schema": "unified schema",
        "low_risk_edits": "low-risk local edits",
        "high_risk_items": "{count} high-risk items",
        "main_claim": "Main demo claim: Feedback Safety Graph-driven teacher review routing for AI-generated ESL writing feedback. Teachers can run single-essay or batch feedback review, inspect why each item activates meaning-preservation, content-grounding, tone, specificity, or agreement signals, and route risky feedback into a teacher queue before student release.",
        "prototype_info": "The current product UI reference is ui_prototype/index.html. Streamlit retains technical and auxiliary modules for inspection, but earlier modules are not the main EMNLP 2026 demo claim.",
        "routing_snapshot": "ESL Writing Feedback Routing Snapshot",
        "design_title": "Page 9 · Design Reference",
        "design_caption": "Designer-facing preview for the current ESL writing teacher-review workspace. The standalone source is ui_prototype/index.html.",
        "design_text": "Use this page when sharing the live site with a UI/UX designer. The intended design direction is a teacher workflow for reviewing ESL writing feedback, with model diagnostics moved into Settings / Diagnostics.",
        "download_design_brief": "Download Chinese design brief",
        "download_html_mockup": "Download HTML mockup",
        "design_missing": "Design reference mockup is not available in this package.",
        "read_error": "Failed to read {path}: {error}",
        "none": "None",
        "not_available": "Not available",
        "no_answer": "No answer",
        "no_model_outputs": "No model outputs yet.",
        "provider_request_errors": "Provider request errors",
        "parse_error": "Parse error",
        "no_adjudication_result": "No adjudication result yet.",
        "recommended_method": "Recommended method",
        "empty_answer": "empty",
        "three_methods": "Three adjudication methods",
        "workflow_line": "Single / Batch Review -> AI Feedback Comparison -> Teacher Queue -> Reports -> Personal History",
        "aux_qa_metrics": "Auxiliary QA reliability metrics",
        "literary_title": "ESL comparative-literature essay feedback",
        "literary_caption": "Teacher-facing workflow: low-risk language edits are separated from factual and interpretive suggestions that need human review.",
        "demo_essay": "Demo essay",
        "student_excerpt": "Student essay excerpt",
        "reviewer_source": "Reviewer source",
        "no_api_reviewers": "No-API deterministic reviewers",
        "live_api_reviewers": "Live API reviewers",
        "run_kg_feedback": "Run knowledge-grounded feedback",
        "auto_accept_metric": "Auto-accept",
        "kg_supported": "KG-supported",
        "kg_works": "KG works",
        "legacy_triples": "Legacy triples",
        "download_legacy_report": "Download legacy feedback report.md",
        "run_literary_info": "Run the demo to inspect knowledge retrieval, reviewer suggestions, and adjudicated feedback.",
        "teacher_view": "Teacher View",
        "knowledge_evidence": "Knowledge Evidence",
        "adjudication_trace": "Adjudication Trace",
        "raw_suggestions": "Raw Suggestions",
        "original_essay": "Original essay",
        "original": "Original",
        "auto_preview": "Auto-accepted preview",
        "preview": "Preview",
        "feedback_distribution": "Feedback Distribution",
        "no_kg_match": "No literary knowledge entry matched this essay excerpt.",
        "live_status": "Live reviewer call status",
        "legacy_title": "Legacy feedback technical demo",
        "run_page_first": "Run the technical demo first or regenerate data/results/literary_feedback_records.json.",
        "legacy_caption": "Legacy technical module retained for inspection. It is not the current main ESL writing feedback claim.",
        "no_teacher_items": "No teacher-review items in the selected record.",
        "no_kg_evidence": "No KG evidence is attached to this record.",
        "export_preview": "Export Preview",
        "tech_demo_title": "Technical Demo / Live Mode",
        "mode": "Mode",
        "legacy_warning": "This legacy module is retained for technical inspection. The current product storyline is ESL writing teacher-review routing, shown in the design reference.",
        "task_type": "Task type",
        "task_fact_qa": "Open factual QA",
        "task_claim": "Claim TRUE/FALSE/UNKNOWN",
        "task_choice": "A/B/C/D multiple choice",
        "question_claim": "Question / Claim",
        "temperature": "Temperature",
        "run_live": "Run Live Comparison",
        "calling_models": "Calling answer models and adjudicators...",
        "unified_format": "Multi-Model Answer Generation · Unified Format",
        "no_samples": "No samples are available. Generate data/processed/clean_dataset.csv first.",
        "dataset": "Dataset",
        "all": "All",
        "show_evaluated": "Show evaluated samples only",
        "no_sample_match": "No samples match the current filters.",
        "sample_id": "Sample ID",
        "sample_audit_title": "Sample Audit Mode",
        "question_claim_label": "Question / Claim",
        "options": "Options",
        "gold_answer": "Gold answer",
        "task": "Task",
        "model_outputs": "Model Outputs",
        "no_sample_outputs": "This sample has no model outputs.",
        "adjudication_layer": "Adjudication Layer",
        "risk_labels_label": "Risk Labels",
        "comparison_legacy_title": "Adjudication Comparison",
        "comparison_legacy_caption": "For ESL feedback, the main routing decision is auto-accept versus teacher review. The table below is retained for the auxiliary QA reliability module.",
        "aux_qa_offline_metrics": "Auxiliary QA Offline Metrics",
        "missing_method_metrics": "Missing data/results/method_metrics.csv.",
        "risk_dashboard_title": "Risk Dashboard",
        "esl_risk_title": "ESL Writing Feedback Routing Risk",
        "synthetic_counts_caption": "These are synthetic review-routing counts, not automatic essay-scoring results or classroom validation.",
        "missing_risk_labels": "Missing auxiliary QA risk_labels.csv.",
        "offline_diagnostic_labels": "Auxiliary QA Offline Diagnostic Labels",
        "offline_labels_caption": "These labels use gold answers and are not deploy-time knowledge.",
        "risk_samples": "Risk samples",
        "false_consensus": "False consensus",
        "minority_correct": "Minority correct",
        "risk_effectiveness": "Risk Level Effectiveness",
        "model_reliability_title": "Model Reliability Dashboard",
        "missing_model_files": "Missing model outputs or sample file.",
        "generation_stats": "Generation Statistics",
        "case_explorer_title": "Auxiliary QA Case Explorer",
        "case_explorer_caption": "Auxiliary reliability cases from saved QA traces. They are not the main ESL feedback demo claim.",
        "missing_error_cases": "Missing error_cases.csv.",
        "case_tags": "Case tags",
        "inspect_case": "Inspect case",
        "report_export_title": "Report Export",
        "download_esl_report": "Download esl_writing_routing_report.md",
        "download_esl_routing": "Download esl_writing_routing_results.csv",
        "download_live_report": "Download Live report.md",
        "download_summary_json": "Download system_summary.json",
        "download_method_metrics": "Download method_metrics.csv",
        "download_risk_labels": "Download risk_labels.csv",
        "storage_backend": "Storage backend",
        "session_only": "Browser session only",
        "reviewer_id": "Reviewer ID",
        "reviewer_id_help": "Anonymous label used only in the current browser session.",
        "decision_saved": "Decision saved.",
        "graph_route_summary": "Active dimensions: {dimensions}. Recommended route: {route}.",
        },
    "zh": {
        "language_label": "Language / 语言",
        "sidebar_tagline": "AI 写作反馈审核工作台",
        "topbar_subtitle": "面向 AI 生成 ESL 写作反馈的教师可控审核路由",
        "badge_graph": "反馈安全图谱",
        "badge_teacher": "教师参与复核",
        "badge_esl": "ESL 写作评审",
        "api_configuration": "API 配置",
        "api_mode": "模型服务配置",
        "api_caption": "辅助实时模型仅使用部署端密钥，访问者无需也不能在浏览器中输入 API key。",
        "answer_models": "回答生成模型",
        "answer_models_help": "这里只显示部署管理员已经配置的模型服务商。",
        "enable_fixed_judge": "实时模式启用固定裁判",
        "fixed_judge_model": "固定裁判模型",
        "account_access": "登录 ConsensusScope",
        "account_access_caption": "创建个人账号后，评审历史、教师决策和意见反馈会分别保存在你的账号下。",
        "backend_required": "账号服务暂时不可用，请稍后重试。",
        "login_tab": "登录",
        "register_tab": "注册账号",
        "username": "用户名",
        "password": "密码",
        "confirm_password": "确认密码",
        "display_name": "显示名称",
        "email_optional": "邮箱（选填）",
        "sign_in": "登录",
        "create_account": "创建账号",
        "privacy_ack": "我只会上传匿名化作文，不包含姓名、学号、邮箱或其他个人身份信息。",
        "privacy_notice": "个人账号仅用于保存评审记录。请勿上传可识别学生身份的信息。",
        "password_mismatch": "两次输入的密码不一致。",
        "password_rules": "密码不少于 8 位；用户名可使用字母、数字、点、下划线和连字符。",
        "auth_error": "账号请求失败：{error}",
        "account_section": "个人账号",
        "signed_in_as": "当前账号：{name}",
        "sign_out": "退出登录",
        "navigation": "导航",
        "workspace_section": "教师工作区",
        "account_section_label": "账号与支持",
        "page_home": "评审工作台",
        "page_single": "单篇作文评审",
        "page_batch": "批量评审",
        "page_compare": "AI 反馈对比",
        "page_queue": "教师复核队列",
        "page_reports": "报告与导出",
        "page_account": "我的账号",
        "page_feedback": "意见反馈",
        "page_settings": "设置与诊断",
        "service_online": "服务运行正常",
        "service_offline": "服务暂不可用",
        "secure_workspace": "个人工作区",
        "account_required": "账号访问",
        "page_eval": "有效性评估",
        "page_design": "设计参考",
        "feedback_items": "反馈项",
        "auto_accepted": "自动接受",
        "teacher_review": "教师复核",
        "high_risk": "高风险",
        "urgent": "紧急",
        "mean_risk": "平均风险",
        "no_feedback": "暂无反馈项。",
        "single_title": "单篇作文评审",
        "single_caption": "粘贴一篇 ESL 作文，生成本地 AI 风格反馈候选，为每条反馈建立反馈安全图谱，并查看哪些反馈需要教师复核。",
        "load_demo": "加载 demo 作文或新建空白工作区",
        "blank_workspace": "空白工作区",
        "essay_id": "作文 ID",
        "assignment_prompt": "作文题目",
        "student_level": "学生水平",
        "student_draft": "学生作文草稿",
        "include_stress": "加入不安全压力测试建议用于演示",
        "generate_route": "生成并路由 AI 反馈",
        "what_window_does": "该窗口的作用",
        "single_explain": "它在无需 API 的模式下模拟多个 AI 反馈评审器，将每条建议规范到同一数据格式，再构建条目级反馈安全图谱，把目标片段、AI 建议、证据信号、安全维度和路由决策连起来。",
        "single_info": "公开部署时，本页无需 API key 即可运行。真实 LLM 服务商后续也可以写入同一反馈格式。",
        "paste_essay_error": "请先粘贴作文草稿。",
        "review_result": "评审结果",
        "routed_feedback": "路由后的反馈",
        "teacher_queue_table": "教师复核队列",
        "download_single_report": "下载单篇作文报告.md",
        "batch_title": "批量评审",
        "batch_caption": "上传或使用 ESL 作文 CSV，为每篇作文生成反馈候选、反馈安全图谱和教师复核路由。",
        "upload_csv": "上传 CSV",
        "upload_help": "期望字段：essay_id, assignment_prompt, student_level, essay_text 或 essay_text_anonymized。",
        "include_stress_batch": "批量演示加入不安全压力测试建议",
        "using_demo_data": "正在使用内置合成 ESL 写作演示数据。上传 CSV 可处理你自己的作文。",
        "no_essays": "暂无可用作文。",
        "run_batch": "运行批量 AI 反馈评审",
        "csv_required": "CSV 必须包含 essay_text 或 essay_text_anonymized。",
        "batch_result": "批量结果",
        "all_routed_feedback": "全部路由反馈",
        "download_batch_feedback": "下载批量路由反馈.csv",
        "download_batch_summary": "下载批量摘要.csv",
        "compare_title": "AI 反馈对比",
        "run_first": "请先运行单篇作文评审或批量评审，或使用内置 demo 数据。",
        "compare_caption": "本页按目标片段、问题类型、评审器、路由风险、安全图谱维度和一致性状态对比 AI 反馈候选。",
        "no_comparison": "暂无对比结果。",
        "consensus_states": "一致性状态",
        "queue_title": "教师复核队列",
        "queue_empty": "当前没有需要教师复核的项目。",
        "queue_caption": "你可以接受、修改、拒绝或暂缓每条反馈；保存后的决策会保留在个人账号中。",
        "risk_level": "风险等级",
        "issue_type": "问题类型",
        "target_span": "目标片段",
        "ai_suggestion": "AI 建议",
        "routing_reason": "路由原因",
        "ai_review_explanation": "AI 评审解释",
        "feedback_safety_graph": "反馈安全图谱",
        "safety_graph_summary": "安全图谱摘要",
        "safety_graph_path": "安全图谱路径",
        "active_safety_dimensions": "激活的安全维度",
        "safety_graph_mechanism": "每条反馈都会被表示为部署时安全图谱：目标片段 -> AI 建议 -> 激活的安全维度 -> 路由决策。图谱只使用部署时可见信号，不使用标准答案或教师标注。",
        "review_confidence": "评审置信度",
        "evidence_signal": "证据信号",
        "priority": "优先级",
        "teacher_action": "教师动作",
        "save_decision": "保存决策",
        "corrected_feedback": "修改后的学生可见反馈",
        "teacher_reason_optional": "教师备注（选填）",
        "edit_feedback_required": "选择“修改”时，请先填写修改后的反馈。",
        "select_decision": "请先选择处理动作再保存。",
        "session_not_persistent": "请先运行一次个人单篇或批量评审，再保存教师决策。",
        "download_queue": "下载教师队列.csv",
        "eval_title": "有效性评估",
        "eval_caption": "本页在合成期望标签、AI 评审压力测试案例和公开学习者纠错语料上评估实现行为。公开语料结果是基于离线 gold correction 的路由评估，不是真实课堂效果。",
        "combined_items": "合并项目数",
        "action_accuracy": "动作准确率",
        "risk_accuracy": "风险准确率",
        "high_risk_recall": "高风险召回",
        "auto_precision": "自动接受精确率",
        "evaluation_sets": "评估集合",
        "packaged_demo": "内置合成演示",
        "stress_cases": "AI 评审压力测试",
        "public_gec_results": "公开学习者语料评测",
        "public_gec_caption": "来自 JFLEG、CoNLL-2014 官方测试标注、FCE 和 W&I+LOCNESS 的聚合离线路由结果。公开纠错 gold label 只在路由后用于评估，部署时路由器不可见。",
        "public_gec_policy": "复核路由策略对比",
        "public_gec_note": "解释说明：自动接受准确率高，是因为正确反馈候选来自公开 gold correction，并与构造的风险干扰项对比评估。这些数字验证的是路由层，不代表真实 LLM 反馈质量或课堂有效性。",
        "validity_assessment": "有效性说明",
        "validity_text": "当前证据支持图谱驱动的复核路由主张：系统可以实现教师复核工作流，为每条反馈构建部署时反馈安全图谱，将合成高风险反馈送入复核，并能在转换为反馈级 gold label 的公开学习者纠错语料上复现该路由行为。但它还不能证明真实课堂有效性，因为尚未收集真实教师标注、学生结果或耗时数据。",
        "reports_title": "报告与导出",
        "reports_caption": "查看当前评审记录，并导出便于教师阅读的审计证据与后续材料。",
        "report_table": "报告表格",
        "report_preview": "报告预览",
        "download_routed_csv": "下载路由反馈.csv",
        "download_report_md": "下载报告.md",
        "account_title": "我的账号",
        "account_caption": "管理个人资料、评审历史与账号安全。",
        "personal_overview": "个人评审概览",
        "review_sessions": "评审记录",
        "saved_decisions": "已保存决策",
        "review_routed": "送入复核",
        "recent_reviews": "最近评审",
        "no_history": "暂时没有已保存的评审记录。",
        "open_review": "打开所选评审",
        "delete_review": "删除所选评审",
        "confirm_delete_review": "我确认永久删除该作文、反馈项、教师决策和对应审计记录。",
        "review_deleted": "评审记录已删除。",
        "session_loaded": "评审记录已加载，可前往反馈对比、教师复核队列或报告页继续处理。",
        "profile": "个人资料",
        "save_profile": "保存资料",
        "profile_saved": "个人资料已更新。",
        "change_password": "修改密码",
        "current_password": "当前密码",
        "new_password": "新密码",
        "password_changed": "密码已修改，请重新登录。",
        "feedback_title": "意见反馈",
        "feedback_caption": "可以报告问题、提出改进建议，或评价本次作文评审体验。",
        "feedback_category": "反馈类型",
        "feedback_rating": "整体体验",
        "feedback_message": "反馈内容",
        "feedback_page": "相关页面（选填）",
        "allow_contact": "允许通过账号邮箱就此反馈联系我。",
        "submit_feedback": "提交反馈",
        "feedback_submitted": "感谢反馈，内容已经保存。",
        "feedback_message_required": "请至少填写 5 个字符后再提交。",
        "my_feedback": "我提交的反馈",
        "admin_feedback": "反馈收件箱",
        "saving_review": "正在运行评审并保存到个人账号...",
        "saved_to_account": "评审已保存到个人账号。",
        "persistent_storage": "个人账号存储",
        "backend_request_failed": "服务器未能完成请求：{error}",
        "settings_title": "设置与诊断",
        "settings_info": "API 设置、有效性评测和旧辅助诊断统一收在本页，主导航只保留教师日常工作流。",
        "backend_api": "后端 API",
        "backend_description": "FastAPI 服务用于保存评审会话、教师决策、审计日志和导出报告。",
        "backend_url": "后端地址",
        "backend_status": "后端状态",
        "backend_available": "可用",
        "backend_unavailable": "不可用",
        "backend_not_configured": "未配置",
        "api_diagnostics": "API 诊断",
        "legacy_feedback": "旧反馈技术演示",
        "aux_qa_comparison": "辅助 QA 对比",
        "aux_qa_risk": "辅助 QA 风险面板",
        "aux_qa_case": "辅助 QA 案例浏览",
        "home_title": "评审工作台",
        "home_caption": "在反馈发给学生前审核 AI 生成的 ESL 写作建议，将不确定项目交给教师，并保留可追溯的决策记录。",
        "welcome_back": "欢迎回来，{name}",
        "quick_actions": "快捷操作",
        "new_single_review": "新建单篇评审",
        "new_batch_review": "开始批量评审",
        "open_queue": "打开教师队列",
        "open_reports": "查看报告",
        "recent_activity": "最近活动",
        "resume_review": "继续最近评审",
        "no_recent_activity": "完成评审后，记录会显示在这里。",
        "workflow_status": "评审流程",
        "step_input": "1. 提交作文",
        "step_generate": "2. 生成反馈",
        "step_route": "3. 风险路由",
        "step_review": "4. 教师决策",
        "step_export": "5. 导出报告",
        "reference_data": "内置参考数据",
        "draft_check": "草稿检查",
        "word_count": "词数",
        "draft_ready": "可以开始评审",
        "draft_short": "请补充更多作文内容，以获得有意义的评审结果。",
        "privacy_check": "仅使用匿名化作文。评审前请删除姓名、学号、邮箱和班级等身份信息。",
        "advanced_options": "高级选项",
        "download_csv_template": "下载 CSV 模板",
        "batch_source": "输入来源",
        "uploaded_file": "上传文件",
        "packaged_examples": "内置示例",
        "valid_essays": "有效作文",
        "batch_rows": "总行数",
        "empty_essay_rows": "有 {count} 行缺少作文正文，请补全或删除后再运行批量评审。",
        "batch_limit": "单个批次最多包含 {count} 篇作文。",
        "pending_items": "待处理",
        "completed_items": "已完成",
        "show_pending_only": "仅显示待处理项目",
        "review_progress": "复核进度",
        "all_queue_items_complete": "当前队列中的项目均已保存教师决策。",
        "history_search": "按作文 ID 或评审 ID 搜索",
        "no_feedback_history": "尚未提交意见反馈。",
        "footer_notice": "ConsensusScope v{version} · 由教师控制发布 · 仅使用匿名化作文",
        "synthetic_essays": "合成作文",
        "esl_demo": "ESL 写作演示",
        "unified_schema": "统一数据格式",
        "low_risk_edits": "低风险局部修改",
        "high_risk_items": "{count} 个高风险项目",
        "main_claim": "主演示主张：基于反馈安全图谱的 AI 生成 ESL 写作反馈教师复核路由。教师可以进行单篇或批量反馈评审，查看每条反馈为什么触发保留原意、内容依据、语气安全、具体性或一致性信号，并在学生看到反馈前将风险反馈送入教师队列。",
        "prototype_info": "当前产品 UI 参考为 ui_prototype/index.html。Streamlit 保留技术和辅助模块供检查，但早期模块不是当前 EMNLP 2026 演示主张。",
        "routing_snapshot": "ESL 写作反馈路由快照",
        "design_title": "第 9 页 · 设计参考",
        "design_caption": "面向设计师的当前 ESL 写作教师复核工作台预览。独立源文件是 ui_prototype/index.html。",
        "design_text": "将在线网站分享给 UI/UX 设计师时可使用本页。目标设计方向是 ESL 写作反馈教师复核工作流，模型诊断移至设置 / 诊断中。",
        "download_design_brief": "下载中文设计说明",
        "download_html_mockup": "下载 HTML 原型",
        "design_missing": "该包中没有设计参考原型。",
        "read_error": "读取 {path} 失败：{error}",
        "none": "无",
        "not_available": "不可用",
        "no_answer": "无答案",
        "no_model_outputs": "暂无模型输出。",
        "provider_request_errors": "模型请求错误",
        "parse_error": "解析错误",
        "no_adjudication_result": "暂无裁决结果。",
        "recommended_method": "推荐方法",
        "empty_answer": "空",
        "three_methods": "三种裁决方法",
        "workflow_line": "单篇 / 批量评审 -> AI 反馈对比 -> 教师复核队列 -> 报告导出 -> 个人历史",
        "aux_qa_metrics": "辅助 QA 可靠性指标",
        "literary_title": "ESL 比较文学作文反馈",
        "literary_caption": "教师工作流：低风险语言修改会与需要人工复核的事实性、解释性建议分开。",
        "demo_essay": "示例作文",
        "student_excerpt": "学生作文片段",
        "reviewer_source": "评审来源",
        "no_api_reviewers": "无需 API 的确定性评审器",
        "live_api_reviewers": "实时 API 评审器",
        "run_kg_feedback": "运行知识增强反馈",
        "auto_accept_metric": "自动接受",
        "kg_supported": "知识库支持",
        "kg_works": "知识库作品数",
        "legacy_triples": "旧知识三元组数",
        "download_legacy_report": "下载旧技术报告.md",
        "run_literary_info": "运行演示后可查看知识检索、评审建议和裁决结果。",
        "teacher_view": "教师视图",
        "knowledge_evidence": "知识证据",
        "adjudication_trace": "裁决轨迹",
        "raw_suggestions": "原始建议",
        "original_essay": "原作文",
        "original": "原文",
        "auto_preview": "自动接受后的预览",
        "preview": "预览",
        "feedback_distribution": "反馈分布",
        "no_kg_match": "该作文片段没有匹配到文学知识条目。",
        "live_status": "实时评审调用状态",
        "legacy_title": "旧反馈技术演示",
        "run_page_first": "请先运行技术演示，或重新生成 data/results/literary_feedback_records.json。",
        "legacy_caption": "该旧技术模块仅保留用于检查，不属于当前 ESL 写作反馈主线。",
        "no_teacher_items": "当前记录没有教师复核项。",
        "no_kg_evidence": "当前记录没有附加知识证据。",
        "export_preview": "导出预览",
        "tech_demo_title": "技术演示 / 实时模式",
        "mode": "模式",
        "legacy_warning": "该旧模块仅用于技术检查。当前产品主线是 ESL 写作反馈教师复核路由，见设计参考页。",
        "task_type": "任务类型",
        "task_fact_qa": "开放事实问答",
        "task_claim": "声明判断 TRUE/FALSE/UNKNOWN",
        "task_choice": "A/B/C/D 多选题",
        "question_claim": "问题 / 声明",
        "temperature": "温度",
        "run_live": "运行实时对比",
        "calling_models": "正在调用回答模型和裁决器...",
        "unified_format": "多模型回答生成 · 统一格式",
        "no_samples": "暂无样本。请先生成 data/processed/clean_dataset.csv。",
        "dataset": "数据集",
        "all": "全部",
        "show_evaluated": "只显示已评估样本",
        "no_sample_match": "当前筛选条件下没有匹配样本。",
        "sample_id": "样本 ID",
        "sample_audit_title": "样本审计模式",
        "question_claim_label": "问题 / 声明",
        "options": "选项",
        "gold_answer": "标准答案",
        "task": "任务",
        "model_outputs": "模型输出",
        "no_sample_outputs": "该样本没有模型输出。",
        "adjudication_layer": "裁决层",
        "risk_labels_label": "风险标签",
        "comparison_legacy_title": "裁决方法对比",
        "comparison_legacy_caption": "对于 ESL 反馈，主线决策是自动接受还是进入教师复核。下表保留为辅助 QA 可靠性模块。",
        "aux_qa_offline_metrics": "辅助 QA 离线指标",
        "missing_method_metrics": "缺少 data/results/method_metrics.csv。",
        "risk_dashboard_title": "风险看板",
        "esl_risk_title": "ESL 写作反馈路由风险",
        "synthetic_counts_caption": "这些是合成数据上的复核路由统计，不是自动作文评分结果，也不是真实课堂验证。",
        "missing_risk_labels": "缺少辅助 QA risk_labels.csv。",
        "offline_diagnostic_labels": "辅助 QA 离线诊断标签",
        "offline_labels_caption": "这些标签使用了标准答案，只能用于离线诊断，不能视为部署时自动知道的信息。",
        "risk_samples": "风险样本数",
        "false_consensus": "错误共识",
        "minority_correct": "少数正确",
        "risk_effectiveness": "风险等级有效性",
        "model_reliability_title": "模型可靠性看板",
        "missing_model_files": "缺少模型输出或样本文件。",
        "generation_stats": "生成统计",
        "case_explorer_title": "辅助 QA 案例浏览",
        "case_explorer_caption": "来自已保存 QA 轨迹的辅助可靠性案例，不属于当前 ESL 反馈主线。",
        "missing_error_cases": "缺少 error_cases.csv。",
        "case_tags": "案例标签",
        "inspect_case": "查看案例",
        "report_export_title": "报告导出",
        "download_esl_report": "下载 ESL 写作路由报告.md",
        "download_esl_routing": "下载 ESL 写作路由结果.csv",
        "download_live_report": "下载实时报告.md",
        "download_summary_json": "下载系统摘要.json",
        "download_method_metrics": "下载方法指标.csv",
        "download_risk_labels": "下载风险标签.csv",
        "storage_backend": "存储后端",
        "session_only": "仅当前浏览器会话",
        "reviewer_id": "教师编号",
        "reviewer_id_help": "仅作为当前浏览器会话中的匿名标识。",
        "decision_saved": "决策已保存。",
        "graph_route_summary": "激活维度：{dimensions}。建议路由：{route}。",
    },
}


MAIN_TRANSLATIONS["en"].update(
    {
        "page_assignments": "Courses and assignments",
        "assignments_title": "Courses and assignments",
        "assignments_caption": "Organize anonymized essays by course and assignment before generating or reviewing AI feedback.",
        "courses": "Courses",
        "assignments": "Assignments",
        "essays": "Essays",
        "active_jobs": "Active jobs",
        "new_course": "New course",
        "course_name": "Course name",
        "term": "Term",
        "description_optional": "Description (optional)",
        "create_course": "Create course",
        "course_created": "Course created.",
        "select_course": "Select course",
        "new_assignment": "New assignment",
        "assignment_title": "Assignment title",
        "due_date_optional": "Due date (optional)",
        "create_assignment": "Create assignment",
        "assignment_created": "Assignment created.",
        "select_assignment": "Select assignment",
        "stored_essays": "Stored anonymized essays",
        "add_essay": "Add one essay",
        "external_essay_id": "Anonymous essay ID",
        "draft_stage": "Draft stage",
        "save_essay": "Save essay",
        "essay_saved": "Essay saved.",
        "upload_essay_batch": "Upload essay CSV",
        "save_essay_batch": "Save CSV essays",
        "essays_saved": "{count} essays saved.",
        "no_courses": "Create a course to begin organizing assignments.",
        "no_assignments": "Create an assignment before adding essays.",
        "no_stored_essays": "No anonymized essays are stored for this assignment.",
        "open_single_review": "Open in single review",
        "start_assignment_batch": "Review all essays in this assignment",
        "privacy_scan": "Privacy preflight",
        "privacy_clear": "No high-confidence personal identifiers were detected.",
        "privacy_blocked": "Remove the detected personal information before saving or reviewing this draft.",
        "detected_types": "Detected identifier types: {types}",
        "generation_source": "Feedback generation source",
        "local_generation": "Built-in demonstration reviewers",
        "live_generation": "Live server-side AI models",
        "local_generation_help": "Fast, reproducible, and free of external API calls. Suitable for exploring the review workflow.",
        "live_generation_help": "Uses configured server-side model providers. Student text is sent only after the privacy preflight passes.",
        "configured_providers": "Configured model providers",
        "no_live_providers": "No live model provider is currently configured. Use the built-in reviewers or ask the administrator to configure a provider.",
        "model_providers": "Model providers",
        "submit_review_job": "Start feedback review",
        "job_queued": "Review job submitted.",
        "job_running": "Generating and routing feedback...",
        "job_completed": "Review completed and saved to your account.",
        "job_failed": "Review job failed: {error}",
        "job_timed_out": "The job is still running. You can leave this page and resume it from Recent jobs.",
        "recent_jobs": "Recent review jobs",
        "job_status": "Status",
        "job_progress": "Progress",
        "generation_mode": "Generation mode",
        "model_trace": "Model execution trace",
        "open_completed_review": "Open completed review",
        "run_selected_essay": "Review selected essay",
        "assignment_workspace": "Assignment workspace",
        "workspace_inventory": "Workspace inventory",
        "password_reset": "Reset password",
        "forgot_password": "Forgot password?",
        "email": "Email",
        "request_reset": "Send reset instructions",
        "reset_requested": "If this email is registered, reset instructions have been sent.",
        "reset_token": "Reset token",
        "set_new_password": "Set new password",
        "password_reset_complete": "Password reset complete. Sign in with your new password.",
        "verify_email": "Verify email",
        "email_verified": "Email verified",
        "email_unverified": "Email not verified",
        "request_verification": "Send verification email",
        "verification_requested": "Verification instructions have been sent.",
        "account_data": "Account data",
        "download_account_data": "Download my account data.json",
        "danger_zone": "Danger zone",
        "delete_account": "Delete account",
        "delete_account_warning": "This permanently deletes your account, essays, review sessions, decisions, audit logs, and submitted feedback.",
        "delete_confirmation": "Type DELETE to confirm",
        "account_deleted": "Your account has been deleted.",
        "security_and_data": "Security and data",
        "student_report": "Student-facing report",
        "student_report_caption": "Contains low-risk auto-released local edits plus feedback explicitly accepted or edited by the teacher. Pending and rejected items are withheld.",
        "download_student_report": "Download student feedback.md",
        "audit_report": "Teacher audit report",
        "assignment": "Assignment",
        "course": "Course",
        "created_at": "Created",
        "review_jobs": "Review jobs",
        "admin_settings": "Administrator settings",
        "settings_admin_only": "Technical diagnostics are available only to configured administrators.",
        "saved_essay_notice": "This review uses a stored anonymized essay from your assignment workspace.",
        "select_saved_or_demo": "Start from a saved essay, a synthetic example, or a blank draft",
        "blank_or_demo": "Synthetic example / blank draft",
        "saved_assignment_essay": "Saved assignment essay",
        "batch_job_summary": "{completed} completed, {running} running, {failed} failed",
        "student_release_status": "Student release status",
        "released_items": "Released items",
        "withheld_items": "Withheld items",
        "prepare_student_report": "Prepare student-facing report",
        "select_review_session": "Select review session",
        "email_delivery_unavailable": "Email delivery is not configured on this deployment. Ask the administrator to configure SMTP before using email verification or password recovery.",
        "words_short": "words",
        "manage_assignments": "Manage assignments",
        "workspace_activity": "Workspace activity",
        "back_to_workspace": "Back to workspace",
    }
)

MAIN_TRANSLATIONS["zh"].update(
    {
        "page_assignments": "课程与作业",
        "assignments_title": "课程与作业",
        "assignments_caption": "先按课程和作业整理匿名化作文，再生成或审核 AI 反馈。",
        "courses": "课程",
        "assignments": "作业",
        "essays": "作文",
        "active_jobs": "运行中任务",
        "new_course": "新建课程",
        "course_name": "课程名称",
        "term": "学期",
        "description_optional": "课程说明（选填）",
        "create_course": "创建课程",
        "course_created": "课程已创建。",
        "select_course": "选择课程",
        "new_assignment": "新建作业",
        "assignment_title": "作业名称",
        "due_date_optional": "截止日期（选填）",
        "create_assignment": "创建作业",
        "assignment_created": "作业已创建。",
        "select_assignment": "选择作业",
        "stored_essays": "已保存的匿名化作文",
        "add_essay": "添加单篇作文",
        "external_essay_id": "匿名作文编号",
        "draft_stage": "草稿阶段",
        "save_essay": "保存作文",
        "essay_saved": "作文已保存。",
        "upload_essay_batch": "上传作文 CSV",
        "save_essay_batch": "保存 CSV 作文",
        "essays_saved": "已保存 {count} 篇作文。",
        "no_courses": "请先创建课程，再整理作业。",
        "no_assignments": "请先创建作业，再添加作文。",
        "no_stored_essays": "该作业下尚未保存匿名化作文。",
        "open_single_review": "进入单篇评审",
        "start_assignment_batch": "评审该作业全部作文",
        "privacy_scan": "隐私预检",
        "privacy_clear": "未检测到高置信度个人身份信息。",
        "privacy_blocked": "请先删除检测到的个人信息，再保存或评审作文。",
        "detected_types": "检测到的信息类型：{types}",
        "generation_source": "反馈生成来源",
        "local_generation": "内置演示评审器",
        "live_generation": "服务器端实时 AI 模型",
        "local_generation_help": "速度快、可复现且不调用外部 API，适合体验完整审核流程。",
        "live_generation_help": "使用服务器已配置的模型；只有通过隐私预检后，作文才会发送给外部模型。",
        "configured_providers": "已配置模型服务商",
        "no_live_providers": "当前没有可用的实时模型服务商。请使用内置评审器，或联系管理员配置服务商。",
        "model_providers": "模型服务商",
        "submit_review_job": "开始反馈评审",
        "job_queued": "评审任务已提交。",
        "job_running": "正在生成并路由反馈……",
        "job_completed": "评审已完成并保存到个人账号。",
        "job_failed": "评审任务失败：{error}",
        "job_timed_out": "任务仍在运行。你可以离开本页，之后从“最近任务”继续查看。",
        "recent_jobs": "最近评审任务",
        "job_status": "任务状态",
        "job_progress": "进度",
        "generation_mode": "生成模式",
        "model_trace": "模型调用记录",
        "open_completed_review": "打开已完成评审",
        "run_selected_essay": "评审所选作文",
        "assignment_workspace": "作业工作区",
        "workspace_inventory": "工作区概览",
        "password_reset": "重置密码",
        "forgot_password": "忘记密码？",
        "email": "邮箱",
        "request_reset": "发送重置说明",
        "reset_requested": "若该邮箱已注册，系统会发送密码重置说明。",
        "reset_token": "重置令牌",
        "set_new_password": "设置新密码",
        "password_reset_complete": "密码已重置，请使用新密码登录。",
        "verify_email": "验证邮箱",
        "email_verified": "邮箱已验证",
        "email_unverified": "邮箱未验证",
        "request_verification": "发送验证邮件",
        "verification_requested": "邮箱验证说明已发送。",
        "account_data": "账号数据",
        "download_account_data": "下载我的账号数据.json",
        "danger_zone": "危险操作",
        "delete_account": "删除账号",
        "delete_account_warning": "此操作会永久删除账号、作文、评审记录、教师决策、审计日志和已提交的意见反馈。",
        "delete_confirmation": "输入 DELETE 确认",
        "account_deleted": "账号已删除。",
        "security_and_data": "安全与数据",
        "student_report": "学生版反馈报告",
        "student_report_caption": "仅包含低风险自动发布的局部修改，以及教师明确接受或修改后的反馈；待处理和已拒绝项目不会出现在报告中。",
        "download_student_report": "下载学生反馈.md",
        "audit_report": "教师审计报告",
        "assignment": "作业",
        "course": "课程",
        "created_at": "创建时间",
        "review_jobs": "评审任务",
        "admin_settings": "管理员设置",
        "settings_admin_only": "技术诊断仅对已配置的管理员开放。",
        "saved_essay_notice": "本次评审使用作业工作区中已保存的匿名化作文。",
        "select_saved_or_demo": "从已保存作文、合成示例或空白草稿开始",
        "blank_or_demo": "合成示例 / 空白草稿",
        "saved_assignment_essay": "作业中已保存作文",
        "batch_job_summary": "{completed} 个已完成，{running} 个运行中，{failed} 个失败",
        "student_release_status": "学生发布状态",
        "released_items": "已发布反馈",
        "withheld_items": "暂不发布反馈",
        "prepare_student_report": "生成学生版报告",
        "select_review_session": "选择评审记录",
        "email_delivery_unavailable": "当前部署尚未配置邮件发送服务。使用邮箱验证或找回密码前，请联系管理员配置 SMTP。",
        "words_short": "词",
        "manage_assignments": "管理课程与作业",
        "workspace_activity": "工作区动态",
        "back_to_workspace": "返回工作台",
    }
)


def ui_lang() -> str:
    return safe_str(st.session_state.get("ui_language") or "en")


def mt(key: str, **kwargs: Any) -> str:
    text = MAIN_TRANSLATIONS.get(ui_lang(), MAIN_TRANSLATIONS["en"]).get(key, key)
    return text.format(**kwargs) if kwargs else text


def logo_data_uri() -> str:
    if not LOGO_PATH.exists():
        return ""
    encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def render_sidebar_brand() -> None:
    logo = logo_data_uri()
    image_markup = f'<img src="{logo}" alt="">' if logo else ""
    st.sidebar.markdown(
        f"""
        <div class="sidebar-brand">
            {image_markup}
            <div>
                <div class="sidebar-brand__name">ConsensusScope</div>
                <div class="sidebar-brand__tagline">{html.escape(mt("sidebar_tagline"))}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_header(title_key: str, caption_key: Optional[str] = None) -> None:
    caption = mt(caption_key) if caption_key else ""
    caption_markup = f"<p>{html.escape(caption)}</p>" if caption else ""
    st.markdown(
        f"""
        <div class="page-heading">
            <div>
                <h1>{html.escape(mt(title_key))}</h1>
                {caption_markup}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def navigate_to(page_key: str) -> None:
    st.session_state["pending_page_key"] = page_key


def render_workflow_strip() -> None:
    steps = [mt("step_input"), mt("step_generate"), mt("step_route"), mt("step_review"), mt("step_export")]
    markup = "".join(f'<div class="workflow-step">{html.escape(step)}</div>' for step in steps)
    st.markdown(f'<div class="workflow-strip">{markup}</div>', unsafe_allow_html=True)


def render_footer() -> None:
    st.markdown(
        f'<div class="app-footer">{html.escape(mt("footer_notice", version=APP_VERSION))}</div>',
        unsafe_allow_html=True,
    )


def decision_state_key(session_id: Any, feedback_item_id: Any) -> str:
    session_text = safe_str(session_id)
    item_text = safe_str(feedback_item_id)
    return f"{session_text}:{item_text}" if session_text else item_text


VALUE_LABELS_EN = {
    "auto_accept": "Auto accept",
    "teacher_review": "Teacher review",
    "needs_more_evidence": "Needs more evidence",
    "reject": "Reject",
    "pending": "Pending",
    "accept": "Accept",
    "edit": "Edit",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
    "urgent": "Urgent",
    "normal": "Normal",
    "grammar": "Grammar",
    "vocabulary": "Vocabulary",
    "sentence_structure": "Sentence structure",
    "coherence": "Coherence",
    "organization": "Organization",
    "task_response": "Task response",
    "argument_clarity": "Argument clarity",
    "tone_register": "Tone and register",
    "meaning_change": "Meaning change",
    "overcorrection": "Overcorrection",
    "unsupported_claim": "Unsupported claim",
    "introduces_new_argument": "Introduces a new argument",
    "low_model_agreement": "Low model agreement",
    "missing_evidence": "Missing evidence",
    "conflict_evidence": "Conflicting evidence",
    "broad_target": "Broad target span",
    "parse_error": "Parse error",
    "harsh_feedback": "Potentially harsh wording",
    "local_edit": "Local edit",
    "meaning_preservation": "Meaning preservation",
    "content_grounding": "Content grounding",
    "pedagogical_tone": "Pedagogical tone",
    "specificity": "Feedback specificity",
    "model_agreement": "Model agreement",
    "preserves_meaning": "Preserves meaning",
    "changes_meaning": "Changes meaning",
    "conflict": "Conflict",
    "none": "None",
    "bug": "Problem report",
    "feature": "Feature request",
    "usability": "Usability",
    "output_quality": "Feedback quality",
    "other": "Other",
}


FIELD_LABELS_ZH = {
    "essay_id": "作文 ID",
    "feedback_item_id": "反馈项 ID",
    "target_span": "目标片段",
    "model_source": "模型来源",
    "issue_type_predicted": "预测问题类型",
    "issue_type": "问题类型",
    "ai_suggestion": "AI 建议",
    "risk_level": "风险等级",
    "recommended_action": "推荐动作",
    "risk_score": "风险分数",
    "review_confidence": "复核置信度",
    "evidence_signal": "证据信号",
    "review_priority": "复核优先级",
    "risk_reasons": "风险原因",
    "meaning_preservation_predicted": "是否保留原意",
    "review_explanation": "复核解释",
    "safety_graph_active_dimensions": "安全图谱维度",
    "safety_graph_active_signals": "安全图谱信号",
    "safety_graph_path": "安全图谱路径",
    "safety_graph_summary": "安全图谱摘要",
    "safety_graph_nodes": "安全图谱节点",
    "safety_graph_edges": "安全图谱边",
    "teacher_action": "教师动作",
    "dataset_run": "数据集运行",
    "parallel_records": "平行句记录",
    "gold_edits": "Gold 修改数",
    "feedback_candidates": "反馈候选数",
    "auto_share": "自动接受占比",
    "auto_acc": "自动接受准确率",
    "review_share": "复核占比",
    "errors_reviewed": "错误送审占比",
    "policy": "策略",
    "items": "项目数",
    "assignment_prompt": "作文题目",
    "student_level": "学生水平",
    "essay_text_anonymized": "匿名作文文本",
    "word_count": "词数",
    "draft_stage": "草稿阶段",
    "pii_removed": "已移除个人信息",
    "dataset": "数据集",
    "sample_id": "样本 ID",
    "id": "ID",
    "question": "问题",
    "gold_answer": "标准答案",
    "gold_label": "标准标签",
    "task_type": "任务类型",
    "method": "方法",
    "final_answer": "最终答案",
    "correct_offline": "离线正确性",
    "risk_or_confidence": "风险 / 置信度",
    "reasoning": "理由",
    "provider": "服务商",
    "model": "模型",
    "answer": "回答",
    "normalized_answer": "归一化回答",
    "confidence": "置信度",
    "evidence_quality": "证据质量",
    "evidence": "证据",
    "request_error": "请求错误",
    "parse_error": "解析错误",
    "latency_sec": "延迟（秒）",
    "consensus_state": "一致性状态",
    "safety_dimensions": "安全维度",
    "items": "项目数",
    "set": "评估集合",
    "action_accuracy": "动作准确率",
    "risk_accuracy": "风险准确率",
    "high_risk_recall": "高风险召回",
    "auto_accept_precision": "自动接受精确率",
    "expected_risk_level": "期望风险等级",
    "expected_action": "期望动作",
    "expected_reason": "期望原因",
    "action_match": "动作是否匹配",
    "risk_match": "风险是否匹配",
    "source": "来源",
    "synthetic_essays": "合成作文数",
    "feedback_items": "反馈项数",
    "ai_review_stress_cases": "压力测试案例数",
    "auto_accept": "自动接受",
    "teacher_review": "教师复核",
    "high_risk": "高风险",
    "medium_risk": "中风险",
    "low_risk": "低风险",
    "mean_risk_score": "平均风险分数",
    "historical_accuracy_smoothed": "平滑历史准确率",
    "avg_confidence": "平均置信度",
    "calls": "调用次数",
    "notes": "备注",
    "priority": "优先级",
    "span": "片段",
    "selected_suggestion": "选中建议",
    "agreement": "一致性",
    "kg_supported": "知识库支持",
    "rationale": "理由",
    "work": "作品",
    "concept": "概念",
    "relation": "关系",
    "value": "内容",
    "reviewer_role": "评审角色",
}

VALUE_LABELS_ZH = {
    "auto_accept": "自动接受",
    "teacher_review": "教师复核",
    "needs_more_evidence": "需要更多证据",
    "reject": "拒绝",
    "pending": "待处理",
    "accept": "接受",
    "edit": "修改",
    "high": "高",
    "medium": "中",
    "low": "低",
    "urgent": "紧急",
    "normal": "普通",
    "grammar": "语法",
    "vocabulary": "词汇",
    "sentence_structure": "句子结构",
    "coherence": "连贯性",
    "organization": "结构组织",
    "task_response": "任务回应",
    "argument_clarity": "论证清晰度",
    "tone_register": "语气 / 语域",
    "meaning_change": "改变原意",
    "overcorrection": "过度修改",
    "low_model_agreement": "模型一致性偏低",
    "missing_evidence": "缺少证据",
    "conflict_evidence": "证据冲突",
    "broad_target": "目标片段过宽",
    "parse_error": "解析失败",
    "harsh_feedback": "语气可能过重",
    "mechanical_rephrase": "机械改写",
    "interpretive_claim": "解释性判断",
    "factual_claim": "事实性判断",
    "local_language_edit": "局部语言修改",
    "wrong_correction": "错误修改",
    "introduces_new_argument": "引入新论点",
    "too_vague": "过于笼统",
    "too_harsh": "语气过重",
    "unsupported_claim": "无依据内容",
    "task_mismatch": "偏离任务",
    "local_edit": "局部语言修改",
    "meaning_preservation": "保留原意",
    "content_grounding": "内容依据",
    "pedagogical_tone": "教学语气",
    "specificity": "反馈具体性",
    "model_agreement": "模型一致性",
    "preserves_meaning": "保留原意",
    "changes_meaning": "改变原意",
    "unclear": "不确定",
    "true": "是",
    "false": "否",
    "True": "是",
    "False": "否",
    "combined": "合并集合",
    "synthetic_esl_writing_demo": "合成 ESL 写作 demo",
    "false_consensus": "错误共识",
    "minority_correct": "少数正确",
    "true_consensus": "真实共识",
    "high_disagreement": "高分歧",
    "confidence_mismatch": "置信度不匹配",
    "bug": "问题报告",
    "feature": "功能建议",
    "usability": "使用体验",
    "output_quality": "反馈质量",
    "other": "其他",
}


def field_label(column: Any) -> str:
    text = safe_str(column)
    if ui_lang() == "zh":
        return FIELD_LABELS_ZH.get(text, text)
    acronyms = {"ai": "AI", "api": "API", "id": "ID", "pii": "PII", "csv": "CSV"}
    parts = [acronyms.get(part, part) for part in text.split("_")]
    label = " ".join(parts)
    return label[:1].upper() + label[1:] if label else text


def value_label(value: Any) -> Any:
    text = safe_str(value)
    if not text:
        return value
    if ";" in text:
        return "; ".join(value_label(part.strip()) for part in text.split(";"))
    labels = VALUE_LABELS_ZH if ui_lang() == "zh" else VALUE_LABELS_EN
    if text in labels:
        return labels[text]
    if ui_lang() == "en" and "_" in text and " " not in text:
        return field_label(text)
    return value


def value_list_label(value: Any) -> str:
    text = safe_str(value)
    if not text:
        return mt("none")
    parts = [part.strip() for part in text.replace(";", ",").split(",") if part.strip()]
    return ", ".join(safe_str(value_label(part)) for part in parts)


def graph_path_label(value: Any) -> str:
    parts = [part.strip() for part in safe_str(value).split("->") if part.strip()]
    return " → ".join(safe_str(value_label(part)) for part in parts)


def display_frame(df: pd.DataFrame, public: bool = False) -> pd.DataFrame:
    if df.empty:
        return df
    display = public_display_frame(df) if public else df.copy()
    for col in display.columns:
        if display[col].dtype == "object":
            display[col] = display[col].map(value_label)
        elif ui_lang() == "zh" and display[col].dtype == "bool":
            display[col] = display[col].map(lambda value: "是" if value else "否")
    display = display.rename(columns={col: field_label(col) for col in display.columns})
    return display


def display_method_label(label: Any) -> str:
    text = safe_str(label)
    if ui_lang() != "zh":
        return text
    return {
        "Majority Vote": "多数投票",
        "Fixed Judge": "固定裁判",
        "Dynamic Rule-Based Judge": "动态规则裁决",
    }.get(text, text)


def english_note(value: Any) -> str:
    text = safe_str(value)
    translated = NOTE_TRANSLATIONS.get(text, text)
    if any("\u4e00" <= char <= "\u9fff" for char in translated):
        return "Saved judge rationale is available in the CSV; non-English provider text is hidden in the public UI."
    return translated


def public_text(value: Any) -> Any:
    text = safe_str(value)
    if not text:
        return value
    if text == "\u65e0":
        return mt("no_answer")
    if any("\u4e00" <= char <= "\u9fff" for char in text):
        return PUBLIC_TEXT_PLACEHOLDER
    return value


def public_display_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    display = df.copy()
    for col in display.columns:
        if display[col].dtype == "object":
            display[col] = display[col].map(public_text)
    return display


def configured_value(key: str) -> str:
    value = os.getenv(key, "")
    if value:
        return value
    local_secret_paths = [
        Path.home() / ".streamlit" / "secrets.toml",
        ROOT / ".streamlit" / "secrets.toml",
    ]
    if not any(path.exists() for path in local_secret_paths) and not truthy(os.getenv("STREAMLIT_SHARING_MODE", "")):
        return ""
    try:
        secret_value = st.secrets.get(key, "")
    except Exception:
        secret_value = ""
    return str(secret_value) if secret_value else ""


def storage_backend_name() -> str:
    if st.session_state.get("account_user"):
        return mt("persistent_storage")
    return mt("session_only")


def backend_api_url() -> str:
    return configured_value("CONSENSUS_SCOPE_BACKEND_URL") or "http://127.0.0.1:7864"


@st.cache_data(ttl=15, show_spinner=False)
def backend_healthcheck(url: str) -> Dict[str, Any]:
    try:
        response = requests.get(f"{url.rstrip('/')}/health", timeout=2)
        response.raise_for_status()
        return {"ok": True, "payload": response.json(), "error": ""}
    except Exception as exc:
        return {"ok": False, "payload": {}, "error": str(exc)}


def current_account_user() -> Dict[str, Any]:
    user = st.session_state.get("account_user")
    return user if isinstance(user, dict) else {}


def clear_account_session() -> None:
    st.session_state["account_token"] = ""
    st.session_state["account_user"] = None
    st.session_state["active_review_session_id"] = ""
    st.session_state["teacher_decisions"] = {}
    st.session_state["saved_teacher_decisions"] = {}


def store_account_session(payload: Dict[str, Any]) -> None:
    st.session_state["account_token"] = safe_str(payload.get("access_token"))
    st.session_state["account_user"] = payload.get("user") or None


def backend_request(
    method: str,
    endpoint: str,
    *,
    payload: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    authenticated: bool = True,
    timeout: int = 60,
) -> tuple[Optional[Dict[str, Any]], str]:
    headers: Dict[str, str] = {"Accept": "application/json"}
    if authenticated:
        token = safe_str(st.session_state.get("account_token"))
        if not token:
            return None, "authentication required"
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.request(
            method,
            f"{backend_api_url().rstrip('/')}{endpoint}",
            json=payload,
            params=params,
            headers=headers,
            timeout=timeout,
        )
    except Exception as exc:
        return None, str(exc)
    if response.status_code == 401 and authenticated:
        clear_account_session()
    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        if isinstance(detail, dict):
            message = safe_str(detail.get("message"))
            findings = detail.get("findings") or []
            finding_types = sorted(
                {
                    safe_str(item.get("type"))
                    for item in findings
                    if isinstance(item, dict) and safe_str(item.get("type"))
                }
            )
            if finding_types:
                message = f"{message} ({', '.join(finding_types)})" if message else ", ".join(finding_types)
            detail = message or json.dumps(detail, ensure_ascii=False)
        return None, safe_str(detail) or f"HTTP {response.status_code}"
    if not response.content:
        return {}, ""
    try:
        return response.json(), ""
    except Exception:
        return {"text": response.text}, ""


def privacy_preflight(text: str) -> tuple[Optional[Dict[str, Any]], str]:
    return backend_request("POST", "/api/privacy/check", payload={"text": text})


def configured_feedback_providers() -> List[Dict[str, Any]]:
    payload, _ = backend_request("GET", "/api/providers")
    providers = payload.get("providers", []) if payload else []
    return providers if isinstance(providers, list) else []


def wait_for_review_job(
    job_id: str,
    *,
    timeout_seconds: int = 240,
    progress_label: Optional[str] = None,
) -> tuple[Optional[Dict[str, Any]], str]:
    status_slot = st.empty()
    progress_bar = st.progress(0, text=progress_label or mt("job_running"))
    deadline = time.monotonic() + timeout_seconds
    last_job: Dict[str, Any] = {}
    while time.monotonic() < deadline:
        payload, error = backend_request("GET", f"/api/review/jobs/{job_id}", timeout=15)
        if not payload:
            progress_bar.empty()
            status_slot.empty()
            return None, error
        last_job = payload.get("job", {})
        status_value = safe_str(last_job.get("status")) or "queued"
        progress_value = int(last_job.get("progress") or 0)
        progress_bar.progress(
            max(0, min(100, progress_value)),
            text=f"{mt('job_running')} {progress_value}%",
        )
        status_slot.caption(f"{mt('job_status')}: {value_label(status_value)}")
        if status_value == "completed":
            progress_bar.empty()
            status_slot.empty()
            return last_job, ""
        if status_value == "failed":
            progress_bar.empty()
            status_slot.empty()
            return None, safe_str(last_job.get("error_message")) or "review job failed"
        time.sleep(0.6)
    progress_bar.empty()
    status_slot.empty()
    return last_job or None, mt("job_timed_out")


def wait_for_review_jobs(
    job_ids: List[str],
    *,
    timeout_seconds: int = 600,
) -> tuple[List[Dict[str, Any]], str]:
    status_slot = st.empty()
    progress_bar = st.progress(0, text=mt("job_running"))
    deadline = time.monotonic() + timeout_seconds
    jobs_by_id: Dict[str, Dict[str, Any]] = {}
    while time.monotonic() < deadline:
        for job_id in job_ids:
            current = jobs_by_id.get(job_id, {})
            if current.get("status") in {"completed", "failed"}:
                continue
            payload, error = backend_request("GET", f"/api/review/jobs/{job_id}", timeout=15)
            if not payload:
                progress_bar.empty()
                status_slot.empty()
                return list(jobs_by_id.values()), error
            jobs_by_id[job_id] = payload.get("job", {})
        jobs = [jobs_by_id.get(job_id, {}) for job_id in job_ids]
        completed = sum(job.get("status") == "completed" for job in jobs)
        failed = sum(job.get("status") == "failed" for job in jobs)
        running = len(job_ids) - completed - failed
        mean_progress = int(
            sum(int(job.get("progress") or 0) for job in jobs) / max(1, len(job_ids))
        )
        progress_bar.progress(mean_progress, text=f"{mt('job_running')} {mean_progress}%")
        status_slot.caption(
            mt("batch_job_summary", completed=completed, running=running, failed=failed)
        )
        if completed + failed == len(job_ids):
            progress_bar.empty()
            status_slot.empty()
            if failed:
                errors = [
                    safe_str(job.get("error_message"))
                    for job in jobs
                    if job.get("status") == "failed"
                ]
                return jobs, "; ".join(item for item in errors if item) or "one or more jobs failed"
            return jobs, ""
        time.sleep(0.7)
    progress_bar.empty()
    status_slot.empty()
    return [jobs_by_id.get(job_id, {}) for job_id in job_ids], mt("job_timed_out")


def batch_result_from_completed_jobs(jobs: List[Dict[str, Any]]) -> tuple[Optional[Dict[str, Any]], str]:
    sessions: List[Dict[str, Any]] = []
    merged_frames: List[pd.DataFrame] = []
    comparison_frames: List[pd.DataFrame] = []
    summary_rows: List[Dict[str, Any]] = []
    for job in jobs:
        session_id = safe_str(job.get("session_id"))
        if not session_id:
            continue
        loaded, error = load_personal_review(session_id)
        if not loaded:
            return None, error
        sessions.append(
            {
                "session_id": session_id,
                "essay_id": loaded.get("essay_id"),
                "summary": loaded.get("summary", {}),
            }
        )
        merged = loaded.get("merged", pd.DataFrame())
        comparison = loaded.get("comparison", pd.DataFrame())
        if isinstance(merged, pd.DataFrame) and not merged.empty:
            merged_frames.append(merged)
        if isinstance(comparison, pd.DataFrame) and not comparison.empty:
            comparison_frames.append(comparison)
        summary_rows.append({"essay_id": loaded.get("essay_id"), **loaded.get("summary", {})})
    if not sessions:
        return None, "no completed review session was returned"
    merged_all = pd.concat(merged_frames, ignore_index=True) if merged_frames else pd.DataFrame()
    comparison_all = pd.concat(comparison_frames, ignore_index=True) if comparison_frames else pd.DataFrame()
    return {
        "batch_id": f"job-batch-{int(time.time())}",
        "sessions": sessions,
        "summary": pd.DataFrame(summary_rows),
        "merged": merged_all,
        "comparison": comparison_all,
        "report": "ConsensusScope batch review. Download the routed feedback table for item-level details.",
    }, ""


def query_parameter(name: str) -> str:
    try:
        value = st.query_params.get(name, "")
    except Exception:
        value = ""
    if isinstance(value, list):
        value = value[0] if value else ""
    return safe_str(value)


def handle_account_action_query() -> None:
    action = query_parameter("action")
    token = query_parameter("token")
    if action != "verify_email" or not token:
        return
    marker = f"verify:{token[:12]}"
    if st.session_state.get("handled_account_action") == marker:
        return
    st.session_state["handled_account_action"] = marker
    data, error = backend_request(
        "POST",
        "/api/auth/email-verification/confirm",
        params={"token": token},
        authenticated=False,
    )
    if data:
        st.success(mt("email_verified"))
        if current_account_user():
            refreshed, _ = backend_request("GET", "/api/auth/me")
            if refreshed:
                st.session_state["account_user"] = refreshed.get("user")
    else:
        st.error(mt("auth_error", error=error))


def render_account_gate() -> bool:
    if current_account_user() and safe_str(st.session_state.get("account_token")):
        return True

    health = backend_healthcheck(backend_api_url())
    st.markdown(
        f"""
        <div class="auth-intro">
            <h1>{html.escape(mt("account_access"))}</h1>
            <p>{html.escape(mt("account_access_caption"))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _, auth_column, _ = st.columns([0.65, 1.7, 0.65], gap="large")
    with auth_column:
        st.info(mt("privacy_notice"))
        if not health["ok"]:
            st.error(mt("backend_required"))
            st.code(health["error"], language="text")
            return False

        login_tab, register_tab, reset_tab = st.tabs(
            [mt("login_tab"), mt("register_tab"), mt("password_reset")]
        )
        with login_tab:
            with st.form("account_login_form"):
                username = st.text_input(mt("username"), key="login_username")
                password = st.text_input(mt("password"), type="password", key="login_password")
                submitted = st.form_submit_button(mt("sign_in"), use_container_width=True, type="primary")
            if submitted:
                data, error = backend_request(
                    "POST",
                    "/api/auth/login",
                    payload={"username": username, "password": password},
                    authenticated=False,
                )
                if data:
                    store_account_session(data)
                    st.rerun()
                else:
                    st.error(mt("auth_error", error=error))

        with register_tab:
            st.caption(mt("password_rules"))
            with st.form("account_register_form"):
                username = st.text_input(mt("username"), key="register_username")
                display_name = st.text_input(mt("display_name"), key="register_display_name")
                email = st.text_input(mt("email_optional"), key="register_email")
                password = st.text_input(mt("password"), type="password", key="register_password")
                confirmation = st.text_input(
                    mt("confirm_password"),
                    type="password",
                    key="register_password_confirmation",
                )
                privacy_acknowledged = st.checkbox(mt("privacy_ack"), key="register_privacy_ack")
                submitted = st.form_submit_button(mt("create_account"), use_container_width=True, type="primary")
            if submitted:
                if password != confirmation:
                    st.error(mt("password_mismatch"))
                else:
                    data, error = backend_request(
                        "POST",
                        "/api/auth/register",
                        payload={
                            "username": username,
                            "password": password,
                            "display_name": display_name,
                            "email": email or None,
                            "privacy_acknowledged": privacy_acknowledged,
                        },
                        authenticated=False,
                    )
                    if data:
                        store_account_session(data)
                        st.rerun()
                    else:
                        st.error(mt("auth_error", error=error))

        with reset_tab:
            reset_token = query_parameter("token") if query_parameter("action") == "reset_password" else ""
            if reset_token:
                st.caption(mt("password_rules"))
                with st.form("password_reset_confirm_form"):
                    new_password = st.text_input(mt("new_password"), type="password")
                    confirmation = st.text_input(mt("confirm_password"), type="password")
                    submitted = st.form_submit_button(mt("set_new_password"), use_container_width=True, type="primary")
                if submitted:
                    if new_password != confirmation:
                        st.error(mt("password_mismatch"))
                    else:
                        data, error = backend_request(
                            "POST",
                            "/api/auth/password-reset/confirm",
                            payload={"token": reset_token, "new_password": new_password},
                            authenticated=False,
                        )
                        if data:
                            st.success(mt("password_reset_complete"))
                            try:
                                st.query_params.clear()
                            except Exception:
                                pass
                        else:
                            st.error(mt("auth_error", error=error))
            else:
                with st.form("password_reset_request_form"):
                    email = st.text_input(mt("email"), key="password_reset_email")
                    submitted = st.form_submit_button(mt("request_reset"), use_container_width=True)
                if submitted:
                    data, error = backend_request(
                        "POST",
                        "/api/auth/password-reset/request",
                        payload={"email": email},
                        authenticated=False,
                    )
                    if data:
                        st.success(mt("reset_requested"))
                        if not data.get("email_delivery"):
                            st.info(mt("email_delivery_unavailable"))
                    else:
                        st.error(mt("auth_error", error=error))
    return False


def render_account_sidebar() -> None:
    user = current_account_user()
    if not user:
        return
    display_name = safe_str(user.get("display_name")) or safe_str(user.get("username"))
    username = safe_str(user.get("username"))
    initial = html.escape((display_name or username or "U")[:1].upper())
    st.sidebar.markdown(
        f"""
        <div class="sidebar-account">
            <div class="account-row">
                <div class="account-avatar">{initial}</div>
                <div>
                    <div class="account-name">{html.escape(display_name)}</div>
                    <div class="account-username">@{html.escape(username)}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.sidebar.button(mt("sign_out"), use_container_width=True):
        backend_request("POST", "/api/auth/logout")
        clear_account_session()
        st.rerun()


def render_sidebar_service() -> None:
    health = backend_healthcheck(backend_api_url())
    status_class = "" if health["ok"] else " offline"
    status_text = mt("service_online") if health["ok"] else mt("service_offline")
    st.sidebar.markdown(
        f"""
        <div class="sidebar-service">
            <div class="service-line">
                <span class="service-dot{status_class}"></span>
                <span>{html.escape(status_text)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def single_result_from_backend(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "session_id": payload.get("session_id", ""),
        "batch_id": payload.get("batch_id"),
        "essay_id": payload.get("essay_id", ""),
        "summary": payload.get("summary", {}),
        "merged": pd.DataFrame(payload.get("feedback_items", [])),
        "comparison": pd.DataFrame(payload.get("comparison", [])),
        "report": payload.get("report", ""),
        "essay_text": payload.get("essay_text", ""),
        "assignment_id": payload.get("assignment_id"),
        "essay_record_id": payload.get("essay_record_id"),
        "generation_mode": payload.get("generation_mode", "local"),
        "providers": payload.get("providers", []),
        "model_metadata": payload.get("model_metadata", {}),
    }


def batch_result_from_backend(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "batch_id": payload.get("batch_id", ""),
        "sessions": payload.get("sessions", []),
        "summary": pd.DataFrame(payload.get("summary", [])),
        "merged": pd.DataFrame(payload.get("feedback_items", [])),
        "comparison": pd.DataFrame(payload.get("comparison", [])),
        "report": payload.get("report", ""),
    }


def load_personal_review(session_id: str) -> tuple[Optional[Dict[str, Any]], str]:
    session, error = backend_request("GET", f"/api/sessions/{session_id}")
    if not session:
        return None, error
    feedback, feedback_error = backend_request("GET", f"/api/sessions/{session_id}/feedback")
    if feedback is None:
        return None, feedback_error
    payload = {
        "session_id": session_id,
        "batch_id": session.get("batch_id"),
        "essay_id": session.get("essay_id", ""),
        "summary": session.get("summary", {}),
        "feedback_items": feedback.get("feedback_items", []),
        "comparison": session.get("comparison", []),
        "report": session.get("report_text", ""),
        "essay_text": session.get("essay_text", ""),
        "assignment_id": session.get("assignment_id"),
        "essay_record_id": session.get("essay_record_id"),
        "generation_mode": session.get("generation_mode", "local"),
        "providers": session.get("providers", []),
        "model_metadata": session.get("model_metadata", {}),
    }
    return single_result_from_backend(payload), ""


def resume_personal_review(session_id: str) -> None:
    loaded, error = load_personal_review(session_id)
    if not loaded:
        st.session_state["workspace_error"] = error
        return
    st.session_state["esl_single_result"] = loaded
    st.session_state["esl_batch_result"] = None
    st.session_state["active_review_session_id"] = session_id
    decisions_payload, _ = backend_request(
        "GET",
        "/api/teacher/decisions",
        params={"session_id": session_id},
    )
    decisions = decisions_payload.get("decisions", []) if decisions_payload else []
    saved_decisions = {
        decision_state_key(session_id, item.get("feedback_item_id")): safe_str(item.get("teacher_action"))
        for item in decisions
    }
    st.session_state["teacher_decisions"] = saved_decisions.copy()
    st.session_state["saved_teacher_decisions"] = saved_decisions.copy()
    navigate_to("page_single")


def truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@st.cache_data(show_spinner=False)
def read_table(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    try:
        if p.suffix.lower() == ".jsonl":
            return pd.read_json(p, lines=True)
        return pd.read_csv(p)
    except Exception as exc:
        st.warning(mt("read_error", path=p, error=exc))
        return pd.DataFrame()


def load_outputs() -> pd.DataFrame:
    outputs = read_table(str(DATA_PATHS["outputs_csv"]))
    if not outputs.empty:
        return outputs
    return read_table(str(DATA_PATHS["outputs_jsonl"]))


@st.cache_data(show_spinner=False)
def read_json_records(path: str) -> List[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as exc:
        st.warning(mt("read_error", path=p, error=exc))
        return []




def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --cs-bg: #f3f5f7;
            --cs-surface: #ffffff;
            --cs-surface-soft: #f8fafc;
            --cs-text: #111827;
            --cs-muted: #64748b;
            --cs-border: #d8e0e9;
            --cs-border-strong: #bcc8d6;
            --cs-sidebar: #111827;
            --cs-sidebar-active: #23314a;
            --cs-blue: #2563eb;
            --cs-blue-dark: #1746a2;
            --cs-blue-soft: #edf4ff;
            --cs-green: #16815d;
            --cs-green-soft: #edf8f3;
            --cs-amber: #a85d00;
            --cs-amber-soft: #fff7e8;
            --cs-red: #c23a4b;
            --cs-red-soft: #fff0f2;
            --cs-shadow: 0 8px 22px rgba(15, 23, 42, 0.07);
            --cs-radius: 8px;
        }

        html, body, [class*="css"] {
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            letter-spacing: 0;
        }

        .stApp {
            background: var(--cs-bg);
            color: var(--cs-text);
        }

        header[data-testid="stHeader"] {
            height: 2.75rem;
            background: var(--cs-bg);
            border-bottom: 1px solid rgba(216, 224, 233, 0.72);
        }

        #MainMenu,
        footer {
            visibility: hidden;
        }

        [data-testid="stToolbarActions"],
        [data-testid="stAppDeployButton"],
        [data-testid="stHeaderActionElements"] {
            display: none;
        }

        .block-container {
            max-width: 1380px;
            padding: 1.1rem 2rem 3rem;
        }

        .main .block-container > div {
            display: flex;
            flex-direction: column;
            gap: 0.7rem;
        }

        section[data-testid="stSidebar"] {
            width: 286px !important;
            min-width: 286px !important;
            background: var(--cs-sidebar);
            border-right: 1px solid #263247;
        }

        section[data-testid="stSidebar"][aria-expanded="false"] {
            width: 0 !important;
            min-width: 0 !important;
            border-right: 0;
        }

        section[data-testid="stSidebar"] > div {
            padding-top: 0.85rem;
        }

        section[data-testid="stSidebar"] * {
            letter-spacing: 0;
        }

        .sidebar-brand {
            display: flex;
            align-items: center;
            gap: 11px;
            padding: 2px 2px 15px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.12);
            margin-bottom: 14px;
        }

        .sidebar-brand img {
            width: 40px;
            height: 40px;
            border-radius: 8px;
            flex: 0 0 auto;
        }

        .sidebar-brand__name {
            color: #ffffff;
            font-size: 1rem;
            font-weight: 780;
            line-height: 1.2;
        }

        .sidebar-brand__tagline {
            color: #aebbd0;
            font-size: 0.7rem;
            line-height: 1.35;
            margin-top: 3px;
        }

        .sidebar-section-label {
            color: #94a3b8;
            font-size: 0.69rem;
            font-weight: 760;
            text-transform: uppercase;
            margin: 13px 2px 7px;
        }

        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] small {
            color: #dbe4f1;
        }

        section[data-testid="stSidebar"] [data-testid="stSelectbox"] label,
        section[data-testid="stSidebar"] [data-testid="stMultiSelect"] label,
        section[data-testid="stSidebar"] [data-testid="stTextInput"] label,
        section[data-testid="stSidebar"] [data-testid="stCheckbox"] label {
            color: #cbd5e1 !important;
            font-size: 0.78rem;
            font-weight: 650;
        }

        section[data-testid="stSidebar"] div[data-baseweb="select"] > div,
        section[data-testid="stSidebar"] input,
        section[data-testid="stSidebar"] textarea {
            background: #1c2739 !important;
            border-color: #394963 !important;
            border-radius: 6px !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }

        section[data-testid="stSidebar"] div[data-baseweb="select"] *,
        section[data-testid="stSidebar"] div[data-baseweb="input"] * {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }

        section[data-testid="stSidebar"] [data-testid="stRadio"] > label {
            display: none;
        }

        section[data-testid="stSidebar"] [role="radiogroup"] {
            gap: 4px;
        }

        section[data-testid="stSidebar"] [role="radiogroup"] > label {
            min-height: 39px;
            margin: 0;
            padding: 8px 10px;
            border: 0;
            border-radius: 6px;
            background: transparent;
            color: #cbd5e1 !important;
        }

        section[data-testid="stSidebar"] [role="radiogroup"] > label:hover {
            background: rgba(255, 255, 255, 0.06);
            color: #ffffff !important;
        }

        section[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {
            background: var(--cs-sidebar-active);
            box-shadow: inset 3px 0 0 #78a7ff;
            color: #ffffff !important;
        }

        section[data-testid="stSidebar"] [role="radiogroup"] > label > div:first-child {
            display: none;
        }

        section[data-testid="stSidebar"] [role="radiogroup"] > label p {
            color: #cbd5e1 !important;
            -webkit-text-fill-color: #cbd5e1 !important;
            font-size: 0.82rem;
            font-weight: 650;
        }

        section[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) p {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }

        .sidebar-service,
        .sidebar-account {
            border-top: 1px solid rgba(255, 255, 255, 0.12);
            padding: 13px 2px 2px;
            margin-top: 12px;
        }

        .service-line {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #cbd5e1;
            font-size: 0.74rem;
        }

        .service-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #34d399;
            box-shadow: 0 0 0 3px rgba(52, 211, 153, 0.14);
        }

        .service-dot.offline {
            background: #fb7185;
            box-shadow: 0 0 0 3px rgba(251, 113, 133, 0.14);
        }

        .account-row {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
        }

        .account-avatar {
            width: 34px;
            height: 34px;
            border-radius: 50%;
            display: grid;
            place-items: center;
            background: #334155;
            color: #ffffff;
            font-size: 0.82rem;
            font-weight: 760;
        }

        .account-name {
            color: #ffffff;
            font-size: 0.82rem;
            font-weight: 700;
            line-height: 1.2;
        }

        .account-username {
            color: #94a3b8;
            font-size: 0.7rem;
            margin-top: 2px;
        }

        section[data-testid="stSidebar"] .stButton > button {
            min-height: 36px;
            border-radius: 6px !important;
            border: 1px solid #465770 !important;
            background: #1c2739 !important;
            color: #eef4ff !important;
            box-shadow: none !important;
        }

        .topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 18px;
            background: var(--cs-surface);
            border: 1px solid var(--cs-border);
            border-radius: var(--cs-radius);
            padding: 14px 16px;
            margin-bottom: 8px;
        }

        .title {
            color: var(--cs-text);
            font-size: 1.08rem;
            font-weight: 780;
            line-height: 1.2;
        }

        .subtitle {
            color: var(--cs-muted);
            font-size: 0.78rem;
            line-height: 1.4;
            margin-top: 4px;
        }

        .topbar-status {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 7px;
            flex-wrap: wrap;
        }

        .ui-pill {
            min-height: 26px;
            display: inline-flex;
            align-items: center;
            border-radius: 6px;
            padding: 0 9px;
            background: var(--cs-surface-soft);
            border: 1px solid var(--cs-border);
            color: #344256;
            font-size: 0.7rem;
            font-weight: 680;
            white-space: nowrap;
        }

        .ui-pill.is-online {
            background: var(--cs-green-soft);
            border-color: #bfe2d2;
            color: #116347;
        }

        .page-heading {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 20px;
            margin: 8px 0 12px;
        }

        .page-heading h1 {
            color: var(--cs-text);
            font-size: 1.72rem;
            font-weight: 790;
            line-height: 1.18;
            margin: 0;
        }

        .page-heading p {
            max-width: 880px;
            color: var(--cs-muted);
            font-size: 0.87rem;
            line-height: 1.55;
            margin: 7px 0 0;
        }

        .section-title {
            color: var(--cs-text);
            font-size: 1.04rem;
            font-weight: 760;
            margin: 14px 0 10px;
            padding: 0 0 9px;
            border-bottom: 1px solid var(--cs-border);
        }

        .welcome-line {
            color: #334155;
            font-size: 0.9rem;
            font-weight: 650;
        }

        .workflow-strip {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            border-top: 1px solid var(--cs-border);
            border-bottom: 1px solid var(--cs-border);
            background: rgba(255, 255, 255, 0.52);
            margin: 7px 0 14px;
        }

        .workflow-step {
            min-height: 52px;
            display: flex;
            align-items: center;
            padding: 10px 12px;
            color: #415166;
            font-size: 0.76rem;
            font-weight: 680;
            border-right: 1px solid var(--cs-border);
        }

        .workflow-step:last-child {
            border-right: 0;
        }

        .metric-panel,
        div[data-testid="stMetric"] {
            background: var(--cs-surface);
            border: 1px solid var(--cs-border);
            border-radius: var(--cs-radius);
            padding: 14px 15px;
            min-height: 100px;
            box-shadow: 0 2px 5px rgba(15, 23, 42, 0.03);
        }

        .metric-panel {
            margin: 3px 0 10px;
        }

        div[data-testid="stMetric"] {
            margin: 3px 0 10px;
        }

        .metric-label,
        div[data-testid="stMetric"] label {
            color: var(--cs-muted) !important;
            font-size: 0.74rem !important;
            font-weight: 660 !important;
        }

        .metric-value,
        div[data-testid="stMetricValue"] {
            color: var(--cs-text) !important;
            font-size: 1.65rem !important;
            font-weight: 790 !important;
            margin-top: 5px;
        }

        .hint {
            color: var(--cs-muted);
            font-size: 0.72rem;
            line-height: 1.35;
            margin-top: 3px;
        }

        div[data-testid="stForm"],
        div[data-testid="stExpander"] {
            background: var(--cs-surface);
            border: 1px solid var(--cs-border) !important;
            border-radius: var(--cs-radius) !important;
            box-shadow: none;
            margin: 5px 0 12px;
        }

        div[data-testid="stForm"] > div,
        div[data-testid="stExpander"] > details {
            padding: 12px !important;
        }

        textarea,
        input,
        div[data-baseweb="select"] > div,
        div[data-baseweb="textarea"] textarea {
            border-radius: 6px !important;
            border-color: var(--cs-border-strong) !important;
            background: var(--cs-surface) !important;
        }

        [data-testid="stTextInputRootElement"],
        div[data-baseweb="textarea"] {
            border: 1px solid var(--cs-border-strong) !important;
            border-radius: 6px !important;
            background: var(--cs-surface) !important;
        }

        [data-testid="stTextInputRootElement"]:focus-within,
        div[data-baseweb="textarea"]:focus-within {
            border-color: var(--cs-blue) !important;
            box-shadow: 0 0 0 1px var(--cs-blue) !important;
        }

        textarea:focus,
        input:focus {
            border-color: var(--cs-blue) !important;
        }

        .stButton > button,
        .stDownloadButton > button {
            min-height: 38px;
            border-radius: 6px !important;
            border: 1px solid var(--cs-border-strong) !important;
            background: var(--cs-surface) !important;
            color: var(--cs-text) !important;
            font-weight: 680 !important;
            box-shadow: none !important;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover {
            border-color: #8ea0b7 !important;
            color: var(--cs-blue-dark) !important;
        }

        .stButton > button[kind="primary"],
        .stDownloadButton > button[kind="primary"] {
            background: var(--cs-blue) !important;
            border-color: var(--cs-blue) !important;
            color: #ffffff !important;
        }

        .stButton > button[kind="primary"]:hover,
        .stDownloadButton > button[kind="primary"]:hover {
            background: var(--cs-blue-dark) !important;
            border-color: var(--cs-blue-dark) !important;
            color: #ffffff !important;
        }

        div[data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 18px;
            border-bottom: 1px solid var(--cs-border);
        }

        div[data-testid="stTabs"] button[data-baseweb="tab"] {
            min-height: 42px;
            padding: 0 2px;
            border-radius: 0;
            font-weight: 650;
        }

        .stDataFrame,
        div[data-testid="stDataFrame"] {
            border: 1px solid var(--cs-border);
            border-radius: var(--cs-radius) !important;
            overflow: hidden;
            box-shadow: none;
            margin: 5px 0 12px;
        }

        div[data-testid="stAlert"] {
            border-radius: 6px;
            border-color: var(--cs-border);
        }

        .winner-box {
            border-left: 4px solid var(--cs-green);
            background: var(--cs-green-soft);
            color: #14532d;
            padding: 11px 13px;
            border-radius: 6px;
            margin: 7px 0 11px;
        }

        .risk-low { color: var(--cs-green); font-weight: 740; }
        .risk-medium { color: var(--cs-amber); font-weight: 740; }
        .risk-high { color: var(--cs-red); font-weight: 740; }

        .auth-intro {
            max-width: 760px;
            margin: 12px auto 4px;
            text-align: center;
        }

        .auth-intro h1 {
            color: var(--cs-text);
            font-size: 1.65rem;
            margin: 0;
        }

        .auth-intro p {
            color: var(--cs-muted);
            font-size: 0.86rem;
            line-height: 1.5;
            margin: 7px 0 0;
        }

        .app-footer {
            color: #7a889b;
            font-size: 0.7rem;
            text-align: center;
            padding: 24px 0 4px;
            margin-top: 12px;
            border-top: 1px solid var(--cs-border);
        }

        hr {
            border-color: var(--cs-border);
        }

        @media (max-width: 900px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }

            .topbar,
            .page-heading {
                display: block;
            }

            .topbar-status {
                justify-content: flex-start;
                margin-top: 10px;
            }

            .workflow-strip {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }

            .workflow-step {
                border-bottom: 1px solid var(--cs-border);
            }
        }

        @media (max-width: 560px) {
            .page-heading h1 {
                font-size: 1.42rem;
            }

            .workflow-strip {
                grid-template-columns: 1fr;
            }

            .workflow-step {
                border-right: 0;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def ensure_state() -> None:
    defaults = {
        "live_result": None,
        "literary_result": None,
        "esl_single_result": None,
        "esl_batch_result": None,
        "teacher_decisions": {},
        "saved_teacher_decisions": {},
        "main_reviewer_id": "demo_teacher",
        "audit_selection": None,
        "api_mode": "Server-managed",
        "account_token": "",
        "account_user": None,
        "active_review_session_id": "",
        "active_page_key": "page_home",
        "account_flash": "",
        "workspace_error": "",
        "handled_account_action": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def topbar() -> None:
    user = current_account_user()
    health = backend_healthcheck(backend_api_url())
    workspace_label = mt("secure_workspace") if user else mt("account_required")
    service_label = mt("service_online") if health["ok"] else mt("service_offline")
    service_class = " is-online" if health["ok"] else ""
    st.markdown(
        f"""
        <div class="topbar">
          <div>
            <div class="title">ConsensusScope</div>
            <div class="subtitle">{html.escape(mt("topbar_subtitle"))}</div>
          </div>
          <div class="topbar-status">
            <span class="ui-pill">{html.escape(mt("badge_graph"))}</span>
            <span class="ui-pill">{html.escape(workspace_label)}</span>
            <span class="ui-pill{service_class}">{html.escape(service_label)}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def parse_options(options: Any) -> str:
    text = safe_str(options)
    if not text:
        return mt("none")
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return "\n".join(
                f"{safe_str(item.get('label', ''))}. {safe_str(item.get('text', item.get('content', '')))}"
                if isinstance(item, dict)
                else safe_str(item)
                for item in parsed
            )
        return json.dumps(parsed, ensure_ascii=False, indent=2)
    except Exception:
        return text


def dataframe_for_sample(df: pd.DataFrame, key_col: str, sample_id: str) -> pd.DataFrame:
    if df.empty or key_col not in df.columns:
        return pd.DataFrame()
    return df[df[key_col].astype(str) == str(sample_id)].copy()


def first_record(df: pd.DataFrame) -> Dict[str, Any]:
    return {} if df.empty else df.iloc[0].to_dict()


def decision_row(label: str, rec: Dict[str, Any], sample: Dict[str, Any]) -> Dict[str, Any]:
    final_answer = safe_str(rec.get("final_answer", ""))
    correct = (
        is_correct(final_answer, sample.get("gold_answer", ""), sample.get("gold_label", ""))
        if final_answer
        else "Not available"
    )
    score = rec.get("reliability_score", rec.get("confidence", rec.get("agreement_rate", "")))
    return {
        "method": label,
        "final_answer": final_answer or mt("not_available"),
        "correct_offline": correct,
        "risk_or_confidence": safe_str(rec.get("risk_level", "")) or safe_str(score) or mt("not_available"),
        "reasoning": english_note(rec.get("decision_note", rec.get("decision_reason", ""))) or mt("not_available"),
    }


def visible_method_metrics(metrics_df: pd.DataFrame) -> pd.DataFrame:
    if metrics_df.empty or "method" not in metrics_df.columns:
        return metrics_df
    method_text = metrics_df["method"].astype(str).str.lower()
    return metrics_df[~method_text.str.contains("learned")].copy()


def provider_env_value(provider: str, field: str) -> str:
    cfg = PROVIDER_CONFIG[provider]
    key = cfg[field]
    return configured_value(key)


def build_live_configs(api_mode: str, selected: List[str], user_inputs: Dict[str, Dict[str, str]]) -> List[LiveModelConfig]:
    del api_mode, user_inputs
    configs: List[LiveModelConfig] = []
    defaults = default_live_model_configs()
    for provider in selected:
        if provider not in defaults:
            continue
        api_key = provider_env_value(provider, "api_key")
        base_url = provider_env_value(provider, "base_url") or defaults[provider]["base_url"]
        model = provider_env_value(provider, "model") or defaults[provider]["model"]
        configs.append(LiveModelConfig(provider=provider, api_key=api_key, base_url=base_url, model=model, enabled=True))
    return configs


def build_fixed_judge_config(api_mode: str, provider: str, user_inputs: Dict[str, Dict[str, str]], enabled: bool) -> Optional[LiveModelConfig]:
    del api_mode, user_inputs
    if not enabled:
        return None
    defaults = default_live_model_configs()
    if provider not in defaults:
        return None
    api_key = provider_env_value(provider, "api_key")
    base_url = provider_env_value(provider, "base_url") or defaults[provider]["base_url"]
    model = provider_env_value(provider, "model") or defaults[provider]["model"]
    return LiveModelConfig(provider=provider, api_key=api_key, base_url=base_url, model=model, enabled=True)


def render_api_sidebar() -> tuple[str, List[str], Dict[str, Dict[str, str]], bool, str]:
    load_dotenv(ROOT / ".env")
    st.sidebar.markdown(f"#### {mt('api_configuration')}")
    api_mode = "Server-managed"
    st.session_state["api_mode"] = api_mode
    st.sidebar.caption(mt("api_caption"))
    available = [provider for provider in ANSWER_PROVIDERS if provider_env_value(provider, "api_key")]
    selected = st.sidebar.multiselect(mt("answer_models"), available, default=available)
    st.sidebar.caption(mt("answer_models_help"))
    fixed_enabled = st.sidebar.checkbox(mt("enable_fixed_judge"), value=False, disabled=not available)
    fixed_provider = (
        st.sidebar.selectbox(mt("fixed_judge_model"), selected or available, index=0)
        if available
        else ""
    )
    return api_mode, selected, {}, fixed_enabled, fixed_provider


def render_model_outputs(outputs: List[Dict[str, Any]]) -> None:
    if not outputs:
        st.info(mt("no_model_outputs"))
        return
    cols = [
        "provider",
        "model",
        "answer",
        "normalized_answer",
        "confidence",
        "evidence_quality",
        "evidence",
        "request_error",
        "parse_error",
        "latency_sec",
    ]
    df = pd.DataFrame(outputs)
    st.dataframe(display_frame(df[[c for c in cols if c in df.columns]], public=True), use_container_width=True, hide_index=True)
    error_rows = [
        item
        for item in outputs
        if safe_str(item.get("request_error")) or safe_str(item.get("parse_error"))
    ]
    if error_rows:
        with st.expander(mt("provider_request_errors"), expanded=True):
            for item in error_rows:
                provider = safe_str(item.get("provider")) or "unknown provider"
                model = safe_str(item.get("model")) or "unknown model"
                request_error = safe_str(item.get("request_error"))
                parse_error = safe_str(item.get("parse_error"))
                st.markdown(f"**{provider} · {model}**")
                if request_error:
                    st.code(request_error, language="text")
                if parse_error:
                    st.code(f"{mt('parse_error')}: {parse_error}", language="text")


def render_adjudication_comparison(comparison: Optional[Dict[str, Any]]) -> None:
    if not comparison:
        st.info(mt("no_adjudication_result"))
        return
    methods = [
        item
        for item in comparison.get("methods", [])
        if "learned" not in safe_str(item.get("label", item.get("method", ""))).lower()
    ]
    final = next((item for item in methods if item.get("label") == "Dynamic Rule-Based Judge"), comparison.get("final", {}))
    method_label = final.get("label", "Dynamic Rule-Based Judge")
    st.markdown(
        f"""
        <div class="winner-box">
        {mt("recommended_method")}: <b>{display_method_label(method_label)}</b> · answer=<b>{safe_str(final.get('final_answer', '')) or mt('empty_answer')}</b>
        · risk=<b>{value_label(final.get('risk_level', ''))}</b>
        · score=<b>{safe_str(final.get('reliability_score', ''))}</b><br/>
        {safe_str(final.get('explanation', ''))}
        </div>
        """,
        unsafe_allow_html=True,
    )
    comparison_rows = [
        row
        for row in comparison.get("comparison", [])
        if "learned" not in safe_str(row.get("method", "")).lower()
    ]
    st.dataframe(display_frame(pd.DataFrame(comparison_rows)), use_container_width=True, hide_index=True)
    with st.expander(mt("three_methods"), expanded=False):
        for method in methods:
            st.markdown(f"**{display_method_label(method.get('label', method.get('method', '')))}**")
            st.json(method)


def demo_esl_result() -> Dict[str, Any]:
    feedback = read_table(str(DATA_PATHS["esl_feedback"]))
    evidence = read_table(str(DATA_PATHS["esl_evidence"]))
    routing = read_table(str(DATA_PATHS["esl_routing"]))
    if feedback.empty or routing.empty:
        return {}
    merged = feedback.merge(routing, on="feedback_item_id", how="left")
    if not evidence.empty:
        merged = merged.merge(evidence, on="feedback_item_id", how="left")
    summary = summarize_routing(routing)
    comparison = compare_esl_feedback(feedback, routing)
    return {
        "essay_id": "demo_set",
        "feedback": feedback,
        "evidence": evidence,
        "routing": routing,
        "merged": merged,
        "comparison": comparison,
        "summary": summary,
        "report": "Packaged synthetic ESL writing demo. Run Single Essay Review or Batch Review to generate a live local report.",
    }


def current_esl_result() -> Dict[str, Any]:
    if st.session_state.get("esl_batch_result"):
        return st.session_state["esl_batch_result"]
    if st.session_state.get("esl_single_result"):
        return st.session_state["esl_single_result"]
    return {}


def display_esl_summary(summary: Dict[str, Any]) -> None:
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric(mt("feedback_items"), summary.get("feedback_items", 0))
    c2.metric(mt("auto_accepted"), summary.get("auto_accept", 0))
    c3.metric(mt("teacher_review"), summary.get("teacher_review", 0))
    c4.metric(mt("high_risk"), summary.get("high_risk", 0))
    c5.metric(mt("urgent"), summary.get("urgent_review", 0))
    c6.metric(mt("mean_risk"), summary.get("mean_risk_score", 0.0))


def teacher_queue_frame(result: Dict[str, Any]) -> pd.DataFrame:
    merged = result.get("merged", pd.DataFrame())
    if merged is None or merged.empty:
        return pd.DataFrame()
    queue = merged[merged["recommended_action"].isin(["teacher_review", "needs_more_evidence", "reject"])].copy()
    decisions = st.session_state.get("saved_teacher_decisions", {})
    if not queue.empty:
        default_session_id = safe_str(result.get("session_id"))
        queue["teacher_action"] = queue.apply(
            lambda row: decisions.get(
                decision_state_key(row.get("session_id", default_session_id), row.get("feedback_item_id")),
                "pending",
            ),
            axis=1,
        )
    return queue


def display_esl_feedback_table(df: pd.DataFrame, title: str = "Routed feedback") -> None:
    st.markdown(f"### {title}")
    if df.empty:
        st.info(mt("no_feedback"))
        return
    cols = [
        "essay_id",
        "feedback_item_id",
        "target_span",
        "model_source",
        "issue_type_predicted",
        "ai_suggestion",
        "risk_level",
        "recommended_action",
        "risk_score",
        "review_confidence",
        "evidence_signal",
        "review_priority",
        "risk_reasons",
        "safety_graph_active_dimensions",
        "safety_graph_path",
        "safety_graph_summary",
        "meaning_preservation_predicted",
        "review_explanation",
    ]
    st.dataframe(display_frame(df[[c for c in cols if c in df.columns]]), use_container_width=True, hide_index=True)


def load_assignment_workspace() -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    courses_payload, _ = backend_request("GET", "/api/courses")
    assignments_payload, _ = backend_request("GET", "/api/assignments")
    essays_payload, _ = backend_request("GET", "/api/essays", params={"limit": 2000})
    jobs_payload, _ = backend_request("GET", "/api/review/jobs", params={"limit": 100})
    return (
        courses_payload.get("courses", []) if courses_payload else [],
        assignments_payload.get("assignments", []) if assignments_payload else [],
        essays_payload.get("essays", []) if essays_payload else [],
        jobs_payload.get("jobs", []) if jobs_payload else [],
    )


def page_assignments() -> None:
    page_header("assignments_title", "assignments_caption")
    flash = safe_str(st.session_state.pop("assignment_flash", ""))
    if flash:
        st.success(flash)
    courses, assignments, essays, jobs = load_assignment_workspace()

    metric_course, metric_assignment, metric_essay, metric_job = st.columns(4)
    metric_course.metric(mt("courses"), len(courses))
    metric_assignment.metric(mt("assignments"), len(assignments))
    metric_essay.metric(mt("essays"), len(essays))
    metric_job.metric(mt("active_jobs"), sum(job.get("status") in {"queued", "running"} for job in jobs))

    create_course_tab, create_assignment_tab = st.tabs([mt("new_course"), mt("new_assignment")])
    with create_course_tab:
        with st.form("create_course_form", clear_on_submit=True):
            course_name = st.text_input(mt("course_name"))
            term = st.text_input(mt("term"))
            description = st.text_area(mt("description_optional"), height=90)
            submitted = st.form_submit_button(mt("create_course"), use_container_width=True, type="primary")
        if submitted:
            data, error = backend_request(
                "POST",
                "/api/courses",
                payload={"name": course_name, "term": term, "description": description},
            )
            if data:
                st.session_state["assignment_flash"] = mt("course_created")
                st.rerun()
            else:
                st.error(mt("backend_request_failed", error=error))

    with create_assignment_tab:
        if not courses:
            st.info(mt("no_courses"))
        else:
            course_labels = {
                safe_str(course["course_id"]): f"{safe_str(course['name'])} · {safe_str(course.get('term'))}"
                for course in courses
            }
            with st.form("create_assignment_form", clear_on_submit=True):
                course_id = st.selectbox(
                    mt("select_course"),
                    list(course_labels),
                    format_func=lambda value: course_labels[value],
                )
                title = st.text_input(mt("assignment_title"))
                prompt = st.text_area(mt("assignment_prompt"), height=130)
                student_level = st.selectbox(
                    mt("student_level"),
                    ["intermediate", "upper-intermediate", "advanced", "not specified"],
                    index=1,
                )
                due_date = st.text_input(mt("due_date_optional"), placeholder="2026-10-31")
                submitted = st.form_submit_button(mt("create_assignment"), use_container_width=True, type="primary")
            if submitted:
                data, error = backend_request(
                    "POST",
                    "/api/assignments",
                    payload={
                        "course_id": course_id,
                        "title": title,
                        "prompt": prompt,
                        "student_level": student_level,
                        "due_date": due_date or None,
                    },
                )
                if data:
                    st.session_state["assignment_flash"] = mt("assignment_created")
                    st.rerun()
                else:
                    st.error(mt("backend_request_failed", error=error))

    if not assignments:
        st.info(mt("no_assignments"))
    else:
        st.markdown(f'<div class="section-title">{mt("assignment_workspace")}</div>', unsafe_allow_html=True)
        assignment_labels = {
            safe_str(item["assignment_id"]): (
                f"{safe_str(item.get('course_name'))} · {safe_str(item.get('title'))} "
                f"({int(item.get('essay_count') or 0)})"
            )
            for item in assignments
        }
        selected_assignment_id = st.selectbox(
            mt("select_assignment"),
            list(assignment_labels),
            format_func=lambda value: assignment_labels[value],
            key="workspace_assignment_selector",
        )
        selected_assignment = next(
            (item for item in assignments if safe_str(item.get("assignment_id")) == selected_assignment_id),
            {},
        )
        st.info(safe_str(selected_assignment.get("prompt")))
        assignment_essays = [
            item for item in essays if safe_str(item.get("assignment_id")) == selected_assignment_id
        ]
        add_tab, upload_tab = st.tabs([mt("add_essay"), mt("upload_essay_batch")])
        with add_tab:
            with st.form("add_assignment_essay_form", clear_on_submit=True):
                external_id = st.text_input(mt("external_essay_id"), placeholder="ANON-001")
                draft_stage = st.selectbox(mt("draft_stage"), ["draft", "revised", "final"])
                essay_text = st.text_area(mt("student_draft"), height=260)
                submitted = st.form_submit_button(mt("save_essay"), use_container_width=True, type="primary")
            if submitted:
                privacy, privacy_error = privacy_preflight(essay_text)
                if not privacy:
                    st.error(mt("backend_request_failed", error=privacy_error))
                elif not privacy.get("safe_to_submit"):
                    st.error(mt("privacy_blocked"))
                    st.caption(mt("detected_types", types=", ".join(privacy.get("finding_types", []))))
                else:
                    data, error = backend_request(
                        "POST",
                        "/api/essays",
                        payload={
                            "assignment_id": selected_assignment_id,
                            "external_id": external_id,
                            "essay_text": essay_text,
                            "student_level": selected_assignment.get("student_level"),
                            "draft_stage": draft_stage,
                        },
                    )
                    if data:
                        st.session_state["assignment_flash"] = mt("essay_saved")
                        st.rerun()
                    else:
                        st.error(mt("backend_request_failed", error=error))

        with upload_tab:
            upload = st.file_uploader(mt("upload_essay_batch"), type=["csv"], key="assignment_csv_upload")
            if upload is not None:
                try:
                    upload_frame = pd.read_csv(upload).fillna("")
                except Exception as exc:
                    upload_frame = pd.DataFrame()
                    st.error(safe_str(exc))
                st.caption(mt("upload_help"))
                if not upload_frame.empty:
                    st.dataframe(display_frame(upload_frame.head(20)), use_container_width=True, hide_index=True)
                    text_column = "essay_text" if "essay_text" in upload_frame.columns else "essay_text_anonymized"
                    id_column = "external_id" if "external_id" in upload_frame.columns else "essay_id"
                    valid_columns = text_column in upload_frame.columns and id_column in upload_frame.columns
                    if not valid_columns:
                        st.error(mt("csv_required"))
                    if st.button(
                        mt("save_essay_batch"),
                        use_container_width=True,
                        type="primary",
                        disabled=not valid_columns or len(upload_frame) > MAX_BATCH_ESSAYS,
                    ):
                        privacy_failures = []
                        payload_rows = []
                        for _, row in upload_frame.iterrows():
                            row_text = safe_str(row.get(text_column))
                            row_id = safe_str(row.get(id_column))
                            privacy, _ = privacy_preflight(row_text)
                            if not privacy or not privacy.get("safe_to_submit"):
                                privacy_failures.append(row_id)
                                continue
                            payload_rows.append(
                                {
                                    "assignment_id": selected_assignment_id,
                                    "external_id": row_id,
                                    "essay_text": row_text,
                                    "student_level": safe_str(row.get("student_level"))
                                    or selected_assignment.get("student_level"),
                                    "draft_stage": safe_str(row.get("draft_stage")) or "draft",
                                }
                            )
                        if privacy_failures:
                            st.error(f"{mt('privacy_blocked')} {', '.join(privacy_failures[:10])}")
                        elif payload_rows:
                            data, error = backend_request(
                                "POST",
                                "/api/essays/batch",
                                payload={"essays": payload_rows},
                                timeout=120,
                            )
                            if data:
                                st.session_state["assignment_flash"] = mt(
                                    "essays_saved", count=int(data.get("count", 0))
                                )
                                st.rerun()
                            else:
                                st.error(mt("backend_request_failed", error=error))

        st.markdown(f"### {mt('stored_essays')}")
        if not assignment_essays:
            st.info(mt("no_stored_essays"))
        else:
            essay_frame = pd.DataFrame(assignment_essays)
            visible_columns = [
                "external_id",
                "student_level",
                "draft_stage",
                "word_count",
                "pii_status",
                "updated_at",
            ]
            st.dataframe(
                display_frame(essay_frame[[col for col in visible_columns if col in essay_frame.columns]]),
                use_container_width=True,
                hide_index=True,
            )
            essay_labels = {
                safe_str(item["essay_record_id"]): (
                    f"{safe_str(item.get('external_id'))} · {int(item.get('word_count') or 0)} {mt('words_short')}"
                )
                for item in assignment_essays
            }
            selected_essay_id = st.selectbox(
                mt("select_saved_or_demo"),
                list(essay_labels),
                format_func=lambda value: essay_labels[value],
                key="workspace_essay_selector",
            )
            single_col, batch_col = st.columns(2)
            if single_col.button(mt("open_single_review"), use_container_width=True, type="primary"):
                st.session_state["prefill_essay_record_id"] = selected_essay_id
                st.session_state["single_source_selection"] = f"saved:{selected_essay_id}"
                navigate_to("page_single")
                st.rerun()
            if batch_col.button(mt("start_assignment_batch"), use_container_width=True):
                st.session_state["prefill_assignment_id"] = selected_assignment_id
                st.session_state["batch_source_selection"] = "assignment"
                st.session_state["batch_assignment_selection"] = selected_assignment_id
                navigate_to("page_batch")
                st.rerun()

    if jobs:
        st.markdown(f'<div class="section-title">{mt("recent_jobs")}</div>', unsafe_allow_html=True)
        job_rows = [
            {
                "job_id": job.get("job_id"),
                "status": job.get("status"),
                "progress": job.get("progress"),
                "generation_mode": job.get("generation_mode"),
                "session_id": job.get("session_id"),
                "created_at": job.get("created_at"),
            }
            for job in jobs[:20]
        ]
        st.dataframe(display_frame(pd.DataFrame(job_rows)), use_container_width=True, hide_index=True)


def page_single_essay_review() -> None:
    st.button(mt("back_to_workspace"), on_click=navigate_to, args=("page_home",))
    page_header("single_title", "single_caption")
    demo_essays = read_table(str(DATA_PATHS["esl_essays"]))
    _, assignments, saved_essays, _ = load_assignment_workspace()
    assignment_map = {safe_str(item.get("assignment_id")): item for item in assignments}
    essay_map = {safe_str(item.get("essay_record_id")): item for item in saved_essays}

    source_options = ["blank"]
    source_labels = {"blank": mt("blank_workspace")}
    for _, row in demo_essays.iterrows():
        source_key = f"demo:{safe_str(row.get('essay_id'))}"
        source_options.append(source_key)
        source_labels[source_key] = f"{mt('blank_or_demo')} · {safe_str(row.get('essay_id'))}"
    for item in saved_essays:
        source_key = f"saved:{safe_str(item.get('essay_record_id'))}"
        source_options.append(source_key)
        assignment = assignment_map.get(safe_str(item.get("assignment_id")), {})
        source_labels[source_key] = (
            f"{mt('saved_assignment_essay')} · {safe_str(assignment.get('title'))} · "
            f"{safe_str(item.get('external_id'))}"
        )
    prefill_id = safe_str(st.session_state.pop("prefill_essay_record_id", ""))
    default_source = f"saved:{prefill_id}" if prefill_id in essay_map else "blank"
    if prefill_id in essay_map:
        st.session_state["single_source_selection"] = default_source
    if st.session_state.get("single_source_selection") not in source_options:
        st.session_state["single_source_selection"] = default_source
    source = st.selectbox(
        mt("select_saved_or_demo"),
        source_options,
        format_func=lambda value: source_labels[value],
        key="single_source_selection",
    )

    selected: Dict[str, Any] = {}
    selected_assignment: Dict[str, Any] = {}
    assignment_id: Optional[str] = None
    essay_record_id: Optional[str] = None
    if source.startswith("demo:"):
        demo_id = source.split(":", 1)[1]
        selected = first_record(demo_essays[demo_essays["essay_id"].astype(str) == demo_id])
    elif source.startswith("saved:"):
        essay_record_id = source.split(":", 1)[1]
        selected_payload, _ = backend_request("GET", f"/api/essays/{essay_record_id}")
        selected = selected_payload.get("essay", {}) if selected_payload else essay_map.get(essay_record_id, {})
        assignment_id = safe_str(selected.get("assignment_id")) or None
        selected_assignment = assignment_map.get(assignment_id or "", {})
        st.info(mt("saved_essay_notice"))

    default_prompt = (
        safe_str(selected_assignment.get("prompt"))
        or safe_str(selected.get("assignment_prompt"))
        or "Write an ESL essay responding clearly to the assignment prompt."
    )
    default_level = (
        safe_str(selected.get("student_level"))
        or safe_str(selected_assignment.get("student_level"))
        or "upper-intermediate"
    )
    default_essay = safe_str(selected.get("essay_text")) or safe_str(selected.get("essay_text_anonymized"))
    levels = ["intermediate", "upper-intermediate", "advanced", "not specified"]
    default_level_index = levels.index(default_level) if default_level in levels else 1
    widget_suffix = source.replace(":", "_").replace(" ", "_")

    providers = configured_feedback_providers()
    provider_names = [safe_str(item.get("provider")) for item in providers]

    left, right = st.columns([1.35, 0.65], gap="large")
    with left:
        essay_id = st.text_input(
            mt("essay_id"),
            value=safe_str(selected.get("external_id")) or safe_str(selected.get("essay_id")) or "USER-ESSAY-001",
            key=f"single_essay_id_{widget_suffix}",
        )
        assignment = st.text_area(
            mt("assignment_prompt"),
            value=default_prompt,
            height=92,
            key=f"single_assignment_{widget_suffix}",
        )
        level = st.selectbox(
            mt("student_level"),
            levels,
            index=default_level_index,
            key=f"single_level_{widget_suffix}",
        )
        essay_text = st.text_area(
            mt("student_draft"),
            value=default_essay,
            height=330,
            key=f"single_draft_{widget_suffix}",
        )
    with right:
        st.markdown(f'<div class="section-title">{mt("draft_check")}</div>', unsafe_allow_html=True)
        word_count = len(essay_text.split())
        st.metric(mt("word_count"), word_count)
        if word_count >= 30:
            st.success(mt("draft_ready"))
        else:
            st.warning(mt("draft_short"))
        st.info(mt("privacy_check"))
        generation_mode_label = st.radio(
            mt("generation_source"),
            ["local", "live"],
            format_func=lambda value: mt("local_generation") if value == "local" else mt("live_generation"),
            key=f"single_generation_mode_{widget_suffix}",
        )
        st.caption(
            mt("local_generation_help")
            if generation_mode_label == "local"
            else mt("live_generation_help")
        )
        selected_providers: List[str] = []
        if generation_mode_label == "live":
            if provider_names:
                provider_display = {
                    safe_str(item.get("provider")): f"{safe_str(item.get('provider')).title()} · {safe_str(item.get('model'))}"
                    for item in providers
                }
                selected_providers = st.multiselect(
                    mt("model_providers"),
                    provider_names,
                    default=provider_names[: min(3, len(provider_names))],
                    format_func=lambda value: provider_display.get(value, value),
                    key=f"single_providers_{widget_suffix}",
                )
            else:
                st.warning(mt("no_live_providers"))
        with st.expander(mt("advanced_options"), expanded=False):
            include_stress = st.checkbox(
                mt("include_stress"),
                value=False,
                disabled=generation_mode_label == "live",
            )

    can_run = bool(essay_text.strip()) and (
        generation_mode_label == "local" or bool(selected_providers)
    )
    run = st.button(
        mt("submit_review_job"),
        use_container_width=True,
        type="primary",
        disabled=not can_run,
    )

    if run:
        privacy, privacy_error = privacy_preflight(essay_text)
        if not privacy:
            st.error(mt("backend_request_failed", error=privacy_error))
        elif not privacy.get("safe_to_submit"):
            st.error(mt("privacy_blocked"))
            st.caption(mt("detected_types", types=", ".join(privacy.get("finding_types", []))))
        else:
            st.success(mt("privacy_clear"))
            data, error = backend_request(
                "POST",
                "/api/review/jobs",
                payload={
                    "essay_text": essay_text,
                    "essay_id": essay_id,
                    "assignment_prompt": assignment,
                    "student_level": level,
                    "include_stress_tests": include_stress if generation_mode_label == "local" else False,
                    "assignment_id": assignment_id,
                    "essay_record_id": essay_record_id,
                    "generation_mode": generation_mode_label,
                    "providers": selected_providers,
                },
                timeout=30,
            )
            if data:
                job_id = safe_str((data.get("job") or {}).get("job_id"))
                job, job_error = wait_for_review_job(job_id)
                if job and safe_str(job.get("status")) == "completed":
                    result, load_error = load_personal_review(safe_str(job.get("session_id")))
                    if result:
                        st.session_state["esl_single_result"] = result
                        st.session_state["esl_batch_result"] = None
                        st.session_state["active_review_session_id"] = result.get("session_id", "")
                        st.session_state["teacher_decisions"] = {}
                        st.session_state["saved_teacher_decisions"] = {}
                        st.success(mt("job_completed"))
                    else:
                        st.error(mt("backend_request_failed", error=load_error))
                elif job_error == mt("job_timed_out"):
                    st.warning(job_error)
                else:
                    st.error(mt("job_failed", error=job_error))
            else:
                st.error(mt("backend_request_failed", error=error))

    result = st.session_state.get("esl_single_result")
    if not result:
        return
    st.markdown(f'<div class="section-title">{mt("review_result")}</div>', unsafe_allow_html=True)
    display_esl_summary(result["summary"])
    queue = teacher_queue_frame(result)
    all_feedback_tab, comparison_tab, queue_tab = st.tabs(
        [mt("all_routed_feedback"), mt("compare_title"), mt("teacher_queue_table")]
    )
    with all_feedback_tab:
        display_esl_feedback_table(result["merged"], mt("routed_feedback"))
    with comparison_tab:
        comparison = result.get("comparison", pd.DataFrame())
        if isinstance(comparison, pd.DataFrame) and not comparison.empty:
            st.dataframe(display_frame(comparison), use_container_width=True, hide_index=True)
        else:
            st.info(mt("no_comparison"))
    with queue_tab:
        display_esl_feedback_table(queue, mt("teacher_queue_table"))
    metadata = result.get("model_metadata") or {}
    if metadata:
        with st.expander(mt("model_trace"), expanded=False):
            st.json(metadata)
    st.download_button(
        mt("download_single_report"),
        data=result["report"].encode("utf-8"),
        file_name=f"{result.get('essay_id', 'essay')}_review_report.md",
        mime="text/markdown",
        use_container_width=True,
    )


def page_batch_review() -> None:
    st.button(mt("back_to_workspace"), on_click=navigate_to, args=("page_home",))
    page_header("batch_title", "batch_caption")
    _, assignments, stored_essays, _ = load_assignment_workspace()
    assignment_map = {safe_str(item.get("assignment_id")): item for item in assignments}
    prefill_assignment_id = safe_str(st.session_state.pop("prefill_assignment_id", ""))
    source_options = ["assignment", "upload", "demo"] if assignments else ["upload", "demo"]
    default_source = "assignment" if prefill_assignment_id in assignment_map else source_options[0]
    source_labels = {
        "assignment": mt("saved_assignment_essay"),
        "upload": mt("uploaded_file"),
        "demo": mt("packaged_examples"),
    }
    if prefill_assignment_id in assignment_map:
        st.session_state["batch_source_selection"] = "assignment"
        st.session_state["batch_assignment_selection"] = prefill_assignment_id
    if st.session_state.get("batch_source_selection") not in source_options:
        st.session_state["batch_source_selection"] = default_source
    source = st.segmented_control(
        mt("batch_source"),
        source_options,
        format_func=lambda value: source_labels[value],
        key="batch_source_selection",
    ) or default_source

    template = pd.DataFrame(
        [
            {
                "essay_id": "ESSAY-001",
                "assignment_prompt": "Write an opinion essay responding to the prompt.",
                "student_level": "upper-intermediate",
                "essay_text_anonymized": "Paste anonymized student writing here.",
            }
        ]
    )
    uploaded = None
    assignment_id: Optional[str] = None
    selected_assignment: Dict[str, Any] = {}
    if source == "assignment":
        assignment_labels = {
            safe_str(item.get("assignment_id")): (
                f"{safe_str(item.get('course_name'))} · {safe_str(item.get('title'))} "
                f"({int(item.get('essay_count') or 0)})"
            )
            for item in assignments
        }
        default_assignment_index = (
            list(assignment_labels).index(prefill_assignment_id)
            if prefill_assignment_id in assignment_labels
            else 0
        )
        if st.session_state.get("batch_assignment_selection") not in assignment_labels:
            st.session_state["batch_assignment_selection"] = list(assignment_labels)[default_assignment_index]
        assignment_id = st.selectbox(
            mt("select_assignment"),
            list(assignment_labels),
            format_func=lambda value: assignment_labels[value],
            key="batch_assignment_selection",
        )
        selected_assignment = assignment_map.get(assignment_id, {})
        assignment_essays_payload, assignment_essays_error = backend_request(
            "GET",
            "/api/essays",
            params={"assignment_id": assignment_id, "include_text": True, "limit": MAX_BATCH_ESSAYS},
        )
        assignment_rows = assignment_essays_payload.get("essays", []) if assignment_essays_payload else []
        if assignment_essays_error:
            st.warning(mt("backend_request_failed", error=assignment_essays_error))
        essays = pd.DataFrame(
            [
                {
                    "essay_id": item.get("external_id"),
                    "essay_record_id": item.get("essay_record_id"),
                    "assignment_id": assignment_id,
                    "assignment_prompt": selected_assignment.get("prompt"),
                    "student_level": item.get("student_level") or selected_assignment.get("student_level"),
                    "essay_text": item.get("essay_text"),
                }
                for item in assignment_rows
            ]
        )
        source_label = mt("saved_assignment_essay")
    elif source == "upload":
        upload_column, template_column = st.columns([1.45, 0.55], gap="large")
        with upload_column:
            uploaded = st.file_uploader(
                mt("upload_csv"),
                type=["csv"],
                help=mt("upload_help"),
            )
        with template_column:
            st.download_button(
                mt("download_csv_template"),
                data=template.to_csv(index=False, encoding="utf-8-sig"),
                file_name="consensusscope_batch_template.csv",
                mime="text/csv",
                use_container_width=True,
            )
        if uploaded is None:
            st.info(mt("upload_help"))
            essays = pd.DataFrame()
        else:
            try:
                essays = pd.read_csv(uploaded).fillna("")
            except Exception as exc:
                st.error(mt("read_error", path=uploaded.name, error=exc))
                return
        source_label = mt("uploaded_file")
    else:
        essays = read_table(str(DATA_PATHS["esl_essays"]))
        source_label = mt("packaged_examples")

    providers = configured_feedback_providers()
    provider_names = [safe_str(item.get("provider")) for item in providers]
    options_col, model_col = st.columns([0.85, 1.15], gap="large")
    with options_col:
        generation_mode = st.radio(
            mt("generation_source"),
            ["local", "live"],
            format_func=lambda value: mt("local_generation") if value == "local" else mt("live_generation"),
            key="batch_generation_mode",
        )
        include_stress = st.checkbox(
            mt("include_stress_batch"),
            value=False,
            disabled=generation_mode == "live",
        )
    with model_col:
        selected_providers: List[str] = []
        if generation_mode == "live":
            if provider_names:
                provider_display = {
                    safe_str(item.get("provider")): f"{safe_str(item.get('provider')).title()} · {safe_str(item.get('model'))}"
                    for item in providers
                }
                selected_providers = st.multiselect(
                    mt("model_providers"),
                    provider_names,
                    default=provider_names[: min(3, len(provider_names))],
                    format_func=lambda value: provider_display.get(value, value),
                    key="batch_model_providers",
                )
                st.caption(mt("live_generation_help"))
            else:
                st.warning(mt("no_live_providers"))
        else:
            st.info(mt("local_generation_help"))

    if essays.empty:
        if source != "upload" or uploaded is not None:
            st.warning(mt("no_essays"))
        return

    essay_text_column = "essay_text" if "essay_text" in essays.columns else "essay_text_anonymized"
    has_text_column = essay_text_column in essays.columns
    valid_count = int(essays[essay_text_column].astype(str).str.strip().ne("").sum()) if has_text_column else 0
    total_count = len(essays)
    source_metric, rows_metric, valid_metric = st.columns(3)
    source_metric.metric(mt("batch_source"), source_label)
    rows_metric.metric(mt("batch_rows"), total_count)
    valid_metric.metric(mt("valid_essays"), valid_count)

    if not has_text_column:
        st.error(mt("csv_required"))
    elif valid_count != total_count:
        st.error(mt("empty_essay_rows", count=total_count - valid_count))
    if total_count > MAX_BATCH_ESSAYS:
        st.error(mt("batch_limit", count=MAX_BATCH_ESSAYS))

    preview_columns = [
        col for col in ["essay_id", "student_level", "assignment_prompt", essay_text_column] if col in essays.columns
    ]
    st.dataframe(display_frame(essays[preview_columns].head(10)), use_container_width=True, hide_index=True)
    can_run = (
        has_text_column
        and valid_count == total_count
        and total_count <= MAX_BATCH_ESSAYS
        and (generation_mode == "local" or bool(selected_providers))
    )
    if st.button(mt("run_batch"), use_container_width=True, type="primary", disabled=not can_run):
        combined_text = "\n\n".join(essays[essay_text_column].astype(str).tolist())
        privacy, privacy_error = privacy_preflight(combined_text)
        if not privacy:
            st.error(mt("backend_request_failed", error=privacy_error))
        elif not privacy.get("safe_to_submit"):
            st.error(mt("privacy_blocked"))
            st.caption(mt("detected_types", types=", ".join(privacy.get("finding_types", []))))
        else:
            payload_essays = []
            for index, row in essays.fillna("").iterrows():
                payload_essays.append(
                    {
                        "essay_id": safe_str(row.get("essay_id")) or f"BATCH-ESSAY-{index + 1:03d}",
                        "essay_text": safe_str(row.get(essay_text_column)),
                        "assignment_prompt": safe_str(row.get("assignment_prompt"))
                        or safe_str(selected_assignment.get("prompt"))
                        or "Write an ESL essay responding clearly to the assignment prompt.",
                        "student_level": safe_str(row.get("student_level"))
                        or safe_str(selected_assignment.get("student_level"))
                        or "not specified",
                        "include_stress_tests": include_stress if generation_mode == "local" else False,
                        "assignment_id": safe_str(row.get("assignment_id")) or assignment_id,
                        "essay_record_id": safe_str(row.get("essay_record_id")) or None,
                    }
                )
            data, error = backend_request(
                "POST",
                "/api/review/jobs/batch",
                payload={
                    "essays": payload_essays,
                    "generation_mode": generation_mode,
                    "providers": selected_providers,
                },
                timeout=30,
            )
            if data:
                job_ids = [safe_str(job.get("job_id")) for job in data.get("jobs", [])]
                jobs, jobs_error = wait_for_review_jobs(job_ids)
                completed_jobs = [job for job in jobs if job.get("status") == "completed"]
                result, result_error = batch_result_from_completed_jobs(completed_jobs)
                if result:
                    st.session_state["esl_batch_result"] = result
                    st.session_state["esl_single_result"] = None
                    st.session_state["active_review_session_id"] = ""
                    st.session_state["teacher_decisions"] = {}
                    st.session_state["saved_teacher_decisions"] = {}
                    st.success(mt("job_completed"))
                if jobs_error:
                    st.warning(jobs_error)
                if result_error and not result:
                    st.error(mt("backend_request_failed", error=result_error))
            else:
                st.error(mt("backend_request_failed", error=error))
    result = st.session_state.get("esl_batch_result")
    if not result:
        return
    st.markdown(f'<div class="section-title">{mt("batch_result")}</div>', unsafe_allow_html=True)
    st.dataframe(display_frame(result["summary"]), use_container_width=True, hide_index=True)
    display_esl_feedback_table(result["merged"], mt("all_routed_feedback"))
    feedback_download, summary_download = st.columns(2)
    feedback_download.download_button(
        mt("download_batch_feedback"),
        data=result["merged"].to_csv(index=False, encoding="utf-8-sig"),
        file_name="batch_esl_routed_feedback.csv",
        mime="text/csv",
        use_container_width=True,
    )
    summary_download.download_button(
        mt("download_batch_summary"),
        data=result["summary"].to_csv(index=False, encoding="utf-8-sig"),
        file_name="batch_esl_summary.csv",
        mime="text/csv",
        use_container_width=True,
    )


def page_ai_feedback_comparison() -> None:
    page_header("compare_title", "compare_caption")
    result = current_esl_result()
    if not result:
        st.info(mt("run_first"))
        st.button(
            mt("new_single_review"),
            type="primary",
            on_click=navigate_to,
            args=("page_single",),
        )
        return
    comparison = result.get("comparison", pd.DataFrame())
    if comparison.empty:
        st.info(mt("no_comparison"))
        return
    counts = comparison["consensus_state"].value_counts().rename_axis("consensus_state").reset_index(name="items")
    item_metric, state_metric = st.columns(2)
    item_metric.metric(mt("feedback_items"), len(comparison))
    state_metric.metric(mt("consensus_states"), comparison["consensus_state"].nunique())
    st.dataframe(display_frame(comparison), use_container_width=True, hide_index=True)
    st.markdown(f"### {mt('consensus_states')}")
    st.dataframe(display_frame(counts), use_container_width=True, hide_index=True)


def page_teacher_queue() -> None:
    page_header("queue_title", "queue_caption")
    queue_flash = safe_str(st.session_state.pop("queue_flash", ""))
    if queue_flash:
        st.success(queue_flash)
    result = current_esl_result()
    if not result:
        st.info(mt("run_first"))
        st.button(
            mt("new_single_review"),
            type="primary",
            on_click=navigate_to,
            args=("page_single",),
        )
        return
    queue = teacher_queue_frame(result)
    if queue.empty:
        st.success(mt("queue_empty"))
        return

    pending_count = int(queue["teacher_action"].eq("pending").sum())
    completed_count = len(queue) - pending_count
    high_count = int(queue["risk_level"].eq("high").sum())
    pending_metric, completed_metric, high_metric = st.columns(3)
    pending_metric.metric(mt("pending_items"), pending_count)
    completed_metric.metric(mt("completed_items"), completed_count)
    high_metric.metric(mt("high_risk"), high_count)

    show_pending_only = st.checkbox(mt("show_pending_only"), value=True)
    risk_filter = st.multiselect(
        mt("risk_level"),
        ["high", "medium", "low"],
        default=["high", "medium", "low"],
        format_func=value_label,
    )
    issue_options = sorted(queue["issue_type_predicted"].fillna("").astype(str).unique().tolist())
    issue_filter = st.multiselect(mt("issue_type"), issue_options, default=issue_options, format_func=value_label)
    filtered = queue[queue["risk_level"].isin(risk_filter) & queue["issue_type_predicted"].isin(issue_filter)].copy()
    if show_pending_only:
        filtered = filtered[filtered["teacher_action"].eq("pending")].copy()
    if filtered.empty:
        st.success(mt("all_queue_items_complete") if pending_count == 0 else mt("no_feedback"))
        return

    for item_index, (_, row) in enumerate(filtered.iterrows()):
        item_id = safe_str(row.get("feedback_item_id"))
        session_id = safe_str(row.get("session_id")) or safe_str(result.get("session_id"))
        state_key = decision_state_key(session_id, item_id)
        priority = safe_str(row.get("review_priority")) or "normal"
        score = safe_str(row.get("risk_score")) or "n/a"
        with st.expander(
            f"{item_id} · {value_label(row.get('risk_level'))} · {mt('priority')}={value_label(priority)} · score={score}",
            expanded=item_index == 0,
        ):
            original_column, suggestion_column = st.columns(2, gap="large")
            with original_column:
                st.caption(mt("target_span"))
                st.text_area(
                    mt("target_span"),
                    value=safe_str(row.get("target_span")),
                    height=110,
                    disabled=True,
                    label_visibility="collapsed",
                    key=f"queue_original_{session_id}_{item_id}",
                )
            with suggestion_column:
                st.caption(mt("ai_suggestion"))
                st.text_area(
                    mt("ai_suggestion"),
                    value=safe_str(row.get("ai_suggestion")),
                    height=110,
                    disabled=True,
                    label_visibility="collapsed",
                    key=f"queue_suggestion_{session_id}_{item_id}",
                )
            st.write(f"**{mt('routing_reason')}:** {value_label(row.get('risk_reasons'))}")
            if safe_str(row.get("safety_graph_summary")) or safe_str(row.get("safety_graph_path")):
                st.markdown(f"**{mt('feedback_safety_graph')}**")
                active_dimensions = value_list_label(row.get("safety_graph_active_dimensions"))
                st.write(
                    mt(
                        "graph_route_summary",
                        dimensions=active_dimensions,
                        route=value_label(row.get("recommended_action")),
                    )
                )
                if safe_str(row.get("safety_graph_path")):
                    st.code(graph_path_label(row.get("safety_graph_path")), language="text")
                if safe_str(row.get("safety_graph_active_dimensions")):
                    st.write(f"**{mt('active_safety_dimensions')}:** {active_dimensions}")
            if safe_str(row.get("review_explanation")):
                st.write(f"**{mt('ai_review_explanation')}:** {row.get('review_explanation')}")
            cols = st.columns(3)
            cols[0].caption(mt("review_confidence"))
            cols[0].write(f"**{safe_str(row.get('review_confidence')) or 'n/a'}**")
            cols[1].caption(mt("evidence_signal"))
            cols[1].write(f"**{safe_str(row.get('evidence_signal')) or 'none'}**")
            cols[2].caption(mt("priority"))
            cols[2].write(f"**{value_label(priority)}**")
            action_options = ["pending", "accept", "edit", "reject", "needs_more_evidence"]
            saved_action = st.session_state.get("teacher_decisions", {}).get(
                state_key,
                st.session_state.get("saved_teacher_decisions", {}).get(state_key, "pending"),
            )
            if saved_action not in action_options:
                saved_action = "pending"
            action = st.radio(
                mt("teacher_action"),
                action_options,
                format_func=value_label,
                horizontal=True,
                key=f"teacher_action_{session_id}_{item_id}",
                index=action_options.index(saved_action),
            )
            st.session_state["teacher_decisions"][state_key] = action
            corrected_feedback = ""
            if action == "edit":
                corrected_feedback = st.text_area(
                    mt("corrected_feedback"),
                    value=safe_str(row.get("ai_suggestion")),
                    key=f"corrected_feedback_{session_id}_{item_id}",
                    height=96,
                )
            teacher_reason = st.text_area(
                mt("teacher_reason_optional"),
                key=f"teacher_reason_{session_id}_{item_id}",
                height=72,
            )
            if st.button(
                mt("save_decision"),
                key=f"save_decision_{session_id}_{item_id}",
                use_container_width=True,
                type="primary",
            ):
                if not session_id:
                    st.warning(mt("session_not_persistent"))
                elif action == "edit" and not corrected_feedback.strip():
                    st.error(mt("edit_feedback_required"))
                elif action == "pending":
                    st.warning(mt("select_decision"))
                else:
                    saved, error = backend_request(
                        "POST",
                        "/api/teacher/decision",
                        payload={
                            "session_id": session_id,
                            "feedback_item_id": item_id,
                            "teacher_action": action,
                            "teacher_corrected_feedback": corrected_feedback or None,
                            "teacher_reason": teacher_reason or None,
                            "metadata": {
                                "risk_level": safe_str(row.get("risk_level")),
                                "risk_score": safe_str(row.get("risk_score")),
                            },
                        },
                    )
                    if saved:
                        st.session_state["saved_teacher_decisions"][state_key] = action
                        st.session_state["queue_flash"] = mt("decision_saved")
                        st.rerun()
                    else:
                        st.error(mt("backend_request_failed", error=error))
    st.download_button(
        mt("download_queue"),
        data=filtered.to_csv(index=False, encoding="utf-8-sig"),
        file_name="teacher_queue.csv",
        mime="text/csv",
        use_container_width=True,
    )


def page_effectiveness_evaluation() -> None:
    st.markdown(f'<div class="section-title">{mt("eval_title")}</div>', unsafe_allow_html=True)
    st.caption(mt("eval_caption"))
    feedback = read_table(str(DATA_PATHS["esl_feedback"]))
    evidence = read_table(str(DATA_PATHS["esl_evidence"]))
    expected = read_table(str(DATA_PATHS["esl_expected"]))
    result = review_esl_batch(read_table(str(DATA_PATHS["esl_essays"])), include_stress_tests=False)
    demo_routing = result["routing"] if result else pd.DataFrame()
    if not feedback.empty and not evidence.empty:
        demo_routing = route_feedback_dataframe(feedback, evidence)
    stress = read_table(str(DATA_PATHS["esl_stress"]))
    stress_routing = pd.DataFrame()
    stress_expected = pd.DataFrame()
    if not stress.empty:
        stress_expected = stress[["feedback_item_id", "expected_risk_level", "expected_action", "expected_reason"]].copy()
        stress_feedback = stress.drop(columns=["expected_risk_level", "expected_action", "expected_reason"])
        stress_routing = route_feedback_dataframe(stress_feedback, build_review_evidence(stress_feedback))
    combined_routing = pd.concat([demo_routing, stress_routing], ignore_index=True)
    combined_expected = pd.concat([expected, stress_expected], ignore_index=True)
    metrics = evaluate_routing_against_expected(demo_routing, expected)
    stress_metrics = evaluate_routing_against_expected(stress_routing, stress_expected)
    combined_metrics = evaluate_routing_against_expected(combined_routing, combined_expected)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(mt("combined_items"), combined_metrics["items"])
    c2.metric(mt("action_accuracy"), combined_metrics["action_accuracy"])
    c3.metric(mt("risk_accuracy"), combined_metrics["risk_accuracy"])
    c4.metric(mt("high_risk_recall"), combined_metrics["high_risk_recall"])
    c5.metric(mt("auto_precision"), combined_metrics["auto_accept_precision"])
    st.info(combined_metrics["note"])
    st.markdown(f"### {mt('evaluation_sets')}")
    st.dataframe(
        display_frame(pd.DataFrame(
            [
                {"set": mt("packaged_demo"), **metrics},
                {"set": mt("stress_cases"), **stress_metrics},
                {"set": "combined", **combined_metrics},
            ]
        )),
        use_container_width=True,
        hide_index=True,
    )
    merged = demo_routing.merge(expected, on="feedback_item_id", how="left") if not demo_routing.empty and not expected.empty else pd.DataFrame()
    if not merged.empty:
        merged["action_match"] = merged["recommended_action"] == merged["expected_action"]
        merged["risk_match"] = merged["risk_level"] == merged["expected_risk_level"]
        st.markdown(f"### {mt('packaged_demo')}")
        st.dataframe(display_frame(merged), use_container_width=True, hide_index=True)
    stress_merged = (
        stress_routing.merge(stress_expected, on="feedback_item_id", how="left")
        if not stress_routing.empty and not stress_expected.empty
        else pd.DataFrame()
    )
    if not stress_merged.empty:
        stress_merged["action_match"] = stress_merged["recommended_action"] == stress_merged["expected_action"]
        stress_merged["risk_match"] = stress_merged["risk_level"] == stress_merged["expected_risk_level"]
        st.markdown(f"### {mt('stress_cases')}")
        st.dataframe(display_frame(stress_merged), use_container_width=True, hide_index=True)
    public_summary = read_table(str(DATA_PATHS["public_gec_summary"]))
    public_policy = read_table(str(DATA_PATHS["public_gec_policy_summary"]))
    if not public_summary.empty:
        st.markdown(f"### {mt('public_gec_results')}")
        st.caption(mt("public_gec_caption"))
        public_cols = [
            "dataset_run",
            "parallel_records",
            "gold_edits",
            "feedback_candidates",
            "auto_share",
            "auto_acc",
            "review_share",
            "errors_reviewed",
        ]
        st.dataframe(
            display_frame(public_summary[[c for c in public_cols if c in public_summary.columns]]),
            use_container_width=True,
            hide_index=True,
        )
        st.info(mt("public_gec_note"))
    if not public_policy.empty:
        st.markdown(f"### {mt('public_gec_policy')}")
        policy_cols = ["dataset_run", "policy", "items", "auto_share", "auto_acc", "review_share", "errors_reviewed"]
        st.dataframe(
            display_frame(public_policy[[c for c in policy_cols if c in public_policy.columns]]),
            use_container_width=True,
            hide_index=True,
        )
    st.markdown(f"### {mt('validity_assessment')}")
    st.write(mt("validity_text"))


def page_reports() -> None:
    page_header("reports_title", "reports_caption")
    sessions_payload, sessions_error = backend_request("GET", "/api/sessions", params={"limit": 200})
    sessions = sessions_payload.get("sessions", []) if sessions_payload else []
    if not sessions:
        st.info(mt("run_first"))
        if sessions_error:
            st.caption(sessions_error)
        st.button(
            mt("new_single_review"),
            type="primary",
            on_click=navigate_to,
            args=("page_single",),
        )
        return

    session_labels = {
        safe_str(item.get("session_id")): (
            f"{safe_str(item.get('essay_id'))} · {safe_str(item.get('created_at'))[:16]} · "
            f"{value_label(item.get('generation_mode'))}"
        )
        for item in sessions
    }
    active_session_id = safe_str(st.session_state.get("active_review_session_id"))
    default_index = list(session_labels).index(active_session_id) if active_session_id in session_labels else 0
    session_id = st.selectbox(
        mt("select_review_session"),
        list(session_labels),
        index=default_index,
        format_func=lambda value: session_labels[value],
        key="report_session_selector",
    )
    result, load_error = load_personal_review(session_id)
    if not result:
        st.error(mt("backend_request_failed", error=load_error))
        return
    merged = result.get("merged", pd.DataFrame())
    summary = result.get("summary", {})
    if isinstance(summary, pd.DataFrame):
        st.dataframe(display_frame(summary), use_container_width=True, hide_index=True)
    else:
        display_esl_summary(summary)
    report_text = result.get("report", "")
    if not report_text and not merged.empty:
        report_text = (
            "ConsensusScope 批量报告\n\n请下载路由反馈 CSV 查看逐条反馈细节。"
            if ui_lang() == "zh"
            else "ConsensusScope batch report\n\nDownload the routed feedback CSV for item-level details."
        )
    audit_tab, student_tab, data_tab = st.tabs(
        [mt("audit_report"), mt("student_report"), mt("report_table")]
    )
    with audit_tab:
        st.text_area(mt("report_preview"), value=report_text, height=320, disabled=True)
        st.download_button(
            mt("download_report_md"),
            data=report_text.encode("utf-8"),
            file_name=f"{safe_str(result.get('essay_id'))}_teacher_audit.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with student_tab:
        st.info(mt("student_report_caption"))
        report_state_key = f"student_report_{session_id}"
        if st.button(mt("prepare_student_report"), use_container_width=True, type="primary"):
            student_payload, student_error = backend_request(
                "GET",
                f"/api/export/student-report/{session_id}",
            )
            if student_payload:
                st.session_state[report_state_key] = safe_str(student_payload.get("text"))
            else:
                st.error(mt("backend_request_failed", error=student_error))
        student_report = safe_str(st.session_state.get(report_state_key))
        if student_report:
            st.text_area(mt("student_report"), value=student_report, height=320, disabled=True)
            st.download_button(
                mt("download_student_report"),
                data=student_report.encode("utf-8"),
                file_name=f"{safe_str(result.get('essay_id'))}_student_feedback.md",
                mime="text/markdown",
                use_container_width=True,
            )
    with data_tab:
        display_esl_feedback_table(merged, mt("report_table"))
    st.download_button(
        mt("download_routed_csv"),
        data=merged.to_csv(index=False, encoding="utf-8-sig") if not merged.empty else "",
        file_name=f"{safe_str(result.get('essay_id'))}_routed_feedback.csv",
        mime="text/csv",
        use_container_width=True,
    )


def page_account() -> None:
    page_header("account_title", "account_caption")
    flash = safe_str(st.session_state.pop("account_flash", ""))
    if flash:
        st.success(flash)
    user = current_account_user()
    summary_payload, summary_error = backend_request("GET", "/api/account/summary")
    if summary_payload:
        summary = summary_payload.get("summary", {})
        st.markdown(f"### {mt('personal_overview')}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(mt("review_sessions"), int(summary.get("review_sessions", 0)))
        c2.metric(mt("feedback_items"), int(summary.get("feedback_items", 0)))
        c3.metric(mt("review_routed"), int(summary.get("review_routed", 0)))
        c4.metric(mt("saved_decisions"), int(summary.get("teacher_decisions", 0)))
    elif summary_error:
        st.warning(mt("backend_request_failed", error=summary_error))

    profile_tab, history_tab, password_tab, data_tab = st.tabs(
        [mt("profile"), mt("recent_reviews"), mt("change_password"), mt("security_and_data")]
    )
    with profile_tab:
        with st.form("account_profile_form"):
            display_name = st.text_input(
                mt("display_name"),
                value=safe_str(user.get("display_name")),
            )
            email = st.text_input(
                mt("email_optional"),
                value=safe_str(user.get("email")),
            )
            submitted = st.form_submit_button(mt("save_profile"), use_container_width=True)
        if submitted:
            data, error = backend_request(
                "PATCH",
                "/api/account/profile",
                payload={"display_name": display_name, "email": email or None},
            )
            if data:
                st.session_state["account_user"] = data.get("user")
                st.success(mt("profile_saved"))
            else:
                st.error(mt("backend_request_failed", error=error))
        current_email = safe_str(current_account_user().get("email"))
        if current_email:
            if current_account_user().get("email_verified"):
                st.success(mt("email_verified"))
            else:
                st.warning(mt("email_unverified"))
                if st.button(mt("request_verification"), use_container_width=True):
                    verification, error = backend_request(
                        "POST",
                        "/api/account/email-verification/request",
                    )
                    if verification:
                        if verification.get("email_delivery"):
                            st.success(mt("verification_requested"))
                        else:
                            st.warning(mt("email_delivery_unavailable"))
                    else:
                        st.error(mt("backend_request_failed", error=error))

    with history_tab:
        history_payload, history_error = backend_request(
            "GET",
            "/api/sessions",
            params={"limit": 100},
        )
        sessions = history_payload.get("sessions", []) if history_payload else []
        if not sessions:
            st.info(mt("no_history"))
            if history_error:
                st.caption(history_error)
        else:
            rows = []
            for session in sessions:
                item_summary = session.get("summary") or {}
                rows.append(
                    {
                        "session_id": session.get("session_id"),
                        "essay_id": session.get("essay_id"),
                        "student_level": session.get("student_level"),
                        "feedback_items": item_summary.get("feedback_items", 0),
                        "auto_accept": item_summary.get("auto_accept", 0),
                        "teacher_review": item_summary.get("teacher_review", 0),
                        "created_at": session.get("created_at"),
                    }
                )
            history_frame = pd.DataFrame(rows)
            search_text = st.text_input(mt("history_search"), key="account_history_search").strip().lower()
            if search_text:
                mask = (
                    history_frame["essay_id"].astype(str).str.lower().str.contains(search_text, regex=False)
                    | history_frame["session_id"].astype(str).str.lower().str.contains(search_text, regex=False)
                )
                visible_history = history_frame[mask].copy()
            else:
                visible_history = history_frame.copy()
            if visible_history.empty:
                st.info(mt("no_history"))
            else:
                st.dataframe(display_frame(visible_history), use_container_width=True, hide_index=True)
                visible_session_ids = set(visible_history["session_id"].astype(str))
                visible_sessions = [
                    item for item in sessions if safe_str(item.get("session_id")) in visible_session_ids
                ]
                labels = {
                    f"{safe_str(item.get('essay_id'))} · {safe_str(item.get('created_at'))[:16]} · {safe_str(item.get('session_id'))}": safe_str(item.get("session_id"))
                    for item in visible_sessions
                }
                selected_label = st.selectbox(mt("recent_reviews"), list(labels))
                session_id = labels[selected_label]
                confirm_deletion = st.checkbox(
                    mt("confirm_delete_review"),
                    key=f"confirm_delete_review_{session_id}",
                )
                open_col, delete_col = st.columns(2)
                if open_col.button(mt("open_review"), use_container_width=True, type="primary"):
                    loaded, error = load_personal_review(session_id)
                    if loaded:
                        st.session_state["esl_single_result"] = loaded
                        st.session_state["esl_batch_result"] = None
                        st.session_state["active_review_session_id"] = session_id
                        decisions_payload, _ = backend_request(
                            "GET",
                            "/api/teacher/decisions",
                            params={"session_id": session_id},
                        )
                        decisions = decisions_payload.get("decisions", []) if decisions_payload else []
                        saved_decisions = {
                            decision_state_key(session_id, item.get("feedback_item_id")): safe_str(item.get("teacher_action"))
                            for item in decisions
                        }
                        st.session_state["teacher_decisions"] = saved_decisions.copy()
                        st.session_state["saved_teacher_decisions"] = saved_decisions.copy()
                        st.success(mt("session_loaded"))
                        display_esl_summary(loaded.get("summary", {}))
                    else:
                        st.error(mt("backend_request_failed", error=error))
                if delete_col.button(
                    mt("delete_review"),
                    use_container_width=True,
                    disabled=not confirm_deletion,
                ):
                    deleted, error = backend_request("DELETE", f"/api/sessions/{session_id}")
                    if deleted:
                        if safe_str(st.session_state.get("active_review_session_id")) == session_id:
                            st.session_state["esl_single_result"] = None
                            st.session_state["esl_batch_result"] = None
                            st.session_state["active_review_session_id"] = ""
                            st.session_state["teacher_decisions"] = {}
                            st.session_state["saved_teacher_decisions"] = {}
                        st.session_state["account_flash"] = mt("review_deleted")
                        st.rerun()
                    else:
                        st.error(mt("backend_request_failed", error=error))

    with password_tab:
        with st.form("account_password_form"):
            current_password = st.text_input(mt("current_password"), type="password")
            new_password = st.text_input(mt("new_password"), type="password")
            confirmation = st.text_input(mt("confirm_password"), type="password")
            submitted = st.form_submit_button(mt("change_password"), use_container_width=True)
        if submitted:
            if new_password != confirmation:
                st.error(mt("password_mismatch"))
            else:
                data, error = backend_request(
                    "POST",
                    "/api/account/password",
                    payload={
                        "current_password": current_password,
                        "new_password": new_password,
                    },
                )
                if data:
                    clear_account_session()
                    st.success(mt("password_changed"))
                    time.sleep(0.4)
                    st.rerun()
                else:
                    st.error(mt("backend_request_failed", error=error))

    with data_tab:
        st.markdown(f"### {mt('account_data')}")
        export_payload, export_error = backend_request("GET", "/api/account/export", timeout=120)
        if export_payload:
            export_data = export_payload.get("account_data", {})
            st.download_button(
                mt("download_account_data"),
                data=json.dumps(export_data, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name="consensusscope_account_data.json",
                mime="application/json",
                use_container_width=True,
            )
        elif export_error:
            st.warning(mt("backend_request_failed", error=export_error))

        st.markdown(f"### {mt('danger_zone')}")
        st.error(mt("delete_account_warning"))
        with st.form("delete_account_form"):
            deletion_password = st.text_input(mt("current_password"), type="password")
            deletion_confirmation = st.text_input(mt("delete_confirmation"))
            submitted = st.form_submit_button(
                mt("delete_account"),
                use_container_width=True,
            )
        if submitted:
            deleted, error = backend_request(
                "DELETE",
                "/api/account",
                payload={
                    "password": deletion_password,
                    "confirmation": deletion_confirmation,
                },
            )
            if deleted:
                clear_account_session()
                st.success(mt("account_deleted"))
                time.sleep(0.5)
                st.rerun()
            else:
                st.error(mt("backend_request_failed", error=error))


def page_product_feedback() -> None:
    page_header("feedback_title", "feedback_caption")
    user = current_account_user()
    categories = ["bug", "feature", "usability", "output_quality", "other"]
    related_pages = [
        "",
        mt("page_home"),
        mt("page_single"),
        mt("page_batch"),
        mt("page_compare"),
        mt("page_queue"),
        mt("page_reports"),
        mt("page_account"),
        mt("page_settings"),
    ]
    with st.form("product_feedback_form", clear_on_submit=True):
        category = st.selectbox(mt("feedback_category"), categories, format_func=value_label)
        rating = st.slider(mt("feedback_rating"), min_value=1, max_value=5, value=4)
        related_page = st.selectbox(mt("feedback_page"), related_pages)
        message = st.text_area(mt("feedback_message"), height=180)
        has_email = bool(safe_str(user.get("email")))
        allow_contact = st.checkbox(mt("allow_contact"), value=False, disabled=not has_email)
        submitted = st.form_submit_button(mt("submit_feedback"), use_container_width=True, type="primary")
    if submitted:
        if len(message.strip()) < 5:
            st.error(mt("feedback_message_required"))
        else:
            data, error = backend_request(
                "POST",
                "/api/feedback",
                payload={
                    "category": category,
                    "rating": rating,
                    "message": message,
                    "page": related_page or None,
                    "allow_contact": allow_contact,
                },
            )
            if data:
                st.success(mt("feedback_submitted"))
            else:
                st.error(mt("backend_request_failed", error=error))

    history_payload, _ = backend_request("GET", "/api/feedback/mine")
    own_feedback = history_payload.get("feedback", []) if history_payload else []
    if own_feedback:
        st.markdown(f"### {mt('my_feedback')}")
        own_frame = pd.DataFrame(own_feedback)
        own_columns = ["category", "rating", "message", "page", "status", "created_at"]
        st.dataframe(
            display_frame(own_frame[[col for col in own_columns if col in own_frame.columns]]),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(mt("no_feedback_history"))

    if user.get("is_admin"):
        admin_payload, error = backend_request("GET", "/api/admin/feedback")
        inbox = admin_payload.get("feedback", []) if admin_payload else []
        st.markdown(f"### {mt('admin_feedback')}")
        if inbox:
            st.dataframe(display_frame(pd.DataFrame(inbox)), use_container_width=True, hide_index=True)
        elif error:
            st.warning(mt("backend_request_failed", error=error))


def page_settings_diagnostics(
    api_mode: str,
    selected: List[str],
    user_inputs: Dict[str, Dict[str, str]],
    fixed_enabled: bool,
    fixed_provider: str,
    samples_df: pd.DataFrame,
    outputs_df: pd.DataFrame,
    metrics_df: pd.DataFrame,
    risk_df: pd.DataFrame,
    effectiveness_df: pd.DataFrame,
    error_df: pd.DataFrame,
) -> None:
    page_header("settings_title")
    st.info(mt("settings_info"))
    with st.expander(mt("backend_api"), expanded=True):
        url = backend_api_url()
        health = backend_healthcheck(url)
        st.caption(mt("backend_description"))
        st.write(f"{mt('backend_url')}: {url}")
        status = mt("backend_available") if health["ok"] else mt("backend_unavailable")
        st.write(f"{mt('backend_status')}: {status}")
        if health["ok"]:
            st.json(health["payload"])
        else:
            st.code(health["error"] or mt("backend_not_configured"), language="text")
    with st.expander(mt("api_diagnostics"), expanded=False):
        st.write(f"{mt('api_mode')}: {api_mode}")
        st.write(f"{mt('answer_models')}: {', '.join(selected) if selected else mt('none')}")
        st.write(f"{mt('enable_fixed_judge')}: {fixed_enabled}; {mt('fixed_judge_model')}: {fixed_provider or mt('not_available')}")
        st.write(f"{mt('storage_backend')}: {storage_backend_name()}")
    with st.expander(mt("page_eval"), expanded=False):
        page_effectiveness_evaluation()
    with st.expander(mt("legacy_feedback"), expanded=False):
        render_literary_feedback_mode(api_mode, selected, user_inputs)
    with st.expander(mt("aux_qa_comparison"), expanded=False):
        page_comparison(metrics_df)
    with st.expander(mt("aux_qa_risk"), expanded=False):
        page_risk_dashboard(risk_df, effectiveness_df)
    with st.expander(mt("aux_qa_case"), expanded=False):
        page_case_explorer(error_df, samples_df, outputs_df)


def page_home(samples_df: pd.DataFrame, outputs_df: pd.DataFrame, metrics_df: pd.DataFrame, risk_df: pd.DataFrame) -> None:
    del samples_df, outputs_df, metrics_df, risk_df
    page_header("home_title", "home_caption")
    workspace_error = safe_str(st.session_state.pop("workspace_error", ""))
    if workspace_error:
        st.error(mt("backend_request_failed", error=workspace_error))

    user = current_account_user()
    display_name = safe_str(user.get("display_name")) or safe_str(user.get("username"))
    st.markdown(
        f'<div class="welcome-line">{html.escape(mt("welcome_back", name=display_name))}</div>',
        unsafe_allow_html=True,
    )

    personal_payload, summary_error = backend_request("GET", "/api/account/summary")
    personal = personal_payload.get("summary", {}) if personal_payload else {}
    if summary_error:
        st.warning(mt("backend_request_failed", error=summary_error))
    p1, p2, p3, p4 = st.columns(4)
    p1.metric(mt("courses"), int(personal.get("courses", 0)))
    p2.metric(mt("assignments"), int(personal.get("assignments", 0)))
    p3.metric(mt("essays"), int(personal.get("essays", 0)))
    p4.metric(mt("active_jobs"), int(personal.get("active_jobs", 0)))
    r1, r2, r3, r4 = st.columns(4)
    r1.metric(mt("review_sessions"), int(personal.get("review_sessions", 0)))
    r2.metric(mt("feedback_items"), int(personal.get("feedback_items", 0)))
    r3.metric(mt("review_routed"), int(personal.get("review_routed", 0)))
    r4.metric(mt("saved_decisions"), int(personal.get("teacher_decisions", 0)))

    st.markdown(f'<div class="section-title">{mt("quick_actions")}</div>', unsafe_allow_html=True)
    assignment_action, single_action, batch_action, queue_action, report_action = st.columns(5)
    assignment_action.button(
        mt("manage_assignments"),
        use_container_width=True,
        on_click=navigate_to,
        args=("page_assignments",),
    )
    single_action.button(
        mt("new_single_review"),
        use_container_width=True,
        type="primary",
        on_click=navigate_to,
        args=("page_single",),
    )
    batch_action.button(
        mt("new_batch_review"),
        use_container_width=True,
        on_click=navigate_to,
        args=("page_batch",),
    )
    queue_action.button(
        mt("open_queue"),
        use_container_width=True,
        on_click=navigate_to,
        args=("page_queue",),
    )
    report_action.button(
        mt("open_reports"),
        use_container_width=True,
        on_click=navigate_to,
        args=("page_reports",),
    )

    st.markdown(f'<div class="section-title">{mt("workflow_status")}</div>', unsafe_allow_html=True)
    render_workflow_strip()

    st.markdown(f'<div class="section-title">{mt("workspace_activity")}</div>', unsafe_allow_html=True)
    jobs_payload, _ = backend_request("GET", "/api/review/jobs", params={"limit": 8})
    recent_jobs = jobs_payload.get("jobs", []) if jobs_payload else []
    if recent_jobs:
        job_rows = [
            {
                "job_status": item.get("status"),
                "generation_mode": item.get("generation_mode"),
                "progress": item.get("progress"),
                "created_at": item.get("created_at"),
            }
            for item in recent_jobs
        ]
        st.dataframe(display_frame(pd.DataFrame(job_rows)), use_container_width=True, hide_index=True)

    st.markdown(f'<div class="section-title">{mt("recent_activity")}</div>', unsafe_allow_html=True)
    history_payload, history_error = backend_request("GET", "/api/sessions", params={"limit": 5})
    sessions = history_payload.get("sessions", []) if history_payload else []
    if sessions:
        recent_rows = []
        for session in sessions:
            item_summary = session.get("summary") or {}
            recent_rows.append(
                {
                    "essay_id": session.get("essay_id"),
                    "feedback_items": item_summary.get("feedback_items", 0),
                    "teacher_review": item_summary.get("teacher_review", 0),
                    "created_at": session.get("created_at"),
                }
            )
        st.dataframe(display_frame(pd.DataFrame(recent_rows)), use_container_width=True, hide_index=True)
        latest_session_id = safe_str(sessions[0].get("session_id"))
        st.button(
            mt("resume_review"),
            use_container_width=True,
            on_click=resume_personal_review,
            args=(latest_session_id,),
        )
    else:
        st.info(mt("no_recent_activity"))
        if history_error:
            st.caption(history_error)

    with st.expander(mt("reference_data"), expanded=False):
        esl_essays = read_table(str(DATA_PATHS["esl_essays"]))
        esl_feedback = read_table(str(DATA_PATHS["esl_feedback"]))
        esl_routing = read_table(str(DATA_PATHS["esl_routing"]))
        esl_stress = read_table(str(DATA_PATHS["esl_stress"]))
        teacher_review = int((esl_routing.get("recommended_action", pd.Series(dtype=str)) == "teacher_review").sum()) if not esl_routing.empty else 0
        auto_accept = int((esl_routing.get("recommended_action", pd.Series(dtype=str)) == "auto_accept").sum()) if not esl_routing.empty else 0
        high_risk = int((esl_routing.get("risk_level", pd.Series(dtype=str)) == "high").sum()) if not esl_routing.empty else 0
        snapshot = {
            "synthetic_essays": len(esl_essays),
            "feedback_items": len(esl_feedback),
            "ai_review_stress_cases": len(esl_stress),
            "auto_accept": auto_accept,
            "teacher_review": teacher_review,
            "high_risk": high_risk,
        }
        st.dataframe(display_frame(pd.DataFrame([snapshot])), use_container_width=True, hide_index=True)
        st.info(mt("safety_graph_mechanism"))


def render_literary_feedback_mode(api_mode: str, selected: List[str], user_inputs: Dict[str, Dict[str, str]]) -> None:
    kg = load_literary_kg(str(DATA_PATHS["literary_kg"]))
    st.markdown(f'<div class="section-title">{mt("literary_title")}</div>', unsafe_allow_html=True)
    st.caption(mt("literary_caption"))
    left, right = st.columns([1.05, 0.95], gap="large")
    with left:
        example = st.selectbox(mt("demo_essay"), list(EXAMPLE_ESSAYS.keys()))
        default_essay = EXAMPLE_ESSAYS.get(example, DEFAULT_LITERARY_ESSAY)
        essay = st.text_area(mt("student_excerpt"), value=default_essay, height=230)
        reviewer_source = st.radio(
            mt("reviewer_source"),
            ["No-API deterministic reviewers", "Live API reviewers"],
            format_func=lambda value: mt("no_api_reviewers") if value.startswith("No-API") else mt("live_api_reviewers"),
            horizontal=True,
        )
        run_feedback = st.button(mt("run_kg_feedback"), use_container_width=True)
        if run_feedback:
            kg_rows = retrieve_literary_knowledge(essay, kg, limit=16)
            reviewer_results: List[Dict[str, Any]] = []
            if reviewer_source == "Live API reviewers":
                configs = build_live_configs(api_mode, selected, user_inputs)
                live_result = run_live_literary_reviewers(configs, essay, kg_rows)
                feedback = live_result.get("feedback", [])
                reviewer_results = live_result.get("reviewer_results", [])
                if not feedback:
                    feedback = generate_demo_literary_feedback(essay, kg)
            else:
                feedback = generate_demo_literary_feedback(essay, kg)
            decisions = adjudicate_literary_feedback(feedback)
            revised = apply_auto_accepted_edits(essay, decisions)
            st.session_state["literary_result"] = {
                "essay": essay,
                "revised": revised,
                "kg_rows": kg_rows,
                "feedback": feedback,
                "reviewer_source": reviewer_source,
                "reviewer_results": reviewer_results,
                "decisions": decisions,
                "report": build_literary_feedback_report(essay, kg_rows, feedback, decisions),
            }
    with right:
        result = st.session_state.get("literary_result")
        decisions = (result or {}).get("decisions", [])
        summary = literary_routing_summary(decisions)
        c1, c2 = st.columns(2)
        c1.metric(mt("auto_accept_metric"), summary["auto_accept"])
        c2.metric(mt("teacher_review"), summary["teacher_review"])
        c3, c4 = st.columns(2)
        c3.metric(mt("high_risk"), summary["high_risk"])
        c4.metric(mt("kg_supported"), summary["kg_supported"])
        c5, c6 = st.columns(2)
        c5.metric(mt("kg_works"), int(kg["work"].nunique()) if not kg.empty and "work" in kg else 0)
        c6.metric(mt("legacy_triples"), len(kg))
        if result:
            st.download_button(
                mt("download_legacy_report"),
                data=result["report"].encode("utf-8"),
                file_name="legacy_feedback_report.md",
                mime="text/markdown",
                use_container_width=True,
            )

    result = st.session_state.get("literary_result")
    if not result:
        st.info(mt("run_literary_info"))
        return

    decisions = result.get("decisions", [])
    queue = review_queue(decisions)
    tabs = st.tabs([mt("teacher_view"), mt("knowledge_evidence"), mt("adjudication_trace"), mt("raw_suggestions")])
    with tabs[0]:
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown(f"**{mt('original_essay')}**")
            st.text_area(mt("original"), value=result.get("essay", ""), height=210, disabled=True, label_visibility="collapsed")
        with c2:
            st.markdown(f"**{mt('auto_preview')}**")
            st.text_area(mt("preview"), value=result.get("revised", result.get("essay", "")), height=210, disabled=True, label_visibility="collapsed")
        if queue:
            st.markdown(f'<div class="section-title">{mt("teacher_queue_table")}</div>', unsafe_allow_html=True)
            queue_df = pd.DataFrame(queue)
            display_cols = [
                "priority",
                "risk_level",
                "issue_type",
                "span",
                "selected_suggestion",
                "teacher_action",
                "agreement",
                "kg_supported",
                "rationale",
            ]
            st.dataframe(display_frame(queue_df[[c for c in display_cols if c in queue_df.columns]]), use_container_width=True, hide_index=True)
        summary_rows = decision_summary_by_type(decisions)
        if summary_rows:
            st.markdown(f'<div class="section-title">{mt("feedback_distribution")}</div>', unsafe_allow_html=True)
            st.dataframe(display_frame(pd.DataFrame(summary_rows)), use_container_width=True, hide_index=True)

    with tabs[1]:
        kg_rows = result.get("kg_rows", [])
        if kg_rows:
            st.dataframe(display_frame(pd.DataFrame(kg_rows)), use_container_width=True, hide_index=True)
        else:
            st.info(mt("no_kg_match"))

    with tabs[2]:
        decisions_df = pd.DataFrame(decisions)
        st.dataframe(display_frame(decisions_df), use_container_width=True, hide_index=True)

    with tabs[3]:
        reviewer_results = result.get("reviewer_results", [])
        if reviewer_results:
            st.markdown(f"**{mt('live_status')}**")
            status_df = pd.DataFrame(
                [
                    {
                        "provider": item.get("provider", ""),
                        "model": item.get("model", ""),
                        "reviewer_role": item.get("reviewer_role", ""),
                        "feedback_items": len(item.get("feedback", [])),
                        "request_error": item.get("request_error", ""),
                        "parse_error": item.get("parse_error", ""),
                        "latency_sec": item.get("latency_sec", 0.0),
                    }
                    for item in reviewer_results
                ]
            )
            st.dataframe(display_frame(status_df), use_container_width=True, hide_index=True)
        feedback_df = pd.DataFrame(result.get("feedback", []))
        if not feedback_df.empty and "knowledge_evidence" in feedback_df.columns:
            feedback_df = feedback_df.copy()
            feedback_df["knowledge_evidence"] = feedback_df["knowledge_evidence"].map(lambda values: " | ".join(values) if isinstance(values, list) else values)
        st.dataframe(display_frame(feedback_df), use_container_width=True, hide_index=True)


def saved_literary_result() -> Dict[str, Any]:
    session_result = st.session_state.get("literary_result")
    if session_result:
        return session_result
    records = read_json_records(str(DATA_PATHS["literary_records"]))
    if not records:
        return {}
    record = records[0]
    essay = record.get("essay", "")
    kg_rows = record.get("kg_rows", [])
    feedback = record.get("feedback", [])
    decisions = record.get("decisions", [])
    return {
        "essay": essay,
        "revised": apply_auto_accepted_edits(essay, decisions),
        "kg_rows": kg_rows,
        "feedback": feedback,
        "reviewer_source": "Saved no-API deterministic reviewers",
        "reviewer_results": [],
        "decisions": decisions,
        "report": build_literary_feedback_report(essay, kg_rows, feedback, decisions),
    }


def page_knowledge_teacher_queue() -> None:
    st.markdown(f'<div class="section-title">{mt("legacy_title")}</div>', unsafe_allow_html=True)
    result = saved_literary_result()
    if not result:
        st.info(mt("run_page_first"))
        return
    st.caption(mt("legacy_caption"))
    decisions = result.get("decisions", [])
    summary = literary_routing_summary(decisions)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(mt("auto_accept_metric"), summary["auto_accept"])
    c2.metric(mt("teacher_review"), summary["teacher_review"])
    c3.metric(mt("high_risk"), summary["high_risk"])
    c4.metric(mt("kg_supported"), summary["kg_supported"])

    tabs = st.tabs([mt("teacher_queue_table"), mt("knowledge_evidence"), mt("adjudication_trace"), mt("export_preview")])
    with tabs[0]:
        queue = review_queue(decisions)
        if queue:
            display_cols = [
                "priority",
                "risk_level",
                "issue_type",
                "span",
                "selected_suggestion",
                "teacher_action",
                "agreement",
                "kg_supported",
                "rationale",
            ]
            queue_df = pd.DataFrame(queue)
            st.dataframe(display_frame(queue_df[[c for c in display_cols if c in queue_df.columns]]), use_container_width=True, hide_index=True)
        else:
            st.success(mt("no_teacher_items"))
    with tabs[1]:
        kg_rows = result.get("kg_rows", [])
        if kg_rows:
            st.dataframe(display_frame(pd.DataFrame(kg_rows)), use_container_width=True, hide_index=True)
        else:
            st.info(mt("no_kg_evidence"))
    with tabs[2]:
        st.dataframe(display_frame(pd.DataFrame(decisions)), use_container_width=True, hide_index=True)
    with tabs[3]:
        st.download_button(
            mt("download_legacy_report"),
            data=result.get("report", "").encode("utf-8"),
            file_name="legacy_feedback_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.text_area(mt("report_preview"), result.get("report", ""), height=260)


def page_live(api_mode: str, selected: List[str], user_inputs: Dict[str, Dict[str, str]], fixed_enabled: bool, fixed_provider: str) -> None:
    st.markdown(f'<div class="section-title">{mt("tech_demo_title")}</div>', unsafe_allow_html=True)
    mode = st.radio(
        mt("mode"),
        ["Legacy feedback technical demo", "Auxiliary QA live comparison"],
        format_func=lambda value: mt("legacy_feedback") if value.startswith("Legacy") else mt("aux_qa_comparison"),
        horizontal=True,
        label_visibility="collapsed",
    )
    if mode == "Legacy feedback technical demo":
        st.warning(mt("legacy_warning"))
        render_literary_feedback_mode(api_mode, selected, user_inputs)
        return

    left, right = st.columns([0.95, 1.05], gap="large")
    with left:
        task_type = st.selectbox(
            mt("task_type"),
            [TASK_FACT_QA, TASK_CLAIM, TASK_CHOICE],
            format_func=lambda x: {TASK_FACT_QA: mt("task_fact_qa"), TASK_CLAIM: mt("task_claim"), TASK_CHOICE: mt("task_choice")}[x],
        )
        question = st.text_area(mt("question_claim"), height=130)
        choices: Dict[str, str] = {}
        if task_type == TASK_CHOICE:
            c1, c2 = st.columns(2)
            with c1:
                choices["A"] = st.text_input("A")
                choices["B"] = st.text_input("B")
            with c2:
                choices["C"] = st.text_input("C")
                choices["D"] = st.text_input("D")
        temperature = st.slider(mt("temperature"), 0.0, 1.0, 0.2, 0.05)
        if st.button(mt("run_live"), use_container_width=True):
            configs = build_live_configs(api_mode, selected, user_inputs)
            fixed_cfg = build_fixed_judge_config(api_mode, fixed_provider, user_inputs, fixed_enabled)
            history = load_historical_reliability(str(DATA_PATHS["samples"]), str(DATA_PATHS["outputs_csv"]))
            with st.spinner(mt("calling_models")):
                outputs = run_live_models(configs, task_type, question, choices, temperature=temperature)
                comparison = adjudication_comparison_live(task_type, question, choices, outputs, history, fixed_cfg)
            st.session_state["live_result"] = {
                "task_type": task_type,
                "question": question,
                "choices": choices,
                "outputs": outputs,
                "comparison": comparison,
                "report": build_live_report(
                    task_type,
                    question,
                    choices,
                    outputs,
                    comparison["methods"][0],
                    comparison["methods"][2],
                    comparison["methods"][1],
                ),
            }
    with right:
        result = st.session_state.get("live_result")
        render_adjudication_comparison((result or {}).get("comparison"))
    st.markdown(f'<div class="section-title">{mt("unified_format")}</div>', unsafe_allow_html=True)
    render_model_outputs((st.session_state.get("live_result") or {}).get("outputs", []))


def sample_selector(samples_df: pd.DataFrame, risk_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    if samples_df.empty:
        st.error(mt("no_samples"))
        return None
    samples = samples_df.copy()
    if "dataset" not in samples.columns:
        samples["dataset"] = "unknown"
    datasets = ["All"] + sorted(samples["dataset"].fillna("unknown").astype(str).unique().tolist())
    selected_dataset = st.selectbox(mt("dataset"), datasets, format_func=lambda value: mt("all") if value == "All" else value)
    filtered = samples if selected_dataset == "All" else samples[samples["dataset"].astype(str) == selected_dataset]
    if not risk_df.empty and "sample_id" in risk_df.columns:
        only_risk = st.checkbox(mt("show_evaluated"), value=True)
        if only_risk:
            ids = set(risk_df["sample_id"].dropna().astype(str))
            filtered = filtered[filtered["id"].astype(str).isin(ids)]
    if filtered.empty:
        st.warning(mt("no_sample_match"))
        return None
    sample_ids = filtered["id"].astype(str).tolist()
    default_sample_id = "fever_0366" if "fever_0366" in sample_ids else sample_ids[0]
    sid = st.selectbox(mt("sample_id"), sample_ids, index=sample_ids.index(default_sample_id))
    return filtered[filtered["id"].astype(str) == sid].iloc[0].to_dict()


def page_sample_audit(samples_df: pd.DataFrame, outputs_df: pd.DataFrame, majority_df: pd.DataFrame, dynamic_df: pd.DataFrame, fixed_df: pd.DataFrame, risk_df: pd.DataFrame) -> None:
    st.markdown(f'<div class="section-title">{mt("sample_audit_title")}</div>', unsafe_allow_html=True)
    sample = sample_selector(samples_df, risk_df)
    if not sample:
        return
    sid = safe_str(sample.get("id", ""))
    st.markdown(f"**{mt('question_claim_label')}**")
    st.write(safe_str(sample.get("question", "")))
    st.markdown(f"**{mt('options')}**")
    st.text(parse_options(sample.get("options", "")))
    c1, c2, c3 = st.columns(3)
    c1.metric(mt("dataset"), safe_str(sample.get("dataset", "")))
    c2.metric(mt("gold_answer"), safe_str(sample.get("gold_answer", "")) or safe_str(sample.get("gold_label", "")))
    c3.metric(mt("task"), safe_str(sample.get("task_type", "")))

    outputs = dataframe_for_sample(outputs_df, "sample_id", sid)
    st.markdown(f'<div class="section-title">{mt("model_outputs")}</div>', unsafe_allow_html=True)
    if outputs.empty:
        st.warning(mt("no_sample_outputs"))
    else:
        display = outputs.copy()
        if "correct" not in display.columns:
            display["correct"] = display["answer"].map(lambda ans: is_correct(ans, sample.get("gold_answer", ""), sample.get("gold_label", "")))
        st.dataframe(display_frame(display, public=True), use_container_width=True, hide_index=True)

    rows = []
    for label, df in [
        ("Majority Vote", majority_df),
        ("Fixed Judge", fixed_df),
        ("Dynamic Rule-Based Judge", dynamic_df),
    ]:
        rec = first_record(dataframe_for_sample(df, "sample_id", sid))
        rows.append(decision_row(label, rec, sample))
    st.markdown(f'<div class="section-title">{mt("adjudication_layer")}</div>', unsafe_allow_html=True)
    st.dataframe(display_frame(pd.DataFrame(rows)), use_container_width=True, hide_index=True)

    risk = first_record(dataframe_for_sample(risk_df, "sample_id", sid))
    st.markdown(f'<div class="section-title">{mt("risk_labels_label")}</div>', unsafe_allow_html=True)
    risk_text = safe_str(risk.get("risk_labels", ""))
    st.write(value_label(risk_text) if risk_text else mt("none"))


def page_comparison(metrics_df: pd.DataFrame) -> None:
    st.markdown(f'<div class="section-title">{mt("comparison_legacy_title")}</div>', unsafe_allow_html=True)
    st.caption(mt("comparison_legacy_caption"))
    live = st.session_state.get("live_result")
    render_adjudication_comparison((live or {}).get("comparison"))
    st.markdown(f"### {mt('aux_qa_offline_metrics')}")
    metrics_df = visible_method_metrics(metrics_df)
    if metrics_df.empty:
        st.info(mt("missing_method_metrics"))
        return
    st.dataframe(display_frame(metrics_df), use_container_width=True, hide_index=True)
    if {"method", "accuracy"}.issubset(metrics_df.columns):
        st.bar_chart(metrics_df.set_index("method")["accuracy"])


def page_risk_dashboard(risk_df: pd.DataFrame, effectiveness_df: pd.DataFrame) -> None:
    st.markdown(f'<div class="section-title">{mt("risk_dashboard_title")}</div>', unsafe_allow_html=True)
    esl_routing = read_table(str(DATA_PATHS["esl_routing"]))
    if not esl_routing.empty:
        st.markdown(f"### {mt('esl_risk_title')}")
        auto_accept = int((esl_routing["recommended_action"] == "auto_accept").sum()) if "recommended_action" in esl_routing else 0
        teacher_review = int((esl_routing["recommended_action"] == "teacher_review").sum()) if "recommended_action" in esl_routing else 0
        high_risk = int((esl_routing["risk_level"] == "high").sum()) if "risk_level" in esl_routing else 0
        medium_risk = int((esl_routing["risk_level"] == "medium").sum()) if "risk_level" in esl_routing else 0
        low_risk = int((esl_routing["risk_level"] == "low").sum()) if "risk_level" in esl_routing else 0
        summary = {
            "source": "synthetic_esl_writing_demo",
            "feedback_items": len(esl_routing),
            "auto_accept": auto_accept,
            "teacher_review": teacher_review,
            "low_risk": low_risk,
            "medium_risk": medium_risk,
            "high_risk": high_risk,
        }
        st.dataframe(display_frame(pd.DataFrame([summary])), use_container_width=True, hide_index=True)
        st.caption(mt("synthetic_counts_caption"))
    if risk_df.empty:
        st.info(mt("missing_risk_labels"))
        return
    st.markdown(f"### {mt('offline_diagnostic_labels')}")
    st.caption(mt("offline_labels_caption"))
    labels: List[str] = []
    for item in risk_df.get("risk_labels", pd.Series(dtype=str)).fillna(""):
        labels.extend([x.strip() for x in str(item).split(";") if x.strip()])
    c1, c2, c3 = st.columns(3)
    c1.metric(mt("risk_samples"), len(risk_df))
    c2.metric(mt("false_consensus"), labels.count("false_consensus"))
    c3.metric(mt("minority_correct"), labels.count("minority_correct"))
    if labels:
        st.bar_chart(pd.Series(labels).value_counts())
    if not effectiveness_df.empty:
        st.markdown(f"### {mt('risk_effectiveness')}")
        st.dataframe(display_frame(effectiveness_df), use_container_width=True, hide_index=True)


def page_model_reliability(outputs_df: pd.DataFrame, samples_df: pd.DataFrame) -> None:
    st.markdown(f'<div class="section-title">{mt("model_reliability_title")}</div>', unsafe_allow_html=True)
    if outputs_df.empty or samples_df.empty:
        st.info(mt("missing_model_files"))
        return
    reliability = load_historical_reliability(str(DATA_PATHS["samples"]), str(DATA_PATHS["outputs_csv"]))
    rows = [{"model": k, "historical_accuracy_smoothed": v} for k, v in reliability.items()]
    st.dataframe(display_frame(pd.DataFrame(rows)), use_container_width=True, hide_index=True)
    if rows:
        st.bar_chart(pd.DataFrame(rows).set_index("model")["historical_accuracy_smoothed"])
    agg = outputs_df.groupby("model", as_index=False).agg(
        avg_confidence=("confidence", "mean"),
        calls=("answer", "size"),
    )
    st.markdown(f"### {mt('generation_stats')}")
    st.dataframe(display_frame(agg), use_container_width=True, hide_index=True)


def page_case_explorer(error_df: pd.DataFrame, samples_df: pd.DataFrame, outputs_df: pd.DataFrame) -> None:
    st.markdown(f'<div class="section-title">{mt("case_explorer_title")}</div>', unsafe_allow_html=True)
    st.caption(mt("case_explorer_caption"))
    if error_df.empty:
        st.info(mt("missing_error_cases"))
        return
    note_filter = st.multiselect(mt("case_tags"), sorted({x for s in error_df["notes"].fillna("") for x in str(s).split(";") if x}), default=[])
    df = error_df.copy()
    if note_filter:
        df = df[df["notes"].fillna("").apply(lambda s: any(tag in str(s).split(";") for tag in note_filter))]
    st.dataframe(display_frame(df, public=True), use_container_width=True, hide_index=True)
    if not df.empty:
        sid = st.selectbox(mt("inspect_case"), df["sample_id"].astype(str).tolist())
        sample = first_record(dataframe_for_sample(samples_df, "id", sid))
        st.write(sample.get("question", ""))
        st.dataframe(display_frame(dataframe_for_sample(outputs_df, "sample_id", sid), public=True), use_container_width=True, hide_index=True)


def page_report_export(samples_df: pd.DataFrame, outputs_df: pd.DataFrame, metrics_df: pd.DataFrame, risk_df: pd.DataFrame) -> None:
    st.markdown(f'<div class="section-title">{mt("report_export_title")}</div>', unsafe_allow_html=True)
    live = st.session_state.get("live_result")
    esl_essays = read_table(str(DATA_PATHS["esl_essays"]))
    esl_feedback = read_table(str(DATA_PATHS["esl_feedback"]))
    esl_routing = read_table(str(DATA_PATHS["esl_routing"]))
    if not esl_routing.empty:
        auto_accept = int((esl_routing["recommended_action"] == "auto_accept").sum()) if "recommended_action" in esl_routing else 0
        teacher_review = int((esl_routing["recommended_action"] == "teacher_review").sum()) if "recommended_action" in esl_routing else 0
        high_risk = int((esl_routing["risk_level"] == "high").sum()) if "risk_level" in esl_routing else 0
        if ui_lang() == "zh":
            esl_report = f"""ConsensusScope ESL 写作反馈路由报告

数据状态：合成演示数据
作文数：{len(esl_essays)}
反馈项数：{len(esl_feedback)}
自动接受：{auto_accept}
教师复核：{teacher_review}
高风险：{high_risk}

限制：
- 内置 ESL 写作演示使用合成记录。
- 系统用于路由 AI 反馈，不用于给作文自动评分。
- 离线教师标注需要与部署时路由信号分开报告。
"""
        else:
            esl_report = f"""ConsensusScope ESL Writing Feedback Routing Report

Data status: synthetic demo data
Essays: {len(esl_essays)}
Feedback items: {len(esl_feedback)}
Auto accepted: {auto_accept}
Teacher review: {teacher_review}
High risk: {high_risk}

Limitations:
- The packaged ESL writing demo uses synthetic records.
- The system routes AI feedback for teacher review; it does not grade essays.
- Offline teacher annotations must be reported separately from deploy-time routing signals.
"""
        st.download_button(
            mt("download_esl_report"),
            data=esl_report.encode("utf-8"),
            file_name="esl_writing_routing_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.download_button(
            mt("download_esl_routing"),
            data=esl_routing.to_csv(index=False, encoding="utf-8-sig"),
            file_name="esl_writing_routing_results.csv",
            mime="text/csv",
            use_container_width=True,
        )
    literary = saved_literary_result()
    if literary:
        st.download_button(
            mt("download_legacy_report"),
            data=literary.get("report", "").encode("utf-8"),
            file_name="legacy_feedback_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
    if live:
        st.download_button(
            mt("download_live_report"),
            data=live.get("report", "").encode("utf-8"),
            file_name="live_consensusscope_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
    report = {
        "esl_writing_essays": len(esl_essays),
        "esl_writing_feedback_items": len(esl_feedback),
        "esl_writing_routing_items": len(esl_routing),
        "samples": len(samples_df),
        "model_outputs": len(outputs_df),
        "method_metrics": metrics_df.to_dict(orient="records") if not metrics_df.empty else [],
        "risk_count": len(risk_df),
    }
    st.download_button(
        mt("download_summary_json"),
        data=json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name="system_summary.json",
        mime="application/json",
        use_container_width=True,
    )
    if not metrics_df.empty:
        st.download_button(
            mt("download_method_metrics"),
            data=metrics_df.to_csv(index=False, encoding="utf-8-sig"),
            file_name="method_metrics.csv",
            mime="text/csv",
            use_container_width=True,
        )
    if not risk_df.empty:
        buf = io.StringIO()
        risk_df.to_csv(buf, index=False, encoding="utf-8-sig")
        st.download_button(mt("download_risk_labels"), data=buf.getvalue(), file_name="risk_labels.csv", mime="text/csv", use_container_width=True)


def page_design_reference() -> None:
    st.markdown(f'<div class="section-title">{mt("design_title")}</div>', unsafe_allow_html=True)
    st.caption(mt("design_caption"))
    brief_path = ROOT / "ui_prototype" / "README.md"
    mockup_path = ROOT / "ui_prototype" / "index.html"

    c1, c2, c3 = st.columns([0.55, 0.23, 0.22])
    with c1:
        st.markdown(mt("design_text"))
    with c2:
        if brief_path.exists():
            st.download_button(
                mt("download_design_brief"),
                brief_path.read_bytes(),
                file_name="ConsensusScope_ESL_UI_prototype_readme.md",
                mime="text/markdown",
                use_container_width=True,
            )
    with c3:
        if mockup_path.exists():
            st.download_button(
                mt("download_html_mockup"),
                mockup_path.read_bytes(),
                file_name="ConsensusScope_ESL_writing_UI_prototype.html",
                mime="text/html",
                use_container_width=True,
            )

    if not mockup_path.exists():
        st.warning(mt("design_missing"))
        return

    components.html(mockup_path.read_text(encoding="utf-8"), height=1120, scrolling=True)


def main() -> None:
    st.set_page_config(
        page_title="ConsensusScope",
        page_icon=str(LOGO_PATH),
        layout="wide",
        initial_sidebar_state="auto",
    )
    load_dotenv(ROOT / ".env")
    inject_styles()
    ensure_state()
    render_sidebar_brand()
    language_choice = st.sidebar.selectbox(
        mt("language_label"),
        ["English", "中文"],
        index=0 if ui_lang() == "en" else 1,
        key="main_language_selector",
    )
    st.session_state["ui_language"] = "zh" if language_choice == "中文" else "en"
    topbar()
    handle_account_action_query()
    if not render_account_gate():
        render_footer()
        return

    page_keys = [
        "page_home",
        "page_assignments",
        "page_single",
        "page_batch",
        "page_queue",
        "page_reports",
        "page_account",
        "page_feedback",
    ]
    if current_account_user().get("is_admin"):
        page_keys.append("page_settings")
    pending_page_key = safe_str(st.session_state.pop("pending_page_key", ""))
    active_page_key = pending_page_key or safe_str(st.session_state.get("active_page_key")) or "page_home"
    if active_page_key not in page_keys:
        active_page_key = "page_home"
    if active_page_key == "page_settings" and not current_account_user().get("is_admin"):
        active_page_key = "page_home"
    navigation_key = f"main_page_key_{ui_lang()}"
    if pending_page_key:
        st.session_state.pop(navigation_key, None)
    st.sidebar.markdown(
        f'<div class="sidebar-section-label">{html.escape(mt("workspace_section"))}</div>',
        unsafe_allow_html=True,
    )
    page_key = st.sidebar.radio(
        mt("navigation"),
        page_keys,
        index=page_keys.index(active_page_key),
        format_func=mt,
        key=navigation_key,
        label_visibility="collapsed",
    )
    st.session_state["active_page_key"] = page_key
    if page_key == "page_settings":
        api_mode, selected, user_inputs, fixed_enabled, fixed_provider = render_api_sidebar()
    else:
        api_mode, selected, user_inputs, fixed_enabled, fixed_provider = "Server-managed", [], {}, False, ""
    render_sidebar_service()
    render_account_sidebar()

    samples_df = pd.DataFrame()
    outputs_df = pd.DataFrame()
    risk_df = pd.DataFrame()
    metrics_df = pd.DataFrame()
    effectiveness_df = pd.DataFrame()
    error_df = pd.DataFrame()
    if page_key == "page_settings":
        samples_df = read_table(str(DATA_PATHS["samples"]))
        outputs_df = load_outputs()
        risk_df = read_table(str(DATA_PATHS["risk_labels"]))
        metrics_df = read_table(str(DATA_PATHS["method_metrics"]))
        effectiveness_df = read_table(str(DATA_PATHS["risk_effectiveness"]))
        error_df = read_table(str(DATA_PATHS["error_cases"]))

    if page_key == "page_home":
        page_home(samples_df, outputs_df, metrics_df, risk_df)
    elif page_key == "page_assignments":
        page_assignments()
    elif page_key == "page_single":
        page_single_essay_review()
    elif page_key == "page_batch":
        page_batch_review()
    elif page_key == "page_compare":
        page_ai_feedback_comparison()
    elif page_key == "page_queue":
        page_teacher_queue()
    elif page_key == "page_reports":
        page_reports()
    elif page_key == "page_account":
        page_account()
    elif page_key == "page_feedback":
        page_product_feedback()
    elif page_key == "page_settings":
        page_settings_diagnostics(
            api_mode,
            selected,
            user_inputs,
            fixed_enabled,
            fixed_provider,
            samples_df,
            outputs_df,
            metrics_df,
            risk_df,
            effectiveness_df,
            error_df,
        )
    render_footer()


if __name__ == "__main__":
    main()
