from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.llm.clients import get_client


MODELS = ["deepseek", "qwen", "glm", "kimi", "judge"]
OUTPUT_PATH = ROOT / "data" / "outputs" / "api_connection_test.csv"
TEST_PROMPT = '请用JSON回答：{"answer":"A","reason":"test","confidence":0.5,"evidence":"无"}'


def check_one_model(model_name: str) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "model": model_name,
        "configured": False,
        "reachable": False,
        "json_parse_ok": False,
        "error_message": "",
    }
    try:
        client = get_client(model_name)
    except Exception as exc:
        row["error_message"] = str(exc)
        return row

    row["configured"] = bool(client.is_available)
    if not client.is_available:
        row["error_message"] = "未配置 API key，已跳过"
        return row

    result = client.call_json(TEST_PROMPT, temperature=0.0, max_tokens=120)
    request_error = str(result.get("request_error", "") or "")
    parse_error = str(result.get("parse_error", "") or "")
    row["reachable"] = not bool(request_error)
    row["json_parse_ok"] = row["reachable"] and not bool(parse_error) and isinstance(result, dict)

    if request_error:
        row["error_message"] = request_error[:500]
    elif parse_error:
        row["error_message"] = parse_error[:500]
    elif not row["json_parse_ok"]:
        row["error_message"] = "返回结果不是可用 JSON 对象"
    return row


def main() -> None:
    load_dotenv(ROOT / ".env")
    rows: List[Dict[str, Any]] = []
    print("Testing API connections. API keys will not be printed.")
    for model in MODELS:
        row = check_one_model(model)
        rows.append(row)
        if not row["configured"]:
            status = "SKIP"
        elif row["reachable"] and row["json_parse_ok"]:
            status = "OK"
        elif row["reachable"]:
            status = "PARSE_FAIL"
        else:
            status = "FAIL"
        print(
            f"[{status}] {model}: "
            f"configured={row['configured']} "
            f"reachable={row['reachable']} "
            f"json_parse_ok={row['json_parse_ok']} "
            f"error={row['error_message']}"
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"Saved results to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
