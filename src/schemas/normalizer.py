"""Schema normalization for converting raw analysis output to the standardized CR2A format."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_output_schema(repo_root: Path) -> Dict[str, Any]:
    """Load the output schema definition.
    
    Args:
        repo_root: Repository root path
    
    Returns:
        Output schema as a dictionary
    
    Raises:
        FileNotFoundError: If schema file doesn't exist
        ValueError: If schema file contains invalid JSON
    """
    schema_path = repo_root / "schemas" / "output_schemas.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"Output schema not found: {schema_path}")
    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in output schema: {e}") from e


def convert_clause(block: Dict[str, Any]) -> Dict[str, str]:
    """Align clause fields with schema-required labels.
    
    Args:
        block: Raw clause data from analyzer
    
    Returns:
        Normalized clause dictionary
    """
    return {
        "Clause Language": block.get("clause_language", ""),
        "Clause Summary": block.get("clause_summary", ""),
        "Risk Triggers Identified": block.get("risk_triggers", ""),
        "Flow-Down Obligations": block.get("flow_down_obligations", ""),
        "Redline Recommendations": block.get("redline_recommendations", ""),
        "Harmful Language / Policy Conflicts": block.get("harmful_language_conflicts", ""),
    }


def _extract_clause_dicts(clauses_raw: Any) -> List[Dict[str, Any]]:
    """Extract clause dictionaries from raw data with proper type narrowing.
    
    This helper function isolates the type-checking logic so the main function
    doesn't need complex type guards.
    
    Args:
        clauses_raw: Raw clause data (typically Any from .get())
    
    Returns:
        List of validated clause dictionaries
    """
    if not isinstance(clauses_raw, list):
        return []

    result: List[Dict[str, Any]] = []
    for item in clauses_raw:  # type: ignore[union-attr]
        if isinstance(item, dict):
            item_dict: Dict[str, Any] = item  # type: ignore[assignment]
            result.append(item_dict)

    return result


def convert_items(items: List[Dict[str, Any]], section_label: str, closing_line: str) -> List[Dict[str, Any]]:
    """Convert section items to normalized format.
    
    Args:
        items: Raw item data from analyzer
        section_label: Section identifier (e.g., "II", "III")
        closing_line: Default closing line text
    
    Returns:
        List of normalized item dictionaries
    """
    normalized: List[Dict[str, Any]] = []
    
    for idx, item in enumerate(items or [], start=1):
        # Extract clauses using helper function (returns properly typed list)
        clauses_list = _extract_clause_dicts(item.get("clauses"))
        
        normalized.append({
            "item_number": item.get("item_number", idx),
            "item_title": item.get("item_title") or f"{section_label} Item {idx}",
            "clauses": [convert_clause(c) for c in clauses_list],
            "closing_line": item.get("closing_line") or closing_line,
        })
    
    return normalized


def normalize_to_schema(
    raw: Dict[str, Any],
    closing_line: str,
    policy_version: Optional[str] = None
) -> Dict[str, Any]:
    """Map heuristic analyzer output into the stricter JSON schema shape expected by the template exporter.
    
    This function:
    1. Normalizes SECTION_I header fields with fallback values
    2. Converts sections II-VI items to standardized format
    3. Adds document metadata

    Note: Sections VII (Supplemental Risks) and VIII (Final Summary) have been removed from the schema.

    Args:
        raw: Raw analysis output from analyzer
        closing_line: Standard closing line for sections II-VI
        policy_version: Optional policy version identifier
    
    Returns:
        Normalized output conforming to output_schemas.json
    """
    section_i_keys = [
        "PROJECT TITLE:",
        "SOLICITATION NO.:",
        "OWNER:",
        "CONTRACTOR:",
        "SCOPE:",
        "GENERAL RISK LEVEL:",
        "BID MODEL:",
        "NOTES:",
    ]

    source_i: Dict[str, Any] = (raw.get("SECTION_I") or {})  # type: ignore[assignment]
    section_i: Dict[str, str] = {}

    # Case-insensitive key matching with fallback to default value
    try:
        for key in section_i_keys:
            match = next(
                (source_i[k] for k in source_i if k.rstrip(":").lower() == key.rstrip(":").lower()),
                ""
            )
            section_i[key] = match or "Not present in contract."
    except (AttributeError, TypeError) as e:
        # Handle cases where source_i keys are not strings or source_i is malformed
        for key in section_i_keys:
            section_i[key] = "Not present in contract."

    normalized = {"SECTION_I": section_i}

    # Convert sections II through VI
    for sec in ["II", "III", "IV", "V", "VI"]:
        normalized[f"SECTION_{sec}"] = convert_items(
            raw.get(f"SECTION_{sec}") or [],
            sec,
            closing_line
        )

    return normalized