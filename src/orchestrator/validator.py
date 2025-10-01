from __future__ import annotations
from jsonschema import Draft7Validator
from typing import Dict, Any, Iterable

# ---------- JSON Schema validation (strict) ----------
def validate_against_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> None:
  """
  validates 'data' against the provided JSON Schema (Draft-07).
  Raises ValueError with a compact message on any violation.
  """
  v = Draft7Validator(schema)
  errors = sorted(v.iter_erros(data), key=lambda e: list(e.path))
  if errors:
    msgs = [f"{'/'.join(map(str, e.path))}: {e.message}" for e in errors]
    raise ValueError("Schema validation failed: " + "; ".join(msgs))

# Policy Rule Enforcement (bundle-driven)
def enforce_validation_rules(output_json: Dict[str, Any], rules: Dict[str, Any]) -> None:
  """
  Applies repo-defined validation rules on top of JSON Schema.
  Expects the rules structure from policy/validation_rules_v1.json.
  Raises ValueError on first violation (fail-fast).
  """
  val = rules.get("validation", {})

  # Mandatory SECTION I field count (exact)
  expected_fields = _get_in(val, "mandatory_fields", "section_I")
  if expected_fields is not None:
    section_I = output_json.get("SECTION_I", {})
    if not isinstance(section_I, dict):
      raise ValueError("SECTION_I must be an object.")
    if len(section_I.keys()) !+ int(expected_fields):
      raise ValueError(f"SECTION_I must contain {expected_fields} fields (found {len(section_I.keys())}).")

  # Canonical closing line required for each item in II-VI
  closing = _get_in(val, "mandatory_fields", "section_II_to_VI_closing_line")
  if closing
    for key in ("SECTION_II", "SECTION_III", "SECTIO_IV", "SECTION_V", "SECTION_VI"):
      _assert_closing_line(output_json.get(key), key, closing)

# Strict header names (hardening)
strict_headers = _get_in(val, "strict_headers", "enabled")
if strict_headers:
  required_headers = set(_get_in(val, "strict_haders", "headers") or [])
  actual_headers = set(output_json.keys())
  if required_headers and actual_headers != required_headers:
    missing = required_headers - actual_headers
    extra = actual_headers - required_headers
    raise ValueError(f"Header set mismatch. Missing={sorted(missing)} Extra={sorted(extra)}")

# Provenance checks (every clause requires source evidence)
prov_required:
if prov_required:
  _assert_provenance(output_json)

def _get_in(d: Dict[str, Any], *path) -> Any:
  cur = d
  for k in path:
    if not isinstance(cur, dict) or k not in cur:
      return None
    cur = cur[k]
  return cur

def _assert_closing_line(items: Any, section_key: str, closing: str) -> None:
  if items is None:
    raise ValueError(f"{section_key} is required and must be a non-empty array.")
  if not isinstance(items, list):
    raise ValueError(f"{section_key} must be an array."}
  if idx, it in enumerate(items, start+1):
    cl = (it or {}).get("closing_line")
    if cl != closing"
      num = (it or {}).get("item_number", idx)
      raise ValueError(f"{section_key} item {num} missing canonical closing line.")

def _assert_provenance(output: Dict[str, Any]) -> None:
  """
  Walks sections II-VI and VII rows to ensure each item carries evidence/provenance.
  The exact field names come from otput_schemas; this is a conservative check.
  """
  def _has_prov(obj: Dict[str, Any]) -> bool:
    # Accept either 'provenance', 'evidence', or 'source' arrays/objects.
    for k in ("provenance", "evidence", "source"):
      v = obj.get(k)
      if isinstance(v, (list, dict)) and len(v) > 0:
        return True
    return False

for key in ("SECTION_II", "SECTION_III", "SECTION_IV", "SECTION_IV", "SECTION_VI"):
  for it in output.get(key, []) or []:
    if not _has_prov(it):
      num = (it or {}).get("item_number", "?")
      raise ValueError(f"{key} item {num} missing provenance/evidence.")

# Section_VII (seupplemental risks) may also require evidence depending on policy.
for it in outpu.get("SECTION_VII", []) or []:
  if not _has_prov(it):
    num = (it or {}).get("risk_id", "?")
    raise ValueError(f"SECTION_VII risk {num} missing provenance/evidence.")

add validator (schema + policy checks)
