from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from dotenv import load_dotenv

from src.literary_feedback import (
    adjudicate_literary_feedback,
    generate_demo_literary_feedback,
    literary_routing_summary,
    load_literary_kg,
    retrieve_literary_knowledge,
    run_live_literary_reviewers,
)
from src.llm.clients import PROVIDER_CONFIG


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ScriptModelConfig:
    provider: str
    api_key: str
    base_url: str
    model: str
    enabled: bool = True


def _load_env(env_path: Path | None = None) -> None:
    candidates = [env_path] if env_path else [ROOT / ".env", ROOT.parent.parent / ".env", ROOT.parent.parent.parent / ".env"]
    for path in candidates:
        if path and path.exists():
            load_dotenv(path)
            return


def build_configs(providers: List[str]) -> List[ScriptModelConfig]:
    configs: List[ScriptModelConfig] = []
    for provider in providers:
        cfg = PROVIDER_CONFIG[provider]
        api_key = os.getenv(cfg["api_key"], "")
        configs.append(
            ScriptModelConfig(
                provider=provider,
                api_key=api_key,
                base_url=os.getenv(cfg["base_url"], cfg["default_base_url"]).rstrip("/"),
                model=os.getenv(cfg["model"], cfg["default_model"]),
                enabled=bool(api_key),
            )
        )
    return configs


def run_benchmark(args: argparse.Namespace) -> pd.DataFrame:
    _load_env(Path(args.env) if args.env else None)
    benchmark = pd.read_csv(args.benchmark)
    kg = load_literary_kg(args.knowledge)
    configs = build_configs(args.providers.split(",")) if args.live else []
    rows: List[Dict[str, Any]] = []
    raw_records: List[Dict[str, Any]] = []

    for _, sample in benchmark.head(args.limit or len(benchmark)).iterrows():
        essay = str(sample["essay"])
        kg_rows = retrieve_literary_knowledge(essay, kg, limit=16)
        reviewer_results = []
        if args.live:
            live_result = run_live_literary_reviewers(configs, essay, kg_rows)
            feedback = live_result.get("feedback", [])
            reviewer_results = live_result.get("reviewer_results", [])
            if not feedback:
                feedback = generate_demo_literary_feedback(essay, kg)
        else:
            feedback = generate_demo_literary_feedback(essay, kg)
        decisions = adjudicate_literary_feedback(feedback)
        summary = literary_routing_summary(decisions)
        rows.append(
            {
                "id": sample["id"],
                "focus": sample["focus"],
                "reviewer_source": "live_api" if args.live else "deterministic",
                **summary,
            }
        )
        raw_records.append(
            {
                "id": sample["id"],
                "essay": essay,
                "kg_rows": kg_rows,
                "feedback": feedback,
                "decisions": decisions,
                "reviewer_results": [
                    {
                        "provider": item.get("provider", ""),
                        "model": item.get("model", ""),
                        "reviewer_role": item.get("reviewer_role", ""),
                        "feedback_items": len(item.get("feedback", [])),
                        "request_error": item.get("request_error", ""),
                        "parse_error": item.get("parse_error", ""),
                        "latency_sec": item.get("latency_sec", 0.0),
                    }
                    for item in reviewer_results
                ],
            }
        )

    metrics = pd.DataFrame(rows)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(args.output, index=False)
    if args.raw_output:
        Path(args.raw_output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.raw_output).write_text(json.dumps(raw_records, ensure_ascii=False, indent=2), encoding="utf-8")
    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the ESL literary feedback routing benchmark.")
    parser.add_argument("--benchmark", default=str(ROOT / "data" / "literary_feedback" / "benchmark.csv"))
    parser.add_argument("--knowledge", default=str(ROOT / "data" / "knowledge" / "literary_kg_triples.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "results" / "literary_feedback_routing_metrics.csv"))
    parser.add_argument("--raw-output", default=str(ROOT / "data" / "results" / "literary_feedback_live_records.json"))
    parser.add_argument("--env", default="")
    parser.add_argument("--providers", default="deepseek,qwen,glm,kimi")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--live", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    df = run_benchmark(parse_args())
    print(df.to_string(index=False))
