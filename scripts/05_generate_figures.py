from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_config, resolve_path
from src.visualization.plots import plot_risk_distribution


def main() -> None:
    config = load_config()
    adjudication_path = resolve_path(config["experiment"]["adjudication_file"])
    figure_path = resolve_path(config["paths"]["figures_dir"]) / "risk_distribution.png"
    if not adjudication_path.exists():
        print(f"Missing adjudication file: {adjudication_path}")
        return
    df = pd.read_csv(adjudication_path)
    plot_risk_distribution(df, figure_path)
    print(f"Wrote figure to {figure_path}")


if __name__ == "__main__":
    main()
