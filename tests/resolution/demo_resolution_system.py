"""
Demo script showing how to use the automated issue resolution system.
"""

import logging
from typing import List

from ..core.models import (
    TestConfiguration, TestResult, TestStatus, Issue, IssueType, Severity,
    ComponentTestReport, IntegrationTestReport
)
from .resolution_orchestrator import ResolutionOrchestrator
from .fix_applicator import FixConfiguration


def create_sample_test_reports() -> tuple[List[ComponentTestReport], List[IntegrationTestReport]]:
    """Create sample test reports with various issues for demonstration."""
    
    # Create sample component test report with failures
    component_report = ComponentTestReport(
        lambda_function="cr2a-analyzer",
        dependency_tests=[
            TestResult(
                test_name="test_package_imports",
                status=TestStatus.FAIL,
                message="ImportError: No module named 'openai'",
                details={"missing_package": "openai"}
            )
        ],
        client_tests=[
            TestResult(
                test_name="test_openai_client_init",
                status=TestStatus.FAIL,
                message="Authentication failed: Invalid API key",
                details={"error_type": "AuthenticationError"}
            )
        ],
        database_tests=[
            TestResult(
                test_name="test_dynamodb_write",
                status=TestStatus.FAIL,
                message="ValidationException: Reserved keyword 'status' used",
                details={"reserved_keyword": "status"}
            )
        ],
        overall_status=TestStatus.FAIL,
        recommendations=["Update Lambda layer", "Fix API key", "Use expression attribute names"]
    )
    
    # Create sample integration test report with failures
    integration_report = IntegrationTestReport(
        state_machine_tests=[
            TestResult(
                test_name="test_state_machine_exists",
                status=TestStatus.PASS,
                message="State machine found and active"
            )
        ],
        api_endpoint_tests=[
            TestResult(
                test_name="test_upload_endpoint",
                status=TestStatus.FAIL,
                message="HTTP 500: Internal server error",
                details={"endpoint": "/upload", "status_code": 500}
            )
        ],
        workflow_tests=[
            TestResult(
                test_name="test_end_to_end_workflow",
                status=TestStatus.FAIL,
                message="Workflow execution failed at AnalyzeChunk state"
            )
        ],
        permission_tests=[
            TestResult(
                test_name="test_execution_permissions",
                status=TestStatus.FAIL,
                message="AccessDenied: Role cannot start Step Functions execution"
            )
        ],
        overall_status=TestStatus.FAIL,
        identified_issues=[]  # Will be populated by the analyzer
    )
    
    return [component_report], [integration_report]


def demo_issue_analysis():
    """Demonstrate issue analysis without applying fixes."""
    
    print("=" * 60)
    print("DEMO: Issue Analysis")
    print("=" * 60)
    
    # Set up configuration
    config = TestConfiguration(
        aws_region="us-east-1",
        verbose_logging=True
    )
    
    # Create orchestrator
    orchestrator = ResolutionOrchestrator(config)
    
    # Get sample test reports
    component_reports, integration_reports = create_sample_test_reports()
    
    # Analyze issues
    issue_analysis = orchestrator.get_issue_analysis_only(
        component_reports=component_reports,
        integration_reports=integration_reports
    )
    
    print(f"Issues identified: {len(issue_analysis.issues)}")
    print("\nIssue Details:")
    for i, issue in enumerate(issue_analysis.issues, 1):
        print(f"\n{i}. {issue.issue_type.value} - {issue.severity.value}")
        print(f"   Component: {issue.component}")
        print(f"   Description: {issue.description}")
        print(f"   Suggested Fix: {issue.suggested_fix}")
    
    print(f"\nPriority Order:")
    for i, issue in enumerate(issue_analysis.priority_order, 1):
        print(f"{i}. {issue.component} - {issue.issue_type.value} ({issue.severity.value})")
    
    print(f"\nBlocking Issues:")
    blocking_issues = orchestrator.get_blocking_issues(component_reports, integration_reports)
    for issue in blocking_issues:
        print(f"- {issue.component}: {issue.description}")


def demo_full_resolution_cycle():
    """Demonstrate the full resolution cycle with dry run."""
    
    print("\n" + "=" * 60)
    print("DEMO: Full Resolution Cycle (Dry Run)")
    print("=" * 60)
    
    # Set up configuration for dry run
    config = TestConfiguration(
        aws_region="us-east-1",
        verbose_logging=True
    )
    
    fix_config = FixConfiguration(
        dry_run=True,  # Don't actually make changes
        backup_resources=True,
        rollback_on_failure=True
    )
    
    # Create orchestrator
    orchestrator = ResolutionOrchestrator(config, fix_config)
    
    # Get sample test reports
    component_reports, integration_reports = create_sample_test_reports()
    
    # Execute full resolution cycle
    summary = orchestrator.execute_full_resolution_cycle(
        component_reports=component_reports,
        integration_reports=integration_reports
    )
    
    # Generate and display report
    report = orchestrator.generate_resolution_report(summary)
    print(report)


def demo_targeted_resolution():
    """Demonstrate targeted resolution for specific issues."""
    
    print("\n" + "=" * 60)
    print("DEMO: Targeted Resolution")
    print("=" * 60)
    
    # Set up configuration
    config = TestConfiguration(
        aws_region="us-east-1",
        verbose_logging=True
    )
    
    fix_config = FixConfiguration(dry_run=True)
    
    # Create orchestrator
    orchestrator = ResolutionOrchestrator(config, fix_config)
    
    # Create specific issues to resolve
    specific_issues = [
        Issue(
            issue_type=IssueType.DEPENDENCY,
            severity=Severity.CRITICAL,
            component="cr2a-analyzer",
            description="Missing OpenAI package in Lambda layer",
            suggested_fix="Update Lambda layer with OpenAI package",
            resolution_steps=[
                "Add openai package to requirements.txt",
                "Rebuild Lambda layer",
                "Update Lambda function layer configuration"
            ]
        ),
        Issue(
            issue_type=IssueType.CONFIGURATION,
            severity=Severity.HIGH,
            component="cr2a-analyzer",
            description="Invalid OpenAI API key configuration",
            suggested_fix="Update environment variable with valid API key",
            resolution_steps=[
                "Obtain valid OpenAI API key",
                "Update Lambda function environment variables",
                "Test API key connectivity"
            ]
        )
    ]
    
    # Execute targeted resolution
    summary = orchestrator.execute_targeted_resolution(specific_issues)
    
    # Generate and display report
    report = orchestrator.generate_resolution_report(summary)
    print(report)


def main():
    """Run all demos."""
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("CR2A Automated Issue Resolution System Demo")
    print("This demo shows how the resolution system works with sample data.")
    print("All operations are in DRY RUN mode - no actual changes are made.")
    
    try:
        # Run demos
        demo_issue_analysis()
        demo_full_resolution_cycle()
        demo_targeted_resolution()
        
        print("\n" + "=" * 60)
        print("DEMO COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nTo use the resolution system in production:")
        print("1. Set dry_run=False in FixConfiguration")
        print("2. Ensure AWS credentials are configured")
        print("3. Provide real ComponentTester and IntegrationTester instances")
        print("4. Run with actual test reports from your system")
        
    except Exception as e:
        print(f"\nDemo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()