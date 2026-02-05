"""
Schema Completer Module

This module provides reference definitions for all clause categories in the
comprehensive contract analysis schema. It serves as the authoritative source
for category lists used by the template-based UI display system.

Note: This module no longer modifies analysis results. The StructuredAnalysisView
uses these category definitions to build a complete UI template that displays
all categories, with missing ones shown as "Not found in contract".
"""

from typing import Dict, Any
from src.analysis_models import (
    ComprehensiveAnalysisResult,
    AdministrativeAndCommercialTerms,
    TechnicalAndPerformanceTerms,
    LegalRiskAndEnforcement,
    RegulatoryAndComplianceTerms,
    DataTechnologyAndDeliverables,
    ClauseBlock
)


class SchemaCompleter:
    """
    Provides reference definitions for all clause categories in the schema.
    
    This class serves as the authoritative source for category lists used by
    the StructuredAnalysisView to build a complete UI template. The template-based
    approach pre-creates all category boxes, eliminating the need for dynamic
    schema completion.
    
    Usage:
        The StructuredAnalysisView uses these category lists to:
        1. Build a complete UI template with all sections and categories
        2. Match analysis results to the pre-built template boxes
        3. Display found categories with data, and missing ones as "Not found"
    """
    
    # Define all required categories for each section
    ADMINISTRATIVE_CATEGORIES = [
        "Contract Term, Renewal & Extensions",
        "Bonding, Surety, & Insurance Obligations",
        "Retainage, Progress Payments & Final Payment Terms",
        "Pay-When-Paid, Pay-If-Paid, or Owner Payment Contingencies",
        "Price Escalation Clauses (Labor, Materials, Fuel, Inflation Adjustments)",
        "Fuel Price Adjustment / Fuel Cost Caps",
        "Change Orders, Scope Adjustments & Modifications",
        "Termination for Convenience (Owner/Agency Right to Terminate Without Cause)",
        "Termination for Cause / Default by Contractor",
        "Bid Protest Procedures & Claims of Improper Award",
        "Bid Tabulation, Competition & Award Process Requirements",
        "Contractor Qualification, Licensing & Certification Requirements",
        "Release Orders, Task Orders & Work Authorization Protocols",
        "Assignment & Novation Restrictions (Transfer of Contract Rights)",
        "Audit Rights, Recordkeeping & Document Retention Obligations",
        "Notice Requirements & Claim Timeframes (Notice to Cure, Delay Notices, Termination Notices, etc.)"
    ]
    
    TECHNICAL_CATEGORIES = [
        "Scope of Work (Work Inclusions, Exclusions & Defined Deliverables)",
        "Performance Schedule, Time for Completion & Critical Path Obligations",
        "Delays of Any Kind (Force Majeure, Acts of God, Weather, Owner-Caused, Unforeseen Events)",
        "Suspension of Work, Work Stoppages & Agency Directives",
        "Submittals, Documentation & Approval Requirements",
        "Emergency & Contingency Work Obligations",
        "Permits, Licensing & Regulatory Approvals for Work",
        "Warranty, Guarantee & Defects Liability Periods",
        "Use of APS Tools, Equipment, Materials or Supplies",
        "Owner-Supplied Support, Utilities & Site Access Provisions",
        "Field Ticket, Daily Work Log & Documentation Requirements",
        "Mobilization & Demobilization Provisions",
        "Utility Coordination, Locate Risk & Conflict Avoidance",
        "Delivery Deadlines, Milestone Dates, Substantial & Final Completion Standards",
        "Punch List, Closeout Procedures & Acceptance of Work",
        "Worksite Coordination, Access Restrictions & Sequencing Obligations",
        "Deliverables, Digital Submissions & Documentation Standards"
    ]
    
    LEGAL_CATEGORIES = [
        "Indemnification, Defense & Hold Harmless Provisions",
        "Duty to Defend vs. Indemnify Scope Clarifications",
        "Limitations of Liability, Damage Caps & Waivers of Consequential Damages",
        "Insurance Coverage, Additional Insured & Waiver of Subrogation Clauses",
        "Dispute Resolution (Mediation, Arbitration, Litigation)",
        "Flow-Down Clauses (Prime-to-Subcontract Risk Pass-Through)",
        "Subcontracting Restrictions, Approval & Substitution Requirements",
        "Background Screening, Security Clearance & Worker Eligibility Requirements",
        "Safety Standards, OSHA Compliance & Site-Specific Safety Obligations",
        "Site Conditions, Differing Site Conditions & Changed Circumstances Clauses",
        "Environmental Hazards, Waste Disposal & Hazardous Materials Provisions",
        "Conflicting Documents / Order of Precedence Clauses",
        "Setoff & Withholding Rights (Owner's Right to Deduct or Withhold Payment)"
    ]
    
    REGULATORY_CATEGORIES = [
        "Certified Payroll, Recordkeeping & Reporting Obligations",
        "Prevailing Wage, Davis-Bacon & Federal/State Wage Compliance",
        "EEO, Non-Discrimination, MWBE/DBE Participation Requirements",
        "Anti-Lobbying / Cone of Silence Provisions",
        "Apprenticeship, Training & Workforce Development Requirements",
        "Immigration / E-Verify Compliance Obligations",
        "Worker Classification & Independent Contractor Restrictions",
        "Drug-Free Workplace Programs & Substance Testing Requirements"
    ]
    
    DATA_TECH_CATEGORIES = [
        "Data Ownership, Access & Rights to Digital Deliverables",
        "AI / Technology Use Restrictions (Automation, Digital Tools, Proprietary Systems)",
        "Digital Surveillance, GIS-Tagged Deliverables & Monitoring Requirements",
        "GIS, Digital Workflow Integration & Electronic Submittals",
        "Confidentiality, Data Security & Records Retention Obligations",
        "Intellectual Property, Licensing & Ownership of Work Product",
        "Cybersecurity Standards, Breach Notification & IT System Use Policies"
    ]
    
    @staticmethod
    def create_not_found_clause() -> ClauseBlock:
        """Create a ClauseBlock for categories not found in the contract."""
        return ClauseBlock(
            clause_language="Not found",
            clause_summary="Not found",
            risk_triggers_identified=[],
            flow_down_obligations=[],
            redline_recommendations=[],
            harmful_language_policy_conflicts=[]
        )
    
    @classmethod
    def complete_result(cls, result: ComprehensiveAnalysisResult) -> ComprehensiveAnalysisResult:
        """
        Add missing clause categories to the analysis result.
        
        Args:
            result: The analysis result from OpenAI
            
        Returns:
            Complete analysis result with all categories
        """
        # Complete Administrative & Commercial Terms
        if result.administrative_and_commercial_terms:
            result.administrative_and_commercial_terms = cls._complete_section(
                result.administrative_and_commercial_terms,
                cls.ADMINISTRATIVE_CATEGORIES
            )
        
        # Complete Technical & Performance Terms
        if result.technical_and_performance_terms:
            result.technical_and_performance_terms = cls._complete_section(
                result.technical_and_performance_terms,
                cls.TECHNICAL_CATEGORIES
            )
        
        # Complete Legal Risk & Enforcement
        if result.legal_risk_and_enforcement:
            result.legal_risk_and_enforcement = cls._complete_section(
                result.legal_risk_and_enforcement,
                cls.LEGAL_CATEGORIES
            )
        
        # Complete Regulatory & Compliance Terms
        if result.regulatory_and_compliance_terms:
            result.regulatory_and_compliance_terms = cls._complete_section(
                result.regulatory_and_compliance_terms,
                cls.REGULATORY_CATEGORIES
            )
        
        # Complete Data, Technology & Deliverables
        if result.data_technology_and_deliverables:
            result.data_technology_and_deliverables = cls._complete_section(
                result.data_technology_and_deliverables,
                cls.DATA_TECH_CATEGORIES
            )
        
        return result
    
    @classmethod
    def _complete_section(cls, section: Any, required_categories: list) -> Any:
        """
        Add missing categories to a section.
        
        Args:
            section: The section object (e.g., AdministrativeAndCommercialTerms)
            required_categories: List of all required category names
            
        Returns:
            Section with all categories present
        """
        section_dict = section.to_dict() if hasattr(section, 'to_dict') else section
        
        # Add missing categories
        for category in required_categories:
            if category not in section_dict or section_dict[category] is None:
                section_dict[category] = cls.create_not_found_clause().to_dict()
        
        # Reconstruct the section object
        # This is a simplified approach - in practice, you'd reconstruct the proper type
        return section_dict
    
    @classmethod
    def complete_dict(cls, result_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add missing clause categories to a dictionary representation.
        
        This is useful when working with dict representations instead of
        ComprehensiveAnalysisResult objects.
        
        Args:
            result_dict: Dictionary representation of analysis result
            
        Returns:
            Complete dictionary with all categories
        """
        not_found_clause = {
            "Clause Language": "Not found",
            "Clause Summary": "Not found",
            "Risk Triggers Identified": [],
            "Flow-Down Obligations": [],
            "Redline Recommendations": [],
            "Harmful Language / Policy Conflicts": []
        }
        
        # Complete each section
        if "administrative_and_commercial_terms" in result_dict:
            section = result_dict["administrative_and_commercial_terms"]
            for category in cls.ADMINISTRATIVE_CATEGORIES:
                if category not in section or section[category] is None:
                    section[category] = not_found_clause.copy()
        
        if "technical_and_performance_terms" in result_dict:
            section = result_dict["technical_and_performance_terms"]
            for category in cls.TECHNICAL_CATEGORIES:
                if category not in section or section[category] is None:
                    section[category] = not_found_clause.copy()
        
        if "legal_risk_and_enforcement" in result_dict:
            section = result_dict["legal_risk_and_enforcement"]
            for category in cls.LEGAL_CATEGORIES:
                if category not in section or section[category] is None:
                    section[category] = not_found_clause.copy()
        
        if "regulatory_and_compliance_terms" in result_dict:
            section = result_dict["regulatory_and_compliance_terms"]
            for category in cls.REGULATORY_CATEGORIES:
                if category not in section or section[category] is None:
                    section[category] = not_found_clause.copy()
        
        if "data_technology_and_deliverables" in result_dict:
            section = result_dict["data_technology_and_deliverables"]
            for category in cls.DATA_TECH_CATEGORIES:
                if category not in section or section[category] is None:
                    section[category] = not_found_clause.copy()
        
        return result_dict
