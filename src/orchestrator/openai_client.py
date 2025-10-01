from __future__ import annotations
import os, httpx, orjson
from typing import Dict, Any, List

OPENAI_BASE = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
  # Don’t crash the import; fail at call-time with a clear message
  pass

HEADERS = {
  "Authorization": f"Bearer {API_KEY or ''}",
  "Content-Type": "application/json",
}

class OpenAIError(RuntimeError):
  pass

async def llm_structured(messages: List[Dict[str, Any]], json_schema: Dict[str, Any]) -> Dict[str, Any]:
  """
  Try the Responses API with JSON Schema (strict). If unavailable or rejected,
  fall back to JSON-object mode and validate locally later.
  """
  if not API_KEY:
    raise OpenAIError("OPENAI_API_KEY is not set")

url = f"{OPENAI_BASE}/responses"
# Primary attempt: Structured Outputs (schema-constrained)
payload = {
  "model": OPENAI_MODEL,
  "input": messages,
  "response_format": {
  "type": "json_schema",
  "json_schema": {"name": "aps_contract_output", "strict": True, "schema": json_schema},
  },
  "temperature": 0.1,
}

async with httpx.AsyncClient(timeout=120) as client:
  r = await client.post(url, headers=HEADERS, json=payload)

  # If 4xx/5xx, try fallback to json_object mode
  if r.status_code >= 400:
    fb = {
      "model": OPENAI_MODEL,
      "input": messages,
      "response_format": {"type": "json_object"},
      "temperature": 0.1,
    }
    r2 = await client.post(url, headers=HEADERS, json=fb)
    if r2.status_code >= 400:
      raise OpenAIError(f"OpenAI error {r2.status_code}: {r2.text}")
    data = r2.json()
  else:
    data = r.json()

# Extract JSON text robustly (Responses API shape)
text = (
  data.get("output_text")
  or _first_text(data.get("output"))
  or data.get("content")
  or "{}"
)
try:
  return orjson.loads(text)
except Exception as e:
  raise OpenAIError(f"Model returned non-JSON payload: {e}\n{text[:400]}")

def _first_text(output: Any) -> str | None:
  """
  Responses API returns: {"output":[{"content":[{"type":"output_text","text":"..."}]}]}
  """
  try:
    return output[0]["content"][0]["text"]
  except Exception:
    return None

add OpenAI client with structured-outputs + fallback
