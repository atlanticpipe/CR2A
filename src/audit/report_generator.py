"""Report generation for the Security Audit System."""

import re
from typing import List, Set, Optional
from .models import Finding, ClassifiedIssues, Severity, IssueType
from .file_scanner import FileError


class ReportGenerator:
    """Generates markdown reports with remediation guidance."""
    
    def __init__(self):
        """Initialize the report generator."""
        pass
    
    def generate_audit_report(self, issues: ClassifiedIssues, errors: Optional[List[FileError]] = None) -> str:
        """Generate comprehensive audit report.
        
        Args:
            issues: Classified findings to report
            errors: Optional list of file errors encountered during scanning
            
        Returns:
            Markdown-formatted audit report
        """
        sections = []
        
        # Executive Summary
        sections.append(self._generate_executive_summary(issues, errors))
        sections.append("")
        
        # Findings by Category
        sections.append("## Findings by Category")
        sections.append("")
        
        # Group by type and severity
        for issue_type in IssueType:
            if issue_type in issues.by_type:
                type_findings = issues.by_type[issue_type]
                sections.append(self._generate_category_section(issue_type, type_findings))
                sections.append("")
        
        # External Service Mapping (if API calls exist)
        if IssueType.API_CALL in issues.by_type:
            sections.append(self._generate_service_mapping(issues.by_type[IssueType.API_CALL]))
            sections.append("")
        
        return "\n".join(sections)
    
    def generate_remediation_plan(self, issues: ClassifiedIssues) -> str:
        """Generate prioritized remediation plan.
        
        Args:
            issues: Classified findings to remediate
            
        Returns:
            Markdown-formatted remediation plan
        """
        sections = []
        
        sections.append("# Remediation Plan")
        sections.append("")
        sections.append("## Priority Actions")
        sections.append("")
        
        # Sort by severity (CRITICAL -> HIGH -> MEDIUM -> LOW)
        severity_order = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]
        
        priority_num = 1
        for severity in severity_order:
            if severity in issues.by_severity:
                findings = issues.by_severity[severity]
                
                # Group by file for this severity level
                by_file = {}
                for finding in findings:
                    if finding.file_path not in by_file:
                        by_file[finding.file_path] = []
                    by_file[finding.file_path].append(finding)
                
                # Generate remediation items
                for file_path, file_findings in by_file.items():
                    sections.append(f"{priority_num}. [{severity.value.upper()}] {file_path} ({len(file_findings)} issue{'s' if len(file_findings) > 1 else ''})")
                    sections.append("")
                    
                    for finding in file_findings:
                        sections.append(f"   - **Line {finding.line_number}**: {finding.issue_type.value}")
                        sections.append(f"     - **Issue**: {finding.matched_pattern}")
                        sections.append(f"     - **Code**: `{finding.code_snippet.strip()}`")
                        sections.append(f"     - **Recommendation**: {finding.recommendation}")
                        sections.append("")
                    
                    priority_num += 1
        
        return "\n".join(sections)
    
    def format_finding(self, finding: Finding) -> str:
        """Format individual finding with context.
        
        Args:
            finding: The finding to format
            
        Returns:
            Formatted markdown string for the finding
        """
        lines = []
        lines.append(f"- **File**: `{finding.file_path}:{finding.line_number}`")
        lines.append(f"  - **Severity**: {finding.severity.value.upper()}")
        lines.append(f"  - **Issue**: {finding.matched_pattern}")
        lines.append(f"  - **Code**: `{finding.code_snippet.strip()}`")
        lines.append(f"  - **Recommendation**: {finding.recommendation}")
        return "\n".join(lines)
    
    def _generate_executive_summary(self, issues: ClassifiedIssues, errors: Optional[List[FileError]] = None) -> str:
        """Generate executive summary section."""
        lines = []
        lines.append("# Security Audit Report")
        lines.append("")
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(f"- **Total issues found**: {issues.total_count}")
        
        # Error count if provided
        if errors:
            lines.append(f"- **Files with errors**: {len(errors)}")
        
        # Severity breakdown
        severity_counts = []
        for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]:
            count = issues.summary.get(severity.value, 0)
            severity_counts.append(f"{severity.value.capitalize()}: {count}")
        
        lines.append(f"- **By Severity**: {' | '.join(severity_counts)}")
        
        # Type breakdown
        type_counts = []
        type_map = {
            'secrets': 'Secrets',
            'hardcoded_paths': 'Hardcoded Paths',
            'config_variables': 'Config Variables',
            'api_calls': 'API Calls'
        }
        for key, label in type_map.items():
            count = issues.summary.get(key, 0)
            if count > 0:
                type_counts.append(f"{label}: {count}")
        
        if type_counts:
            lines.append(f"- **By Type**: {' | '.join(type_counts)}")
        
        return "\n".join(lines)
    
    def _generate_category_section(self, issue_type: IssueType, findings: List[Finding]) -> str:
        """Generate a section for a specific issue category."""
        lines = []
        
        # Section title
        type_titles = {
            IssueType.SECRET: "Hardcoded Secrets",
            IssueType.HARDCODED_PATH: "Hardcoded Paths",
            IssueType.CONFIG_VARIABLE: "Configuration Variables",
            IssueType.API_CALL: "API Calls"
        }
        
        title = type_titles.get(issue_type, issue_type.value)
        
        # Determine typical severity for this type
        if findings:
            typical_severity = findings[0].severity.value.upper()
            lines.append(f"### {title} ({typical_severity})")
        else:
            lines.append(f"### {title}")
        
        lines.append("")
        
        # List findings
        for finding in findings:
            lines.append(self.format_finding(finding))
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_service_mapping(self, api_findings: List[Finding]) -> str:
        """Generate external service dependency map."""
        lines = []
        lines.append("## External Service Dependencies")
        lines.append("")
        
        # Extract unique services from API call findings
        services = self._extract_services(api_findings)
        
        if services:
            lines.append("The following external services were detected:")
            lines.append("")
            for service in sorted(services):
                lines.append(f"- {service}")
        else:
            lines.append("No external services detected.")
        
        return "\n".join(lines)
    
    def _extract_services(self, api_findings: List[Finding]) -> Set[str]:
        """Extract unique service names/URLs from API call findings.
        
        Args:
            api_findings: List of API call findings
            
        Returns:
            Set of unique service identifiers
        """
        services = set()
        
        for finding in api_findings:
            # Try to extract URLs from code snippet
            url_pattern = r'https?://([^/\s"\'\)]+)'
            matches = re.findall(url_pattern, finding.code_snippet)
            services.update(matches)
            
            # Also check matched_pattern
            matches = re.findall(url_pattern, finding.matched_pattern)
            services.update(matches)
        
        return services
    
    def generate_error_log(self, errors: List[FileError]) -> str:
        """Generate detailed error log report.
        
        Args:
            errors: List of file errors encountered during scanning
            
        Returns:
            Markdown-formatted error log
        """
        if not errors:
            return "# Error Log\n\nNo errors encountered during scanning."
        
        lines = []
        lines.append("# Error Log")
        lines.append("")
        lines.append(f"**Total errors**: {len(errors)}")
        lines.append("")
        
        # Group errors by type
        errors_by_type = {}
        for error in errors:
            if error.error_type not in errors_by_type:
                errors_by_type[error.error_type] = []
            errors_by_type[error.error_type].append(error)
        
        # Generate sections for each error type
        for error_type, error_list in sorted(errors_by_type.items()):
            lines.append(f"## {error_type.capitalize()} Errors ({len(error_list)})")
            lines.append("")
            
            for error in error_list:
                lines.append(f"- **File**: `{error.file_path}`")
                lines.append(f"  - **Message**: {error.message}")
                lines.append("")
        
        return "\n".join(lines)
