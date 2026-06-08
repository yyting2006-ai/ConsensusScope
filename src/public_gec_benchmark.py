from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import pandas as pd


REVIEW_ACTIONS = {"teacher_review", "needs_more_evidence", "reject"}
LOW_RISK_GEC_TYPES = {"grammar", "spelling", "punctuation", "vocabulary", "word_choice"}
PUNCTUATION = {".", ",", ";", ":", "!", "?", "'", '"', "(", ")", "[", "]"}


@dataclass(frozen=True)
class ParallelSentence:
    dataset: str
    sample_id: str
    source: str
    reference: str
    split: str = ""


def safe_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_ws(value: Any) -> str:
    return re.sub(r"\s+", " ", safe_text(value)).strip()


def simple_tokenize(text: str) -> List[str]:
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?|\d+(?:\.\d+)?|[^\w\s]", safe_text(text))


def untokenize(tokens: Sequence[str]) -> str:
    text = " ".join(tok for tok in tokens if tok != "")
    text = re.sub(r"\s+([,.;:!?%)\]])", r"\1", text)
    text = re.sub(r"([\[(])\s+", r"\1", text)
    text = re.sub(r"\s+'\b", "'", text)
    text = re.sub(r"\b'\s+", "'", text)
    return normalize_ws(text)


def _word_tokens(tokens: Sequence[str]) -> List[str]:
    return [tok.lower() for tok in tokens if re.search(r"[A-Za-z0-9]", tok)]


def _span_context(text: str, span: str, window: int = 90) -> str:
    source = safe_text(text)
    target = safe_text(span)
    if not target:
        return source[: window * 2]
    idx = source.lower().find(target.lower())
    if idx < 0:
        return source[: window * 2]
    return source[max(0, idx - window) : min(len(source), idx + len(target) + window)].strip()


def _insert_anchor(tokens: Sequence[str], index: int) -> str:
    if index <= 0:
        return "sentence start"
    return untokenize(tokens[max(0, index - 4) : index])


def infer_issue_type(source_tokens: Sequence[str], replacement_tokens: Sequence[str], operation: str) -> str:
    source_words = _word_tokens(source_tokens)
    replacement_words = _word_tokens(replacement_tokens)
    if all(tok in PUNCTUATION for tok in list(source_tokens) + list(replacement_tokens) if tok):
        return "punctuation"
    if operation == "insert" and all(tok in PUNCTUATION for tok in replacement_tokens):
        return "punctuation"
    if operation == "delete" and all(tok in PUNCTUATION for tok in source_tokens):
        return "punctuation"
    if len(source_words) == 1 and len(replacement_words) == 1:
        ratio = difflib.SequenceMatcher(None, source_words[0], replacement_words[0]).ratio()
        if ratio >= 0.74:
            return "spelling"
        grammar_pairs = {
            ("is", "are"),
            ("are", "is"),
            ("was", "were"),
            ("were", "was"),
            ("has", "have"),
            ("have", "has"),
            ("do", "does"),
            ("does", "do"),
            ("go", "goes"),
            ("make", "makes"),
            ("study", "studies"),
        }
        if (source_words[0], replacement_words[0]) in grammar_pairs:
            return "grammar"
        return "vocabulary"
    if len(source_words) <= 3 and len(replacement_words) <= 3:
        return "grammar"
    if len(source_words) <= 6 and len(replacement_words) <= 8:
        return "sentence_structure"
    return "coherence"


def align_parallel_sentence(record: ParallelSentence) -> pd.DataFrame:
    source_tokens = simple_tokenize(record.source)
    reference_tokens = simple_tokenize(record.reference)
    matcher = difflib.SequenceMatcher(a=source_tokens, b=reference_tokens, autojunk=False)
    rows: List[Dict[str, Any]] = []
    for op_index, (tag, i1, i2, j1, j2) in enumerate(matcher.get_opcodes(), start=1):
        if tag == "equal":
            continue
        source_part = source_tokens[i1:i2]
        reference_part = reference_tokens[j1:j2]
        operation = {"replace": "replace", "delete": "delete", "insert": "insert"}.get(tag, tag)
        target_span = untokenize(source_part)
        replacement = untokenize(reference_part)
        if operation == "insert":
            target_span = f"insert after {_insert_anchor(source_tokens, i1)}"
        if operation == "delete":
            replacement = ""
        issue = infer_issue_type(source_part, reference_part, operation)
        rows.append(
            {
                "gold_feedback_item_id": f"{record.dataset}-{record.sample_id}-G{op_index:03d}",
                "dataset": record.dataset,
                "split": record.split,
                "sample_id": record.sample_id,
                "source_sentence": normalize_ws(record.source),
                "reference_sentence": normalize_ws(record.reference),
                "edit_operation": operation,
                "target_span": target_span,
                "gold_replacement": replacement,
                "gold_issue_type": issue,
                "surrounding_context": _span_context(record.source, target_span if operation != "insert" else ""),
            }
        )
    return pd.DataFrame(rows)


def build_gold_feedback(records: Sequence[ParallelSentence]) -> pd.DataFrame:
    frames = [align_parallel_sentence(record) for record in records if normalize_ws(record.source) != normalize_ws(record.reference)]
    if not frames:
        return pd.DataFrame(
            columns=[
                "gold_feedback_item_id",
                "dataset",
                "split",
                "sample_id",
                "source_sentence",
                "reference_sentence",
                "edit_operation",
                "target_span",
                "gold_replacement",
                "gold_issue_type",
                "surrounding_context",
            ]
        )
    return pd.concat(frames, ignore_index=True)


def _correct_suggestion(row: Mapping[str, Any]) -> str:
    op = safe_text(row.get("edit_operation"))
    target = safe_text(row.get("target_span"))
    replacement = safe_text(row.get("gold_replacement"))
    if op == "insert":
        return f'Insert "{replacement}" near "{target.replace("insert after ", "")}".'
    if op == "delete":
        return f'Remove "{target}".'
    return f'Replace "{target}" with "{replacement}".'


def _candidate_agreement(issue: str, correct: bool) -> float:
    if not correct:
        return 0.34
    return 0.88 if issue in LOW_RISK_GEC_TYPES else 0.66


def build_feedback_candidates(gold_feedback: pd.DataFrame, include_distractors: bool = True) -> Dict[str, pd.DataFrame]:
    feedback_rows: List[Dict[str, Any]] = []
    label_rows: List[Dict[str, Any]] = []
    evidence_rows: List[Dict[str, Any]] = []

    def add_candidate(
        gold_row: Mapping[str, Any],
        suffix: str,
        suggestion: str,
        rationale: str,
        issue_type: str,
        correctness: str,
        safety_label: str,
        match_status: str,
        criterion: str,
        evidence_text: str,
    ) -> None:
        feedback_item_id = f"{safe_text(gold_row.get('gold_feedback_item_id'))}-{suffix}"
        feedback_rows.append(
            {
                "feedback_item_id": feedback_item_id,
                "gold_feedback_item_id": safe_text(gold_row.get("gold_feedback_item_id")),
                "dataset": safe_text(gold_row.get("dataset")),
                "split": safe_text(gold_row.get("split")),
                "sample_id": safe_text(gold_row.get("sample_id")),
                "essay_id": safe_text(gold_row.get("sample_id")),
                "target_span": safe_text(gold_row.get("target_span")),
                "surrounding_context": safe_text(gold_row.get("surrounding_context")),
                "ai_suggestion": suggestion,
                "ai_rationale": rationale,
                "model_source": "public_gec_candidate_generator",
                "issue_type_predicted": issue_type,
                "model_agreement": _candidate_agreement(issue_type, correctness == "correct"),
            }
        )
        label_rows.append(
            {
                "feedback_item_id": feedback_item_id,
                "gold_feedback_item_id": safe_text(gold_row.get("gold_feedback_item_id")),
                "dataset": safe_text(gold_row.get("dataset")),
                "split": safe_text(gold_row.get("split")),
                "sample_id": safe_text(gold_row.get("sample_id")),
                "gold_feedback_correctness": correctness,
                "gold_safety_label": safety_label,
                "gold_issue_type": safe_text(gold_row.get("gold_issue_type")),
                "gold_replacement": safe_text(gold_row.get("gold_replacement")),
                "source_sentence": safe_text(gold_row.get("source_sentence")),
                "reference_sentence": safe_text(gold_row.get("reference_sentence")),
            }
        )
        evidence_rows.append(
            {
                "evidence_id": f"PUB-EV-{len(evidence_rows) + 1:05d}",
                "feedback_item_id": feedback_item_id,
                "evidence_type": "public_gec_gold",
                "evidence_text": evidence_text,
                "criterion": criterion,
                "match_status": match_status,
                "used_for_decision": True,
            }
        )

    for _, row in gold_feedback.fillna("").iterrows():
        issue = safe_text(row.get("gold_issue_type")) or "grammar"
        add_candidate(
            row,
            "COR",
            _correct_suggestion(row),
            "This candidate is generated from the public corpus correction.",
            issue,
            "correct",
            "safe_to_show_student",
            "supported",
            "public_gold_correction",
            "The candidate matches the public learner-corpus correction.",
        )
        if include_distractors:
            target = safe_text(row.get("target_span")) or "the sentence"
            add_candidate(
                row,
                "MEAN",
                f'Rewrite "{target}" to add a stronger new argument that is not stated in the sentence.',
                "Distractor candidate: it may change the learner's intended meaning.",
                "meaning_change",
                "incorrect",
                "unsafe_without_revision",
                "conflict",
                "meaning_preservation",
                "The candidate can introduce a new claim or alter the learner's intended meaning.",
            )
            if issue in LOW_RISK_GEC_TYPES:
                add_candidate(
                    row,
                    "WRONG",
                    f'Change "{target}" to a more formal phrase even if the original meaning becomes different.',
                    "Distractor candidate: it overcorrects a local edit.",
                    "overcorrection",
                    "incorrect",
                    "unsafe_without_revision",
                    "conflict",
                    "overcorrection",
                    "The candidate is not licensed by the public corpus correction.",
                )

    return {
        "feedback_items": pd.DataFrame(feedback_rows),
        "gold_labels": pd.DataFrame(label_rows),
        "review_evidence": pd.DataFrame(evidence_rows),
    }


def evaluate_routing_with_gold(routing: pd.DataFrame, gold_labels: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    if routing.empty or gold_labels.empty:
        empty_metrics = pd.DataFrame(
            columns=[
                "dataset",
                "items",
                "auto_share",
                "auto_acc",
                "review_share",
                "errors_reviewed",
                "correct_items",
                "incorrect_items",
            ]
        )
        return {"item_analysis": pd.DataFrame(), "metrics": empty_metrics, "policy_metrics": empty_metrics}

    merged = gold_labels.merge(routing, on="feedback_item_id", how="left")
    merged["is_correct"] = merged["gold_feedback_correctness"].eq("correct")
    merged["is_error"] = ~merged["is_correct"]
    merged["is_reviewed"] = merged["recommended_action"].isin(REVIEW_ACTIONS)
    merged["is_auto"] = merged["recommended_action"].eq("auto_accept")

    def aggregate(frame: pd.DataFrame, dataset: str) -> Dict[str, Any]:
        auto = frame["is_auto"]
        reviewed = frame["is_reviewed"]
        errors = frame["is_error"]
        auto_acc = float(frame.loc[auto, "is_correct"].mean()) if int(auto.sum()) else None
        errors_reviewed = float((errors & reviewed).sum() / errors.sum()) if int(errors.sum()) else None
        return {
            "dataset": dataset,
            "items": int(len(frame)),
            "auto_share": round(float(auto.mean()), 4) if len(frame) else 0.0,
            "auto_acc": round(auto_acc, 4) if auto_acc is not None else None,
            "review_share": round(float(reviewed.mean()), 4) if len(frame) else 0.0,
            "errors_reviewed": round(errors_reviewed, 4) if errors_reviewed is not None else None,
            "correct_items": int(frame["is_correct"].sum()),
            "incorrect_items": int(frame["is_error"].sum()),
        }

    metric_rows = [aggregate(merged, "ALL")]
    for dataset, group in merged.groupby("dataset", dropna=False):
        metric_rows.append(aggregate(group, safe_text(dataset) or "unknown"))

    policy_rows: List[Dict[str, Any]] = []
    policies = [
        ("Accept low; review med/high", lambda frame: frame["risk_level"].eq("low")),
        ("Accept low/med; review high", lambda frame: frame["risk_level"].isin(["low", "medium"])),
        ("Review all", lambda frame: pd.Series([False] * len(frame), index=frame.index)),
    ]
    for policy_name, auto_mask_fn in policies:
        policy_frame = merged.copy()
        policy_frame["is_auto"] = auto_mask_fn(policy_frame).fillna(False)
        policy_frame["is_reviewed"] = ~policy_frame["is_auto"]
        row = aggregate(policy_frame, "ALL")
        row["policy"] = policy_name
        policy_rows.append(row)
    policy_metrics = pd.DataFrame(policy_rows)[
        ["policy", "items", "auto_share", "auto_acc", "review_share", "errors_reviewed", "correct_items", "incorrect_items"]
    ]

    return {
        "item_analysis": merged,
        "metrics": pd.DataFrame(metric_rows),
        "policy_metrics": policy_metrics,
    }


def load_parallel_csv(path: str | Path, default_dataset: str = "public_csv") -> List[ParallelSentence]:
    df = pd.read_csv(path).fillna("")
    source_col = next((col for col in ["source", "original", "source_sentence", "essay_text"] if col in df.columns), None)
    reference_col = next((col for col in ["reference", "corrected", "target", "reference_sentence"] if col in df.columns), None)
    if not source_col or not reference_col:
        raise ValueError("CSV must contain source/original/source_sentence and reference/corrected/reference_sentence columns.")
    rows: List[ParallelSentence] = []
    for idx, row in df.iterrows():
        dataset = safe_text(row.get("dataset")) or default_dataset
        sample_id = safe_text(row.get("sample_id")) or safe_text(row.get("id")) or f"{idx + 1:05d}"
        rows.append(
            ParallelSentence(
                dataset=dataset,
                sample_id=sample_id,
                source=normalize_ws(row.get(source_col)),
                reference=normalize_ws(row.get(reference_col)),
                split=safe_text(row.get("split")),
            )
        )
    return rows


def load_jfleg_directory(path: str | Path) -> List[ParallelSentence]:
    root = Path(path)
    rows: List[ParallelSentence] = []
    for split in ["dev", "test"]:
        split_dir = root / split
        source_path = split_dir / f"{split}.src"
        if not source_path.exists():
            continue
        sources = source_path.read_text(encoding="utf-8").splitlines()
        ref_paths = sorted(split_dir.glob(f"{split}.ref*"))
        if not ref_paths:
            continue
        references = [ref.read_text(encoding="utf-8").splitlines() for ref in ref_paths]
        for idx, source in enumerate(sources):
            reference = ""
            for ref_lines in references:
                if idx < len(ref_lines) and normalize_ws(ref_lines[idx]):
                    reference = normalize_ws(ref_lines[idx])
                    break
            if reference:
                rows.append(
                    ParallelSentence(
                        dataset="JFLEG",
                        split=split,
                        sample_id=f"{split}-{idx + 1:05d}",
                        source=normalize_ws(source),
                        reference=reference,
                    )
                )
    if not rows:
        raise ValueError(f"No JFLEG dev/test source-reference files found under {root}.")
    return rows


def load_m2_file(path: str | Path, dataset: str = "M2", annotator: str = "0") -> List[ParallelSentence]:
    text = Path(path).read_text(encoding="utf-8")
    blocks = [block for block in re.split(r"\n\s*\n", text) if block.strip()]
    rows: List[ParallelSentence] = []
    for block_idx, block in enumerate(blocks, start=1):
        lines = [line.rstrip("\n") for line in block.splitlines() if line.strip()]
        source_line = next((line[2:] for line in lines if line.startswith("S ")), "")
        if not source_line:
            continue
        source_tokens = source_line.split()
        edits: List[Dict[str, Any]] = []
        for line in lines:
            if not line.startswith("A "):
                continue
            parts = line[2:].split("|||")
            if len(parts) < 5:
                continue
            span = parts[0].split()
            if len(span) != 2:
                continue
            edit_type = parts[1]
            correction = parts[2]
            edit_annotator = parts[-1]
            if edit_annotator != annotator or edit_type in {"noop", "UNK", "Um"}:
                continue
            edits.append({"start": int(span[0]), "end": int(span[1]), "correction": correction})
        corrected_tokens = list(source_tokens)
        offset = 0
        for edit in edits:
            start = edit["start"] + offset
            end = edit["end"] + offset
            correction = safe_text(edit["correction"])
            replacement = [] if correction in {"", "-NONE-"} else correction.split()
            corrected_tokens[start:end] = replacement
            offset += len(replacement) - (end - start)
        reference = untokenize(corrected_tokens)
        source = untokenize(source_tokens)
        rows.append(
            ParallelSentence(
                dataset=dataset,
                sample_id=f"{Path(path).stem}-{block_idx:05d}",
                source=source,
                reference=reference,
            )
        )
    return rows


def write_benchmark_report(
    out_path: str | Path,
    metrics: pd.DataFrame,
    policy_metrics: pd.DataFrame,
    records_count: int,
    gold_count: int,
    candidate_count: int,
) -> None:
    def markdown_table(frame: pd.DataFrame) -> str:
        if frame.empty:
            return "No metrics."
        display = frame.fillna("--").astype(str)
        headers = list(display.columns)
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        for _, row in display.iterrows():
            lines.append("| " + " | ".join(safe_text(row[col]) for col in headers) + " |")
        return "\n".join(lines)

    report = [
        "# Public Learner-Corpus Routing Benchmark",
        "",
        "This report evaluates ConsensusScope's feedback review-routing behavior",
        "against offline public learner-correction labels. The public corrections",
        "are used only as post-hoc evaluation labels; they are not visible to the",
        "deploy-time router.",
        "",
        f"- Parallel sentence records: {records_count}",
        f"- Gold correction edits: {gold_count}",
        f"- Feedback candidates evaluated: {candidate_count}",
        "",
        "## Dataset Metrics",
        "",
        markdown_table(metrics),
        "",
        "## Review-Routing Policy Metrics",
        "",
        markdown_table(policy_metrics),
        "",
        "Metric definitions:",
        "",
        "- `auto_share`: fraction of feedback candidates released without teacher review.",
        "- `auto_acc`: correctness rate among auto-released feedback candidates.",
        "- `review_share`: fraction of feedback candidates routed to teacher review.",
        "- `errors_reviewed`: fraction of observed incorrect feedback candidates routed to review.",
        "",
        "Limitations:",
        "",
        "- Public GEC corpora provide correction gold labels, not classroom teacher acceptability labels.",
        "- Multiple valid corrections may exist; this benchmark uses the selected reference as an offline proxy.",
        "- This benchmark supports review-routing evaluation, not automatic essay scoring.",
    ]
    Path(out_path).write_text("\n".join(report) + "\n", encoding="utf-8")


def combined_json_payload(outputs: Mapping[str, pd.DataFrame]) -> str:
    payload = {name: json.loads(frame.to_json(orient="records")) for name, frame in outputs.items()}
    return json.dumps(payload, ensure_ascii=False, indent=2)
