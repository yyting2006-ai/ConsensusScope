from __future__ import annotations

import argparse
import json
import pickle
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.decision.baselines import majority_vote
from src.decision.dynamic_decision import dynamic_decision
from src.evaluation.metrics import is_correct


FEATURE_COLUMNS = [
    "agreement_rate",
    "avg_confidence",
    "confidence_std",
    "evidence_support_score",
    "answer_diversity",
    "minority_warning",
    "max_vote_count",
    "model_count",
]

METRIC_COLUMNS = [
    "label_source",
    "model_type",
    "accuracy",
    "precision",
    "recall",
    "f1",
    "roc_auc",
    "train_count",
    "test_count",
    "positive_rate",
    "feature_importance",
    "model_path",
]


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        value_float = float(value)
    except Exception:
        return default
    if np.isnan(value_float) or np.isinf(value_float):
        return default
    return value_float


def _valid_outputs(group: pd.DataFrame) -> pd.DataFrame:
    df = group.copy()
    if "parse_error" in df.columns:
        df = df[df["parse_error"].map(_safe_str) == ""]
    elif "parse_ok" in df.columns:
        df = df[df["parse_ok"].astype(str).str.lower().isin(["true", "1", "yes"])]
    if "answer" not in df.columns:
        return pd.DataFrame(columns=df.columns)
    return df[df["answer"].map(_safe_str) != ""]


def _evidence_present(value: Any) -> bool:
    text = _safe_str(value).lower()
    return bool(text and text not in {"无", "none", "null", "unknown", "n/a", "na"})


def _feature_row(sample: Dict[str, Any], outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    valid = [row for row in outputs if _safe_str(row.get("answer", ""))]
    model_count = len(valid)
    if model_count == 0:
        return {
            "sample_id": _safe_str(sample.get("id", "")),
            "agreement_rate": 0.0,
            "avg_confidence": 0.0,
            "confidence_std": 0.0,
            "evidence_support_score": 0.0,
            "answer_diversity": 0.0,
            "minority_warning": 0,
            "max_vote_count": 0,
            "model_count": 0,
        }

    answers = [_safe_str(row.get("answer", "")) for row in valid]
    counts = Counter(answers)
    max_vote_count = counts.most_common(1)[0][1] if counts else 0
    agreement_rate = max_vote_count / model_count if model_count else 0.0
    confidences = [_safe_float(row.get("confidence", 0.0)) for row in valid]
    avg_confidence = float(np.mean(confidences)) if confidences else 0.0
    confidence_std = float(np.std(confidences, ddof=0)) if confidences else 0.0
    evidence_support_score = sum(1.0 for row in valid if _evidence_present(row.get("evidence", ""))) / model_count
    answer_diversity = len(counts) / model_count if model_count else 0.0

    majority_answer = counts.most_common(1)[0][0]
    majority_confidences = [
        _safe_float(row.get("confidence", 0.0))
        for row in valid
        if _safe_str(row.get("answer", "")) == majority_answer
    ]
    minority_confidences = [
        _safe_float(row.get("confidence", 0.0))
        for row in valid
        if _safe_str(row.get("answer", "")) != majority_answer
    ]
    majority_avg = float(np.mean(majority_confidences)) if majority_confidences else 0.0
    minority_max = max(minority_confidences) if minority_confidences else 0.0
    minority_warning = bool(minority_confidences) and minority_max >= max(0.60, majority_avg - 0.15)

    return {
        "sample_id": _safe_str(sample.get("id", "")),
        "agreement_rate": round(agreement_rate, 6),
        "avg_confidence": round(avg_confidence, 6),
        "confidence_std": round(confidence_std, 6),
        "evidence_support_score": round(evidence_support_score, 6),
        "answer_diversity": round(answer_diversity, 6),
        "minority_warning": int(minority_warning),
        "max_vote_count": int(max_vote_count),
        "model_count": int(model_count),
    }


def build_feature_table(samples_df: pd.DataFrame, outputs_df: pd.DataFrame) -> pd.DataFrame:
    """Build per-sample collaborative reliability features from model outputs."""

    outputs_by_sample: Dict[str, List[Dict[str, Any]]] = {}
    if not outputs_df.empty and "sample_id" in outputs_df.columns:
        for sample_id, group in outputs_df.groupby("sample_id", sort=False):
            outputs_by_sample[str(sample_id)] = _valid_outputs(group).to_dict(orient="records")

    rows = [
        _feature_row(sample, outputs_by_sample.get(str(sample.get("id", "")), []))
        for sample in samples_df.to_dict(orient="records")
    ]
    return pd.DataFrame(rows, columns=["sample_id", *FEATURE_COLUMNS])


def build_decision_labels(
    samples_df: pd.DataFrame,
    outputs_df: pd.DataFrame,
    label_source: str,
) -> pd.DataFrame:
    """Create correctness labels for majority_vote or dynamic_decision final answers."""

    sample_by_id = {str(row["id"]): row for row in samples_df.to_dict(orient="records")}
    label_source = label_source.lower()
    rows: List[Dict[str, Any]] = []

    if label_source == "majority_vote":
        decision_df = majority_vote(outputs_df)
        for row in decision_df.to_dict(orient="records"):
            sample = sample_by_id.get(str(row.get("sample_id", "")))
            if not sample:
                continue
            rows.append(
                {
                    "sample_id": str(row.get("sample_id", "")),
                    "final_answer": row.get("final_answer", ""),
                    "label": int(is_correct(row.get("final_answer", ""), sample.get("gold_answer", ""), sample.get("gold_label", ""))),
                }
            )
    elif label_source == "dynamic_decision":
        valid_outputs = outputs_df.copy()
        if "sample_id" not in valid_outputs.columns:
            valid_outputs["sample_id"] = ""
        grouped = {str(sample_id): group.to_dict(orient="records") for sample_id, group in valid_outputs.groupby("sample_id", sort=False)}
        for sample_id, sample in sample_by_id.items():
            decision = dynamic_decision(sample, grouped.get(sample_id, []))
            rows.append(
                {
                    "sample_id": sample_id,
                    "final_answer": decision.get("final_answer", ""),
                    "label": int(is_correct(decision.get("final_answer", ""), sample.get("gold_answer", ""), sample.get("gold_label", ""))),
                }
            )
    else:
        raise ValueError("label_source must be 'majority_vote' or 'dynamic_decision'")

    return pd.DataFrame(rows, columns=["sample_id", "final_answer", "label"])


def _split_data(df: pd.DataFrame, seed: int, test_size: float) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if len(df) < 4:
        return df.copy(), df.copy()
    labels = df["label"].astype(int)
    stratify = labels if labels.nunique() == 2 and labels.value_counts().min() >= 2 else None
    return train_test_split(df, test_size=test_size, random_state=seed, stratify=stratify)


def _metric_row(
    label_source: str,
    model_type: str,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_score: np.ndarray | None,
    train_count: int,
    feature_importance: Dict[str, float],
    model_path: Path,
) -> Dict[str, Any]:
    if y_true.size == 0:
        accuracy = precision = recall = f1 = roc_auc = 0.0
    else:
        accuracy = float(accuracy_score(y_true, y_pred))
        precision = float(precision_score(y_true, y_pred, zero_division=0))
        recall = float(recall_score(y_true, y_pred, zero_division=0))
        f1 = float(f1_score(y_true, y_pred, zero_division=0))
        roc_auc = float("nan")
        if y_score is not None and len(np.unique(y_true)) == 2:
            roc_auc = float(roc_auc_score(y_true, y_score))

    return {
        "label_source": label_source,
        "model_type": model_type,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": roc_auc,
        "train_count": int(train_count),
        "test_count": int(y_true.size),
        "positive_rate": float(np.mean(y_true)) if y_true.size else 0.0,
        "feature_importance": json.dumps(feature_importance, ensure_ascii=False),
        "model_path": str(model_path),
    }


def _fit_single_class_baseline(
    label_source: str,
    model_type: str,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    models_dir: Path,
) -> Dict[str, Any]:
    constant = int(train_df["label"].mode().iloc[0]) if not train_df.empty else 0
    y_true = test_df["label"].astype(int).to_numpy()
    y_pred = np.full_like(y_true, constant)
    y_score = np.full(y_true.shape, float(constant), dtype=float)
    model_path = models_dir / f"ml_reliability_{label_source}_{model_type}.pkl"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    with model_path.open("wb") as f:
        pickle.dump({"type": "constant_baseline", "constant": constant, "features": FEATURE_COLUMNS}, f)
    return _metric_row(label_source, model_type, y_true, y_pred, y_score, len(train_df), {}, model_path)


def _feature_importance(model_type: str, estimator: Any) -> Dict[str, float]:
    if model_type == "logistic_regression":
        clf = estimator.named_steps["classifier"]
        values = np.abs(clf.coef_[0])
    else:
        clf = estimator
        values = clf.feature_importances_
    total = float(np.sum(values))
    if total <= 0:
        return {name: 0.0 for name in FEATURE_COLUMNS}
    return {name: round(float(value / total), 6) for name, value in zip(FEATURE_COLUMNS, values)}


def train_models_for_label_source(
    dataset_df: pd.DataFrame,
    label_source: str,
    models_dir: Path,
    seed: int,
    test_size: float,
) -> List[Dict[str, Any]]:
    train_df, test_df = _split_data(dataset_df, seed=seed, test_size=test_size)
    rows: List[Dict[str, Any]] = []
    if train_df["label"].nunique() < 2:
        for model_type in ["logistic_regression", "random_forest"]:
            rows.append(_fit_single_class_baseline(label_source, model_type, train_df, test_df, models_dir))
        return rows

    x_train = train_df[FEATURE_COLUMNS].astype(float)
    y_train = train_df["label"].astype(int)
    x_test = test_df[FEATURE_COLUMNS].astype(float)
    y_test = test_df["label"].astype(int).to_numpy()

    estimators: List[Tuple[str, Any]] = [
        (
            "logistic_regression",
            Pipeline(
                [
                    ("scaler", StandardScaler()),
                    ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=seed)),
                ]
            ),
        ),
        (
            "random_forest",
            RandomForestClassifier(
                n_estimators=200,
                max_depth=4,
                min_samples_leaf=2,
                class_weight="balanced",
                random_state=seed,
            ),
        ),
    ]

    for model_type, estimator in estimators:
        estimator.fit(x_train, y_train)
        y_pred = estimator.predict(x_test)
        y_score = estimator.predict_proba(x_test)[:, 1] if hasattr(estimator, "predict_proba") else None
        model_path = models_dir / f"ml_reliability_{label_source}_{model_type}.pkl"
        model_path.parent.mkdir(parents=True, exist_ok=True)
        with model_path.open("wb") as f:
            pickle.dump({"model": estimator, "features": FEATURE_COLUMNS, "label_source": label_source}, f)
        rows.append(
            _metric_row(
                label_source=label_source,
                model_type=model_type,
                y_true=y_test,
                y_pred=y_pred,
                y_score=y_score,
                train_count=len(train_df),
                feature_importance=_feature_importance(model_type, estimator),
                model_path=model_path,
            )
        )
    return rows


def run_ml_reliability(
    samples_path: Path,
    outputs_path: Path,
    metrics_out: Path,
    models_dir: Path,
    seed: int = 42,
    test_size: float = 0.3,
) -> pd.DataFrame:
    samples_df = pd.read_csv(samples_path)
    outputs_df = pd.read_csv(outputs_path)
    feature_df = build_feature_table(samples_df, outputs_df)

    rows: List[Dict[str, Any]] = []
    for label_source in ["majority_vote", "dynamic_decision"]:
        label_df = build_decision_labels(samples_df, outputs_df, label_source)
        dataset_df = feature_df.merge(label_df[["sample_id", "label"]], on="sample_id", how="inner")
        dataset_df = dataset_df.dropna(subset=FEATURE_COLUMNS + ["label"]).copy()
        if dataset_df.empty:
            continue
        rows.extend(train_models_for_label_source(dataset_df, label_source, models_dir, seed, test_size))

    metrics_df = pd.DataFrame(rows, columns=METRIC_COLUMNS)
    metrics_out.parent.mkdir(parents=True, exist_ok=True)
    metrics_df.to_csv(metrics_out, index=False, encoding="utf-8-sig")
    return metrics_df


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train optional ML reliability models from existing experiment data.")
    parser.add_argument("--samples", type=Path, default=Path("data/processed/clean_dataset.csv"))
    parser.add_argument("--outputs", type=Path, default=Path("data/outputs/model_outputs.csv"))
    parser.add_argument("--metrics_out", type=Path, default=Path("data/results/ml_reliability_metrics.csv"))
    parser.add_argument("--models_dir", type=Path, default=Path("models"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test_size", type=float, default=0.3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metrics_df = run_ml_reliability(
        samples_path=args.samples,
        outputs_path=args.outputs,
        metrics_out=args.metrics_out,
        models_dir=args.models_dir,
        seed=args.seed,
        test_size=args.test_size,
    )
    print(f"Wrote ML reliability metrics to {args.metrics_out}")
    if metrics_df.empty:
        print("No training rows were available.")
    else:
        display_cols = ["label_source", "model_type", "accuracy", "precision", "recall", "f1", "roc_auc"]
        print(metrics_df[display_cols].to_string(index=False))


if __name__ == "__main__":
    main()
