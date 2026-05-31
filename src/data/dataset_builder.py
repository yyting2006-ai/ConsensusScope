from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from src.config import PROJECT_ROOT


COLUMNS = [
    "id",
    "dataset",
    "task_type",
    "question",
    "options",
    "gold_answer",
    "gold_label",
    "evidence",
    "category",
    "source_file",
]


def _warn(message: str) -> None:
    warnings.warn(message, stacklevel=2)


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def _first_present(row: Dict[str, Any], keys: Iterable[str], default: str = "") -> str:
    for key in keys:
        if key in row and _as_str(row[key]):
            return _as_str(row[key])
    return default


def _json_dumps(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    return json.dumps(value, ensure_ascii=False)


def _sample_rows(rows: List[Dict[str, str]], n: Optional[int], seed: int) -> List[Dict[str, str]]:
    if n is None or n <= 0 or len(rows) <= n:
        return rows
    return pd.DataFrame(rows).sample(n=n, random_state=seed).to_dict(orient="records")


def _format_id(prefix: str, index: int) -> str:
    return f"{prefix}_{index:04d}"


def build_truthfulqa(
    path: Path,
    n: Optional[int] = None,
    seed: int = 42,
) -> List[Dict[str, str]]:
    if not path.exists():
        _warn(
            "TruthfulQA file not found, skipped: "
            f"{path}\n"
            "下载提示：请从 TruthfulQA 官方仓库或 HuggingFace 数据集页面下载 TruthfulQA.csv，"
            "并放置到 data/raw/truthfulqa/TruthfulQA.csv"
        )
        return []

    df = pd.read_csv(path)
    rows: List[Dict[str, str]] = []
    for idx, row in enumerate(df.to_dict(orient="records"), start=1):
        question = _first_present(row, ["Question", "question", "prompt"])
        gold_answer = _first_present(
            row,
            ["Best Answer", "best_answer", "Correct Answers", "correct_answers", "answer", "gold_answer"],
        )
        category = _first_present(row, ["Category", "category", "Type", "type"])
        evidence = _first_present(row, ["Source", "source", "Evidence", "evidence"])
        if not question:
            continue

        rows.append(
            {
                "id": _format_id("truthfulqa", idx),
                "dataset": "truthfulqa",
                "task_type": "truthfulness_qa",
                "question": question,
                "options": "",
                "gold_answer": gold_answer,
                "gold_label": "truthful",
                "evidence": evidence,
                "category": category,
                "source_file": path.name,
            }
        )
    return _sample_rows(rows, n, seed)


def _iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if path.name.startswith("._"):
        _warn(f"AppleDouble metadata file skipped: {path}")
        return
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line_no, line in enumerate(f, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                yield json.loads(text)
            except json.JSONDecodeError as exc:
                _warn(f"Invalid JSON skipped: {path}:{line_no} ({exc})")


def _extract_fever_evidence(record: Dict[str, Any]) -> str:
    evidence = record.get("evidence", "")
    if isinstance(evidence, str):
        return evidence.strip()
    if isinstance(evidence, list):
        snippets: List[str] = []
        for item in evidence:
            if isinstance(item, str):
                snippets.append(item)
            elif isinstance(item, dict):
                snippets.append(
                    _first_present(
                        item,
                        ["text", "sentence", "evidence", "page", "title", "doc_id"],
                    )
                )
            elif isinstance(item, list):
                snippets.append(" ".join(_as_str(x) for x in item if _as_str(x)))
        return " | ".join(x for x in snippets if x)
    return _as_str(evidence)


def build_fever(
    raw_dir: Path,
    n: Optional[int] = None,
    seed: int = 42,
) -> List[Dict[str, str]]:
    files = sorted(raw_dir.glob("*.jsonl"))
    if not files:
        _warn(
            "FEVER jsonl files not found, skipped: "
            f"{raw_dir}\n"
            "下载提示：请从 FEVER 官方数据页面或公开镜像下载 train/dev/test 的 JSONL 文件，"
            "并放置到 data/raw/fever/*.jsonl"
        )
        return []

    rows: List[Dict[str, str]] = []
    counter = 1
    for path in files:
        for record in _iter_jsonl(path):
            claim = _first_present(record, ["claim", "question", "statement", "text"])
            label = _first_present(record, ["label", "gold_label", "verdict"]).upper()
            if not claim:
                continue
            rows.append(
                {
                    "id": _format_id("fever", counter),
                    "dataset": "fever",
                    "task_type": "fact_verification",
                    "question": claim,
                    "options": "",
                    "gold_answer": label,
                    "gold_label": label,
                    "evidence": _extract_fever_evidence(record),
                    "category": _first_present(record, ["category", "domain"]),
                    "source_file": path.name,
                }
            )
            counter += 1
    return _sample_rows(rows, n, seed)


def _extract_csqa_question(record: Dict[str, Any]) -> str:
    question = record.get("question", "")
    if isinstance(question, dict):
        return _first_present(question, ["stem", "question", "text"])
    return _first_present(record, ["question", "stem", "text"])


def _extract_csqa_options(record: Dict[str, Any]) -> List[Dict[str, str]]:
    question = record.get("question", {})
    raw_choices = None
    if isinstance(question, dict):
        raw_choices = question.get("choices")
    raw_choices = raw_choices or record.get("choices") or record.get("options")

    options: List[Dict[str, str]] = []
    if isinstance(raw_choices, list):
        for idx, item in enumerate(raw_choices):
            default_label = chr(ord("A") + idx)
            if isinstance(item, dict):
                label = _first_present(item, ["label", "key"], default_label)
                text = _first_present(item, ["text", "answer", "content"])
            else:
                label = default_label
                text = _as_str(item)
            if text:
                options.append({"label": label, "text": text})
    elif isinstance(raw_choices, dict):
        for label, text in raw_choices.items():
            options.append({"label": _as_str(label), "text": _as_str(text)})
    return options


def build_commonsenseqa(
    raw_dir: Path,
    n: Optional[int] = None,
    seed: int = 42,
) -> List[Dict[str, str]]:
    files = sorted(raw_dir.glob("*.jsonl"))
    if not files:
        _warn(
            "CommonsenseQA jsonl files not found, skipped: "
            f"{raw_dir}\n"
            "下载提示：请从 CommonsenseQA 官方数据页面或 HuggingFace 数据集页面下载 JSONL 文件，"
            "并放置到 data/raw/commonsenseqa/*.jsonl"
        )
        return []

    rows: List[Dict[str, str]] = []
    counter = 1
    for path in files:
        for record in _iter_jsonl(path):
            question = _extract_csqa_question(record)
            options = _extract_csqa_options(record)
            gold_label = _first_present(record, ["answerKey", "answer_key", "label", "gold_label"]).upper()
            gold_answer = ""
            for option in options:
                if option["label"].upper() == gold_label:
                    gold_answer = option["text"]
                    break
            gold_answer = gold_answer or _first_present(record, ["answer", "gold_answer"])
            if not question:
                continue
            rows.append(
                {
                    "id": _format_id("csqa", counter),
                    "dataset": "commonsenseqa",
                    "task_type": "commonsense_reasoning",
                    "question": question,
                    "options": _json_dumps(options),
                    "gold_answer": gold_answer,
                    "gold_label": gold_label,
                    "evidence": _first_present(record, ["evidence", "explanation", "reason"]),
                    "category": _first_present(record, ["category", "question_concept", "concept"]),
                    "source_file": path.name,
                }
            )
            counter += 1
    return _sample_rows(rows, n, seed)


def build_clean_dataset(
    truthfulqa_n: Optional[int] = None,
    fever_n: Optional[int] = None,
    commonsenseqa_n: Optional[int] = None,
    seed: int = 42,
    raw_root: Path | None = None,
    output_path: Path | None = None,
    summary_path: Path | None = None,
) -> pd.DataFrame:
    raw_root = raw_root or PROJECT_ROOT / "data" / "raw"
    output_path = output_path or PROJECT_ROOT / "data" / "processed" / "clean_dataset.csv"
    summary_path = summary_path or PROJECT_ROOT / "data" / "processed" / "dataset_summary.csv"

    rows: List[Dict[str, str]] = []
    rows.extend(build_truthfulqa(raw_root / "truthfulqa" / "TruthfulQA.csv", truthfulqa_n, seed))
    rows.extend(build_fever(raw_root / "fever", fever_n, seed))
    rows.extend(build_commonsenseqa(raw_root / "commonsenseqa", commonsenseqa_n, seed))

    df = pd.DataFrame(rows, columns=COLUMNS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    if df.empty:
        summary = pd.DataFrame(columns=["dataset", "sample_count"])
    else:
        summary = (
            df.groupby("dataset", dropna=False)
            .size()
            .reset_index(name="sample_count")
            .sort_values("dataset")
        )
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    return df


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a unified clean_dataset.csv from raw QA datasets.")
    parser.add_argument("--truthfulqa_n", type=int, default=None, help="Number of TruthfulQA samples to keep.")
    parser.add_argument("--fever_n", type=int, default=None, help="Number of FEVER samples to keep.")
    parser.add_argument("--commonsenseqa_n", type=int, default=None, help="Number of CommonsenseQA samples to keep.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling.")
    parser.add_argument("--raw_root", type=Path, default=PROJECT_ROOT / "data" / "raw")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "processed" / "clean_dataset.csv")
    parser.add_argument(
        "--summary",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "dataset_summary.csv",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = build_clean_dataset(
        truthfulqa_n=args.truthfulqa_n,
        fever_n=args.fever_n,
        commonsenseqa_n=args.commonsenseqa_n,
        seed=args.seed,
        raw_root=args.raw_root,
        output_path=args.output,
        summary_path=args.summary,
    )
    print(f"Wrote {len(df)} samples to {args.output}")
    print(f"Wrote summary to {args.summary}")


if __name__ == "__main__":
    main()
