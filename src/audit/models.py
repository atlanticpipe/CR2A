"""Core data models for the Security Audit System."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List


class IssueType(Enum):
    """Categories of security and configuration issues."""
    HARDCODED_PATH = "hardcoded_path"
    SECRET = "secret"
    CONFIG_VARIABLE = "config_variable"
    API_CALL = "api_call"


class Severity(Enum):
    """Severity levels for detected issues."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Finding:
    """Represents a single detected security or configuration issue.
    
    Attributes:
        file_path: Relative path from project root
        line_number: Line where issue was found
        column: Column position
        issue_type: Category of issue
        severity: Critical, High, Medium, Low
        code_snippet: Surrounding code context
        matched_pattern: What pattern matched
        recommendation: How to fix
    """
    file_path: str
    line_number: int
    column: int
    issue_type: IssueType
    severity: Severity
    code_snippet: str
    matched_pattern: str
    recommendation: str


@dataclass
class ClassifiedIssues:
    """Organized collection of findings.
    
    Attributes:
        by_severity: Findings grouped by severity level
        by_type: Findings grouped by issue type
        by_file: Findings grouped by source file
        total_count: Total number of findings
        summary: Counts by category
    """
    by_severity: Dict[Severity, List[Finding]]
    by_type: Dict[IssueType, List[Finding]]
    by_file: Dict[str, List[Finding]]
    total_count: int
    summary: Dict[str, int]
