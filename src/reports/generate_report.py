from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "data" / "results"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "reports"


def read_csv_optional(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[warning] 缺少数据文件，报告中将跳过：{path}")
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception as exc:
        print(f"[warning] 读取失败，报告中将跳过：{path} ({exc})")
        return pd.DataFrame()


def df_to_markdown(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df.empty:
        return "暂无数据。"
    return df.head(max_rows).to_markdown(index=False)


def dataset_scale_section(samples: pd.DataFrame, summary: pd.DataFrame) -> str:
    if not summary.empty:
        return df_to_markdown(summary)
    if samples.empty or "dataset" not in samples.columns:
        return "暂无数据集规模统计。"
    scale = samples.groupby("dataset").size().reset_index(name="sample_count")
    return df_to_markdown(scale)


def risk_distribution_section(risk_labels: pd.DataFrame) -> str:
    if risk_labels.empty or "risk_labels" not in risk_labels.columns:
        return "暂无风险类型统计。"
    labels: List[str] = []
    for item in risk_labels["risk_labels"].fillna(""):
        labels.extend([x.strip() for x in str(item).split(";") if x.strip()])
    if not labels:
        return "暂无风险类型统计。"
    df = pd.Series(labels).value_counts().reset_index()
    df.columns = ["risk_type", "sample_count"]
    return df_to_markdown(df)


def typical_cases_section(error_cases: pd.DataFrame) -> str:
    if error_cases.empty:
        return "暂无典型错误或风险案例。"
    cols = [
        col
        for col in ["sample_id", "question", "gold_answer", "risk_labels", "majority_answer", "dynamic_answer", "notes"]
        if col in error_cases.columns
    ]
    return df_to_markdown(error_cases[cols], max_rows=10)


def generate_report(
    output_path: Path = REPORTS_DIR / "experiment_report.md",
    results_dir: Path = RESULTS_DIR,
    processed_dir: Path = PROCESSED_DIR,
) -> None:
    samples = read_csv_optional(processed_dir / "clean_dataset.csv")
    summary = read_csv_optional(processed_dir / "dataset_summary.csv")
    method_metrics = read_csv_optional(results_dir / "method_metrics.csv")
    risk_labels = read_csv_optional(results_dir / "risk_labels.csv")
    effectiveness = read_csv_optional(results_dir / "risk_level_effectiveness.csv")
    error_cases = read_csv_optional(results_dir / "error_cases.csv")

    report = f"""# 多大模型协同决策可靠性评估实验报告

## 1. 项目简介

本项目《面向多大模型协同决策的可靠性评估与动态裁决机制研究》关注多个大语言模型在同一批公开数据集问题上的协同决策是否可靠。实验不训练大模型，而是比较单模型回答、多模型多数投票、固定裁决器和动态裁决机制的效果，并识别真实共识、虚假共识、少数派正确、高分歧不确定和置信错配等风险类型。

## 2. 数据集规模统计

{dataset_scale_section(samples, summary)}

## 3. 实验方法说明

本实验首先将 TruthfulQA、FEVER、CommonsenseQA 等数据整理为统一格式，然后调用多个大语言模型独立回答，要求模型输出答案、理由、置信度和证据。随后使用以下策略生成最终答案：

- 单模型基线：直接采用某一模型的答案。
- 多数投票：统计多个模型答案，采纳唯一最高票答案；若平票则标记为高风险。
- 固定裁决器：由指定裁决模型综合多个模型输出给出最终答案。
- 动态裁决机制：综合答案一致率、平均置信度、证据支持度、答案多样性和高置信少数派预警，计算可靠性评分并给出裁决建议。

## 4. 指标定义

- Accuracy：裁决答案与标准答案或标准标签一致的比例。
- Macro F1：对不同答案类别计算宏平均 F1。
- false_consensus_rate：多数答案一致但多数答案错误的样本比例。
- minority_correct_rate：少数模型正确而多数模型错误的样本比例。
- high_disagreement_rate：无唯一多数答案或答案分歧明显的样本比例。
- confidence_mismatch_rate：存在模型高置信但答案错误的样本比例。
- risk_level_effectiveness：统计 low、medium、high 风险组内的准确率与错误率。

## 5. 各方法结果表

{df_to_markdown(method_metrics)}

## 6. 风险类型分布

{risk_distribution_section(risk_labels)}

## 7. 风险等级有效性

{df_to_markdown(effectiveness)}

## 8. 典型案例

{typical_cases_section(error_cases)}

## 9. 初步结论

从当前实验流程看，系统已经能够完成公开数据集整理、多模型结构化回答采集、多策略裁决、风险标注、指标计算和图表/报告生成。后续应扩大样本规模，重点分析虚假共识、少数派正确和置信错配案例，并比较动态裁决机制相对于多数投票和固定裁决器是否能降低高风险错误。

## 10. 图表文件

图表默认保存在 `reports/figures/`：

- `methods_accuracy_bar.png`
- `risk_type_distribution.png`
- `risk_level_error_rate.png`
- `reliability_score_distribution.png`
- `agreement_vs_correctness.png`
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"已生成报告：{output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Markdown experiment report.")
    parser.add_argument("--output", type=Path, default=REPORTS_DIR / "experiment_report.md")
    parser.add_argument("--results_dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--processed_dir", type=Path, default=PROCESSED_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_report(args.output, args.results_dir, args.processed_dir)


if __name__ == "__main__":
    main()

