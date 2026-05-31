from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from src.evaluation.metrics import (
    compute_accuracy,
    compute_confidence_mismatch_rate,
    compute_false_consensus_rate,
    compute_high_disagreement_rate,
    compute_minority_correct_rate,
    is_correct,
    risk_level_effectiveness,
)
from src.evaluation.risk_labeler import label_risks


DEFAULT_RISK_LABELS_OUT = Path("data/results/risk_labels.csv")
DEFAULT_METHOD_METRICS_OUT = Path("data/results/method_metrics.csv")
DEFAULT_RISK_EFFECTIVENESS_OUT = Path("data/results/risk_level_effectiveness.csv")
DEFAULT_ERROR_CASES_OUT = Path("data/results/error_cases.csv")


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value)


def _read_table(path: Path, required: bool = True) -> pd.DataFrame:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Input file not found: {path}")
        return pd.DataFrame()
    if path.suffix.lower() == ".jsonl":
        return pd.read_json(path, lines=True)
    return pd.read_csv(path)


def _write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def _load_decision_frames(args: argparse.Namespace) -> List[pd.DataFrame]:
    frames: List[pd.DataFrame] = []
    for method_name, path in [
        ("majority_vote", args.majority),
        ("dynamic_decision", args.dynamic),
        ("fixed_judge", args.fixed_judge),
    ]:
        df = _read_table(path, required=False)
        if df.empty:
            continue
        if "method" not in df.columns:
            df["method"] = method_name
        frames.append(df)
    if args.include_learned_meta:
        df = _read_table(args.learned_meta, required=False)
        if not df.empty:
            if "method" not in df.columns:
                df["method"] = "learned_meta_judge"
            frames.append(df)
    return frames


def _method_metrics(decision_frames: List[pd.DataFrame], samples_df: pd.DataFrame, risk_df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for df in decision_frames:
        for method, method_df in df.groupby("method", sort=False):
            rows.append(
                {
                    "method": method,
                    "accuracy": compute_accuracy(method_df, samples_df),
                    "false_consensus_rate": compute_false_consensus_rate(risk_df),
                    "minority_correct_rate": compute_minority_correct_rate(risk_df),
                    "high_disagreement_rate": compute_high_disagreement_rate(risk_df),
                    "confidence_mismatch_rate": compute_confidence_mismatch_rate(risk_df),
                    "sample_count": len(method_df),
                }
            )
    return pd.DataFrame(rows)


def _all_risk_level_effectiveness(decision_frames: List[pd.DataFrame], samples_df: pd.DataFrame) -> pd.DataFrame:
    rows: List[pd.DataFrame] = []
    for df in decision_frames:
        for method, method_df in df.groupby("method", sort=False):
            eff = risk_level_effectiveness(method_df, samples_df)
            if not eff.empty:
                eff.insert(0, "method", method)
                rows.append(eff)
    if not rows:
        return pd.DataFrame(columns=["method", "risk_level", "sample_count", "accuracy", "error_rate"])
    return pd.concat(rows, ignore_index=True)


def _answer_map(df: pd.DataFrame) -> Dict[str, str]:
    if df.empty or "sample_id" not in df.columns or "final_answer" not in df.columns:
        return {}
    return {str(row["sample_id"]): _safe_str(row.get("final_answer", "")) for row in df.to_dict(orient="records")}


def _outputs_by_sample(outputs_df: pd.DataFrame) -> Dict[str, List[Dict[str, Any]]]:
    if outputs_df.empty or "sample_id" not in outputs_df.columns:
        return {}
    return {
        str(sample_id): group.to_dict(orient="records")
        for sample_id, group in outputs_df.groupby("sample_id", sort=False)
    }


def _model_answers_json(rows: List[Dict[str, Any]]) -> str:
    compact = [
        {
            "model": row.get("model", row.get("provider", row.get("model_name", ""))),
            "answer": row.get("answer", ""),
            "confidence": row.get("confidence", ""),
        }
        for row in rows
    ]
    return json.dumps(compact, ensure_ascii=False)


def _error_cases(
    samples_df: pd.DataFrame,
    outputs_df: pd.DataFrame,
    risk_df: pd.DataFrame,
    majority_df: pd.DataFrame,
    dynamic_df: pd.DataFrame,
) -> pd.DataFrame:
    risk_by_sample = {str(row["sample_id"]): row for row in risk_df.to_dict(orient="records")}
    majority_answers = _answer_map(majority_df)
    dynamic_answers = _answer_map(dynamic_df)
    outputs_map = _outputs_by_sample(outputs_df)

    rows: List[Dict[str, Any]] = []
    for sample in samples_df.to_dict(orient="records"):
        sample_id = str(sample.get("id", ""))
        gold_answer = sample.get("gold_answer", "")
        gold_label = sample.get("gold_label", "")
        majority_answer = majority_answers.get(sample_id, "")
        dynamic_answer = dynamic_answers.get(sample_id, "")
        majority_wrong = majority_answer and not is_correct(majority_answer, gold_answer, gold_label)
        dynamic_wrong = dynamic_answer and not is_correct(dynamic_answer, gold_answer, gold_label)
        risk_labels = str(risk_by_sample.get(sample_id, {}).get("risk_labels", ""))
        noteworthy_risk = risk_labels and risk_labels != "true_consensus" and risk_labels != "normal"
        if not (majority_wrong or dynamic_wrong or noteworthy_risk):
            continue

        notes: List[str] = []
        if majority_wrong:
            notes.append("majority_wrong")
        if dynamic_wrong:
            notes.append("dynamic_wrong")
        if noteworthy_risk:
            notes.append("risk_case")

        rows.append(
            {
                "sample_id": sample_id,
                "question": sample.get("question", ""),
                "gold_answer": gold_answer,
                "risk_labels": risk_labels,
                "majority_answer": majority_answer,
                "dynamic_answer": dynamic_answer,
                "model_answers": _model_answers_json(outputs_map.get(sample_id, [])),
                "notes": ";".join(notes),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "sample_id",
            "question",
            "gold_answer",
            "risk_labels",
            "majority_answer",
            "dynamic_answer",
            "model_answers",
            "notes",
        ],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate decision results and risk labels.")
    parser.add_argument("--samples", type=Path, default=Path("data/processed/clean_dataset.csv"))
    parser.add_argument("--outputs", type=Path, default=Path("data/outputs/model_outputs.csv"))
    parser.add_argument("--majority", type=Path, default=Path("data/results/majority_vote_results.csv"))
    parser.add_argument("--dynamic", type=Path, default=Path("data/results/dynamic_decision_results.csv"))
    parser.add_argument("--learned_meta", type=Path, default=Path("data/results/learned_meta_judge_results.csv"))
    parser.add_argument("--fixed_judge", type=Path, default=Path("data/results/fixed_judge_results.csv"))
    parser.add_argument("--include_learned_meta", action="store_true", help="Include the experimental learned-meta variant in auxiliary metrics.")
    parser.add_argument("--risk_labels_out", type=Path, default=DEFAULT_RISK_LABELS_OUT)
    parser.add_argument("--method_metrics_out", type=Path, default=DEFAULT_METHOD_METRICS_OUT)
    parser.add_argument("--risk_effectiveness_out", type=Path, default=DEFAULT_RISK_EFFECTIVENESS_OUT)
    parser.add_argument("--error_cases_out", type=Path, default=DEFAULT_ERROR_CASES_OUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    samples_df = _read_table(args.samples)
    outputs_df = _read_table(args.outputs)

    risk_df = label_risks(samples_df, outputs_df)
    _write_csv(risk_df, args.risk_labels_out)

    decision_frames = _load_decision_frames(args)
    metrics_df = _method_metrics(decision_frames, samples_df, risk_df)
    _write_csv(metrics_df, args.method_metrics_out)

    effectiveness_df = _all_risk_level_effectiveness(decision_frames, samples_df)
    _write_csv(effectiveness_df, args.risk_effectiveness_out)

    majority_df = _read_table(args.majority, required=False)
    dynamic_df = _read_table(args.dynamic, required=False)
    error_df = _error_cases(samples_df, outputs_df, risk_df, majority_df, dynamic_df)
    _write_csv(error_df, args.error_cases_out)

    print(f"Wrote risk labels to {args.risk_labels_out}")
    print(f"Wrote method metrics to {args.method_metrics_out}")
    print(f"Wrote risk-level effectiveness to {args.risk_effectiveness_out}")
    print(f"Wrote error cases to {args.error_cases_out}")


if __name__ == "__main__":
    main()
