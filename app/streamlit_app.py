from __future__ import annotations

import hmac
import io
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
        "topbar_subtitle": "Feedback Safety Graphs for teacher-in-the-loop ESL writing feedback review",
        "demo_access": "Demo Access",
        "demo_access_info": "This live demo is password-protected to prevent unintended API usage.",
        "demo_password": "Demo password",
        "unlock_demo": "Unlock demo",
        "invalid_password": "Invalid password.",
        "api_configuration": "API Configuration",
        "api_mode": "API mode",
        "mode_a": "Mode A · Built-in API keys for live demos",
        "mode_b": "Mode B · User-provided API keys for public deployment",
        "api_caption": "Mode A uses local .env or deployment secrets. Mode B uses user-provided keys only for the current request. API keys must not appear in the paper or be hard-coded.",
        "answer_models": "Answer generation models",
        "answer_models_help": "Each selected provider needs its own matching API key. If you only have one key, select only that provider.",
        "enable_fixed_judge": "Enable Fixed Judge in Live mode",
        "fixed_judge_model": "Fixed judge model",
        "provider_settings": "Provider settings",
        "provider_settings_help": "Use the provider base URL only; the app appends /chat/completions automatically.",
        "lock_demo": "Lock demo",
        "navigation": "Navigation",
        "page_home": "Page 1: Review Workspace",
        "page_single": "Page 2: Single Essay Review",
        "page_batch": "Page 3: Batch Review",
        "page_compare": "Page 4: AI Feedback Comparison",
        "page_queue": "Page 5: Teacher Queue",
        "page_eval": "Page 6: Effectiveness Evaluation",
        "page_reports": "Page 7: Reports",
        "page_settings": "Page 8: Settings / Diagnostics",
        "page_design": "Page 9: Design Reference",
        "feedback_items": "Feedback items",
        "auto_accepted": "Auto accepted",
        "teacher_review": "Teacher review",
        "high_risk": "High risk",
        "urgent": "Urgent",
        "mean_risk": "Mean risk",
        "no_feedback": "No feedback items available.",
        "single_title": "Page 2 · Single Essay Review",
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
        "batch_title": "Page 3 · Batch Review",
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
        "compare_title": "Page 4 · AI Feedback Comparison",
        "run_first": "Run Single Essay Review or Batch Review first, or use the packaged demo data.",
        "compare_caption": "This page compares AI feedback candidates by target span, issue type, reviewers, routed risk, safety-graph dimensions, and consensus state.",
        "no_comparison": "No comparison rows are available.",
        "consensus_states": "Consensus states",
        "queue_title": "Page 5 · Teacher Queue",
        "queue_empty": "No teacher-review items are currently queued.",
        "queue_caption": "Teachers can accept, edit, reject, or defer feedback. Decisions are stored in the local Streamlit session.",
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
        "download_queue": "Download teacher queue.csv",
        "eval_title": "Page 6 · Effectiveness Evaluation",
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
        "reports_title": "Page 7 · Reports",
        "report_table": "Report table",
        "report_preview": "Report preview",
        "download_routed_csv": "Download routed feedback.csv",
        "download_report_md": "Download report.md",
        "settings_title": "Page 8 · Settings / Diagnostics",
        "settings_info": "Operational teacher workflow pages are now Pages 2-7. This page keeps API settings and legacy diagnostics secondary.",
        "api_diagnostics": "API diagnostics",
        "legacy_feedback": "Legacy feedback technical demo",
        "aux_qa_comparison": "Auxiliary QA comparison",
        "aux_qa_risk": "Auxiliary QA risk dashboard",
        "aux_qa_case": "Auxiliary QA case explorer",
        "home_title": "Page 1 · Home / System Overview",
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
        "auth_not_configured": "Demo authentication is enabled, but CONSENSUS_SCOPE_DEMO_PASSWORD is not configured.",
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
        "workflow_line": "Single Essay Review -> Batch Review -> AI Feedback Comparison -> Teacher Queue -> Effectiveness Evaluation -> Reports",
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
        "api_key_label": "{provider} API key",
        "model_label": "{provider} model",
        "base_url_label": "{provider} base URL",
        "storage_backend": "Storage backend",
        "session_only": "Browser session only",
        "reviewer_id": "Reviewer ID",
        "reviewer_id_help": "Anonymous label used only in the current browser session.",
        "decision_saved": "Decision saved.",
        },
    "zh": {
        "language_label": "Language / 语言",
        "topbar_subtitle": "基于反馈安全图谱的 ESL 写作 AI 反馈教师复核路由",
        "demo_access": "演示访问",
        "demo_access_info": "该在线演示已启用密码保护，以避免无意调用 API。",
        "demo_password": "演示密码",
        "unlock_demo": "解锁演示",
        "invalid_password": "密码错误。",
        "api_configuration": "API 配置",
        "api_mode": "API 模式",
        "mode_a": "模式 A · 使用部署端内置 API key，适合现场演示",
        "mode_b": "模式 B · 使用用户自己的 API key，适合公开部署",
        "api_caption": "模式 A 使用本地 .env 或部署端 Secrets。模式 B 只在当前请求中使用用户输入的 key。API key 不能写入论文，也不能硬编码进代码。",
        "answer_models": "回答生成模型",
        "answer_models_help": "每个服务商都需要对应 API key。如果你只有一个 key，只选择对应服务商。",
        "enable_fixed_judge": "实时模式启用固定裁判",
        "fixed_judge_model": "固定裁判模型",
        "provider_settings": "服务商设置",
        "provider_settings_help": "只填写服务商 base URL；应用会自动追加 /chat/completions。",
        "lock_demo": "锁定演示",
        "navigation": "导航",
        "page_home": "第 1 页：评审工作台",
        "page_single": "第 2 页：单篇作文评审",
        "page_batch": "第 3 页：批量评审",
        "page_compare": "第 4 页：AI 反馈对比",
        "page_queue": "第 5 页：教师复核队列",
        "page_eval": "第 6 页：有效性评估",
        "page_reports": "第 7 页：报告导出",
        "page_settings": "第 8 页：设置 / 诊断",
        "page_design": "第 9 页：设计参考",
        "feedback_items": "反馈项",
        "auto_accepted": "自动接受",
        "teacher_review": "教师复核",
        "high_risk": "高风险",
        "urgent": "紧急",
        "mean_risk": "平均风险",
        "no_feedback": "暂无反馈项。",
        "single_title": "第 2 页 · 单篇作文评审",
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
        "batch_title": "第 3 页 · 批量评审",
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
        "compare_title": "第 4 页 · AI 反馈对比",
        "run_first": "请先运行单篇作文评审或批量评审，或使用内置 demo 数据。",
        "compare_caption": "本页按目标片段、问题类型、评审器、路由风险、安全图谱维度和一致性状态对比 AI 反馈候选。",
        "no_comparison": "暂无对比结果。",
        "consensus_states": "一致性状态",
        "queue_title": "第 5 页 · 教师复核队列",
        "queue_empty": "当前没有需要教师复核的项目。",
        "queue_caption": "教师可以接受、编辑、拒绝或暂缓反馈。决策会保存在当前网页会话中。",
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
        "download_queue": "下载教师队列.csv",
        "eval_title": "第 6 页 · 有效性评估",
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
        "reports_title": "第 7 页 · 报告导出",
        "report_table": "报告表格",
        "report_preview": "报告预览",
        "download_routed_csv": "下载路由反馈.csv",
        "download_report_md": "下载报告.md",
        "settings_title": "第 8 页 · 设置 / 诊断",
        "settings_info": "当前主线教师工作流位于第 2-7 页。本页只保留 API 设置和旧辅助诊断。",
        "api_diagnostics": "API 诊断",
        "legacy_feedback": "旧反馈技术演示",
        "aux_qa_comparison": "辅助 QA 对比",
        "aux_qa_risk": "辅助 QA 风险面板",
        "aux_qa_case": "辅助 QA 案例浏览",
        "home_title": "第 1 页 · 首页 / 系统概览",
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
        "auth_not_configured": "已启用演示密码保护，但未配置 CONSENSUS_SCOPE_DEMO_PASSWORD。",
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
        "workflow_line": "单篇作文评审 -> 批量评审 -> AI 反馈对比 -> 教师复核队列 -> 有效性评估 -> 报告导出",
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
        "api_key_label": "{provider} API key",
        "model_label": "{provider} 模型名称",
        "base_url_label": "{provider} Base URL",
        "storage_backend": "存储后端",
        "session_only": "仅当前浏览器会话",
        "reviewer_id": "教师编号",
        "reviewer_id_help": "仅作为当前浏览器会话中的匿名标识。",
        "decision_saved": "决策已保存。",
    },
}


def ui_lang() -> str:
    return safe_str(st.session_state.get("ui_language") or "en")


def mt(key: str, **kwargs: Any) -> str:
    text = MAIN_TRANSLATIONS.get(ui_lang(), MAIN_TRANSLATIONS["en"]).get(key, key)
    return text.format(**kwargs) if kwargs else text


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
}


def field_label(column: Any) -> str:
    text = safe_str(column)
    if ui_lang() == "zh":
        return FIELD_LABELS_ZH.get(text, text)
    return text


def value_label(value: Any) -> Any:
    text = safe_str(value)
    if ui_lang() != "zh" or not text:
        return value
    if ";" in text:
        return "; ".join(VALUE_LABELS_ZH.get(part.strip(), part.strip()) for part in text.split(";"))
    return VALUE_LABELS_ZH.get(text, value)


def display_frame(df: pd.DataFrame, public: bool = False) -> pd.DataFrame:
    if df.empty:
        return df
    display = public_display_frame(df) if public else df.copy()
    if ui_lang() == "zh":
        for col in display.columns:
            if display[col].dtype == "object":
                display[col] = display[col].map(value_label)
            elif display[col].dtype == "bool":
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
    return mt("session_only")


def truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def demo_auth_required() -> bool:
    return bool(configured_value("CONSENSUS_SCOPE_DEMO_PASSWORD")) or truthy(configured_value("CONSENSUS_SCOPE_AUTH_ENABLED"))


def render_demo_auth_gate() -> bool:
    expected = configured_value("CONSENSUS_SCOPE_DEMO_PASSWORD")
    if not expected and not demo_auth_required():
        return True
    if st.session_state.get("demo_authenticated"):
        return True

    st.markdown(f'<div class="section-title">{mt("demo_access")}</div>', unsafe_allow_html=True)
    st.info(mt("demo_access_info"))
    if not expected:
        st.error(mt("auth_not_configured"))
        return False
    with st.form("demo_auth_form"):
        entered = st.text_input(mt("demo_password"), type="password")
        submitted = st.form_submit_button(mt("unlock_demo"), use_container_width=True)
    if submitted:
        if hmac.compare_digest(entered, expected):
            st.session_state["demo_authenticated"] = True
            st.rerun()
        else:
            st.error(mt("invalid_password"))
    return False


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
        .stApp { background: #f6f7fb; }
        .block-container { max-width: 1520px; padding-top: 1.15rem; padding-bottom: 2rem; }
        section[data-testid="stSidebar"] { background: #101827; }
        section[data-testid="stSidebar"] * { color: #f8fafc; }
        .topbar {
            background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px;
            padding: 18px 22px; margin-bottom: 16px;
        }
        .title { font-size: 1.65rem; font-weight: 760; color: #111827; margin-bottom: 2px; }
        .subtitle { color: #64748b; font-size: 0.95rem; }
        .section-title { font-size: 1.08rem; font-weight: 720; color: #111827; margin: 8px 0 8px; }
        .hint { color: #667085; font-size: 0.88rem; }
        .metric-panel {
            background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px;
            padding: 16px; min-height: 108px;
        }
        .metric-label { color: #667085; font-size: 0.82rem; font-weight: 650; }
        .metric-value { color: #111827; font-size: 1.75rem; font-weight: 780; margin-top: 6px; }
        .winner-box {
            border-left: 4px solid #16a34a; background: #f0fdf4; color: #14532d;
            padding: 12px 14px; border-radius: 8px; margin: 8px 0 12px;
        }
        .risk-low { color: #166534; font-weight: 760; }
        .risk-medium { color: #b45309; font-weight: 760; }
        .risk-high { color: #b91c1c; font-weight: 760; }
        textarea, input { border-radius: 8px !important; }
        .stButton > button, .stDownloadButton > button { border-radius: 8px !important; font-weight: 700 !important; }
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
        "main_reviewer_id": "demo_teacher",
        "audit_selection": None,
        "api_mode": "Mode A",
        "demo_authenticated": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def metric_panel(label: str, value: str, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-panel">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="hint">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def topbar() -> None:
    st.markdown(
        f"""
        <div class="topbar">
          <div class="title">ConsensusScope</div>
          <div class="subtitle">{mt("topbar_subtitle")}</div>
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
    configs: List[LiveModelConfig] = []
    defaults = default_live_model_configs()
    for provider in selected:
        if provider not in defaults:
            continue
        item = user_inputs.get(provider, {})
        if api_mode == "Mode A":
            api_key = provider_env_value(provider, "api_key")
            base_url = provider_env_value(provider, "base_url") or defaults[provider]["base_url"]
            model = provider_env_value(provider, "model") or defaults[provider]["model"]
        else:
            api_key = item.get("api_key", "")
            base_url = item.get("base_url", "") or defaults[provider]["base_url"]
            model = item.get("model", "") or defaults[provider]["model"]
        configs.append(LiveModelConfig(provider=provider, api_key=api_key, base_url=base_url, model=model, enabled=True))
    return configs


def build_fixed_judge_config(api_mode: str, provider: str, user_inputs: Dict[str, Dict[str, str]], enabled: bool) -> Optional[LiveModelConfig]:
    if not enabled:
        return None
    defaults = default_live_model_configs()
    if provider not in defaults:
        return None
    item = user_inputs.get(provider, {})
    if api_mode == "Mode A":
        api_key = provider_env_value(provider, "api_key")
        base_url = provider_env_value(provider, "base_url") or defaults[provider]["base_url"]
        model = provider_env_value(provider, "model") or defaults[provider]["model"]
    else:
        api_key = item.get("api_key", "")
        base_url = item.get("base_url", "") or defaults[provider]["base_url"]
        model = item.get("model", "") or defaults[provider]["model"]
    return LiveModelConfig(provider=provider, api_key=api_key, base_url=base_url, model=model, enabled=True)


def render_api_sidebar() -> tuple[str, List[str], Dict[str, Dict[str, str]], bool, str]:
    load_dotenv(ROOT / ".env")
    st.sidebar.markdown(f"#### {mt('api_configuration')}")
    api_mode = st.sidebar.radio(
        mt("api_mode"),
        ["Mode A", "Mode B"],
        format_func=lambda x: mt("mode_a") if x == "Mode A" else mt("mode_b"),
        index=0 if st.session_state["api_mode"] == "Mode A" else 1,
    )
    st.session_state["api_mode"] = api_mode
    st.sidebar.caption(mt("api_caption"))
    default_selected = [p for p in ["deepseek", "qwen", "glm", "kimi"] if p in ANSWER_PROVIDERS]
    selected = st.sidebar.multiselect(mt("answer_models"), ANSWER_PROVIDERS, default=default_selected)
    st.sidebar.caption(mt("answer_models_help"))
    fixed_enabled = st.sidebar.checkbox(mt("enable_fixed_judge"), value=False)
    fixed_provider = st.sidebar.selectbox(mt("fixed_judge_model"), selected or default_selected or ANSWER_PROVIDERS, index=0)

    user_inputs: Dict[str, Dict[str, str]] = {}
    defaults = default_live_model_configs()
    with st.sidebar.expander(mt("provider_settings"), expanded=(api_mode == "Mode B")):
        st.caption(mt("provider_settings_help"))
        for provider in ANSWER_PROVIDERS:
            st.markdown(f"**{provider}**")
            api_key = ""
            if api_mode == "Mode B":
                api_key = st.text_input(mt("api_key_label", provider=provider), type="password", key=f"{provider}_api_key")
            model = st.text_input(mt("model_label", provider=provider), value=defaults.get(provider, {}).get("model", ""), key=f"{provider}_model")
            base_url = st.text_input(mt("base_url_label", provider=provider), value=defaults.get(provider, {}).get("base_url", ""), key=f"{provider}_base_url")
            user_inputs[provider] = {"api_key": api_key, "model": model, "base_url": base_url}
    return api_mode, selected, user_inputs, fixed_enabled, fixed_provider


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
    return demo_esl_result()


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
    decisions = st.session_state.get("teacher_decisions", {})
    if not queue.empty:
        queue["teacher_action"] = queue["feedback_item_id"].map(lambda item_id: decisions.get(item_id, "pending"))
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


def page_single_essay_review() -> None:
    st.markdown(f'<div class="section-title">{mt("single_title")}</div>', unsafe_allow_html=True)
    st.caption(mt("single_caption"))
    demo_essays = read_table(str(DATA_PATHS["esl_essays"]))
    demo_choice = "Blank workspace"
    if not demo_essays.empty:
        blank = mt("blank_workspace")
        demo_choice = st.selectbox(mt("load_demo"), [blank] + demo_essays["essay_id"].astype(str).tolist())
    selected = first_record(demo_essays[demo_essays["essay_id"].astype(str) == demo_choice]) if demo_choice != mt("blank_workspace") and not demo_essays.empty else {}
    default_prompt = safe_str(selected.get("assignment_prompt")) or "Write an ESL essay responding clearly to the assignment prompt."
    default_level = safe_str(selected.get("student_level")) or "upper-intermediate"
    default_essay = safe_str(selected.get("essay_text_anonymized"))

    left, right = st.columns([0.92, 1.08], gap="large")
    with left:
        essay_id = st.text_input(mt("essay_id"), value=safe_str(selected.get("essay_id")) or "USER-ESSAY-001")
        assignment = st.text_area(mt("assignment_prompt"), value=default_prompt, height=92)
        level = st.selectbox(mt("student_level"), ["intermediate", "upper-intermediate", "advanced", "not specified"], index=1)
        essay_text = st.text_area(mt("student_draft"), value=default_essay, height=260)
        include_stress = st.checkbox(mt("include_stress"), value=True)
        run = st.button(mt("generate_route"), use_container_width=True, type="primary")
    with right:
        st.markdown(f"### {mt('what_window_does')}")
        st.write(mt("single_explain"))
        st.info(mt("single_info"))

    if run:
        if not essay_text.strip():
            st.error(mt("paste_essay_error"))
        else:
            st.session_state["esl_single_result"] = review_esl_essay(
                essay_text=essay_text,
                essay_id=essay_id,
                assignment_prompt=assignment,
                student_level=level,
                include_stress_tests=include_stress,
            )
            st.session_state["esl_batch_result"] = None

    result = st.session_state.get("esl_single_result")
    if not result:
        return
    st.markdown(f'<div class="section-title">{mt("review_result")}</div>', unsafe_allow_html=True)
    display_esl_summary(result["summary"])
    display_esl_feedback_table(result["merged"], mt("routed_feedback"))
    queue = teacher_queue_frame(result)
    display_esl_feedback_table(queue, mt("teacher_queue_table"))
    st.download_button(
        mt("download_single_report"),
        data=result["report"].encode("utf-8"),
        file_name=f"{result.get('essay_id', 'essay')}_review_report.md",
        mime="text/markdown",
        use_container_width=True,
    )


def page_batch_review() -> None:
    st.markdown(f'<div class="section-title">{mt("batch_title")}</div>', unsafe_allow_html=True)
    st.caption(mt("batch_caption"))
    uploaded = st.file_uploader(
        mt("upload_csv"),
        type=["csv"],
        help=mt("upload_help"),
    )
    include_stress = st.checkbox(mt("include_stress_batch"), value=True)
    if uploaded is not None:
        essays = pd.read_csv(uploaded).fillna("")
    else:
        essays = read_table(str(DATA_PATHS["esl_essays"]))
        st.info(mt("using_demo_data"))
    if essays.empty:
        st.warning(mt("no_essays"))
        return
    st.dataframe(display_frame(essays.head(10)), use_container_width=True, hide_index=True)
    if st.button(mt("run_batch"), use_container_width=True, type="primary"):
        if "essay_text" not in essays.columns and "essay_text_anonymized" not in essays.columns:
            st.error(mt("csv_required"))
        else:
            st.session_state["esl_batch_result"] = review_esl_batch(essays, include_stress_tests=include_stress)
            st.session_state["esl_single_result"] = None
    result = st.session_state.get("esl_batch_result")
    if not result:
        return
    st.markdown(f'<div class="section-title">{mt("batch_result")}</div>', unsafe_allow_html=True)
    st.dataframe(display_frame(result["summary"]), use_container_width=True, hide_index=True)
    display_esl_feedback_table(result["merged"], mt("all_routed_feedback"))
    st.download_button(
        mt("download_batch_feedback"),
        data=result["merged"].to_csv(index=False, encoding="utf-8-sig"),
        file_name="batch_esl_routed_feedback.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.download_button(
        mt("download_batch_summary"),
        data=result["summary"].to_csv(index=False, encoding="utf-8-sig"),
        file_name="batch_esl_summary.csv",
        mime="text/csv",
        use_container_width=True,
    )


def page_ai_feedback_comparison() -> None:
    st.markdown(f'<div class="section-title">{mt("compare_title")}</div>', unsafe_allow_html=True)
    result = current_esl_result()
    if not result:
        st.info(mt("run_first"))
        return
    st.caption(mt("compare_caption"))
    comparison = result.get("comparison", pd.DataFrame())
    if comparison.empty:
        st.info(mt("no_comparison"))
        return
    st.dataframe(display_frame(comparison), use_container_width=True, hide_index=True)
    counts = comparison["consensus_state"].value_counts().rename_axis("consensus_state").reset_index(name="items")
    st.markdown(f"### {mt('consensus_states')}")
    st.dataframe(display_frame(counts), use_container_width=True, hide_index=True)


def page_teacher_queue() -> None:
    st.markdown(f'<div class="section-title">{mt("queue_title")}</div>', unsafe_allow_html=True)
    result = current_esl_result()
    queue = teacher_queue_frame(result)
    if queue.empty:
        st.success(mt("queue_empty"))
        return
    st.caption(mt("queue_caption"))
    st.caption(f"{mt('storage_backend')}: {storage_backend_name()}")
    reviewer_id = st.text_input(
        mt("reviewer_id"),
        value=safe_str(st.session_state.get("main_reviewer_id")) or "demo_teacher",
        help=mt("reviewer_id_help"),
    )
    st.session_state["main_reviewer_id"] = reviewer_id
    risk_filter = st.multiselect(mt("risk_level"), ["high", "medium", "low"], default=["high", "medium"], format_func=value_label)
    issue_options = sorted(queue["issue_type_predicted"].fillna("").astype(str).unique().tolist())
    issue_filter = st.multiselect(mt("issue_type"), issue_options, default=issue_options, format_func=value_label)
    filtered = queue[queue["risk_level"].isin(risk_filter) & queue["issue_type_predicted"].isin(issue_filter)].copy()
    for _, row in filtered.iterrows():
        item_id = safe_str(row.get("feedback_item_id"))
        priority = safe_str(row.get("review_priority")) or "normal"
        score = safe_str(row.get("risk_score")) or "n/a"
        with st.expander(
            f"{item_id} · {value_label(row.get('risk_level'))} · {mt('priority')}={value_label(priority)} · score={score}",
            expanded=row.get("risk_level") == "high",
        ):
            st.write(f"**{mt('target_span')}:** {row.get('target_span')}")
            st.write(f"**{mt('ai_suggestion')}:** {row.get('ai_suggestion')}")
            st.write(f"**{mt('routing_reason')}:** {row.get('risk_reasons')}")
            if safe_str(row.get("safety_graph_summary")) or safe_str(row.get("safety_graph_path")):
                st.markdown(f"**{mt('feedback_safety_graph')}**")
                if safe_str(row.get("safety_graph_summary")):
                    st.write(row.get("safety_graph_summary"))
                if safe_str(row.get("safety_graph_path")):
                    st.code(row.get("safety_graph_path"), language="text")
                if safe_str(row.get("safety_graph_active_dimensions")):
                    st.write(f"**{mt('active_safety_dimensions')}:** {value_label(row.get('safety_graph_active_dimensions'))}")
            if safe_str(row.get("review_explanation")):
                st.write(f"**{mt('ai_review_explanation')}:** {row.get('review_explanation')}")
            cols = st.columns(3)
            cols[0].metric(mt("review_confidence"), safe_str(row.get("review_confidence")) or "n/a")
            cols[1].metric(mt("evidence_signal"), safe_str(row.get("evidence_signal")) or "none")
            cols[2].metric(mt("priority"), priority)
            action = st.radio(
                mt("teacher_action"),
                ["pending", "accept", "edit", "reject", "needs_more_evidence"],
                format_func=value_label,
                horizontal=True,
                key=f"teacher_action_{item_id}",
                index=["pending", "accept", "edit", "reject", "needs_more_evidence"].index(
                    st.session_state.get("teacher_decisions", {}).get(item_id, "pending")
                ),
            )
            st.session_state["teacher_decisions"][item_id] = action
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
    st.markdown(f'<div class="section-title">{mt("reports_title")}</div>', unsafe_allow_html=True)
    result = current_esl_result()
    if not result:
        st.info(mt("run_first"))
        return
    merged = result.get("merged", pd.DataFrame())
    summary = result.get("summary", {})
    if isinstance(summary, pd.DataFrame):
        st.dataframe(display_frame(summary), use_container_width=True, hide_index=True)
    else:
        display_esl_summary(summary)
    display_esl_feedback_table(merged, mt("report_table"))
    report_text = result.get("report", "")
    if not report_text and not merged.empty:
        report_text = (
            "ConsensusScope 批量报告\n\n请下载路由反馈 CSV 查看逐条反馈细节。"
            if ui_lang() == "zh"
            else "ConsensusScope batch report\n\nDownload the routed feedback CSV for item-level details."
        )
    st.text_area(mt("report_preview"), value=report_text, height=260)
    st.download_button(
        mt("download_routed_csv"),
        data=merged.to_csv(index=False, encoding="utf-8-sig") if not merged.empty else "",
        file_name="esl_routed_feedback.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.download_button(
        mt("download_report_md"),
        data=report_text.encode("utf-8"),
        file_name="esl_feedback_review_report.md",
        mime="text/markdown",
        use_container_width=True,
    )


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
    st.markdown(f'<div class="section-title">{mt("settings_title")}</div>', unsafe_allow_html=True)
    st.info(mt("settings_info"))
    with st.expander(mt("api_diagnostics"), expanded=False):
        st.write(f"{mt('api_mode')}: {api_mode}")
        st.write(f"{mt('answer_models')}: {', '.join(selected) if selected else mt('none')}")
        st.write(f"{mt('enable_fixed_judge')}: {fixed_enabled}; {mt('fixed_judge_model')}: {fixed_provider or mt('not_available')}")
        st.write(f"{mt('storage_backend')}: {storage_backend_name()}")
    with st.expander(mt("legacy_feedback"), expanded=False):
        render_literary_feedback_mode(api_mode, selected, user_inputs)
    with st.expander(mt("aux_qa_comparison"), expanded=False):
        page_comparison(metrics_df)
    with st.expander(mt("aux_qa_risk"), expanded=False):
        page_risk_dashboard(risk_df, effectiveness_df)
    with st.expander(mt("aux_qa_case"), expanded=False):
        page_case_explorer(error_df, samples_df, outputs_df)


def page_home(samples_df: pd.DataFrame, outputs_df: pd.DataFrame, metrics_df: pd.DataFrame, risk_df: pd.DataFrame) -> None:
    st.markdown(f'<div class="section-title">{mt("home_title")}</div>', unsafe_allow_html=True)
    esl_essays = read_table(str(DATA_PATHS["esl_essays"]))
    esl_feedback = read_table(str(DATA_PATHS["esl_feedback"]))
    esl_routing = read_table(str(DATA_PATHS["esl_routing"]))
    esl_stress = read_table(str(DATA_PATHS["esl_stress"]))
    metrics_df = visible_method_metrics(metrics_df)
    teacher_review = int((esl_routing.get("recommended_action", pd.Series(dtype=str)) == "teacher_review").sum()) if not esl_routing.empty else 0
    auto_accept = int((esl_routing.get("recommended_action", pd.Series(dtype=str)) == "auto_accept").sum()) if not esl_routing.empty else 0
    high_risk = int((esl_routing.get("risk_level", pd.Series(dtype=str)) == "high").sum()) if not esl_routing.empty else 0
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_panel(mt("synthetic_essays"), str(len(esl_essays)), mt("esl_demo"))
    with c2:
        metric_panel(mt("feedback_items"), str(len(esl_feedback)), mt("unified_schema"))
    with c3:
        metric_panel(mt("auto_accepted"), str(auto_accept), mt("low_risk_edits"))
    with c4:
        metric_panel(mt("teacher_review"), str(teacher_review), mt("high_risk_items", count=high_risk))
    st.code(mt("workflow_line"), language="text")
    st.markdown(
        mt("main_claim")
    )
    st.info(mt("safety_graph_mechanism"))
    st.info(mt("prototype_info"))
    if not esl_routing.empty:
        st.markdown(f'<div class="section-title">{mt("routing_snapshot")}</div>', unsafe_allow_html=True)
        snapshot = {
            "synthetic_essays": len(esl_essays),
            "feedback_items": len(esl_feedback),
            "ai_review_stress_cases": len(esl_stress),
            "auto_accept": auto_accept,
            "teacher_review": teacher_review,
            "high_risk": high_risk,
            "mean_risk_score": round(float(pd.to_numeric(esl_routing.get("risk_score", pd.Series(dtype=float)), errors="coerce").fillna(0).mean()), 3),
        }
        st.dataframe(display_frame(pd.DataFrame([snapshot])), use_container_width=True, hide_index=True)
    if not metrics_df.empty:
        st.markdown(f'<div class="section-title">{mt("aux_qa_metrics")}</div>', unsafe_allow_html=True)
        st.dataframe(display_frame(metrics_df), use_container_width=True, hide_index=True)
    if not risk_df.empty and "risk_labels" in risk_df:
        labels: List[str] = []
        for item in risk_df["risk_labels"].fillna(""):
            labels.extend([x.strip() for x in str(item).split(";") if x.strip()])
        if labels:
            st.bar_chart(pd.Series(labels).value_counts())


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
    st.set_page_config(page_title="ConsensusScope", layout="wide")
    load_dotenv(ROOT / ".env")
    inject_styles()
    ensure_state()
    language_choice = st.sidebar.selectbox(
        mt("language_label"),
        ["English", "中文"],
        index=0 if ui_lang() == "en" else 1,
        key="main_language_selector",
    )
    st.session_state["ui_language"] = "zh" if language_choice == "中文" else "en"
    topbar()
    if not render_demo_auth_gate():
        return

    samples_df = read_table(str(DATA_PATHS["samples"]))
    outputs_df = load_outputs()
    majority_df = read_table(str(DATA_PATHS["majority"]))
    dynamic_df = read_table(str(DATA_PATHS["dynamic"]))
    fixed_df = read_table(str(DATA_PATHS["fixed_judge"]))
    risk_df = read_table(str(DATA_PATHS["risk_labels"]))
    metrics_df = read_table(str(DATA_PATHS["method_metrics"]))
    effectiveness_df = read_table(str(DATA_PATHS["risk_effectiveness"]))
    error_df = read_table(str(DATA_PATHS["error_cases"]))

    st.sidebar.markdown("### ConsensusScope")
    if demo_auth_required() and st.session_state.get("demo_authenticated"):
        if st.sidebar.button(mt("lock_demo"), use_container_width=True):
            st.session_state["demo_authenticated"] = False
            st.rerun()
    page_keys = [
        "page_home",
        "page_single",
        "page_batch",
        "page_compare",
        "page_queue",
        "page_eval",
        "page_reports",
        "page_settings",
        "page_design",
    ]
    page_labels = [mt(key) for key in page_keys]
    page_label = st.sidebar.radio(
        mt("navigation"),
        page_labels,
        label_visibility="collapsed",
    )
    page_key = page_keys[page_labels.index(page_label)]
    st.sidebar.divider()
    if page_key == "page_design":
        api_mode, selected, user_inputs, fixed_enabled, fixed_provider = "Mode A", [], {}, False, ""
    else:
        api_mode, selected, user_inputs, fixed_enabled, fixed_provider = render_api_sidebar()
        st.sidebar.caption(f"{mt('storage_backend')}: {storage_backend_name()}")

    if page_key == "page_home":
        page_home(samples_df, outputs_df, metrics_df, risk_df)
    elif page_key == "page_single":
        page_single_essay_review()
    elif page_key == "page_batch":
        page_batch_review()
    elif page_key == "page_compare":
        page_ai_feedback_comparison()
    elif page_key == "page_queue":
        page_teacher_queue()
    elif page_key == "page_eval":
        page_effectiveness_evaluation()
    elif page_key == "page_reports":
        page_reports()
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
    else:
        page_design_reference()


if __name__ == "__main__":
    main()
