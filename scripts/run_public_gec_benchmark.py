#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import ssl
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import List

import pandas as pd

from src.esl_writing_feedback import route_feedback_dataframe
from src.public_gec_benchmark import (
    ParallelSentence,
    build_feedback_candidates,
    build_gold_feedback,
    combined_json_payload,
    evaluate_routing_with_gold,
    load_jfleg_directory,
    load_m2_file,
    load_parallel_csv,
    write_benchmark_report,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE = ROOT / "data" / "public_gec_sample" / "sample_parallel.csv"
DEFAULT_OUT_DIR = ROOT / "reports" / "public_gec_benchmark"


def download_jfleg(target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    urls = [
        "https://github.com/keisks/jfleg/archive/refs/heads/master.zip",
        "https://github.com/keisks/jfleg/archive/refs/heads/main.zip",
    ]
    last_error: Exception | None = None
    for url in urls:
        try:
            archive_path = target_dir / "jfleg.zip"
            try:
                with urllib.request.urlopen(url, timeout=30) as response:
                    archive_path.write_bytes(response.read())
            except Exception as exc:
                if "CERTIFICATE_VERIFY_FAILED" not in str(exc):
                    raise
                # Public GitHub archive fallback for macOS Python installs whose
                # local certificate store has not been initialized.
                context = ssl._create_unverified_context()
                with urllib.request.urlopen(url, timeout=30, context=context) as response:
                    archive_path.write_bytes(response.read())
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(target_dir)
            matches = sorted(target_dir.glob("jfleg-*"))
            if matches:
                return matches[0]
        except Exception as exc:  # pragma: no cover - network-dependent convenience path
            last_error = exc
    raise RuntimeError(f"Unable to download JFLEG from GitHub: {last_error}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run ConsensusScope review-routing evaluation on public learner-correction corpora."
    )
    parser.add_argument("--input-csv", type=Path, help="CSV with source/reference correction columns.")
    parser.add_argument("--jfleg-dir", type=Path, help="Local JFLEG checkout directory containing dev/ and test/.")
    parser.add_argument("--download-jfleg", action="store_true", help="Download JFLEG from GitHub into a temporary directory.")
    parser.add_argument("--m2-file", type=Path, action="append", default=[], help="M2 GEC file; can be supplied multiple times.")
    parser.add_argument("--m2-dataset-name", default="", help="Dataset name to use for a single --m2-file input.")
    parser.add_argument("--max-samples", type=int, default=0, help="Maximum parallel sentences to evaluate; 0 means all.")
    parser.add_argument("--no-distractors", action="store_true", help="Evaluate only gold-derived correct feedback candidates.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Output directory for CSV/JSON/Markdown reports.")
    return parser.parse_args()


def load_records(args: argparse.Namespace) -> List[ParallelSentence]:
    records: List[ParallelSentence] = []
    if args.input_csv:
        records.extend(load_parallel_csv(args.input_csv))
    if args.jfleg_dir:
        records.extend(load_jfleg_directory(args.jfleg_dir))
    temp_ctx = None
    if args.download_jfleg:
        temp_ctx = tempfile.TemporaryDirectory(prefix="consensusscope_jfleg_")
        jfleg_root = download_jfleg(Path(temp_ctx.name))
        records.extend(load_jfleg_directory(jfleg_root))
    for m2_path in args.m2_file:
        dataset = args.m2_dataset_name or m2_path.stem
        records.extend(load_m2_file(m2_path, dataset=dataset))
    if not records:
        records.extend(load_parallel_csv(DEFAULT_SAMPLE, default_dataset="synthetic_smoke"))
    if args.max_samples and args.max_samples > 0:
        records = records[: args.max_samples]
    if temp_ctx is not None:
        # Keep the temporary directory alive until loading is complete.
        temp_ctx.cleanup()
    return records


def main() -> None:
    args = parse_args()
    records = load_records(args)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    gold = build_gold_feedback(records)
    candidates = build_feedback_candidates(gold, include_distractors=not args.no_distractors)
    feedback = candidates["feedback_items"]
    evidence = candidates["review_evidence"]
    labels = candidates["gold_labels"]
    routing = route_feedback_dataframe(feedback, evidence)
    evaluation = evaluate_routing_with_gold(routing, labels)
    item_analysis = evaluation["item_analysis"]
    metrics = evaluation["metrics"]
    policy_metrics = evaluation["policy_metrics"]

    outputs = {
        "public_gec_gold_feedback": gold,
        "public_gec_feedback_candidates": feedback,
        "public_gec_review_evidence": evidence,
        "public_gec_gold_labels": labels,
        "public_gec_routing_results": routing,
        "public_gec_item_analysis": item_analysis,
        "public_gec_metrics": metrics,
        "public_gec_policy_metrics": policy_metrics,
    }
    for name, frame in outputs.items():
        frame.to_csv(args.out_dir / f"{name}.csv", index=False)
    (args.out_dir / "public_gec_combined_outputs.json").write_text(combined_json_payload(outputs), encoding="utf-8")
    write_benchmark_report(
        args.out_dir / "public_gec_report.md",
        metrics=metrics,
        policy_metrics=policy_metrics,
        records_count=len(records),
        gold_count=len(gold),
        candidate_count=len(feedback),
    )

    summary = {
        "records": len(records),
        "gold_edits": int(len(gold)),
        "feedback_candidates": int(len(feedback)),
        "out_dir": str(args.out_dir),
        "metrics": json.loads(metrics.to_json(orient="records")),
        "policy_metrics": json.loads(policy_metrics.to_json(orient="records")),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
