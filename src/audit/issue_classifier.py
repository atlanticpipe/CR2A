"""Issue classification and prioritization for the Security Audit System."""

from typing import List, Dict
from collections import defaultdict

from .models import Finding, ClassifiedIssues, Severity, IssueType


class IssueClassifier:
    """Categorizes and prioritizes detected security and configuration issues."""
    
    def classify(self, findings: List[Finding]) -> ClassifiedIssues:
        """Categorize findings by type, severity, and file.
        
        Args:
            findings: List of detected findings
            
        Returns:
            ClassifiedIssues with findings organized by multiple dimensions
        """
        by_severity = self._group_by_severity(findings)
        by_type = self._group_by_type(findings)
        by_file = self._group_by_file(findings)
        total_count = len(findings)
        summary = self._generate_summary(findings)
        
        return ClassifiedIssues(
            by_severity=by_severity,
            by_type=by_type,
            by_file=by_file,
            total_count=total_count,
            summary=summary
        )
    
    def calculate_severity(self, finding: Finding) -> Severity:
        """Determine severity level based on issue type and context.
        
        Args:
            finding: The finding to evaluate
            
        Returns:
            Severity level (CRITICAL, HIGH, MEDIUM, or LOW)
        """
        # Secrets are CRITICAL or HIGH priority
        if finding.issue_type == IssueType.SECRET:
            # Check for particularly sensitive patterns
            sensitive_keywords = ['private_key', 'certificate', 'password', 'passwd', 'pwd']
            if any(keyword in finding.matched_pattern.lower() for keyword in sensitive_keywords):
                return Severity.CRITICAL
            return Severity.HIGH
        
        # Hardcoded paths are MEDIUM priority
        elif finding.issue_type == IssueType.HARDCODED_PATH:
            return Severity.MEDIUM
        
        # Config variables are MEDIUM priority
        elif finding.issue_type == IssueType.CONFIG_VARIABLE:
            return Severity.MEDIUM
        
        # API calls are LOW priority
        elif finding.issue_type == IssueType.API_CALL:
            return Severity.LOW
        
        # Default to MEDIUM if unknown
        return Severity.MEDIUM
    
    def _group_by_severity(self, findings: List[Finding]) -> Dict[Severity, List[Finding]]:
        """Group findings by severity level."""
        grouped: Dict[Severity, List[Finding]] = defaultdict(list)
        for finding in findings:
            grouped[finding.severity].append(finding)
        return dict(grouped)
    
    def _group_by_type(self, findings: List[Finding]) -> Dict[IssueType, List[Finding]]:
        """Group findings by issue type."""
        grouped: Dict[IssueType, List[Finding]] = defaultdict(list)
        for finding in findings:
            grouped[finding.issue_type].append(finding)
        return dict(grouped)
    
    def _group_by_file(self, findings: List[Finding]) -> Dict[str, List[Finding]]:
        """Group findings by source file path."""
        grouped: Dict[str, List[Finding]] = defaultdict(list)
        for finding in findings:
            grouped[finding.file_path].append(finding)
        return dict(grouped)
    
    def _generate_summary(self, findings: List[Finding]) -> Dict[str, int]:
        """Generate summary statistics by category."""
        summary = {
            'total': len(findings),
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'secrets': 0,
            'hardcoded_paths': 0,
            'config_variables': 0,
            'api_calls': 0
        }
        
        for finding in findings:
            # Count by severity
            summary[finding.severity.value] += 1
            
            # Count by type
            if finding.issue_type == IssueType.SECRET:
                summary['secrets'] += 1
            elif finding.issue_type == IssueType.HARDCODED_PATH:
                summary['hardcoded_paths'] += 1
            elif finding.issue_type == IssueType.CONFIG_VARIABLE:
                summary['config_variables'] += 1
            elif finding.issue_type == IssueType.API_CALL:
                summary['api_calls'] += 1
        
        return summary
