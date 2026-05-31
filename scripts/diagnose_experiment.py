from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluation.metrics import is_correct


PATHS = {
    "samples": ROOT / "data" / "processed" / "clean_dataset.csv",
    "outputs": ROOT / "data" / "outputs" / "model_outputs.csv",
    "majority": ROOT / "data" / "results" / "majority_vote_results.csv",
    "dynamic": ROOT / "data" / "results" / "dynamic_decision_results.csv",
    "metrics": ROOT / "data" / "results" / "method_metrics.csv",
    "risk_labels": ROOT / "data" / "results" / "risk_labels.csv",
    "risk_effectiveness": ROOT / "data" / "results" / "risk_level_effectiveness.csv",
    "error_cases": ROOT / "data" / "results" / "error_cases.csv",
    "report": ROOT / "data" / "results" / "diagnosis_report.md",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose an experiment run and write a Markdown report.")
    parser.add_argument("--samples", type=Path, default=PATHS["samples"])
    parser.add_argument("--outputs", type=Path, default=PATHS["outputs"])
    parser.add_argument("--majority", type=Path, default=PATHS["majority"])
    parser.add_argument("--dynamic", type=Path, default=PATHS["dynamic"])
    parser.add_argument("--metrics", type=Path, default=PATHS["metrics"])
    parser.add_argument("--risk_labels", type=Path, default=PATHS["risk_labels"])
    parser.add_argument("--risk_effectiveness", type=Path, default=PATHS["risk_effectiveness"])
    parser.add_argument("--error_cases", type=Path, default=PATHS["error_cases"])
    parser.add_argument("--report", type=Path, default=PATHS["report"])
    return parser.parse_args()


def read_csv_optional(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def markdown_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df.empty:
        return "暂无数据。"
    return df.head(max_rows).to_markdown(index=False)


def dataset_summary(samples: pd.DataFrame) -> pd.DataFrame:
    if samples.empty:
        return pd.DataFrame(columns=["dataset", "sample_count"])
    if "dataset" not in samples.columns:
        return pd.DataFrame([{"dataset": "unknown", "sample_count": len(samples)}])
    return samples.groupby("dataset").size().reset_index(name="sample_count")


def model_output_summary(outputs: pd.DataFrame) -> pd.DataFrame:
    columns = ["model", "success_count", "json_parse_failed_count", "avg_confidence"]
    if outputs.empty or "model" not in outputs.columns:
        return pd.DataFrame(columns=columns)
    df = outputs.copy()
    df["parse_error"] = df.get("parse_error", "").fillna("").astype(str)
    df["success"] = df["parse_error"].str.strip() == ""
    df["json_parse_failed"] = ~df["success"]
    df["confidence_num"] = pd.to_numeric(df.get("confidence", 0.0), errors="coerce")
    summary = (
        df.groupby("model")
        .agg(
            success_count=("success", "sum"),
            json_parse_failed_count=("json_parse_failed", "sum"),
            avg_confidence=("confidence_num", "mean"),
        )
        .reset_index()
    )
    summary["avg_confidence"] = summary["avg_confidence"].fillna(0.0).round(4)
    return summary[columns]


def accuracy_by_method(metrics: pd.DataFrame) -> pd.DataFrame:
    if metrics.empty or "method" not in metrics.columns or "accuracy" not in metrics.columns:
        return pd.DataFrame(columns=["method", "accuracy"])
    return metrics[["method", "accuracy"]].copy()


def majority_dynamic_gap(metrics: pd.DataFrame) -> Dict[str, Any]:
    if metrics.empty or not {"method", "accuracy"}.issubset(metrics.columns):
        return {"majority_accuracy": None, "dynamic_accuracy": None, "gap": None}
    by_method = {str(row["method"]): safe_float(row["accuracy"]) for row in metrics.to_dict(orient="records")}
    majority = by_method.get("majority_vote")
    dynamic = by_method.get("dynamic_decision")
    gap = None if majority is None or dynamic is None else dynamic - majority
    return {"majority_accuracy": majority, "dynamic_accuracy": dynamic, "gap": gap}


def risk_distribution(risk_labels: pd.DataFrame) -> pd.DataFrame:
    if risk_labels.empty or "risk_labels" not in risk_labels.columns:
        return pd.DataFrame(columns=["risk_type", "count"])
    labels: List[str] = []
    for item in risk_labels["risk_labels"].fillna(""):
        labels.extend([label.strip() for label in str(item).split(";") if label.strip()])
    if not labels:
        return pd.DataFrame(columns=["risk_type", "count"])
    return pd.Series(labels).value_counts().reset_index(name="count").rename(columns={"index": "risk_type"})


def risk_error_rates(effectiveness: pd.DataFrame) -> pd.DataFrame:
    if effectiveness.empty or not {"risk_level", "error_rate"}.issubset(effectiveness.columns):
        return pd.DataFrame(columns=["risk_level", "error_rate"])
    df = effectiveness.copy()
    if "method" in df.columns:
        df = df.groupby("risk_level", as_index=False)["error_rate"].mean()
    return df[["risk_level", "error_rate"]]


def random_error_cases(error_cases: pd.DataFrame, n: int = 5, seed: int = 42) -> pd.DataFrame:
    if error_cases.empty:
        return error_cases
    take = min(n, len(error_cases))
    return error_cases.sample(n=take, random_state=seed)


def infer_error_cases(samples: pd.DataFrame, majority: pd.DataFrame, dynamic: pd.DataFrame, outputs: pd.DataFrame) -> pd.DataFrame:
    if samples.empty:
        return pd.DataFrame()
    majority_map = {
        str(row["sample_id"]): row.get("final_answer", "")
        for row in majority.to_dict(orient="records")
    } if not majority.empty and "sample_id" in majority.columns else {}
    dynamic_map = {
        str(row["sample_id"]): row.get("final_answer", "")
        for row in dynamic.to_dict(orient="records")
    } if not dynamic.empty and "sample_id" in dynamic.columns else {}
    outputs_map = {
        str(sample_id): group.to_dict(orient="records")
        for sample_id, group in outputs.groupby("sample_id")
    } if not outputs.empty and "sample_id" in outputs.columns else {}

    rows = []
    for sample in samples.to_dict(orient="records"):
        sample_id = str(sample.get("id", ""))
        gold_answer = sample.get("gold_answer", "")
        gold_label = sample.get("gold_label", "")
        majority_answer = majority_map.get(sample_id, "")
        dynamic_answer = dynamic_map.get(sample_id, "")
        majority_wrong = majority_answer and not is_correct(majority_answer, gold_answer, gold_label)
        dynamic_wrong = dynamic_answer and not is_correct(dynamic_answer, gold_answer, gold_label)
        if not (majority_wrong or dynamic_wrong):
            continue
        rows.append(
            {
                "sample_id": sample_id,
                "question": sample.get("question", ""),
                "gold_answer": gold_answer,
                "majority_answer": majority_answer,
                "dynamic_answer": dynamic_answer,
                "model_answers": json.dumps(
                    [
                        {"model": r.get("model", ""), "answer": r.get("answer", ""), "confidence": r.get("confidence", "")}
                        for r in outputs_map.get(sample_id, [])
                    ],
                    ensure_ascii=False,
                ),
                "notes": ";".join(
                    [name for name, flag in [("majority_wrong", majority_wrong), ("dynamic_wrong", dynamic_wrong)] if flag]
                ),
            }
        )
    return pd.DataFrame(rows)


def expansion_recommendation(
    samples: pd.DataFrame,
    outputs: pd.DataFrame,
    model_summary: pd.DataFrame,
    metrics: pd.DataFrame,
    risk_dist: pd.DataFrame,
) -> tuple[bool, List[str]]:
    reasons: List[str] = []
    sample_count = len(samples)
    if sample_count < 20:
        reasons.append(f"当前样本数为 {sample_count}，建议先完成约 30 条小实验再扩大。")
    else:
        reasons.append(f"当前样本数为 {sample_count}，已接近/达到小实验规模。")

    if outputs.empty:
        reasons.append("缺少模型输出，暂不建议扩大。")
        return False, reasons

    total_outputs = len(outputs)
    success_outputs = int((outputs.get("parse_error", "").fillna("").astype(str).str.strip() == "").sum())
    success_rate = success_outputs / total_outputs if total_outputs else 0.0
    reasons.append(f"模型输出成功率为 {success_rate:.1%}。")

    methods = set(metrics["method"].astype(str)) if not metrics.empty and "method" in metrics.columns else set()
    has_core_methods = {"majority_vote", "dynamic_decision"}.issubset(methods)
    reasons.append("已生成多数投票和动态裁决指标。" if has_core_methods else "缺少多数投票或动态裁决指标。")

    if not risk_dist.empty:
        reasons.append("风险标签已生成，可用于错误分析。")
    else:
        reasons.append("风险类型分布缺失。")

    ok = success_rate >= 0.8 and has_core_methods and not risk_dist.empty and sample_count >= 20
    if ok:
        reasons.append("结论：可以扩大到 300 条样本。")
    else:
        reasons.append("结论：暂不建议直接扩大到 300 条，建议先修复上述问题。")
    return ok, reasons


def build_report(paths: Dict[str, Path] | None = None) -> str:
    paths = paths or PATHS
    samples = read_csv_optional(paths["samples"])
    outputs = read_csv_optional(paths["outputs"])
    majority = read_csv_optional(paths["majority"])
    dynamic = read_csv_optional(paths["dynamic"])
    metrics = read_csv_optional(paths["metrics"])
    risk_labels = read_csv_optional(paths["risk_labels"])
    effectiveness = read_csv_optional(paths["risk_effectiveness"])
    error_cases = read_csv_optional(paths["error_cases"])

    ds_summary = dataset_summary(samples)
    model_summary = model_output_summary(outputs)
    method_acc = accuracy_by_method(metrics)
    gap = majority_dynamic_gap(metrics)
    risk_dist = risk_distribution(risk_labels)
    risk_err = risk_error_rates(effectiveness)
    if error_cases.empty:
        error_cases = infer_error_cases(samples, majority, dynamic, outputs)
    case_sample = random_error_cases(error_cases, n=5)
    can_expand, expand_reasons = expansion_recommendation(samples, outputs, model_summary, metrics, risk_dist)

    gap_text = "暂无数据"
    if gap["gap"] is not None:
        gap_text = (
            f"多数投票 Accuracy={gap['majority_accuracy']:.4f}，"
            f"动态裁决 Accuracy={gap['dynamic_accuracy']:.4f}，"
            f"差异={gap['gap']:+.4f}"
        )

    report = f"""# 小规模实验诊断报告

## 1. 数据集样本数量

总样本数：{len(samples)}

{markdown_table(ds_summary)}

## 2. 每个模型成功回答数量、JSON 解析失败数量、平均置信度

{markdown_table(model_summary)}

## 3. 各方法准确率

{markdown_table(method_acc)}

## 4. 多数投票 vs 动态裁决准确率差异

{gap_text}

## 5. 风险类型分布

{markdown_table(risk_dist)}

## 6. 低/中/高风险组错误率

{markdown_table(risk_err)}

## 7. 随机展示 5 个典型错误案例

{markdown_table(case_sample, max_rows=5)}

## 8. 是否可以扩大到 300 条样本

判断：{"可以扩大" if can_expand else "暂不建议扩大"}

""" + "\n".join(f"- {reason}" for reason in expand_reasons) + "\n"

    return report


def print_summary(report: str, report_path: Path = PATHS["report"]) -> None:
    lines = report.splitlines()
    keep_prefixes = [
        "总样本数：",
        "多数投票 Accuracy=",
        "判断：",
        "- 模型输出成功率",
        "- 结论：",
    ]
    print("===== 实验诊断摘要 =====")
    for line in lines:
        if any(line.startswith(prefix) for prefix in keep_prefixes):
            print(line)
    print(f"完整报告：{report_path}")


def main() -> None:
    args = parse_args()
    paths = {
        "samples": args.samples,
        "outputs": args.outputs,
        "majority": args.majority,
        "dynamic": args.dynamic,
        "metrics": args.metrics,
        "risk_labels": args.risk_labels,
        "risk_effectiveness": args.risk_effectiveness,
        "error_cases": args.error_cases,
        "report": args.report,
    }
    report = build_report(paths)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print_summary(report, args.report)


if __name__ == "__main__":
    main()
