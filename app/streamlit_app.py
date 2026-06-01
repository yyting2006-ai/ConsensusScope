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
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluation.simple_correctness import is_correct
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

    st.markdown('<div class="section-title">Demo Access</div>', unsafe_allow_html=True)
    st.info("This live demo is password-protected to prevent unintended API usage.")
    if not expected:
        st.error("Demo authentication is enabled, but CONSENSUS_SCOPE_DEMO_PASSWORD is not configured.")
        return False
    with st.form("demo_auth_form"):
        entered = st.text_input("Demo password", type="password")
        submitted = st.form_submit_button("Unlock demo", use_container_width=True)
    if submitted:
        if hmac.compare_digest(entered, expected):
            st.session_state["demo_authenticated"] = True
            st.rerun()
        else:
            st.error("Invalid password.")
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
        """
        <div class="topbar">
          <div class="title">ConsensusScope</div>
          <div class="subtitle">Knowledge-grounded multi-LLM adjudication for ESL literary writing feedback</div>
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
    st.sidebar.markdown("#### API Configuration")
    api_mode = st.sidebar.radio(
        "API mode",
        ["Mode A", "Mode B"],
        format_func=lambda x: "Mode A · Built-in API keys for live demos" if x == "Mode A" else "Mode B · User-provided API keys for public deployment",
        index=0 if st.session_state["api_mode"] == "Mode A" else 1,
    )
    st.session_state["api_mode"] = api_mode
    st.sidebar.caption(
        "Mode A uses local .env or deployment secrets. Mode B uses user-provided keys only for the current request. API keys must not appear in the paper or be hard-coded."
    )
    default_selected = [p for p in ["deepseek", "qwen", "glm", "kimi"] if p in ANSWER_PROVIDERS]
    selected = st.sidebar.multiselect("Answer generation models", ANSWER_PROVIDERS, default=default_selected)
    st.sidebar.caption("Each selected provider needs its own matching API key. If you only have one key, select only that provider.")
    fixed_enabled = st.sidebar.checkbox("Enable Fixed Judge in Live mode", value=False)
    fixed_provider = st.sidebar.selectbox("Fixed judge model", selected or default_selected or ANSWER_PROVIDERS, index=0)

    user_inputs: Dict[str, Dict[str, str]] = {}
    defaults = default_live_model_configs()
    with st.sidebar.expander("Provider settings", expanded=(api_mode == "Mode B")):
        st.caption("Use the provider base URL only; the app appends /chat/completions automatically.")
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


def page_home(samples_df: pd.DataFrame, outputs_df: pd.DataFrame, metrics_df: pd.DataFrame, risk_df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Page 1 · Home / System Overview</div>', unsafe_allow_html=True)
    kg_df = read_table(str(DATA_PATHS["literary_kg"]))
    benchmark_df = read_table(str(DATA_PATHS["literary_benchmark"]))
    literary_metrics = read_table(str(DATA_PATHS["literary_metrics"]))
    metrics_df = visible_method_metrics(metrics_df)
    teacher_review = int(literary_metrics["teacher_review"].sum()) if not literary_metrics.empty and "teacher_review" in literary_metrics else 0
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        works = int(kg_df["work"].nunique()) if not kg_df.empty and "work" in kg_df else 0
        metric_panel("Literary Works", str(works), "curated KG")
    with c2:
        metric_panel("KG Triples", str(len(kg_df)), "author, genre, character, theme")
    with c3:
        metric_panel("Benchmark Essays", str(len(benchmark_df)), "diagnostic ESL snippets")
    with c4:
        metric_panel("Teacher Review", str(teacher_review), "routed feedback decisions")
    st.code(
        "Essay / Question Input -> Expert Knowledge Retrieval -> Multi-Model Feedback Generation -> "
        "Unified Output Format -> Knowledge-Grounded Adjudication -> Risk Dashboard -> Report Export",
        language="text",
    )
    st.markdown(
        "**Main demo claim:** ESL comparative-literature feedback review routing. "
        "ConsensusScope separates low-risk local edits from literary facts, argument changes, "
        "and interpretation changes that need teacher review."
    )
    st.info(
        "The auxiliary QA reliability module remains available for inspecting saved multi-model traces, "
        "but it is not the main EMNLP 2026 demo claim."
    )
    if not literary_metrics.empty:
        st.markdown('<div class="section-title">ESL Feedback Routing Snapshot</div>', unsafe_allow_html=True)
        snapshot = {
            "adjudicated_decisions": int(literary_metrics["total_suggestions"].sum()),
            "auto_accept": int(literary_metrics["auto_accept"].sum()),
            "teacher_review": int(literary_metrics["teacher_review"].sum()),
            "high_risk": int(literary_metrics["high_risk"].sum()),
            "kg_supported": int(literary_metrics["kg_supported"].sum()),
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
        c6.metric("KG triples", len(kg))
        if result:
            st.download_button(
                "Download feedback report.md",
                data=result["report"].encode("utf-8"),
                file_name="literary_feedback_report.md",
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
    st.markdown('<div class="section-title">Page 3 · Knowledge Grounding & Teacher Queue</div>', unsafe_allow_html=True)
    result = saved_literary_result()
    if not result:
        st.info("Run Page 2 first or regenerate data/results/literary_feedback_records.json.")
        return
    st.caption(
        "This page keeps the ESL feedback workflow in view: KG evidence supports inspection, "
        "and meaning-changing feedback remains in the teacher-review queue."
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
            "Download literary_feedback_report.md",
            data=result.get("report", "").encode("utf-8"),
            file_name="literary_feedback_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.text_area("Report preview", result.get("report", ""), height=260)


def page_live(api_mode: str, selected: List[str], user_inputs: Dict[str, Dict[str, str]], fixed_enabled: bool, fixed_provider: str) -> None:
    st.markdown('<div class="section-title">Page 2 · ESL Feedback Review</div>', unsafe_allow_html=True)
    mode = st.radio(
        "Mode",
        ["ESL literary essay feedback", "Auxiliary QA live comparison"],
        horizontal=True,
        label_visibility="collapsed",
    )
    if mode == "ESL literary essay feedback":
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
    literary_metrics = read_table(str(DATA_PATHS["literary_metrics"]))
    live_metrics = read_table(str(DATA_PATHS["literary_live_metrics"]))
    if not literary_metrics.empty:
        st.markdown("### ESL Feedback Routing Risk")
        summary = {
            "source": "no_api_benchmark",
            "decisions": int(literary_metrics["total_suggestions"].sum()),
            "auto_accept": int(literary_metrics["auto_accept"].sum()),
            "teacher_review": int(literary_metrics["teacher_review"].sum()),
            "high_risk": int(literary_metrics["high_risk"].sum()),
            "kg_supported": int(literary_metrics["kg_supported"].sum()),
        }
        if not live_metrics.empty:
            live_summary = {
                "source": "saved_live_validation",
                "decisions": int(live_metrics["total_suggestions"].sum()),
                "auto_accept": int(live_metrics["auto_accept"].sum()),
                "teacher_review": int(live_metrics["teacher_review"].sum()),
                "high_risk": int(live_metrics["high_risk"].sum()),
                "kg_supported": int(live_metrics["kg_supported"].sum()),
            }
            st.dataframe(pd.DataFrame([summary, live_summary]), use_container_width=True, hide_index=True)
        else:
            st.dataframe(pd.DataFrame([summary]), use_container_width=True, hide_index=True)
        st.caption("These are review-routing counts, not automatic essay-scoring results.")
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
    literary = saved_literary_result()
    if literary:
        st.download_button(
            "Download literary_feedback_report.md",
            data=literary.get("report", "").encode("utf-8"),
            file_name="literary_feedback_report.md",
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


def main() -> None:
    st.set_page_config(page_title="ConsensusScope", layout="wide")
    load_dotenv(ROOT / ".env")
    inject_styles()
    ensure_state()
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
        if st.sidebar.button("Lock demo", use_container_width=True):
            st.session_state["demo_authenticated"] = False
            st.rerun()
    page = st.sidebar.radio(
        "Navigation",
        [
            "Page 1: Home / System Overview",
            "Page 2: ESL Feedback Review",
            "Page 3: Knowledge Grounding & Teacher Queue",
            "Page 4: Adjudication Comparison",
            "Page 5: Risk Dashboard",
            "Page 6: Model Reliability Dashboard",
            "Page 7: Auxiliary QA Case Explorer",
            "Page 8: Report Export",
        ],
        label_visibility="collapsed",
    )
    st.sidebar.divider()
    api_mode, selected, user_inputs, fixed_enabled, fixed_provider = render_api_sidebar()

    if page.startswith("Page 1"):
        page_home(samples_df, outputs_df, metrics_df, risk_df)
    elif page.startswith("Page 2"):
        page_live(api_mode, selected, user_inputs, fixed_enabled, fixed_provider)
    elif page.startswith("Page 3"):
        page_knowledge_teacher_queue()
    elif page.startswith("Page 4"):
        page_comparison(metrics_df)
    elif page.startswith("Page 5"):
        page_risk_dashboard(risk_df, effectiveness_df)
    elif page.startswith("Page 6"):
        page_model_reliability(outputs_df, samples_df)
    elif page.startswith("Page 7"):
        page_case_explorer(error_df, samples_df, outputs_df)
    else:
        page_report_export(samples_df, outputs_df, metrics_df, risk_df)


if __name__ == "__main__":
    main()
