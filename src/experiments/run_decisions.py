from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from src.decision.baselines import fixed_judge_decision, majority_vote
from src.decision.dynamic_decision import dynamic_decision, estimate_model_reliability, learned_meta_judge_decision
from src.llm.clients import get_client


DEFAULT_MAJORITY_OUT = Path("data/results/majority_vote_results.csv")
DEFAULT_DYNAMIC_OUT = Path("data/results/dynamic_decision_results.csv")
DEFAULT_FIXED_JUDGE_OUT = Path("data/results/fixed_judge_results.csv")
DEFAULT_LEARNED_META_OUT = Path("data/results/learned_meta_judge_results.csv")


def _read_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    if path.suffix.lower() == ".jsonl":
        return pd.read_json(path, lines=True)
    return pd.read_csv(path)


def _records_by_sample(outputs_df: pd.DataFrame) -> Dict[str, List[Dict[str, Any]]]:
    if "sample_id" not in outputs_df.columns:
        raise ValueError("model outputs must contain sample_id")
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for sample_id, group in outputs_df.groupby("sample_id", sort=False):
        grouped[str(sample_id)] = group.to_dict(orient="records")
    return grouped


def _samples_by_id(samples_df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    if "id" not in samples_df.columns:
        raise ValueError("samples file must contain id")
    return {str(row["id"]): row for row in samples_df.to_dict(orient="records")}


def _write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def _is_successful_fixed_judge_row(row: Dict[str, Any]) -> bool:
    final_answer = str(row.get("final_answer", "") or "").strip()
    reason = str(row.get("decision_reason", "") or "").strip()
    return bool(final_answer or reason)


def run_majority(outputs_df: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    df = majority_vote(outputs_df)
    _write_csv(df, output_path)
    return df


def run_dynamic(samples_df: pd.DataFrame, outputs_df: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    outputs_by_sample = _records_by_sample(outputs_df)
    rows: List[Dict[str, Any]] = []
    for sample in samples_df.to_dict(orient="records"):
        sample_id = str(sample.get("id", ""))
        if sample_id not in outputs_by_sample:
            continue
        rows.append(dynamic_decision(sample, outputs_by_sample.get(sample_id, [])))
    df = pd.DataFrame(rows)
    _write_csv(df, output_path)
    return df


def run_learned_meta(samples_df: pd.DataFrame, outputs_df: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    outputs_by_sample = _records_by_sample(outputs_df)
    reliability = estimate_model_reliability(samples_df, outputs_df)
    rows: List[Dict[str, Any]] = []
    for sample in samples_df.to_dict(orient="records"):
        sample_id = str(sample.get("id", ""))
        if sample_id not in outputs_by_sample:
            continue
        rows.append(learned_meta_judge_decision(sample, outputs_by_sample.get(sample_id, []), reliability))
    df = pd.DataFrame(rows)
    _write_csv(df, output_path)
    return df


def run_fixed_judge(
    samples_df: pd.DataFrame,
    outputs_df: pd.DataFrame,
    output_path: Path,
    resume: bool = False,
) -> pd.DataFrame:
    judge_client = get_client("judge")
    outputs_by_sample = _records_by_sample(outputs_df)
    samples_by_id = _samples_by_id(samples_df)

    existing_rows: List[Dict[str, Any]] = []
    completed_sample_ids: set[str] = set()
    if resume and output_path.exists():
        existing_df = _read_table(output_path)
        if not existing_df.empty and "sample_id" in existing_df.columns:
            for row in existing_df.to_dict(orient="records"):
                sample_id = str(row.get("sample_id", ""))
                if sample_id in samples_by_id and _is_successful_fixed_judge_row(row):
                    existing_rows.append(row)
                    completed_sample_ids.add(sample_id)

    rows: List[Dict[str, Any]] = []
    for sample_id, sample in samples_by_id.items():
        if sample_id in completed_sample_ids:
            continue
        rows.append(fixed_judge_decision(sample, outputs_by_sample.get(sample_id, []), judge_client))
        partial_df = pd.DataFrame(
            existing_rows + rows,
            columns=["sample_id", "method", "final_answer", "decision_reason", "risk_level", "confidence"],
        )
        _write_csv(partial_df, output_path)

    df = pd.DataFrame(
        existing_rows + rows,
        columns=["sample_id", "method", "final_answer", "decision_reason", "risk_level", "confidence"],
    )
    _write_csv(df, output_path)
    return df


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run majority, dynamic, and optional fixed-judge decisions.")
    parser.add_argument("--samples", type=Path, default=Path("data/processed/clean_dataset.csv"))
    parser.add_argument("--outputs", type=Path, default=Path("data/outputs/model_outputs.csv"))
    parser.add_argument("--majority_out", type=Path, default=DEFAULT_MAJORITY_OUT)
    parser.add_argument("--dynamic_out", type=Path, default=DEFAULT_DYNAMIC_OUT)
    parser.add_argument("--fixed_judge_out", type=Path, default=DEFAULT_FIXED_JUDGE_OUT)
    parser.add_argument("--learned_meta_out", type=Path, default=DEFAULT_LEARNED_META_OUT)
    parser.add_argument("--run_majority", action="store_true")
    parser.add_argument("--run_dynamic", action="store_true")
    parser.add_argument("--run_learned_meta", action="store_true", help="Run the experimental learned-meta variant; not part of the main demo claim.")
    parser.add_argument("--run_judge", action="store_true")
    parser.add_argument("--resume_judge", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    samples_df = _read_table(args.samples)
    outputs_df = _read_table(args.outputs)

    run_any = args.run_majority or args.run_dynamic or args.run_learned_meta or args.run_judge
    run_majority_flag = args.run_majority or not run_any
    run_dynamic_flag = args.run_dynamic or not run_any
    run_learned_meta_flag = args.run_learned_meta

    if run_majority_flag:
        majority_df = run_majority(outputs_df, args.majority_out)
        print(f"Wrote {len(majority_df)} rows to {args.majority_out}")
    if run_dynamic_flag:
        dynamic_df = run_dynamic(samples_df, outputs_df, args.dynamic_out)
        print(f"Wrote {len(dynamic_df)} rows to {args.dynamic_out}")
    if run_learned_meta_flag:
        learned_df = run_learned_meta(samples_df, outputs_df, args.learned_meta_out)
        print(f"Wrote {len(learned_df)} rows to {args.learned_meta_out}")
    if args.run_judge:
        judge_df = run_fixed_judge(samples_df, outputs_df, args.fixed_judge_out, resume=args.resume_judge)
        print(f"Wrote {len(judge_df)} rows to {args.fixed_judge_out}")


if __name__ == "__main__":
    main()
