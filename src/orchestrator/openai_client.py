# openai_client.py
# A tiny OpenAI client with Structured Outputs (JSON Schema) + fallback.
# Provides build_client_from_env(...) → client.extract_json(...)
from __future__ import annotations
# tdlib imports
import os                                   # read env vars
from typing import Any, Dict, List, Optional # typing helpers
# third-party imports
import httpx                                # HTTP client
import orjson                               # fast JSON encode/decode

# Environment & defaults           # default temperature (0=
def _first_text(output: Any) -> Optional[str]:
    """
    Best-effort extractor for the first text leaf from an OpenAI Responses payload.
    Supports:
      - SDK objects with `.output_text`
      - dicts: {"output":[{"content":[{"type":"output_text","text":"..."}]}]}
      - simple {"content": "..."} fallbacks
    Returns None if nothing textual is found.
    """
    # 1) SDK convenience property
    try:
        txt = getattr(output, "output_text", None)
        if isinstance(txt, str) and txt.strip():
            return txt
    except Exception:
        pass
    # 2) Structured list form
    try:
        # works for both objects with .output and dicts with ["output"]
        items = getattr(output, "output", None) or (isinstance(output, dict) and output.get("output"))
        if items and isinstance(items, list):
            content = items[0].get("content") if isinstance(items[0], dict) else None
            if content and isinstance(content, list):
                text = content[0].get("text")
                if isinstance(text, str) and text.strip():
                    return text
    except Exception:
        pass
    # 3) Simpler dict fallback
    if isinstance(output, dict):
        cand = output.get("content") or output.get("output_text")
        if isinstance(cand, str) and cand.strip():
            return cand
    return None

def _masksecret(s: Optional[str], n: int = 3, mask_char: str = "•") -> str:
    """
    Redact secrets for logs: keep the first `n` characters, mask the rest.
    Examples:
      "sk-abcdef" -> "sk-•••••"   (n=3)
    """
    if not s:
        return ""
    if n <= 0:
        return mask_char * len(s)
    if n >= len(s):
        # caller opted to keep >= length; still mask at least one char for safety
        return s[:-1] + mask_char if len(s) > 0 else ""
    return s[:n] + (mask_char * (len(s) - n))

# Client
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
    # public: schema-constrained extraction
    def extract_json(
        self,
        *,                                           # force keyword-only for clarity/safety
        text: str,                                   # raw contract text
        schema: Dict[str, Any],                      # JSON Schema to enforce
        system_prompt: str,                          # system message
        name: str = "aps_contract_output",           # schema label
    ) -> Dict[str, Any]:
        """
        Call the OpenAI Responses API with strict JSON Schema enforcement.
        If the server rejects schema mode (4xx/5xx), fall back to json_object and parse.
        Returns a Python dict parsed from the model's JSON output, or raises OpenAIError.
        """
        # basic input validation (fail fast, avoid wasting a call)
        if not isinstance(text, str) or not text.strip():
            raise OpenAIError("extract_json: 'text' is empty.")
        if not isinstance(schema, dict) or not schema:
            raise OpenAIError("extract_json: 'schema' is missing or not a dict.")
        # endpoint and message assembly
        url = f"{self.base_url}/responses"        # normalized base_url ensures no double slashes
        messages: List[Dict[str, Any]] = [        # minimal, predictable message shape
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]
        # Primary attempt: strict JSON Schema
        primary_payload: Dict[str, Any] = {
            "model": self.model,
            "input": messages,                    # Responses API expects 'input' for messages
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": name,           # schema name/label
                    "strict": True,         # hard enforcement
                    "schema": schema,       # the actual JSON Schema
                },
            },
            "temperature": self.temperature # deterministic by default
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(url, headers=self._headers, json=primary_payload)
                if r.status_code >= 400:
                    # fallback: ask for any well-formed JSON object
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
            except httpx.RequestError as e:
                # network/timeout layer issues
                raise OpenAIError(f"HTTP error: {e}") from e
            except ValueError as e:
                # response body not JSON
                raise OpenAIError(f"Invalid JSON from server: {e}") from e
            # extract the text leaf from Responses API shapes
            # Prefer explicit 'output_text'; otherwise walk 'output' list; otherwise allow 'content'.
            text_out = (
                data.get("output_text")            # direct text field
                or _first_text(data.get("output")) # nested array form
                or data.get("content")             # older compatibility
                or "{}"                            # make sure we parse something
            )
            try:
                obj = orjson.loads(text_out)
            except Exception as e:
                # provide a short preview to aid debugging without leaking full payloads
                preview = text_out if isinstance(text_out, str) else str(text_out)
                preview = preview[:400]
                raise OpenAIError(f"Model returned non-JSON payload: {e}\n{preview}") from e
            if not isinstance(obj, dict):
                raise OpenAIError(f"Model returned JSON, but not an object: {type(obj)}")
            return obj  # return the parsed object
        # Perform HTTP request synchronously
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(url, headers=self._headers, json=primary_payload)
                if r.status_code >= 400:
                    # Fallback: ask for any well-formed JSON object
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
        except httpx.RequestError as e:
            # Network/timeout layer issues
            raise OpenAIError(f"HTTP error: {e}") from e
        except ValueError as e:
            # Response body not JSON
            raise OpenAIError(f"Invalid JSON from server: {e}") from e
        # Extract text from the Responses API shape in a robust way
        # Prefer explicit 'output_text'; otherwise walk 'output' list; otherwise allow 'content'.
        text_out = (
            data.get("output_text")            # direct text field
            or _first_text(data.get("output")) # nested array form
            or data.get("content")             # older compatibility
            or "{}"                            # make sure we parse something
        )
        # Parse the model's JSON payload
        try:
            parsed = orjson.loads(text_out)
        except Exception as e:
            # Provide a short preview to aid debugging without leaking full payloads
            preview = text_out if isinstance(text_out, str) else str(text_out)
            preview = preview[:400]
            raise OpenAIError(f"Model returned non-JSON payload: {e}\n{preview}") from e
        if not isinstance(parsed, dict):
            raise OpenAIError(f"Model returned JSON, but not an object: {type(parsed)}")
        return parsed  # return the parsed object
        # parse the model's JSON payload safely
        try:
            return orjson.loads(text_out)      # return parsed JSON
        except Exception as e:
            # Keep a short preview of what we got to aid debugging
            preview = text_out if isinstance(text_out, str) else str(text_out)
            preview = preview[:400]             # limit length
            raise OpenAIError(f"Model returned non-JSON payload: {e}\n{preview}")
        if not isinstance(obj, dict):
            # Contract: downstream validators expect a top-level JSON object
            raise OpenAIError(f"Model returned JSON, but not an object: {type(obj)}")
        return obj  # return the parsed object

# Factory
def build_client_from_env(
    *,
    model: Optional[str] = None,            # override model if desired
    temperature: Optional[float] = None,    # override temperature
    timeout: int = 120,                     # request timeout (seconds)
) -> OpenAIClient:
    """
    Construct an OpenAIClient using environment variables, with optional overrides.
    The CLI calls this after load_dotenv() so .env values are available.
    """
    # load configuration from environment
    api_key = os.getenv("OPENAI_API_KEY")                              # required API key
    base = os.getenv("OPENAI_BASE_URL", OPENAI_BASE)                   # base URL
    mdl = model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)            # model name
    # resolve temperature precedence
    if temperature is not None:
        tmp = temperature
    else:
        temp_env = os.getenv("OPENAI_TEMPERATURE")
        if temp_env is not None:
            try:
                tmp = float(temp_env)
            except ValueError:
                tmp = DEFAULT_TEMP
        else:
            tmp = DEFAULT_TEMP
    # create and return configured client
    return OpenAIClient(
        api_key=api_key,                                               # required key
        base_url=base,                                                 # API base
        model=mdl,                                                     # model name
        temperature=tmp,                                               # temperature (float)
        timeout=timeout,                                               # request timeout
    )
