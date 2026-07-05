#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.llm.clients import get_client


DEFAULT_FEEDBACK = ROOT / "expert_annotation_app" / "sample_data" / "feedback_items.csv"
DEFAULT_ROUTING = ROOT / "expert_annotation_app" / "sample_data" / "routing_results.csv"
DEFAULT_ITEM_AGG = ROOT / "reports" / "teacher_likert_pilot" / "likert_item_aggregates.csv"
DEFAULT_OUT_DIR = ROOT / "reports" / "teacher_likert_pilot"
LOW_RISK_ISSUES = {"grammar", "spelling", "punctuation", "vocabulary", "word_choice"}
REVIEW_ACTIONS = {"teacher_review", "needs_more_evidence", "reject"}


def _safe_div(num: float, den: float) -> float | None:
    return None if den == 0 else float(num) / float(den)


def _round(value: float | None) -> float | None:
    return None if value is None else round(float(value), 4)


def _load_merged(feedback_path: Path, routing_path: Path, item_agg_path: Path) -> pd.DataFrame:
    feedback = pd.read_csv(feedback_path).drop_duplicates("feedback_item_id").fillna("")
    routing = pd.read_csv(routing_path).drop_duplicates("feedback_item_id").fillna("")
    item_agg = pd.read_csv(item_agg_path).drop_duplicates("feedback_item_id").fillna("")
    merged = feedback.merge(routing, on=["feedback_item_id", "essay_id"], how="inner", suffixes=("", "_route"))
    merged = merged.merge(item_agg, on=["feedback_item_id", "essay_id"], how="inner")
    if merged.empty:
        raise ValueError("No overlapping feedback, routing, and teacher-rating records.")
    for field in ["teacher_safe_for_release", "teacher_review_needed", "teacher_marked_unsafe"]:
        merged[field] = merged[field].astype(str).str.lower().eq("true") | merged[field].eq(True)
    return merged


def _evaluate_policy(df: pd.DataFrame, policy: str, auto_mask: Iterable[bool]) -> Dict[str, Any]:
    auto = pd.Series(list(auto_mask), index=df.index).astype(bool)
    review = ~auto
    safe = df["teacher_safe_for_release"].astype(bool)
    review_needed = df["teacher_review_needed"].astype(bool)
    unsafe = df["teacher_marked_unsafe"].astype(bool)
    auto_n = int(auto.sum())
    review_n = int(review.sum())
    safe_auto_n = int((auto & safe).sum())
    return {
        "policy": policy,
        "items": int(len(df)),
        "auto_count": auto_n,
        "safe_auto_count": safe_auto_n,
        "auto_share": _round(_safe_div(auto_n, len(df))),
        "auto_accept_precision_teacher_safe": _round(_safe_div(safe_auto_n, auto_n)),
        "review_count": review_n,
        "review_share": _round(_safe_div(review_n, len(df))),
        "review_needed_recall": _round(_safe_div(int((review & review_needed).sum()), int(review_needed.sum()))),
        "unsafe_reviewed_recall": _round(_safe_div(int((review & unsafe).sum()), int(unsafe.sum()))),
        "unsafe_auto_released": int((auto & unsafe).sum()),
        "teacher_safe_auto_released": int((auto & safe).sum()),
    }


def _bootstrap_ci(df: pd.DataFrame, auto_mask: Iterable[bool], seed: int = 13, rounds: int = 5000) -> Dict[str, Any]:
    rng = random.Random(seed)
    rows = list(range(len(df)))
    auto_series = pd.Series(list(auto_mask), index=df.index).astype(bool).reset_index(drop=True)
    clean = df.reset_index(drop=True)
    values: Dict[str, List[float]] = {
        "auto_accept_precision_teacher_safe": [],
        "review_needed_recall": [],
        "unsafe_reviewed_recall": [],
    }
    for _ in range(rounds):
        sample_idx = [rng.choice(rows) for _ in rows]
        sample = clean.iloc[sample_idx].reset_index(drop=True)
        sample_auto = auto_series.iloc[sample_idx].reset_index(drop=True)
        metrics = _evaluate_policy(sample, "bootstrap", sample_auto)
        for key in values:
            value = metrics.get(key)
            if value is not None:
                values[key].append(float(value))
    out: Dict[str, Any] = {}
    for key, vals in values.items():
        if not vals:
            out[key] = None
            continue
        vals = sorted(vals)
        out[key] = {
            "low": round(vals[int(0.025 * (len(vals) - 1))], 4),
            "high": round(vals[int(0.975 * (len(vals) - 1))], 4),
        }
    return out


def _llm_prompt(row: pd.Series) -> str:
    return f"""
You are judging whether one AI-generated ESL writing feedback item can be shown
directly to a student without teacher editing. Use only the anonymized essay
context and feedback item below. Do not assume any gold label.

Return valid JSON with:
- safe_to_release: boolean
- needs_teacher_review: boolean
- risk_reason: short string
- confidence: number from 0 to 1

Mark needs_teacher_review=true if the feedback may change the student's meaning,
introduce unsupported content, make a wrong correction, overcorrect the draft,
use harsh or vague wording, depend on teacher preference, or require missing
evidence. Mark safe_to_release=true only for narrow local edits that preserve
meaning and are clear enough for a student.

Target span: {row.get("target_span", "")}
Surrounding context: {row.get("surrounding_context", "")}
AI suggestion: {row.get("ai_suggestion", "")}
AI rationale: {row.get("ai_rationale", "")}
Predicted issue type: {row.get("issue_type_predicted", "")}
""".strip()


def _run_llm_judge(df: pd.DataFrame, provider: str, cache_path: Path) -> pd.DataFrame:
    if cache_path.exists():
        cached = pd.read_csv(cache_path).fillna("")
        if set(df["feedback_item_id"]).issubset(set(cached["feedback_item_id"])):
            return cached
    client = get_client(provider)
    rows: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        result = client.call_json(_llm_prompt(row), temperature=0.0, max_tokens=240)
        request_error = str(result.get("request_error", "") or "")
        parse_error = str(result.get("parse_error", "") or "")
        safe = bool(result.get("safe_to_release", False)) if not request_error else False
        review = bool(result.get("needs_teacher_review", not safe)) if not request_error else True
        rows.append(
            {
                "feedback_item_id": row["feedback_item_id"],
                "provider": provider,
                "model": result.get("model", ""),
                "safe_to_release": safe,
                "needs_teacher_review": review,
                "risk_reason": result.get("risk_reason", result.get("reason", "")),
                "confidence": result.get("confidence", ""),
                "request_error": request_error,
                "parse_error": parse_error,
            }
        )
    out = pd.DataFrame(rows)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(cache_path, index=False)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate teacher-pilot routing baselines.")
    parser.add_argument("--feedback", type=Path, default=DEFAULT_FEEDBACK)
    parser.add_argument("--routing", type=Path, default=DEFAULT_ROUTING)
    parser.add_argument("--item-aggregates", type=Path, default=DEFAULT_ITEM_AGG)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--run-llm-judge", action="store_true")
    parser.add_argument("--provider", default="judge")
    parser.add_argument("--env-file", type=Path, default=None)
    args = parser.parse_args()

    if args.env_file:
        load_dotenv(args.env_file)
    else:
        load_dotenv(ROOT / ".env")

    df = _load_merged(args.feedback, args.routing, args.item_aggregates)
    fsgr_auto = df["recommended_action"].eq("auto_accept")
    rule_auto = df["issue_type_predicted"].astype(str).str.lower().isin(LOW_RISK_ISSUES)
    probability_auto = pd.to_numeric(df["calibrated_review_probability"], errors="coerce").lt(0.30)

    rows = [
        _evaluate_policy(df, "FSGR default", fsgr_auto),
        _evaluate_policy(df, "Issue-type rule only", rule_auto),
        _evaluate_policy(df, "Probability-only cutoff", probability_auto),
        _evaluate_policy(df, "Review all", [False] * len(df)),
        _evaluate_policy(df, "Auto-release all", [True] * len(df)),
    ]

    if args.run_llm_judge:
        llm_path = args.out_dir / f"llm_as_judge_{args.provider}.csv"
        llm_df = _run_llm_judge(df, args.provider, llm_path)
        llm_merged = df[["feedback_item_id"]].merge(llm_df, on="feedback_item_id", how="left")
        llm_auto = llm_merged["safe_to_release"].astype(bool) & ~llm_merged["needs_teacher_review"].astype(bool)
        rows.insert(1, _evaluate_policy(df, f"LLM-as-judge ({args.provider})", llm_auto))

    out_df = pd.DataFrame(rows)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(args.out_dir / "teacher_pilot_baseline_comparison.csv", index=False)
    summary = {
        "teacher_pilot_items": int(len(df)),
        "baseline_rows": rows,
        "fsgr_bootstrap_ci_95": _bootstrap_ci(df, fsgr_auto),
        "note": (
            "Teacher labels are offline diagnostics. Baselines are evaluated on the same 30 blind-rated "
            "feedback items and do not use teacher labels at deploy time."
        ),
    }
    (args.out_dir / "teacher_pilot_baseline_comparison.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
