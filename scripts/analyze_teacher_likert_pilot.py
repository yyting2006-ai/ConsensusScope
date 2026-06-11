#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROUTING = ROOT / "data" / "esl_writing_demo" / "routing_results.csv"
DEFAULT_OUT = ROOT / "reports" / "teacher_likert_pilot"

SCORE_FIELDS = [
    "correctness_score",
    "meaning_preservation_score",
    "student_readiness_score",
    "usefulness_score",
    "clarity_score",
    "direct_release_score",
]
CORE_SAFE_FIELDS = [
    "correctness_score",
    "meaning_preservation_score",
    "student_readiness_score",
    "direct_release_score",
]
TEACHER_REVIEW_ACTIONS = {"teacher_review", "needs_more_evidence", "reject"}


def _safe_div(num: float, den: float) -> float:
    return 0.0 if den == 0 else float(num) / float(den)


def _read_ratings(path: Path) -> pd.DataFrame:
    rating_file = path / "likert_feedback_ratings.csv" if path.is_dir() else path
    if not rating_file.exists():
        raise FileNotFoundError(
            f"Missing Likert rating file: {rating_file}. "
            "Expected export file name: likert_feedback_ratings.csv."
        )
    ratings = pd.read_csv(rating_file).fillna("")
    required = {"expert_id", "batch_id", "feedback_item_id", "essay_id", *SCORE_FIELDS}
    missing = sorted(required.difference(ratings.columns))
    if missing:
        raise ValueError(f"Likert rating file is missing required columns: {missing}")
    for field in ["expert_id", "batch_id", "feedback_item_id", "essay_id"]:
        ratings[field] = ratings[field].astype(str)
    expert_count = ratings["expert_id"].astype(str).nunique()
    if expert_count > 2:
        raise ValueError(f"This pilot protocol supports at most two teachers; found {expert_count}.")
    for field in SCORE_FIELDS:
        ratings[field] = pd.to_numeric(ratings[field], errors="coerce")
        bad = ratings[field].isna() | ratings[field].lt(1) | ratings[field].gt(5)
        if bool(bad.any()):
            bad_ids = ratings.loc[bad, "feedback_item_id"].astype(str).head(5).tolist()
            raise ValueError(f"{field} must be an integer 1-5. Bad examples: {bad_ids}")
    return ratings


def _agreement_metrics(ratings: pd.DataFrame) -> Dict[str, Any]:
    experts = sorted(ratings["expert_id"].astype(str).unique().tolist())
    if len(experts) != 2:
        return {
            "expert_count": len(experts),
            "items_with_two_ratings": 0,
            "note": "Agreement metrics require exactly two teachers.",
        }

    two_counts = ratings.groupby("feedback_item_id")["expert_id"].nunique()
    two_items = two_counts[two_counts == 2].index
    paired = ratings[ratings["feedback_item_id"].isin(two_items)].copy()
    out: Dict[str, Any] = {"expert_count": 2, "items_with_two_ratings": int(len(two_items))}
    field_rows: List[Dict[str, Any]] = []
    for field in SCORE_FIELDS:
        pivot = paired.pivot_table(index="feedback_item_id", columns="expert_id", values=field, aggfunc="first")
        if len(experts) != 2 or pivot.empty or not set(experts).issubset(pivot.columns):
            continue
        diff = (pivot[experts[0]] - pivot[experts[1]]).abs()
        corr = pivot[experts[0]].corr(pivot[experts[1]], method="spearman")
        field_rows.append(
            {
                "field": field,
                "mean_absolute_difference": round(float(diff.mean()), 4),
                "within_1_point_share": round(float(diff.le(1).mean()), 4),
                "exact_agreement_share": round(float(diff.eq(0).mean()), 4),
                "spearman": None if pd.isna(corr) else round(float(corr), 4),
            }
        )
    out["fields"] = field_rows
    if field_rows:
        out["mean_within_1_point_share"] = round(
            sum(row["within_1_point_share"] for row in field_rows) / len(field_rows), 4
        )
    return out


def analyze(ratings: pd.DataFrame, routing: pd.DataFrame) -> Dict[str, Any]:
    ratings = ratings.copy()
    routing = routing.copy()
    for field in ["expert_id", "batch_id", "feedback_item_id", "essay_id"]:
        if field in ratings:
            ratings[field] = ratings[field].astype(str)
    if "feedback_item_id" in routing:
        routing["feedback_item_id"] = routing["feedback_item_id"].astype(str)

    item_agg = (
        ratings.groupby(["feedback_item_id", "essay_id"], as_index=False)
        .agg(
            expert_count=("expert_id", "nunique"),
            rating_count=("expert_id", "size"),
            mean_duration_seconds=("duration_seconds", "mean") if "duration_seconds" in ratings else ("expert_id", "size"),
            **{f"mean_{field}": (field, "mean") for field in SCORE_FIELDS},
        )
    )
    for field in SCORE_FIELDS:
        item_agg[f"mean_{field}"] = item_agg[f"mean_{field}"].round(4)

    core_mean_fields = [f"mean_{field}" for field in CORE_SAFE_FIELDS]
    item_agg["teacher_safe_for_release"] = item_agg[core_mean_fields].ge(4.0).all(axis=1)
    item_agg["teacher_review_needed"] = item_agg[core_mean_fields].le(3.0).any(axis=1)
    item_agg["teacher_marked_unsafe"] = item_agg[core_mean_fields].le(2.0).any(axis=1)

    merged = routing.merge(item_agg, on="feedback_item_id", how="left")
    missing = int(merged["expert_count"].isna().sum()) if "expert_count" in merged else len(merged)
    merged["system_reviewed"] = merged["recommended_action"].isin(TEACHER_REVIEW_ACTIONS)
    merged["system_auto_accept"] = merged["recommended_action"].eq("auto_accept")

    covered = merged.dropna(subset=["expert_count"]).copy()
    total = len(covered)
    reviewed = int(covered["system_reviewed"].sum()) if total else 0
    auto = int(covered["system_auto_accept"].sum()) if total else 0
    teacher_review_needed = int(covered["teacher_review_needed"].sum()) if total else 0
    teacher_unsafe = int(covered["teacher_marked_unsafe"].sum()) if total else 0
    teacher_safe = int(covered["teacher_safe_for_release"].sum()) if total else 0
    reviewed_needed = int((covered["system_reviewed"] & covered["teacher_review_needed"]).sum()) if total else 0
    reviewed_unsafe = int((covered["system_reviewed"] & covered["teacher_marked_unsafe"]).sum()) if total else 0
    auto_safe = int((covered["system_auto_accept"] & covered["teacher_safe_for_release"]).sum()) if total else 0

    route_score_summary = (
        covered.groupby("recommended_action", dropna=False)
        .agg(
            items=("feedback_item_id", "count"),
            **{f"avg_{field}": (f"mean_{field}", "mean") for field in SCORE_FIELDS},
        )
        .reset_index()
    )
    for col in route_score_summary.columns:
        if col.startswith("avg_"):
            route_score_summary[col] = route_score_summary[col].round(4)

    summary = {
        "rated_items": int(total),
        "missing_routed_items": missing,
        "teacher_count": int(ratings["expert_id"].astype(str).nunique()),
        "rating_rows": int(len(ratings)),
        "auto_share": round(_safe_div(auto, total), 4),
        "review_share": round(_safe_div(reviewed, total), 4),
        "teacher_safe_items": teacher_safe,
        "teacher_review_needed_items": teacher_review_needed,
        "teacher_unsafe_items": teacher_unsafe,
        "review_needed_recall": round(_safe_div(reviewed_needed, teacher_review_needed), 4),
        "unsafe_reviewed_recall": round(_safe_div(reviewed_unsafe, teacher_unsafe), 4),
        "auto_accept_precision_against_teacher_safe": round(_safe_div(auto_safe, auto), 4),
        "agreement": _agreement_metrics(ratings),
        "note": (
            "Likert ratings are offline teacher diagnostics. They are not used by the deploy-time router. "
            "Scores are averaged across at most two teachers."
        ),
    }
    return {
        "summary": summary,
        "item_aggregates": item_agg,
        "merged": merged,
        "route_score_summary": route_score_summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze two-teacher 1-5 Likert ratings for ESL feedback review.")
    parser.add_argument("--ratings", type=Path, required=True, help="Directory or CSV file with likert_feedback_ratings.csv.")
    parser.add_argument("--routing", type=Path, default=DEFAULT_ROUTING, help="ConsensusScope routing CSV.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help="Output directory.")
    args = parser.parse_args()

    ratings = _read_ratings(args.ratings)
    routing = pd.read_csv(args.routing).fillna("")
    result = analyze(ratings, routing)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "likert_summary_metrics.json").write_text(
        json.dumps(result["summary"], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    result["item_aggregates"].to_csv(args.out_dir / "likert_item_aggregates.csv", index=False)
    result["merged"].to_csv(args.out_dir / "likert_routing_analysis.csv", index=False)
    result["route_score_summary"].to_csv(args.out_dir / "likert_route_score_summary.csv", index=False)
    print(json.dumps(result["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
