from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


plt.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti SC", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def plot_strategy_accuracy(df: pd.DataFrame, output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if df.empty or "strategy" not in df or "accuracy" not in df:
        return
    ax = df.plot(kind="bar", x="strategy", y="accuracy", legend=False, ylim=(0, 1))
    ax.set_ylabel("Accuracy")
    ax.set_xlabel("Strategy")
    ax.set_title("Strategy Accuracy Comparison")
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def plot_risk_distribution(df: pd.DataFrame, output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if df.empty or "risk_type" not in df:
        return
    counts = df["risk_type"].value_counts()
    ax = counts.plot(kind="bar")
    ax.set_ylabel("Count")
    ax.set_title("Risk Type Distribution")
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()
