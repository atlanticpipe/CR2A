# -*- coding: utf-8 -*-
# Thin OpenAI client used by the orchestrator with Structured Outputs + fallback.

from __future__ import annotations  # allow forward refs in type hints
import os                           # read environment variables
import httpx                        # async HTTP client
import orjson as json               # fast JSON (used for final parse)
from typing import Dict, Any, List  # typing annotations


# ---- Environment + defaults ---------------------------------------------------
OPENAI_BASE = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")   # API base URL
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")                   # default model
API_KEY = os.getenv("OPENAI_API_KEY")                                     # bearer token

# Build common headers once; empty token is OK at import (checked at call time)
HEADERS = {
    "Authorization": f"Bearer {API_KEY or ''}",   # auth header (may be empty now)
    "Content-Type": "application/json",           # send JSON body
}


class OpenAIError(RuntimeError):
    """Raised for transport/format errors coming from the API or bad responses."""
    pass


async def llm_structured(messages: List[Dict[str, Any]], json_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call the OpenAI Responses API and ask for a JSON payload constrained by `json_schema`.
    If the server rejects structured outputs, fall back to `json_object` and validate locally.
    Returns a parsed Python dict. Raises OpenAIError on transport/format issues.
    """
    # --- basic sanity checks before doing IO ---
    if not API_KEY:  # enforce presence of the API key at *call* time
        raise OpenAIError("OPENAI_API_KEY is not set")

    url = f"{OPENAI_BASE}/responses"  # final endpoint for Responses API

    # Primary attempt: Structured Outputs (strict JSON Schema on the server)
    payload = {
        "model": OPENAI_MODEL,                      # which model to use
        "input": messages,                          # chat-style list of messages
        "response_format": {                        # strict JSON Schema enforcement
            "type": "json_schema",
            "json_schema": {
                "name": "aps_contract_output",      # schema name (arbitrary but stable)
                "strict": True,                     # require strict server-side validation
                "schema": json_schema               # the actual Draft-07 schema
            },
        },
        "temperature": 0.1,                         # keep outputs deterministic-ish
    }

    async with httpx.AsyncClient(timeout=120) as client:              # create client w/ timeout
        r = await client.post(url, headers=HEADERS, json=payload)     # send primary request

        # Fallback path: if server rejects structured outputs, request a plain JSON object
        if r.status_code >= 400:
            fb = {
                "model": OPENAI_MODEL,                                # same model
                "input": messages,                                    # same messages
                "response_format": {"type": "json_object"},           # relaxed format
                "temperature": 0.1,
            }
            r2 = await client.post(url, headers=HEADERS, json=fb)     # send fallback request
            if r2.status_code >= 400:                                 # both attempts failed
                raise OpenAIError(f"OpenAI error {r2.status_code}: {r2.text}")
            data = r2.json()                                          # parse HTTP JSON frame
        else:
            data = r.json()                                           # parse HTTP JSON frame

    # Extract the assistant JSON text from the Responses API shape
    text = (
        data.get("output_text")                # simple path (some SDKs flatten)
        or _first_text(data.get("output"))     # canonical Responses API structure
        or data.get("content")                 # defensive fallback
        or "{}"                                # ensure we pass something to the parser
    )

    # Parse the model’s JSON string robustly
    try:
        return json.loads(text)                # fast JSON → Python dict
    except Exception as e:
        # Include a small snippet of the bad payload for debugging
        snippet = text[:400].replace("\n", "\\n")
        raise OpenAIError(f"Model returned non-JSON payload: {e}\n{snippet}")


def _first_text(output: Any) -> str | None:
    """
    Pull the first text chunk from the Responses API shape:
      {"output":[{"content":[{"type":"output_text","text":"..."}]}]}
    Returns None if the expected shape isn’t present.
    """
    try:
        return output[0]["content"][0]["text"]  # walk the nested arrays/maps
    except Exception:
        return None

# add near the bottom of openai_client.py

class _Client:
    """Tiny wrapper so cli.py can call client.extract_json(...)."""
    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("OPENAI_MODEL", OPENAI_MODEL)

    async def extract_json_async(self, text: str, schema: dict, system_prompt: str, name: str = "contract_template_v1") -> dict:
        # build messages in the format llm_structured expects
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]
        return await llm_structured(messages, schema)

    def extract_json(self, text: str, schema: dict, system_prompt: str, name: str = "contract_template_v1") -> dict:
        # convenience sync wrapper for CLI (runs the coroutine)
        import asyncio
        return asyncio.run(self.extract_json_async(text, schema, system_prompt, name))

def build_client_from_env() -> _Client:
    """Factory used by cli.py; honors OPENAI_MODEL if set."""
    return _Client()
