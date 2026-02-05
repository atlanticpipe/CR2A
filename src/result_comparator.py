"""
Result Comparator Module

Compares analysis results across multiple passes to identify
consensus findings, conflicts, and unique findings.
"""

import logging
import uuid
from typing import List, Dict, Any, Tuple, Set
from dataclasses import dataclass
from difflib import SequenceMatcher

from src.analysis_models import AnalysisResult, ComprehensiveAnalysisResult, Clause, Risk, ComplianceIssue, RedliningSuggestion
from src.exhaustiveness_models import Conflict

logger = logging.getLogger(__name__)


@dataclass
class ComparisonResult:
    """Result of comparing multiple analysis passes."""
    consensus_findings: List[Dict[str, Any]]  # Findings in all passes
    flagged_findings: List[Dict[str, Any]]  # Findings in some but not all passes
    conflicts: List[Conflict]  # Conflicting findings between passes
    pass_finding_counts: Dict[int, int]  # pass_number -> finding count


class ResultComparator:
    """
    Compares analysis results across multiple passes.
    
    Identifies consensus findings, conflicts, and unique findings
    to support confidence scoring and conflict resolution.
    """
    
    DEFAULT_SIMILARITY_THRESHOLD = 0.8
    
    def __init__(self, similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD):
        """
        Initialize the result comparator.
        
        Args:
            similarity_threshold: Minimum similarity to consider findings as matching
        """
        self.similarity_threshold = similarity_threshold
        logger.debug(f"ResultComparator initialized with similarity_threshold={similarity_threshold}")
    
    def compare_passes(
        self,
        pass_results: List  # List of AnalysisResult or ComprehensiveAnalysisResult
    ) -> ComparisonResult:
        """
        Compare results from multiple analysis passes.
        
        Args:
            pass_results: List of AnalysisResult from each pass
            
        Returns:
            ComparisonResult with consensus, conflicts, and unique findings
        """
        if not pass_results:
            return ComparisonResult(
                consensus_findings=[],
                flagged_findings=[],
                conflicts=[],
                pass_finding_counts={}
            )
        
        num_passes = len(pass_results)
        logger.info(f"Comparing {num_passes} analysis passes")
        
        # Extract all findings from each pass
        pass_findings = []
        for i, result in enumerate(pass_results):
            findings = self._extract_all_findings(result, pass_number=i)
            pass_findings.append(findings)
            logger.debug(f"Pass {i}: {len(findings)} findings")
        
        # Find consensus and flagged findings
        consensus, flagged, conflicts = self._categorize_findings(pass_findings, num_passes)
        
        # Calculate pass finding counts
        pass_counts = {i: len(findings) for i, findings in enumerate(pass_findings)}
        
        logger.info(f"Comparison complete: {len(consensus)} consensus, "
                   f"{len(flagged)} flagged, {len(conflicts)} conflicts")
        
        return ComparisonResult(
            consensus_findings=consensus,
            flagged_findings=flagged,
            conflicts=conflicts,
            pass_finding_counts=pass_counts
        )

    
    def _extract_all_findings(
        self,
        result,  # Can be AnalysisResult or ComprehensiveAnalysisResult
        pass_number: int
    ) -> List[Dict[str, Any]]:
        """
        Extract all findings from an AnalysisResult or ComprehensiveAnalysisResult into a flat list.
        
        Args:
            result: AnalysisResult or ComprehensiveAnalysisResult to extract from
            pass_number: Pass number for tracking
            
        Returns:
            List of finding dictionaries with type and pass info
        """
        findings = []
        
        # Check if this is a ComprehensiveAnalysisResult (new format)
        if hasattr(result, 'administrative_and_commercial_terms'):
            # Extract from comprehensive schema sections
            findings.extend(self._extract_from_comprehensive_result(result, pass_number))
        else:
            # Extract from legacy format
            findings.extend(self._extract_from_legacy_result(result, pass_number))
        
        return findings
    
    def _extract_from_comprehensive_result(
        self,
        result,  # ComprehensiveAnalysisResult
        pass_number: int
    ) -> List[Dict[str, Any]]:
        """
        Extract findings from ComprehensiveAnalysisResult.
        
        Args:
            result: ComprehensiveAnalysisResult to extract from
            pass_number: Pass number for tracking
            
        Returns:
            List of finding dictionaries
        """
        findings = []
        
        # Extract from all sections
        sections = [
            ('administrative_and_commercial_terms', result.administrative_and_commercial_terms),
            ('technical_and_performance_terms', result.technical_and_performance_terms),
            ('legal_risk_and_enforcement', result.legal_risk_and_enforcement),
            ('regulatory_and_compliance_terms', result.regulatory_and_compliance_terms),
            ('data_technology_and_deliverables', result.data_technology_and_deliverables),
        ]
        
        for section_name, section in sections:
            if section is None:
                continue
            
            # Get the section's __dict__ to access only data attributes, not methods
            section_dict = section.__dict__ if hasattr(section, '__dict__') else {}
            
            # Iterate through all clause blocks in the section
            for field_name, clause_block in section_dict.items():
                if field_name.startswith('_') or clause_block is None:
                    continue
                
                # Check if this is actually a ClauseBlock object
                if not hasattr(clause_block, 'clause_language'):
                    continue
                
                # Extract clause block as a finding
                findings.append({
                    'type': 'clause',
                    'data': {
                        'section': section_name,
                        'category': field_name,
                        'text': clause_block.clause_language,
                        'summary': clause_block.clause_summary,
                        'risk_triggers': clause_block.risk_triggers_identified,
                        'flow_down_obligations': clause_block.flow_down_obligations,
                        'redline_recommendations': [r.to_dict() for r in clause_block.redline_recommendations],
                        'harmful_language': clause_block.harmful_language_policy_conflicts,
                    },
                    'pass_number': pass_number,
                    'text_key': 'text',
                    'id_key': 'category'
                })
        
        # Extract supplemental operational risks
        if result.supplemental_operational_risks:
            for i, risk_block in enumerate(result.supplemental_operational_risks):
                findings.append({
                    'type': 'risk',
                    'data': {
                        'text': risk_block.clause_language,
                        'description': risk_block.clause_summary,
                        'risk_triggers': risk_block.risk_triggers_identified,
                    },
                    'pass_number': pass_number,
                    'text_key': 'description',
                    'id_key': 'text'
                })
        
        return findings
    
    def _extract_from_legacy_result(
        self,
        result,  # AnalysisResult
        pass_number: int
    ) -> List[Dict[str, Any]]:
        """
        Extract findings from legacy AnalysisResult.
        
        Args:
            result: AnalysisResult to extract from
            pass_number: Pass number for tracking
            
        Returns:
            List of finding dictionaries
        """
        findings = []
        
        # Extract clauses
        for clause in result.clauses:
            findings.append({
                'type': 'clause',
                'data': clause.to_dict(),
                'pass_number': pass_number,
                'text_key': 'text',
                'id_key': 'id'
            })
        
        # Extract risks
        for risk in result.risks:
            findings.append({
                'type': 'risk',
                'data': risk.to_dict(),
                'pass_number': pass_number,
                'text_key': 'description',
                'id_key': 'id'
            })
        
        # Extract compliance issues
        for issue in result.compliance_issues:
            findings.append({
                'type': 'compliance',
                'data': issue.to_dict(),
                'pass_number': pass_number,
                'text_key': 'issue',
                'id_key': 'id'
            })
        
        # Extract redlining suggestions
        for suggestion in result.redlining_suggestions:
            findings.append({
                'type': 'redlining',
                'data': suggestion.to_dict(),
                'pass_number': pass_number,
                'text_key': 'original_text',
                'id_key': 'clause_id'
            })
        
        return findings
    
    def _categorize_findings(
        self,
        pass_findings: List[List[Dict[str, Any]]],
        num_passes: int
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Conflict]]:
        """
        Categorize findings into consensus, flagged, and conflicts.
        
        Args:
            pass_findings: List of findings for each pass
            num_passes: Total number of passes
            
        Returns:
            Tuple of (consensus_findings, flagged_findings, conflicts)
        """
        # Build a unified list of all unique findings
        all_findings = []
        for pass_list in pass_findings:
            for finding in pass_list:
                all_findings.append(finding)
        
        # Group similar findings
        finding_groups = self._group_similar_findings(all_findings)
        
        consensus = []
        flagged = []
        conflicts = []
        
        for group in finding_groups:
            passes_in_group = set(f['pass_number'] for f in group)
            
            if len(passes_in_group) == num_passes:
                # Found in all passes - consensus
                # Check for content conflicts within the group
                content_conflict = self._check_content_conflict(group)
                if content_conflict:
                    conflicts.append(content_conflict)
                    flagged.append(self._merge_group(group, passes_in_group))
                else:
                    consensus.append(self._merge_group(group, passes_in_group))
            else:
                # Found in some but not all passes - flagged
                flagged.append(self._merge_group(group, passes_in_group))
        
        return consensus, flagged, conflicts
    
    def _group_similar_findings(
        self,
        findings: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """
        Group similar findings together based on text similarity.
        
        Args:
            findings: List of all findings
            
        Returns:
            List of groups, where each group contains similar findings
        """
        groups = []
        used = set()
        
        for i, finding in enumerate(findings):
            if i in used:
                continue
            
            group = [finding]
            used.add(i)
            
            finding_text = finding['data'].get(finding['text_key'], '')
            finding_type = finding['type']
            
            for j, other in enumerate(findings):
                if j in used or j == i:
                    continue
                
                # Must be same type
                if other['type'] != finding_type:
                    continue
                
                other_text = other['data'].get(other['text_key'], '')
                similarity = self._calculate_similarity(finding_text, other_text)
                
                if similarity >= self.similarity_threshold:
                    group.append(other)
                    used.add(j)
            
            groups.append(group)
        
        return groups
    
    def _merge_group(
        self,
        group: List[Dict[str, Any]],
        passes_in_group: Set[int]
    ) -> Dict[str, Any]:
        """
        Merge a group of similar findings into a single finding with metadata.
        
        Args:
            group: List of similar findings
            passes_in_group: Set of pass numbers containing this finding
            
        Returns:
            Merged finding dictionary
        """
        # Use the first finding as the base
        base = group[0]
        
        return {
            'type': base['type'],
            'data': base['data'],
            'passes_found_in': list(passes_in_group),
            'total_occurrences': len(group),
            'text_key': base['text_key']
        }
    
    def _check_content_conflict(
        self,
        group: List[Dict[str, Any]]
    ) -> Conflict:
        """
        Check if findings in a group have conflicting content.
        
        Args:
            group: List of similar findings
            
        Returns:
            Conflict object if conflict found, None otherwise
        """
        if len(group) < 2:
            return None
        
        # Check for risk level conflicts (for clauses and risks)
        risk_levels = set()
        for finding in group:
            risk_level = finding['data'].get('risk_level') or finding['data'].get('severity')
            if risk_level:
                risk_levels.add(risk_level)
        
        if len(risk_levels) > 1:
            # Create conflict for risk level disagreement
            pass_findings = {f['pass_number']: f['data'] for f in group}
            return Conflict(
                conflict_id=str(uuid.uuid4())[:8],
                conflict_type='risk_level',
                finding_type=group[0]['type'],
                pass_findings=pass_findings,
                description=f"Risk level disagreement: {', '.join(risk_levels)}"
            )
        
        return None
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity ratio between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity ratio between 0.0 and 1.0
        """
        if not text1 or not text2:
            return 0.0
        
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()
        
        if text1 == text2:
            return 1.0
        
        return SequenceMatcher(None, text1, text2).ratio()
    
    def find_consensus_findings(
        self,
        pass_results: List  # List of AnalysisResult or ComprehensiveAnalysisResult
    ) -> List[Dict[str, Any]]:
        """
        Identify findings that appear in all passes.
        
        Args:
            pass_results: List of AnalysisResult from each pass
            
        Returns:
            List of findings with consensus across all passes
        """
        comparison = self.compare_passes(pass_results)
        return comparison.consensus_findings
    
    def find_conflicts(
        self,
        pass_results: List  # List of AnalysisResult or ComprehensiveAnalysisResult
    ) -> List[Conflict]:
        """
        Identify conflicting findings between passes.
        
        Args:
            pass_results: List of AnalysisResult from each pass
            
        Returns:
            List of conflicts requiring resolution
        """
        comparison = self.compare_passes(pass_results)
        return comparison.conflicts
