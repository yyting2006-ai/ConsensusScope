from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import PROJECT_ROOT, load_config


PIPELINE = [
    "scripts/01_build_samples.py",
    "scripts/02_run_model_answers.py",
    "scripts/03_run_adjudication.py",
    "scripts/04_compute_metrics.py",
    "scripts/05_generate_figures.py",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Only validate config and print planned steps.")
    args = parser.parse_args()

    config = load_config()
    print(f"Project: {config['project']['name']}")
    print("Pipeline:")
    for step in PIPELINE:
        print(f"- {step}")

    if args.dry_run:
        return

    for step in PIPELINE:
        subprocess.run([sys.executable, str(PROJECT_ROOT / step)], cwd=PROJECT_ROOT, check=True)


if __name__ == "__main__":
    main()
