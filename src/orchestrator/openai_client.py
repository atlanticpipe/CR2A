# openai_client.py
# A tiny OpenAI client with Structured Outputs (JSON Schema) + fallback.
# Provides build_client_from_env(...) → client.extract_json(...)

from __future__ import annotations

# --- stdlib imports
import os                                   # read env vars
from typing import Any, Dict, List, Optional # typing helpers

# --- third-party imports
import httpx                                # HTTP client
import orjson                               # fast JSON encode/decode


# =============================
# Environment & defaults
# =============================
OPENAI_BASE = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")  # API base URL
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")                 # default model
DEFAULT_TEMP = float(os.getenv("OPENAI_TEMPERATURE", "0") or 0)               # default temperature (0=deterministic)


# =============================
# Errors
# =============================
class OpenAIError(RuntimeError):
    """Raised for any OpenAI client errors."""
    pass


# =============================
# Small helpers
# =============================
def _first_text(output: Any) -> Optional[str]:
    """
    Responses API shape helper:
      {"output":[{"content":[{"type":"output_text","text":"..."}]}]}
    We try to pull the first text leaf out of that structure.
    """
    try:
        return output[0]["content"][0]["text"]
    except Exception:
        return None


def _mask(s: str, n: int = 8) -> str:
    """Mask a secret for logs (keep first n chars)."""
    return f"{s[:n]}..." if s else ""


# =============================
# Client
# =============================
class OpenAIClient:
    """Tiny client that performs a schema-constrained call with fallback."""

    def __init__(
        self,
        api_key: str,                          # required API key
        base_url: str = OPENAI_BASE,           # base API URL
        model: str = DEFAULT_MODEL,            # model name
        temperature: float = DEFAULT_TEMP,     # sampling temp
        timeout: int = 120,                    # request timeout (seconds)
    ) -> None:
        if not api_key:
            raise OpenAIError(
                "OPENAI_API_KEY is not set. Please set it in your environment variables. See the README or OpenAI docs for setup instructions."
            )
        self.api_key = api_key                      # store key for headers
        self.base_url = base_url.rstrip("/")        # normalize base url
        self.model = model                          # store model name
        self.temperature = float(temperature or 0)  # cast to float
        self.timeout = timeout                      # seconds

        # prebuild headers to avoid redoing work on every call
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",  # auth header
            "Content-Type": "application/json",         # JSON content type
        }

    # -------------------------
    # public: schema-constrained extraction
    # -------------------------
    def extract_json(
        self,
        *,
        text: str,                                   # raw contract text
        schema: Dict[str, Any],                      # JSON Schema to enforce
        system_prompt: str,                          # system message
        name: str = "aps_contract_output",           # schema label
        policy_root: Optional[str] = None,           # optional for trace/debug
    ) -> Dict[str, Any]:
        """
        Use the Responses API with JSON Schema (strict). If that fails (e.g. 4xx/5xx),
        we fall back to `json_object` and then parse/return the JSON.
        """
        # API key validation is now performed during client initialization.

        url = f"{self.base_url}/responses"              # endpoint URL

        # Build messages for the Responses API:
        # Keep the format simple: system + user(text)
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},   # role instruction
            {"role": "user", "content": text},              # contract content
        ]

        # Primary attempt: strict JSON Schema
        primary_payload = {
            "model": self.model,            # model
            "input": messages,              # messages array
            "response_format": {            # tell the API to use schema
                "type": "json_schema",
                "json_schema": {
                    "name": name,           # schema name/label
                    "strict": True,         # hard enforcement
                    "schema": schema,       # the actual JSON Schema
                },
            },
            "temperature": self.temperature # deterministic by default
        }

        # Perform HTTP request synchronously
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(url, headers=self._headers, json=primary_payload)  # send primary
            if r.status_code >= 400:
                # Fallback to json_object mode if the server rejected schema
                fb_payload = {
                    "model": self.model,            # model
                    "input": messages,              # messages
                    "response_format": {"type": "json_object"},  # ask for a JSON object
                    "temperature": self.temperature
                }
                r2 = client.post(url, headers=self._headers, json=fb_payload)  # fallback call
                if r2.status_code >= 400:
                    raise OpenAIError(f"OpenAI error {r2.status_code}: {r2.text}")  # fail if both fail
                data = r2.json()   # fallback JSON
            else:
                data = r.json()    # primary JSON

        # Extract text from the Responses API shape in a robust way
        text_out = (
            data.get("output_text")            # direct text field
            or _first_text(data.get("output")) # nested array form
            or data.get("content")             # older compatibility
            or "{}"                            # make sure we parse something
        )

        try:
            return orjson.loads(text_out)      # return parsed JSON
        except Exception as e:
            # Keep a short preview of what we got to aid debugging
            preview = text_out if len(text_out) < 400 else text_out[:400]
            raise OpenAIError(f"Model returned non-JSON payload: {e}\n{preview}")


# =============================
# Factory
# =============================
def build_client_from_env(
    *,
    model: Optional[str] = None,            # override model if desired
    temperature: Optional[float] = None,    # override temperature
    timeout: int = 120,                     # request timeout
) -> OpenAIClient:
    """
    Construct an OpenAIClient using environment variables, with optional overrides.
    The CLI calls this after load_dotenv() so .env values are available.
    """
    api_key = os.getenv("OPENAI_API_KEY")                     # get API key
    base = os.getenv("OPENAI_BASE_URL", OPENAI_BASE)          # base URL
    mdl = model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)   # model selection

    if temperature is not None:
        tmp = temperature
    else:
        temp_env = os.getenv("OPENAI_TEMPERATURE")
        if temp_env is not None:
            tmp = float(temp_env)
        else:
            tmp = DEFAULT_TEMP

    # For minimal visibility (useful when troubleshooting), you may log the API key prefix.
    # However, logging API keys (even masked) is discouraged for security reasons.
    # If needed, use a proper logging framework with configurable levels.

    return OpenAIClient(                                      # return configured client
        api_key=api_key,                                      # required
        base_url=base,                                        # API base
        model=mdl,                                            # model
        temperature=tmp,                                      # temperature
        timeout=timeout,                                      # timeout seconds
    )