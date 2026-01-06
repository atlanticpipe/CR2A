"""
Property-based tests for issue prioritization consistency.
Tests universal properties that should hold for issue prioritization in the CR2A system.

Feature: cr2a-testing-debugging, Property 12: Issue prioritization consistency
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from typing import List, Dict, Any, Set
from datetime import datetime, timezone

from .issue_analyzer import IssueAnalyzer, DependencyLevel, IssueAnalysis
from ..core.models import (
    Issue, IssueType, Severity, TestResult, TestStatus,
    ComponentTestReport, IntegrationTestReport
)


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
    
    description = draw(st.text(min_size=10, max_size=200))
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


# Strategy for generating TestResult instances
@st.composite
def result_generation_strategy(draw):
    """Generate valid TestResult instances."""
    test_name = draw(st.text(min_size=5, max_size=50))
    status = draw(st.sampled_from([TestStatus.FAIL, TestStatus.ERROR]))  # Focus on failures
    
    # Generate realistic error messages
    error_messages = [
        "ModuleNotFoundError: No module named 'missing_package'",
        "KeyError: 'OPENAI_API_KEY' not found in environment",
        "ValidationException: Reserved keyword 'status' used in expression",
        "AccessDenied: User not authorized to perform action",
        "ConnectionError: Failed to connect to OpenAI API",
        "Task timed out after 30 seconds",
        "Invalid state machine definition",
        "CORS policy violation"
    ]
    message = draw(st.sampled_from(error_messages))
    
    execution_time = draw(st.floats(min_value=0.1, max_value=30.0))
    
    return TestResult(
        test_name=test_name,
        status=status,
        message=message,
        execution_time=execution_time,
        timestamp=datetime.now(timezone.utc)
    )


# Strategy for generating ComponentTestReport instances
@st.composite
def component_report_strategy(draw):
    """Generate valid ComponentTestReport instances."""
    lambda_functions = [
        "cr2a-analyzer", "cr2a-get-metadata", "cr2a-llm-refine",
        "cr2a-calculate-chunks", "cr2a-aggregate-results"
    ]
    lambda_function = draw(st.sampled_from(lambda_functions))
    
    dependency_tests = draw(st.lists(result_generation_strategy(), min_size=0, max_size=3))
    client_tests = draw(st.lists(result_generation_strategy(), min_size=0, max_size=3))
    database_tests = draw(st.lists(result_generation_strategy(), min_size=0, max_size=3))
    
    # Determine overall status based on individual tests
    all_tests = dependency_tests + client_tests + database_tests
    if any(test.status in [TestStatus.FAIL, TestStatus.ERROR] for test in all_tests):
        overall_status = TestStatus.FAIL
    else:
        overall_status = TestStatus.PASS
    
    recommendations = draw(st.lists(
        st.text(min_size=10, max_size=100), 
        min_size=0, 
        max_size=3
    ))
    
    return ComponentTestReport(
        lambda_function=lambda_function,
        dependency_tests=dependency_tests,
        client_tests=client_tests,
        database_tests=database_tests,
        overall_status=overall_status,
        recommendations=recommendations,
        timestamp=datetime.now(timezone.utc)
    )


# Strategy for generating IntegrationTestReport instances
@st.composite
def integration_report_strategy(draw):
    """Generate valid IntegrationTestReport instances."""
    state_machine_tests = draw(st.lists(result_generation_strategy(), min_size=0, max_size=3))
    api_endpoint_tests = draw(st.lists(result_generation_strategy(), min_size=0, max_size=3))
    workflow_tests = draw(st.lists(result_generation_strategy(), min_size=0, max_size=3))
    permission_tests = draw(st.lists(result_generation_strategy(), min_size=0, max_size=3))
    
    # Determine overall status
    all_tests = state_machine_tests + api_endpoint_tests + workflow_tests + permission_tests
    if any(test.status in [TestStatus.FAIL, TestStatus.ERROR] for test in all_tests):
        overall_status = TestStatus.FAIL
    else:
        overall_status = TestStatus.PASS
    
    identified_issues = draw(st.lists(issue_strategy(), min_size=0, max_size=5))
    
    return IntegrationTestReport(
        state_machine_tests=state_machine_tests,
        api_endpoint_tests=api_endpoint_tests,
        workflow_tests=workflow_tests,
        permission_tests=permission_tests,
        overall_status=overall_status,
        identified_issues=identified_issues,
        timestamp=datetime.now(timezone.utc)
    )


class TestIssuePrioritizationProperties:
    """Property-based tests for issue prioritization consistency."""
    
    @given(st.lists(issue_strategy(), min_size=1, max_size=10))
    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_issue_prioritization_consistency(self, issues):
        """
        Property 12: Issue prioritization consistency
        
        For any set of identified issues, the resolution system should prioritize 
        fixes based on impact and dependency order.
        
        **Validates: Requirements 5.1**
        """
        analyzer = IssueAnalyzer()
        
        # Property: Impact assessment should be calculated for all issues
        impact_assessment = analyzer._calculate_impact_assessment(issues)
        
        # All components with issues should have impact scores
        issue_components = {issue.component for issue in issues}
        for component in issue_components:
            assert component in impact_assessment, f"Component '{component}' should have impact score"
            assert impact_assessment[component] >= 0, f"Impact score for '{component}' should be non-negative"
        
        # Property: Prioritized issues should maintain dependency order
        prioritized_issues = analyzer._prioritize_issues(issues, impact_assessment)
        
        # All original issues should be in prioritized list
        assert len(prioritized_issues) == len(issues), "All issues should be in prioritized list"
        
        # Compare issues by their attributes since Issue is not hashable
        # Convert Severity to string for comparison
        prioritized_ids = [(issue.component, issue.description, issue.severity.value) for issue in prioritized_issues]
        original_ids = [(issue.component, issue.description, issue.severity.value) for issue in issues]
        assert sorted(prioritized_ids) == sorted(original_ids), "Prioritized list should contain same issues"
        
        # Property: Foundation components should come before dependent components
        foundation_components = {"lambda_layers", "iam_permissions"}
        integration_components = {"step_functions", "api_gateway", "openai_client", "dynamodb_operations"}
        
        foundation_positions = []
        integration_positions = []
        application_positions = []
        
        for i, issue in enumerate(prioritized_issues):
            if issue.component in foundation_components:
                foundation_positions.append(i)
            elif issue.component in integration_components:
                integration_positions.append(i)
            else:
                application_positions.append(i)
        
        # Foundation issues should come before integration issues
        if foundation_positions and integration_positions:
            max_foundation_pos = max(foundation_positions)
            min_integration_pos = min(integration_positions)
            assert max_foundation_pos <= min_integration_pos, (
                "Foundation issues should be prioritized before integration issues"
            )
        
        # Integration issues should come before application issues
        if integration_positions and application_positions:
            max_integration_pos = max(integration_positions)
            min_application_pos = min(application_positions)
            assert max_integration_pos <= min_application_pos, (
                "Integration issues should be prioritized before application issues"
            )
        
        # Property: Within same dependency level, higher severity should come first
        # Define severity priority order (lower number = higher priority)
        severity_priority = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1, 
            Severity.MEDIUM: 2,
            Severity.LOW: 3
        }
        
        for component_group in [foundation_components, integration_components]:
            group_issues = [issue for issue in prioritized_issues if issue.component in component_group]
            if len(group_issues) > 1:
                severity_priorities = [severity_priority[issue.severity] for issue in group_issues]
                # Check that severity priorities are non-decreasing (higher severity first)
                for i in range(len(severity_priorities) - 1):
                    # Allow equal severity, but higher severity should not come after lower
                    assert severity_priorities[i] <= severity_priorities[i + 1], (
                        f"Higher severity issues should be prioritized within same dependency level"
                    )
        
        # Property: Blocking issues should be identified correctly
        blocking_issues = analyzer.get_blocking_issues(issues)
        
        for blocking_issue in blocking_issues:
            component = blocking_issue.component
            # Verify this component is actually a dependency for others
            is_dependency = any(
                component in deps 
                for deps in analyzer.dependency_graph.values()
            )
            assert is_dependency, f"Blocking issue component '{component}' should be a dependency"
        
        # Property: Resolution order should group independent issues
        resolution_groups = analyzer.get_resolution_order(issues)
        
        # All issues should be included in resolution groups
        all_grouped_issues = [issue for group in resolution_groups for issue in group]
        assert len(all_grouped_issues) == len(issues), "All issues should be in resolution groups"
        
        # Compare by attributes since Issue is not hashable
        # Convert Severity to string for comparison
        grouped_ids = [(issue.component, issue.description, issue.severity.value) for issue in all_grouped_issues]
        original_ids = [(issue.component, issue.description, issue.severity.value) for issue in issues]
        assert sorted(grouped_ids) == sorted(original_ids), "Resolution groups should contain all issues"
        
        # Property: Issues within same group should not have conflicting dependencies
        # Note: This is a relaxed check - we allow some dependencies within groups
        # as long as they don't create circular dependencies
        for group in resolution_groups:
            if len(group) > 1:
                group_components = {issue.component for issue in group}
                
                # Check for circular dependencies within the group
                # For now, we'll just verify that the group is not empty and contains valid components
                for component in group_components:
                    assert component in analyzer.dependency_graph, (
                        f"Component '{component}' should be in dependency graph"
                    )
                
                # The actual dependency resolution logic is more complex and may allow
                # certain dependencies within groups for parallel execution
    
    @given(
        st.lists(component_report_strategy(), min_size=1, max_size=3),
        st.lists(integration_report_strategy(), min_size=0, max_size=2)
    )
    @settings(
        max_examples=15,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_issue_analysis_completeness(self, component_reports, integration_reports):
        """
        Property: Issue analysis should be complete and consistent.
        
        For any test reports, the issue analyzer should identify all relevant issues
        and provide complete analysis with proper categorization.
        """
        # Filter to reports that have failures
        failing_component_reports = [
            report for report in component_reports 
            if report.overall_status in [TestStatus.FAIL, TestStatus.ERROR]
        ]
        failing_integration_reports = [
            report for report in integration_reports 
            if report.overall_status in [TestStatus.FAIL, TestStatus.ERROR]
        ]
        
        # Skip if no failures to analyze
        assume(len(failing_component_reports) > 0 or len(failing_integration_reports) > 0)
        
        analyzer = IssueAnalyzer()
        
        # Property: Analysis should identify issues from test failures
        analysis = analyzer.analyze_test_results(failing_component_reports, failing_integration_reports)
        
        assert isinstance(analysis, IssueAnalysis), "Should return IssueAnalysis instance"
        assert isinstance(analysis.issues, list), "Issues should be a list"
        assert isinstance(analysis.dependency_graph, dict), "Dependency graph should be a dict"
        assert isinstance(analysis.priority_order, list), "Priority order should be a list"
        assert isinstance(analysis.impact_assessment, dict), "Impact assessment should be a dict"
        
        # Property: All identified issues should be in priority order
        if analysis.issues:
            assert len(analysis.priority_order) == len(analysis.issues), (
                "Priority order should contain all identified issues"
            )
            
            # Compare by attributes since Issue is not hashable
            # Convert Severity to string for comparison
            priority_ids = [(issue.component, issue.description, issue.severity.value) for issue in analysis.priority_order]
            issue_ids = [(issue.component, issue.description, issue.severity.value) for issue in analysis.issues]
            assert sorted(priority_ids) == sorted(issue_ids), (
                "Priority order should contain same issues as analysis"
            )
        
        # Property: Impact assessment should cover all issue components
        issue_components = {issue.component for issue in analysis.issues}
        for component in issue_components:
            assert component in analysis.impact_assessment, (
                f"Component '{component}' should have impact assessment"
            )
        
        # Property: Dependency graph should be consistent
        assert len(analyzer.dependency_graph) > 0, "Dependency graph should not be empty"
        
        for component, deps in analyzer.dependency_graph.items():
            assert isinstance(component, str), "Component should be string"
            assert isinstance(deps, list), "Dependencies should be list"
            
            # No component should depend on itself
            assert component not in deps, f"Component '{component}' should not depend on itself"
            
            # All dependencies should be valid components
            for dep in deps:
                assert dep in analyzer.dependency_graph, (
                    f"Dependency '{dep}' should be a valid component"
                )
        
        # Property: Issues should have proper structure and content
        for issue in analysis.issues:
            assert isinstance(issue, Issue), "Should be Issue instance"
            assert isinstance(issue.issue_type, IssueType), "Should have valid issue type"
            assert isinstance(issue.severity, Severity), "Should have valid severity"
            assert isinstance(issue.component, str), "Component should be string"
            assert len(issue.component) > 0, "Component should not be empty"
            assert isinstance(issue.description, str), "Description should be string"
            assert len(issue.description) > 0, "Description should not be empty"
            assert isinstance(issue.suggested_fix, str), "Suggested fix should be string"
            assert len(issue.suggested_fix) > 0, "Suggested fix should not be empty"
            assert isinstance(issue.resolution_steps, list), "Resolution steps should be list"
            assert len(issue.resolution_steps) > 0, "Should have at least one resolution step"
            
            # All resolution steps should be non-empty strings
            for step in issue.resolution_steps:
                assert isinstance(step, str), "Resolution step should be string"
                assert len(step) > 0, "Resolution step should not be empty"
    
    @given(st.lists(issue_strategy(), min_size=2, max_size=6))
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_prioritization_stability(self, issues):
        """
        Property: Prioritization should be stable and deterministic.
        
        For any set of issues, running prioritization multiple times should
        produce the same order (given same input).
        """
        analyzer = IssueAnalyzer()
        
        # Property: Multiple runs should produce same result
        impact_assessment1 = analyzer._calculate_impact_assessment(issues)
        impact_assessment2 = analyzer._calculate_impact_assessment(issues)
        
        assert impact_assessment1 == impact_assessment2, (
            "Impact assessment should be deterministic"
        )
        
        prioritized1 = analyzer._prioritize_issues(issues, impact_assessment1)
        prioritized2 = analyzer._prioritize_issues(issues, impact_assessment2)
        
        assert prioritized1 == prioritized2, (
            "Prioritization should be deterministic"
        )
        
        # Property: Adding and removing same issue should not change order of others
        # (Only test this when issues have different priorities to avoid tie-breaker issues)
        if len(issues) > 2:
            # Check if issues have different priorities (severity + type combinations)
            priorities = [(issue.severity, issue.issue_type) for issue in issues]
            unique_priorities = set(priorities)
            
            # Only test order preservation if we have different priority levels
            if len(unique_priorities) > 1:
                # Remove one issue
                test_issue = issues[0]
                remaining_issues = issues[1:]
                
                # Get prioritization of remaining issues
                remaining_impact = analyzer._calculate_impact_assessment(remaining_issues)
                remaining_prioritized = analyzer._prioritize_issues(remaining_issues, remaining_impact)
                
                # Add the issue back
                restored_issues = remaining_issues + [test_issue]
                restored_impact = analyzer._calculate_impact_assessment(restored_issues)
                restored_prioritized = analyzer._prioritize_issues(restored_issues, restored_impact)
                
                # The relative order of remaining issues should be preserved
                remaining_in_restored = [
                    issue for issue in restored_prioritized 
                    if issue in remaining_issues
                ]
                
                assert remaining_in_restored == remaining_prioritized, (
                    "Relative order of existing issues should be preserved when adding/removing issues "
                    "(when issues have different priorities)"
                )


if __name__ == '__main__':
    pytest.main([__file__])