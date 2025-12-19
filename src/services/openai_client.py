from __future__ import annotations
import json
import os
from typing import Any, Dict, Optional
import httpx
from src.core.config import get_secret_env_or_aws
from schemas.template_spec import CR2A_TEMPLATE_SPEC

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
        "You are a contracts attorney and risk analyst generating a Clause Risk & "
        "Compliance Analysis (CR2A) report.\n\n"
        "The CR2A JSON must conform to this structure:\n"
        "- SECTION_I: a flat object with contract overview fields.\n"
        "- SECTION_II through SECTION_VI: arrays of SectionItem objects.\n"
        "- Each SectionItem has: item_number, item_title, clauses, closing_line.\n"
        "- Each clauses entry is a ClauseBlock with exactly these fields:\n"
        "  clause_language, clause_summary, risk_triggers, "
        "flow_down_obligations, redline_recommendations, "
        "harmful_language_conflicts.\n"
        "Return ONLY valid JSON; no commentary or markdown."
    )

    payload_for_llm = {
    "current_cr2a": payload,
    "template_spec": CR2A_TEMPLATE_SPEC,
    }

    user_text = (
        "You are given a JSON object with two keys:\n"
        "- 'current_cr2a': a partial CR2A analysis of a contract.\n"
        "- 'template_spec': the complete list of required SectionItem templates "
        "for SECTION_II through SECTION_VI.\n\n"
        "Your task is to produce a FINAL CR2A JSON object that:\n"
        "1) Preserves SECTION_I from current_cr2a, enriching fields only where the "
        "contract clearly provides information.\n"
        "2) For EACH SectionItem listed in template_spec for SECTION_II–SECTION_VI, "
        "creates an element in that section's array with:\n"
        "   - item_number and item_title exactly as in template_spec.\n"
        "   - closing_line copied from template_spec for that section.\n"
        "   - clauses: an array containing one or more ClauseBlock objects.\n"
        "3) For EVERY ClauseBlock you create, you MUST fill all six fields:\n"
        "   clause_language, clause_summary, risk_triggers, "
        "flow_down_obligations, redline_recommendations, "
        "harmful_language_conflicts.\n\n"
        "Rules:\n"
        "- Do NOT invent new SectionItem records or change item_title text.\n"
        "- Do NOT omit any items that appear in template_spec; every item "
        "must appear in the final JSON.\n"
        "- If the contract is silent for an item, you MUST still create a single "
        "ClauseBlock for that item and set all six fields to a clear statement "
        "such as 'Not present in contract.' plus a brief risk explanation.\n"
        "- You may add more than one ClauseBlock for an item if the contract "
        "has multiple distinct clauses affecting that risk area.\n"
        "- Only return the final CR2A JSON object. No explanations.\n\n"
        f"{json.dumps(llm_input, ensure_ascii=False)}"
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
            {"role": "user", "content": user_text},
        ],
        "response_format": {"type": "json_object"},
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