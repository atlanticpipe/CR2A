from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Tuple

# Canonical CR2A template spec. Clauses are intentionally empty; they are filled by the analyzer/LLM.
# Sections I-VI only: Overview, Administrative & Commercial, Technical & Performance, Legal Risk, Regulatory, and Data/Technology.
CR2A_TEMPLATE_SPEC: Dict[str, Dict[str, Any]] = {
    "SECTION_II": {
        "closing_line": "All applicable clauses for Administrative & Commercial Terms have been identified and analyzed.",
        "items": [
            {"item_number": 1, "item_title": "Contract Term, Renewal & Extensions", "clauses": []},
            {"item_number": 2, "item_title": "Bonding, Surety & Insurance Obligations", "clauses": []},
            {"item_number": 3, "item_title": "Retainage, Progress Payments & Final Payment Terms", "clauses": []},
            {"item_number": 4, "item_title": "Pay-When-Paid, Pay-If-Paid, or Owner Payment Contingencies", "clauses": []},
            {"item_number": 5, "item_title": "Price Escalation Clauses (Labor, Materials, Fuel, Inflation Adjustments)", "clauses": []},
            {"item_number": 6, "item_title": "Fuel Price Adjustment / Fuel Cost Caps", "clauses": []},
            {"item_number": 7, "item_title": "Change Orders, Scope Adjustments & Modifications", "clauses": []},
            {"item_number": 8, "item_title": "Termination for Convenience (Owner/Agency Right to Terminate Without Cause)", "clauses": []},
            {"item_number": 9, "item_title": "Termination for Cause / Default by Contractor", "clauses": []},
            {"item_number": 10, "item_title": "Bid Protest Procedures & Claims of Improper Award", "clauses": []},
            {"item_number": 11, "item_title": "Bid Tabulation, Competition & Award Process Requirements", "clauses": []},
            {"item_number": 12, "item_title": "Contractor Qualification, Licensing & Certification Requirements", "clauses": []},
            {"item_number": 13, "item_title": "Release Orders, Task Orders & Work Authorization Protocols", "clauses": []},
            {"item_number": 14, "item_title": "Assignment & Novation Restrictions (Transfer of Contract Rights)", "clauses": []},
            {"item_number": 15, "item_title": "Audit Rights, Recordkeeping & Document Retention Obligations", "clauses": []},
            {"item_number": 16, "item_title": "Notice Requirements & Claim Timeframes (Notice to Cure, Delay Notices, Termination Notices, etc.)", "clauses": []},
        ],
    },
    "SECTION_III": {
        "closing_line": "All applicable clauses for Technical & Performance Terms have been identified and analyzed.",
        "items": [
            {"item_number": 1, "item_title": "Scope of Work (Work Inclusions, Exclusions & Defined Deliverables)", "clauses": []},
            {"item_number": 2, "item_title": "Performance Schedule, Time for Completion & Critical Path Obligations", "clauses": []},
            {"item_number": 3, "item_title": "Delays of Any Kind (Force Majeure, Acts of God, Weather, Owner-Caused, Unforeseen Events)", "clauses": []},
            {"item_number": 4, "item_title": "Suspension of Work, Work Stoppages & Agency Directives", "clauses": []},
            {"item_number": 5, "item_title": "Submittals, Documentation & Approval Requirements", "clauses": []},
            {"item_number": 6, "item_title": "Emergency & Contingency Work Obligations", "clauses": []},
            {"item_number": 7, "item_title": "Permits, Licensing & Regulatory Approvals for Work", "clauses": []},
            {"item_number": 8, "item_title": "Warranty, Guarantee & Defects Liability Periods", "clauses": []},
            {"item_number": 9, "item_title": "Use of APS Tools, Equipment, Materials or Supplies", "clauses": []},
            {"item_number": 10, "item_title": "Owner-Supplied Support, Utilities & Site Access Provisions", "clauses": []},
            {"item_number": 11, "item_title": "Field Ticket, Daily Work Log & Documentation Requirements", "clauses": []},
            {"item_number": 12, "item_title": "Mobilization & Demobilization Provisions", "clauses": []},
            {"item_number": 13, "item_title": "Utility Coordination, Locate Risk & Conflict Avoidance", "clauses": []},
            {"item_number": 14, "item_title": "Delivery Deadlines, Milestone Dates, Substantial & Final Completion Standards", "clauses": []},
            {"item_number": 15, "item_title": "Punch List, Closeout Procedures & Acceptance of Work", "clauses": []},
            {"item_number": 16, "item_title": "Worksite Coordination, Access Restrictions & Sequencing Obligations", "clauses": []},
            {"item_number": 17, "item_title": "Deliverables, Digital Submissions & Documentation Standards", "clauses": []},
        ],
    },
    "SECTION_IV": {
        "closing_line": "All applicable clauses for Legal Risk & Enforcement have been identified and analyzed.",
        "items": [
            {"item_number": 1, "item_title": "Indemnification, Defense & Hold Harmless Provisions", "clauses": []},
            {"item_number": 2, "item_title": "Duty to Defend vs. Indemnify Scope Clarifications", "clauses": []},
            {"item_number": 3, "item_title": "Limitations of Liability, Damage Caps & Waivers of Consequential Damages", "clauses": []},
            {"item_number": 4, "item_title": "Insurance Coverage, Additional Insured & Waiver of Subrogation Clauses", "clauses": []},
            {"item_number": 5, "item_title": "Dispute Resolution (Mediation, Arbitration, Litigation)", "clauses": []},
            {"item_number": 6, "item_title": "Flow-Down Clauses (Prime-to-Subcontract Risk Pass-Through)", "clauses": []},
            {"item_number": 7, "item_title": "Subcontracting Restrictions, Approval & Substitution Requirements", "clauses": []},
            {"item_number": 8, "item_title": "Background Screening, Security Clearance & Worker Eligibility Requirements", "clauses": []},
            {"item_number": 9, "item_title": "Safety Standards, OSHA Compliance & Site-Specific Safety Obligations", "clauses": []},
            {"item_number": 10, "item_title": "Site Conditions, Differing Site Conditions & Changed Circumstances Clauses", "clauses": []},
            {"item_number": 11, "item_title": "Environmental Hazards, Waste Disposal & Hazardous Materials Provisions", "clauses": []},
            {"item_number": 12, "item_title": "Conflicting Documents / Order of Precedence Clauses", "clauses": []},
            {"item_number": 13, "item_title": "Setoff & Withholding Rights (Owner's Right to Deduct or Withhold Payment)", "clauses": []},
        ],
    },
    "SECTION_V": {
        "closing_line": "All applicable clauses for Regulatory & Compliance Terms have been identified and analyzed.",
        "items": [
            {"item_number": 1, "item_title": "Certified Payroll, Recordkeeping & Reporting Obligations", "clauses": []},
            {"item_number": 2, "item_title": "Prevailing Wage, Davis-Bacon & Federal/State Wage Compliance", "clauses": []},
            {"item_number": 3, "item_title": "EEO, Non-Discrimination, MWBE/DBE Participation Requirements", "clauses": []},
            {"item_number": 4, "item_title": "Anti-Lobbying / Cone of Silence Provisions", "clauses": []},
            {"item_number": 5, "item_title": "Apprenticeship, Training & Workforce Development Requirements", "clauses": []},
            {"item_number": 6, "item_title": "Immigration / E-Verify Compliance Obligations", "clauses": []},
            {"item_number": 7, "item_title": "Worker Classification & Independent Contractor Restrictions", "clauses": []},
            {"item_number": 8, "item_title": "Drug-Free Workplace Programs & Substance Testing Requirements", "clauses": []},
        ],
    },
    "SECTION_VI": {
        "closing_line": "All applicable clauses for Data, Technology & Deliverables have been identified and analyzed.",
        "items": [
            {"item_number": 1, "item_title": "Data Ownership, Access & Rights to Digital Deliverables", "clauses": []},
            {"item_number": 2, "item_title": "AI / Technology Use Restrictions (Automation, Digital Tools, Proprietary Systems)", "clauses": []},
            {"item_number": 3, "item_title": "Digital Surveillance, GIS-Tagged Deliverables & Monitoring Requirements", "clauses": []},
            {"item_number": 4, "item_title": "GIS, Digital Workflow Integration & Electronic Submittals", "clauses": []},
            {"item_number": 5, "item_title": "Confidentiality, Data Security & Records Retention Obligations", "clauses": []},
            {"item_number": 6, "item_title": "Intellectual Property, Licensing & Ownership of Work Product", "clauses": []},
            {"item_number": 7, "item_title": "Cybersecurity Standards, Breach Notification & IT System Use Policies", "clauses": []},
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
