from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "data" / "results"
FIGURES_DIR = ROOT / "reports" / "figures"


def configure_chinese_font() -> None:
    plt.rcParams["font.sans-serif"] = [
        "PingFang SC",
        "Heiti SC",
        "Songti SC",
        "Microsoft YaHei",
        "SimHei",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False


def warn_skip(message: str) -> None:
    print(f"[warning] {message}")


def read_csv_optional(path: Path) -> pd.DataFrame:
    if not path.exists():
        warn_skip(f"缺少数据文件，跳过：{path}")
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception as exc:
        warn_skip(f"读取失败，跳过：{path} ({exc})")
        return pd.DataFrame()


def save_current_figure(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=220)
    plt.close()
    print(f"已保存图表：{path}")


def plot_methods_accuracy(method_metrics: pd.DataFrame, out_dir: Path) -> None:
    if method_metrics.empty or not {"method", "accuracy"}.issubset(method_metrics.columns):
        warn_skip("method_metrics.csv 缺少 method/accuracy 字段，跳过 methods_accuracy_bar.png")
        return
    df = method_metrics[["method", "accuracy"]].dropna()
    if df.empty:
        warn_skip("方法准确率数据为空，跳过 methods_accuracy_bar.png")
        return

    plt.figure(figsize=(8, 5))
    plt.bar(df["method"].astype(str), df["accuracy"].astype(float), color="#4C78A8")
    plt.ylim(0, 1)
    plt.title("不同方法 Accuracy 对比")
    plt.xlabel("方法")
    plt.ylabel("Accuracy")
    plt.xticks(rotation=25, ha="right")
    save_current_figure(out_dir / "methods_accuracy_bar.png")


def split_risk_labels(labels: Iterable[str]) -> list[str]:
    out: list[str] = []
    for item in labels:
        for label in str(item or "").split(";"):
            label = label.strip()
            if label:
                out.append(label)
    return out


def plot_risk_type_distribution(risk_labels: pd.DataFrame, out_dir: Path) -> None:
    if risk_labels.empty or "risk_labels" not in risk_labels.columns:
        warn_skip("risk_labels.csv 缺少 risk_labels 字段，跳过 risk_type_distribution.png")
        return
    labels = split_risk_labels(risk_labels["risk_labels"].fillna(""))
    if not labels:
        warn_skip("风险标签为空，跳过 risk_type_distribution.png")
        return
    counts = pd.Series(labels).value_counts()

    plt.figure(figsize=(9, 5))
    plt.bar(counts.index.astype(str), counts.values, color="#F58518")
    plt.title("风险类型分布")
    plt.xlabel("风险类型")
    plt.ylabel("样本数")
    plt.xticks(rotation=25, ha="right")
    save_current_figure(out_dir / "risk_type_distribution.png")


def plot_risk_level_error_rate(effectiveness: pd.DataFrame, out_dir: Path) -> None:
    required = {"risk_level", "error_rate"}
    if effectiveness.empty or not required.issubset(effectiveness.columns):
        warn_skip("risk_level_effectiveness.csv 缺少 risk_level/error_rate 字段，跳过 risk_level_error_rate.png")
        return

    df = effectiveness.copy()
    if "method" in df.columns:
        df = df.groupby("risk_level", as_index=False)["error_rate"].mean()
    order = ["low", "medium", "high"]
    df["risk_level"] = pd.Categorical(df["risk_level"], categories=order, ordered=True)
    df = df.sort_values("risk_level").dropna(subset=["risk_level"])
    if df.empty:
        warn_skip("风险等级错误率数据为空，跳过 risk_level_error_rate.png")
        return

    plt.figure(figsize=(7, 5))
    plt.bar(df["risk_level"].astype(str), df["error_rate"].astype(float), color="#E45756")
    plt.ylim(0, 1)
    plt.title("低/中/高风险组错误率")
    plt.xlabel("风险等级")
    plt.ylabel("错误率")
    save_current_figure(out_dir / "risk_level_error_rate.png")


def plot_reliability_score_distribution(dynamic_results: pd.DataFrame, out_dir: Path) -> None:
    if dynamic_results.empty or "reliability_score" not in dynamic_results.columns:
        warn_skip("dynamic_decision_results.csv 缺少 reliability_score 字段，跳过 reliability_score_distribution.png")
        return
    scores = pd.to_numeric(dynamic_results["reliability_score"], errors="coerce").dropna()
    if scores.empty:
        warn_skip("可靠性评分为空，跳过 reliability_score_distribution.png")
        return

    plt.figure(figsize=(8, 5))
    plt.hist(scores, bins=10, color="#72B7B2", edgecolor="white")
    plt.title("动态裁决可靠性评分分布")
    plt.xlabel("可靠性评分")
    plt.ylabel("样本数")
    save_current_figure(out_dir / "reliability_score_distribution.png")


def plot_agreement_vs_correctness(dynamic_results: pd.DataFrame, samples: pd.DataFrame, out_dir: Path) -> None:
    if dynamic_results.empty or "agreement_rate" not in dynamic_results.columns:
        warn_skip("缺少 agreement_rate 字段，跳过 agreement_vs_correctness.png")
        return
    if samples.empty or "id" not in samples.columns:
        warn_skip("缺少样本文件或 id 字段，跳过 agreement_vs_correctness.png")
        return

    from src.evaluation.metrics import is_correct

    gold_map = {
        str(row["id"]): (row.get("gold_answer", ""), row.get("gold_label", ""))
        for row in samples.to_dict(orient="records")
    }
    rows = []
    for row in dynamic_results.to_dict(orient="records"):
        sample_id = str(row.get("sample_id", ""))
        if sample_id not in gold_map:
            continue
        gold_answer, gold_label = gold_map[sample_id]
        rows.append(
            {
                "agreement_rate": row.get("agreement_rate", None),
                "correct": 1 if is_correct(row.get("final_answer", ""), gold_answer, gold_label) else 0,
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        warn_skip("一致率与正确性可视化数据为空，跳过 agreement_vs_correctness.png")
        return

    plt.figure(figsize=(8, 5))
    plt.scatter(df["agreement_rate"], df["correct"], alpha=0.75, color="#54A24B")
    plt.yticks([0, 1], ["错误", "正确"])
    plt.xlim(-0.02, 1.02)
    plt.title("答案一致率与正确性关系")
    plt.xlabel("答案一致率")
    plt.ylabel("裁决是否正确")
    save_current_figure(out_dir / "agreement_vs_correctness.png")


def generate_all_figures(results_dir: Path = RESULTS_DIR, figures_dir: Path = FIGURES_DIR) -> None:
    configure_chinese_font()
    figures_dir.mkdir(parents=True, exist_ok=True)

    method_metrics = read_csv_optional(results_dir / "method_metrics.csv")
    risk_labels = read_csv_optional(results_dir / "risk_labels.csv")
    effectiveness = read_csv_optional(results_dir / "risk_level_effectiveness.csv")
    dynamic_results = read_csv_optional(results_dir / "dynamic_decision_results.csv")
    samples = read_csv_optional(ROOT / "data" / "processed" / "clean_dataset.csv")

    plot_methods_accuracy(method_metrics, figures_dir)
    plot_risk_type_distribution(risk_labels, figures_dir)
    plot_risk_level_error_rate(effectiveness, figures_dir)
    plot_reliability_score_distribution(dynamic_results, figures_dir)
    plot_agreement_vs_correctness(dynamic_results, samples, figures_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate experiment figures.")
    parser.add_argument("--results_dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--figures_dir", type=Path, default=FIGURES_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_all_figures(args.results_dir, args.figures_dir)


if __name__ == "__main__":
    main()

