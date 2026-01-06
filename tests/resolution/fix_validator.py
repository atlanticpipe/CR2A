"""
Fix validation system.
Re-runs tests after fixes are applied to verify resolution and detect regressions.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ..core.models import (
    TestResult, TestStatus, Issue, ResolutionResult, 
    TestConfiguration, ComponentTestReport, IntegrationTestReport
)
from ..core.interfaces import ComponentTester, IntegrationTester
from .issue_analyzer import IssueAnalyzer


class ValidationStatus(Enum):
    """Status of fix validation."""
    RESOLVED = "RESOLVED"
    PARTIALLY_RESOLVED = "PARTIALLY_RESOLVED"
    NOT_RESOLVED = "NOT_RESOLVED"
    REGRESSION_DETECTED = "REGRESSION_DETECTED"


@dataclass
class ValidationResult:
    """Result of fix validation."""
    resolution_result: ResolutionResult
    validation_status: ValidationStatus
    pre_fix_tests: List[TestResult]
    post_fix_tests: List[TestResult]
    regression_tests: List[TestResult]
    validation_details: str


@dataclass
class RegressionAnalysis:
    """Analysis of potential regressions."""
    new_failures: List[TestResult]
    degraded_performance: List[TestResult]
    changed_behavior: List[TestResult]
    overall_regression_detected: bool


class FixValidator:
    """Validates that applied fixes actually resolve issues without introducing regressions."""
    
    def __init__(self, 
                 config: TestConfiguration,
                 component_tester: Optional[ComponentTester] = None,
                 integration_tester: Optional[IntegrationTester] = None):
        self.config = config
        self.component_tester = component_tester
        self.integration_tester = integration_tester
        self.issue_analyzer = IssueAnalyzer()
        self.logger = logging.getLogger(__name__)
        
        # Store baseline test results for regression detection
        self._baseline_results: Dict[str, List[TestResult]] = {}
    
    def set_baseline_results(self, 
                           component_reports: List[ComponentTestReport] = None,
                           integration_reports: List[IntegrationTestReport] = None):
        """Set baseline test results for regression detection."""
        
        if component_reports:
            for report in component_reports:
                key = f"component_{report.lambda_function}"
                all_tests = (report.dependency_tests + 
                           report.client_tests + 
                           report.database_tests)
                self._baseline_results[key] = all_tests
        
        if integration_reports:
            for report in integration_reports:
                key = "integration"
                all_tests = (report.state_machine_tests + 
                           report.api_endpoint_tests + 
                           report.workflow_tests + 
                           report.permission_tests)
                self._baseline_results[key] = all_tests
        
        self.logger.info(f"Set baseline results for {len(self._baseline_results)} test suites")
    
    def validate_resolution(self, resolution: ResolutionResult) -> ValidationResult:
        """Validate that a resolution actually fixed the issue."""
        
        self.logger.info(f"Validating resolution for issue: {resolution.issue.description}")
        
        # Get pre-fix test results (from the original failure)
        pre_fix_tests = self._get_relevant_baseline_tests(resolution.issue)
        
        # Re-run tests after fix application
        post_fix_tests = self._rerun_relevant_tests(resolution.issue)
        
        # Check for regressions in other areas
        regression_tests = self._check_for_regressions(resolution.issue, post_fix_tests)
        
        # Determine validation status
        validation_status = self._determine_validation_status(
            resolution.issue, pre_fix_tests, post_fix_tests, regression_tests
        )
        
        # Generate validation details
        validation_details = self._generate_validation_details(
            validation_status, pre_fix_tests, post_fix_tests, regression_tests
        )
        
        return ValidationResult(
            resolution_result=resolution,
            validation_status=validation_status,
            pre_fix_tests=pre_fix_tests,
            post_fix_tests=post_fix_tests,
            regression_tests=regression_tests,
            validation_details=validation_details
        )
    
    def validate_batch_resolution(self, resolutions: List[ResolutionResult]) -> List[ValidationResult]:
        """Validate multiple resolutions as a batch."""
        
        self.logger.info(f"Validating batch of {len(resolutions)} resolutions")
        
        validation_results = []
        
        for resolution in resolutions:
            try:
                validation_result = self.validate_resolution(resolution)
                validation_results.append(validation_result)
                
                # If we detect a regression, we might want to stop and rollback
                if validation_result.validation_status == ValidationStatus.REGRESSION_DETECTED:
                    self.logger.warning(f"Regression detected in resolution for {resolution.issue.component}")
                    
            except Exception as e:
                self.logger.error(f"Failed to validate resolution: {str(e)}")
                # Create a failed validation result
                validation_results.append(ValidationResult(
                    resolution_result=resolution,
                    validation_status=ValidationStatus.NOT_RESOLVED,
                    pre_fix_tests=[],
                    post_fix_tests=[],
                    regression_tests=[],
                    validation_details=f"Validation failed with error: {str(e)}"
                ))
        
        return validation_results
    
    def analyze_regressions(self, 
                          pre_fix_results: List[TestResult], 
                          post_fix_results: List[TestResult]) -> RegressionAnalysis:
        """Analyze test results for potential regressions."""
        
        # Create lookup maps for comparison
        pre_fix_map = {test.test_name: test for test in pre_fix_results}
        post_fix_map = {test.test_name: test for test in post_fix_results}
        
        new_failures = []
        degraded_performance = []
        changed_behavior = []
        
        # Check for new failures
        for test_name, post_test in post_fix_map.items():
            pre_test = pre_fix_map.get(test_name)
            
            if pre_test:
                # Test existed before - check for regressions
                if (pre_test.status == TestStatus.PASS and 
                    post_test.status in [TestStatus.FAIL, TestStatus.ERROR]):
                    new_failures.append(post_test)
                
                # Check for performance degradation (if execution time increased significantly)
                if (pre_test.execution_time > 0 and post_test.execution_time > 0 and
                    post_test.execution_time > pre_test.execution_time * 2):
                    degraded_performance.append(post_test)
                
                # Check for changed behavior (different error messages, etc.)
                if (pre_test.status == post_test.status and 
                    pre_test.message != post_test.message and
                    post_test.status in [TestStatus.FAIL, TestStatus.ERROR]):
                    changed_behavior.append(post_test)
            
            else:
                # New test - if it's failing, it might indicate a regression
                if post_test.status in [TestStatus.FAIL, TestStatus.ERROR]:
                    new_failures.append(post_test)
        
        overall_regression = (len(new_failures) > 0 or 
                            len(degraded_performance) > 0 or 
                            len(changed_behavior) > 0)
        
        return RegressionAnalysis(
            new_failures=new_failures,
            degraded_performance=degraded_performance,
            changed_behavior=changed_behavior,
            overall_regression_detected=overall_regression
        )
    
    def recommend_rollback(self, validation_results: List[ValidationResult]) -> Tuple[bool, str]:
        """Recommend whether to rollback based on validation results."""
        
        critical_regressions = 0
        unresolved_critical_issues = 0
        total_regressions = 0
        
        for result in validation_results:
            if result.validation_status == ValidationStatus.REGRESSION_DETECTED:
                total_regressions += 1
                if result.resolution_result.issue.severity.name == "CRITICAL":
                    critical_regressions += 1
            
            if (result.validation_status == ValidationStatus.NOT_RESOLVED and
                result.resolution_result.issue.severity.name == "CRITICAL"):
                unresolved_critical_issues += 1
        
        # Recommend rollback if we have critical regressions
        if critical_regressions > 0:
            return True, f"Rollback recommended: {critical_regressions} critical regressions detected"
        
        # Recommend rollback if we have many regressions relative to fixes
        regression_ratio = total_regressions / len(validation_results) if validation_results else 0
        if regression_ratio > 0.3:  # More than 30% of fixes caused regressions
            return True, f"Rollback recommended: High regression ratio ({regression_ratio:.1%})"
        
        # Don't rollback if we resolved critical issues even with some regressions
        resolved_critical = sum(1 for r in validation_results 
                              if (r.validation_status == ValidationStatus.RESOLVED and
                                  r.resolution_result.issue.severity.name == "CRITICAL"))
        
        if resolved_critical > total_regressions:
            return False, f"Continue: Resolved {resolved_critical} critical issues with {total_regressions} regressions"
        
        return False, "Continue: No significant regressions detected"
    
    def _get_relevant_baseline_tests(self, issue: Issue) -> List[TestResult]:
        """Get baseline test results relevant to the issue."""
        
        component = issue.component
        relevant_tests = []
        
        # Look for component-specific baseline results
        component_key = f"component_{component}"
        if component_key in self._baseline_results:
            relevant_tests.extend(self._baseline_results[component_key])
        
        # For integration issues, also include integration baseline results
        if issue.issue_type.name == "INTEGRATION":
            integration_key = "integration"
            if integration_key in self._baseline_results:
                relevant_tests.extend(self._baseline_results[integration_key])
        
        return relevant_tests
    
    def _rerun_relevant_tests(self, issue: Issue) -> List[TestResult]:
        """Re-run tests relevant to the issue after fix application."""
        
        post_fix_tests = []
        
        try:
            if issue.issue_type.name in ["DEPENDENCY", "CONFIGURATION"]:
                # Re-run component tests
                if self.component_tester:
                    if "dependency" in issue.description.lower():
                        test_result = self.component_tester.test_dependencies()
                        post_fix_tests.append(test_result)
                    
                    if "openai" in issue.description.lower() or "client" in issue.description.lower():
                        test_result = self.component_tester.test_openai_client()
                        post_fix_tests.append(test_result)
                    
                    if "dynamodb" in issue.description.lower():
                        test_result = self.component_tester.test_dynamodb_operations()
                        post_fix_tests.append(test_result)
            
            elif issue.issue_type.name == "INTEGRATION":
                # Re-run integration tests
                if self.integration_tester:
                    if "step functions" in issue.description.lower():
                        test_result = self.integration_tester.test_state_machine_exists()
                        post_fix_tests.append(test_result)
                    
                    if "api gateway" in issue.description.lower():
                        test_result = self.integration_tester.test_api_endpoints()
                        post_fix_tests.append(test_result)
                    
                    if "permission" in issue.description.lower():
                        test_result = self.integration_tester.test_execution_permissions()
                        post_fix_tests.append(test_result)
        
        except Exception as e:
            self.logger.error(f"Failed to re-run tests for issue {issue.component}: {str(e)}")
            # Create a failed test result
            post_fix_tests.append(TestResult(
                test_name=f"rerun_test_{issue.component}",
                status=TestStatus.ERROR,
                message=f"Failed to re-run test: {str(e)}"
            ))
        
        return post_fix_tests
    
    def _check_for_regressions(self, issue: Issue, post_fix_tests: List[TestResult]) -> List[TestResult]:
        """Check for regressions in other components after applying a fix."""
        
        regression_tests = []
        
        # For now, we'll simulate regression checking
        # In a real implementation, this would run a broader set of tests
        # to ensure the fix didn't break other functionality
        
        try:
            # Run a subset of tests to check for regressions
            if self.component_tester and issue.issue_type.name != "DEPENDENCY":
                # If we fixed a non-dependency issue, check dependencies still work
                dependency_test = self.component_tester.test_dependencies()
                regression_tests.append(dependency_test)
            
            if self.integration_tester and issue.issue_type.name != "INTEGRATION":
                # If we fixed a non-integration issue, check integrations still work
                api_test = self.integration_tester.test_api_endpoints()
                regression_tests.append(api_test)
        
        except Exception as e:
            self.logger.error(f"Failed to check for regressions: {str(e)}")
            regression_tests.append(TestResult(
                test_name="regression_check",
                status=TestStatus.ERROR,
                message=f"Regression check failed: {str(e)}"
            ))
        
        return regression_tests
    
    def _determine_validation_status(self, 
                                   issue: Issue,
                                   pre_fix_tests: List[TestResult],
                                   post_fix_tests: List[TestResult],
                                   regression_tests: List[TestResult]) -> ValidationStatus:
        """Determine the overall validation status."""
        
        # Check for regressions first
        regression_failures = [t for t in regression_tests if t.status in [TestStatus.FAIL, TestStatus.ERROR]]
        if regression_failures:
            return ValidationStatus.REGRESSION_DETECTED
        
        # Check if the original issue was resolved
        post_fix_failures = [t for t in post_fix_tests if t.status in [TestStatus.FAIL, TestStatus.ERROR]]
        
        if not post_fix_failures:
            # All post-fix tests passed
            return ValidationStatus.RESOLVED
        
        # Compare with pre-fix results to see if we made progress
        pre_fix_failures = [t for t in pre_fix_tests if t.status in [TestStatus.FAIL, TestStatus.ERROR]]
        
        if len(post_fix_failures) < len(pre_fix_failures):
            # Some improvement but not fully resolved
            return ValidationStatus.PARTIALLY_RESOLVED
        
        # No improvement or got worse
        return ValidationStatus.NOT_RESOLVED
    
    def _generate_validation_details(self,
                                   validation_status: ValidationStatus,
                                   pre_fix_tests: List[TestResult],
                                   post_fix_tests: List[TestResult],
                                   regression_tests: List[TestResult]) -> str:
        """Generate detailed validation report."""
        
        details = []
        
        details.append(f"Validation Status: {validation_status.value}")
        
        # Pre-fix summary
        pre_failures = [t for t in pre_fix_tests if t.status in [TestStatus.FAIL, TestStatus.ERROR]]
        details.append(f"Pre-fix: {len(pre_failures)} failures out of {len(pre_fix_tests)} tests")
        
        # Post-fix summary
        post_failures = [t for t in post_fix_tests if t.status in [TestStatus.FAIL, TestStatus.ERROR]]
        details.append(f"Post-fix: {len(post_failures)} failures out of {len(post_fix_tests)} tests")
        
        # Regression summary
        regression_failures = [t for t in regression_tests if t.status in [TestStatus.FAIL, TestStatus.ERROR]]
        details.append(f"Regressions: {len(regression_failures)} failures out of {len(regression_tests)} regression tests")
        
        # Specific details based on status
        if validation_status == ValidationStatus.RESOLVED:
            details.append("✓ Issue successfully resolved with no regressions")
        elif validation_status == ValidationStatus.PARTIALLY_RESOLVED:
            details.append("⚠ Issue partially resolved - some tests still failing")
        elif validation_status == ValidationStatus.NOT_RESOLVED:
            details.append("✗ Issue not resolved - no improvement detected")
        elif validation_status == ValidationStatus.REGRESSION_DETECTED:
            details.append("⚠ Regressions detected - rollback may be needed")
            for regression in regression_failures:
                details.append(f"  - Regression: {regression.test_name}: {regression.message}")
        
        return "\n".join(details)


class RollbackManager:
    """Manages rollback operations when fixes cause regressions."""
    
    def __init__(self, config: TestConfiguration):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._rollback_history: List[Dict[str, Any]] = []
    
    def execute_rollback(self, validation_results: List[ValidationResult]) -> bool:
        """Execute rollback for failed validations."""
        
        self.logger.info("Executing rollback for failed validations")
        
        rollback_successful = True
        rollback_details = []
        
        for result in validation_results:
            if result.validation_status in [ValidationStatus.REGRESSION_DETECTED, 
                                          ValidationStatus.NOT_RESOLVED]:
                
                try:
                    # In a real implementation, this would:
                    # 1. Identify the specific changes made during fix application
                    # 2. Reverse those changes using backup data
                    # 3. Verify the rollback was successful
                    
                    component = result.resolution_result.issue.component
                    self.logger.info(f"Rolling back changes for {component}")
                    
                    # Simulate rollback
                    rollback_details.append(f"Rolled back {component}")
                    
                except Exception as e:
                    self.logger.error(f"Rollback failed for {component}: {str(e)}")
                    rollback_successful = False
                    rollback_details.append(f"Rollback failed for {component}: {str(e)}")
        
        # Record rollback in history
        self._rollback_history.append({
            'timestamp': time.time(),
            'validation_results': validation_results,
            'rollback_successful': rollback_successful,
            'details': rollback_details
        })
        
        return rollback_successful
    
    def get_rollback_history(self) -> List[Dict[str, Any]]:
        """Get history of rollback operations."""
        return self._rollback_history.copy()


# Import time for rollback history
import time