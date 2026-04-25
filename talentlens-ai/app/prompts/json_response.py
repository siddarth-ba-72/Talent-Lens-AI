from __future__ import annotations

import json
import re
from typing import Any


_JSON_BLOCK_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


def parse_json_object(raw_text: str) -> dict[str, Any]:
    cleaned = (raw_text or "").strip()
    if not cleaned:
        raise ValueError("LLM returned an empty response")

    if cleaned.startswith("```"):
        cleaned = _strip_markdown_fence(cleaned)

    try:
        payload = json.loads(cleaned)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass

    block_match = _JSON_BLOCK_PATTERN.search(cleaned)
    if not block_match:
        raise ValueError("No JSON object found in LLM response")

    payload = json.loads(block_match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("LLM JSON response must be an object")
    return payload


def _strip_markdown_fence(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return text

    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()
