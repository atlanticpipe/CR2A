# -*- coding: utf-8 -*-
# Validation helpers: JSON Schema + policy-rule enforcement.
# Every function is import-safe (no code runs at import time).
from __future__ import annotations

from dataclasses import dataclass, field
from jsonschema import Draft7Validator
from typing import Dict, Any, Iterable, List, Optional, Union
from pathlib import Path
import json


# ----------------------------- JSON Schema ----------------------------- #

def validate_against_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> None:
    """
    Validate 'data' against the provided JSON Schema (Draft-07).
    Raises ValueError with a compact message on any violation.
    """
    v = Draft7Validator(schema)
    errors = sorted(v.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        parts: List[str] = []
        for e in errors[:10]:
            loc = ".".join(str(x) for x in e.path) or "<root>"
            parts.append(f"{loc}: {e.message}")
        msg = "JSON schema validation failed: " + "; ".join(parts)
        if len(errors) > 10:
            msg += f" (+{len(errors)-10} more)"
        raise ValueError(msg)


# ----------------------------- Findings/Report ----------------------------- #

@dataclass
class ValidationFinding:
    level: str  # "ERROR" | "WARN" | "INFO"
    code: str
    message: str
    path: Optional[str] = None


@dataclass
class ValidationReport:
    ok: bool
    findings: List[ValidationFinding] = field(default_factory=list)


# ----------------------------- Helpers ----------------------------- #

def _get_in(obj: Any, *path: Union[str, int]) -> Any:
    cur = obj
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur


def _assert_closing_line(output_json: Dict[str, Any],
                         sections: Iterable[str],
                         expected: str) -> List[ValidationFinding]:
    findings: List[ValidationFinding] = []
    for sec in sections:
        key = f"SECTION_{sec}"
        node = output_json.get(key)
        if node is None:
            findings.append(ValidationFinding(
                level="ERROR",
                code="MISSING_SECTION",
                message=f"Section {key} must be present."
            ))
            continue
        # Sections II–VI are arrays of items in the schema; validate per-item closing_line
        if isinstance(node, list):
            for idx, item in enumerate(node):
                if not isinstance(item, dict):
                    findings.append(ValidationFinding(
                        level="ERROR",
                        code="INVALID_ITEM",
                        message=f"{key}[{idx}] must be an object."
                    ))
                    continue
                if expected:
                    closing = item.get("closing_line")
                    if closing != expected:
                        findings.append(ValidationFinding(
                            level="ERROR",
                            code="CLOSING_LINE",
                            message=f"{key}[{idx}].closing_line must equal the required policy string."
                        ))
        elif isinstance(node, dict):
            # Some schemas might allow a single object; check its closing_line
            if expected:
                closing = node.get("closing_line")
                if closing != expected:
                    findings.append(ValidationFinding(
                        level="ERROR",
                        code="CLOSING_LINE",
                        message=f"{key}.closing_line must equal the required policy string."
                    ))
        else:
            findings.append(ValidationFinding(
                level="ERROR",
                code="INVALID_SECTION_TYPE",
                message=f"{key} must be an array or object per schema."
            ))
    return findings


def _assert_provenance(output_json: Dict[str, Any]) -> List[ValidationFinding]:
    prov = output_json.get("PROVENANCE")
    if prov is None:
        return []
    if not isinstance(prov, dict):
        return [ValidationFinding(level="ERROR", code="PROVENANCE", message="PROVENANCE must be an object.")]
    must = ["version", "generated_at"]
    missing = [m for m in must if m not in prov]
    if missing:
        return [ValidationFinding(level="ERROR",
                                  code="PROVENANCE",
                                  message=f"PROVENANCE missing required fields: {', '.join(missing)}")]
    return []


# ----------------------------- Policy Rules ----------------------------- #

def enforce_validation_rules(output_json: Dict[str, Any], validation_rules: Dict[str, Any]) -> None:
    """
    Enforce policy-level validation rules (beyond JSON Schema).
    Raises ValueError for hard failures; may aggregate multiple issues.
    Expected subset of rules (as per validation_rules_v1.json):
      validation.mandatory_fields.section_I_min_items
      validation.mandatory_fields.section_II_to_VI_closing_line
    """
    findings: List[ValidationFinding] = []

    val = validation_rules if "mandatory_fields" in validation_rules else validation_rules.get("validation", {})
    mandatory = val.get("mandatory_fields", {}) if isinstance(val, dict) else {}

    # 1) SECTION I: minimum number of fields
    min_items = mandatory.get("section_I_min_items")
    if min_items is not None:
        section_I = output_json.get("SECTION_I", {})
        if not isinstance(section_I, dict):
            findings.append(ValidationFinding(level="ERROR", code="SECTION_I", message="SECTION_I must be an object."))
        else:
            if len(section_I.keys()) < int(min_items):
                findings.append(ValidationFinding(
                    level="ERROR",
                    code="SECTION_I_MIN_ITEMS",
                    message=f"SECTION_I must contain at least {int(min_items)} fields (found {len(section_I.keys())})."
                ))

    # 2) SECTION II–VI: closing line must match policy string (only if still required in your policy)
    closing_line = mandatory.get("section_II_to_VI_closing_line")
    if closing_line:
        findings.extend(_assert_closing_line(output_json, sections=["II", "III", "IV", "V", "VI"], expected=closing_line))

    # 3) Optional provenance check (if provided in output)
    findings.extend(_assert_provenance(output_json))

    abort_on_failure = bool(val.get("abort_on_failure", True))
    fail_fast = bool(val.get("fail_fast", True))
    errors = [f for f in findings if f.level == "ERROR"]
    if errors and (abort_on_failure or fail_fast):
        msg = "; ".join(f"{f.code}: {f.message}" for f in errors[:10])
        if len(errors) > 10:
            msg += f" (+{len(errors)-10} more)"
        raise ValueError(msg)


# ----------------------------- Public API ----------------------------- #

def validate_filled_template(output_json: Dict[str, Any],
                             schema: Dict[str, Any],
                             validation_rules: Dict[str, Any]) -> ValidationReport:
    """
    Validate a filled CR2A template object:
      1) JSON Schema validation (Draft-07)
      2) Policy-level validation rules
    Returns a ValidationReport with aggregated findings; ok=False if any error occurs.
    """
    findings: List[ValidationFinding] = []
    try:
        validate_against_schema(output_json, schema)
        enforce_validation_rules(output_json, validation_rules)
    except Exception as e:
        findings.append(ValidationFinding(level="ERROR", code="VALIDATION", message=str(e)))
        return ValidationReport(ok=False, findings=findings)

    return ValidationReport(ok=True, findings=findings)
