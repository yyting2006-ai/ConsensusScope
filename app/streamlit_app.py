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
        "topbar_subtitle": "Teacher-in-the-loop review routing for safe AI feedback on ESL writing",
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
        "single_caption": "Paste one ESL writing draft, generate local AI-style feedback candidates, route them, and inspect what needs teacher review.",
        "load_demo": "Load a demo essay or start blank",
        "blank_workspace": "Blank workspace",
        "essay_id": "Essay ID",
        "assignment_prompt": "Assignment prompt",
        "student_level": "Student level",
        "student_draft": "Student essay draft",
        "include_stress": "Include unsafe stress-test suggestions for demo",
        "generate_route": "Generate and route AI feedback",
        "what_window_does": "What this window does",
        "single_explain": "It simulates multiple AI feedback reviewers in a no-API mode, normalizes every suggestion into the same schema, then routes low-risk local edits separately from items that need teacher review.",
        "single_info": "For public deployment, this page can run without API keys. Live LLM providers can later write into the same feedback schema.",
        "paste_essay_error": "Please paste an essay draft before running review.",
        "review_result": "Review Result",
        "routed_feedback": "Routed feedback",
        "teacher_queue_table": "Teacher-review queue",
        "download_single_report": "Download single essay report.md",
        "batch_title": "Page 3 · Batch Review",
        "batch_caption": "Upload or use a CSV of ESL essays, then generate feedback candidates and teacher-review routing for every row.",
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
        "compare_caption": "This page compares AI feedback candidates by target span, issue type, reviewers, routed risk, and consensus state.",
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
        "review_confidence": "Review confidence",
        "evidence_signal": "Evidence signal",
        "priority": "Priority",
        "teacher_action": "Teacher action",
        "download_queue": "Download teacher queue.csv",
        "eval_title": "Page 6 · Effectiveness Evaluation",
        "eval_caption": "This page evaluates implementation behavior on synthetic expectation labels and AI-review stress cases. It is a sanity check for routing logic, not evidence from real classroom use.",
        "combined_items": "Combined items",
        "action_accuracy": "Action accuracy",
        "risk_accuracy": "Risk accuracy",
        "high_risk_recall": "High-risk recall",
        "auto_precision": "Auto precision",
        "evaluation_sets": "Evaluation sets",
        "packaged_demo": "Packaged synthetic demo",
        "stress_cases": "AI-review stress cases",
        "validity_assessment": "Validity assessment",
        "validity_text": "Current evidence supports a demo-level claim: the system can operationalize a teacher-review workflow and reliably route synthetic high-risk feedback to review. It does not yet support a classroom effectiveness claim because no real teacher annotations, student outcomes, or time-on-task measurements have been collected.",
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
        "main_claim": "Main demo claim: teacher-in-the-loop review routing for safe AI-generated ESL writing feedback. Teachers can run single-essay or batch feedback review, inspect AI feedback comparisons, and route risky feedback into a teacher queue before student release.",
        "prototype_info": "The current product UI reference is ui_prototype/index.html. Streamlit retains technical and auxiliary modules for inspection, but earlier modules are not the main EMNLP 2026 demo claim.",
        "routing_snapshot": "ESL Writing Feedback Routing Snapshot",
        "design_title": "Page 9 · Design Reference",
        "design_caption": "Designer-facing preview for the current ESL writing teacher-review workspace. The standalone source is ui_prototype/index.html.",
        "design_text": "Use this page when sharing the live site with a UI/UX designer. The intended design direction is a teacher workflow for reviewing ESL writing feedback, with model diagnostics moved into Settings / Diagnostics.",
        "download_design_brief": "Download Chinese design brief",
        "download_html_mockup": "Download HTML mockup",
        "design_missing": "Design reference mockup is not available in this package.",
    },
    "zh": {
        "language_label": "Language / 语言",
        "topbar_subtitle": "面向 ESL 写作 AI 反馈的教师在环安全复核路由",
        "demo_access": "演示访问",
        "demo_access_info": "该在线演示已启用密码保护，以避免无意调用 API。",
        "demo_password": "演示密码",
        "unlock_demo": "解锁演示",
        "invalid_password": "密码错误。",
        "api_configuration": "API 配置",
        "api_mode": "API 模式",
        "mode_a": "Mode A · 内置 API key，适合现场演示",
        "mode_b": "Mode B · 用户自带 API key，适合公开部署",
        "api_caption": "Mode A 使用本地 .env 或部署 Secrets。Mode B 仅在当前请求中使用用户输入的 key。API key 不应写入论文或硬编码进代码。",
        "answer_models": "回答生成模型",
        "answer_models_help": "每个 provider 都需要对应 API key。如果你只有一个 key，只选择对应 provider。",
        "enable_fixed_judge": "Live 模式启用 Fixed Judge",
        "fixed_judge_model": "固定裁判模型",
        "provider_settings": "Provider 设置",
        "provider_settings_help": "只填写 provider base URL；应用会自动追加 /chat/completions。",
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
        "single_caption": "粘贴一篇 ESL 作文，生成本地 AI 风格反馈候选，完成路由，并查看哪些反馈需要教师复核。",
        "load_demo": "加载 demo 作文或新建空白工作区",
        "blank_workspace": "空白工作区",
        "essay_id": "作文 ID",
        "assignment_prompt": "作文题目",
        "student_level": "学生水平",
        "student_draft": "学生作文草稿",
        "include_stress": "包含不安全 stress-test 建议用于演示",
        "generate_route": "生成并路由 AI 反馈",
        "what_window_does": "该窗口的作用",
        "single_explain": "它在 no-API 模式下模拟多个 AI feedback reviewer，将每条建议规范到同一 schema，再把低风险局部语言修改和需要教师复核的项目分开。",
        "single_info": "公开部署时，本页无需 API key 即可运行。真实 LLM provider 后续也可以写入同一反馈 schema。",
        "paste_essay_error": "请先粘贴作文草稿。",
        "review_result": "评审结果",
        "routed_feedback": "路由后的反馈",
        "teacher_queue_table": "教师复核队列",
        "download_single_report": "下载单篇作文报告.md",
        "batch_title": "第 3 页 · 批量评审",
        "batch_caption": "上传或使用 ESL 作文 CSV，为每篇作文生成反馈候选并进行教师复核路由。",
        "upload_csv": "上传 CSV",
        "upload_help": "期望字段：essay_id, assignment_prompt, student_level, essay_text 或 essay_text_anonymized。",
        "include_stress_batch": "批量演示包含不安全 stress-test 建议",
        "using_demo_data": "正在使用内置合成 ESL 写作 demo 数据。上传 CSV 可处理你自己的作文。",
        "no_essays": "暂无可用作文。",
        "run_batch": "运行批量 AI 反馈评审",
        "csv_required": "CSV 必须包含 essay_text 或 essay_text_anonymized。",
        "batch_result": "批量结果",
        "all_routed_feedback": "全部路由反馈",
        "download_batch_feedback": "下载批量路由反馈.csv",
        "download_batch_summary": "下载批量摘要.csv",
        "compare_title": "第 4 页 · AI 反馈对比",
        "run_first": "请先运行单篇作文评审或批量评审，或使用内置 demo 数据。",
        "compare_caption": "本页按目标片段、问题类型、reviewer、路由风险和一致性状态对比 AI 反馈候选。",
        "no_comparison": "暂无对比结果。",
        "consensus_states": "一致性状态",
        "queue_title": "第 5 页 · 教师复核队列",
        "queue_empty": "当前没有需要教师复核的项目。",
        "queue_caption": "教师可以接受、编辑、拒绝或暂缓反馈。决策会保存在本地 Streamlit session 中。",
        "risk_level": "风险等级",
        "issue_type": "问题类型",
        "target_span": "目标片段",
        "ai_suggestion": "AI 建议",
        "routing_reason": "路由原因",
        "ai_review_explanation": "AI 评审解释",
        "review_confidence": "评审置信度",
        "evidence_signal": "证据信号",
        "priority": "优先级",
        "teacher_action": "教师动作",
        "download_queue": "下载教师队列.csv",
        "eval_title": "第 6 页 · 有效性评估",
        "eval_caption": "本页在合成期望标签和 AI-review stress cases 上评估实现行为。这是路由逻辑 sanity check，不是真实课堂有效性证据。",
        "combined_items": "合并项目数",
        "action_accuracy": "动作准确率",
        "risk_accuracy": "风险准确率",
        "high_risk_recall": "高风险召回",
        "auto_precision": "自动接受精确率",
        "evaluation_sets": "评估集合",
        "packaged_demo": "内置合成 demo",
        "stress_cases": "AI 评审压力测试",
        "validity_assessment": "有效性说明",
        "validity_text": "当前证据支持 demo 级主张：系统可以实现教师复核工作流，并按设计将合成高风险反馈送入复核。但它还不能证明真实课堂有效性，因为尚未收集真实教师标注、学生结果或耗时数据。",
        "reports_title": "第 7 页 · 报告导出",
        "report_table": "报告表格",
        "report_preview": "报告预览",
        "download_routed_csv": "下载路由反馈.csv",
        "download_report_md": "下载报告.md",
        "settings_title": "第 8 页 · 设置 / 诊断",
        "settings_info": "当前主线教师工作流位于第 2-7 页。本页保留 API 设置和旧辅助诊断。",
        "api_diagnostics": "API 诊断",
        "legacy_feedback": "旧反馈技术 demo",
        "aux_qa_comparison": "辅助 QA 对比",
        "aux_qa_risk": "辅助 QA 风险面板",
        "aux_qa_case": "辅助 QA 案例浏览",
        "home_title": "第 1 页 · 首页 / 系统概览",
        "synthetic_essays": "合成作文",
        "esl_demo": "ESL 写作 demo",
        "unified_schema": "统一 schema",
        "low_risk_edits": "低风险局部修改",
        "high_risk_items": "{count} 个高风险项目",
        "main_claim": "主 demo 主张：面向 AI 生成 ESL 写作反馈的教师在环复核路由。教师可以进行单篇或批量反馈评审，查看 AI 反馈对比，并在学生看到反馈前将风险反馈送入教师队列。",
        "prototype_info": "当前产品 UI 参考为 ui_prototype/index.html。Streamlit 保留技术和辅助模块供检查，但早期模块不是当前 EMNLP 2026 demo 主张。",
        "routing_snapshot": "ESL 写作反馈路由快照",
        "design_title": "第 9 页 · 设计参考",
        "design_caption": "面向设计师的当前 ESL 写作教师复核工作台预览。独立源文件是 ui_prototype/index.html。",
        "design_text": "将 live site 分享给 UI/UX 设计师时可使用本页。目标设计方向是 ESL 写作反馈教师复核工作流，模型诊断移至设置 / 诊断中。",
        "download_design_brief": "下载中文设计说明",
        "download_html_mockup": "下载 HTML 原型",
        "design_missing": "该包中没有设计参考 mockup。",
    },
}


def ui_lang() -> str:
    return safe_str(st.session_state.get("ui_language") or "en")


def mt(key: str, **kwargs: Any) -> str:
    text = MAIN_TRANSLATIONS.get(ui_lang(), MAIN_TRANSLATIONS["en"]).get(key, key)
    return text.format(**kwargs) if kwargs else text



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
        return "No answer"
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
        st.error("Demo authentication is enabled, but CONSENSUS_SCOPE_DEMO_PASSWORD is not configured.")
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
        st.warning(f"Failed to read {p}: {exc}")
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
        st.warning(f"Failed to read {p}: {exc}")
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
        return "None"
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
        "final_answer": final_answer or "Not available",
        "correct_offline": correct,
        "risk_or_confidence": safe_str(rec.get("risk_level", "")) or safe_str(score) or "Not available",
        "reasoning": english_note(rec.get("decision_note", rec.get("decision_reason", ""))) or "Not available",
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
                api_key = st.text_input(f"{provider} API Key", type="password", key=f"{provider}_api_key")
            model = st.text_input(f"{provider} model", value=defaults.get(provider, {}).get("model", ""), key=f"{provider}_model")
            base_url = st.text_input(f"{provider} base URL", value=defaults.get(provider, {}).get("base_url", ""), key=f"{provider}_base_url")
            user_inputs[provider] = {"api_key": api_key, "model": model, "base_url": base_url}
    return api_mode, selected, user_inputs, fixed_enabled, fixed_provider


def render_model_outputs(outputs: List[Dict[str, Any]]) -> None:
    if not outputs:
        st.info("No model outputs yet.")
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
    st.dataframe(public_display_frame(df[[c for c in cols if c in df.columns]]), use_container_width=True, hide_index=True)
    error_rows = [
        item
        for item in outputs
        if safe_str(item.get("request_error")) or safe_str(item.get("parse_error"))
    ]
    if error_rows:
        with st.expander("Provider request errors", expanded=True):
            for item in error_rows:
                provider = safe_str(item.get("provider")) or "unknown provider"
                model = safe_str(item.get("model")) or "unknown model"
                request_error = safe_str(item.get("request_error"))
                parse_error = safe_str(item.get("parse_error"))
                st.markdown(f"**{provider} · {model}**")
                if request_error:
                    st.code(request_error, language="text")
                if parse_error:
                    st.code(f"Parse error: {parse_error}", language="text")


def render_adjudication_comparison(comparison: Optional[Dict[str, Any]]) -> None:
    if not comparison:
        st.info("No adjudication result yet.")
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
        Recommended method: <b>{safe_str(method_label)}</b> · answer=<b>{safe_str(final.get('final_answer', '')) or 'empty'}</b>
        · risk=<b>{safe_str(final.get('risk_level', ''))}</b>
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
    st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)
    with st.expander("Three adjudication methods", expanded=False):
        for method in methods:
            st.markdown(f"**{method.get('label', method.get('method', ''))}**")
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
        "meaning_preservation_predicted",
        "review_explanation",
    ]
    st.dataframe(df[[c for c in cols if c in df.columns]], use_container_width=True, hide_index=True)


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
    st.dataframe(essays.head(10), use_container_width=True, hide_index=True)
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
    st.dataframe(result["summary"], use_container_width=True, hide_index=True)
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
    st.dataframe(comparison, use_container_width=True, hide_index=True)
    counts = comparison["consensus_state"].value_counts().rename_axis("consensus_state").reset_index(name="items")
    st.markdown(f"### {mt('consensus_states')}")
    st.dataframe(counts, use_container_width=True, hide_index=True)


def page_teacher_queue() -> None:
    st.markdown(f'<div class="section-title">{mt("queue_title")}</div>', unsafe_allow_html=True)
    result = current_esl_result()
    queue = teacher_queue_frame(result)
    if queue.empty:
        st.success(mt("queue_empty"))
        return
    st.caption(mt("queue_caption"))
    risk_filter = st.multiselect(mt("risk_level"), ["high", "medium", "low"], default=["high", "medium"])
    issue_options = sorted(queue["issue_type_predicted"].fillna("").astype(str).unique().tolist())
    issue_filter = st.multiselect(mt("issue_type"), issue_options, default=issue_options)
    filtered = queue[queue["risk_level"].isin(risk_filter) & queue["issue_type_predicted"].isin(issue_filter)].copy()
    for _, row in filtered.iterrows():
        item_id = safe_str(row.get("feedback_item_id"))
        priority = safe_str(row.get("review_priority")) or "normal"
        score = safe_str(row.get("risk_score")) or "n/a"
        with st.expander(
            f"{item_id} · {row.get('risk_level')} · priority={priority} · score={score}",
            expanded=row.get("risk_level") == "high",
        ):
            st.write(f"**{mt('target_span')}:** {row.get('target_span')}")
            st.write(f"**{mt('ai_suggestion')}:** {row.get('ai_suggestion')}")
            st.write(f"**{mt('routing_reason')}:** {row.get('risk_reasons')}")
            if safe_str(row.get("review_explanation")):
                st.write(f"**{mt('ai_review_explanation')}:** {row.get('review_explanation')}")
            cols = st.columns(3)
            cols[0].metric(mt("review_confidence"), safe_str(row.get("review_confidence")) or "n/a")
            cols[1].metric(mt("evidence_signal"), safe_str(row.get("evidence_signal")) or "none")
            cols[2].metric(mt("priority"), priority)
            action = st.radio(
                mt("teacher_action"),
                ["pending", "accept", "edit", "reject", "needs_more_evidence"],
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
        pd.DataFrame(
            [
                {"set": mt("packaged_demo"), **metrics},
                {"set": mt("stress_cases"), **stress_metrics},
                {"set": "combined", **combined_metrics},
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
    merged = demo_routing.merge(expected, on="feedback_item_id", how="left") if not demo_routing.empty and not expected.empty else pd.DataFrame()
    if not merged.empty:
        merged["action_match"] = merged["recommended_action"] == merged["expected_action"]
        merged["risk_match"] = merged["risk_level"] == merged["expected_risk_level"]
        st.markdown(f"### {mt('packaged_demo')}")
        st.dataframe(merged, use_container_width=True, hide_index=True)
    stress_merged = (
        stress_routing.merge(stress_expected, on="feedback_item_id", how="left")
        if not stress_routing.empty and not stress_expected.empty
        else pd.DataFrame()
    )
    if not stress_merged.empty:
        stress_merged["action_match"] = stress_merged["recommended_action"] == stress_merged["expected_action"]
        stress_merged["risk_match"] = stress_merged["risk_level"] == stress_merged["expected_risk_level"]
        st.markdown(f"### {mt('stress_cases')}")
        st.dataframe(stress_merged, use_container_width=True, hide_index=True)
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
        st.dataframe(summary, use_container_width=True, hide_index=True)
    else:
        display_esl_summary(summary)
    display_esl_feedback_table(merged, mt("report_table"))
    report_text = result.get("report", "")
    if not report_text and not merged.empty:
        report_text = "ConsensusScope batch report\n\nDownload the routed feedback CSV for item-level details."
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
        st.write(f"API mode: {api_mode}")
        st.write(f"Selected providers: {', '.join(selected) if selected else 'none'}")
        st.write(f"Fixed judge enabled: {fixed_enabled}; provider: {fixed_provider or 'not selected'}")
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
    st.code(
        "Single Essay Review -> Batch Review -> AI Feedback Comparison -> Teacher Queue -> Effectiveness Evaluation -> Reports",
        language="text",
    )
    st.markdown(
        mt("main_claim")
    )
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
        st.dataframe(pd.DataFrame([snapshot]), use_container_width=True, hide_index=True)
    if not metrics_df.empty:
        st.markdown('<div class="section-title">Auxiliary QA Reliability Metrics</div>', unsafe_allow_html=True)
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)
    if not risk_df.empty and "risk_labels" in risk_df:
        labels: List[str] = []
        for item in risk_df["risk_labels"].fillna(""):
            labels.extend([x.strip() for x in str(item).split(";") if x.strip()])
        if labels:
            st.bar_chart(pd.Series(labels).value_counts())


def render_literary_feedback_mode(api_mode: str, selected: List[str], user_inputs: Dict[str, Dict[str, str]]) -> None:
    kg = load_literary_kg(str(DATA_PATHS["literary_kg"]))
    st.markdown('<div class="section-title">ESL Comparative Literature Essay Feedback</div>', unsafe_allow_html=True)
    st.caption(
        "Teacher-facing workflow: low-risk language edits are separated from factual and interpretive suggestions "
        "that need human review."
    )
    left, right = st.columns([1.05, 0.95], gap="large")
    with left:
        example = st.selectbox("Demo essay", list(EXAMPLE_ESSAYS.keys()))
        default_essay = EXAMPLE_ESSAYS.get(example, DEFAULT_LITERARY_ESSAY)
        essay = st.text_area("Student essay excerpt", value=default_essay, height=230)
        reviewer_source = st.radio(
            "Reviewer source",
            ["No-API deterministic reviewers", "Live API reviewers"],
            horizontal=True,
        )
        run_feedback = st.button("Run Knowledge-Grounded Feedback", use_container_width=True)
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
        c1.metric("Auto-accept", summary["auto_accept"])
        c2.metric("Teacher review", summary["teacher_review"])
        c3, c4 = st.columns(2)
        c3.metric("High risk", summary["high_risk"])
        c4.metric("KG-supported", summary["kg_supported"])
        c5, c6 = st.columns(2)
        c5.metric("KG works", int(kg["work"].nunique()) if not kg.empty and "work" in kg else 0)
        c6.metric("Legacy triples", len(kg))
        if result:
            st.download_button(
                "Download legacy feedback report.md",
                data=result["report"].encode("utf-8"),
                file_name="legacy_feedback_report.md",
                mime="text/markdown",
                use_container_width=True,
            )

    result = st.session_state.get("literary_result")
    if not result:
        st.info("Run the demo to inspect knowledge retrieval, reviewer suggestions, and adjudicated feedback.")
        return

    decisions = result.get("decisions", [])
    queue = review_queue(decisions)
    tabs = st.tabs(["Teacher View", "Knowledge Evidence", "Adjudication Trace", "Raw Suggestions"])
    with tabs[0]:
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown("**Original essay**")
            st.text_area("Original", value=result.get("essay", ""), height=210, disabled=True, label_visibility="collapsed")
        with c2:
            st.markdown("**Auto-accepted preview**")
            st.text_area("Preview", value=result.get("revised", result.get("essay", "")), height=210, disabled=True, label_visibility="collapsed")
        if queue:
            st.markdown('<div class="section-title">Teacher Review Queue</div>', unsafe_allow_html=True)
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
            st.dataframe(queue_df[[c for c in display_cols if c in queue_df.columns]], use_container_width=True, hide_index=True)
        summary_rows = decision_summary_by_type(decisions)
        if summary_rows:
            st.markdown('<div class="section-title">Feedback Distribution</div>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    with tabs[1]:
        kg_rows = result.get("kg_rows", [])
        if kg_rows:
            st.dataframe(pd.DataFrame(kg_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No literary knowledge entry matched this essay excerpt.")

    with tabs[2]:
        decisions_df = pd.DataFrame(decisions)
        st.dataframe(decisions_df, use_container_width=True, hide_index=True)

    with tabs[3]:
        reviewer_results = result.get("reviewer_results", [])
        if reviewer_results:
            st.markdown("**Live reviewer call status**")
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
            st.dataframe(status_df, use_container_width=True, hide_index=True)
        feedback_df = pd.DataFrame(result.get("feedback", []))
        if not feedback_df.empty and "knowledge_evidence" in feedback_df.columns:
            feedback_df = feedback_df.copy()
            feedback_df["knowledge_evidence"] = feedback_df["knowledge_evidence"].map(lambda values: " | ".join(values) if isinstance(values, list) else values)
        st.dataframe(feedback_df, use_container_width=True, hide_index=True)


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
    st.markdown('<div class="section-title">Page 3 · Legacy Feedback Technical Demo</div>', unsafe_allow_html=True)
    result = saved_literary_result()
    if not result:
        st.info("Run Page 2 first or regenerate data/results/literary_feedback_records.json.")
        return
    st.caption(
        "Legacy technical module retained for inspection. It is not the current main ESL writing feedback claim."
    )
    decisions = result.get("decisions", [])
    summary = literary_routing_summary(decisions)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Auto-accept", summary["auto_accept"])
    c2.metric("Teacher review", summary["teacher_review"])
    c3.metric("High risk", summary["high_risk"])
    c4.metric("KG-supported", summary["kg_supported"])

    tabs = st.tabs(["Teacher Review Queue", "Knowledge Evidence", "Adjudication Trace", "Export Preview"])
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
            st.dataframe(queue_df[[c for c in display_cols if c in queue_df.columns]], use_container_width=True, hide_index=True)
        else:
            st.success("No teacher-review items in the selected record.")
    with tabs[1]:
        kg_rows = result.get("kg_rows", [])
        if kg_rows:
            st.dataframe(pd.DataFrame(kg_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No KG evidence is attached to this record.")
    with tabs[2]:
        st.dataframe(pd.DataFrame(decisions), use_container_width=True, hide_index=True)
    with tabs[3]:
        st.download_button(
            "Download legacy feedback report.md",
            data=result.get("report", "").encode("utf-8"),
            file_name="legacy_feedback_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.text_area("Report preview", result.get("report", ""), height=260)


def page_live(api_mode: str, selected: List[str], user_inputs: Dict[str, Dict[str, str]], fixed_enabled: bool, fixed_provider: str) -> None:
    st.markdown('<div class="section-title">Page 2 · Technical Demo / Live Mode</div>', unsafe_allow_html=True)
    mode = st.radio(
        "Mode",
        ["Legacy feedback technical demo", "Auxiliary QA live comparison"],
        horizontal=True,
        label_visibility="collapsed",
    )
    if mode == "Legacy feedback technical demo":
        st.warning(
            "This legacy module is retained for technical inspection. The current product storyline is ESL writing "
            "teacher review routing, shown in ui_prototype/index.html."
        )
        render_literary_feedback_mode(api_mode, selected, user_inputs)
        return

    left, right = st.columns([0.95, 1.05], gap="large")
    with left:
        task_type = st.selectbox(
            "Task type",
            [TASK_FACT_QA, TASK_CLAIM, TASK_CHOICE],
            format_func=lambda x: {"fact_qa": "Open factual QA", "claim_verification": "Claim TRUE/FALSE/UNKNOWN", "multiple_choice": "A/B/C/D multiple choice"}[x],
        )
        question = st.text_area("Question / Claim", height=130)
        choices: Dict[str, str] = {}
        if task_type == TASK_CHOICE:
            c1, c2 = st.columns(2)
            with c1:
                choices["A"] = st.text_input("A")
                choices["B"] = st.text_input("B")
            with c2:
                choices["C"] = st.text_input("C")
                choices["D"] = st.text_input("D")
        temperature = st.slider("Temperature", 0.0, 1.0, 0.2, 0.05)
        if st.button("Run Live Comparison", use_container_width=True):
            configs = build_live_configs(api_mode, selected, user_inputs)
            fixed_cfg = build_fixed_judge_config(api_mode, fixed_provider, user_inputs, fixed_enabled)
            history = load_historical_reliability(str(DATA_PATHS["samples"]), str(DATA_PATHS["outputs_csv"]))
            with st.spinner("Calling answer models and adjudicators..."):
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
    st.markdown('<div class="section-title">Multi-Model Answer Generation · Unified Format</div>', unsafe_allow_html=True)
    render_model_outputs((st.session_state.get("live_result") or {}).get("outputs", []))


def sample_selector(samples_df: pd.DataFrame, risk_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    if samples_df.empty:
        st.error("No samples are available. Generate data/processed/clean_dataset.csv first.")
        return None
    samples = samples_df.copy()
    if "dataset" not in samples.columns:
        samples["dataset"] = "unknown"
    datasets = ["All"] + sorted(samples["dataset"].fillna("unknown").astype(str).unique().tolist())
    selected_dataset = st.selectbox("Dataset", datasets)
    filtered = samples if selected_dataset == "All" else samples[samples["dataset"].astype(str) == selected_dataset]
    if not risk_df.empty and "sample_id" in risk_df.columns:
        only_risk = st.checkbox("Show evaluated samples only", value=True)
        if only_risk:
            ids = set(risk_df["sample_id"].dropna().astype(str))
            filtered = filtered[filtered["id"].astype(str).isin(ids)]
    if filtered.empty:
        st.warning("No samples match the current filters.")
        return None
    sample_ids = filtered["id"].astype(str).tolist()
    default_sample_id = "fever_0366" if "fever_0366" in sample_ids else sample_ids[0]
    sid = st.selectbox("Sample ID", sample_ids, index=sample_ids.index(default_sample_id))
    return filtered[filtered["id"].astype(str) == sid].iloc[0].to_dict()


def page_sample_audit(samples_df: pd.DataFrame, outputs_df: pd.DataFrame, majority_df: pd.DataFrame, dynamic_df: pd.DataFrame, fixed_df: pd.DataFrame, risk_df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Page 3 · Sample Audit Mode</div>', unsafe_allow_html=True)
    sample = sample_selector(samples_df, risk_df)
    if not sample:
        return
    sid = safe_str(sample.get("id", ""))
    st.markdown("**Question / Claim**")
    st.write(safe_str(sample.get("question", "")))
    st.markdown("**Options**")
    st.text(parse_options(sample.get("options", "")))
    c1, c2, c3 = st.columns(3)
    c1.metric("Dataset", safe_str(sample.get("dataset", "")))
    c2.metric("Gold answer", safe_str(sample.get("gold_answer", "")) or safe_str(sample.get("gold_label", "")))
    c3.metric("Task", safe_str(sample.get("task_type", "")))

    outputs = dataframe_for_sample(outputs_df, "sample_id", sid)
    st.markdown('<div class="section-title">Model Outputs</div>', unsafe_allow_html=True)
    if outputs.empty:
        st.warning("This sample has no model outputs.")
    else:
        display = outputs.copy()
        if "correct" not in display.columns:
            display["correct"] = display["answer"].map(lambda ans: is_correct(ans, sample.get("gold_answer", ""), sample.get("gold_label", "")))
        st.dataframe(public_display_frame(display), use_container_width=True, hide_index=True)

    rows = []
    for label, df in [
        ("Majority Vote", majority_df),
        ("Fixed Judge", fixed_df),
        ("Dynamic Rule-Based Judge", dynamic_df),
    ]:
        rec = first_record(dataframe_for_sample(df, "sample_id", sid))
        rows.append(decision_row(label, rec, sample))
    st.markdown('<div class="section-title">Adjudication Layer</div>', unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    risk = first_record(dataframe_for_sample(risk_df, "sample_id", sid))
    st.markdown('<div class="section-title">Risk Labels</div>', unsafe_allow_html=True)
    risk_text = safe_str(risk.get("risk_labels", ""))
    st.write(risk_text or "None")


def page_comparison(metrics_df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Page 4 · Adjudication Comparison</div>', unsafe_allow_html=True)
    st.caption(
        "For ESL feedback, the main routing decision is auto-accept versus teacher review. "
        "The table below is retained for the auxiliary QA reliability module."
    )
    live = st.session_state.get("live_result")
    render_adjudication_comparison((live or {}).get("comparison"))
    st.markdown("### Auxiliary QA Offline Metrics")
    metrics_df = visible_method_metrics(metrics_df)
    if metrics_df.empty:
        st.info("Missing data/results/method_metrics.csv.")
        return
    st.dataframe(metrics_df, use_container_width=True, hide_index=True)
    if {"method", "accuracy"}.issubset(metrics_df.columns):
        st.bar_chart(metrics_df.set_index("method")["accuracy"])


def page_risk_dashboard(risk_df: pd.DataFrame, effectiveness_df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Page 5 · Risk Dashboard</div>', unsafe_allow_html=True)
    esl_routing = read_table(str(DATA_PATHS["esl_routing"]))
    if not esl_routing.empty:
        st.markdown("### ESL Writing Feedback Routing Risk")
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
        st.dataframe(pd.DataFrame([summary]), use_container_width=True, hide_index=True)
        st.caption("These are synthetic review-routing counts, not automatic essay-scoring results or classroom validation.")
    if risk_df.empty:
        st.info("Missing auxiliary QA risk_labels.csv.")
        return
    st.markdown("### Auxiliary QA Offline Diagnostic Labels")
    st.caption("These labels use gold answers and are not deploy-time knowledge.")
    labels: List[str] = []
    for item in risk_df.get("risk_labels", pd.Series(dtype=str)).fillna(""):
        labels.extend([x.strip() for x in str(item).split(";") if x.strip()])
    c1, c2, c3 = st.columns(3)
    c1.metric("Risk samples", len(risk_df))
    c2.metric("False consensus", labels.count("false_consensus"))
    c3.metric("Minority correct", labels.count("minority_correct"))
    if labels:
        st.bar_chart(pd.Series(labels).value_counts())
    if not effectiveness_df.empty:
        st.markdown("### Risk Level Effectiveness")
        st.dataframe(effectiveness_df, use_container_width=True, hide_index=True)


def page_model_reliability(outputs_df: pd.DataFrame, samples_df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Page 6 · Model Reliability Dashboard</div>', unsafe_allow_html=True)
    if outputs_df.empty or samples_df.empty:
        st.info("Missing model outputs or sample file.")
        return
    reliability = load_historical_reliability(str(DATA_PATHS["samples"]), str(DATA_PATHS["outputs_csv"]))
    rows = [{"model": k, "historical_accuracy_smoothed": v} for k, v in reliability.items()]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    if rows:
        st.bar_chart(pd.DataFrame(rows).set_index("model")["historical_accuracy_smoothed"])
    agg = outputs_df.groupby("model", as_index=False).agg(
        avg_confidence=("confidence", "mean"),
        calls=("answer", "size"),
    )
    st.markdown("### Generation Statistics")
    st.dataframe(agg, use_container_width=True, hide_index=True)


def page_case_explorer(error_df: pd.DataFrame, samples_df: pd.DataFrame, outputs_df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Page 7 · Auxiliary QA Case Explorer</div>', unsafe_allow_html=True)
    st.caption("Auxiliary reliability cases from saved QA traces. They are not the main ESL feedback demo claim.")
    if error_df.empty:
        st.info("Missing error_cases.csv.")
        return
    note_filter = st.multiselect("Case tags", sorted({x for s in error_df["notes"].fillna("") for x in str(s).split(";") if x}), default=[])
    df = error_df.copy()
    if note_filter:
        df = df[df["notes"].fillna("").apply(lambda s: any(tag in str(s).split(";") for tag in note_filter))]
    st.dataframe(public_display_frame(df), use_container_width=True, hide_index=True)
    if not df.empty:
        sid = st.selectbox("Inspect case", df["sample_id"].astype(str).tolist())
        sample = first_record(dataframe_for_sample(samples_df, "id", sid))
        st.write(sample.get("question", ""))
        st.dataframe(public_display_frame(dataframe_for_sample(outputs_df, "sample_id", sid)), use_container_width=True, hide_index=True)


def page_report_export(samples_df: pd.DataFrame, outputs_df: pd.DataFrame, metrics_df: pd.DataFrame, risk_df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Page 8 · Report Export</div>', unsafe_allow_html=True)
    live = st.session_state.get("live_result")
    esl_essays = read_table(str(DATA_PATHS["esl_essays"]))
    esl_feedback = read_table(str(DATA_PATHS["esl_feedback"]))
    esl_routing = read_table(str(DATA_PATHS["esl_routing"]))
    if not esl_routing.empty:
        auto_accept = int((esl_routing["recommended_action"] == "auto_accept").sum()) if "recommended_action" in esl_routing else 0
        teacher_review = int((esl_routing["recommended_action"] == "teacher_review").sum()) if "recommended_action" in esl_routing else 0
        high_risk = int((esl_routing["risk_level"] == "high").sum()) if "risk_level" in esl_routing else 0
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
            "Download esl_writing_routing_report.md",
            data=esl_report.encode("utf-8"),
            file_name="esl_writing_routing_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.download_button(
            "Download esl_writing_routing_results.csv",
            data=esl_routing.to_csv(index=False, encoding="utf-8-sig"),
            file_name="esl_writing_routing_results.csv",
            mime="text/csv",
            use_container_width=True,
        )
    literary = saved_literary_result()
    if literary:
        st.download_button(
            "Download legacy_feedback_report.md",
            data=literary.get("report", "").encode("utf-8"),
            file_name="legacy_feedback_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
    if live:
        st.download_button(
            "Download Live report.md",
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
        "Download system_summary.json",
        data=json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name="system_summary.json",
        mime="application/json",
        use_container_width=True,
    )
    if not metrics_df.empty:
        st.download_button(
            "Download method_metrics.csv",
            data=metrics_df.to_csv(index=False, encoding="utf-8-sig"),
            file_name="method_metrics.csv",
            mime="text/csv",
            use_container_width=True,
        )
    if not risk_df.empty:
        buf = io.StringIO()
        risk_df.to_csv(buf, index=False, encoding="utf-8-sig")
        st.download_button("Download risk_labels.csv", data=buf.getvalue(), file_name="risk_labels.csv", mime="text/csv", use_container_width=True)


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
