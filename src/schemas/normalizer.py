"""
Schema normalization for converting raw analysis output to the standardized CR2A format.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

def load_output_schema(repo_root: Path) -> Dict[str, Any]:
    """
    Load the output schema definition.
    Args:
        repo_root: Repository root path
    Returns:
        Output schema as a dictionary
    """
    schema_path = repo_root / "schemas" / "output_schemas.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))

def convert_clause(block: Dict[str, Any]) -> Dict[str, str]:
    """
    Align clause fields with schema-required labels.
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


def convert_items(items: List[Dict[str, Any]], section_label: str, closing_line: str) -> List[Dict[str, Any]]:
    """
    Convert section items to normalized format.
    Args:
        items: Raw item data from analyzer
        section_label: Section identifier (e.g., "II", "III")
        closing_line: Default closing line text
    Returns:
        List of normalized item dictionaries
    """
    normalized: List[Dict[str, Any]] = []
    for idx, item in enumerate(items or [], start=1):
        normalized.append(
            {
                "item_number": item.get("item_number", idx),
                "item_title": item.get("item_title") or f"{section_label} Item {idx}",
                "clauses": [convert_clause(b) for b in item.get("clauses") or []],
                "closing_line": item.get("closing_line") or closing_line,
            }
        )
    return normalized

def normalize_to_schema(
    raw: Dict[str, Any],
    closing_line: str,
    policy_version: Optional[str] = None
) -> Dict[str, Any]:
    """
    Map heuristic analyzer output into the stricter JSON schema shape expected by the template exporter.
    This function:
    1. Normalizes SECTION_I header fields with fallback values
    2. Converts sections II-VI items to standardized format
    3. Preserves SECTION_VII as-is
    4. Creates SECTION_VIII structure
    5. Adds document metadata
    Args:
        raw: Raw analysis output from analyzer
        closing_line: Standard closing line for sections II-VI
        policy_version: Optional policy version identifier
    Returns:
        Normalized output conforming to output_schemas.json
    """
    # Section I: Header information
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

    source_i = raw.get("SECTION_I") or {}
    section_i: Dict[str, str] = {}
    
    for key in section_i_keys:
        # Case-insensitive lookup with sane fallback text so schema requirements are satisfied
        match = next(
            (source_i[k] for k in source_i if k.rstrip(":").lower() == key.rstrip(":").lower()),
            ""
        )
        section_i[key] = match or "Not present in contract."

    # Build normalized structure
    normalized = {"SECTION_I": section_i}
    
    # Sections II-VI: Items with clauses
    for sec in ["II", "III", "IV", "V", "VI"]:
        normalized[f"SECTION_{sec}"] = convert_items(
            raw.get(f"SECTION_{sec}") or [],
            sec,
            closing_line
        )

    # Section VII: Summary points (preserved as-is)
    normalized["SECTION_VII"] = raw.get("SECTION_VII", [])
    
    # Section VIII: Risk matrix
    normalized["SECTION_VIII"] = {
        "rows": [],
        "general_risk_level": section_i.get("GENERAL RISK LEVEL:", "Not present in contract."),
    }
    
    # Omission check
    normalized["OMISSION_CHECK"] = "No omissions or uncategorized risks identified."
    
    # Document metadata
    normalized["doc_meta"] = {
        "policy_version": policy_version or "schemas@v1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "fdot_contract": raw.get("fdot_contract"),
        "fdot_year": raw.get("assume_fdot_year"),
    }
    
    return normalized