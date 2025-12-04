from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

import httpx

from .config import get_secret_env_or_aws, AppConfig

OPENAI_BASE = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")
OPENAI_MODEL_DEFAULT = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _get_api_key() -> Optional[str]:
    key = get_secret_env_or_aws("OPENAI_API_KEY", "OPENAI_SECRET_ARN")
    return key


def refine_cr2a(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Best-effort JSON refinement with OpenAI. If no key is present, raises.
    Keeps token usage low by prompting for structured JSON only.
    """
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY/OPENAI_SECRET_ARN not set")

    model = os.getenv("OPENAI_MODEL", OPENAI_MODEL_DEFAULT)

    system = (
        "You are an assistant that improves a contract risk report JSON. "
        "Only return valid JSON with the same top-level keys: SECTION_I, SECTION_II..SECTION_VI (arrays), PROVENANCE. "
        "Do not add prose; keep fields concise. If information is missing, keep existing values."
    )
    user = (
        "Refine the following JSON fields for clarity and completeness. "
        "Do not change the structure. Return JSON only.\n\n"
        + json.dumps(payload, ensure_ascii=False)
    )

    url = f"{OPENAI_BASE}/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    with httpx.Client(timeout=60) as client:
        resp = client.post(url, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        refined = json.loads(content)
        # Basic sanity: preserve required top-level keys if missing
        for k in ["SECTION_I", "SECTION_II", "SECTION_III", "SECTION_IV", "SECTION_V", "SECTION_VI"]:
            if k not in refined:
                refined[k] = payload.get(k, [] if k != "SECTION_I" else {})
        if "PROVENANCE" not in refined and "PROVENANCE" in payload:
            refined["PROVENANCE"] = payload["PROVENANCE"]
        return refined