"""
Exhaustiveness Gate Data Models

This module defines the data models for the exhaustiveness gate verification system.
All models support serialization to/from dictionaries for JSON compatibility.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any


class PresenceStatus(Enum):
    """Status indicating presence of a finding in the contract."""
    PRESENT = "present"      # Definitively found in contract
    ABSENT = "absent"        # Definitively not in contract
    UNCERTAIN = "uncertain"  # Cannot determine with certainty


@dataclass
class ContractChunk:
    """
    A chunk of contract text with metadata.
    
    Tracks position, overlap regions, and chunk index for
    result merging and deduplication.
    """
    chunk_index: int  # 0-based index of this chunk
    total_chunks: int  # Total number of chunks
    text: str  # The chunk text content
    start_position: int  # Character position in original contract
    end_position: int  # End character position in original contract
    overlap_start: int  # Characters of overlap at start (0 for first chunk)
    overlap_end: int  # Characters of overlap at end (0 for last chunk)
    estimated_tokens: int  # Estimated token count for this chunk
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'chunk_index': self.chunk_index,
            'total_chunks': self.total_chunks,
            'text': self.text,
            'start_position': self.start_position,
            'end_position': self.end_position,
            'overlap_start': self.overlap_start,
            'overlap_end': self.overlap_end,
            'estimated_tokens': self.estimated_tokens
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContractChunk':
        """Create from dictionary."""
        return cls(
            chunk_index=data['chunk_index'],
            total_chunks=data['total_chunks'],
            text=data['text'],
            start_position=data['start_position'],
            end_position=data['end_position'],
            overlap_start=data['overlap_start'],
            overlap_end=data['overlap_end'],
            estimated_tokens=data['estimated_tokens']
        )
    
    def is_in_overlap_region(self, position: int) -> bool:
        """Check if a position falls within an overlap region."""
        # Check start overlap
        if self.overlap_start > 0 and position < self.start_position + self.overlap_start:
            return True
        # Check end overlap
        if self.overlap_end > 0 and position >= self.end_position - self.overlap_end:
            return True
        return False


@dataclass
class SourceReference:
    """Reference to source text in the contract."""
    clause_id: Optional[str]
    page_number: Optional[int]
    text_excerpt: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'clause_id': self.clause_id,
            'page_number': self.page_number,
            'text_excerpt': self.text_excerpt
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SourceReference':
        """Create from dictionary."""
        return cls(
            clause_id=data.get('clause_id'),
            page_number=data.get('page_number'),
            text_excerpt=data['text_excerpt']
        )


@dataclass
class VerifiedFinding:
    """
    A finding with verification metadata.
    
    Wraps any finding type (Clause, Risk, etc.) with confidence
    score, presence status, and verification details.
    """
    finding_type: str  # "clause", "risk", "compliance", "redlining"
    finding_data: Dict[str, Any]  # Original finding data
    confidence_score: float  # 0.0 to 1.0
    presence_status: PresenceStatus
    passes_found_in: int  # Number of passes containing this finding
    total_passes: int
    is_verified: bool  # Whether verification was performed
    verification_source: Optional[str]  # Contract text supporting finding
    is_hallucinated: bool  # Whether flagged as potential hallucination
    chunk_sources: List[int] = field(default_factory=list)  # Chunk indices where found
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'finding_type': self.finding_type,
            'finding_data': self.finding_data,
            'confidence_score': self.confidence_score,
            'presence_status': self.presence_status.value,
            'passes_found_in': self.passes_found_in,
            'total_passes': self.total_passes,
            'is_verified': self.is_verified,
            'verification_source': self.verification_source,
            'is_hallucinated': self.is_hallucinated,
            'chunk_sources': self.chunk_sources
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VerifiedFinding':
        """Create from dictionary."""
        return cls(
            finding_type=data['finding_type'],
            finding_data=data['finding_data'],
            confidence_score=data['confidence_score'],
            presence_status=PresenceStatus(data['presence_status']),
            passes_found_in=data['passes_found_in'],
            total_passes=data['total_passes'],
            is_verified=data['is_verified'],
            verification_source=data.get('verification_source'),
            is_hallucinated=data['is_hallucinated'],
            chunk_sources=data.get('chunk_sources', [])
        )


@dataclass
class VerificationMetadata:
    """
    Metadata about the verification process.
    
    Records details about the multi-pass analysis and verification
    for audit and review purposes.
    """
    num_passes: int
    pass_timestamps: List[datetime]
    total_findings_before_verification: int
    total_findings_after_verification: int
    hallucinations_detected: int
    conflicts_found: int
    conflicts_resolved: int
    average_confidence_score: float
    verification_duration_seconds: float
    chunks_processed: int = 0
    total_tokens_processed: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'num_passes': self.num_passes,
            'pass_timestamps': [ts.isoformat() for ts in self.pass_timestamps],
            'total_findings_before_verification': self.total_findings_before_verification,
            'total_findings_after_verification': self.total_findings_after_verification,
            'hallucinations_detected': self.hallucinations_detected,
            'conflicts_found': self.conflicts_found,
            'conflicts_resolved': self.conflicts_resolved,
            'average_confidence_score': self.average_confidence_score,
            'verification_duration_seconds': self.verification_duration_seconds,
            'chunks_processed': self.chunks_processed,
            'total_tokens_processed': self.total_tokens_processed
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VerificationMetadata':
        """Create from dictionary."""
        return cls(
            num_passes=data['num_passes'],
            pass_timestamps=[datetime.fromisoformat(ts) for ts in data['pass_timestamps']],
            total_findings_before_verification=data['total_findings_before_verification'],
            total_findings_after_verification=data['total_findings_after_verification'],
            hallucinations_detected=data['hallucinations_detected'],
            conflicts_found=data['conflicts_found'],
            conflicts_resolved=data['conflicts_resolved'],
            average_confidence_score=data['average_confidence_score'],
            verification_duration_seconds=data['verification_duration_seconds'],
            chunks_processed=data.get('chunks_processed', 0),
            total_tokens_processed=data.get('total_tokens_processed', 0)
        )


@dataclass
class CoverageReport:
    """
    Report on coverage of standard clause types.
    
    Shows which standard clause types were found, not found,
    or uncertain, along with coverage percentage.
    """
    clause_types_found: List[str]
    clause_types_not_found: List[str]
    clause_types_uncertain: List[str]
    coverage_percentage: float
    is_below_threshold: bool
    threshold: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'clause_types_found': self.clause_types_found,
            'clause_types_not_found': self.clause_types_not_found,
            'clause_types_uncertain': self.clause_types_uncertain,
            'coverage_percentage': self.coverage_percentage,
            'is_below_threshold': self.is_below_threshold,
            'threshold': self.threshold
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CoverageReport':
        """Create from dictionary."""
        return cls(
            clause_types_found=data['clause_types_found'],
            clause_types_not_found=data['clause_types_not_found'],
            clause_types_uncertain=data['clause_types_uncertain'],
            coverage_percentage=data['coverage_percentage'],
            is_below_threshold=data['is_below_threshold'],
            threshold=data['threshold']
        )


@dataclass
class Conflict:
    """
    A conflict between analysis passes.
    
    Represents a disagreement where passes produced different
    findings for the same aspect of the contract.
    """
    conflict_id: str
    conflict_type: str  # "presence", "content", "risk_level"
    finding_type: str  # "clause", "risk", etc.
    pass_findings: Dict[int, Dict[str, Any]]  # pass_number -> finding
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'conflict_id': self.conflict_id,
            'conflict_type': self.conflict_type,
            'finding_type': self.finding_type,
            'pass_findings': {str(k): v for k, v in self.pass_findings.items()},
            'description': self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conflict':
        """Create from dictionary."""
        return cls(
            conflict_id=data['conflict_id'],
            conflict_type=data['conflict_type'],
            finding_type=data['finding_type'],
            pass_findings={int(k): v for k, v in data['pass_findings'].items()},
            description=data['description']
        )


@dataclass
class ConflictResolution:
    """
    Resolution of a conflict between passes.
    
    Contains the resolved finding or both options if
    automatic resolution was not possible.
    """
    conflict: Conflict
    is_resolved: bool
    resolved_finding: Optional[VerifiedFinding]
    unresolved_options: Optional[List[VerifiedFinding]]
    resolution_method: str  # "verification", "consensus", "manual"
    explanation: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'conflict': self.conflict.to_dict(),
            'is_resolved': self.is_resolved,
            'resolved_finding': self.resolved_finding.to_dict() if self.resolved_finding else None,
            'unresolved_options': [f.to_dict() for f in self.unresolved_options] if self.unresolved_options else None,
            'resolution_method': self.resolution_method,
            'explanation': self.explanation
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConflictResolution':
        """Create from dictionary."""
        return cls(
            conflict=Conflict.from_dict(data['conflict']),
            is_resolved=data['is_resolved'],
            resolved_finding=VerifiedFinding.from_dict(data['resolved_finding']) if data.get('resolved_finding') else None,
            unresolved_options=[VerifiedFinding.from_dict(f) for f in data['unresolved_options']] if data.get('unresolved_options') else None,
            resolution_method=data['resolution_method'],
            explanation=data['explanation']
        )


@dataclass
class VerifiedQueryResponse:
    """
    A verified response to a user query.
    
    Contains the response text along with verification status
    and source references from the contract.
    """
    query: str
    response: str
    is_verified: bool
    verification_status: str  # "verified", "partially_verified", "unverified", "not_found"
    verified_portions: List[str]  # Parts of response that are verified
    unverified_portions: List[str]  # Parts that couldn't be verified
    source_references: List[SourceReference]
    confidence_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'query': self.query,
            'response': self.response,
            'is_verified': self.is_verified,
            'verification_status': self.verification_status,
            'verified_portions': self.verified_portions,
            'unverified_portions': self.unverified_portions,
            'source_references': [ref.to_dict() for ref in self.source_references],
            'confidence_score': self.confidence_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VerifiedQueryResponse':
        """Create from dictionary."""
        return cls(
            query=data['query'],
            response=data['response'],
            is_verified=data['is_verified'],
            verification_status=data['verification_status'],
            verified_portions=data['verified_portions'],
            unverified_portions=data['unverified_portions'],
            source_references=[SourceReference.from_dict(ref) for ref in data['source_references']],
            confidence_score=data['confidence_score']
        )


@dataclass
class VerifiedAnalysisResult:
    """
    Complete verified analysis result.
    
    Extends the base ComprehensiveAnalysisResult with verification metadata,
    confidence scores, and presence status for all findings.
    
    The base_result field stores the ComprehensiveAnalysisResult as a dictionary
    to maintain compatibility with serialization. Use get_base_result() to
    reconstruct the ComprehensiveAnalysisResult object.
    """
    base_result: Dict[str, Any]  # ComprehensiveAnalysisResult stored as dict
    verified_clauses: List[VerifiedFinding]
    verified_risks: List[VerifiedFinding]
    verified_compliance_issues: List[VerifiedFinding]
    verified_redlining_suggestions: List[VerifiedFinding]
    verification_metadata: VerificationMetadata
    coverage_report: CoverageReport
    conflicts: List[ConflictResolution]
    
    def get_base_result(self) -> 'ComprehensiveAnalysisResult':
        """
        Reconstruct the ComprehensiveAnalysisResult from the stored dictionary.
        
        Returns:
            ComprehensiveAnalysisResult instance
            
        Raises:
            ImportError: If ComprehensiveAnalysisResult cannot be imported
            ValueError: If base_result cannot be parsed
        """
        from src.analysis_models import ComprehensiveAnalysisResult
        return ComprehensiveAnalysisResult.from_dict(self.base_result)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'base_result': self.base_result,
            'verified_clauses': [c.to_dict() for c in self.verified_clauses],
            'verified_risks': [r.to_dict() for r in self.verified_risks],
            'verified_compliance_issues': [ci.to_dict() for ci in self.verified_compliance_issues],
            'verified_redlining_suggestions': [rs.to_dict() for rs in self.verified_redlining_suggestions],
            'verification_metadata': self.verification_metadata.to_dict(),
            'coverage_report': self.coverage_report.to_dict(),
            'conflicts': [c.to_dict() for c in self.conflicts]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VerifiedAnalysisResult':
        """Create from dictionary."""
        return cls(
            base_result=data['base_result'],
            verified_clauses=[VerifiedFinding.from_dict(c) for c in data['verified_clauses']],
            verified_risks=[VerifiedFinding.from_dict(r) for r in data['verified_risks']],
            verified_compliance_issues=[VerifiedFinding.from_dict(ci) for ci in data['verified_compliance_issues']],
            verified_redlining_suggestions=[VerifiedFinding.from_dict(rs) for rs in data['verified_redlining_suggestions']],
            verification_metadata=VerificationMetadata.from_dict(data['verification_metadata']),
            coverage_report=CoverageReport.from_dict(data['coverage_report']),
            conflicts=[ConflictResolution.from_dict(c) for c in data['conflicts']]
        )
    
    def to_pretty_string(self) -> str:
        """Format as human-readable text."""
        lines = []
        lines.append("=" * 60)
        lines.append("VERIFIED CONTRACT ANALYSIS REPORT")
        lines.append("=" * 60)
        lines.append("")
        
        # Verification Summary
        meta = self.verification_metadata
        lines.append("VERIFICATION SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Analysis Passes: {meta.num_passes}")
        lines.append(f"Chunks Processed: {meta.chunks_processed}")
        lines.append(f"Findings Before Verification: {meta.total_findings_before_verification}")
        lines.append(f"Findings After Verification: {meta.total_findings_after_verification}")
        lines.append(f"Hallucinations Detected: {meta.hallucinations_detected}")
        lines.append(f"Conflicts Found: {meta.conflicts_found}")
        lines.append(f"Conflicts Resolved: {meta.conflicts_resolved}")
        lines.append(f"Average Confidence: {meta.average_confidence_score:.2%}")
        lines.append(f"Duration: {meta.verification_duration_seconds:.1f}s")
        lines.append("")
        
        # Coverage Report
        cov = self.coverage_report
        lines.append("COVERAGE REPORT")
        lines.append("-" * 40)
        lines.append(f"Coverage: {cov.coverage_percentage:.1f}%")
        if cov.is_below_threshold:
            lines.append(f"⚠️ WARNING: Below threshold of {cov.threshold:.1f}%")
        lines.append(f"Found: {', '.join(cov.clause_types_found) or 'None'}")
        lines.append(f"Not Found: {', '.join(cov.clause_types_not_found) or 'None'}")
        lines.append(f"Uncertain: {', '.join(cov.clause_types_uncertain) or 'None'}")
        lines.append("")
        
        # Verified Clauses
        if self.verified_clauses:
            lines.append("VERIFIED CLAUSES")
            lines.append("-" * 40)
            for finding in self.verified_clauses:
                status_icon = self._get_status_icon(finding.presence_status)
                # Handle both legacy and comprehensive schema formats
                finding_desc = finding.finding_data.get('type', 
                              finding.finding_data.get('clause_summary', 'Unknown'))[:50]
                lines.append(f"{status_icon} [{finding.confidence_score:.0%}] {finding_desc}")
                if finding.is_hallucinated:
                    lines.append("   ⚠️ FLAGGED AS POTENTIAL HALLUCINATION")
            lines.append("")
        
        # Verified Risks
        if self.verified_risks:
            lines.append("VERIFIED RISKS")
            lines.append("-" * 40)
            for finding in self.verified_risks:
                status_icon = self._get_status_icon(finding.presence_status)
                # Handle both legacy and comprehensive schema formats
                severity = finding.finding_data.get('severity', 'unknown').upper()
                desc = finding.finding_data.get('description',
                       finding.finding_data.get('clause_summary', 'No description'))[:50]
                lines.append(f"{status_icon} [{finding.confidence_score:.0%}] [{severity}] {desc}...")
            lines.append("")
        
        # Conflicts
        if self.conflicts:
            lines.append("CONFLICTS")
            lines.append("-" * 40)
            for resolution in self.conflicts:
                status = "✓ Resolved" if resolution.is_resolved else "✗ Unresolved"
                lines.append(f"{status}: {resolution.conflict.description}")
                lines.append(f"   Method: {resolution.resolution_method}")
                lines.append(f"   Explanation: {resolution.explanation}")
            lines.append("")
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def _get_status_icon(self, status: PresenceStatus) -> str:
        """Get icon for presence status."""
        if status == PresenceStatus.PRESENT:
            return "✓"
        elif status == PresenceStatus.ABSENT:
            return "✗"
        else:
            return "?"
