"""
Core interfaces for the CR2A testing framework.
Defines abstract base classes and protocols for testing components.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from .models import TestResult, TestSuite, Issue, ResolutionResult, TestConfiguration


class ComponentTester(ABC):
    """Abstract base class for component testing."""
    
    @abstractmethod
    def test_dependencies(self) -> TestResult:
        """Test Lambda layer dependencies and package imports."""
        pass
    
    @abstractmethod
    def test_openai_client(self) -> TestResult:
        """Test OpenAI client initialization and connectivity."""
        pass
    
    @abstractmethod
    def test_dynamodb_operations(self) -> TestResult:
        """Test DynamoDB operations and reserved keyword handling."""
        pass
    
    @abstractmethod
    def generate_test_report(self) -> 'ComponentTestReport':
        """Generate comprehensive component test report."""
        pass


class IntegrationTester(ABC):
    """Abstract base class for integration testing."""
    
    @abstractmethod
    def test_state_machine_exists(self) -> TestResult:
        """Test Step Functions state machine existence and accessibility."""
        pass
    
    @abstractmethod
    def test_execution_permissions(self) -> TestResult:
        """Test IAM permissions for Step Functions execution."""
        pass
    
    @abstractmethod
    def test_api_endpoints(self) -> TestResult:
        """Test API Gateway endpoint functionality."""
        pass
    
    @abstractmethod
    def run_manual_execution(self, test_input: Dict[str, Any]) -> TestResult:
        """Run manual Step Functions execution with test input."""
        pass
    
    @abstractmethod
    def generate_test_report(self) -> 'IntegrationTestReport':
        """Generate comprehensive integration test report."""
        pass


class IssueResolver(ABC):
    """Abstract base class for automated issue resolution."""
    
    @abstractmethod
    def resolve_dependency_issues(self, issues: List[Issue]) -> List[ResolutionResult]:
        """Resolve dependency-related issues."""
        pass
    
    @abstractmethod
    def resolve_configuration_issues(self, issues: List[Issue]) -> List[ResolutionResult]:
        """Resolve configuration-related issues."""
        pass
    
    @abstractmethod
    def resolve_integration_issues(self, issues: List[Issue]) -> List[ResolutionResult]:
        """Resolve integration-related issues."""
        pass
    
    @abstractmethod
    def validate_resolution(self, resolution: ResolutionResult) -> TestResult:
        """Validate that a resolution actually fixed the issue."""
        pass


class TestOrchestrator(ABC):
    """Abstract base class for test orchestration and automation."""
    
    @abstractmethod
    def run_component_tests(self, config: TestConfiguration) -> TestSuite:
        """Execute all component tests."""
        pass
    
    @abstractmethod
    def run_integration_tests(self, config: TestConfiguration) -> TestSuite:
        """Execute all integration tests."""
        pass
    
    @abstractmethod
    def run_full_test_suite(self, config: TestConfiguration) -> List[TestSuite]:
        """Execute complete test suite with all phases."""
        pass
    
    @abstractmethod
    def generate_summary_report(self, test_suites: List[TestSuite]) -> Dict[str, Any]:
        """Generate summary report across all test suites."""
        pass


class TestReporter(ABC):
    """Abstract base class for test reporting."""
    
    @abstractmethod
    def generate_html_report(self, test_suites: List[TestSuite], output_path: str) -> str:
        """Generate HTML test report."""
        pass
    
    @abstractmethod
    def generate_json_report(self, test_suites: List[TestSuite], output_path: str) -> str:
        """Generate JSON test report."""
        pass
    
    @abstractmethod
    def generate_console_summary(self, test_suites: List[TestSuite]) -> str:
        """Generate console-friendly test summary."""
        pass


class AWSResourceValidator(ABC):
    """Abstract base class for AWS resource validation."""
    
    @abstractmethod
    def validate_lambda_function(self, function_name: str) -> TestResult:
        """Validate Lambda function exists and is accessible."""
        pass
    
    @abstractmethod
    def validate_step_function(self, state_machine_arn: str) -> TestResult:
        """Validate Step Functions state machine."""
        pass
    
    @abstractmethod
    def validate_api_gateway(self, api_id: str) -> TestResult:
        """Validate API Gateway configuration."""
        pass
    
    @abstractmethod
    def validate_dynamodb_table(self, table_name: str) -> TestResult:
        """Validate DynamoDB table configuration."""
        pass
    
    @abstractmethod
    def validate_iam_permissions(self, role_arn: str, required_actions: List[str]) -> TestResult:
        """Validate IAM role has required permissions."""
        pass