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

from src.analysis_models import AnalysisResult, Clause, Risk, ComplianceIssue, RedliningSuggestion
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
        pass_results: List[AnalysisResult]
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
        result: AnalysisResult,
        pass_number: int
    ) -> List[Dict[str, Any]]:
        """
        Extract all findings from an AnalysisResult into a flat list.
        
        Args:
            result: AnalysisResult to extract from
            pass_number: Pass number for tracking
            
        Returns:
            List of finding dictionaries with type and pass info
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
        pass_results: List[AnalysisResult]
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
        pass_results: List[AnalysisResult]
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
