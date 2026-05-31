from __future__ import annotations

import json
import re
from typing import Any, Dict


def parse_model_json(text: str) -> Dict[str, Any]:
    try:
        data = json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text or "", re.S)
        if not match:
            raise ValueError("No JSON object found in model output")
        data = json.loads(match.group(0))

    if not isinstance(data, dict):
        raise ValueError("Model output JSON is not an object")
    for key in ["answer", "reason", "confidence", "evidence"]:
        data.setdefault(key, "" if key != "confidence" else 0.0)
    return data
