#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROUTING = ROOT / "data" / "esl_writing_demo" / "routing_results.csv"
DEFAULT_OUT = ROOT / "reports" / "esl_writing_feedback_analysis"

UNSAFE_LABELS = {"unsafe_without_revision", "uncertain_needs_review"}
SAFE_LABELS = {"safe_to_show_student"}
TEACHER_REVIEW_ACTIONS = {"teacher_review", "needs_more_evidence", "reject"}


def _safe_div(num: float, den: float) -> float:
    return 0.0 if den == 0 else float(num) / float(den)


def _read_annotations(path: Path) -> pd.DataFrame:
    annotation_file = path / "feedback_decisions.csv" if path.is_dir() else path
    if not annotation_file.exists():
        raise FileNotFoundError(
            f"Missing teacher annotation file: {annotation_file}. "
            "Expected columns include feedback_item_id, teacher_safety_label, "
            "feedback_correctness, meaning_preservation, and teacher_final_action."
        )
    return pd.read_csv(annotation_file).fillna("")


def analyze(annotations: pd.DataFrame, routing: pd.DataFrame) -> Dict[str, Any]:
    merged = routing.merge(annotations, on="feedback_item_id", how="left", validate="one_to_one")
    missing_annotations = int(merged["teacher_safety_label"].eq("").sum()) if "teacher_safety_label" in merged else len(merged)
    if missing_annotations:
        raise ValueError(f"{missing_annotations} routed items do not have teacher_safety_label annotations.")

    merged["system_reviewed"] = merged["recommended_action"].isin(TEACHER_REVIEW_ACTIONS)
    merged["teacher_marked_unsafe"] = merged["teacher_safety_label"].isin(UNSAFE_LABELS)
    merged["teacher_marked_safe"] = merged["teacher_safety_label"].isin(SAFE_LABELS)

    total = len(merged)
    reviewed = int(merged["system_reviewed"].sum())
    unsafe_total = int(merged["teacher_marked_unsafe"].sum())
    safe_total = int(merged["teacher_marked_safe"].sum())
    unsafe_reviewed = int((merged["system_reviewed"] & merged["teacher_marked_unsafe"]).sum())
    safe_auto = int((~merged["system_reviewed"] & merged["teacher_marked_safe"]).sum())
    auto_total = total - reviewed

    issue_table = (
        merged.groupby("issue_type_teacher", dropna=False)
        .agg(
            items=("feedback_item_id", "count"),
            reviewed=("system_reviewed", "sum"),
            unsafe=("teacher_marked_unsafe", "sum"),
        )
        .reset_index()
        if "issue_type_teacher" in merged
        else pd.DataFrame()
    )

    summary = {
        "items": total,
        "auto_share": round(_safe_div(auto_total, total), 4),
        "review_share": round(_safe_div(reviewed, total), 4),
        "unsafe_feedback_reviewed_recall": round(_safe_div(unsafe_reviewed, unsafe_total), 4),
        "safe_feedback_auto_accept_precision": round(_safe_div(safe_auto, auto_total), 4),
        "teacher_marked_unsafe_items": unsafe_total,
        "teacher_marked_safe_items": safe_total,
        "note": "Metrics use teacher annotations as offline diagnostics, not deploy-time gold labels.",
    }
    return {"summary": summary, "merged": merged, "issue_table": issue_table}


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze ESL writing feedback review-routing results.")
    parser.add_argument("--annotations-dir", type=Path, required=True, help="Directory or CSV with teacher feedback decisions.")
    parser.add_argument("--routing", type=Path, default=DEFAULT_ROUTING, help="Routing CSV produced by the ESL router.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help="Output directory for analysis artifacts.")
    args = parser.parse_args()

    annotations = _read_annotations(args.annotations_dir)
    routing = pd.read_csv(args.routing).fillna("")
    result = analyze(annotations, routing)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with (args.out_dir / "summary_metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(result["summary"], handle, indent=2, ensure_ascii=False)
    result["merged"].to_csv(args.out_dir / "routing_table.csv", index=False)
    result["issue_table"].to_csv(args.out_dir / "issue_type_analysis.csv", index=False)
    print(json.dumps(result["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

