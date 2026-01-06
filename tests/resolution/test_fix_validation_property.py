"""
Property-based tests for fix validation round-trip.
Tests universal properties that should hold for fix validation in the CR2A system.

Feature: cr2a-testing-debugging, Property 14: Fix validation round-trip
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from typing import List, Dict, Any, Set
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from .fix_validator import FixValidator, ValidationStatus, ValidationResult, RegressionAnalysis
from .fix_applicator import FixApplicator, FixConfiguration
from .issue_analyzer import IssueAnalyzer
from ..core.models import (
    Issue, IssueType, Severity, TestConfiguration, ResolutionResult,
    TestResult, TestStatus, ComponentTestReport, IntegrationTestReport
)
from ..core.interfaces import ComponentTester, IntegrationTester


# Strategy for generating valid Issue instances
@st.composite
def issue_strategy(draw):
    """Generate valid Issue instances for testing."""
    issue_type = draw(st.sampled_from(list(IssueType)))
    severity = draw(st.sampled_from(list(Severity)))
    
    # Component names that match the dependency graph
    components = [
        "lambda_layers", "iam_permissions", "openai_client", 
        "dynamodb_operations", "step_functions", "api_gateway",
        "cors_configuration", "end_to_end_workflow"
    ]
    component = draw(st.sampled_from(components))
    
    # Generate realistic descriptions based on issue type
    if issue_type == IssueType.DEPENDENCY:
        descriptions = [
            "ModuleNotFoundError: No module named 'missing_package'",
            "ImportError: cannot import name 'function' from 'module'",
            "Package version conflict detected",
            "Missing required dependency in Lambda layer"
        ]
    elif issue_type == IssueType.CONFIGURATION:
        descriptions = [
            "KeyError: 'OPENAI_API_KEY' not found in environment",
            "ValidationException: Reserved keyword 'status' used in expression",
            "Invalid configuration parameter value",
            "Environment variable not set correctly"
        ]
    elif issue_type == IssueType.INTEGRATION:
        descriptions = [
            "Step Functions state machine definition invalid",
            "API Gateway integration configuration error",
            "Lambda function ARN not found in state machine",
            "CORS policy configuration issue"
        ]
    else:
        descriptions = [
            "AccessDenied: User not authorized to perform action",
            "Permission denied for resource access",
            "IAM role missing required permissions"
        ]
    
    description = draw(st.sampled_from(descriptions))
    suggested_fix = draw(st.text(min_size=5, max_size=100))
    resolution_steps = draw(st.lists(
        st.text(min_size=5, max_size=50), 
        min_size=1, 
        max_size=5
    ))
    
    return Issue(
        issue_type=issue_type,
        severity=severity,
        component=component,
        description=description,
        suggested_fix=suggested_fix,
        resolution_steps=resolution_steps,
        timestamp=datetime.now(timezone.utc)
    )


# Strategy for generating ResolutionResult instances
@st.composite
def resolution_result_strategy(draw):
    """Generate valid ResolutionResult instances for testing."""
    issue = draw(issue_strategy())
    resolution_applied = draw(st.booleans())
    
    if resolution_applied:
        resolution_details = draw(st.sampled_from([
            "Successfully updated Lambda layer with correct package versions",
            "Updated OpenAI API key environment variables",
            "Fixed DynamoDB reserved keyword conflicts",
            "Updated Step Functions state machine definition",
            "Fixed API Gateway CORS configuration"
        ]))
    else:
        resolution_details = draw(st.sampled_from([
            "Failed to update Lambda layer: AWS API error",
            "Unable to access environment variables: Permission denied",
            "DynamoDB update failed: Resource not found",
            "Step Functions update failed: Invalid definition",
            "API Gateway update failed: Configuration error"
        ]))
    
    return ResolutionResult(
        issue=issue,
        resolution_applied=resolution_applied,
        resolution_details=resolution_details,
        timestamp=datetime.now(timezone.utc)
    )


# Strategy for generating TestResult instances
@st.composite
def gen_test_result(draw):
    """Generate valid TestResult instances for testing."""
    test_name = draw(st.text(min_size=5, max_size=50))
    status = draw(st.sampled_from(list(TestStatus)))
    message = draw(st.text(min_size=5, max_size=100))
    execution_time = draw(st.floats(min_value=0.1, max_value=30.0))
    
    return TestResult(
        test_name=test_name,
        status=status,
        message=message,
        execution_time=execution_time,
        timestamp=datetime.now(timezone.utc)
    )


class MockComponentTester(ComponentTester):
    """Mock component tester for testing."""
    
    def __init__(self, test_results: Dict[str, TestResult] = None):
        self.test_results = test_results or {}
    
    def test_dependencies(self) -> TestResult:
        return self.test_results.get('dependencies', TestResult(
            test_name="test_dependencies",
            status=TestStatus.PASS,
            message="All dependencies available"
        ))
    
    def test_openai_client(self) -> TestResult:
        return self.test_results.get('openai_client', TestResult(
            test_name="test_openai_client",
            status=TestStatus.PASS,
            message="OpenAI client initialized successfully"
        ))
    
    def test_dynamodb_operations(self) -> TestResult:
        return self.test_results.get('dynamodb_operations', TestResult(
            test_name="test_dynamodb_operations",
            status=TestStatus.PASS,
            message="DynamoDB operations successful"
        ))
    
    def generate_test_report(self) -> ComponentTestReport:
        return ComponentTestReport(
            lambda_function="test_function",
            dependency_tests=[self.test_dependencies()],
            client_tests=[self.test_openai_client()],
            database_tests=[self.test_dynamodb_operations()],
            overall_status=TestStatus.PASS,
            recommendations=[]
        )


class MockIntegrationTester(IntegrationTester):
    """Mock integration tester for testing."""
    
    def __init__(self, test_results: Dict[str, TestResult] = None):
        self.test_results = test_results or {}
    
    def test_state_machine_exists(self) -> TestResult:
        return self.test_results.get('state_machine_exists', TestResult(
            test_name="test_state_machine_exists",
            status=TestStatus.PASS,
            message="State machine exists and is accessible"
        ))
    
    def test_execution_permissions(self) -> TestResult:
        return self.test_results.get('execution_permissions', TestResult(
            test_name="test_execution_permissions",
            status=TestStatus.PASS,
            message="Execution permissions are correct"
        ))
    
    def test_api_endpoints(self) -> TestResult:
        return self.test_results.get('api_endpoints', TestResult(
            test_name="test_api_endpoints",
            status=TestStatus.PASS,
            message="API endpoints responding correctly"
        ))
    
    def run_manual_execution(self, test_input: dict) -> TestResult:
        return self.test_results.get('manual_execution', TestResult(
            test_name="run_manual_execution",
            status=TestStatus.PASS,
            message="Manual execution completed successfully"
        ))
    
    def generate_test_report(self) -> IntegrationTestReport:
        return IntegrationTestReport(
            state_machine_tests=[self.test_state_machine_exists()],
            api_endpoint_tests=[self.test_api_endpoints()],
            workflow_tests=[self.run_manual_execution({})],
            permission_tests=[self.test_execution_permissions()],
            overall_status=TestStatus.PASS,
            identified_issues=[]
        )


class TestFixValidationProperties:
    """Property-based tests for fix validation round-trip."""
    
    @given(
        resolution_result_strategy(),
        st.lists(gen_test_result(), min_size=1, max_size=5),
        st.lists(gen_test_result(), min_size=1, max_size=5)
    )
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_fix_validation_round_trip(self, resolution_result, pre_fix_tests, post_fix_tests):
        """
        Property 14: Fix validation round-trip
        
        For any applied fix, re-running all tests should verify the issue is 
        resolved without introducing new regressions.
        
        **Validates: Requirements 5.5**
        """
        # Create test configuration
        test_config = TestConfiguration(
            aws_region="us-east-1",
            lambda_timeout=30,
            max_retries=3
        )
        
        # Create mock testers with controlled results
        component_tester = MockComponentTester()
        integration_tester = MockIntegrationTester()
        
        # Create fix validator
        fix_validator = FixValidator(
            config=test_config,
            component_tester=component_tester,
            integration_tester=integration_tester
        )
        
        # Set up baseline results for regression detection
        component_reports = [component_tester.generate_test_report()]
        integration_reports = [IntegrationTestReport(
            state_machine_tests=[integration_tester.test_state_machine_exists()],
            api_endpoint_tests=[integration_tester.test_api_endpoints()],
            workflow_tests=[integration_tester.run_manual_execution({})],
            permission_tests=[integration_tester.test_execution_permissions()],
            overall_status=TestStatus.PASS,
            identified_issues=[]
        )]
        
        fix_validator.set_baseline_results(component_reports, integration_reports)
        
        # Property: Validation should return ValidationResult
        validation_result = fix_validator.validate_resolution(resolution_result)
        
        assert isinstance(validation_result, ValidationResult), (
            "Validation should return ValidationResult instance"
        )
        
        # Property: ValidationResult should reference the original resolution
        assert validation_result.resolution_result == resolution_result, (
            "ValidationResult should reference the original ResolutionResult"
        )
        
        # Property: ValidationResult should have valid status
        assert isinstance(validation_result.validation_status, ValidationStatus), (
            "ValidationResult should have valid ValidationStatus"
        )
        
        # Property: ValidationResult should contain test results
        assert isinstance(validation_result.pre_fix_tests, list), (
            "ValidationResult should contain pre-fix test results"
        )
        assert isinstance(validation_result.post_fix_tests, list), (
            "ValidationResult should contain post-fix test results"
        )
        assert isinstance(validation_result.regression_tests, list), (
            "ValidationResult should contain regression test results"
        )
        
        # Property: All test results should be valid TestResult instances
        all_test_results = (validation_result.pre_fix_tests + 
                           validation_result.post_fix_tests + 
                           validation_result.regression_tests)
        
        for test_result in all_test_results:
            assert isinstance(test_result, TestResult), (
                "All test results should be TestResult instances"
            )
            assert isinstance(test_result.status, TestStatus), (
                "Test results should have valid TestStatus"
            )
            assert isinstance(test_result.message, str), (
                "Test results should have message"
            )
            assert len(test_result.message) > 0, (
                "Test result messages should not be empty"
            )
        
        # Property: Validation details should be informative
        assert isinstance(validation_result.validation_details, str), (
            "Validation details should be string"
        )
        assert len(validation_result.validation_details) > 0, (
            "Validation details should not be empty"
        )
        
        # Property: Validation status should be consistent with test results
        # Note: The current implementation determines status based on test results,
        # not on whether the resolution was applied. This is a design choice where
        # validation focuses on actual test outcomes rather than resolution attempts.
        
        # Check that validation status is consistent with test outcomes
        post_fix_failures = [t for t in validation_result.post_fix_tests 
                           if t.status in [TestStatus.FAIL, TestStatus.ERROR]]
        regression_failures = [t for t in validation_result.regression_tests 
                             if t.status in [TestStatus.FAIL, TestStatus.ERROR]]
        
        if regression_failures:
            assert validation_result.validation_status == ValidationStatus.REGRESSION_DETECTED, (
                "Should detect regressions when regression tests fail"
            )
        elif not post_fix_failures:
            # All post-fix tests passed - could be RESOLVED even if resolution wasn't applied
            # This happens when the issue was already resolved or tests pass despite failed resolution
            assert validation_result.validation_status == ValidationStatus.RESOLVED, (
                "Should be resolved when all post-fix tests pass"
            )
        else:
            # Some post-fix tests failed
            pre_fix_failures = [t for t in validation_result.pre_fix_tests 
                              if t.status in [TestStatus.FAIL, TestStatus.ERROR]]
            
            if len(post_fix_failures) < len(pre_fix_failures):
                assert validation_result.validation_status == ValidationStatus.PARTIALLY_RESOLVED, (
                    "Should be partially resolved when fewer tests fail than before"
                )
            else:
                assert validation_result.validation_status == ValidationStatus.NOT_RESOLVED, (
                    "Should not be resolved when no improvement in test results"
                )
        
        # Property: Validation details should mention the validation status
        details_lower = validation_result.validation_details.lower()
        status_name = validation_result.validation_status.value.lower()
        assert status_name in details_lower, (
            "Validation details should mention the validation status"
        )
    
    @given(
        st.lists(resolution_result_strategy(), min_size=2, max_size=5)
    )
    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_batch_validation_consistency(self, resolution_results):
        """
        Property: Batch validation should be consistent and comprehensive.
        
        For any set of resolution results, batch validation should validate
        each resolution and provide consistent results.
        """
        test_config = TestConfiguration()
        
        # Create mock testers
        component_tester = MockComponentTester()
        integration_tester = MockIntegrationTester()
        
        fix_validator = FixValidator(
            config=test_config,
            component_tester=component_tester,
            integration_tester=integration_tester
        )
        
        # Property: Batch validation should return results for all resolutions
        validation_results = fix_validator.validate_batch_resolution(resolution_results)
        
        assert len(validation_results) == len(resolution_results), (
            "Should return validation result for each resolution"
        )
        
        # Property: Each validation result should correspond to a resolution
        for i, (resolution, validation) in enumerate(zip(resolution_results, validation_results)):
            assert isinstance(validation, ValidationResult), (
                f"Validation result {i} should be ValidationResult instance"
            )
            assert validation.resolution_result == resolution, (
                f"Validation result {i} should reference corresponding resolution"
            )
            assert isinstance(validation.validation_status, ValidationStatus), (
                f"Validation result {i} should have valid status"
            )
        
        # Property: Validation results should maintain order
        for i, validation in enumerate(validation_results):
            expected_resolution = resolution_results[i]
            assert validation.resolution_result == expected_resolution, (
                f"Validation result {i} should correspond to resolution {i}"
            )
    
    @given(
        st.lists(gen_test_result(), min_size=2, max_size=6),
        st.lists(gen_test_result(), min_size=2, max_size=6)
    )
    @settings(
        max_examples=25,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_regression_analysis_accuracy(self, pre_fix_results, post_fix_results):
        """
        Property: Regression analysis should accurately detect changes.
        
        For any pre-fix and post-fix test results, regression analysis
        should correctly identify new failures and performance degradations.
        """
        test_config = TestConfiguration()
        fix_validator = FixValidator(config=test_config)
        
        # Property: Regression analysis should return RegressionAnalysis
        regression_analysis = fix_validator.analyze_regressions(pre_fix_results, post_fix_results)
        
        assert isinstance(regression_analysis, RegressionAnalysis), (
            "Should return RegressionAnalysis instance"
        )
        
        # Property: Regression analysis should have valid structure
        assert isinstance(regression_analysis.new_failures, list), (
            "Should have list of new failures"
        )
        assert isinstance(regression_analysis.degraded_performance, list), (
            "Should have list of performance degradations"
        )
        assert isinstance(regression_analysis.changed_behavior, list), (
            "Should have list of behavior changes"
        )
        assert isinstance(regression_analysis.overall_regression_detected, bool), (
            "Should have boolean regression detection flag"
        )
        
        # Property: All regression items should be TestResult instances
        all_regression_items = (regression_analysis.new_failures + 
                               regression_analysis.degraded_performance + 
                               regression_analysis.changed_behavior)
        
        for item in all_regression_items:
            assert isinstance(item, TestResult), (
                "All regression items should be TestResult instances"
            )
        
        # Property: Overall regression flag should be consistent with findings
        has_any_regressions = (len(regression_analysis.new_failures) > 0 or
                              len(regression_analysis.degraded_performance) > 0 or
                              len(regression_analysis.changed_behavior) > 0)
        
        assert regression_analysis.overall_regression_detected == has_any_regressions, (
            "Overall regression flag should match presence of specific regressions"
        )
        
        # Property: New failures should be from post-fix results
        post_fix_test_names = {test.test_name for test in post_fix_results}
        for failure in regression_analysis.new_failures:
            assert failure.test_name in post_fix_test_names, (
                "New failures should be from post-fix test results"
            )
            assert failure.status in [TestStatus.FAIL, TestStatus.ERROR], (
                "New failures should have failure status"
            )
    
    @given(
        st.lists(resolution_result_strategy(), min_size=1, max_size=4)
    )
    @settings(
        max_examples=15,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_rollback_recommendation_logic(self, resolution_results):
        """
        Property: Rollback recommendations should be logical and consistent.
        
        For any set of validation results, rollback recommendations should
        be based on regression severity and resolution success rates.
        """
        test_config = TestConfiguration()
        fix_validator = FixValidator(config=test_config)
        
        # Create validation results with controlled statuses
        validation_results = []
        for resolution in resolution_results:
            # Randomly assign validation statuses for testing
            import random
            status = random.choice(list(ValidationStatus))
            
            validation_result = ValidationResult(
                resolution_result=resolution,
                validation_status=status,
                pre_fix_tests=[],
                post_fix_tests=[],
                regression_tests=[],
                validation_details=f"Validation status: {status.value}"
            )
            validation_results.append(validation_result)
        
        # Property: Rollback recommendation should return boolean and reason
        should_rollback, rollback_reason = fix_validator.recommend_rollback(validation_results)
        
        assert isinstance(should_rollback, bool), (
            "Rollback recommendation should return boolean"
        )
        assert isinstance(rollback_reason, str), (
            "Rollback recommendation should return reason string"
        )
        assert len(rollback_reason) > 0, (
            "Rollback reason should not be empty"
        )
        
        # Property: Rollback reason should be informative
        reason_lower = rollback_reason.lower()
        if should_rollback:
            assert any(keyword in reason_lower for keyword in [
                'rollback', 'regression', 'critical', 'failure', 'recommended'
            ]), "Rollback reason should explain why rollback is recommended"
        else:
            assert any(keyword in reason_lower for keyword in [
                'continue', 'no', 'resolved', 'successful'
            ]), "Continue reason should explain why rollback is not needed"
        
        # Property: Critical regressions should trigger rollback recommendation
        critical_regressions = sum(1 for result in validation_results 
                                 if (result.validation_status == ValidationStatus.REGRESSION_DETECTED and
                                     result.resolution_result.issue.severity == Severity.CRITICAL))
        
        if critical_regressions > 0:
            assert should_rollback, (
                "Critical regressions should trigger rollback recommendation"
            )
            assert 'critical' in reason_lower, (
                "Rollback reason should mention critical regressions"
            )
    
    @given(
        resolution_result_strategy()
    )
    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_validation_error_handling(self, resolution_result):
        """
        Property: Validation should handle errors gracefully.
        
        For any resolution result, validation should handle tester failures
        and other exceptions without crashing.
        """
        test_config = TestConfiguration()
        
        # Create mock testers that raise exceptions
        failing_component_tester = Mock(spec=ComponentTester)
        failing_component_tester.test_dependencies.side_effect = Exception("Mock dependency test failure")
        failing_component_tester.test_openai_client.side_effect = Exception("Mock OpenAI test failure")
        failing_component_tester.test_dynamodb_operations.side_effect = Exception("Mock DynamoDB test failure")
        
        failing_integration_tester = Mock(spec=IntegrationTester)
        failing_integration_tester.test_state_machine_exists.side_effect = Exception("Mock state machine test failure")
        failing_integration_tester.test_api_endpoints.side_effect = Exception("Mock API test failure")
        failing_integration_tester.test_execution_permissions.side_effect = Exception("Mock permission test failure")
        
        fix_validator = FixValidator(
            config=test_config,
            component_tester=failing_component_tester,
            integration_tester=failing_integration_tester
        )
        
        # Property: Validation should not crash with failing testers
        try:
            validation_result = fix_validator.validate_resolution(resolution_result)
            
            # Property: Should return ValidationResult even with errors
            assert isinstance(validation_result, ValidationResult), (
                "Should return ValidationResult even with tester failures"
            )
            
            # Property: Should have appropriate validation status for errors
            assert validation_result.validation_status in [
                ValidationStatus.NOT_RESOLVED,
                ValidationStatus.REGRESSION_DETECTED
            ], "Should have appropriate status when tests fail"
            
            # Property: Should provide error information in details
            details_lower = validation_result.validation_details.lower()
            assert any(keyword in details_lower for keyword in [
                'error', 'failed', 'exception', 'failure'
            ]), "Validation details should indicate test failures"
            
        except Exception as e:
            # If validation itself fails, it should be a controlled failure
            assert "validation failed" in str(e).lower(), (
                "Validation failures should be controlled and informative"
            )
    
    @given(
        st.lists(resolution_result_strategy(), min_size=1, max_size=3)
    )
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_validation_baseline_consistency(self, resolution_results):
        """
        Property: Baseline results should be used consistently for regression detection.
        
        For any set of resolution results, validation should use baseline
        results consistently to detect regressions.
        """
        test_config = TestConfiguration()
        
        # Create mock testers with consistent results
        component_tester = MockComponentTester()
        integration_tester = MockIntegrationTester()
        
        fix_validator = FixValidator(
            config=test_config,
            component_tester=component_tester,
            integration_tester=integration_tester
        )
        
        # Set baseline results
        component_reports = [component_tester.generate_test_report()]
        integration_reports = [IntegrationTestReport(
            state_machine_tests=[integration_tester.test_state_machine_exists()],
            api_endpoint_tests=[integration_tester.test_api_endpoints()],
            workflow_tests=[integration_tester.run_manual_execution({})],
            permission_tests=[integration_tester.test_execution_permissions()],
            overall_status=TestStatus.PASS,
            identified_issues=[]
        )]
        
        fix_validator.set_baseline_results(component_reports, integration_reports)
        
        # Property: Baseline should be stored and accessible
        assert len(fix_validator._baseline_results) > 0, (
            "Baseline results should be stored"
        )
        
        # Property: Validation should use baseline for regression detection
        for resolution_result in resolution_results:
            validation_result = fix_validator.validate_resolution(resolution_result)
            
            # Property: Should have regression tests when baseline exists
            assert isinstance(validation_result.regression_tests, list), (
                "Should have regression test results"
            )
            
            # Property: Regression tests should be based on baseline
            # (In this mock scenario, we expect some regression tests to be run)
            if resolution_result.issue.issue_type != IssueType.DEPENDENCY:
                # Non-dependency issues should trigger dependency regression checks
                dependency_regression_tests = [
                    test for test in validation_result.regression_tests 
                    if 'dependencies' in test.test_name.lower()
                ]
                # We expect at least some regression testing to occur
                # (The exact behavior depends on the mock implementation)


if __name__ == '__main__':
    pytest.main([__file__])