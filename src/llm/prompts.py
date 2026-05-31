from __future__ import annotations

import json
from typing import Any, Dict, List


def _compact_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def build_answer_prompt(sample: Dict[str, Any]) -> str:
    """Build the independent-answer prompt for one normalized sample."""

    options = sample.get("options", "")
    if isinstance(options, (list, dict)):
        options_text = _compact_json(options)
    else:
        options_text = str(options or "")

    return f"""你是多大模型协同决策可靠性实验中的一个独立答题模型。
请只根据题目信息独立作答，不要参考其他模型。

请严格输出一个 JSON 对象，不要输出 Markdown，不要输出额外解释。
JSON 格式必须为：
{{
  "answer": "最终答案，只写选项或简短答案",
  "reason": "简要推理理由，不超过100字",
  "confidence": 0.0,
  "evidence": "支持答案的依据；没有则写无"
}}

字段要求：
- answer: 如果是选择题，只写 A/B/C/D/E；如果是判断或事实核查题，写 SUPPORTED/REFUTED/NOT ENOUGH INFO 或 true/false；其他题写简短答案。
- reason: 不超过100字。
- confidence: 0.0 到 1.0 之间的小数。
- evidence: 支持答案的依据；没有则写“无”。

样本信息：
- id: {sample.get("id", "")}
- dataset: {sample.get("dataset", "")}
- task_type: {sample.get("task_type", "")}
- question: {sample.get("question", "")}
- options: {options_text}
- category: {sample.get("category", "")}
"""


def build_judge_prompt(sample: Dict[str, Any], model_outputs: List[Dict[str, Any]]) -> str:
    """Build the fixed-adjudicator prompt for multiple model outputs."""

    outputs_text = _compact_json(model_outputs)
    return f"""你是多大模型协同决策实验中的固定裁决器。
请根据多个模型的 answer、reason、confidence、evidence，对同一道题给出最终裁决。

请严格输出一个 JSON 对象，不要输出 Markdown，不要输出额外解释。
JSON 格式必须为：
{{
  "final_answer": "最终裁决答案",
  "decision_reason": "裁决理由，不超过150字",
  "risk_level": "low",
  "confidence": 0.0
}}

字段要求：
- final_answer: 最终裁决答案。选择题只写 A/B/C/D/E；事实核查题写 SUPPORTED/REFUTED/NOT ENOUGH INFO；其他题写简短答案。
- decision_reason: 说明为何采纳该答案，需考虑多数一致性、证据质量、置信度和少数派意见，不超过150字。
- risk_level: 只能是 low、medium、high。
- confidence: 0.0 到 1.0 之间的小数。

题目信息：
- id: {sample.get("id", "")}
- dataset: {sample.get("dataset", "")}
- task_type: {sample.get("task_type", "")}
- question: {sample.get("question", "")}
- options: {sample.get("options", "")}

模型输出：
{outputs_text}
"""
