from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Tuple

# Canonical CR2A template spec. Clauses are intentionally empty; they are filled by the analyzer/LLM.
CR2A_TEMPLATE_SPEC: Dict[str, Dict[str, Any]] = {
    "SECTION_II": {
        "closing_line": "All applicable clauses for Administrative & Commercial Terms have been identified and analyzed.",
        "items": [
            {"item_number": 1, "item_title": "Contract Term, Renewal & Extensions", "clauses": []},
            {"item_number": 2, "item_title": "Bonding, Surety & Insurance Obligations", "clauses": []},
            {"item_number": 3, "item_title": "Payment Terms, Retainage & Invoicing Requirements", "clauses": []},
            # ...continue with every Section II item from the template...
        ],
    },
    "SECTION_III": {
        "closing_line": "All applicable clauses for Technical & Performance Scope have been identified and analyzed.",
        "items": [
            {
                "item_number": 1,
                "item_title": "Delivery Deadlines, Milestone Dates, Substantial & Final Completion Standards",
                "clauses": [],
            },
            {"item_number": 2, "item_title": "Punch List, Closeout Procedures & Acceptance of Work", "clauses": []},
            # ...all remaining Section III items...
        ],
    },
    "SECTION_IV": {
        "closing_line": "All applicable clauses for Legal Risk & Enforcement have been identified and analyzed.",
        "items": [
            {"item_number": 1, "item_title": "Indemnification, Defense & Hold Harmless Provisions", "clauses": []},
            {"item_number": 2, "item_title": "Duty to Defend vs. Indemnify Scope Clarifications", "clauses": []},
            # ...etc...
        ],
    },
    "SECTION_V": {
        "closing_line": "All applicable clauses for Regulatory & Compliance Terms have been identified and analyzed.",
        "items": [
            {"item_number": 1, "item_title": "Certified Payroll, Recordkeeping & Reporting Obligations", "clauses": []},
            {"item_number": 2, "item_title": "Prevailing Wage, Davis-Bacon & Federal/State Wage Compliance", "clauses": []},
            # ...etc...
        ],
    },
    "SECTION_VI": {
        "closing_line": "All applicable clauses for Data, Technology & Deliverables have been identified and analyzed.",
        "items": [
            {"item_number": 1, "item_title": "Data Ownership, Access & Rights to Digital Deliverables", "clauses": []},
            {
                "item_number": 2,
                "item_title": "AI / Technology Use Restrictions (Automation, Digital Tools, Proprietary Systems)",
                "clauses": [],
            },
            # ...etc...
        ],
    },
}


def build_template_scaffold(empty_clauses: bool = False) -> Dict[str, List[Dict[str, Any]]]:
    """
    Return a deep-copied scaffold of the template spec so callers can seed payloads safely.
    Args:
        empty_clauses: When True, force every item to start with an empty clauses array.
    """
    scaffold: Dict[str, List[Dict[str, Any]]] = {}
    for section_key, section in CR2A_TEMPLATE_SPEC.items():
        closing_line = section.get("closing_line", "")
        scaffold[section_key] = []
        for item in section.get("items", []):
            seed = deepcopy(item)
            seed["closing_line"] = closing_line
            # For LLM seeding we deliberately clear clauses so the model fills them explicitly.
            if empty_clauses:
                seed["clauses"] = []
            scaffold[section_key].append(seed)
    return scaffold


def canonical_template_items(section_key: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Convenience accessor returning the closing line and items for a given section key.
    Raises KeyError if the section is unknown so callers fail fast.
    """
    section = CR2A_TEMPLATE_SPEC[section_key]
    return section.get("closing_line", ""), section.get("items", [])
