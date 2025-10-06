# -*- coding: utf-8 -*-
# Validation helpers: JSON Schema + policy-rule enforcement.
# Every function is import-safe (no code runs at import time).
from __future__ import annotations
from jsonschema import Draft7Validator  # validates against Draft-07 schemas
from typing import Dict, Any, Iterable, List
import asyncio                                  # stdlib: event loop
from utils.error_handler import handle_exception  # our handler function

# JSON Schema validation (strict)
def validate_against_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> None:
    # Validate 'data' against the provided JSON Schema (Draft-07).
    # Raises ValueError with a compact message on any violation.
    v = Draft7Validator(schema)  # build validator
    # iter_errors() (fixed typo) yields all errors; sort for stable messages
    errors = sorted(v.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        msgs = [f"{'/'.join(map(str, e.path))}: {e.message}" for e in errors]
        raise ValueError("Schema validation failed: " + "; ".join(msgs))

# Policy Rule Enforcement (bundle-driven)
def enforce_validation_rules(output_json: Dict[str, Any], rules: Dict[str, Any]) -> None:
    # Applies repo-defined validation rules on top of JSON Schema.
    # Expects the structure from policy/validation_rules_v1.json.
    # Raises ValueError on first violation (fail-fast).
    val = rules.get("validation", {})  # pull "validation" sub-object

    # --- Mandatory SECTION I field count (exact) ---
    expected_fields = _get_in(val, "mandatory_fields", "section_I")
    if expected_fields is not None:
        section_I = output_json.get("SECTION_I", {})
        if not isinstance(section_I, dict):
            raise ValueError("SECTION_I must be an object.")
        if len(section_I.keys()) != int(expected_fields):  # fixed '!+' to '!='
            raise ValueError(
                f"SECTION_I must contain {expected_fields} fields (found {len(section_I.keys())})."
            )

    # Canonical closing line required for each item in II–VI
    pattern = _get_in(val, "mandatory_fields", "section_II_to_VI_closing_line")
    if pattern:  # fixed 'if closing' missing colon
        for key in ("SECTION_II", "SECTION_III", "SECTION_IV", "SECTION_V", "SECTION_VI"):  # fixed key typos
            _assert_closing_line(output_json.get(key), key, pattern)

    # Strict header names (if enabled)
    # Note: your JSON uses "strict_string_match_headers"; support that.
    if _get_in(val, "strict_string_match_headers"):
        required_headers = set(
            _get_in(val, "strict_headers", "headers") or []  # keep optional table future-proof
        )
        if required_headers:
            actual_headers = set(output_json.keys())
            if actual_headers != required_headers:
                missing = required_headers - actual_headers
                extra = actual_headers - required_headers
                raise ValueError(
                    f"Header set mismatch. Missing={sorted(missing)} Extra={sorted(extra)}"
                )

    # Provenance checks (optional, conservative)
    prov_required = _get_in(val, "audit_logging", "record_provenance")
    if prov_required:  # fixed stray label 'prov_required:' to proper if
        _assert_provenance(output_json)


# Helpers
def _get_in(d: Dict[str, Any], *path) -> Any:
    #Safely walk nested dict by keys; return None if any key missing.
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def _assert_closing_line(items: Any, section_key: str, closing: str) -> None:
    #Ensure each Section II–VI item carries the canonical closing line string.
    if items is None:
        raise ValueError(f"{section_key} is required and must be a non-empty array.")
    if not isinstance(items, list):
        raise ValueError(f"{section_key} must be an array.")
    for idx, it in enumerate(items, start=1):  # fixed 'start+1' and invalid 'if idx, it'
        cl = (it or {}).get("closing_line")
        if cl != closing:  # fixed stray quote
            num = (it or {}).get("item_number", idx)
            raise ValueError(f"{section_key} item {num} missing canonical closing line.")


def _assert_provenance(output: Dict[str, Any]) -> None:
    # Walk Sections II–VI and VII items to ensure each clause item carries some evidence/provenance.
    # This is a conservative check; exact fields are defined in output_schemas.
    def _has_prov(obj: Dict[str, Any]) -> bool:
        # Accept either 'provenance', 'evidence', or 'source' arrays/objects.
        for k in ("provenance", "evidence", "source"):
            v = obj.get(k)
            if isinstance(v, (list, dict)) and len(v) > 0:
                return True
        return False

    for key in ("SECTION_II", "SECTION_III", "SECTION_IV", "SECTION_V", "SECTION_VI"):
        for it in (output.get(key) or []):
            # When items contain "clauses", verify each clause’s provenance
            for clause in (it or {}).get("clauses", []):
                if not _has_prov(clause):
                    num = (it or {}).get("item_number", "?")
                    raise ValueError(f"{key} item {num} has a clause missing provenance/evidence.")

    # Section VII (supplemental risks) may also require evidence depending on policy.
    for it in (output.get("SECTION_VII") or []):  # fixed 'outpu'
        for clause in (it or {}).get("clauses", []):
            if not _has_prov(clause):
                title = (it or {}).get("risk_title", "?")
                raise ValueError(f"SECTION_VII item '{title}' has a clause missing provenance/evidence.")


# No top-level execution; import is safe.
if __name__ == "__main__":
    # Optional: put ad-hoc tests here if you want to run this file directly.
    pass

# High-level wrapper used by the CLI
from dataclasses import dataclass              # lightweight report container
from pathlib import Path
import json                                   # read policy JSON files
from typing import List

@dataclass
class ValidationFinding:
    level: str          # "ERROR" | "WARN" (we only emit "ERROR" here)
    code: str           # short machine code, e.g., "SCHEMA" or "POLICY"
    message: str        # human-readable message

@dataclass
class ValidationReport:
    ok: bool
    findings: List[ValidationFinding]

def _load_policy_json(path: Path) -> dict:
    #Read a JSON file with UTF-8, raising a clean error if missing/bad.
    if not path.exists():
        raise FileNotFoundError(f"Missing policy file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def validate_filled_template(
    output_json: Dict[str, Any],
    policy_root: Path,                       # points to ./contract-analysis-policy-bundle
) -> ValidationReport:
    # Validates a filled template JSON against:
    # 1) the output schema (Draft-07)
    # 2) additional policy rules (closing lines, counts, provenance)
    # Returns a ValidationReport (ok/findings).
    findings: List[ValidationFinding] = []
    try:
        # 1) Load schema + rules directly from the bundle folder
        schema_path = policy_root / "schemas" / "output_schemas_v1.json"
        rules_path  = policy_root / "policy"  / "validation_rules_v1.json"
        schema = _load_policy_json(schema_path)     # JSON Schema dict
        rules  = _load_policy_json(rules_path)      # Policy rules dict
        # If the schema file wraps definitions, allow a direct schema too.
        # (Your bundle currently exposes the schema as a single object.)
        schema_obj = schema
        # 2) JSON Schema validation
        validate_against_schema(output_json, schema_obj)
        # 3) Policy-level validation
        enforce_validation_rules(output_json, rules)

    except Exception as e:
        findings.append(ValidationFinding(level="ERROR", code="VALIDATION", message=str(e)))
        return ValidationReport(ok=False, findings=findings)

    # If we got here, all checks passed
    return ValidationReport(ok=True, findings=findings)
