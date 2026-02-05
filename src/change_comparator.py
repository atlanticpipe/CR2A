"""
Change Comparator Module

Compares two versions of a contract and identifies changes at the clause level.
Implements Requirements 4.1, 4.2, 4.3, 4.4, 4.5, and 4.6.
"""

import difflib
import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional

from src.analysis_models import ClauseBlock, ComprehensiveAnalysisResult


logger = logging.getLogger(__name__)


class ClauseChangeType(Enum):
    """Types of changes that can occur to a clause."""
    UNCHANGED = "unchanged"
    MODIFIED = "modified"
    ADDED = "added"
    DELETED = "deleted"


@dataclass
class ClauseComparison:
    """
    Represents the comparison result for a single clause.
    
    Attributes:
        clause_identifier: Identifier for the clause (e.g., section name)
        change_type: Type of change (unchanged, modified, added, deleted)
        old_content: Content from the old version (None if added)
        new_content: Content from the new version (None if deleted)
        similarity_score: Text similarity score (0.0 to 1.0)
    """
    clause_identifier: str
    change_type: ClauseChangeType
    old_content: Optional[str]
    new_content: Optional[str]
    similarity_score: float


@dataclass
class ContractDiff:
    """
    Represents the complete difference between two contract versions.
    
    Attributes:
        unchanged_clauses: List of clauses that did not change
        modified_clauses: List of clauses that were modified
        added_clauses: List of clauses that were added
        deleted_clauses: List of clauses that were deleted
        change_summary: Summary counts of changes
    """
    unchanged_clauses: List[ClauseComparison]
    modified_clauses: List[ClauseComparison]
    added_clauses: List[ClauseComparison]
    deleted_clauses: List[ClauseComparison]
    change_summary: Dict[str, int]


class ChangeComparator:
    """
    Compares two versions of a contract and identifies changes at the clause level.
    
    This class implements change detection as specified in Requirements 4.1-4.6.
    """
    
    # Threshold for considering clauses as unchanged (95% similarity)
    UNCHANGED_THRESHOLD = 0.95
    
    def __init__(self):
        """Initialize the change comparator."""
        logger.debug("ChangeComparator initialized")
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison.
        
        Implements Requirement 4.6: Text normalization for consistent comparison.
        
        Normalization includes:
        - Convert to lowercase
        - Collapse multiple whitespace to single space
        - Strip leading/trailing whitespace
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text string
        """
        if not text:
            return ""
        
        # Convert to lowercase
        normalized = text.lower()
        
        # Collapse multiple whitespace (spaces, tabs, newlines) to single space
        normalized = ' '.join(normalized.split())
        
        # Strip leading/trailing whitespace
        normalized = normalized.strip()
        
        return normalized
    
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two text strings.
        
        Implements Requirement 4.1: Text comparison for clause change detection.
        
        Uses difflib.SequenceMatcher to calculate similarity ratio.
        Text is normalized before comparison.
        
        Args:
            text1: First text string
            text2: Second text string
            
        Returns:
            Similarity score between 0.0 (completely different) and 1.0 (identical)
        """
        # Normalize both texts
        norm1 = self.normalize_text(text1)
        norm2 = self.normalize_text(text2)
        
        # Handle empty strings
        if not norm1 and not norm2:
            return 1.0  # Both empty = identical
        if not norm1 or not norm2:
            return 0.0  # One empty, one not = completely different
        
        # Calculate similarity using SequenceMatcher
        matcher = difflib.SequenceMatcher(None, norm1, norm2)
        similarity = matcher.ratio()
        
        logger.debug(
            "Text similarity calculated: %.3f (lengths: %d, %d)",
            similarity, len(norm1), len(norm2)
        )
        
        return similarity

    
    def compare_clauses(
        self,
        old_clause: Optional[ClauseBlock],
        new_clause: Optional[ClauseBlock],
        clause_identifier: str
    ) -> ClauseComparison:
        """
        Compare two clause blocks and classify the change.
        
        Implements Requirements 4.2, 4.3, 4.4, 4.5:
        - 4.2: Modified classification (similarity < 0.95)
        - 4.3: Addition detection (new clause exists, old does not)
        - 4.4: Deletion detection (old clause exists, new does not)
        - 4.5: Unchanged classification (similarity >= 0.95)
        
        Args:
            old_clause: Clause from the old version (None if added)
            new_clause: Clause from the new version (None if deleted)
            clause_identifier: Identifier for the clause
            
        Returns:
            ClauseComparison object with change classification
        """
        # Case 1: Clause was added (Requirement 4.3)
        if old_clause is None and new_clause is not None:
            logger.debug("Clause '%s' was added", clause_identifier)
            return ClauseComparison(
                clause_identifier=clause_identifier,
                change_type=ClauseChangeType.ADDED,
                old_content=None,
                new_content=new_clause.clause_language,
                similarity_score=0.0
            )
        
        # Case 2: Clause was deleted (Requirement 4.4)
        if old_clause is not None and new_clause is None:
            logger.debug("Clause '%s' was deleted", clause_identifier)
            return ClauseComparison(
                clause_identifier=clause_identifier,
                change_type=ClauseChangeType.DELETED,
                old_content=old_clause.clause_language,
                new_content=None,
                similarity_score=0.0
            )
        
        # Case 3: Both clauses exist - compare content
        if old_clause is not None and new_clause is not None:
            old_content = old_clause.clause_language
            new_content = new_clause.clause_language
            
            # Calculate similarity
            similarity = self.calculate_text_similarity(old_content, new_content)
            
            # Classify based on threshold
            if similarity >= self.UNCHANGED_THRESHOLD:
                # Requirement 4.5: Unchanged (similarity >= 0.95)
                logger.debug(
                    "Clause '%s' is unchanged (similarity: %.3f)",
                    clause_identifier, similarity
                )
                return ClauseComparison(
                    clause_identifier=clause_identifier,
                    change_type=ClauseChangeType.UNCHANGED,
                    old_content=old_content,
                    new_content=new_content,
                    similarity_score=similarity
                )
            else:
                # Requirement 4.2: Modified (similarity < 0.95)
                logger.debug(
                    "Clause '%s' was modified (similarity: %.3f)",
                    clause_identifier, similarity
                )
                return ClauseComparison(
                    clause_identifier=clause_identifier,
                    change_type=ClauseChangeType.MODIFIED,
                    old_content=old_content,
                    new_content=new_content,
                    similarity_score=similarity
                )
        
        # Should never reach here, but handle gracefully
        logger.warning("Unexpected clause comparison state for '%s'", clause_identifier)
        return ClauseComparison(
            clause_identifier=clause_identifier,
            change_type=ClauseChangeType.UNCHANGED,
            old_content=None,
            new_content=None,
            similarity_score=1.0
        )
    
    def _extract_clause_map(
        self,
        analysis: ComprehensiveAnalysisResult
    ) -> Dict[str, ClauseBlock]:
        """
        Extract all clauses from a comprehensive analysis result into a flat map.
        
        Args:
            analysis: Comprehensive analysis result
            
        Returns:
            Dictionary mapping clause identifiers to ClauseBlock objects
        """
        clause_map: Dict[str, ClauseBlock] = {}
        
        # Extract from administrative_and_commercial_terms
        admin = analysis.administrative_and_commercial_terms
        if admin.contract_term_renewal_extensions:
            clause_map['contract_term_renewal_extensions'] = admin.contract_term_renewal_extensions
        if admin.bonding_surety_insurance:
            clause_map['bonding_surety_insurance'] = admin.bonding_surety_insurance
        if admin.retainage_progress_payments:
            clause_map['retainage_progress_payments'] = admin.retainage_progress_payments
        if admin.pay_when_paid:
            clause_map['pay_when_paid'] = admin.pay_when_paid
        if admin.price_escalation:
            clause_map['price_escalation'] = admin.price_escalation
        if admin.fuel_price_adjustment:
            clause_map['fuel_price_adjustment'] = admin.fuel_price_adjustment
        if admin.change_orders:
            clause_map['change_orders'] = admin.change_orders
        if admin.termination_for_convenience:
            clause_map['termination_for_convenience'] = admin.termination_for_convenience
        if admin.termination_for_cause:
            clause_map['termination_for_cause'] = admin.termination_for_cause
        if admin.bid_protest_procedures:
            clause_map['bid_protest_procedures'] = admin.bid_protest_procedures
        if admin.bid_tabulation:
            clause_map['bid_tabulation'] = admin.bid_tabulation
        if admin.contractor_qualification:
            clause_map['contractor_qualification'] = admin.contractor_qualification
        if admin.release_orders:
            clause_map['release_orders'] = admin.release_orders
        if admin.assignment_novation:
            clause_map['assignment_novation'] = admin.assignment_novation
        if admin.audit_rights:
            clause_map['audit_rights'] = admin.audit_rights
        if admin.notice_requirements:
            clause_map['notice_requirements'] = admin.notice_requirements
        
        # Extract from technical_and_performance_terms
        tech = analysis.technical_and_performance_terms
        if tech.scope_of_work:
            clause_map['scope_of_work'] = tech.scope_of_work
        if tech.performance_schedule:
            clause_map['performance_schedule'] = tech.performance_schedule
        if tech.delays:
            clause_map['delays'] = tech.delays
        if tech.suspension_of_work:
            clause_map['suspension_of_work'] = tech.suspension_of_work
        if tech.submittals:
            clause_map['submittals'] = tech.submittals
        if tech.emergency_contingency:
            clause_map['emergency_contingency'] = tech.emergency_contingency
        if tech.permits_licensing:
            clause_map['permits_licensing'] = tech.permits_licensing
        if tech.warranty:
            clause_map['warranty'] = tech.warranty
        if tech.use_of_aps_tools:
            clause_map['use_of_aps_tools'] = tech.use_of_aps_tools
        if tech.owner_supplied_support:
            clause_map['owner_supplied_support'] = tech.owner_supplied_support
        if tech.field_ticket:
            clause_map['field_ticket'] = tech.field_ticket
        if tech.mobilization_demobilization:
            clause_map['mobilization_demobilization'] = tech.mobilization_demobilization
        if tech.utility_coordination:
            clause_map['utility_coordination'] = tech.utility_coordination
        if tech.delivery_deadlines:
            clause_map['delivery_deadlines'] = tech.delivery_deadlines
        if tech.punch_list:
            clause_map['punch_list'] = tech.punch_list
        if tech.worksite_coordination:
            clause_map['worksite_coordination'] = tech.worksite_coordination
        if tech.deliverables:
            clause_map['deliverables'] = tech.deliverables
        
        # Extract from legal_risk_and_enforcement
        legal = analysis.legal_risk_and_enforcement
        if legal.indemnification:
            clause_map['indemnification'] = legal.indemnification
        if legal.duty_to_defend:
            clause_map['duty_to_defend'] = legal.duty_to_defend
        if legal.limitations_of_liability:
            clause_map['limitations_of_liability'] = legal.limitations_of_liability
        if legal.insurance_coverage:
            clause_map['insurance_coverage'] = legal.insurance_coverage
        if legal.dispute_resolution:
            clause_map['dispute_resolution'] = legal.dispute_resolution
        if legal.flow_down_clauses:
            clause_map['flow_down_clauses'] = legal.flow_down_clauses
        if legal.subcontracting_restrictions:
            clause_map['subcontracting_restrictions'] = legal.subcontracting_restrictions
        if legal.background_screening:
            clause_map['background_screening'] = legal.background_screening
        if legal.safety_standards:
            clause_map['safety_standards'] = legal.safety_standards
        if legal.site_conditions:
            clause_map['site_conditions'] = legal.site_conditions
        if legal.environmental_hazards:
            clause_map['environmental_hazards'] = legal.environmental_hazards
        if legal.conflicting_documents:
            clause_map['conflicting_documents'] = legal.conflicting_documents
        if legal.setoff_withholding:
            clause_map['setoff_withholding'] = legal.setoff_withholding
        
        # Extract from regulatory_and_compliance_terms
        regulatory = analysis.regulatory_and_compliance_terms
        if regulatory.certified_payroll:
            clause_map['certified_payroll'] = regulatory.certified_payroll
        if regulatory.prevailing_wage:
            clause_map['prevailing_wage'] = regulatory.prevailing_wage
        if regulatory.eeo_non_discrimination:
            clause_map['eeo_non_discrimination'] = regulatory.eeo_non_discrimination
        if regulatory.anti_lobbying:
            clause_map['anti_lobbying'] = regulatory.anti_lobbying
        if regulatory.apprenticeship_training:
            clause_map['apprenticeship_training'] = regulatory.apprenticeship_training
        if regulatory.immigration_everify:
            clause_map['immigration_everify'] = regulatory.immigration_everify
        if regulatory.worker_classification:
            clause_map['worker_classification'] = regulatory.worker_classification
        if regulatory.drug_free_workplace:
            clause_map['drug_free_workplace'] = regulatory.drug_free_workplace
        
        # Extract from data_technology_and_deliverables
        data_tech = analysis.data_technology_and_deliverables
        if data_tech.data_ownership:
            clause_map['data_ownership'] = data_tech.data_ownership
        if data_tech.ai_technology_use:
            clause_map['ai_technology_use'] = data_tech.ai_technology_use
        if data_tech.digital_surveillance:
            clause_map['digital_surveillance'] = data_tech.digital_surveillance
        if data_tech.gis_digital_workflow:
            clause_map['gis_digital_workflow'] = data_tech.gis_digital_workflow
        if data_tech.confidentiality:
            clause_map['confidentiality'] = data_tech.confidentiality
        if data_tech.intellectual_property:
            clause_map['intellectual_property'] = data_tech.intellectual_property
        if data_tech.cybersecurity:
            clause_map['cybersecurity'] = data_tech.cybersecurity
        
        # Extract from supplemental_operational_risks
        for idx, clause in enumerate(analysis.supplemental_operational_risks):
            clause_map[f'supplemental_risk_{idx}'] = clause
        
        return clause_map
    
    def compare_contracts(
        self,
        old_analysis: ComprehensiveAnalysisResult,
        new_analysis: ComprehensiveAnalysisResult
    ) -> ContractDiff:
        """
        Compare two contract analyses and generate a complete diff.
        
        Implements Requirement 4.1: Contract comparison with clause-level change detection.
        
        Args:
            old_analysis: Analysis result from the old version
            new_analysis: Analysis result from the new version
            
        Returns:
            ContractDiff object containing all changes
            
        Raises:
            ValueError: If analysis objects are None or invalid
            RuntimeError: If comparison fails
        """
        # Validate inputs (Requirement 8.2)
        if old_analysis is None:
            logger.error("old_analysis is None")
            raise ValueError("old_analysis cannot be None")
        
        if new_analysis is None:
            logger.error("new_analysis is None")
            raise ValueError("new_analysis cannot be None")
        
        logger.info("Comparing contracts: old vs new")
        
        try:
            # Extract clause maps from both analyses
            old_clauses = self._extract_clause_map(old_analysis)
            new_clauses = self._extract_clause_map(new_analysis)
            
            # Get all unique clause identifiers
            all_identifiers = set(old_clauses.keys()) | set(new_clauses.keys())
            
            # Compare each clause
            unchanged_clauses: List[ClauseComparison] = []
            modified_clauses: List[ClauseComparison] = []
            added_clauses: List[ClauseComparison] = []
            deleted_clauses: List[ClauseComparison] = []
            
            for identifier in sorted(all_identifiers):
                try:
                    old_clause = old_clauses.get(identifier)
                    new_clause = new_clauses.get(identifier)
                    
                    comparison = self.compare_clauses(old_clause, new_clause, identifier)
                    
                    # Categorize by change type
                    if comparison.change_type == ClauseChangeType.UNCHANGED:
                        unchanged_clauses.append(comparison)
                    elif comparison.change_type == ClauseChangeType.MODIFIED:
                        modified_clauses.append(comparison)
                    elif comparison.change_type == ClauseChangeType.ADDED:
                        added_clauses.append(comparison)
                    elif comparison.change_type == ClauseChangeType.DELETED:
                        deleted_clauses.append(comparison)
                except Exception as e:
                    logger.error("Failed to compare clause '%s': %s", identifier, e)
                    # Continue with other clauses rather than failing completely
                    continue
            
            # Generate change summary
            change_summary = {
                'unchanged': len(unchanged_clauses),
                'modified': len(modified_clauses),
                'added': len(added_clauses),
                'deleted': len(deleted_clauses),
                'total': len(all_identifiers)
            }
            
            logger.info(
                "Contract comparison complete: %d unchanged, %d modified, %d added, %d deleted",
                change_summary['unchanged'],
                change_summary['modified'],
                change_summary['added'],
                change_summary['deleted']
            )
            
            return ContractDiff(
                unchanged_clauses=unchanged_clauses,
                modified_clauses=modified_clauses,
                added_clauses=added_clauses,
                deleted_clauses=deleted_clauses,
                change_summary=change_summary
            )
            
        except ValueError:
            raise
        except Exception as e:
            logger.error("Contract comparison failed: %s", e, exc_info=True)
            raise RuntimeError(f"Contract comparison failed: {e}")
