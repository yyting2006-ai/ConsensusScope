#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

import pandas as pd
from sklearn.linear_model import LogisticRegression


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "reports" / "teacher_likert_pilot" / "likert_routing_analysis.csv"
DEFAULT_OUTPUT = ROOT / "data" / "esl_writing_demo" / "routing_calibration.json"
FEATURE_NAMES = [
    "risk_score",
    "has_local_edit",
    "has_meaning_risk",
    "has_grounding_risk",
    "has_specificity_risk",
    "has_agreement_risk",
    "has_evidence_gap",
]


def _has_any(text: str, values: set[str]) -> int:
    return int(any(value in text for value in values))


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in df.fillna("").iterrows():
        reasons = str(row.get("risk_reasons", ""))
        dims = str(row.get("safety_graph_active_dimensions", ""))
        evidence = str(row.get("evidence_signal", ""))
        rows.append(
            {
                "risk_score": float(row.get("risk_score") or 0.0),
                "has_local_edit": int("local_language_edit" in reasons or "local_edit" in dims),
                "has_meaning_risk": _has_any(
                    reasons,
                    {"meaning_change", "overcorrection", "wrong_correction"},
                )
                or int("meaning_preservation" in dims),
                "has_grounding_risk": int("unsupported_claim" in reasons or "content_grounding" in dims),
                "has_specificity_risk": _has_any(reasons, {"too_vague", "teacher_dependent"})
                or int("specificity" in dims),
                "has_agreement_risk": int("low_model_agreement" in reasons or "model_agreement" in dims),
                "has_evidence_gap": int(evidence in {"missing", "conflict"}),
            }
        )
    return pd.DataFrame(rows, columns=FEATURE_NAMES)


def select_cutoff(probabilities, labels) -> Dict[str, float]:
    best = None
    labels = labels.astype(bool)
    for idx in range(101):
        cutoff = idx / 100
        predicted_review = probabilities >= cutoff
        review_needed = labels
        review_needed_recall = (
            float((predicted_review & review_needed).sum()) / float(review_needed.sum())
            if review_needed.sum()
            else 0.0
        )
        auto = ~predicted_review
        auto_precision = float((auto & ~review_needed).sum()) / float(auto.sum()) if auto.sum() else 0.0
        auto_count = int(auto.sum())
        candidate = (review_needed_recall >= 1.0, auto_count, auto_precision, cutoff, review_needed_recall)
        if candidate[0] and (best is None or candidate[1:] > best[1:]):
            best = candidate
    if best is None:
        return {"review_probability_cutoff": 0.5, "review_needed_recall": 0.0, "auto_precision": 0.0}
    _, _, auto_precision, cutoff, recall = best
    return {
        "review_probability_cutoff": round(float(cutoff), 4),
        "review_needed_recall": round(float(recall), 4),
        "auto_precision": round(float(auto_precision), 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit the ConsensusScope routing calibration policy.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    if "teacher_review_needed" not in df.columns:
        raise ValueError("Input must contain teacher_review_needed from the Likert pilot analysis.")
    x = build_features(df)
    y = df["teacher_review_needed"].astype(int)
    model = LogisticRegression(C=0.5, class_weight="balanced", random_state=13, max_iter=1000)
    model.fit(x, y)
    probabilities = model.predict_proba(x)[:, 1]
    cutoff = select_cutoff(probabilities, y)
    artifact = {
        "name": "pilot_calibrated_logistic_v1",
        "source": str(args.input.relative_to(ROOT) if args.input.is_relative_to(ROOT) else args.input),
        "target": "teacher_review_needed",
        "items": int(len(df)),
        "feature_names": FEATURE_NAMES,
        "intercept": round(float(model.intercept_[0]), 8),
        "coefficients": {
            name: round(float(value), 8) for name, value in zip(FEATURE_NAMES, model.coef_[0])
        },
        **cutoff,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(artifact, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
