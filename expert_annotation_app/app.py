from __future__ import annotations

import io
import json
import os
import sqlite3
import time
from hmac import compare_digest
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import pandas as pd
import streamlit as st


APP_DIR = Path(__file__).resolve().parent
SAMPLE_DIR = APP_DIR / "sample_data"
DATA_DIR = APP_DIR / "annotation_data"
EXPORT_DIR = APP_DIR / "exports"
DB_PATH = DATA_DIR / "expert_annotations.sqlite3"

PAGES = [
    "1. Expert Session",
    "2. Essay Annotation",
    "3. Feedback Annotation",
    "4. Feedback Safety Check",
    "5. Progress",
    "6. Export",
]

ISSUE_TYPES = [
    "grammar",
    "vocabulary",
    "sentence_structure",
    "coherence",
    "organization",
    "task_response",
    "argument_clarity",
    "tone_register",
    "meaning_change",
    "overcorrection",
    "other",
]
FEEDBACK_CORRECTNESS = ["correct", "partially_correct", "incorrect", "unclear"]
TEACHER_ACCEPTABILITY = ["accept", "edit", "reject", "uncertain"]
TEACHER_SAFETY = ["safe_to_show_student", "unsafe_without_revision", "uncertain_needs_review"]
MEANING_PRESERVATION = ["preserves_meaning", "changes_meaning", "unclear"]
YES_NO = ["yes", "no"]
FINAL_ACTIONS = ["accept", "edit", "reject", "uncertain"]
REVIEW_PRIORITY = ["low", "medium", "high"]
RISK_REASONS = [
    "local_language_edit",
    "wrong_correction",
    "meaning_change",
    "overcorrection",
    "introduces_new_argument",
    "too_vague",
    "too_harsh",
    "unsupported_claim",
    "task_mismatch",
    "other",
]
RUBRIC_DIMENSIONS = [
    "task_response",
    "organization",
    "coherence",
    "grammar",
    "vocabulary",
    "tone_register",
    "meaning_preservation",
    "other",
]

ESSAY_SCORE_FIELDS = [
    "task_response_score",
    "organization_score",
    "coherence_score",
    "grammar_accuracy_score",
    "vocabulary_use_score",
    "overall_writing_quality",
]
ESSAY_REQUIRED_FIELDS = ESSAY_SCORE_FIELDS + ["main_problems", "teacher_review_priority", "teacher_comment"]
FEEDBACK_REQUIRED_FIELDS = [
    "issue_type_teacher",
    "feedback_correctness",
    "teacher_acceptability",
    "teacher_safety_label",
    "meaning_preservation",
    "teacher_review_needed",
    "teacher_final_action",
    "teacher_reason",
]
SAFETY_REQUIRED_FIELDS = ["risk_reason_teacher", "rubric_dimension"]

TRANSLATIONS = {
    "en": {
        "language_label": "Language / 语言",
        "english": "English",
        "chinese": "中文",
        "site_title": "ConsensusScope Expert Annotation",
        "site_caption": "Research annotation tool for AI-generated ESL writing feedback. This is separate from the main demo.",
        "password_info": "This research annotation website is password-protected.",
        "site_password": "Site password",
        "enter_site": "Enter annotation website",
        "invalid_password": "Invalid password.",
        "sidebar_title": "Expert Annotation",
        "no_active_session": "No active session",
        "pages": "Pages",
        "session_summary": "Expert: {expert_id}\n\nBatch: {batch_id}\n\nMode: {mode}",
        "page_0": "1. Expert Session",
        "page_1": "2. Essay Annotation",
        "page_2": "3. Feedback Annotation",
        "page_3": "4. Feedback Safety Check",
        "page_4": "5. Progress",
        "page_5": "6. Export",
        "select_placeholder": "Select...",
        "session_required": "Create or select an expert session before annotation.",
        "expert_session": "Expert Session",
        "expert_session_desc": "Create or select an annotation session. Gold labels are stored locally in SQLite.",
        "existing_sessions": "Existing sessions",
        "load_selected_session": "Load selected session",
        "session_loaded": "Session loaded.",
        "new_current_session": "New or Current Session",
        "expert_id": "Expert ID",
        "batch_id": "Batch ID",
        "annotation_mode": "Annotation mode",
        "blind_mode": "Blind Annotation Mode",
        "assisted_mode": "Assisted Review Mode",
        "create_select_session": "Create / Select Session",
        "session_id_required": "expert_id and batch_id are required.",
        "session_ready": "Session is ready.",
        "data_loaded": "Data Loaded",
        "blind_active": "Blind Annotation Mode is active. System risk, recommended action, model agreement, model name, and ConsensusScope decisions are hidden.",
        "assisted_warning": "Assisted Review Mode can show optional system signals in an expander. Use Blind Annotation Mode for unbiased gold-label collection.",
        "essay_annotation": "Essay Annotation",
        "no_essays": "No essays are available in sample_data/essays.csv.",
        "essay_progress": "Essay {current} of {total}",
        "student_essay": "Student Essay",
        "assignment_prompt": "Assignment prompt",
        "anonymized_essay_text": "Anonymized essay text",
        "essay_text": "Essay text",
        "essay_level_scores": "Essay-level Scores",
        "task_response_score": "Task response score",
        "organization_score": "Organization score",
        "coherence_score": "Coherence score",
        "grammar_accuracy_score": "Grammar accuracy score",
        "vocabulary_use_score": "Vocabulary use score",
        "overall_writing_quality": "Overall writing quality",
        "main_problems": "Main problems",
        "teacher_review_priority": "Teacher review priority",
        "teacher_comment": "Teacher comment",
        "save_essay_annotation": "Save essay annotation",
        "essay_saved": "Essay annotation saved for {item_id}.",
        "feedback_annotation": "Feedback Annotation",
        "no_feedback": "No feedback items are available in sample_data/feedback_items.csv.",
        "feedback_progress": "Feedback item {current} of {total}",
        "feedback_item": "Feedback Item",
        "blind_caption": "Blind mode hides model/source fields and ConsensusScope routing outputs.",
        "feedback_item_id": "Feedback item ID",
        "essay_id": "Essay ID",
        "target_span": "Target span",
        "surrounding_context": "Surrounding context",
        "ai_feedback": "AI-generated feedback shown for teacher judgment",
        "ai_rationale": "AI rationale",
        "no_rationale": "No rationale provided.",
        "assisted_signals": "Assisted review signals",
        "model_source": "Model source",
        "predicted_issue_type": "Predicted issue type",
        "not_provided": "not provided",
        "no_routing": "No routing result is available for this item.",
        "teacher_decision": "Teacher Decision",
        "issue_type_teacher": "Issue type teacher",
        "feedback_correctness": "Feedback correctness",
        "teacher_acceptability": "Teacher acceptability",
        "teacher_safety_label": "Teacher safety label",
        "meaning_preservation": "Meaning preservation",
        "teacher_review_needed": "Teacher review needed",
        "teacher_final_action": "Teacher final action",
        "teacher_corrected_feedback": "Teacher corrected feedback (required if final action = edit)",
        "teacher_reason": "Teacher reason",
        "save_feedback_annotation": "Save feedback annotation",
        "feedback_saved": "Feedback annotation saved for {item_id}.",
        "feedback_safety_check": "Feedback Safety Check",
        "safety_progress": "Safety item {current} of {total}",
        "safety_label": "Safety Label",
        "risk_reason_teacher": "Risk reason teacher",
        "rubric_dimension": "Rubric dimension",
        "evidence_note": "Evidence note (optional)",
        "save_safety_check": "Save safety check",
        "safety_saved": "Safety check saved for {item_id}.",
        "progress": "Progress",
        "no_items": "No annotation items are available.",
        "total_units": "Total annotation units",
        "complete": "Complete",
        "remaining": "Remaining",
        "completion_by_type": "Completion by type",
        "missing_fields": "Missing fields",
        "all_complete": "All required fields are complete for the current expert_id and batch_id.",
        "export": "Export",
        "export_scope": "Exports are scoped to the current expert_id and batch_id.",
        "write_exports": "Write all export files to local exports/ folder",
        "export_written": "Export files written to {path}",
        "previous": "Previous",
        "next": "Next",
        "first_incomplete": "First incomplete",
        "jump_to_item": "Jump to item",
        "missing_required": "Missing required fields: {fields}",
    },
    "zh": {
        "language_label": "Language / 语言",
        "english": "English",
        "chinese": "中文",
        "site_title": "ConsensusScope 专家标注",
        "site_caption": "用于 AI 生成 ESL 写作反馈的研究标注工具。该网站与主 demo 分离。",
        "password_info": "该研究标注网站已启用密码保护。",
        "site_password": "网站密码",
        "enter_site": "进入标注网站",
        "invalid_password": "密码错误。",
        "sidebar_title": "专家标注",
        "no_active_session": "尚未选择会话",
        "pages": "页面",
        "session_summary": "专家：{expert_id}\n\n批次：{batch_id}\n\n模式：{mode}",
        "page_0": "1. 专家会话",
        "page_1": "2. 作文标注",
        "page_2": "3. 反馈标注",
        "page_3": "4. 反馈安全检查",
        "page_4": "5. 进度",
        "page_5": "6. 导出",
        "select_placeholder": "请选择...",
        "session_required": "请先创建或选择专家标注会话。",
        "expert_session": "专家会话",
        "expert_session_desc": "创建或选择一个标注会话。Gold labels 会保存在本地 SQLite 数据库中。",
        "existing_sessions": "已有会话",
        "load_selected_session": "加载选中会话",
        "session_loaded": "会话已加载。",
        "new_current_session": "新建或当前会话",
        "expert_id": "专家 ID",
        "batch_id": "批次 ID",
        "annotation_mode": "标注模式",
        "blind_mode": "盲标模式",
        "assisted_mode": "辅助复核模式",
        "create_select_session": "创建 / 选择会话",
        "session_id_required": "expert_id 和 batch_id 为必填项。",
        "session_ready": "会话已准备好。",
        "data_loaded": "已加载数据",
        "blind_active": "当前为盲标模式。系统风险等级、推荐动作、模型一致性、模型名称和 ConsensusScope 决策均已隐藏。",
        "assisted_warning": "辅助复核模式会在折叠区显示可选系统信号。收集无偏 gold labels 时请使用盲标模式。",
        "essay_annotation": "作文标注",
        "no_essays": "sample_data/essays.csv 中没有可用作文。",
        "essay_progress": "作文 {current} / {total}",
        "student_essay": "学生作文",
        "assignment_prompt": "作文题目",
        "anonymized_essay_text": "匿名作文文本",
        "essay_text": "作文文本",
        "essay_level_scores": "作文层面评分",
        "task_response_score": "任务回应评分",
        "organization_score": "组织结构评分",
        "coherence_score": "连贯性评分",
        "grammar_accuracy_score": "语法准确性评分",
        "vocabulary_use_score": "词汇使用评分",
        "overall_writing_quality": "整体写作质量",
        "main_problems": "主要问题",
        "teacher_review_priority": "教师复核优先级",
        "teacher_comment": "教师备注",
        "save_essay_annotation": "保存作文标注",
        "essay_saved": "已保存作文标注：{item_id}。",
        "feedback_annotation": "反馈标注",
        "no_feedback": "sample_data/feedback_items.csv 中没有可用反馈项。",
        "feedback_progress": "反馈项 {current} / {total}",
        "feedback_item": "反馈项",
        "blind_caption": "盲标模式会隐藏模型/来源字段和 ConsensusScope 路由结果。",
        "feedback_item_id": "反馈项 ID",
        "essay_id": "作文 ID",
        "target_span": "目标片段",
        "surrounding_context": "上下文",
        "ai_feedback": "供教师判断的 AI 生成反馈",
        "ai_rationale": "AI 理由",
        "no_rationale": "未提供理由。",
        "assisted_signals": "辅助复核信号",
        "model_source": "模型来源",
        "predicted_issue_type": "预测问题类型",
        "not_provided": "未提供",
        "no_routing": "该反馈项没有可用路由结果。",
        "teacher_decision": "教师决策",
        "issue_type_teacher": "教师判断的问题类型",
        "feedback_correctness": "反馈正确性",
        "teacher_acceptability": "教师可接受性",
        "teacher_safety_label": "教师安全标签",
        "meaning_preservation": "是否保留原意",
        "teacher_review_needed": "是否需要教师复核",
        "teacher_final_action": "教师最终动作",
        "teacher_corrected_feedback": "教师修改后的反馈（若最终动作为 edit，则必填）",
        "teacher_reason": "教师理由",
        "save_feedback_annotation": "保存反馈标注",
        "feedback_saved": "已保存反馈标注：{item_id}。",
        "feedback_safety_check": "反馈安全检查",
        "safety_progress": "安全检查项 {current} / {total}",
        "safety_label": "安全标签",
        "risk_reason_teacher": "教师判断的风险原因",
        "rubric_dimension": "对应评分维度",
        "evidence_note": "证据备注（可选）",
        "save_safety_check": "保存安全检查",
        "safety_saved": "已保存安全检查：{item_id}。",
        "progress": "进度",
        "no_items": "没有可用标注项。",
        "total_units": "标注单元总数",
        "complete": "已完成",
        "remaining": "未完成",
        "completion_by_type": "按类型统计完成情况",
        "missing_fields": "缺失字段",
        "all_complete": "当前 expert_id 和 batch_id 下所有必填字段均已完成。",
        "export": "导出",
        "export_scope": "导出范围限定为当前 expert_id 和 batch_id。",
        "write_exports": "将所有导出文件写入本地 exports/ 文件夹",
        "export_written": "导出文件已写入 {path}",
        "previous": "上一条",
        "next": "下一条",
        "first_incomplete": "第一个未完成",
        "jump_to_item": "跳转到第几条",
        "missing_required": "缺失必填字段：{fields}",
    }
}

OPTION_LABELS_ZH = {
    "Blind Annotation Mode": "盲标模式",
    "Assisted Review Mode": "辅助复核模式",
    "grammar": "语法",
    "vocabulary": "词汇",
    "sentence_structure": "句子结构",
    "coherence": "连贯性",
    "organization": "组织结构",
    "task_response": "任务回应",
    "argument_clarity": "论证清晰度",
    "tone_register": "语气/语域",
    "meaning_change": "改变原意",
    "overcorrection": "过度修改",
    "other": "其他",
    "correct": "正确",
    "partially_correct": "部分正确",
    "incorrect": "错误",
    "unclear": "不确定",
    "accept": "接受",
    "edit": "修改",
    "reject": "拒绝",
    "uncertain": "不确定",
    "safe_to_show_student": "可直接给学生看",
    "unsafe_without_revision": "未修改前不安全",
    "uncertain_needs_review": "不确定，需要复核",
    "preserves_meaning": "保留原意",
    "changes_meaning": "改变原意",
    "yes": "是",
    "no": "否",
    "low": "低",
    "medium": "中",
    "high": "高",
    "local_language_edit": "局部语言修改",
    "wrong_correction": "错误修改",
    "introduces_new_argument": "引入新论点",
    "too_vague": "过于笼统",
    "too_harsh": "语气过 harsh",
    "unsupported_claim": "无依据内容",
    "task_mismatch": "偏离任务",
    "meaning_preservation": "原意保留",
}


def lang() -> str:
    return safe_str(st.session_state.get("ui_language") or "en")


def t(key: str, **kwargs: Any) -> str:
    text = TRANSLATIONS.get(lang(), {}).get(key, key)
    return text.format(**kwargs) if kwargs else text


def option_label(value: Any) -> str:
    text = safe_str(value)
    if text == "":
        return t("select_placeholder")
    if lang() == "zh":
        return OPTION_LABELS_ZH.get(text, text)
    return text


def page_labels() -> List[str]:
    return [t(f"page_{idx}") for idx in range(len(PAGES))]


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def configured_secret(key: str) -> str:
    value = os.getenv(key, "")
    if value:
        return value
    try:
        secret_value = st.secrets.get(key, "")
    except Exception:
        secret_value = ""
    return safe_str(secret_value)


def render_access_gate() -> bool:
    expected = configured_secret("EXPERT_ANNOTATION_PASSWORD")
    if not expected:
        return True
    if st.session_state.get("expert_annotation_authenticated"):
        return True

    st.title(t("site_title"))
    st.info(t("password_info"))
    with st.form("expert_annotation_access_form"):
        entered = st.text_input(t("site_password"), type="password")
        submitted = st.form_submit_button(t("enter_site"), type="primary", use_container_width=True)
    if submitted:
        if compare_digest(entered, expected):
            st.session_state["expert_annotation_authenticated"] = True
            st.rerun()
        else:
            st.error(t("invalid_password"))
    return False


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def connect() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=MEMORY")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS expert_sessions (
                session_id TEXT PRIMARY KEY,
                expert_id TEXT NOT NULL,
                batch_id TEXT NOT NULL,
                annotation_mode TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                duration_seconds REAL NOT NULL DEFAULT 0,
                UNIQUE(expert_id, batch_id, annotation_mode)
            );

            CREATE TABLE IF NOT EXISTS essay_annotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expert_id TEXT NOT NULL,
                batch_id TEXT NOT NULL,
                essay_id TEXT NOT NULL,
                task_response_score INTEGER,
                organization_score INTEGER,
                coherence_score INTEGER,
                grammar_accuracy_score INTEGER,
                vocabulary_use_score INTEGER,
                overall_writing_quality INTEGER,
                main_problems TEXT,
                teacher_review_priority TEXT,
                teacher_comment TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                duration_seconds REAL NOT NULL DEFAULT 0,
                UNIQUE(expert_id, batch_id, essay_id)
            );

            CREATE TABLE IF NOT EXISTS feedback_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expert_id TEXT NOT NULL,
                batch_id TEXT NOT NULL,
                feedback_item_id TEXT NOT NULL,
                essay_id TEXT NOT NULL,
                issue_type_teacher TEXT,
                feedback_correctness TEXT,
                teacher_acceptability TEXT,
                teacher_safety_label TEXT,
                meaning_preservation TEXT,
                teacher_review_needed TEXT,
                teacher_final_action TEXT,
                teacher_corrected_feedback TEXT,
                teacher_reason TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                duration_seconds REAL NOT NULL DEFAULT 0,
                UNIQUE(expert_id, batch_id, feedback_item_id)
            );

            CREATE TABLE IF NOT EXISTS feedback_safety_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expert_id TEXT NOT NULL,
                batch_id TEXT NOT NULL,
                feedback_item_id TEXT NOT NULL,
                essay_id TEXT NOT NULL,
                risk_reason_teacher TEXT,
                rubric_dimension TEXT,
                evidence_note TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                duration_seconds REAL NOT NULL DEFAULT 0,
                UNIQUE(expert_id, batch_id, feedback_item_id)
            );

            CREATE TABLE IF NOT EXISTS annotation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expert_id TEXT NOT NULL,
                batch_id TEXT NOT NULL,
                item_type TEXT NOT NULL,
                item_id TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                duration_seconds REAL NOT NULL DEFAULT 0
            );
            """
        )


@st.cache_data(show_spinner=False)
def load_csv(name: str) -> pd.DataFrame:
    path = SAMPLE_DIR / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path).fillna("")


def load_data() -> Dict[str, pd.DataFrame]:
    return {
        "essays": load_csv("essays.csv"),
        "feedback": load_csv("feedback_items.csv"),
        "routing": load_csv("routing_results.csv"),
    }


def require_columns(df: pd.DataFrame, required: Sequence[str], name: str) -> List[str]:
    missing = [col for col in required if col not in df.columns]
    if missing:
        st.error(f"{name} is missing required columns: {', '.join(missing)}")
    return missing


def get_session() -> Dict[str, str]:
    return {
        "expert_id": safe_str(st.session_state.get("expert_id")),
        "batch_id": safe_str(st.session_state.get("batch_id")),
        "annotation_mode": safe_str(st.session_state.get("annotation_mode") or "Blind Annotation Mode"),
    }


def session_ready() -> bool:
    session = get_session()
    return bool(session["expert_id"] and session["batch_id"])


def require_session() -> bool:
    if session_ready():
        return True
    st.warning(t("session_required"))
    return False


def session_id_for(expert_id: str, batch_id: str, mode: str) -> str:
    mode_slug = "blind" if mode.startswith("Blind") else "assisted"
    return f"{expert_id}__{batch_id}__{mode_slug}"


def create_or_select_session(expert_id: str, batch_id: str, mode: str) -> None:
    current_time = now_iso()
    sid = session_id_for(expert_id, batch_id, mode)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO expert_sessions (
                session_id, expert_id, batch_id, annotation_mode, created_at, updated_at, duration_seconds
            )
            VALUES (?, ?, ?, ?, ?, ?, 0)
            ON CONFLICT(expert_id, batch_id, annotation_mode)
            DO UPDATE SET updated_at=excluded.updated_at
            """,
            (sid, expert_id, batch_id, mode, current_time, current_time),
        )
    st.session_state["expert_id"] = expert_id
    st.session_state["batch_id"] = batch_id
    st.session_state["annotation_mode"] = mode
    st.session_state["session_timer_started_at"] = time.time()


def touch_session() -> None:
    if not session_ready():
        return
    session = get_session()
    started = float(st.session_state.get("session_timer_started_at", time.time()))
    elapsed = max(0.0, time.time() - started)
    st.session_state["session_timer_started_at"] = time.time()
    sid = session_id_for(session["expert_id"], session["batch_id"], session["annotation_mode"])
    current_time = now_iso()
    with connect() as conn:
        row = conn.execute("SELECT duration_seconds FROM expert_sessions WHERE session_id=?", (sid,)).fetchone()
        previous = float(row["duration_seconds"] or 0) if row else 0.0
        conn.execute(
            "UPDATE expert_sessions SET updated_at=?, duration_seconds=? WHERE session_id=?",
            (current_time, previous + elapsed, sid),
        )


def read_sessions() -> pd.DataFrame:
    with connect() as conn:
        return pd.read_sql_query(
            "SELECT * FROM expert_sessions ORDER BY updated_at DESC, created_at DESC",
            conn,
        )


def read_annotation_table(table: str) -> pd.DataFrame:
    session = get_session()
    if not session_ready():
        return pd.DataFrame()
    with connect() as conn:
        return pd.read_sql_query(
            f"SELECT * FROM {table} WHERE expert_id=? AND batch_id=? ORDER BY updated_at DESC",
            conn,
            params=(session["expert_id"], session["batch_id"]),
        )


def fetch_one(table: str, key_column: str, key_value: str) -> Dict[str, Any]:
    session = get_session()
    if not session_ready():
        return {}
    with connect() as conn:
        row = conn.execute(
            f"SELECT * FROM {table} WHERE expert_id=? AND batch_id=? AND {key_column}=?",
            (session["expert_id"], session["batch_id"], key_value),
        ).fetchone()
    return dict(row) if row else {}


def add_log(item_type: str, item_id: str, action: str, details: Mapping[str, Any] | None, duration: float) -> None:
    session = get_session()
    current_time = now_iso()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO annotation_logs (
                expert_id, batch_id, item_type, item_id, action, details,
                created_at, updated_at, duration_seconds
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["expert_id"],
                session["batch_id"],
                item_type,
                item_id,
                action,
                json.dumps(details or {}, ensure_ascii=False),
                current_time,
                current_time,
                duration,
            ),
        )


def timer_key(item_type: str) -> str:
    return f"{item_type}_timer_item"


def timer_started_key(item_type: str) -> str:
    return f"{item_type}_timer_started_at"


def ensure_item_timer(item_type: str, item_id: str) -> None:
    key = timer_key(item_type)
    started_key = timer_started_key(item_type)
    if st.session_state.get(key) != item_id:
        st.session_state[key] = item_id
        st.session_state[started_key] = time.time()


def elapsed_for_item(item_type: str) -> float:
    started = float(st.session_state.get(timer_started_key(item_type), time.time()))
    return max(0.0, time.time() - started)


def reset_item_timer(item_type: str) -> None:
    st.session_state[timer_started_key(item_type)] = time.time()


def as_records(df: pd.DataFrame, key: str) -> Dict[str, Dict[str, Any]]:
    if df.empty or key not in df:
        return {}
    return {safe_str(row[key]): row.to_dict() for _, row in df.iterrows()}


def missing_text(value: Any) -> bool:
    return not safe_str(value)


def missing_score(value: Any) -> bool:
    if value in (None, ""):
        return True
    try:
        parsed = int(value)
    except Exception:
        return True
    return parsed < 1 or parsed > 5


def essay_missing_fields(row: Mapping[str, Any] | None) -> List[str]:
    if not row:
        return ESSAY_REQUIRED_FIELDS.copy()
    missing: List[str] = []
    for field in ESSAY_SCORE_FIELDS:
        if missing_score(row.get(field)):
            missing.append(field)
    for field in ["main_problems", "teacher_review_priority", "teacher_comment"]:
        if missing_text(row.get(field)):
            missing.append(field)
    return missing


def feedback_missing_fields(row: Mapping[str, Any] | None) -> List[str]:
    if not row:
        return FEEDBACK_REQUIRED_FIELDS.copy()
    missing = [field for field in FEEDBACK_REQUIRED_FIELDS if missing_text(row.get(field))]
    if safe_str(row.get("teacher_final_action")) == "edit" and missing_text(row.get("teacher_corrected_feedback")):
        missing.append("teacher_corrected_feedback")
    return missing


def safety_missing_fields(row: Mapping[str, Any] | None) -> List[str]:
    if not row:
        return SAFETY_REQUIRED_FIELDS.copy()
    return [field for field in SAFETY_REQUIRED_FIELDS if missing_text(row.get(field))]


def first_incomplete_index(items: pd.DataFrame, id_col: str, records: Mapping[str, Mapping[str, Any]], checker) -> int:
    if items.empty:
        return 0
    for idx, row in items.reset_index(drop=True).iterrows():
        item_id = safe_str(row.get(id_col))
        if checker(records.get(item_id)):
            return int(idx)
    return 0


def selectbox_required(label: str, options: Sequence[str], value: Any, key: str) -> str:
    values = [""] + list(options)
    value_str = safe_str(value)
    index = values.index(value_str) if value_str in values else 0
    return st.selectbox(label, values, index=index, key=key, format_func=option_label)


def score_required(label: str, value: Any, key: str) -> int | None:
    values: List[Any] = [""] + [1, 2, 3, 4, 5]
    try:
        parsed = int(value)
    except Exception:
        parsed = ""
    index = values.index(parsed) if parsed in values else 0
    selected = st.selectbox(label, values, index=index, key=key, format_func=lambda x: t("select_placeholder") if x == "" else str(x))
    return None if selected == "" else int(selected)


def text_default(row: Mapping[str, Any], field: str) -> str:
    return safe_str(row.get(field))


def nav_buttons(item_type: str, total: int, index_key: str, first_incomplete: int) -> None:
    col1, col2, col3, col4 = st.columns([1, 1, 1.5, 2])
    with col1:
        if st.button(t("previous"), key=f"{item_type}_prev", disabled=total <= 1):
            st.session_state[index_key] = max(0, int(st.session_state.get(index_key, 0)) - 1)
            st.rerun()
    with col2:
        if st.button(t("next"), key=f"{item_type}_next", disabled=total <= 1):
            st.session_state[index_key] = min(total - 1, int(st.session_state.get(index_key, 0)) + 1)
            st.rerun()
    with col3:
        if st.button(t("first_incomplete"), key=f"{item_type}_first_incomplete", disabled=total == 0):
            st.session_state[index_key] = first_incomplete
            st.rerun()
    with col4:
        if total:
            selected = st.number_input(
                t("jump_to_item"),
                min_value=1,
                max_value=total,
                value=int(st.session_state.get(index_key, 0)) + 1,
                step=1,
                key=f"{item_type}_jump",
            )
            st.session_state[index_key] = int(selected) - 1


def render_essay_card(essay: Mapping[str, Any]) -> None:
    st.markdown(f"### {t('student_essay')}")
    meta = {
        t("essay_id"): essay.get("essay_id"),
        "Genre" if lang() == "en" else "文体": essay.get("essay_genre"),
        "Student level" if lang() == "en" else "学生水平": essay.get("student_level"),
        "Word count" if lang() == "en" else "词数": essay.get("word_count"),
        "Draft stage" if lang() == "en" else "草稿阶段": essay.get("draft_stage"),
        "PII removed" if lang() == "en" else "已移除个人信息": essay.get("pii_removed"),
    }
    st.dataframe(pd.DataFrame([meta]), use_container_width=True, hide_index=True)
    st.markdown(f"**{t('assignment_prompt')}**")
    st.info(safe_str(essay.get("assignment_prompt")))
    st.markdown(f"**{t('anonymized_essay_text')}**")
    st.text_area(t("essay_text"), value=safe_str(essay.get("essay_text_anonymized")), height=240, disabled=True, label_visibility="collapsed")


def render_feedback_card(
    feedback: Mapping[str, Any],
    essays_by_id: Mapping[str, Mapping[str, Any]],
    routing_by_id: Mapping[str, Mapping[str, Any]],
    mode: str,
) -> None:
    essay_id = safe_str(feedback.get("essay_id"))
    essay = essays_by_id.get(essay_id, {})
    st.markdown(f"### {t('feedback_item')}")
    st.caption(t("blind_caption"))
    cols = st.columns(2)
    cols[0].write(f"**{t('feedback_item_id')}:** {safe_str(feedback.get('feedback_item_id'))}")
    cols[1].write(f"**{t('essay_id')}:** {essay_id}")
    st.markdown(f"**{t('assignment_prompt')}**")
    st.info(safe_str(essay.get("assignment_prompt")))
    st.markdown(f"**{t('target_span')}**")
    st.code(safe_str(feedback.get("target_span")) or "[empty target span]", language="text")
    st.markdown(f"**{t('surrounding_context')}**")
    st.text_area(
        t("surrounding_context"),
        value=safe_str(feedback.get("surrounding_context")),
        height=120,
        disabled=True,
        label_visibility="collapsed",
    )
    st.markdown(f"**{t('ai_feedback')}**")
    st.success(safe_str(feedback.get("ai_suggestion")))
    st.markdown(f"**{t('ai_rationale')}**")
    st.write(safe_str(feedback.get("ai_rationale")) or t("no_rationale"))

    if mode.startswith("Assisted"):
        with st.expander(t("assisted_signals"), expanded=False):
            st.write(f"{t('model_source')}: {safe_str(feedback.get('model_source')) or t('not_provided')}")
            st.write(f"{t('predicted_issue_type')}: {safe_str(feedback.get('issue_type_predicted')) or t('not_provided')}")
            route = routing_by_id.get(safe_str(feedback.get("feedback_item_id")), {})
            if route:
                st.dataframe(pd.DataFrame([route]), use_container_width=True, hide_index=True)
            else:
                st.info(t("no_routing"))


def validate_and_show(missing: Sequence[str]) -> bool:
    if missing:
        st.error(t("missing_required", fields=", ".join(missing)))
        return False
    return True


def save_essay_annotation(essay_id: str, values: Mapping[str, Any], duration: float) -> None:
    session = get_session()
    existing = fetch_one("essay_annotations", "essay_id", essay_id)
    previous = float(existing.get("duration_seconds") or 0.0)
    current_time = now_iso()
    params = {
        **values,
        "expert_id": session["expert_id"],
        "batch_id": session["batch_id"],
        "essay_id": essay_id,
        "created_at": current_time,
        "updated_at": current_time,
        "duration_seconds": previous + duration,
    }
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO essay_annotations (
                expert_id, batch_id, essay_id,
                task_response_score, organization_score, coherence_score,
                grammar_accuracy_score, vocabulary_use_score, overall_writing_quality,
                main_problems, teacher_review_priority, teacher_comment,
                created_at, updated_at, duration_seconds
            )
            VALUES (
                :expert_id, :batch_id, :essay_id,
                :task_response_score, :organization_score, :coherence_score,
                :grammar_accuracy_score, :vocabulary_use_score, :overall_writing_quality,
                :main_problems, :teacher_review_priority, :teacher_comment,
                :created_at, :updated_at, :duration_seconds
            )
            ON CONFLICT(expert_id, batch_id, essay_id)
            DO UPDATE SET
                task_response_score=excluded.task_response_score,
                organization_score=excluded.organization_score,
                coherence_score=excluded.coherence_score,
                grammar_accuracy_score=excluded.grammar_accuracy_score,
                vocabulary_use_score=excluded.vocabulary_use_score,
                overall_writing_quality=excluded.overall_writing_quality,
                main_problems=excluded.main_problems,
                teacher_review_priority=excluded.teacher_review_priority,
                teacher_comment=excluded.teacher_comment,
                updated_at=excluded.updated_at,
                duration_seconds=excluded.duration_seconds
            """,
            params,
        )
    add_log("essay", essay_id, "save_essay_annotation", values, duration)
    touch_session()


def save_feedback_decision(feedback_item_id: str, essay_id: str, values: Mapping[str, Any], duration: float) -> None:
    session = get_session()
    existing = fetch_one("feedback_decisions", "feedback_item_id", feedback_item_id)
    previous = float(existing.get("duration_seconds") or 0.0)
    current_time = now_iso()
    params = {
        **values,
        "expert_id": session["expert_id"],
        "batch_id": session["batch_id"],
        "feedback_item_id": feedback_item_id,
        "essay_id": essay_id,
        "created_at": current_time,
        "updated_at": current_time,
        "duration_seconds": previous + duration,
    }
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO feedback_decisions (
                expert_id, batch_id, feedback_item_id, essay_id,
                issue_type_teacher, feedback_correctness, teacher_acceptability,
                teacher_safety_label, meaning_preservation, teacher_review_needed,
                teacher_final_action, teacher_corrected_feedback, teacher_reason,
                created_at, updated_at, duration_seconds
            )
            VALUES (
                :expert_id, :batch_id, :feedback_item_id, :essay_id,
                :issue_type_teacher, :feedback_correctness, :teacher_acceptability,
                :teacher_safety_label, :meaning_preservation, :teacher_review_needed,
                :teacher_final_action, :teacher_corrected_feedback, :teacher_reason,
                :created_at, :updated_at, :duration_seconds
            )
            ON CONFLICT(expert_id, batch_id, feedback_item_id)
            DO UPDATE SET
                essay_id=excluded.essay_id,
                issue_type_teacher=excluded.issue_type_teacher,
                feedback_correctness=excluded.feedback_correctness,
                teacher_acceptability=excluded.teacher_acceptability,
                teacher_safety_label=excluded.teacher_safety_label,
                meaning_preservation=excluded.meaning_preservation,
                teacher_review_needed=excluded.teacher_review_needed,
                teacher_final_action=excluded.teacher_final_action,
                teacher_corrected_feedback=excluded.teacher_corrected_feedback,
                teacher_reason=excluded.teacher_reason,
                updated_at=excluded.updated_at,
                duration_seconds=excluded.duration_seconds
            """,
            params,
        )
    add_log("feedback", feedback_item_id, "save_feedback_decision", values, duration)
    touch_session()


def save_safety_check(feedback_item_id: str, essay_id: str, values: Mapping[str, Any], duration: float) -> None:
    session = get_session()
    existing = fetch_one("feedback_safety_checks", "feedback_item_id", feedback_item_id)
    previous = float(existing.get("duration_seconds") or 0.0)
    current_time = now_iso()
    params = {
        **values,
        "expert_id": session["expert_id"],
        "batch_id": session["batch_id"],
        "feedback_item_id": feedback_item_id,
        "essay_id": essay_id,
        "created_at": current_time,
        "updated_at": current_time,
        "duration_seconds": previous + duration,
    }
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO feedback_safety_checks (
                expert_id, batch_id, feedback_item_id, essay_id,
                risk_reason_teacher, rubric_dimension, evidence_note,
                created_at, updated_at, duration_seconds
            )
            VALUES (
                :expert_id, :batch_id, :feedback_item_id, :essay_id,
                :risk_reason_teacher, :rubric_dimension, :evidence_note,
                :created_at, :updated_at, :duration_seconds
            )
            ON CONFLICT(expert_id, batch_id, feedback_item_id)
            DO UPDATE SET
                essay_id=excluded.essay_id,
                risk_reason_teacher=excluded.risk_reason_teacher,
                rubric_dimension=excluded.rubric_dimension,
                evidence_note=excluded.evidence_note,
                updated_at=excluded.updated_at,
                duration_seconds=excluded.duration_seconds
            """,
            params,
        )
    add_log("feedback_safety", feedback_item_id, "save_feedback_safety_check", values, duration)
    touch_session()


def page_expert_session(data: Mapping[str, pd.DataFrame]) -> None:
    st.header(t("expert_session"))
    st.write(t("expert_session_desc"))
    sessions = read_sessions()
    if not sessions.empty:
        labels = [
            f"{row.expert_id} | {row.batch_id} | {row.annotation_mode} | updated {row.updated_at}"
            for row in sessions.itertuples()
        ]
        selected_label = st.selectbox(t("existing_sessions"), [""] + labels, format_func=lambda x: t("select_placeholder") if x == "" else x)
        if selected_label:
            selected_index = labels.index(selected_label)
            row = sessions.iloc[selected_index]
            if st.button(t("load_selected_session"), type="primary"):
                create_or_select_session(row["expert_id"], row["batch_id"], row["annotation_mode"])
                st.success(t("session_loaded"))
                st.rerun()

    st.markdown(f"### {t('new_current_session')}")
    session = get_session()
    with st.form("session_form"):
        expert_id = st.text_input(t("expert_id"), value=session["expert_id"], placeholder="e.g., TCH-001")
        batch_id = st.text_input(t("batch_id"), value=session["batch_id"], placeholder="e.g., ESL-BATCH-001")
        mode = st.radio(
            t("annotation_mode"),
            ["Blind Annotation Mode", "Assisted Review Mode"],
            index=0 if session["annotation_mode"].startswith("Blind") else 1,
            horizontal=True,
            format_func=option_label,
        )
        submitted = st.form_submit_button(t("create_select_session"), type="primary", use_container_width=True)
    if submitted:
        if not safe_str(expert_id) or not safe_str(batch_id):
            st.error(t("session_id_required"))
        else:
            create_or_select_session(safe_str(expert_id), safe_str(batch_id), mode)
            add_log("session", session_id_for(safe_str(expert_id), safe_str(batch_id), mode), "select_session", {"mode": mode}, 0.0)
            st.success(t("session_ready"))
            st.rerun()

    st.markdown(f"### {t('data_loaded')}")
    st.dataframe(
        pd.DataFrame(
            [
                {"table": "essays.csv", "rows": len(data["essays"]), "path": str(SAMPLE_DIR / "essays.csv")},
                {"table": "feedback_items.csv", "rows": len(data["feedback"]), "path": str(SAMPLE_DIR / "feedback_items.csv")},
                {"table": "routing_results.csv optional", "rows": len(data["routing"]), "path": str(SAMPLE_DIR / "routing_results.csv")},
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
    if get_session()["annotation_mode"].startswith("Blind"):
        st.info(t("blind_active"))
    else:
        st.warning(t("assisted_warning"))


def page_essay_annotation(data: Mapping[str, pd.DataFrame]) -> None:
    st.header(t("essay_annotation"))
    if not require_session():
        return
    essays = data["essays"].reset_index(drop=True)
    if essays.empty:
        st.error(t("no_essays"))
        return
    annotations = read_annotation_table("essay_annotations")
    records = as_records(annotations, "essay_id")
    total = len(essays)
    st.session_state.setdefault("essay_index", 0)
    st.session_state["essay_index"] = min(max(0, int(st.session_state["essay_index"])), total - 1)
    first_incomplete = first_incomplete_index(essays, "essay_id", records, essay_missing_fields)
    nav_buttons("essay", total, "essay_index", first_incomplete)

    row = essays.iloc[int(st.session_state["essay_index"])].to_dict()
    essay_id = safe_str(row.get("essay_id"))
    ensure_item_timer("essay", essay_id)
    existing = fetch_one("essay_annotations", "essay_id", essay_id)
    st.caption(t("essay_progress", current=int(st.session_state["essay_index"]) + 1, total=total))
    render_essay_card(row)

    with st.form(f"essay_annotation_form_{essay_id}"):
        st.markdown(f"### {t('essay_level_scores')}")
        c1, c2, c3 = st.columns(3)
        values: Dict[str, Any] = {}
        with c1:
            values["task_response_score"] = score_required(t("task_response_score"), existing.get("task_response_score"), f"{essay_id}_task_response")
            values["organization_score"] = score_required(t("organization_score"), existing.get("organization_score"), f"{essay_id}_organization")
        with c2:
            values["coherence_score"] = score_required(t("coherence_score"), existing.get("coherence_score"), f"{essay_id}_coherence")
            values["grammar_accuracy_score"] = score_required(t("grammar_accuracy_score"), existing.get("grammar_accuracy_score"), f"{essay_id}_grammar")
        with c3:
            values["vocabulary_use_score"] = score_required(t("vocabulary_use_score"), existing.get("vocabulary_use_score"), f"{essay_id}_vocabulary")
            values["overall_writing_quality"] = score_required(t("overall_writing_quality"), existing.get("overall_writing_quality"), f"{essay_id}_overall")
        values["main_problems"] = st.text_area(t("main_problems"), value=text_default(existing, "main_problems"), height=90)
        values["teacher_review_priority"] = selectbox_required(
            t("teacher_review_priority"),
            REVIEW_PRIORITY,
            existing.get("teacher_review_priority"),
            f"{essay_id}_priority",
        )
        values["teacher_comment"] = st.text_area(t("teacher_comment"), value=text_default(existing, "teacher_comment"), height=100)
        submitted = st.form_submit_button(t("save_essay_annotation"), type="primary", use_container_width=True)

    if submitted:
        missing = essay_missing_fields(values)
        if validate_and_show(missing):
            duration = elapsed_for_item("essay")
            save_essay_annotation(essay_id, values, duration)
            reset_item_timer("essay")
            st.success(t("essay_saved", item_id=essay_id))


def page_feedback_annotation(data: Mapping[str, pd.DataFrame]) -> None:
    st.header(t("feedback_annotation"))
    if not require_session():
        return
    feedback = data["feedback"].reset_index(drop=True)
    if feedback.empty:
        st.error(t("no_feedback"))
        return
    essays_by_id = as_records(data["essays"], "essay_id")
    routing_by_id = as_records(data["routing"], "feedback_item_id")
    decisions = read_annotation_table("feedback_decisions")
    records = as_records(decisions, "feedback_item_id")
    total = len(feedback)
    st.session_state.setdefault("feedback_index", 0)
    st.session_state["feedback_index"] = min(max(0, int(st.session_state["feedback_index"])), total - 1)
    first_incomplete = first_incomplete_index(feedback, "feedback_item_id", records, feedback_missing_fields)
    nav_buttons("feedback", total, "feedback_index", first_incomplete)

    row = feedback.iloc[int(st.session_state["feedback_index"])].to_dict()
    feedback_item_id = safe_str(row.get("feedback_item_id"))
    essay_id = safe_str(row.get("essay_id"))
    ensure_item_timer("feedback", feedback_item_id)
    existing = fetch_one("feedback_decisions", "feedback_item_id", feedback_item_id)
    st.caption(t("feedback_progress", current=int(st.session_state["feedback_index"]) + 1, total=total))
    render_feedback_card(row, essays_by_id, routing_by_id, get_session()["annotation_mode"])

    with st.form(f"feedback_decision_form_{feedback_item_id}"):
        st.markdown(f"### {t('teacher_decision')}")
        c1, c2 = st.columns(2)
        values: Dict[str, Any] = {}
        with c1:
            values["issue_type_teacher"] = selectbox_required(t("issue_type_teacher"), ISSUE_TYPES, existing.get("issue_type_teacher"), f"{feedback_item_id}_issue")
            values["feedback_correctness"] = selectbox_required(t("feedback_correctness"), FEEDBACK_CORRECTNESS, existing.get("feedback_correctness"), f"{feedback_item_id}_correctness")
            values["teacher_acceptability"] = selectbox_required(t("teacher_acceptability"), TEACHER_ACCEPTABILITY, existing.get("teacher_acceptability"), f"{feedback_item_id}_acceptability")
        with c2:
            values["teacher_safety_label"] = selectbox_required(t("teacher_safety_label"), TEACHER_SAFETY, existing.get("teacher_safety_label"), f"{feedback_item_id}_safety")
            values["meaning_preservation"] = selectbox_required(t("meaning_preservation"), MEANING_PRESERVATION, existing.get("meaning_preservation"), f"{feedback_item_id}_meaning")
            values["teacher_review_needed"] = selectbox_required(t("teacher_review_needed"), YES_NO, existing.get("teacher_review_needed"), f"{feedback_item_id}_review_needed")
        values["teacher_final_action"] = selectbox_required(t("teacher_final_action"), FINAL_ACTIONS, existing.get("teacher_final_action"), f"{feedback_item_id}_final_action")
        values["teacher_corrected_feedback"] = st.text_area(
            t("teacher_corrected_feedback"),
            value=text_default(existing, "teacher_corrected_feedback"),
            height=100,
        )
        values["teacher_reason"] = st.text_area(t("teacher_reason"), value=text_default(existing, "teacher_reason"), height=110)
        submitted = st.form_submit_button(t("save_feedback_annotation"), type="primary", use_container_width=True)

    if submitted:
        missing = feedback_missing_fields(values)
        if validate_and_show(missing):
            duration = elapsed_for_item("feedback")
            save_feedback_decision(feedback_item_id, essay_id, values, duration)
            reset_item_timer("feedback")
            st.success(t("feedback_saved", item_id=feedback_item_id))


def page_feedback_safety(data: Mapping[str, pd.DataFrame]) -> None:
    st.header(t("feedback_safety_check"))
    if not require_session():
        return
    feedback = data["feedback"].reset_index(drop=True)
    if feedback.empty:
        st.error(t("no_feedback"))
        return
    essays_by_id = as_records(data["essays"], "essay_id")
    routing_by_id = as_records(data["routing"], "feedback_item_id")
    safety = read_annotation_table("feedback_safety_checks")
    records = as_records(safety, "feedback_item_id")
    total = len(feedback)
    st.session_state.setdefault("safety_index", 0)
    st.session_state["safety_index"] = min(max(0, int(st.session_state["safety_index"])), total - 1)
    first_incomplete = first_incomplete_index(feedback, "feedback_item_id", records, safety_missing_fields)
    nav_buttons("safety", total, "safety_index", first_incomplete)

    row = feedback.iloc[int(st.session_state["safety_index"])].to_dict()
    feedback_item_id = safe_str(row.get("feedback_item_id"))
    essay_id = safe_str(row.get("essay_id"))
    ensure_item_timer("safety", feedback_item_id)
    existing = fetch_one("feedback_safety_checks", "feedback_item_id", feedback_item_id)
    st.caption(t("safety_progress", current=int(st.session_state["safety_index"]) + 1, total=total))
    render_feedback_card(row, essays_by_id, routing_by_id, get_session()["annotation_mode"])

    with st.form(f"feedback_safety_form_{feedback_item_id}"):
        st.markdown(f"### {t('safety_label')}")
        values: Dict[str, Any] = {
            "risk_reason_teacher": selectbox_required(
                t("risk_reason_teacher"),
                RISK_REASONS,
                existing.get("risk_reason_teacher"),
                f"{feedback_item_id}_risk_reason",
            ),
            "rubric_dimension": selectbox_required(
                t("rubric_dimension"),
                RUBRIC_DIMENSIONS,
                existing.get("rubric_dimension"),
                f"{feedback_item_id}_rubric_dimension",
            ),
            "evidence_note": st.text_area(t("evidence_note"), value=text_default(existing, "evidence_note"), height=110),
        }
        submitted = st.form_submit_button(t("save_safety_check"), type="primary", use_container_width=True)

    if submitted:
        missing = safety_missing_fields(values)
        if validate_and_show(missing):
            duration = elapsed_for_item("safety")
            save_safety_check(feedback_item_id, essay_id, values, duration)
            reset_item_timer("safety")
            st.success(t("safety_saved", item_id=feedback_item_id))


def build_progress(data: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    essays = data["essays"]
    feedback = data["feedback"]
    essay_records = as_records(read_annotation_table("essay_annotations"), "essay_id")
    feedback_records = as_records(read_annotation_table("feedback_decisions"), "feedback_item_id")
    safety_records = as_records(read_annotation_table("feedback_safety_checks"), "feedback_item_id")

    rows: List[Dict[str, Any]] = []
    for _, row in essays.iterrows():
        essay_id = safe_str(row.get("essay_id"))
        missing = essay_missing_fields(essay_records.get(essay_id))
        rows.append({"item_type": "essay", "item_id": essay_id, "complete": not missing, "missing_fields": "; ".join(missing)})
    for _, row in feedback.iterrows():
        feedback_id = safe_str(row.get("feedback_item_id"))
        missing = feedback_missing_fields(feedback_records.get(feedback_id))
        rows.append({"item_type": "feedback_decision", "item_id": feedback_id, "complete": not missing, "missing_fields": "; ".join(missing)})
        safety_missing = safety_missing_fields(safety_records.get(feedback_id))
        rows.append({"item_type": "feedback_safety", "item_id": feedback_id, "complete": not safety_missing, "missing_fields": "; ".join(safety_missing)})
    return pd.DataFrame(rows)


def page_progress(data: Mapping[str, pd.DataFrame]) -> None:
    st.header(t("progress"))
    if not require_session():
        return
    progress = build_progress(data)
    if progress.empty:
        st.info(t("no_items"))
        return
    total = len(progress)
    complete = int(progress["complete"].sum())
    c1, c2, c3 = st.columns(3)
    c1.metric(t("total_units"), total)
    c2.metric(t("complete"), complete)
    c3.metric(t("remaining"), total - complete)
    by_type = progress.groupby("item_type")["complete"].agg(["count", "sum"]).reset_index()
    by_type["remaining"] = by_type["count"] - by_type["sum"]
    by_type = by_type.rename(columns={"count": "total", "sum": "complete"})
    st.markdown(f"### {t('completion_by_type')}")
    st.dataframe(by_type, use_container_width=True, hide_index=True)
    st.markdown(f"### {t('missing_fields')}")
    missing = progress[~progress["complete"]].copy()
    if missing.empty:
        st.success(t("all_complete"))
    else:
        st.dataframe(missing, use_container_width=True, hide_index=True)


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def build_combined_json(data: Mapping[str, pd.DataFrame]) -> Dict[str, Any]:
    session = get_session()
    return {
        "metadata": {
            "expert_id": session["expert_id"],
            "batch_id": session["batch_id"],
            "annotation_mode": session["annotation_mode"],
            "exported_at": now_iso(),
            "data_policy": "anonymous_esl_writing_feedback_research_annotation_only",
        },
        "source_essays": data["essays"].to_dict(orient="records"),
        "source_feedback_items": data["feedback"].to_dict(orient="records"),
        "essay_annotations": read_annotation_table("essay_annotations").to_dict(orient="records"),
        "feedback_decisions": read_annotation_table("feedback_decisions").to_dict(orient="records"),
        "feedback_safety_checks": read_annotation_table("feedback_safety_checks").to_dict(orient="records"),
        "annotation_logs": read_annotation_table("annotation_logs").to_dict(orient="records"),
    }


def page_export(data: Mapping[str, pd.DataFrame]) -> None:
    st.header(t("export"))
    if not require_session():
        return
    tables = {
        "essay_annotations.csv": read_annotation_table("essay_annotations"),
        "feedback_decisions.csv": read_annotation_table("feedback_decisions"),
        "feedback_safety_checks.csv": read_annotation_table("feedback_safety_checks"),
        "annotation_logs.csv": read_annotation_table("annotation_logs"),
    }
    st.write(t("export_scope"))
    for file_name, df in tables.items():
        st.download_button(
            ("Download " if lang() == "en" else "下载 ") + file_name,
            data=dataframe_to_csv_bytes(df),
            file_name=file_name,
            mime="text/csv",
            use_container_width=True,
        )

    combined = build_combined_json(data)
    combined_bytes = json.dumps(combined, ensure_ascii=False, indent=2).encode("utf-8")
    st.download_button(
        ("Download " if lang() == "en" else "下载 ") + "combined_annotations.json",
        data=combined_bytes,
        file_name="combined_annotations.json",
        mime="application/json",
        use_container_width=True,
    )

    if st.button(t("write_exports"), type="primary", use_container_width=True):
        session = get_session()
        export_subdir = EXPORT_DIR / f"{session['expert_id']}_{session['batch_id']}"
        export_subdir.mkdir(parents=True, exist_ok=True)
        for file_name, df in tables.items():
            df.to_csv(export_subdir / file_name, index=False, encoding="utf-8-sig")
        (export_subdir / "combined_annotations.json").write_text(
            json.dumps(combined, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        st.success(t("export_written", path=export_subdir))


def inject_style() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #f8fafc; }
        .block-container { max-width: 1260px; padding-top: 1.5rem; }
        section[data-testid="stSidebar"] { background: #111827; }
        section[data-testid="stSidebar"] * { color: #f9fafb; }
        textarea:disabled { color: #111827 !important; -webkit-text-fill-color: #111827 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="ConsensusScope Expert Annotation", layout="wide")
    inject_style()
    init_db()
    language_choice = st.sidebar.selectbox(
        "Language / 语言",
        ["English", "中文"],
        index=0 if lang() == "en" else 1,
        key="expert_language_selector",
    )
    st.session_state["ui_language"] = "zh" if language_choice == "中文" else "en"
    if not render_access_gate():
        return
    data = load_data()
    require_columns(
        data["essays"],
        [
            "essay_id",
            "assignment_prompt",
            "essay_genre",
            "student_level",
            "essay_text_anonymized",
            "word_count",
            "draft_stage",
            "pii_removed",
        ],
        "sample_data/essays.csv",
    )
    require_columns(
        data["feedback"],
        [
            "feedback_item_id",
            "essay_id",
            "target_span",
            "surrounding_context",
            "ai_suggestion",
            "ai_rationale",
            "model_source",
            "issue_type_predicted",
        ],
        "sample_data/feedback_items.csv",
    )

    st.sidebar.title(t("sidebar_title"))
    session = get_session()
    if session_ready():
        st.sidebar.success(
            t(
                "session_summary",
                expert_id=session["expert_id"],
                batch_id=session["batch_id"],
                mode=option_label(session["annotation_mode"]),
            )
        )
    else:
        st.sidebar.warning(t("no_active_session"))
    labels = page_labels()
    page_label = st.sidebar.radio(t("pages"), labels)
    page_index = labels.index(page_label)

    st.title(t("site_title"))
    st.caption(t("site_caption"))

    if page_index == 0:
        page_expert_session(data)
    elif page_index == 1:
        page_essay_annotation(data)
    elif page_index == 2:
        page_feedback_annotation(data)
    elif page_index == 3:
        page_feedback_safety(data)
    elif page_index == 4:
        page_progress(data)
    elif page_index == 5:
        page_export(data)


if __name__ == "__main__":
    main()
