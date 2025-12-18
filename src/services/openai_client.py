from __future__ import annotations
import json
import os
from typing import Any, Dict, Optional
import httpx
from src.core.config import get_secret_env_or_aws

class OpenAIClientError(RuntimeError):
    """Typed error that carries an error category for HTTP mapping."""

    def __init__(self, category: str, message: str):
        super().__init__(message)
        self.category = category

OPENAI_BASE = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")
OPENAI_MODEL_DEFAULT = os.getenv("OPENAI_MODEL", "gpt-5")

def _get_api_key() -> Optional[str]:
    # Resolve key from env or AWS Secrets Manager; keep secrets out of logs.
    key = get_secret_env_or_aws("OPENAI_API_KEY", "OPENAI_SECRET_ARN")
    return key

def _extract_text(data: Dict[str, Any]) -> str:
    # Prefer Responses API shape; fall back to chat-style messages if present.
    if isinstance(data, dict):
        output = data.get("output") or []
        for block in output:
            for item in block.get("content", []):
                if item.get("type") == "output_text" and item.get("text"):
                    return str(item["text"])
        choices = data.get("choices") or []
        if choices:
            msg = choices[0].get("message", {})
            content = msg.get("content")
            if isinstance(content, str):
                return content
    raise RuntimeError("OpenAI response missing text content")

def _parse_json_payload(raw_text: str) -> Dict[str, Any]:
    try:
        # Fast path when the model returned clean JSON.
        return json.loads(raw_text)
    except Exception:
        # Best-effort salvage: slice the outermost object to avoid total failure.
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end > start:
            return json.loads(raw_text[start : end + 1])
        raise

def refine_cr2a(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Best-effort JSON refinement with OpenAI. If no key is present, raises.
    Keeps token usage low by prompting for structured JSON only.
    """
    api_key = _get_api_key()
    if not api_key:
        # Fail fast when no credentials are available so callers can skip refinement.
        raise OpenAIClientError("ValidationError", "Set OPENAI_API_KEY or OPENAI_SECRET_ARN to enable LLM refinement.")

    model = os.getenv("OPENAI_MODEL", OPENAI_MODEL_DEFAULT)
    timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))

    system_text = (
        "You are a JSON-only contract analysis assistant. "
        "Return structured JSON that keeps the same shape and fields that were provided. "
        "Do not add markdown or commentary; only emit valid JSON."
    )

    url = f"{OPENAI_BASE}/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    org_id = os.getenv("OPENAI_ORG_ID")
    if org_id:
        headers["OpenAI-Organization"] = org_id
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_text},
            {
                "role": "user",
                "content": f"Polish the JSON for clarity without changing its keys or nesting. Return JSON only.\n\n{json.dumps(payload, ensure_ascii=False)}"
            },
        ],
        "response_format": {"type": "json_object"},  # This enforces JSON-only output
        "temperature": 0,
        "max_tokens": 2000,
    }

    try:
        # Call the Responses API with a strict JSON-only contract to keep structure intact.
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()

        # Pull the text content and decode as JSON; salvage partial objects when needed.
        content = _extract_text(data)
        refined = _parse_json_payload(content)

        # Backfill any missing sections to keep schema alignment stable for downstream steps.
        for k in ["SECTION_I", "SECTION_II", "SECTION_III", "SECTION_IV", "SECTION_V", "SECTION_VI"]:
            if k not in refined:
                refined[k] = payload.get(k, [] if k != "SECTION_I" else {})

        return refined
    except httpx.TimeoutException as exc:
        # Bubble up a concise timeout message so the caller can retry or bypass refinement.
        raise OpenAIClientError("TimeoutError", f"OpenAI request timed out: {exc}")
    except httpx.RequestError as exc:
        # Network failures should not be silent; expose enough detail without leaking secrets.
        raise OpenAIClientError("NetworkError", f"OpenAI request failed: {exc}")
    except OpenAIClientError:
        # Propagate typed errors unchanged for upstream mapping.
        raise
    except Exception as exc:
        # Catch-all to avoid surfacing raw tracebacks to the API surface.
        raise OpenAIClientError("ProcessingError", f"OpenAI refinement failed: {exc}")