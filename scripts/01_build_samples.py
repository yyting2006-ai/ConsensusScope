from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_config, resolve_path
from src.data.normalizer import sample_to_record
from src.data.sample_builder import build_pilot_samples
from src.utils import write_jsonl


def main() -> None:
    config = load_config()
    output_path = resolve_path(config["experiment"]["sample_file"])
    records = [sample_to_record(sample) for sample in build_pilot_samples()]
    write_jsonl(output_path, records)
    print(f"Wrote {len(records)} pilot samples to {output_path}")


if __name__ == "__main__":
    main()
