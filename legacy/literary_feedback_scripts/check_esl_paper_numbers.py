from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def as_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def main() -> None:
    kg = read_csv(ROOT / "data" / "knowledge" / "literary_kg_triples.csv")
    benchmark = read_csv(ROOT / "data" / "literary_feedback" / "benchmark.csv")
    routing = read_csv(ROOT / "data" / "results" / "literary_feedback_routing_metrics.csv")
    live_routing = read_csv(ROOT / "data" / "results" / "literary_feedback_live_multimodel_metrics.csv")
    live_records = read_json(ROOT / "data" / "results" / "literary_feedback_live_multimodel_records.json") or []

    relations = Counter(row.get("relation", "") for row in kg)
    works = {row.get("work", "") for row in kg if row.get("work", "")}

    provider_summary: dict[str, dict[str, int]] = defaultdict(
        lambda: {"calls": 0, "items": 0, "errors": 0, "parse_errors": 0}
    )
    for record in live_records:
        for item in record.get("reviewer_results", []):
            provider = item.get("provider") or "unknown"
            provider_summary[provider]["calls"] += 1
            provider_summary[provider]["items"] += as_int(item.get("feedback_items"))
            provider_summary[provider]["errors"] += 1 if item.get("request_error") else 0
            provider_summary[provider]["parse_errors"] += 1 if item.get("parse_error") else 0

    print(f"Literary works: {len(works)}")
    print(f"KG triples: {len(kg)}")
    print(f"Theme triples: {relations.get('theme', 0)}")
    print(f"Character triples: {relations.get('central_character', 0)}")
    print(f"Genre triples: {relations.get('genre', 0)}")
    print(f"Author triples: {relations.get('author', 0)}")
    print(f"Publication-year triples: {relations.get('publication_year', 0)}")
    print(f"Form triples: {relations.get('form', 0)}")
    print(f"Alias triples: {relations.get('alias', 0)}")
    print(f"Benchmark essays: {len(benchmark)}")
    print(f"Adjudicated decisions: {sum(as_int(row.get('total_suggestions')) for row in routing)}")
    print(f"Auto-accepted: {sum(as_int(row.get('auto_accept')) for row in routing)}")
    print(f"Teacher review: {sum(as_int(row.get('teacher_review')) for row in routing)}")
    print(f"High risk: {sum(as_int(row.get('high_risk')) for row in routing)}")
    print(f"KG-supported: {sum(as_int(row.get('kg_supported')) for row in routing)}")
    print(f"Live validation cases: {len(live_routing)}")
    print(f"Live adjudicated decisions: {sum(as_int(row.get('total_suggestions')) for row in live_routing)}")
    print(f"Live auto-accepted: {sum(as_int(row.get('auto_accept')) for row in live_routing)}")
    print(f"Live teacher review: {sum(as_int(row.get('teacher_review')) for row in live_routing)}")
    print(f"Live high risk: {sum(as_int(row.get('high_risk')) for row in live_routing)}")
    print(f"Live KG-supported: {sum(as_int(row.get('kg_supported')) for row in live_routing)}")
    for provider in sorted(provider_summary):
        stats = provider_summary[provider]
        print(
            f"Provider {provider}: calls={stats['calls']}, items={stats['items']}, "
            f"errors={stats['errors']}, parse_errors={stats['parse_errors']}"
        )


if __name__ == "__main__":
    main()
