"""
Main integration tester that orchestrates all integration testing components.
Implements the IntegrationTester interface and coordinates testing workflow.
"""

from typing import Dict, Any, List
from ..core.base import BaseTestFramework
from ..core.models import TestResult, TestStatus, TestConfiguration, IntegrationTestReport, Issue, IssueType, Severity
from ..core.interfaces import IntegrationTester

from .step_functions_tester import StepFunctionsTester
from .iam_permission_tester import IAMPermissionTester
from .api_gateway_tester import APIGatewayTester


class CR2AIntegrationTester(IntegrationTester, BaseTestFramework):
    """Main integration tester for CR2A system components."""
    
    def __init__(self, config: TestConfiguration, api_base_url: str = None):
        super().__init__(config)
        
        # Initialize component testers
        self.step_functions_tester = StepFunctionsTester(config)
        self.iam_tester = IAMPermissionTester(config)
        
        if api_base_url:
            self.api_tester = APIGatewayTester(config, api_base_url)
        else:
            self.api_tester = None
            self.logger.warning("API base URL not provided - API tests will be skipped")
    
    def test_state_machine_exists(self) -> TestResult:
        """Test Step Functions state machine existence and accessibility."""
        return self.step_functions_tester.test_state_machine_exists()
    
    def test_state_machine_definition(self) -> TestResult:
        """Test state machine definition validity and Lambda function references."""
        return self.step_functions_tester.test_state_machine_definition()
    
    def test_execution_permissions(self) -> TestResult:
        """Test IAM permissions for Step Functions execution."""
        return self.iam_tester.test_execution_permissions()
    
    def test_api_endpoints(self) -> TestResult:
        """Test API Gateway endpoint functionality."""
        if not self.api_tester:
            return TestResult(
                test_name="test_api_endpoints",
                status=TestStatus.SKIP,
                message="API tester not configured - API base URL required"
            )
        
        # Run comprehensive API tests and aggregate results
        api_results = self.api_tester.run_comprehensive_endpoint_tests()
        
        # Aggregate results into a single test result
        failed_tests = [r for r in api_results if r.status == TestStatus.FAIL]
        error_tests = [r for r in api_results if r.status == TestStatus.ERROR]
        
        if error_tests:
            status = TestStatus.ERROR
            message = f"API endpoint tests had errors: {', '.join([r.test_name for r in error_tests])}"
        elif failed_tests:
            status = TestStatus.FAIL
            message = f"API endpoint tests failed: {', '.join([r.test_name for r in failed_tests])}"
        else:
            status = TestStatus.PASS
            message = "All API endpoint tests passed successfully"
        
        return TestResult(
            test_name="test_api_endpoints",
            status=status,
            message=message,
            details={
                "individual_results": [
                    {
                        "test_name": r.test_name,
                        "status": r.status.value,
                        "message": r.message,
                        "execution_time": r.execution_time
                    }
                    for r in api_results
                ],
                "summary": self.api_tester.get_endpoint_health_summary()
            }
        )
    
    def run_manual_execution(self, test_input: Dict[str, Any]) -> TestResult:
        """Run manual Step Functions execution with test input."""
        return self.step_functions_tester.run_manual_execution(test_input)
    
    def test_cors_configuration(self) -> TestResult:
        """Test CORS configuration for API endpoints."""
        if not self.api_tester:
            return TestResult(
                test_name="test_cors_configuration",
                status=TestStatus.SKIP,
                message="API tester not configured - API base URL required"
            )
        
        return self.api_tester.test_cors_configuration()
    
    def run_comprehensive_integration_tests(self) -> List[TestResult]:
        """Run all integration tests in the proper sequence."""
        test_results = []
        
        self.logger.info("Starting comprehensive integration tests...")
        
        # Phase 1: Infrastructure validation
        self.logger.info("Phase 1: Testing infrastructure components...")
        test_results.append(self.test_state_machine_exists())
        test_results.append(self.test_state_machine_definition())
        test_results.append(self.test_execution_permissions())
        
        # Phase 2: API endpoint testing
        if self.api_tester:
            self.logger.info("Phase 2: Testing API endpoints...")
            test_results.append(self.test_api_endpoints())
            test_results.append(self.test_cors_configuration())
        else:
            self.logger.warning("Phase 2: Skipping API tests - no API base URL configured")
        
        # Phase 3: End-to-end workflow testing
        self.logger.info("Phase 3: Testing end-to-end workflows...")
        sample_inputs = self.step_functions_tester.get_test_input_samples()
        for i, test_input in enumerate(sample_inputs[:2]):  # Test first 2 samples
            workflow_result = self.run_manual_execution(test_input)
            workflow_result.test_name = f"workflow_test_{i+1}"
            test_results.append(workflow_result)
        
        self.logger.info(f"Integration tests completed. Total tests: {len(test_results)}")
        return test_results
    
    def generate_test_report(self) -> IntegrationTestReport:
        """Generate comprehensive integration test report."""
        test_results = self.run_comprehensive_integration_tests()
        
        # Categorize results
        state_machine_tests = [r for r in test_results if "state_machine" in r.test_name or "workflow" in r.test_name]
        api_endpoint_tests = [r for r in test_results if "api" in r.test_name or "cors" in r.test_name]
        workflow_tests = [r for r in test_results if "workflow" in r.test_name or "execution" in r.test_name]
        permission_tests = [r for r in test_results if "permission" in r.test_name]
        
        # Determine overall status
        failed_tests = [r for r in test_results if r.status == TestStatus.FAIL]
        error_tests = [r for r in test_results if r.status == TestStatus.ERROR]
        
        if error_tests:
            overall_status = TestStatus.ERROR
        elif failed_tests:
            overall_status = TestStatus.FAIL
        else:
            overall_status = TestStatus.PASS
        
        # Identify issues from failed tests
        identified_issues = self._identify_issues_from_results(test_results)
        
        return IntegrationTestReport(
            state_machine_tests=state_machine_tests,
            api_endpoint_tests=api_endpoint_tests,
            workflow_tests=workflow_tests,
            permission_tests=permission_tests,
            overall_status=overall_status,
            identified_issues=identified_issues
        )
    
    def _identify_issues_from_results(self, test_results: List[TestResult]) -> List[Issue]:
        """Identify issues from test results and categorize them."""
        issues = []
        
        for result in test_results:
            if result.status in [TestStatus.FAIL, TestStatus.ERROR]:
                issue_type = self._categorize_issue(result.test_name)
                severity = Severity.HIGH if result.status == TestStatus.ERROR else Severity.MEDIUM
                
                issue = Issue(
                    issue_type=issue_type,
                    severity=severity,
                    component=self._extract_component_from_test_name(result.test_name),
                    description=result.message,
                    suggested_fix=self._suggest_fix_for_test(result.test_name, result.message),
                    resolution_steps=self._generate_resolution_steps(result.test_name, result.message)
                )
                issues.append(issue)
        
        return issues
    
    def _categorize_issue(self, test_name: str) -> IssueType:
        """Categorize issue type based on test name."""
        if "permission" in test_name or "iam" in test_name:
            return IssueType.PERMISSION
        elif "state_machine" in test_name or "workflow" in test_name:
            return IssueType.INTEGRATION
        elif "api" in test_name or "cors" in test_name:
            return IssueType.CONFIGURATION
        else:
            return IssueType.INTEGRATION
    
    def _extract_component_from_test_name(self, test_name: str) -> str:
        """Extract component name from test name."""
        if "state_machine" in test_name:
            return "Step Functions"
        elif "api" in test_name:
            return "API Gateway"
        elif "permission" in test_name or "iam" in test_name:
            return "IAM"
        elif "workflow" in test_name:
            return "Workflow"
        else:
            return "Unknown"
    
    def _suggest_fix_for_test(self, test_name: str, message: str) -> str:
        """Suggest a fix based on test name and error message."""
        if "state_machine" in test_name and "not found" in message.lower():
            return "Deploy the cr2a-contract-analysis Step Functions state machine"
        elif "permission" in test_name and "missing" in message.lower():
            return "Update IAM role policies to include required permissions"
        elif "api" in test_name and "cors" in test_name:
            return "Configure CORS settings in API Gateway"
        elif "lambda" in message.lower() and "not found" in message.lower():
            return "Deploy missing Lambda functions referenced in state machine"
        else:
            return "Review logs and configuration for the affected component"
    
    def _generate_resolution_steps(self, test_name: str, message: str) -> List[str]:
        """Generate resolution steps based on test failure."""
        if "state_machine" in test_name and "not found" in message.lower():
            return [
                "Check if Step Functions state machine is deployed",
                "Verify state machine name matches expected value",
                "Check AWS region configuration",
                "Verify AWS credentials have Step Functions access"
            ]
        elif "permission" in test_name:
            return [
                "Review IAM role policies",
                "Add missing permissions to role",
                "Verify role trust relationships",
                "Test permissions with AWS CLI or console"
            ]
        elif "api" in test_name:
            return [
                "Check API Gateway deployment status",
                "Verify endpoint configurations",
                "Test endpoints manually",
                "Check Lambda function integrations"
            ]
        else:
            return [
                "Review test logs for specific error details",
                "Check AWS resource configurations",
                "Verify network connectivity",
                "Contact system administrator if needed"
            ]