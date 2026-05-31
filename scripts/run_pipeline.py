from __future__ import annotations

import argparse
import logging
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.dataset_builder import build_clean_dataset
from src.experiments.evaluate_results import main as evaluate_results_main
from src.experiments.run_decisions import run_dynamic, run_fixed_judge, run_majority
from src.llm.clients import get_client
from src.llm.prompts import build_answer_prompt
from src.reports.generate_figures import generate_all_figures
from src.reports.generate_report import generate_report


LOGGER = logging.getLogger("pipeline")


PATHS = {
    "samples": ROOT / "data" / "processed" / "clean_dataset.csv",
    "samples_run": ROOT / "data" / "processed" / "pipeline_samples.csv",
    "dataset_summary": ROOT / "data" / "processed" / "dataset_summary.csv",
    "model_outputs": ROOT / "data" / "outputs" / "model_outputs.csv",
    "majority": ROOT / "data" / "results" / "majority_vote_results.csv",
    "dynamic": ROOT / "data" / "results" / "dynamic_decision_results.csv",
    "fixed_judge": ROOT / "data" / "results" / "fixed_judge_results.csv",
    "risk_labels": ROOT / "data" / "results" / "risk_labels.csv",
    "method_metrics": ROOT / "data" / "results" / "method_metrics.csv",
    "risk_effectiveness": ROOT / "data" / "results" / "risk_level_effectiveness.csv",
    "error_cases": ROOT / "data" / "results" / "error_cases.csv",
    "figures": ROOT / "reports" / "figures",
    "report": ROOT / "reports" / "experiment_report.md",
}


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def require_file(path: Path, step_name: str) -> bool:
    if path.exists():
        return True
    LOGGER.warning("[%s] 缺少输入文件，跳过该步骤：%s", step_name, path)
    return False


def safe_step(name: str, fn: Callable[[], Any]) -> bool:
    LOGGER.info("========== %s ==========", name)
    try:
        fn()
        LOGGER.info("[完成] %s", name)
        return True
    except Exception as exc:
        LOGGER.error("[失败] %s：%s", name, exc)
        LOGGER.debug(traceback.format_exc())
        return False


def check_api_keys(models: List[str], run_judge: bool) -> None:
    targets = list(models)
    if run_judge:
        targets.append("judge")
    for model in targets:
        try:
            client = get_client(model)
        except Exception as exc:
            LOGGER.warning("模型 %s 配置不可用：%s", model, exc)
            continue
        if not client.is_available:
            LOGGER.warning(
                "缺少 %s API key。请检查 .env 中的对应变量；该模型调用会返回 request_error。",
                model,
            )


def build_dataset_step(sample_per_dataset: int, seed: int) -> None:
    candidate = ROOT / "data" / "processed" / "_clean_dataset_candidate.csv"
    candidate_summary = ROOT / "data" / "processed" / "_dataset_summary_candidate.csv"
    build_clean_dataset(
        truthfulqa_n=sample_per_dataset,
        fever_n=sample_per_dataset,
        commonsenseqa_n=sample_per_dataset,
        seed=seed,
        output_path=candidate,
        summary_path=candidate_summary,
    )
    df = read_csv(candidate) if candidate.exists() else pd.DataFrame()
    if df.empty and PATHS["samples"].exists():
        existing = read_csv(PATHS["samples"])
        if not existing.empty:
            LOGGER.warning("候选数据集为空，保留已有 clean_dataset.csv：%s", PATHS["samples"])
            return

    write_csv(df, PATHS["samples"])
    if candidate_summary.exists():
        summary_df = read_csv(candidate_summary)
        write_csv(summary_df, PATHS["dataset_summary"])
    LOGGER.info("clean_dataset.csv 样本数：%s", len(df))


def prepare_run_samples(limit: Optional[int]) -> Path:
    if not require_file(PATHS["samples"], "准备运行样本"):
        raise FileNotFoundError(PATHS["samples"])
    samples = read_csv(PATHS["samples"])
    if limit is not None and limit > 0:
        samples = samples.head(limit).copy()
        write_csv(samples, PATHS["samples_run"])
        LOGGER.info("启用 --limit=%s，本轮使用样本文件：%s", limit, PATHS["samples_run"])
        return PATHS["samples_run"]
    return PATHS["samples"]


def call_one_model(sample: Dict[str, Any], model_name: str, temperature: float, max_tokens: int) -> Dict[str, Any]:
    client = get_client(model_name)
    prompt = build_answer_prompt(sample)
    result = client.call_json(prompt, temperature=temperature, max_tokens=max_tokens)
    parse_error = str(result.get("parse_error", "") or "")
    request_error = str(result.get("request_error", "") or "")
    final_parse_error = parse_error or request_error
    return {
        "sample_id": sample.get("id", ""),
        "dataset": sample.get("dataset", ""),
        "task_type": sample.get("task_type", ""),
        "model": model_name,
        "answer": result.get("answer", ""),
        "reason": result.get("reason", ""),
        "confidence": result.get("confidence", 0.0),
        "evidence": result.get("evidence", ""),
        "raw_output": result.get("raw_output", ""),
        "parse_error": final_parse_error,
        "prompt": prompt,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def model_calls_step(samples_path: Path, models: List[str], limit: Optional[int], max_workers: int) -> None:
    if not require_file(samples_path, "多模型回答"):
        return
    samples = read_csv(samples_path)
    if limit is not None and limit > 0:
        samples = samples.head(limit).copy()
    if samples.empty:
        LOGGER.warning("样本为空，跳过模型调用。")
        return
    existing = pd.DataFrame()
    completed: set[tuple[str, str]] = set()
    if PATHS["model_outputs"].exists():
        try:
            existing = read_csv(PATHS["model_outputs"])
            if "provider" in existing.columns and "model" not in existing.columns:
                existing = existing.rename(columns={"provider": "model"})
            if "model_name" in existing.columns and "model" not in existing.columns:
                existing = existing.rename(columns={"model_name": "model"})
            if {"sample_id", "model"}.issubset(existing.columns):
                ok_df = existing.copy()
                if "parse_error" in ok_df.columns:
                    ok_df = ok_df[ok_df["parse_error"].fillna("").astype(str).str.strip() == ""]
                elif "parse_ok" in ok_df.columns:
                    ok_df = ok_df[ok_df["parse_ok"].astype(str).str.lower().isin(["true", "1", "yes"])]
                completed = {
                    (str(row["sample_id"]), str(row["model"]))
                    for row in ok_df.to_dict(orient="records")
                }
                LOGGER.info("断点续跑：发现已有成功输出 %s 条，将跳过对应 sample/model。", len(completed))
        except Exception as exc:
            LOGGER.warning("读取已有模型输出失败，将重新生成：%s", exc)

    tasks = [
        (sample, model)
        for sample in samples.to_dict(orient="records")
        for model in models
        if (str(sample.get("id", "")), str(model)) not in completed
    ]
    LOGGER.info("准备调用模型：%s；待执行任务数：%s", ", ".join(models), len(tasks))

    rows: List[Dict[str, Any]] = []
    if tasks:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [
                pool.submit(call_one_model, sample, model, 0.2, 800)
                for sample, model in tasks
            ]
            for fut in as_completed(futures):
                try:
                    row = fut.result()
                except Exception as exc:
                    LOGGER.error("单次模型调用异常：%s", exc)
                    continue
                rows.append(row)
                status = "ok" if not row.get("parse_error") else "fail"
                LOGGER.info("[%s] %s/%s -> %s", status, row.get("sample_id"), row.get("model"), row.get("answer", ""))

    combined = pd.concat([existing, pd.DataFrame(rows)], ignore_index=True) if not existing.empty else pd.DataFrame(rows)
    if "provider" in combined.columns and "model" not in combined.columns:
        combined = combined.rename(columns={"provider": "model"})
    if "model_name" in combined.columns and "model" not in combined.columns:
        combined = combined.rename(columns={"model_name": "model"})
    if not combined.empty and {"sample_id", "model"}.issubset(combined.columns):
        if "parse_error" in combined.columns:
            combined["_parse_rank"] = (combined["parse_error"].fillna("").astype(str).str.strip() == "").astype(int)
        elif "parse_ok" in combined.columns:
            combined["_parse_rank"] = combined["parse_ok"].astype(str).str.lower().isin(["true", "1", "yes"]).astype(int)
        else:
            combined["_parse_rank"] = 1
        combined = (
            combined.sort_values("_parse_rank")
            .drop_duplicates(subset=["sample_id", "model"], keep="last")
            .drop(columns=["_parse_rank"])
        )
    standard_columns = [
        "sample_id",
        "dataset",
        "task_type",
        "model",
        "answer",
        "reason",
        "confidence",
        "evidence",
        "raw_output",
        "parse_error",
        "prompt",
        "created_at",
    ]
    for col in standard_columns:
        if col not in combined.columns:
            combined[col] = ""
    combined = combined[standard_columns]
    write_csv(combined, PATHS["model_outputs"])
    LOGGER.info("已写入模型输出：%s（新增 %s 行，总计 %s 行）", PATHS["model_outputs"], len(rows), len(combined))


def decisions_step(samples_path: Path, run_judge: bool) -> None:
    if not require_file(samples_path, "裁决"):
        return
    if not require_file(PATHS["model_outputs"], "裁决"):
        return
    samples = read_csv(samples_path)
    outputs = read_csv(PATHS["model_outputs"])

    majority_df = run_majority(outputs, PATHS["majority"])
    LOGGER.info("多数投票结果：%s（%s 行）", PATHS["majority"], len(majority_df))

    dynamic_df = run_dynamic(samples, outputs, PATHS["dynamic"])
    LOGGER.info("动态裁决结果：%s（%s 行）", PATHS["dynamic"], len(dynamic_df))

    if run_judge:
        try:
            judge_df = run_fixed_judge(samples, outputs, PATHS["fixed_judge"])
            LOGGER.info("固定裁决器结果：%s（%s 行）", PATHS["fixed_judge"], len(judge_df))
        except Exception as exc:
            LOGGER.error("固定裁决器步骤失败，继续后续流程：%s", exc)


def evaluate_step(samples_path: Path) -> None:
    if not require_file(samples_path, "评估"):
        return
    if not require_file(PATHS["model_outputs"], "评估"):
        return
    # Reuse evaluate_results CLI implementation by setting argv for its parser.
    old_argv = sys.argv[:]
    try:
        sys.argv = [
            "evaluate_results",
            "--samples",
            str(samples_path),
            "--outputs",
            str(PATHS["model_outputs"]),
            "--majority",
            str(PATHS["majority"]),
            "--dynamic",
            str(PATHS["dynamic"]),
            "--fixed_judge",
            str(PATHS["fixed_judge"]),
            "--risk_labels_out",
            str(PATHS["risk_labels"]),
            "--method_metrics_out",
            str(PATHS["method_metrics"]),
            "--risk_effectiveness_out",
            str(PATHS["risk_effectiveness"]),
            "--error_cases_out",
            str(PATHS["error_cases"]),
        ]
        evaluate_results_main()
    finally:
        sys.argv = old_argv


def figures_step() -> None:
    generate_all_figures(ROOT / "data" / "results", PATHS["figures"])


def report_step(samples_path: Path) -> None:
    processed_dir = samples_path.parent
    # The report generator expects clean_dataset.csv. If --limit created a run
    # sample file, copy the current run view to a temporary clean_dataset.csv-like
    # location is overkill; using processed_dir still keeps report generation
    # graceful, and dataset_summary remains in data/processed.
    generate_report(PATHS["report"], ROOT / "data" / "results", ROOT / "data" / "processed")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the full multi-LLM reliability experiment pipeline.")
    parser.add_argument("--sample_per_dataset", type=int, default=100)
    parser.add_argument("--models", nargs="+", default=["deepseek", "qwen", "glm", "kimi"])
    parser.add_argument("--skip_model_calls", action="store_true")
    parser.add_argument("--run_judge", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="Limit samples used after dataset construction.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max_workers", type=int, default=4)
    return parser.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()
    LOGGER.info("项目根目录：%s", ROOT)
    LOGGER.info("模型列表：%s", ", ".join(args.models))
    check_api_keys(args.models, args.run_judge)

    safe_step(
        "1. 构建 clean_dataset.csv",
        lambda: build_dataset_step(args.sample_per_dataset, args.seed),
    )

    samples_path = PATHS["samples"]
    try:
        samples_path = prepare_run_samples(args.limit)
    except Exception as exc:
        LOGGER.error("准备运行样本失败：%s", exc)

    if args.skip_model_calls:
        LOGGER.info("跳过模型调用：使用已有 %s", PATHS["model_outputs"])
        if not PATHS["model_outputs"].exists():
            LOGGER.warning("已设置 --skip_model_calls，但模型输出文件不存在：%s", PATHS["model_outputs"])
    else:
        safe_step(
            "2. 调用多模型回答",
            lambda: model_calls_step(samples_path, args.models, args.limit, args.max_workers),
        )

    safe_step(
        "3-4. 运行多数投票、动态裁决和可选固定裁决器",
        lambda: decisions_step(samples_path, args.run_judge),
    )
    safe_step("5. 计算风险标签和指标", lambda: evaluate_step(samples_path))
    safe_step("6. 生成图表", figures_step)
    safe_step("7. 生成 Markdown 报告", lambda: report_step(samples_path))

    LOGGER.info("流水线结束。关键输出：")
    for key in ["model_outputs", "majority", "dynamic", "fixed_judge", "risk_labels", "method_metrics", "risk_effectiveness", "error_cases", "report"]:
        path = PATHS[key]
        LOGGER.info("- %s: %s%s", key, path, "（存在）" if path.exists() else "（未生成）")


if __name__ == "__main__":
    main()
