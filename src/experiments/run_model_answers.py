from __future__ import annotations

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd

from src.llm.clients import get_client
from src.llm.prompts import build_answer_prompt


STANDARD_COLUMNS = [
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


LOGGER = logging.getLogger("run_model_answers")


def setup_logger(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    LOGGER.setLevel(logging.INFO)
    LOGGER.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    LOGGER.addHandler(stream_handler)
    LOGGER.addHandler(file_handler)


def read_samples(path: Path, limit: int | None = None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input dataset not found: {path}")
    df = pd.read_csv(path)
    required = {"id", "dataset", "task_type", "question"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Input dataset missing required columns: {missing}")
    if limit is not None and limit > 0:
        df = df.head(limit).copy()
    return df


def normalize_existing_outputs(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=STANDARD_COLUMNS)
    df = pd.read_csv(path)
    if "provider" in df.columns and "model" not in df.columns:
        df = df.rename(columns={"provider": "model"})
    if "model_name" in df.columns and "model" not in df.columns:
        df = df.rename(columns={"model_name": "model"})
    if "request_error" in df.columns:
        if "parse_error" not in df.columns:
            df["parse_error"] = ""
        df["parse_error"] = df["parse_error"].fillna("").astype(str)
        df["parse_error"] = df["parse_error"].where(df["parse_error"].str.strip() != "", df["request_error"].fillna(""))
    for col in STANDARD_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[STANDARD_COLUMNS]


def successful_pairs(outputs_df: pd.DataFrame) -> set[tuple[str, str]]:
    if outputs_df.empty:
        return set()
    ok = outputs_df[outputs_df["parse_error"].fillna("").astype(str).str.strip() == ""]
    return {(str(row["sample_id"]), str(row["model"])) for row in ok.to_dict(orient="records")}


def write_outputs(path: Path, rows: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    for col in STANDARD_COLUMNS:
        if col not in rows.columns:
            rows[col] = ""
    rows = rows[STANDARD_COLUMNS]
    rows.to_csv(path, index=False, encoding="utf-8-sig")


def check_api_keys(models: Iterable[str]) -> None:
    for model in models:
        try:
            client = get_client(model)
        except Exception as exc:
            LOGGER.warning("模型配置不可用：%s (%s)", model, exc)
            continue
        if not client.is_available:
            LOGGER.warning("缺少 %s API key：请检查 .env 中对应的 *_API_KEY。该模型调用会记录错误并继续。", model)


def call_model(sample: Dict[str, Any], model: str) -> Dict[str, Any]:
    prompt = build_answer_prompt(sample)
    created_at = datetime.now(timezone.utc).isoformat()
    try:
        client = get_client(model)
        result = client.call_json(prompt, temperature=0.2, max_tokens=800)
    except Exception as exc:
        result = {
            "answer": "",
            "reason": "",
            "confidence": 0.0,
            "evidence": "",
            "raw_output": "",
            "parse_error": str(exc),
        }

    parse_error = str(result.get("parse_error", "") or result.get("request_error", "") or "")
    return {
        "sample_id": sample.get("id", ""),
        "dataset": sample.get("dataset", ""),
        "task_type": sample.get("task_type", ""),
        "model": model,
        "answer": result.get("answer", ""),
        "reason": result.get("reason", ""),
        "confidence": result.get("confidence", 0.0),
        "evidence": result.get("evidence", ""),
        "raw_output": result.get("raw_output", ""),
        "parse_error": parse_error,
        "prompt": prompt,
        "created_at": created_at,
    }


def upsert_output(existing: pd.DataFrame, row: Dict[str, Any]) -> pd.DataFrame:
    if existing.empty:
        return pd.DataFrame([row], columns=STANDARD_COLUMNS)
    mask = (existing["sample_id"].astype(str) == str(row["sample_id"])) & (
        existing["model"].astype(str) == str(row["model"])
    )
    if mask.any():
        existing = existing.loc[~mask].copy()
    return pd.concat([existing, pd.DataFrame([row], columns=STANDARD_COLUMNS)], ignore_index=True)


def run_model_answers(
    input_path: Path,
    output_path: Path,
    models: List[str],
    limit: int | None,
    resume: bool,
    log_path: Path,
    max_workers: int = 1,
) -> pd.DataFrame:
    setup_logger(log_path)
    LOGGER.info("读取样本：%s", input_path)
    samples = read_samples(input_path, limit=limit)
    LOGGER.info("样本数：%s；模型：%s；resume=%s；max_workers=%s", len(samples), ", ".join(models), resume, max_workers)
    check_api_keys(models)

    outputs = normalize_existing_outputs(output_path) if resume else pd.DataFrame(columns=STANDARD_COLUMNS)
    done = successful_pairs(outputs) if resume else set()
    LOGGER.info("已完成成功输出：%s 条", len(done))

    if samples.empty:
        LOGGER.warning("输入样本为空，写出空的标准 model_outputs.csv 后结束。")
        write_outputs(output_path, outputs)
        return outputs

    total = len(samples) * len(models)
    skipped = 0
    completed = 0
    tasks: List[Tuple[Dict[str, Any], str]] = []
    for sample in samples.to_dict(orient="records"):
        sample_id = str(sample.get("id", ""))
        for model in models:
            key = (sample_id, str(model))
            if resume and key in done:
                skipped += 1
                LOGGER.info("[skip] %s/%s 已存在成功输出", sample_id, model)
                continue
            tasks.append((sample, model))

    if max_workers <= 1:
        for sample, model in tasks:
            sample_id = str(sample.get("id", ""))
            LOGGER.info("[call] %s/%s", sample_id, model)
            row = call_model(sample, model)
            outputs = upsert_output(outputs, row)
            write_outputs(output_path, outputs)
            completed += 1

            if row["parse_error"]:
                LOGGER.warning("[fail] %s/%s parse_error=%s", sample_id, model, row["parse_error"][:300])
            else:
                LOGGER.info("[ok] %s/%s answer=%s", sample_id, model, row["answer"])
    else:
        LOGGER.info("并发调用任务数：%s", len(tasks))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_map = {
                pool.submit(call_model, sample, model): (str(sample.get("id", "")), model)
                for sample, model in tasks
            }
            for future in as_completed(future_map):
                sample_id, model = future_map[future]
                try:
                    row = future.result()
                except Exception as exc:
                    row = {
                        "sample_id": sample_id,
                        "dataset": "",
                        "task_type": "",
                        "model": model,
                        "answer": "",
                        "reason": "",
                        "confidence": 0.0,
                        "evidence": "",
                        "raw_output": "",
                        "parse_error": str(exc),
                        "prompt": "",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                outputs = upsert_output(outputs, row)
                write_outputs(output_path, outputs)
                completed += 1

                if row["parse_error"]:
                    LOGGER.warning("[fail] %s/%s parse_error=%s", sample_id, model, row["parse_error"][:300])
                else:
                    LOGGER.info("[ok] %s/%s answer=%s", sample_id, model, row["answer"])

    LOGGER.info("运行结束：total=%s skipped=%s newly_completed=%s output=%s", total, skipped, completed, output_path)
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Call multiple LLM APIs for clean_dataset.csv and save model_outputs.csv.")
    parser.add_argument("--input", type=Path, default=Path("data/processed/clean_dataset.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/outputs/model_outputs.csv"))
    parser.add_argument("--models", nargs="+", default=["deepseek", "qwen", "glm", "kimi"])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--log", type=Path, default=Path("data/outputs/run_log.txt"))
    parser.add_argument("--max_workers", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_model_answers(
        input_path=args.input,
        output_path=args.output,
        models=args.models,
        limit=args.limit,
        resume=args.resume,
        log_path=args.log,
        max_workers=args.max_workers,
    )


if __name__ == "__main__":
    main()
