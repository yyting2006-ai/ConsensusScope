from __future__ import annotations

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

from src.evaluation.metrics import is_correct
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
    "figures": ROOT / "reports" / "figures",
}

ANSWER_PROVIDERS = [p for p in PROVIDER_CONFIG if p != "judge"]
RISK_LABELS = ["true_consensus", "false_consensus", "minority_correct", "high_disagreement", "confidence_mismatch"]

NOTE_TRANSLATIONS = {
    "无有效模型输出，建议人工复核": "No valid model output; human review is recommended.",
    "无唯一多数答案，建议人工复核": "No unique majority answer; human review is recommended.",
    "低风险采纳": "Low-risk adoption.",
    "一致但证据或置信度不足，标记为风险共识": "Agreement exists, but evidence or confidence is insufficient; mark as risky consensus.",
    "事实核查非NEI共识仍需证据审查，避免低风险误判": "Fact-verification consensus still needs evidence review to avoid low-risk misclassification.",
    "开放式真实性问答输出核查标签，避免低风险误判": "Open truthfulness QA produced a verification label; avoid low-risk misclassification.",
    "触发少数派预警": "Minority warning triggered.",
    "高分歧，建议人工复核": "High disagreement; human review is recommended.",
    "事实核查存在分歧，避免低风险误判": "Fact verification contains disagreement; avoid low-risk misclassification.",
    "采纳多数答案，并根据可靠性评分分级": "Adopt the majority answer and assign a risk level using reliability score.",
    "采纳唯一最高票答案": "Adopt the unique top-voted answer.",
    "最高票答案平票，建议人工复核": "Top-voted answers are tied; human review is recommended.",
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
    return NOTE_TRANSLATIONS.get(text, text)


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
        "audit_selection": None,
        "api_mode": "Mode A",
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
          <div class="subtitle">Multi-LLM reliability assessment, risk diagnosis, and dynamic adjudication system</div>
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


def visible_method_metrics(metrics_df: pd.DataFrame) -> pd.DataFrame:
    if metrics_df.empty or "method" not in metrics_df.columns:
        return metrics_df
    method_text = metrics_df["method"].astype(str).str.lower()
    return metrics_df[~method_text.str.contains("learned")].copy()


def provider_env_value(provider: str, field: str) -> str:
    cfg = PROVIDER_CONFIG[provider]
    key = cfg[field]
    value = os.getenv(key, "")
    if value:
        return value
    try:
        secret_value = st.secrets.get(key, "")
    except Exception:
        secret_value = ""
    return str(secret_value) if secret_value else ""


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
    fixed_enabled = st.sidebar.checkbox("Enable Fixed Judge in Live mode", value=False)
    fixed_provider = st.sidebar.selectbox("Fixed judge model", selected or default_selected or ANSWER_PROVIDERS, index=0)

    user_inputs: Dict[str, Dict[str, str]] = {}
    defaults = default_live_model_configs()
    with st.sidebar.expander("Provider settings", expanded=(api_mode == "Mode B")):
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
    st.dataframe(df[[c for c in cols if c in df.columns]], use_container_width=True, hide_index=True)


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
    metrics_df = visible_method_metrics(metrics_df)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_panel("Samples", str(len(samples_df)), "clean_dataset.csv")
    with c2:
        metric_panel("Model Outputs", str(len(outputs_df)), "Unified CSV / JSONL outputs")
    with c3:
        metric_panel("Adjudicators", "3", "Majority, Fixed, Rule")
    with c4:
        best = metrics_df["accuracy"].max() if not metrics_df.empty and "accuracy" in metrics_df else 0
        metric_panel("Best Accuracy", f"{best:.3f}", "current result files")
    st.code(
        "API Configuration -> Multi-Model Answer Generation -> Unified Output Format -> "
        "Adjudication Layer -> Risk Dashboard -> Reliability Dashboard -> Case Explorer -> Report Export",
        language="text",
    )
    st.markdown(
        "**Adjudication Layer:** Majority Vote / Fixed Judge / Dynamic Rule-Based Judge"
    )
    if not metrics_df.empty:
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)
    if not risk_df.empty and "risk_labels" in risk_df:
        labels: List[str] = []
        for item in risk_df["risk_labels"].fillna(""):
            labels.extend([x.strip() for x in str(item).split(";") if x.strip()])
        if labels:
            st.bar_chart(pd.Series(labels).value_counts())


def page_live(api_mode: str, selected: List[str], user_inputs: Dict[str, Dict[str, str]], fixed_enabled: bool, fixed_provider: str) -> None:
    st.markdown('<div class="section-title">Page 2 · Live Question Mode</div>', unsafe_allow_html=True)
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
        st.dataframe(display, use_container_width=True, hide_index=True)

    rows = []
    for label, df in [
        ("Majority Vote", majority_df),
        ("Fixed Judge", fixed_df),
        ("Dynamic Rule-Based Judge", dynamic_df),
    ]:
        rec = first_record(dataframe_for_sample(df, "sample_id", sid))
        rows.append(
            {
                "method": label,
                "final_answer": rec.get("final_answer", ""),
                "risk_level": rec.get("risk_level", ""),
                "score": rec.get("reliability_score", rec.get("confidence", rec.get("agreement_rate", ""))),
                "note": english_note(rec.get("decision_note", rec.get("decision_reason", ""))),
            }
        )
    st.markdown('<div class="section-title">Adjudication Layer</div>', unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    risk = first_record(dataframe_for_sample(risk_df, "sample_id", sid))
    st.markdown('<div class="section-title">Risk Labels</div>', unsafe_allow_html=True)
    risk_text = safe_str(risk.get("risk_labels", ""))
    st.write(risk_text or "None")


def page_comparison(metrics_df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Page 4 · Adjudication Comparison</div>', unsafe_allow_html=True)
    live = st.session_state.get("live_result")
    render_adjudication_comparison((live or {}).get("comparison"))
    st.markdown("### Offline Experiment Metrics")
    metrics_df = visible_method_metrics(metrics_df)
    if metrics_df.empty:
        st.info("Missing data/results/method_metrics.csv.")
        return
    st.dataframe(metrics_df, use_container_width=True, hide_index=True)
    if {"method", "accuracy"}.issubset(metrics_df.columns):
        st.bar_chart(metrics_df.set_index("method")["accuracy"])


def page_risk_dashboard(risk_df: pd.DataFrame, effectiveness_df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Page 5 · Risk Dashboard</div>', unsafe_allow_html=True)
    if risk_df.empty:
        st.info("Missing risk_labels.csv.")
        return
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
    st.markdown('<div class="section-title">Page 7 · Case Explorer</div>', unsafe_allow_html=True)
    if error_df.empty:
        st.info("Missing error_cases.csv.")
        return
    note_filter = st.multiselect("Case tags", sorted({x for s in error_df["notes"].fillna("") for x in str(s).split(";") if x}), default=[])
    df = error_df.copy()
    if note_filter:
        df = df[df["notes"].fillna("").apply(lambda s: any(tag in str(s).split(";") for tag in note_filter))]
    st.dataframe(df, use_container_width=True, hide_index=True)
    if not df.empty:
        sid = st.selectbox("Inspect case", df["sample_id"].astype(str).tolist())
        sample = first_record(dataframe_for_sample(samples_df, "id", sid))
        st.write(sample.get("question", ""))
        st.dataframe(dataframe_for_sample(outputs_df, "sample_id", sid), use_container_width=True, hide_index=True)


def page_report_export(samples_df: pd.DataFrame, outputs_df: pd.DataFrame, metrics_df: pd.DataFrame, risk_df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Page 8 · Report Export</div>', unsafe_allow_html=True)
    live = st.session_state.get("live_result")
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
    inject_styles()
    ensure_state()
    topbar()

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
    page = st.sidebar.radio(
        "Navigation",
        [
            "Page 1: Home / System Overview",
            "Page 2: Live Question Mode",
            "Page 3: Sample Audit Mode",
            "Page 4: Adjudication Comparison",
            "Page 5: Risk Dashboard",
            "Page 6: Model Reliability Dashboard",
            "Page 7: Case Explorer",
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
        page_sample_audit(samples_df, outputs_df, majority_df, dynamic_df, fixed_df, risk_df)
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
