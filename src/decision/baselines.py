from __future__ import annotations

import json
from collections import Counter
from typing import Any, Dict, List

import pandas as pd

from src.llm.prompts import build_judge_prompt


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def _answer_col(df: pd.DataFrame) -> str:
    if "answer" in df.columns:
        return "answer"
    if "final_answer" in df.columns:
        return "final_answer"
    raise ValueError("outputs_df must contain an 'answer' or 'final_answer' column")


def _model_mask(outputs_df: pd.DataFrame, model_name: str) -> pd.Series:
    target = model_name.strip().lower()
    mask = pd.Series(False, index=outputs_df.index)
    for col in ["model", "model_name", "provider"]:
        if col in outputs_df.columns:
            mask = mask | outputs_df[col].astype(str).str.lower().eq(target)
    return mask


def _valid_outputs(outputs_df: pd.DataFrame) -> pd.DataFrame:
    df = outputs_df.copy()
    if "parse_error" in df.columns:
        df = df[df["parse_error"].fillna("").astype(str).str.strip() == ""]
    elif "parse_ok" in df.columns:
        parse_ok = df["parse_ok"]
        if parse_ok.dtype == object:
            parse_ok = parse_ok.astype(str).str.lower().isin(["true", "1", "yes"])
        df = df[parse_ok]
    col = _answer_col(df)
    return df[df[col].map(_safe_str) != ""]


def single_model_decision(outputs_df: pd.DataFrame, model_name: str) -> pd.DataFrame:
    """Return one model's answer as the final answer for each sample."""

    answer_col = _answer_col(outputs_df)
    df = outputs_df[_model_mask(outputs_df, model_name)].copy()
    rows: List[Dict[str, Any]] = []
    for sample_id, group in df.groupby("sample_id", sort=False):
        row = group.iloc[0]
        final_answer = _safe_str(row.get(answer_col, ""))
        rows.append(
            {
                "sample_id": sample_id,
                "method": f"single_model:{model_name}",
                "final_answer": final_answer,
                "vote_distribution": json.dumps({final_answer: 1} if final_answer else {}, ensure_ascii=False),
                "agreement_rate": 1.0 if final_answer else 0.0,
                "risk_level": "low" if final_answer else "high",
                "decision_note": f"使用单模型 {model_name} 的输出",
            }
        )
    return pd.DataFrame(rows)


def majority_vote(outputs_df: pd.DataFrame) -> pd.DataFrame:
    """Run per-sample majority vote over model answers."""

    answer_col = _answer_col(outputs_df)
    df = _valid_outputs(outputs_df)
    rows: List[Dict[str, Any]] = []

    for sample_id, group in df.groupby("sample_id", sort=False):
        answers = [_safe_str(x) for x in group[answer_col].tolist() if _safe_str(x)]
        total = len(answers)
        counts = Counter(answers)
        if not counts:
            rows.append(
                {
                    "sample_id": sample_id,
                    "method": "majority_vote",
                    "final_answer": "",
                    "vote_distribution": "{}",
                    "agreement_rate": 0.0,
                    "risk_level": "high",
                    "decision_note": "无有效模型答案，建议人工复核",
                }
            )
            continue

        top_answer, top_count = counts.most_common(1)[0]
        tied = sum(1 for count in counts.values() if count == top_count) > 1
        agreement_rate = top_count / total if total else 0.0
        if tied:
            final_answer = ""
            risk_level = "high"
            note = "最高票答案平票，建议人工复核"
        else:
            final_answer = top_answer
            risk_level = "low" if agreement_rate >= 0.75 else "medium" if agreement_rate >= 0.5 else "high"
            note = "采纳唯一最高票答案"

        rows.append(
            {
                "sample_id": sample_id,
                "method": "majority_vote",
                "final_answer": final_answer,
                "vote_distribution": json.dumps(dict(counts), ensure_ascii=False),
                "agreement_rate": round(agreement_rate, 6),
                "risk_level": risk_level,
                "decision_note": note,
            }
        )
    columns = [
        "sample_id",
        "method",
        "final_answer",
        "vote_distribution",
        "agreement_rate",
        "risk_level",
        "decision_note",
    ]
    return pd.DataFrame(rows, columns=columns)


def fixed_judge_decision(
    sample: Dict[str, Any],
    model_outputs: List[Dict[str, Any]],
    judge_client: Any,
) -> Dict[str, Any]:
    """Call a fixed judge model and return one adjudication record."""

    prompt = build_judge_prompt(sample, model_outputs)
    result = judge_client.call_json(prompt, temperature=0.0, max_tokens=800)

    parse_error = _safe_str(result.get("parse_error", ""))
    request_error = _safe_str(result.get("request_error", ""))
    final_answer = _safe_str(result.get("final_answer", ""))
    risk_level = _safe_str(result.get("risk_level", "high")).lower()
    if risk_level not in {"low", "medium", "high"}:
        risk_level = "high"

    try:
        confidence = float(result.get("confidence", 0.0))
    except Exception:
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    if parse_error or request_error:
        note = "固定裁决器调用或解析失败，建议人工复核"
        risk_level = "high"
    else:
        note = _safe_str(result.get("decision_reason", "")) or "固定裁决器给出裁决"

    return {
        "sample_id": sample.get("id", ""),
        "method": "fixed_judge",
        "final_answer": final_answer,
        "decision_reason": _safe_str(result.get("decision_reason", "")),
        "risk_level": risk_level,
        "confidence": confidence,
    }
