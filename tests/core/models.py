"""
Core data models for the CR2A testing framework.
Defines test results, issues, and resolution tracking structures.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any


class TestStatus(Enum):
    """Test execution status enumeration."""
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"


class IssueType(Enum):
    """Issue classification types."""
    DEPENDENCY = "DEPENDENCY"
    CONFIGURATION = "CONFIGURATION"
    INTEGRATION = "INTEGRATION"
    PERMISSION = "PERMISSION"
    NETWORK = "NETWORK"


class Severity(Enum):
    """Issue severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class TestResult:
    """Individual test result with execution details."""
    test_name: str
    status: TestStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    execution_time: float = 0.0
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class ComponentTestReport:
    """Comprehensive report for component testing results."""
    lambda_function: str
    dependency_tests: List[TestResult]
    client_tests: List[TestResult]
    database_tests: List[TestResult]
    overall_status: TestStatus
    recommendations: List[str]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class IntegrationTestReport:
    """Comprehensive report for integration testing results."""
    state_machine_tests: List[TestResult]
    api_endpoint_tests: List[TestResult]
    workflow_tests: List[TestResult]
    permission_tests: List[TestResult]
    overall_status: TestStatus
    identified_issues: List['Issue']
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class Issue:
    """Identified issue with resolution guidance."""
    issue_type: IssueType
    severity: Severity
    component: str
    description: str
    suggested_fix: str
    resolution_steps: List[str]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class ResolutionResult:
    """Result of applying an automated fix."""
    issue: Issue
    resolution_applied: bool
    resolution_details: str
    verification_result: Optional[TestResult] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class TestSuite:
    """Collection of related tests with metadata."""
    name: str
    description: str
    tests: List[TestResult]
    overall_status: TestStatus
    execution_time: float
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
    
    def get_pass_rate(self) -> float:
        """Calculate the percentage of passing tests."""
        if not self.tests:
            return 0.0
        passed = sum(1 for test in self.tests if test.status == TestStatus.PASS)
        return (passed / len(self.tests)) * 100.0


@dataclass
class TestConfiguration:
    """Configuration for test execution."""
    aws_region: str = "us-east-1"
    lambda_timeout: int = 30
    max_retries: int = 3
    parallel_execution: bool = False
    verbose_logging: bool = True
    save_artifacts: bool = True
    artifact_path: str = "./test-artifacts"
    api_base_url: str = "https://api.example.com"