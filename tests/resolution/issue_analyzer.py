"""
Issue identification and prioritization system.
Analyzes test results to identify issues and prioritize fixes based on impact and dependencies.
"""

import logging
from typing import List, Dict, Any, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from ..core.models import (
    TestResult, TestStatus, Issue, IssueType, Severity,
    ComponentTestReport, IntegrationTestReport
)


class DependencyLevel(Enum):
    """Dependency levels for prioritization."""
    FOUNDATION = 1  # Core dependencies (Lambda layers, IAM)
    INTEGRATION = 2  # Service integrations (Step Functions, API Gateway)
    APPLICATION = 3  # Application-level features


@dataclass
class IssueAnalysis:
    """Analysis result for identified issues."""
    issues: List[Issue]
    dependency_graph: Dict[str, List[str]]
    priority_order: List[Issue]
    impact_assessment: Dict[str, float]


class IssueAnalyzer:
    """Analyzes test results to identify and prioritize issues."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Define component dependencies (what depends on what)
        self.dependency_graph = {
            "lambda_layers": [],  # Foundation - no dependencies
            "iam_permissions": [],  # Foundation - no dependencies
            "openai_client": ["lambda_layers", "iam_permissions"],
            "dynamodb_operations": ["lambda_layers", "iam_permissions"],
            "step_functions": ["lambda_layers", "iam_permissions", "openai_client", "dynamodb_operations"],
            "api_gateway": ["lambda_layers", "iam_permissions", "step_functions"],
            "cors_configuration": ["api_gateway"],
            "end_to_end_workflow": ["step_functions", "api_gateway", "cors_configuration"]
        }
        
        # Define severity weights for impact calculation
        self.severity_weights = {
            Severity.CRITICAL: 1.0,
            Severity.HIGH: 0.7,
            Severity.MEDIUM: 0.4,
            Severity.LOW: 0.1
        }
    
    def analyze_test_results(self, 
                           component_reports: List[ComponentTestReport] = None,
                           integration_reports: List[IntegrationTestReport] = None) -> IssueAnalysis:
        """Analyze test results and identify issues with prioritization."""
        
        issues = []
        
        # Analyze component test results
        if component_reports:
            for report in component_reports:
                issues.extend(self._analyze_component_report(report))
        
        # Analyze integration test results
        if integration_reports:
            for report in integration_reports:
                issues.extend(self._analyze_integration_report(report))
                # Add any pre-identified issues from the report
                issues.extend(report.identified_issues)
        
        # Calculate impact assessment
        impact_assessment = self._calculate_impact_assessment(issues)
        
        # Prioritize issues based on dependencies and impact
        priority_order = self._prioritize_issues(issues, impact_assessment)
        
        return IssueAnalysis(
            issues=issues,
            dependency_graph=self.dependency_graph,
            priority_order=priority_order,
            impact_assessment=impact_assessment
        )
    
    def _analyze_component_report(self, report: ComponentTestReport) -> List[Issue]:
        """Analyze component test report to identify issues."""
        issues = []
        
        # Analyze dependency tests
        for test in report.dependency_tests:
            if test.status in [TestStatus.FAIL, TestStatus.ERROR]:
                issue = self._create_dependency_issue(test, report.lambda_function)
                issues.append(issue)
        
        # Analyze client tests (OpenAI)
        for test in report.client_tests:
            if test.status in [TestStatus.FAIL, TestStatus.ERROR]:
                issue = self._create_client_issue(test, report.lambda_function)
                issues.append(issue)
        
        # Analyze database tests
        for test in report.database_tests:
            if test.status in [TestStatus.FAIL, TestStatus.ERROR]:
                issue = self._create_database_issue(test, report.lambda_function)
                issues.append(issue)
        
        return issues
    
    def _analyze_integration_report(self, report: IntegrationTestReport) -> List[Issue]:
        """Analyze integration test report to identify issues."""
        issues = []
        
        # Analyze state machine tests
        for test in report.state_machine_tests:
            if test.status in [TestStatus.FAIL, TestStatus.ERROR]:
                issue = self._create_integration_issue(test, "step_functions")
                issues.append(issue)
        
        # Analyze API endpoint tests
        for test in report.api_endpoint_tests:
            if test.status in [TestStatus.FAIL, TestStatus.ERROR]:
                issue = self._create_integration_issue(test, "api_gateway")
                issues.append(issue)
        
        # Analyze workflow tests
        for test in report.workflow_tests:
            if test.status in [TestStatus.FAIL, TestStatus.ERROR]:
                issue = self._create_integration_issue(test, "end_to_end_workflow")
                issues.append(issue)
        
        # Analyze permission tests
        for test in report.permission_tests:
            if test.status in [TestStatus.FAIL, TestStatus.ERROR]:
                issue = self._create_permission_issue(test)
                issues.append(issue)
        
        return issues
    
    def _create_dependency_issue(self, test: TestResult, component: str) -> Issue:
        """Create issue for dependency test failure."""
        severity = self._determine_severity_from_test(test)
        
        if "import" in test.message.lower() or "module" in test.message.lower():
            description = f"Package import failure in {component}: {test.message}"
            suggested_fix = "Update Lambda layer with missing or correct package versions"
            resolution_steps = [
                "Identify missing or incompatible packages",
                "Update requirements.txt with correct versions",
                "Rebuild and deploy Lambda layer",
                "Update Lambda function layer configuration"
            ]
        else:
            description = f"Dependency issue in {component}: {test.message}"
            suggested_fix = "Review and fix dependency configuration"
            resolution_steps = [
                "Analyze dependency error details",
                "Update configuration as needed",
                "Redeploy affected components"
            ]
        
        return Issue(
            issue_type=IssueType.DEPENDENCY,
            severity=severity,
            component=component,
            description=description,
            suggested_fix=suggested_fix,
            resolution_steps=resolution_steps
        )
    
    def _create_client_issue(self, test: TestResult, component: str) -> Issue:
        """Create issue for client test failure."""
        severity = self._determine_severity_from_test(test)
        
        if "api" in test.message.lower() or "key" in test.message.lower():
            description = f"OpenAI client configuration issue in {component}: {test.message}"
            suggested_fix = "Update OpenAI API key configuration"
            resolution_steps = [
                "Verify OpenAI API key is valid and active",
                "Update environment variables with correct API key",
                "Ensure IAM permissions allow access to environment variables",
                "Redeploy Lambda function with updated configuration"
            ]
        else:
            description = f"Client initialization issue in {component}: {test.message}"
            suggested_fix = "Review client configuration and network connectivity"
            resolution_steps = [
                "Check client configuration parameters",
                "Verify network connectivity and security groups",
                "Update client initialization code if needed"
            ]
        
        return Issue(
            issue_type=IssueType.CONFIGURATION,
            severity=severity,
            component=component,
            description=description,
            suggested_fix=suggested_fix,
            resolution_steps=resolution_steps
        )
    
    def _create_database_issue(self, test: TestResult, component: str) -> Issue:
        """Create issue for database test failure."""
        severity = self._determine_severity_from_test(test)
        
        if "reserved" in test.message.lower() or "keyword" in test.message.lower():
            description = f"DynamoDB reserved keyword conflict in {component}: {test.message}"
            suggested_fix = "Update attribute names to avoid reserved keywords"
            resolution_steps = [
                "Identify conflicting attribute names",
                "Update code to use expression attribute names",
                "Test DynamoDB operations with updated code",
                "Deploy updated Lambda function"
            ]
        elif "permission" in test.message.lower():
            description = f"DynamoDB permission issue in {component}: {test.message}"
            suggested_fix = "Update IAM permissions for DynamoDB access"
            resolution_steps = [
                "Review current IAM policy for DynamoDB permissions",
                "Add missing permissions (dynamodb:PutItem, GetItem, etc.)",
                "Update IAM role attached to Lambda function",
                "Test DynamoDB operations after permission update"
            ]
        else:
            description = f"DynamoDB operation issue in {component}: {test.message}"
            suggested_fix = "Review DynamoDB configuration and operations"
            resolution_steps = [
                "Analyze DynamoDB error details",
                "Check table configuration and schema",
                "Update operation code if needed",
                "Redeploy with fixes"
            ]
        
        return Issue(
            issue_type=IssueType.CONFIGURATION,
            severity=severity,
            component=component,
            description=description,
            suggested_fix=suggested_fix,
            resolution_steps=resolution_steps
        )
    
    def _create_integration_issue(self, test: TestResult, component: str) -> Issue:
        """Create issue for integration test failure."""
        severity = self._determine_severity_from_test(test)
        
        description = f"Integration issue in {component}: {test.message}"
        
        if component == "step_functions":
            suggested_fix = "Update Step Functions state machine definition"
            resolution_steps = [
                "Review state machine definition JSON",
                "Verify Lambda function ARNs are correct",
                "Check IAM permissions for state machine execution",
                "Update and redeploy state machine"
            ]
        elif component == "api_gateway":
            suggested_fix = "Update API Gateway configuration"
            resolution_steps = [
                "Review API Gateway endpoint configuration",
                "Check Lambda function integration settings",
                "Verify CORS configuration if needed",
                "Redeploy API Gateway stage"
            ]
        else:
            suggested_fix = "Review integration configuration"
            resolution_steps = [
                "Analyze integration error details",
                "Check component connectivity",
                "Update configuration as needed"
            ]
        
        return Issue(
            issue_type=IssueType.INTEGRATION,
            severity=severity,
            component=component,
            description=description,
            suggested_fix=suggested_fix,
            resolution_steps=resolution_steps
        )
    
    def _create_permission_issue(self, test: TestResult) -> Issue:
        """Create issue for permission test failure."""
        severity = self._determine_severity_from_test(test)
        
        return Issue(
            issue_type=IssueType.PERMISSION,
            severity=severity,
            component="iam_permissions",
            description=f"IAM permission issue: {test.message}",
            suggested_fix="Update IAM role permissions",
            resolution_steps=[
                "Identify missing IAM permissions from error",
                "Update IAM policy with required permissions",
                "Attach updated policy to appropriate role",
                "Test permissions after update"
            ]
        )
    
    def _determine_severity_from_test(self, test: TestResult) -> Severity:
        """Determine issue severity based on test result."""
        if test.status == TestStatus.ERROR:
            return Severity.CRITICAL
        elif "critical" in test.message.lower() or "fatal" in test.message.lower():
            return Severity.CRITICAL
        elif "permission" in test.message.lower() or "access" in test.message.lower():
            return Severity.HIGH
        elif "warning" in test.message.lower():
            return Severity.LOW
        else:
            return Severity.MEDIUM
    
    def _calculate_impact_assessment(self, issues: List[Issue]) -> Dict[str, float]:
        """Calculate impact assessment for each component."""
        impact_scores = {}
        
        for issue in issues:
            component = issue.component
            severity_weight = self.severity_weights[issue.severity]
            
            # Calculate base impact from severity
            base_impact = severity_weight
            
            # Calculate dependency impact (how many components depend on this one)
            dependency_impact = self._calculate_dependency_impact(component)
            
            # Combined impact score
            total_impact = base_impact * (1 + dependency_impact)
            
            if component not in impact_scores:
                impact_scores[component] = 0
            impact_scores[component] += total_impact
        
        return impact_scores
    
    def _calculate_dependency_impact(self, component: str) -> float:
        """Calculate how many components depend on this component."""
        dependent_count = 0
        
        for comp, deps in self.dependency_graph.items():
            if component in deps:
                dependent_count += 1
        
        # Normalize by total number of components
        return dependent_count / len(self.dependency_graph)
    
    def _prioritize_issues(self, issues: List[Issue], impact_assessment: Dict[str, float]) -> List[Issue]:
        """Prioritize issues based on dependencies and impact."""
        
        # Create priority groups based on dependency levels
        foundation_issues = []
        integration_issues = []
        application_issues = []
        
        for issue in issues:
            component = issue.component
            
            # Determine dependency level
            if component in ["lambda_layers", "iam_permissions"]:
                foundation_issues.append(issue)
            elif component in ["step_functions", "api_gateway", "openai_client", "dynamodb_operations"]:
                integration_issues.append(issue)
            else:
                application_issues.append(issue)
        
        # Sort each group by impact score and severity
        def sort_key(issue: Issue) -> Tuple[float, int]:
            impact_score = impact_assessment.get(issue.component, 0)
            severity_value = list(Severity).index(issue.severity)
            return (-impact_score, severity_value)  # Negative for descending order
        
        foundation_issues.sort(key=sort_key)
        integration_issues.sort(key=sort_key)
        application_issues.sort(key=sort_key)
        
        # Combine in dependency order: foundation -> integration -> application
        return foundation_issues + integration_issues + application_issues
    
    def get_blocking_issues(self, issues: List[Issue]) -> List[Issue]:
        """Get issues that are blocking other components."""
        blocking_issues = []
        
        for issue in issues:
            component = issue.component
            
            # Check if this component is a dependency for others
            is_blocking = any(
                component in deps 
                for deps in self.dependency_graph.values()
            )
            
            if is_blocking:
                blocking_issues.append(issue)
        
        return blocking_issues
    
    def get_resolution_order(self, issues: List[Issue]) -> List[List[Issue]]:
        """Get issues grouped by resolution order (parallel groups)."""
        prioritized = self._prioritize_issues(issues, self._calculate_impact_assessment(issues))
        
        # Group issues that can be resolved in parallel
        resolution_groups = []
        current_group = []
        current_dependencies = set()
        
        for issue in prioritized:
            component = issue.component
            issue_dependencies = set(self.dependency_graph.get(component, []))
            
            # If this issue has dependencies that conflict with current group, start new group
            if current_dependencies and issue_dependencies.intersection(current_dependencies):
                if current_group:
                    resolution_groups.append(current_group)
                current_group = [issue]
                current_dependencies = issue_dependencies
            else:
                current_group.append(issue)
                current_dependencies.update(issue_dependencies)
        
        if current_group:
            resolution_groups.append(current_group)
        
        return resolution_groups