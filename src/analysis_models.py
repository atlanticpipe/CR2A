"""
Analysis Result Data Models

This module defines the data models for contract analysis results.
All models support serialization to/from dictionaries for JSON compatibility.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Optional, Any


# Valid actions for redline recommendations
VALID_REDLINE_ACTIONS = frozenset({"insert", "replace", "delete"})


@dataclass
class RedlineRecommendation:
    """
    A structured redline recommendation for contract modifications.
    
    Attributes:
        action: The type of modification - must be one of: "insert", "replace", "delete"
        text: The text to insert, replace with, or delete
        reference: Optional reference to source or justification for the recommendation
    """
    action: str
    text: str
    reference: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Validate that action is one of the allowed values."""
        if self.action not in VALID_REDLINE_ACTIONS:
            raise ValueError(
                f"Invalid action '{self.action}'. Must be one of: {', '.join(sorted(VALID_REDLINE_ACTIONS))}"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation with action, text, and optionally reference
        """
        result: Dict[str, Any] = {
            'action': self.action,
            'text': self.text
        }
        if self.reference is not None:
            result['reference'] = self.reference
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RedlineRecommendation':
        """
        Create a RedlineRecommendation from a dictionary.
        
        Args:
            data: Dictionary containing action, text, and optionally reference
            
        Returns:
            RedlineRecommendation instance
            
        Raises:
            ValueError: If action is not one of: insert, replace, delete
            KeyError: If required fields (action, text) are missing
        """
        return cls(
            action=data['action'],
            text=data['text'],
            reference=data.get('reference')
        )


@dataclass
class ClauseBlock:
    """
    Analysis block for a single clause category.
    
    Contains comprehensive analysis of a contract clause including the original
    language, summary, identified risks, obligations, and recommendations.
    
    Attributes:
        clause_language: The original text/language of the clause from the contract
        clause_summary: A summary of what the clause covers
        risk_triggers_identified: List of specific conditions or language indicating potential risk
        flow_down_obligations: List of contractual requirements that must be passed to subcontractors
        redline_recommendations: List of structured recommendations for contract modifications
        harmful_language_policy_conflicts: List of language that conflicts with policies or is harmful
    """
    clause_language: str
    clause_summary: str
    risk_triggers_identified: List[str]
    flow_down_obligations: List[str]
    redline_recommendations: List[RedlineRecommendation]
    harmful_language_policy_conflicts: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        
        Maps Python field names to schema field names:
        - clause_language -> "Clause Language"
        - clause_summary -> "Clause Summary"
        - risk_triggers_identified -> "Risk Triggers Identified"
        - flow_down_obligations -> "Flow-Down Obligations"
        - redline_recommendations -> "Redline Recommendations"
        - harmful_language_policy_conflicts -> "Harmful Language / Policy Conflicts"
        
        Returns:
            Dictionary representation matching the output_schemas_v1.json ClauseBlock structure
        """
        return {
            'Clause Language': self.clause_language,
            'Clause Summary': self.clause_summary,
            'Risk Triggers Identified': self.risk_triggers_identified,
            'Flow-Down Obligations': self.flow_down_obligations,
            'Redline Recommendations': [rec.to_dict() for rec in self.redline_recommendations],
            'Harmful Language / Policy Conflicts': self.harmful_language_policy_conflicts
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClauseBlock':
        """
        Create a ClauseBlock from a dictionary.
        
        Handles both schema format (with spaces in keys) and Python format (with underscores).
        Parses nested RedlineRecommendation objects from the redline_recommendations array.
        
        Args:
            data: Dictionary containing clause block data. Accepts keys in either format:
                  - Schema format: "Clause Language", "Risk Triggers Identified", etc.
                  - Python format: "clause_language", "risk_triggers_identified", etc.
            
        Returns:
            ClauseBlock instance with all fields populated
            
        Raises:
            KeyError: If required fields are missing from the data
        """
        # Support both schema format (with spaces) and Python format (with underscores)
        clause_language = data.get('Clause Language', data.get('clause_language', ''))
        clause_summary = data.get('Clause Summary', data.get('clause_summary', ''))
        risk_triggers = data.get('Risk Triggers Identified', data.get('risk_triggers_identified', []))
        flow_down = data.get('Flow-Down Obligations', data.get('flow_down_obligations', []))
        redline_recs_data = data.get('Redline Recommendations', data.get('redline_recommendations', []))
        harmful_language = data.get('Harmful Language / Policy Conflicts', 
                                    data.get('harmful_language_policy_conflicts', []))
        
        # Parse nested RedlineRecommendation objects
        redline_recommendations = []
        for rec_data in redline_recs_data:
            if isinstance(rec_data, dict):
                redline_recommendations.append(RedlineRecommendation.from_dict(rec_data))
            elif isinstance(rec_data, RedlineRecommendation):
                redline_recommendations.append(rec_data)
        
        return cls(
            clause_language=clause_language,
            clause_summary=clause_summary,
            risk_triggers_identified=risk_triggers,
            flow_down_obligations=flow_down,
            redline_recommendations=redline_recommendations,
            harmful_language_policy_conflicts=harmful_language
        )


# Valid risk levels for contract overview
VALID_RISK_LEVELS = frozenset({"Low", "Medium", "High", "Critical"})

# Valid bid models for contract overview
VALID_BID_MODELS = frozenset({
    "Lump Sum", "Unit Price", "Cost Plus", "Time & Materials", 
    "GMP", "Design-Build", "Other"
})


@dataclass
class ContractOverview:
    """
    Section I: Contract Overview with 8 required fields.
    
    Contains high-level information about the contract including project details,
    parties involved, scope, risk assessment, and bid model.
    
    Attributes:
        project_title: Title of the project
        solicitation_no: Solicitation or contract number
        owner: The owner/client party in the contract
        contractor: The contractor party in the contract
        scope: Brief description of the contract scope
        general_risk_level: Overall risk level - must be one of: "Low", "Medium", "High", "Critical"
        bid_model: Type of bid/pricing model - must be one of: "Lump Sum", "Unit Price", 
                   "Cost Plus", "Time & Materials", "GMP", "Design-Build", "Other"
        notes: Additional notes or observations about the contract
    """
    project_title: str
    solicitation_no: str
    owner: str
    contractor: str
    scope: str
    general_risk_level: str
    bid_model: str
    notes: str
    
    def __post_init__(self) -> None:
        """Validate that enum fields have valid values."""
        if self.general_risk_level not in VALID_RISK_LEVELS:
            raise ValueError(
                f"Invalid general_risk_level '{self.general_risk_level}'. "
                f"Must be one of: {', '.join(sorted(VALID_RISK_LEVELS))}"
            )
        if self.bid_model not in VALID_BID_MODELS:
            raise ValueError(
                f"Invalid bid_model '{self.bid_model}'. "
                f"Must be one of: {', '.join(sorted(VALID_BID_MODELS))}"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        
        Maps Python field names to schema field names:
        - project_title -> "Project Title"
        - solicitation_no -> "Solicitation No."
        - owner -> "Owner"
        - contractor -> "Contractor"
        - scope -> "Scope"
        - general_risk_level -> "General Risk Level"
        - bid_model -> "Bid Model"
        - notes -> "Notes"
        
        Returns:
            Dictionary representation matching the output_schemas_v1.json contract_overview structure
        """
        return {
            'Project Title': self.project_title,
            'Solicitation No.': self.solicitation_no,
            'Owner': self.owner,
            'Contractor': self.contractor,
            'Scope': self.scope,
            'General Risk Level': self.general_risk_level,
            'Bid Model': self.bid_model,
            'Notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContractOverview':
        """
        Create a ContractOverview from a dictionary.
        
        Handles both schema format (with spaces in keys) and Python format (with underscores).
        
        Args:
            data: Dictionary containing contract overview data. Accepts keys in either format:
                  - Schema format: "Project Title", "Solicitation No.", etc.
                  - Python format: "project_title", "solicitation_no", etc.
            
        Returns:
            ContractOverview instance with all fields populated
            
        Raises:
            ValueError: If general_risk_level or bid_model have invalid values
            KeyError: If required fields are missing from the data
        """
        # Support both schema format (with spaces) and Python format (with underscores)
        project_title = data.get('Project Title', data.get('project_title', ''))
        solicitation_no = data.get('Solicitation No.', data.get('solicitation_no', ''))
        owner = data.get('Owner', data.get('owner', ''))
        contractor = data.get('Contractor', data.get('contractor', ''))
        scope = data.get('Scope', data.get('scope', ''))
        general_risk_level = data.get('General Risk Level', data.get('general_risk_level', ''))
        bid_model = data.get('Bid Model', data.get('bid_model', ''))
        notes = data.get('Notes', data.get('notes', ''))
        
        return cls(
            project_title=project_title,
            solicitation_no=solicitation_no,
            owner=owner,
            contractor=contractor,
            scope=scope,
            general_risk_level=general_risk_level,
            bid_model=bid_model,
            notes=notes
        )


@dataclass
class ContractMetadata:
    """
    Metadata about the analyzed contract.
    
    Attributes:
        filename: Name of the contract file
        analyzed_at: Timestamp when analysis was performed
        page_count: Number of pages in the contract
        file_size_bytes: Size of the file in bytes
    """
    filename: str
    analyzed_at: datetime
    page_count: int
    file_size_bytes: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'filename': self.filename,
            'analyzed_at': self.analyzed_at.isoformat(),
            'page_count': self.page_count,
            'file_size_bytes': self.file_size_bytes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContractMetadata':
        """Create from dictionary."""
        return cls(
            filename=data['filename'],
            analyzed_at=datetime.fromisoformat(data['analyzed_at']),
            page_count=data['page_count'],
            file_size_bytes=data['file_size_bytes']
        )


@dataclass
class Clause:
    """
    A contract clause with risk assessment.
    
    Attributes:
        id: Unique identifier for the clause
        type: Type of clause (e.g., 'payment_terms', 'liability', 'termination')
        text: Excerpt of the clause text from the contract
        page: Page number where the clause appears
        risk_level: Risk level assessment ('low', 'medium', 'high')
    """
    id: str
    type: str
    text: str
    page: int
    risk_level: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Clause':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class Risk:
    """
    An identified risk in the contract.
    
    Attributes:
        id: Unique identifier for the risk
        clause_id: Reference to the associated clause
        severity: Severity level ('low', 'medium', 'high', 'critical')
        description: Description of the risk
        recommendation: Recommended action to mitigate the risk
    """
    id: str
    clause_id: str
    severity: str
    description: str
    recommendation: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Risk':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ComplianceIssue:
    """
    A compliance issue identified in the contract.
    
    Attributes:
        id: Unique identifier for the compliance issue
        regulation: Regulation name (e.g., 'GDPR', 'CCPA', 'SOX')
        issue: Description of the compliance issue
        severity: Severity level ('low', 'medium', 'high')
    """
    id: str
    regulation: str
    issue: str
    severity: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComplianceIssue':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class RedliningSuggestion:
    """
    A suggestion for redlining (modifying) a contract clause.
    
    Attributes:
        clause_id: Reference to the clause to be modified
        original_text: Original text of the clause
        suggested_text: Suggested replacement text
        rationale: Explanation for the suggested change
    """
    clause_id: str
    original_text: str
    suggested_text: str
    rationale: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RedliningSuggestion':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class AnalysisResult:
    """
    Complete analysis result for a contract.
    
    This is the top-level data structure containing all analysis information
    including metadata, clauses, risks, compliance issues, and redlining suggestions.
    
    Attributes:
        metadata: Contract metadata
        clauses: List of identified clauses
        risks: List of identified risks
        compliance_issues: List of compliance issues
        redlining_suggestions: List of redlining suggestions
    """
    metadata: ContractMetadata
    clauses: List[Clause] = field(default_factory=list)
    risks: List[Risk] = field(default_factory=list)
    compliance_issues: List[ComplianceIssue] = field(default_factory=list)
    redlining_suggestions: List[RedliningSuggestion] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of the analysis result
        """
        return {
            'contract_metadata': self.metadata.to_dict(),
            'clauses': [clause.to_dict() for clause in self.clauses],
            'risks': [risk.to_dict() for risk in self.risks],
            'compliance_issues': [issue.to_dict() for issue in self.compliance_issues],
            'redlining_suggestions': [suggestion.to_dict() for suggestion in self.redlining_suggestions]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisResult':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary containing analysis result data
            
        Returns:
            AnalysisResult instance
        """
        return cls(
            metadata=ContractMetadata.from_dict(data['contract_metadata']),
            clauses=[Clause.from_dict(c) for c in data.get('clauses', [])],
            risks=[Risk.from_dict(r) for r in data.get('risks', [])],
            compliance_issues=[ComplianceIssue.from_dict(ci) for ci in data.get('compliance_issues', [])],
            redlining_suggestions=[RedliningSuggestion.from_dict(rs) for rs in data.get('redlining_suggestions', [])]
        )
    
    def validate_result(self) -> bool:
        """
        Validate that the analysis result has all required fields.
        
        Returns:
            True if valid, False otherwise
        """
        # Check that metadata exists and has required fields
        if not self.metadata:
            return False
        
        if not self.metadata.filename or not self.metadata.analyzed_at:
            return False
        
        # All lists can be empty, but they must exist (which they do via default_factory)
        # Check that all clauses have required fields
        for clause in self.clauses:
            if not clause.id or not clause.type or not clause.text:
                return False
            if clause.risk_level not in ['low', 'medium', 'high']:
                return False
        
        # Check that all risks have required fields
        for risk in self.risks:
            if not risk.id or not risk.clause_id or not risk.description:
                return False
            if risk.severity not in ['low', 'medium', 'high', 'critical']:
                return False
        
        # Check that all compliance issues have required fields
        for issue in self.compliance_issues:
            if not issue.id or not issue.regulation or not issue.issue:
                return False
            if issue.severity not in ['low', 'medium', 'high']:
                return False
        
        # Check that all redlining suggestions have required fields
        for suggestion in self.redlining_suggestions:
            if not suggestion.clause_id or not suggestion.original_text or not suggestion.suggested_text:
                return False
        
        return True


# =============================================================================
# Section Dataclasses for Comprehensive Schema
# =============================================================================

# Field name mappings from Python attribute names to schema field names
# These mappings are used by to_dict() and from_dict() methods

ADMINISTRATIVE_FIELD_MAPPING = {
    'contract_term_renewal_extensions': 'Contract Term, Renewal & Extensions',
    'bonding_surety_insurance': 'Bonding, Surety, & Insurance Obligations',
    'retainage_progress_payments': 'Retainage, Progress Payments & Final Payment Terms',
    'pay_when_paid': 'Pay-When-Paid, Pay-If-Paid, or Owner Payment Contingencies',
    'price_escalation': 'Price Escalation Clauses (Labor, Materials, Fuel, Inflation Adjustments)',
    'fuel_price_adjustment': 'Fuel Price Adjustment / Fuel Cost Caps',
    'change_orders': 'Change Orders, Scope Adjustments & Modifications',
    'termination_for_convenience': 'Termination for Convenience (Owner/Agency Right to Terminate Without Cause)',
    'termination_for_cause': 'Termination for Cause / Default by Contractor',
    'bid_protest_procedures': 'Bid Protest Procedures & Claims of Improper Award',
    'bid_tabulation': 'Bid Tabulation, Competition & Award Process Requirements',
    'contractor_qualification': 'Contractor Qualification, Licensing & Certification Requirements',
    'release_orders': 'Release Orders, Task Orders & Work Authorization Protocols',
    'assignment_novation': 'Assignment & Novation Restrictions (Transfer of Contract Rights)',
    'audit_rights': 'Audit Rights, Recordkeeping & Document Retention Obligations',
    'notice_requirements': 'Notice Requirements & Claim Timeframes (Notice to Cure, Delay Notices, Termination Notices, etc.)',
}

TECHNICAL_FIELD_MAPPING = {
    'scope_of_work': 'Scope of Work (Work Inclusions, Exclusions & Defined Deliverables)',
    'performance_schedule': 'Performance Schedule, Time for Completion & Critical Path Obligations',
    'delays': 'Delays of Any Kind (Force Majeure, Acts of God, Weather, Owner-Caused, Unforeseen Events)',
    'suspension_of_work': 'Suspension of Work, Work Stoppages & Agency Directives',
    'submittals': 'Submittals, Documentation & Approval Requirements',
    'emergency_contingency': 'Emergency & Contingency Work Obligations',
    'permits_licensing': 'Permits, Licensing & Regulatory Approvals for Work',
    'warranty': 'Warranty, Guarantee & Defects Liability Periods',
    'use_of_aps_tools': 'Use of APS Tools, Equipment, Materials or Supplies',
    'owner_supplied_support': 'Owner-Supplied Support, Utilities & Site Access Provisions',
    'field_ticket': 'Field Ticket, Daily Work Log & Documentation Requirements',
    'mobilization_demobilization': 'Mobilization & Demobilization Provisions',
    'utility_coordination': 'Utility Coordination, Locate Risk & Conflict Avoidance',
    'delivery_deadlines': 'Delivery Deadlines, Milestone Dates, Substantial & Final Completion Standards',
    'punch_list': 'Punch List, Closeout Procedures & Acceptance of Work',
    'worksite_coordination': 'Worksite Coordination, Access Restrictions & Sequencing Obligations',
    'deliverables': 'Deliverables, Digital Submissions & Documentation Standards',
}

LEGAL_RISK_FIELD_MAPPING = {
    'indemnification': 'Indemnification, Defense & Hold Harmless Provisions',
    'duty_to_defend': 'Duty to Defend vs. Indemnify Scope Clarifications',
    'limitations_of_liability': 'Limitations of Liability, Damage Caps & Waivers of Consequential Damages',
    'insurance_coverage': 'Insurance Coverage, Additional Insured & Waiver of Subrogation Clauses',
    'dispute_resolution': 'Dispute Resolution (Mediation, Arbitration, Litigation)',
    'flow_down_clauses': 'Flow-Down Clauses (Prime-to-Subcontract Risk Pass-Through)',
    'subcontracting_restrictions': 'Subcontracting Restrictions, Approval & Substitution Requirements',
    'background_screening': 'Background Screening, Security Clearance & Worker Eligibility Requirements',
    'safety_standards': 'Safety Standards, OSHA Compliance & Site-Specific Safety Obligations',
    'site_conditions': 'Site Conditions, Differing Site Conditions & Changed Circumstances Clauses',
    'environmental_hazards': 'Environmental Hazards, Waste Disposal & Hazardous Materials Provisions',
    'conflicting_documents': 'Conflicting Documents / Order of Precedence Clauses',
    'setoff_withholding': "Setoff & Withholding Rights (Owner's Right to Deduct or Withhold Payment)",
}

REGULATORY_FIELD_MAPPING = {
    'certified_payroll': 'Certified Payroll, Recordkeeping & Reporting Obligations',
    'prevailing_wage': 'Prevailing Wage, Davis-Bacon & Federal/State Wage Compliance',
    'eeo_non_discrimination': 'EEO, Non-Discrimination, MWBE/DBE Participation Requirements',
    'anti_lobbying': 'Anti-Lobbying / Cone of Silence Provisions',
    'apprenticeship_training': 'Apprenticeship, Training & Workforce Development Requirements',
    'immigration_everify': 'Immigration / E-Verify Compliance Obligations',
    'worker_classification': 'Worker Classification & Independent Contractor Restrictions',
    'drug_free_workplace': 'Drug-Free Workplace Programs & Substance Testing Requirements',
}

DATA_TECHNOLOGY_FIELD_MAPPING = {
    'data_ownership': 'Data Ownership, Access & Rights to Digital Deliverables',
    'ai_technology_use': 'AI / Technology Use Restrictions (Automation, Digital Tools, Proprietary Systems)',
    'digital_surveillance': 'Digital Surveillance, GIS-Tagged Deliverables & Monitoring Requirements',
    'gis_digital_workflow': 'GIS, Digital Workflow Integration & Electronic Submittals',
    'confidentiality': 'Confidentiality, Data Security & Records Retention Obligations',
    'intellectual_property': 'Intellectual Property, Licensing & Ownership of Work Product',
    'cybersecurity': 'Cybersecurity Standards, Breach Notification & IT System Use Policies',
}


def _create_reverse_mapping(mapping: Dict[str, str]) -> Dict[str, str]:
    """Create a reverse mapping from schema field names to Python attribute names."""
    return {v: k for k, v in mapping.items()}


@dataclass
class AdministrativeAndCommercialTerms:
    """
    Section II: Administrative & Commercial Terms (16 clause types).
    
    Contains clause blocks for administrative and commercial aspects of contracts
    including terms, payments, termination, and procedural requirements.
    """
    contract_term_renewal_extensions: Optional[ClauseBlock] = None
    bonding_surety_insurance: Optional[ClauseBlock] = None
    retainage_progress_payments: Optional[ClauseBlock] = None
    pay_when_paid: Optional[ClauseBlock] = None
    price_escalation: Optional[ClauseBlock] = None
    fuel_price_adjustment: Optional[ClauseBlock] = None
    change_orders: Optional[ClauseBlock] = None
    termination_for_convenience: Optional[ClauseBlock] = None
    termination_for_cause: Optional[ClauseBlock] = None
    bid_protest_procedures: Optional[ClauseBlock] = None
    bid_tabulation: Optional[ClauseBlock] = None
    contractor_qualification: Optional[ClauseBlock] = None
    release_orders: Optional[ClauseBlock] = None
    assignment_novation: Optional[ClauseBlock] = None
    audit_rights: Optional[ClauseBlock] = None
    notice_requirements: Optional[ClauseBlock] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        
        Maps Python field names to schema field names and omits None values.
        
        Returns:
            Dictionary representation matching the output_schemas_v1.json 
            administrative_and_commercial_terms structure
        """
        result: Dict[str, Any] = {}
        for python_name, schema_name in ADMINISTRATIVE_FIELD_MAPPING.items():
            value = getattr(self, python_name)
            if value is not None:
                result[schema_name] = value.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AdministrativeAndCommercialTerms':
        """
        Create an AdministrativeAndCommercialTerms from a dictionary.
        
        Handles both schema format (with full clause names) and Python format (with underscores).
        
        Args:
            data: Dictionary containing section data. Accepts keys in either format.
            
        Returns:
            AdministrativeAndCommercialTerms instance with populated clause blocks
        """
        reverse_mapping = _create_reverse_mapping(ADMINISTRATIVE_FIELD_MAPPING)
        kwargs: Dict[str, Optional[ClauseBlock]] = {}
        
        for key, value in data.items():
            # Determine the Python attribute name
            if key in reverse_mapping:
                python_name = reverse_mapping[key]
            elif key in ADMINISTRATIVE_FIELD_MAPPING:
                python_name = key
            else:
                continue  # Skip unknown keys
            
            # Parse the ClauseBlock if value is not None
            if value is not None:
                if isinstance(value, dict):
                    kwargs[python_name] = ClauseBlock.from_dict(value)
                elif isinstance(value, ClauseBlock):
                    kwargs[python_name] = value
        
        return cls(**kwargs)


@dataclass
class TechnicalAndPerformanceTerms:
    """
    Section III: Technical & Performance Terms (17 clause types).
    
    Contains clause blocks for technical and performance aspects of contracts
    including scope, schedule, delays, warranties, and deliverables.
    """
    scope_of_work: Optional[ClauseBlock] = None
    performance_schedule: Optional[ClauseBlock] = None
    delays: Optional[ClauseBlock] = None
    suspension_of_work: Optional[ClauseBlock] = None
    submittals: Optional[ClauseBlock] = None
    emergency_contingency: Optional[ClauseBlock] = None
    permits_licensing: Optional[ClauseBlock] = None
    warranty: Optional[ClauseBlock] = None
    use_of_aps_tools: Optional[ClauseBlock] = None
    owner_supplied_support: Optional[ClauseBlock] = None
    field_ticket: Optional[ClauseBlock] = None
    mobilization_demobilization: Optional[ClauseBlock] = None
    utility_coordination: Optional[ClauseBlock] = None
    delivery_deadlines: Optional[ClauseBlock] = None
    punch_list: Optional[ClauseBlock] = None
    worksite_coordination: Optional[ClauseBlock] = None
    deliverables: Optional[ClauseBlock] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        
        Maps Python field names to schema field names and omits None values.
        
        Returns:
            Dictionary representation matching the output_schemas_v1.json 
            technical_and_performance_terms structure
        """
        result: Dict[str, Any] = {}
        for python_name, schema_name in TECHNICAL_FIELD_MAPPING.items():
            value = getattr(self, python_name)
            if value is not None:
                result[schema_name] = value.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TechnicalAndPerformanceTerms':
        """
        Create a TechnicalAndPerformanceTerms from a dictionary.
        
        Handles both schema format (with full clause names) and Python format (with underscores).
        
        Args:
            data: Dictionary containing section data. Accepts keys in either format.
            
        Returns:
            TechnicalAndPerformanceTerms instance with populated clause blocks
        """
        reverse_mapping = _create_reverse_mapping(TECHNICAL_FIELD_MAPPING)
        kwargs: Dict[str, Optional[ClauseBlock]] = {}
        
        for key, value in data.items():
            # Determine the Python attribute name
            if key in reverse_mapping:
                python_name = reverse_mapping[key]
            elif key in TECHNICAL_FIELD_MAPPING:
                python_name = key
            else:
                continue  # Skip unknown keys
            
            # Parse the ClauseBlock if value is not None
            if value is not None:
                if isinstance(value, dict):
                    kwargs[python_name] = ClauseBlock.from_dict(value)
                elif isinstance(value, ClauseBlock):
                    kwargs[python_name] = value
        
        return cls(**kwargs)


@dataclass
class LegalRiskAndEnforcement:
    """
    Section IV: Legal Risk & Enforcement (13 clause types).
    
    Contains clause blocks for legal risk and enforcement aspects of contracts
    including indemnification, liability, insurance, and dispute resolution.
    """
    indemnification: Optional[ClauseBlock] = None
    duty_to_defend: Optional[ClauseBlock] = None
    limitations_of_liability: Optional[ClauseBlock] = None
    insurance_coverage: Optional[ClauseBlock] = None
    dispute_resolution: Optional[ClauseBlock] = None
    flow_down_clauses: Optional[ClauseBlock] = None
    subcontracting_restrictions: Optional[ClauseBlock] = None
    background_screening: Optional[ClauseBlock] = None
    safety_standards: Optional[ClauseBlock] = None
    site_conditions: Optional[ClauseBlock] = None
    environmental_hazards: Optional[ClauseBlock] = None
    conflicting_documents: Optional[ClauseBlock] = None
    setoff_withholding: Optional[ClauseBlock] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        
        Maps Python field names to schema field names and omits None values.
        
        Returns:
            Dictionary representation matching the output_schemas_v1.json 
            legal_risk_and_enforcement structure
        """
        result: Dict[str, Any] = {}
        for python_name, schema_name in LEGAL_RISK_FIELD_MAPPING.items():
            value = getattr(self, python_name)
            if value is not None:
                result[schema_name] = value.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LegalRiskAndEnforcement':
        """
        Create a LegalRiskAndEnforcement from a dictionary.
        
        Handles both schema format (with full clause names) and Python format (with underscores).
        
        Args:
            data: Dictionary containing section data. Accepts keys in either format.
            
        Returns:
            LegalRiskAndEnforcement instance with populated clause blocks
        """
        reverse_mapping = _create_reverse_mapping(LEGAL_RISK_FIELD_MAPPING)
        kwargs: Dict[str, Optional[ClauseBlock]] = {}
        
        for key, value in data.items():
            # Determine the Python attribute name
            if key in reverse_mapping:
                python_name = reverse_mapping[key]
            elif key in LEGAL_RISK_FIELD_MAPPING:
                python_name = key
            else:
                continue  # Skip unknown keys
            
            # Parse the ClauseBlock if value is not None
            if value is not None:
                if isinstance(value, dict):
                    kwargs[python_name] = ClauseBlock.from_dict(value)
                elif isinstance(value, ClauseBlock):
                    kwargs[python_name] = value
        
        return cls(**kwargs)


@dataclass
class RegulatoryAndComplianceTerms:
    """
    Section V: Regulatory & Compliance Terms (8 clause types).
    
    Contains clause blocks for regulatory and compliance aspects of contracts
    including payroll, wages, EEO, and workforce requirements.
    """
    certified_payroll: Optional[ClauseBlock] = None
    prevailing_wage: Optional[ClauseBlock] = None
    eeo_non_discrimination: Optional[ClauseBlock] = None
    anti_lobbying: Optional[ClauseBlock] = None
    apprenticeship_training: Optional[ClauseBlock] = None
    immigration_everify: Optional[ClauseBlock] = None
    worker_classification: Optional[ClauseBlock] = None
    drug_free_workplace: Optional[ClauseBlock] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        
        Maps Python field names to schema field names and omits None values.
        
        Returns:
            Dictionary representation matching the output_schemas_v1.json 
            regulatory_and_compliance_terms structure
        """
        result: Dict[str, Any] = {}
        for python_name, schema_name in REGULATORY_FIELD_MAPPING.items():
            value = getattr(self, python_name)
            if value is not None:
                result[schema_name] = value.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RegulatoryAndComplianceTerms':
        """
        Create a RegulatoryAndComplianceTerms from a dictionary.
        
        Handles both schema format (with full clause names) and Python format (with underscores).
        
        Args:
            data: Dictionary containing section data. Accepts keys in either format.
            
        Returns:
            RegulatoryAndComplianceTerms instance with populated clause blocks
        """
        reverse_mapping = _create_reverse_mapping(REGULATORY_FIELD_MAPPING)
        kwargs: Dict[str, Optional[ClauseBlock]] = {}
        
        for key, value in data.items():
            # Determine the Python attribute name
            if key in reverse_mapping:
                python_name = reverse_mapping[key]
            elif key in REGULATORY_FIELD_MAPPING:
                python_name = key
            else:
                continue  # Skip unknown keys
            
            # Parse the ClauseBlock if value is not None
            if value is not None:
                if isinstance(value, dict):
                    kwargs[python_name] = ClauseBlock.from_dict(value)
                elif isinstance(value, ClauseBlock):
                    kwargs[python_name] = value
        
        return cls(**kwargs)


@dataclass
class DataTechnologyAndDeliverables:
    """
    Section VI: Data, Technology & Deliverables (7 clause types).
    
    Contains clause blocks for data, technology, and deliverables aspects of contracts
    including data ownership, AI use, cybersecurity, and intellectual property.
    """
    data_ownership: Optional[ClauseBlock] = None
    ai_technology_use: Optional[ClauseBlock] = None
    digital_surveillance: Optional[ClauseBlock] = None
    gis_digital_workflow: Optional[ClauseBlock] = None
    confidentiality: Optional[ClauseBlock] = None
    intellectual_property: Optional[ClauseBlock] = None
    cybersecurity: Optional[ClauseBlock] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        
        Maps Python field names to schema field names and omits None values.
        
        Returns:
            Dictionary representation matching the output_schemas_v1.json 
            data_technology_and_deliverables structure
        """
        result: Dict[str, Any] = {}
        for python_name, schema_name in DATA_TECHNOLOGY_FIELD_MAPPING.items():
            value = getattr(self, python_name)
            if value is not None:
                result[schema_name] = value.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataTechnologyAndDeliverables':
        """
        Create a DataTechnologyAndDeliverables from a dictionary.
        
        Handles both schema format (with full clause names) and Python format (with underscores).
        
        Args:
            data: Dictionary containing section data. Accepts keys in either format.
            
        Returns:
            DataTechnologyAndDeliverables instance with populated clause blocks
        """
        reverse_mapping = _create_reverse_mapping(DATA_TECHNOLOGY_FIELD_MAPPING)
        kwargs: Dict[str, Optional[ClauseBlock]] = {}
        
        for key, value in data.items():
            # Determine the Python attribute name
            if key in reverse_mapping:
                python_name = reverse_mapping[key]
            elif key in DATA_TECHNOLOGY_FIELD_MAPPING:
                python_name = key
            else:
                continue  # Skip unknown keys
            
            # Parse the ClauseBlock if value is not None
            if value is not None:
                if isinstance(value, dict):
                    kwargs[python_name] = ClauseBlock.from_dict(value)
                elif isinstance(value, ClauseBlock):
                    kwargs[python_name] = value
        
        return cls(**kwargs)


@dataclass
class ComprehensiveAnalysisResult:
    """
    Complete analysis result matching output_schemas_v1.json.
    
    This is the top-level data structure for comprehensive contract analysis,
    containing all 8 schema sections plus metadata for internal tracking.
    
    Attributes:
        schema_version: Version of the schema used for this analysis
        contract_overview: Section I - Contract Overview with 8 required fields
        administrative_and_commercial_terms: Section II - Administrative & Commercial Terms (16 clause types)
        technical_and_performance_terms: Section III - Technical & Performance Terms (17 clause types)
        legal_risk_and_enforcement: Section IV - Legal Risk & Enforcement (13 clause types)
        regulatory_and_compliance_terms: Section V - Regulatory & Compliance Terms (8 clause types)
        data_technology_and_deliverables: Section VI - Data, Technology & Deliverables (7 clause types)
        supplemental_operational_risks: Section VII - Supplemental Operational Risks (up to 9 entries)
        metadata: Internal tracking metadata for the contract analysis
    """
    schema_version: str
    contract_overview: ContractOverview
    administrative_and_commercial_terms: AdministrativeAndCommercialTerms
    technical_and_performance_terms: TechnicalAndPerformanceTerms
    legal_risk_and_enforcement: LegalRiskAndEnforcement
    regulatory_and_compliance_terms: RegulatoryAndComplianceTerms
    data_technology_and_deliverables: DataTechnologyAndDeliverables
    supplemental_operational_risks: List[ClauseBlock]
    metadata: ContractMetadata
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        
        Maps Python field names to schema field names:
        - schema_version -> "schema_version"
        - contract_overview -> "contract_overview"
        - administrative_and_commercial_terms -> "administrative_and_commercial_terms"
        - technical_and_performance_terms -> "technical_and_performance_terms"
        - legal_risk_and_enforcement -> "legal_risk_and_enforcement"
        - regulatory_and_compliance_terms -> "regulatory_and_compliance_terms"
        - data_technology_and_deliverables -> "data_technology_and_deliverables"
        - supplemental_operational_risks -> "supplemental_operational_risks"
        - metadata -> "metadata"
        
        Returns:
            Dictionary representation matching the output_schemas_v1.json structure
        """
        return {
            'schema_version': self.schema_version,
            'contract_overview': self.contract_overview.to_dict(),
            'administrative_and_commercial_terms': self.administrative_and_commercial_terms.to_dict(),
            'technical_and_performance_terms': self.technical_and_performance_terms.to_dict(),
            'legal_risk_and_enforcement': self.legal_risk_and_enforcement.to_dict(),
            'regulatory_and_compliance_terms': self.regulatory_and_compliance_terms.to_dict(),
            'data_technology_and_deliverables': self.data_technology_and_deliverables.to_dict(),
            'supplemental_operational_risks': [block.to_dict() for block in self.supplemental_operational_risks],
            'metadata': self.metadata.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComprehensiveAnalysisResult':
        """
        Create a ComprehensiveAnalysisResult from a dictionary.
        
        Handles parsing of all nested objects including:
        - ContractOverview
        - All 6 section models (AdministrativeAndCommercialTerms, etc.)
        - List of ClauseBlock for supplemental_operational_risks
        - ContractMetadata
        
        Args:
            data: Dictionary containing comprehensive analysis result data.
                  Accepts keys in schema format (snake_case).
            
        Returns:
            ComprehensiveAnalysisResult instance with all fields populated
            
        Raises:
            KeyError: If required fields are missing from the data
            ValueError: If nested objects contain invalid data
        """
        # Parse schema version
        schema_version = data.get('schema_version', '1.0')
        
        # Parse contract overview
        contract_overview_data = data.get('contract_overview', {})
        contract_overview = ContractOverview.from_dict(contract_overview_data)
        
        # Parse section models
        admin_data = data.get('administrative_and_commercial_terms', {})
        administrative_and_commercial_terms = AdministrativeAndCommercialTerms.from_dict(admin_data)
        
        technical_data = data.get('technical_and_performance_terms', {})
        technical_and_performance_terms = TechnicalAndPerformanceTerms.from_dict(technical_data)
        
        legal_data = data.get('legal_risk_and_enforcement', {})
        legal_risk_and_enforcement = LegalRiskAndEnforcement.from_dict(legal_data)
        
        regulatory_data = data.get('regulatory_and_compliance_terms', {})
        regulatory_and_compliance_terms = RegulatoryAndComplianceTerms.from_dict(regulatory_data)
        
        data_tech_data = data.get('data_technology_and_deliverables', {})
        data_technology_and_deliverables = DataTechnologyAndDeliverables.from_dict(data_tech_data)
        
        # Parse supplemental operational risks (list of ClauseBlocks)
        supplemental_data = data.get('supplemental_operational_risks', [])
        supplemental_operational_risks: List[ClauseBlock] = []
        for item in supplemental_data:
            if isinstance(item, dict):
                supplemental_operational_risks.append(ClauseBlock.from_dict(item))
            elif isinstance(item, ClauseBlock):
                supplemental_operational_risks.append(item)
        
        # Parse metadata
        metadata_data = data.get('metadata', {})
        metadata = ContractMetadata.from_dict(metadata_data)
        
        return cls(
            schema_version=schema_version,
            contract_overview=contract_overview,
            administrative_and_commercial_terms=administrative_and_commercial_terms,
            technical_and_performance_terms=technical_and_performance_terms,
            legal_risk_and_enforcement=legal_risk_and_enforcement,
            regulatory_and_compliance_terms=regulatory_and_compliance_terms,
            data_technology_and_deliverables=data_technology_and_deliverables,
            supplemental_operational_risks=supplemental_operational_risks,
            metadata=metadata
        )
    
    def validate(self) -> bool:
        """
        Validate that the analysis result has all required fields and valid values.
        
        Checks:
        - schema_version is not empty
        - contract_overview has valid enum values (risk_level, bid_model)
        - All section models exist (can be empty but must be present)
        - metadata has required fields
        
        Returns:
            True if valid, False otherwise
        """
        # Check schema version
        if not self.schema_version:
            return False
        
        # Check contract overview exists and has valid values
        if not self.contract_overview:
            return False
        
        # Validate enum values in contract overview
        if self.contract_overview.general_risk_level not in VALID_RISK_LEVELS:
            return False
        if self.contract_overview.bid_model not in VALID_BID_MODELS:
            return False
        
        # Check all section models exist (they can be empty but must be present)
        if self.administrative_and_commercial_terms is None:
            return False
        if self.technical_and_performance_terms is None:
            return False
        if self.legal_risk_and_enforcement is None:
            return False
        if self.regulatory_and_compliance_terms is None:
            return False
        if self.data_technology_and_deliverables is None:
            return False
        
        # supplemental_operational_risks can be empty list but must exist
        if self.supplemental_operational_risks is None:
            return False
        
        # Check metadata exists and has required fields
        if not self.metadata:
            return False
        if not self.metadata.filename or not self.metadata.analyzed_at:
            return False
        
        return True
