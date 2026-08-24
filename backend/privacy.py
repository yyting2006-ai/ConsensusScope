from __future__ import annotations

import re
from typing import Any, Dict, List


PII_PATTERNS = {
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "phone_number": re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)"),
    "student_id": re.compile(
        r"\b(?:student\s*(?:id|number)|学号)\s*[:：#-]\s*[A-Z0-9-]{5,24}\b",
        re.I,
    ),
    "named_identity": re.compile(
        r"\b(?:student\s*name|name|姓名)\s*[:：]\s*[^\n,;，；]{2,60}",
        re.I,
    ),
    "class_identifier": re.compile(
        r"\b(?:class|section|班级)\s*[:：#-]\s*[A-Z0-9_-]{2,24}\b",
        re.I,
    ),
}


def find_pii(text: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    source = str(text or "")
    for pii_type, pattern in PII_PATTERNS.items():
        for match in pattern.finditer(source):
            findings.append(
                {
                    "type": pii_type,
                    "start": match.start(),
                    "end": match.end(),
                    "preview": _masked_preview(match.group(0)),
                }
            )
    findings.sort(key=lambda item: (item["start"], item["end"]))
    return findings


def redact_pii(text: str) -> str:
    source = str(text or "")
    findings = find_pii(source)
    for item in reversed(findings):
        replacement = f"[{item['type'].upper()} REMOVED]"
        source = source[: item["start"]] + replacement + source[item["end"] :]
    return source


def pii_check(text: str) -> Dict[str, Any]:
    findings = find_pii(text)
    return {
        "safe_to_submit": not findings,
        "finding_count": len(findings),
        "finding_types": sorted({item["type"] for item in findings}),
        "findings": findings,
        "redacted_text": redact_pii(text) if findings else str(text or ""),
    }


def _masked_preview(value: str) -> str:
    text = value.strip()
    if len(text) <= 4:
        return "*" * len(text)
    return f"{text[:2]}{'*' * min(12, len(text) - 4)}{text[-2:]}"
