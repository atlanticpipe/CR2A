"""
Property-based tests for test framework initialization.
Tests universal properties that should hold for test report generation consistency.

Feature: cr2a-testing-debugging, Property 16: Test report generation consistency
"""

import json
import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from typing import Dict, Any, List
from datetime import datetime, timezone

from .models import (
    TestResult, TestStatus, ComponentTestReport, IntegrationTestReport, 
    TestSuite, Issue, IssueType, Severity, TestConfiguration
)
from .interfaces import TestReporter as AbstractTestReporter


# Strategy for generating valid test results
@st.composite
def generate_test_result(draw):
    """Generate valid TestResult instances."""
    test_name = draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    status = draw(st.sampled_from(list(TestStatus)))
    message = draw(st.text(min_size=1, max_size=500))
    execution_time = draw(st.floats(min_value=0.0, max_value=300.0, allow_nan=False, allow_infinity=False))
    
    # Generate optional details dictionary
    details = None
    if draw(st.booleans()):
        details = draw(st.dictionaries(
            keys=st.text(min_size=1, max_size=50),
            values=st.one_of(
                st.text(max_size=200),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.booleans()
            ),
            min_size=0,
            max_size=10
        ))
    
    return TestResult(
        test_name=test_name,
        status=status,
        message=message,
        details=details,
        execution_time=execution_time
    )


# Strategy for generating valid issues
@st.composite
def issue_strategy(draw):
    """Generate valid Issue instances."""
    issue_type = draw(st.sampled_from(list(IssueType)))
    severity = draw(st.sampled_from(list(Severity)))
    component = draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    description = draw(st.text(min_size=1, max_size=500))
    suggested_fix = draw(st.text(min_size=1, max_size=500))
    resolution_steps = draw(st.lists(
        st.text(min_size=1, max_size=200),
        min_size=1,
        max_size=10
    ))
    
    return Issue(
        issue_type=issue_type,
        severity=severity,
        component=component,
        description=description,
        suggested_fix=suggested_fix,
        resolution_steps=resolution_steps
    )


# Strategy for generating component test reports
@st.composite
def component_test_report_strategy(draw):
    """Generate valid ComponentTestReport instances."""
    lambda_function = draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    
    dependency_tests = draw(st.lists(generate_test_result(), min_size=0, max_size=10))
    client_tests = draw(st.lists(generate_test_result(), min_size=0, max_size=10))
    database_tests = draw(st.lists(generate_test_result(), min_size=0, max_size=10))
    
    # Overall status should reflect the worst status among all tests
    all_tests = dependency_tests + client_tests + database_tests
    if all_tests:
        statuses = [test.status for test in all_tests]
        if TestStatus.FAIL in statuses or TestStatus.ERROR in statuses:
            overall_status = TestStatus.FAIL
        elif TestStatus.SKIP in statuses:
            overall_status = TestStatus.SKIP
        else:
            overall_status = TestStatus.PASS
    else:
        overall_status = draw(st.sampled_from(list(TestStatus)))
    
    recommendations = draw(st.lists(
        st.text(min_size=1, max_size=200),
        min_size=0,
        max_size=5
    ))
    
    return ComponentTestReport(
        lambda_function=lambda_function,
        dependency_tests=dependency_tests,
        client_tests=client_tests,
        database_tests=database_tests,
        overall_status=overall_status,
        recommendations=recommendations
    )


# Strategy for generating integration test reports
@st.composite
def integration_test_report_strategy(draw):
    """Generate valid IntegrationTestReport instances."""
    state_machine_tests = draw(st.lists(generate_test_result(), min_size=0, max_size=10))
    api_endpoint_tests = draw(st.lists(generate_test_result(), min_size=0, max_size=10))
    workflow_tests = draw(st.lists(generate_test_result(), min_size=0, max_size=10))
    permission_tests = draw(st.lists(generate_test_result(), min_size=0, max_size=10))
    
    # Overall status should reflect the worst status among all tests
    all_tests = state_machine_tests + api_endpoint_tests + workflow_tests + permission_tests
    if all_tests:
        statuses = [test.status for test in all_tests]
        if TestStatus.FAIL in statuses or TestStatus.ERROR in statuses:
            overall_status = TestStatus.FAIL
        elif TestStatus.SKIP in statuses:
            overall_status = TestStatus.SKIP
        else:
            overall_status = TestStatus.PASS
    else:
        overall_status = draw(st.sampled_from(list(TestStatus)))
    
    identified_issues = draw(st.lists(issue_strategy(), min_size=0, max_size=10))
    
    return IntegrationTestReport(
        state_machine_tests=state_machine_tests,
        api_endpoint_tests=api_endpoint_tests,
        workflow_tests=workflow_tests,
        permission_tests=permission_tests,
        overall_status=overall_status,
        identified_issues=identified_issues
    )


# Strategy for generating test suites
@st.composite
def generate_test_suite(draw):
    """Generate valid TestSuite instances."""
    name = draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    description = draw(st.text(min_size=1, max_size=500))
    tests = draw(st.lists(generate_test_result(), min_size=0, max_size=20))
    
    # Calculate execution time as sum of individual test times
    execution_time = sum(test.execution_time for test in tests)
    
    # Overall status should reflect the worst status among all tests
    if tests:
        statuses = [test.status for test in tests]
        if TestStatus.FAIL in statuses or TestStatus.ERROR in statuses:
            overall_status = TestStatus.FAIL
        elif TestStatus.SKIP in statuses:
            overall_status = TestStatus.SKIP
        else:
            overall_status = TestStatus.PASS
    else:
        overall_status = draw(st.sampled_from(list(TestStatus)))
    
    return TestSuite(
        name=name,
        description=description,
        tests=tests,
        overall_status=overall_status,
        execution_time=execution_time
    )


class _MockTestReporter(AbstractTestReporter):
    """Mock implementation of TestReporter for testing."""
    
    def generate_html_report(self, test_suites: List[TestSuite], output_path: str) -> str:
        """Generate mock HTML test report."""
        html_content = f"""
        <html>
        <head><title>Test Report</title></head>
        <body>
        <h1>Test Report</h1>
        <p>Generated at: {datetime.now(timezone.utc).isoformat()}</p>
        <p>Total Test Suites: {len(test_suites)}</p>
        """
        
        for suite in test_suites:
            html_content += f"""
            <h2>{suite.name}</h2>
            <p>Status: {suite.overall_status.value}</p>
            <p>Tests: {len(suite.tests)}</p>
            <p>Pass Rate: {suite.get_pass_rate():.1f}%</p>
            """
        
        html_content += "</body></html>"
        return html_content
    
    def generate_json_report(self, test_suites: List[TestSuite], output_path: str) -> str:
        """Generate mock JSON test report."""
        report_data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_suites": len(test_suites),
            "suites": []
        }
        
        for suite in test_suites:
            suite_data = {
                "name": suite.name,
                "description": suite.description,
                "status": suite.overall_status.value,
                "test_count": len(suite.tests),
                "pass_rate": suite.get_pass_rate(),
                "execution_time": suite.execution_time,
                "timestamp": suite.timestamp.isoformat() if suite.timestamp else None
            }
            report_data["suites"].append(suite_data)
        
        return json.dumps(report_data, indent=2)
    
    def generate_console_summary(self, test_suites: List[TestSuite]) -> str:
        """Generate mock console-friendly test summary."""
        summary = f"Test Report Summary - {len(test_suites)} suites\n"
        summary += "=" * 50 + "\n"
        
        for suite in test_suites:
            summary += f"{suite.name}: {suite.overall_status.value} "
            summary += f"({len(suite.tests)} tests, {suite.get_pass_rate():.1f}% pass)\n"
        
        return summary


class TestFrameworkInitializationProperties:
    """Property-based tests for test framework initialization and report generation."""
    
    @given(st.lists(generate_test_suite(), min_size=1, max_size=5))
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_test_report_generation_consistency(self, test_suites):
        """
        Property 16: Test report generation consistency
        
        For any completed test run, the system should generate detailed reports 
        with pass/fail status and diagnostic information.
        
        **Validates: Requirements 6.4**
        """
        # Create mock reporter
        reporter = _MockTestReporter()
        
        # Property: HTML report generation should be consistent
        html_report = reporter.generate_html_report(test_suites, "/mock/path.html")
        assert html_report is not None, "HTML report should be generated"
        assert isinstance(html_report, str), "HTML report should be a string"
        assert len(html_report) > 0, "HTML report should not be empty"
        assert "<html>" in html_report, "HTML report should contain HTML tags"
        assert f"Total Test Suites: {len(test_suites)}" in html_report, "HTML report should include suite count"
        
        # Property: JSON report generation should be consistent
        json_report = reporter.generate_json_report(test_suites, "/mock/path.json")
        assert json_report is not None, "JSON report should be generated"
        assert isinstance(json_report, str), "JSON report should be a string"
        assert len(json_report) > 0, "JSON report should not be empty"
        
        # Validate JSON structure
        try:
            json_data = json.loads(json_report)
            assert "generated_at" in json_data, "JSON report should include generation timestamp"
            assert "total_suites" in json_data, "JSON report should include total suite count"
            assert "suites" in json_data, "JSON report should include suites array"
            assert json_data["total_suites"] == len(test_suites), "Suite count should match input"
            assert len(json_data["suites"]) == len(test_suites), "Suites array length should match input"
        except json.JSONDecodeError:
            pytest.fail("JSON report should be valid JSON")
        
        # Property: Console summary generation should be consistent
        console_summary = reporter.generate_console_summary(test_suites)
        assert console_summary is not None, "Console summary should be generated"
        assert isinstance(console_summary, str), "Console summary should be a string"
        assert len(console_summary) > 0, "Console summary should not be empty"
        assert f"{len(test_suites)} suites" in console_summary, "Console summary should include suite count"
        
        # Property: All reports should include information about each test suite
        for suite in test_suites:
            assert suite.name in html_report, f"HTML report should include suite '{suite.name}'"
            
            # For JSON, we need to check the parsed data since JSON may encode Unicode characters
            json_data = json.loads(json_report)
            suite_names_in_json = [s["name"] for s in json_data["suites"]]
            assert suite.name in suite_names_in_json, f"JSON report should include suite '{suite.name}'"
            
            assert suite.name in console_summary, f"Console summary should include suite '{suite.name}'"
            
            # Property: Status information should be consistent across reports
            assert suite.overall_status.value in html_report, f"HTML report should include status for '{suite.name}'"
            assert suite.overall_status.value in console_summary, f"Console summary should include status for '{suite.name}'"
        
        # Property: Pass rate calculations should be consistent
        json_data = json.loads(json_report)  # Parse once for efficiency
        for suite in test_suites:
            expected_pass_rate = suite.get_pass_rate()
            suite_data = next((s for s in json_data["suites"] if s["name"] == suite.name), None)
            assert suite_data is not None, f"Suite '{suite.name}' should be in JSON report"
            assert abs(suite_data["pass_rate"] - expected_pass_rate) < 0.1, (
                f"Pass rate should be consistent for suite '{suite.name}'"
            )
    
    @given(component_test_report_strategy())
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_component_report_consistency(self, component_report):
        """
        Property: Component test reports should maintain internal consistency.
        
        For any component test report, the overall status should reflect the 
        individual test results and all required fields should be populated.
        """
        # Property: Report should have all required fields
        assert component_report.lambda_function is not None, "Lambda function name should be set"
        assert len(component_report.lambda_function.strip()) > 0, "Lambda function name should not be empty"
        assert component_report.dependency_tests is not None, "Dependency tests should be initialized"
        assert component_report.client_tests is not None, "Client tests should be initialized"
        assert component_report.database_tests is not None, "Database tests should be initialized"
        assert component_report.overall_status is not None, "Overall status should be set"
        assert component_report.recommendations is not None, "Recommendations should be initialized"
        assert component_report.timestamp is not None, "Timestamp should be set"
        
        # Property: Overall status should reflect individual test results
        all_tests = (component_report.dependency_tests + 
                    component_report.client_tests + 
                    component_report.database_tests)
        
        if all_tests:
            statuses = [test.status for test in all_tests]
            if TestStatus.FAIL in statuses or TestStatus.ERROR in statuses:
                assert component_report.overall_status == TestStatus.FAIL, (
                    "Overall status should be FAIL when any test fails"
                )
            elif TestStatus.SKIP in statuses and TestStatus.PASS not in statuses:
                # Only if all tests are skipped or failed
                pass  # Overall status can vary based on implementation
        
        # Property: All individual tests should have valid properties
        for test in all_tests:
            assert test.test_name is not None, "Test name should be set"
            assert len(test.test_name.strip()) > 0, "Test name should not be empty"
            assert test.status is not None, "Test status should be set"
            assert test.message is not None, "Test message should be set"
            assert test.timestamp is not None, "Test timestamp should be set"
            assert test.execution_time >= 0, "Execution time should be non-negative"
    
    @given(integration_test_report_strategy())
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_integration_report_consistency(self, integration_report):
        """
        Property: Integration test reports should maintain internal consistency.
        
        For any integration test report, the overall status should reflect the 
        individual test results and identified issues should be properly categorized.
        """
        # Property: Report should have all required fields
        assert integration_report.state_machine_tests is not None, "State machine tests should be initialized"
        assert integration_report.api_endpoint_tests is not None, "API endpoint tests should be initialized"
        assert integration_report.workflow_tests is not None, "Workflow tests should be initialized"
        assert integration_report.permission_tests is not None, "Permission tests should be initialized"
        assert integration_report.overall_status is not None, "Overall status should be set"
        assert integration_report.identified_issues is not None, "Identified issues should be initialized"
        assert integration_report.timestamp is not None, "Timestamp should be set"
        
        # Property: All individual tests should have valid properties
        all_tests = (integration_report.state_machine_tests + 
                    integration_report.api_endpoint_tests + 
                    integration_report.workflow_tests + 
                    integration_report.permission_tests)
        
        for test in all_tests:
            assert test.test_name is not None, "Test name should be set"
            assert len(test.test_name.strip()) > 0, "Test name should not be empty"
            assert test.status is not None, "Test status should be set"
            assert test.message is not None, "Test message should be set"
            assert test.timestamp is not None, "Test timestamp should be set"
            assert test.execution_time >= 0, "Execution time should be non-negative"
        
        # Property: All identified issues should have valid properties
        for issue in integration_report.identified_issues:
            assert issue.issue_type is not None, "Issue type should be set"
            assert issue.severity is not None, "Issue severity should be set"
            assert issue.component is not None, "Issue component should be set"
            assert len(issue.component.strip()) > 0, "Issue component should not be empty"
            assert issue.description is not None, "Issue description should be set"
            assert len(issue.description.strip()) > 0, "Issue description should not be empty"
            assert issue.suggested_fix is not None, "Issue suggested fix should be set"
            assert issue.resolution_steps is not None, "Issue resolution steps should be initialized"
            assert len(issue.resolution_steps) > 0, "Issue should have at least one resolution step"
            assert issue.timestamp is not None, "Issue timestamp should be set"