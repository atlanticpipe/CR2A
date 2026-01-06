"""
Property-based tests for dependency verification.
Tests universal properties that should hold for package dependency verification.

Feature: cr2a-testing-debugging, Property 1: Package dependency verification
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from typing import Dict, List, Optional, Any
import importlib
import sys
from pathlib import Path

from tests.core.models import TestResult, TestStatus, TestConfiguration
from tests.component.dependency_tester import DependencyTester


# Strategy for generating package configurations
@st.composite
def package_config_strategy(draw):
    """Generate valid package configurations for testing."""
    # Generate a mix of real packages and fictional ones
    real_packages = ['json', 'os', 'logging', 'sys', 'datetime', 'pathlib']
    fictional_packages = draw(st.lists(
        st.text(min_size=1, max_size=20).filter(
            lambda x: x.isidentifier() and x not in sys.builtin_module_names
        ),
        min_size=0,
        max_size=5
    ))
    
    # Select some real packages
    selected_real = draw(st.lists(
        st.sampled_from(real_packages),
        min_size=1,
        max_size=len(real_packages)
    ))
    
    # Combine real and fictional packages
    all_packages = list(set(selected_real + fictional_packages))
    
    # Create package configuration with optional versions
    config = {}
    for package in all_packages:
        version = None
        if draw(st.booleans()):
            version = draw(st.text(min_size=1, max_size=10).filter(
                lambda x: all(c.isdigit() or c == '.' for c in x) and x.count('.') <= 2
            ))
        config[package] = version
    
    return config


# Strategy for generating test configurations
@st.composite
def _test_config_strategy(draw):
    """Generate valid TestConfiguration instances."""
    aws_region = draw(st.sampled_from(['us-east-1', 'us-west-2', 'eu-west-1']))
    lambda_timeout = draw(st.integers(min_value=5, max_value=300))
    max_retries = draw(st.integers(min_value=1, max_value=10))
    parallel_execution = draw(st.booleans())
    verbose_logging = draw(st.booleans())
    save_artifacts = draw(st.booleans())
    
    return TestConfiguration(
        aws_region=aws_region,
        lambda_timeout=lambda_timeout,
        max_retries=max_retries,
        parallel_execution=parallel_execution,
        verbose_logging=verbose_logging,
        save_artifacts=save_artifacts
    )


class TestDependencyVerificationProperties:
    """Property-based tests for dependency verification functionality."""
    
    @given(_test_config_strategy())
    @settings(
        max_examples=3,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_package_dependency_verification(self, test_config):
        """
        Property 1: Package dependency verification
        
        For any Lambda layer configuration with required packages, the dependency 
        tester should successfully import all packages and verify their versions 
        match the expected specifications.
        
        **Validates: Requirements 1.1**
        """
        # Create dependency tester with the test configuration
        tester = DependencyTester(test_config)
        
        # Property: Dependency tester should be properly initialized
        assert tester is not None, "Dependency tester should be created successfully"
        assert tester.required_packages is not None, "Required packages should be loaded"
        assert isinstance(tester.required_packages, dict), "Required packages should be a dictionary"
        
        # Property: Test dependencies method should return a valid TestResult
        result = tester.test_dependencies()
        assert result is not None, "Dependency test should return a result"
        assert isinstance(result, TestResult), "Result should be a TestResult instance"
        assert result.test_name == "dependency_imports", "Test name should be 'dependency_imports'"
        assert result.status in [TestStatus.PASS, TestStatus.FAIL, TestStatus.ERROR], (
            "Test status should be a valid TestStatus"
        )
        assert result.message is not None, "Test message should be provided"
        assert len(result.message.strip()) > 0, "Test message should not be empty"
        assert result.timestamp is not None, "Test timestamp should be set"
        assert result.execution_time >= 0, "Execution time should be non-negative"
        
        # Property: Test result details should contain expected information
        assert result.details is not None, "Test details should be provided"
        assert isinstance(result.details, dict), "Test details should be a dictionary"
        
        required_detail_keys = ['failed_imports', 'version_mismatches', 'successful_imports', 'total_packages']
        for key in required_detail_keys:
            assert key in result.details, f"Test details should contain '{key}'"
        
        # Property: Detail values should have correct types and constraints
        assert isinstance(result.details['failed_imports'], list), "Failed imports should be a list"
        assert isinstance(result.details['version_mismatches'], list), "Version mismatches should be a list"
        assert isinstance(result.details['successful_imports'], list), "Successful imports should be a list"
        assert isinstance(result.details['total_packages'], int), "Total packages should be an integer"
        assert result.details['total_packages'] >= 0, "Total packages should be non-negative"
        
        # Property: The sum of successful and failed imports should not exceed total packages
        total_attempts = len(result.details['successful_imports']) + len(result.details['failed_imports'])
        assert total_attempts <= result.details['total_packages'], (
            "Total import attempts should not exceed total packages"
        )
        
        # Property: Test status should be consistent with results
        if result.details['failed_imports']:
            assert result.status == TestStatus.FAIL, (
                "Test status should be FAIL when there are failed imports"
            )
            assert "Failed to import" in result.message, (
                "Test message should mention failed imports"
            )
        elif result.details['version_mismatches']:
            assert result.status == TestStatus.FAIL, (
                "Test status should be FAIL when there are version mismatches"
            )
            assert "version mismatch" in result.message.lower(), (
                "Test message should mention version mismatches"
            )
        elif result.details['successful_imports']:
            assert result.status == TestStatus.PASS, (
                "Test status should be PASS when all imports succeed"
            )
            assert "Successfully imported" in result.message, (
                "Test message should mention successful imports"
            )
        
        # Property: All successful imports should be valid Python identifiers
        for package_name in result.details['successful_imports']:
            assert isinstance(package_name, str), "Package name should be a string"
            assert len(package_name.strip()) > 0, "Package name should not be empty"
            # Note: We don't check isidentifier() because some packages have hyphens in names
        
        # Property: Failed import messages should contain package names
        for failed_import in result.details['failed_imports']:
            assert isinstance(failed_import, str), "Failed import message should be a string"
            assert len(failed_import.strip()) > 0, "Failed import message should not be empty"
            assert ":" in failed_import, "Failed import message should contain package name and error"
        
        # Property: Version mismatch messages should contain version information
        for version_mismatch in result.details['version_mismatches']:
            assert isinstance(version_mismatch, str), "Version mismatch message should be a string"
            assert len(version_mismatch.strip()) > 0, "Version mismatch message should not be empty"
            assert "expected" in version_mismatch.lower(), (
                "Version mismatch message should mention expected version"
            )
            assert "got" in version_mismatch.lower(), (
                "Version mismatch message should mention actual version"
            )
    
    @given(_test_config_strategy())
    @settings(
        max_examples=3,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_critical_imports_verification(self, test_config):
        """
        Property: Critical imports should be consistently testable.
        
        For any test configuration, the critical imports test should return 
        consistent results and properly categorize import successes and failures.
        """
        # Create dependency tester
        tester = DependencyTester(test_config)
        
        # Property: Critical imports test should return valid results
        result = tester.test_critical_imports()
        assert result is not None, "Critical imports test should return a result"
        assert isinstance(result, TestResult), "Result should be a TestResult instance"
        assert result.test_name == "critical_imports", "Test name should be 'critical_imports'"
        assert result.status in [TestStatus.PASS, TestStatus.FAIL, TestStatus.ERROR], (
            "Test status should be a valid TestStatus"
        )
        
        # Property: Result details should contain import information
        assert result.details is not None, "Test details should be provided"
        assert 'failed_imports' in result.details, "Details should contain failed imports"
        assert 'successful_imports' in result.details, "Details should contain successful imports"
        
        # Property: Import lists should be mutually exclusive
        failed_imports = result.details['failed_imports']
        successful_imports = result.details['successful_imports']
        
        assert isinstance(failed_imports, list), "Failed imports should be a list"
        assert isinstance(successful_imports, list), "Successful imports should be a list"
        
        # Extract package names from failed imports (format: "package: error")
        failed_packages = []
        for failed_import in failed_imports:
            if ":" in failed_import:
                package_name = failed_import.split(":")[0].strip()
                failed_packages.append(package_name)
        
        # Property: No package should appear in both successful and failed lists
        for package in successful_imports:
            assert package not in failed_packages, (
                f"Package '{package}' should not appear in both successful and failed imports"
            )
        
        # Property: Built-in modules should generally succeed
        builtin_modules = ['json', 'os', 'logging']
        for module in builtin_modules:
            if module in successful_imports:
                # This is expected - built-in modules should import successfully
                pass
            elif any(module in failed for failed in failed_imports):
                # This would be unexpected but we'll just verify the error is reported
                assert result.status == TestStatus.FAIL, (
                    f"Test should fail if built-in module '{module}' fails to import"
                )
    
    @given(_test_config_strategy())
    @settings(
        max_examples=3,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_lambda_layer_structure_verification(self, test_config):
        """
        Property: Lambda layer structure verification should be consistent.
        
        For any test configuration, the layer structure test should properly 
        validate the environment and return appropriate results.
        """
        # Create dependency tester
        tester = DependencyTester(test_config)
        
        # Property: Layer structure test should return valid results
        result = tester.test_lambda_layer_structure()
        assert result is not None, "Layer structure test should return a result"
        assert isinstance(result, TestResult), "Result should be a TestResult instance"
        assert result.test_name == "lambda_layer_structure", "Test name should be 'lambda_layer_structure'"
        assert result.status in [TestStatus.PASS, TestStatus.FAIL, TestStatus.ERROR], (
            "Test status should be a valid TestStatus"
        )
        
        # Property: Result should contain environment information
        assert result.details is not None, "Test details should be provided"
        assert isinstance(result.details, dict), "Test details should be a dictionary"
        
        # Property: Test message should be descriptive
        assert result.message is not None, "Test message should be provided"
        assert len(result.message.strip()) > 0, "Test message should not be empty"
        
        # Property: If test fails, details should contain issues
        if result.status == TestStatus.FAIL:
            assert 'issues' in result.details, "Failed test should contain issues in details"
            issues = result.details['issues']
            assert isinstance(issues, list), "Issues should be a list"
            assert len(issues) > 0, "Failed test should have at least one issue"
            
            for issue in issues:
                assert isinstance(issue, str), "Each issue should be a string"
                assert len(issue.strip()) > 0, "Each issue should not be empty"
        
        # Property: If test passes, it should indicate valid structure
        if result.status == TestStatus.PASS:
            assert "valid" in result.message.lower(), (
                "Passing test message should indicate valid structure"
            )
    
    @given(_test_config_strategy())
    @settings(
        max_examples=3,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_component_test_report_generation(self, test_config):
        """
        Property: Component test report generation should be comprehensive.
        
        For any test configuration, generating a component test report should 
        include all dependency tests and provide appropriate recommendations.
        """
        # Create dependency tester
        tester = DependencyTester(test_config)
        
        # Property: Report generation should return valid report
        report = tester.generate_test_report()
        assert report is not None, "Test report should be generated"
        assert hasattr(report, 'lambda_function'), "Report should have lambda_function attribute"
        assert hasattr(report, 'dependency_tests'), "Report should have dependency_tests attribute"
        assert hasattr(report, 'overall_status'), "Report should have overall_status attribute"
        assert hasattr(report, 'recommendations'), "Report should have recommendations attribute"
        
        # Property: Report should contain dependency tests
        assert isinstance(report.dependency_tests, list), "Dependency tests should be a list"
        assert len(report.dependency_tests) > 0, "Report should contain at least one dependency test"
        
        # Property: All dependency tests should be valid TestResult instances
        for test in report.dependency_tests:
            assert isinstance(test, TestResult), "Each dependency test should be a TestResult"
            assert test.test_name is not None, "Test name should be set"
            assert test.status is not None, "Test status should be set"
            assert test.message is not None, "Test message should be set"
        
        # Property: Overall status should reflect individual test results
        test_statuses = [test.status for test in report.dependency_tests]
        if TestStatus.FAIL in test_statuses or TestStatus.ERROR in test_statuses:
            assert report.overall_status in [TestStatus.FAIL, TestStatus.ERROR], (
                "Overall status should be FAIL or ERROR when individual tests fail"
            )
        elif all(status == TestStatus.PASS for status in test_statuses):
            assert report.overall_status == TestStatus.PASS, (
                "Overall status should be PASS when all individual tests pass"
            )
        
        # Property: Recommendations should be provided for failed tests
        assert isinstance(report.recommendations, list), "Recommendations should be a list"
        if report.overall_status == TestStatus.FAIL:
            assert len(report.recommendations) > 0, (
                "Failed tests should generate recommendations"
            )
            
            for recommendation in report.recommendations:
                assert isinstance(recommendation, str), "Each recommendation should be a string"
                assert len(recommendation.strip()) > 0, "Each recommendation should not be empty"
        
        # Property: Lambda function name should be set
        assert report.lambda_function is not None, "Lambda function name should be set"
        assert len(report.lambda_function.strip()) > 0, "Lambda function name should not be empty"
        
        # Property: Report timestamp should be set
        assert report.timestamp is not None, "Report timestamp should be set"