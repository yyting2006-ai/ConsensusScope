from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_config, resolve_path
from src.data.dataset_loader import load_samples
from src.llm.deepseek_client import build_deepseek_client
from src.llm.glm_client import build_glm_client
from src.llm.kimi_client import build_kimi_client
from src.llm.multi_model_runner import run_models_for_samples
from src.llm.qwen_client import build_qwen_client
from src.storage.io import save_models_jsonl


CLIENT_BUILDERS = {
    "deepseek": build_deepseek_client,
    "qwen": build_qwen_client,
    "glm": build_glm_client,
    "kimi": build_kimi_client,
}


def main() -> None:
    config = load_config()
    exp = config["experiment"]
    samples = load_samples(resolve_path(exp["sample_file"]))
    kwargs = {
        "temperature": exp["temperature"],
        "max_tokens": exp["max_tokens"],
        "timeout": exp["request_timeout_sec"],
    }
    clients = [CLIENT_BUILDERS[name](**kwargs) for name in config["models"]["enabled"] if name in CLIENT_BUILDERS]
    answers = run_models_for_samples(samples, clients, max_workers=exp["max_workers"])
    save_models_jsonl(resolve_path(exp["output_file"]), answers)
    print(f"Wrote {len(answers)} model outputs to {resolve_path(exp['output_file'])}")


if __name__ == "__main__":
    main()
