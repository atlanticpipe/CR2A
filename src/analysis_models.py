"""
Analysis Result Data Models

This module defines the data models for contract analysis results.
All models support serialization to/from dictionaries for JSON compatibility.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Optional, Any


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
