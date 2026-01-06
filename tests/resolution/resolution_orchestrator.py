"""
Resolution orchestrator that coordinates issue identification, fix application, and validation.
Provides a unified interface for the automated issue resolution system.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from ..core.models import (
    TestConfiguration, ComponentTestReport, IntegrationTestReport,
    Issue, ResolutionResult
)
from ..core.interfaces import ComponentTester, IntegrationTester
from .issue_analyzer import IssueAnalyzer, IssueAnalysis
from .fix_applicator import FixApplicator, FixConfiguration, BatchFixApplicator
from .fix_validator import FixValidator, ValidationResult, RollbackManager


@dataclass
class ResolutionSummary:
    """Summary of the complete resolution process."""
    total_issues_identified: int
    issues_resolved: int
    issues_partially_resolved: int
    issues_not_resolved: int
    regressions_detected: int
    rollback_executed: bool
    resolution_details: List[str]


class ResolutionOrchestrator:
    """Orchestrates the complete automated issue resolution process."""
    
    def __init__(self, 
                 config: TestConfiguration,
                 fix_config: FixConfiguration = None,
                 component_tester: Optional[ComponentTester] = None,
                 integration_tester: Optional[IntegrationTester] = None):
        
        self.config = config
        self.fix_config = fix_config or FixConfiguration()
        self.logger = logging.getLogger(__name__)
        
        # Initialize resolution components
        self.issue_analyzer = IssueAnalyzer()
        self.fix_applicator = FixApplicator(config, self.fix_config)
        self.batch_applicator = BatchFixApplicator(self.fix_applicator)
        self.fix_validator = FixValidator(config, component_tester, integration_tester)
        self.rollback_manager = RollbackManager(config)
        
        # Store testers for validation
        self.component_tester = component_tester
        self.integration_tester = integration_tester
    
    def execute_full_resolution_cycle(self,
                                    component_reports: List[ComponentTestReport] = None,
                                    integration_reports: List[IntegrationTestReport] = None) -> ResolutionSummary:
        """Execute the complete resolution cycle: analyze -> fix -> validate -> rollback if needed."""
        
        self.logger.info("Starting automated issue resolution cycle")
        
        try:
            # Step 1: Analyze test results and identify issues
            self.logger.info("Step 1: Analyzing test results and identifying issues")
            issue_analysis = self.issue_analyzer.analyze_test_results(
                component_reports=component_reports,
                integration_reports=integration_reports
            )
            
            if not issue_analysis.issues:
                self.logger.info("No issues identified - resolution cycle complete")
                return ResolutionSummary(
                    total_issues_identified=0,
                    issues_resolved=0,
                    issues_partially_resolved=0,
                    issues_not_resolved=0,
                    regressions_detected=0,
                    rollback_executed=False,
                    resolution_details=["No issues identified"]
                )
            
            self.logger.info(f"Identified {len(issue_analysis.issues)} issues")
            
            # Step 2: Set baseline for regression detection
            self.logger.info("Step 2: Setting baseline for regression detection")
            self.fix_validator.set_baseline_results(component_reports, integration_reports)
            
            # Step 3: Apply fixes in priority order
            self.logger.info("Step 3: Applying fixes in priority order")
            resolution_groups = self.issue_analyzer.get_resolution_order(issue_analysis.issues)
            
            all_resolution_results = self.batch_applicator.apply_fixes_in_order(resolution_groups)
            
            # Flatten results
            all_resolutions = []
            for group_results in all_resolution_results:
                all_resolutions.extend(group_results)
            
            self.logger.info(f"Applied {len(all_resolutions)} fixes")
            
            # Step 4: Validate fixes and check for regressions
            self.logger.info("Step 4: Validating fixes and checking for regressions")
            validation_results = self.fix_validator.validate_batch_resolution(all_resolutions)
            
            # Step 5: Analyze validation results and decide on rollback
            self.logger.info("Step 5: Analyzing validation results")
            should_rollback, rollback_reason = self.fix_validator.recommend_rollback(validation_results)
            
            rollback_executed = False
            if should_rollback:
                self.logger.warning(f"Rollback recommended: {rollback_reason}")
                rollback_executed = self.rollback_manager.execute_rollback(validation_results)
                if rollback_executed:
                    self.logger.info("Rollback completed successfully")
                else:
                    self.logger.error("Rollback failed")
            
            # Step 6: Generate summary
            summary = self._generate_resolution_summary(
                issue_analysis, validation_results, rollback_executed
            )
            
            self.logger.info("Automated issue resolution cycle completed")
            return summary
            
        except Exception as e:
            self.logger.error(f"Resolution cycle failed with error: {str(e)}")
            return ResolutionSummary(
                total_issues_identified=0,
                issues_resolved=0,
                issues_partially_resolved=0,
                issues_not_resolved=0,
                regressions_detected=0,
                rollback_executed=False,
                resolution_details=[f"Resolution cycle failed: {str(e)}"]
            )
    
    def execute_targeted_resolution(self, specific_issues: List[Issue]) -> ResolutionSummary:
        """Execute resolution for specific issues only."""
        
        self.logger.info(f"Starting targeted resolution for {len(specific_issues)} issues")
        
        try:
            # Apply fixes for specific issues
            all_resolutions = []
            
            for issue in specific_issues:
                if issue.issue_type.name == "DEPENDENCY":
                    results = self.fix_applicator.resolve_dependency_issues([issue])
                elif issue.issue_type.name == "CONFIGURATION":
                    results = self.fix_applicator.resolve_configuration_issues([issue])
                elif issue.issue_type.name == "INTEGRATION":
                    results = self.fix_applicator.resolve_integration_issues([issue])
                else:
                    results = [ResolutionResult(
                        issue=issue,
                        resolution_applied=False,
                        resolution_details=f"No handler for issue type {issue.issue_type}"
                    )]
                
                all_resolutions.extend(results)
            
            # Validate fixes
            validation_results = self.fix_validator.validate_batch_resolution(all_resolutions)
            
            # Check for rollback need
            should_rollback, rollback_reason = self.fix_validator.recommend_rollback(validation_results)
            
            rollback_executed = False
            if should_rollback:
                rollback_executed = self.rollback_manager.execute_rollback(validation_results)
            
            # Create mock issue analysis for summary generation
            issue_analysis = IssueAnalysis(
                issues=specific_issues,
                dependency_graph={},
                priority_order=specific_issues,
                impact_assessment={}
            )
            
            summary = self._generate_resolution_summary(
                issue_analysis, validation_results, rollback_executed
            )
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Targeted resolution failed: {str(e)}")
            return ResolutionSummary(
                total_issues_identified=len(specific_issues),
                issues_resolved=0,
                issues_partially_resolved=0,
                issues_not_resolved=len(specific_issues),
                regressions_detected=0,
                rollback_executed=False,
                resolution_details=[f"Targeted resolution failed: {str(e)}"]
            )
    
    def get_issue_analysis_only(self,
                               component_reports: List[ComponentTestReport] = None,
                               integration_reports: List[IntegrationTestReport] = None) -> IssueAnalysis:
        """Get issue analysis without applying fixes (for planning purposes)."""
        
        return self.issue_analyzer.analyze_test_results(
            component_reports=component_reports,
            integration_reports=integration_reports
        )
    
    def get_blocking_issues(self,
                           component_reports: List[ComponentTestReport] = None,
                           integration_reports: List[IntegrationTestReport] = None) -> List[Issue]:
        """Get issues that are blocking other components."""
        
        issue_analysis = self.get_issue_analysis_only(component_reports, integration_reports)
        return self.issue_analyzer.get_blocking_issues(issue_analysis.issues)
    
    def _generate_resolution_summary(self,
                                   issue_analysis: IssueAnalysis,
                                   validation_results: List[ValidationResult],
                                   rollback_executed: bool) -> ResolutionSummary:
        """Generate summary of the resolution process."""
        
        from .fix_validator import ValidationStatus
        
        # Count validation results by status
        resolved_count = sum(1 for r in validation_results 
                           if r.validation_status == ValidationStatus.RESOLVED)
        
        partially_resolved_count = sum(1 for r in validation_results 
                                     if r.validation_status == ValidationStatus.PARTIALLY_RESOLVED)
        
        not_resolved_count = sum(1 for r in validation_results 
                               if r.validation_status == ValidationStatus.NOT_RESOLVED)
        
        regressions_count = sum(1 for r in validation_results 
                              if r.validation_status == ValidationStatus.REGRESSION_DETECTED)
        
        # Generate detailed resolution information
        resolution_details = []
        resolution_details.append(f"Total issues identified: {len(issue_analysis.issues)}")
        resolution_details.append(f"Issues resolved: {resolved_count}")
        resolution_details.append(f"Issues partially resolved: {partially_resolved_count}")
        resolution_details.append(f"Issues not resolved: {not_resolved_count}")
        resolution_details.append(f"Regressions detected: {regressions_count}")
        
        if rollback_executed:
            resolution_details.append("Rollback was executed due to regressions")
        
        # Add priority information
        blocking_issues = self.issue_analyzer.get_blocking_issues(issue_analysis.issues)
        if blocking_issues:
            resolution_details.append(f"Blocking issues identified: {len(blocking_issues)}")
        
        # Add impact assessment summary
        if issue_analysis.impact_assessment:
            high_impact_components = [comp for comp, impact in issue_analysis.impact_assessment.items() 
                                    if impact > 0.7]
            if high_impact_components:
                resolution_details.append(f"High-impact components: {', '.join(high_impact_components)}")
        
        return ResolutionSummary(
            total_issues_identified=len(issue_analysis.issues),
            issues_resolved=resolved_count,
            issues_partially_resolved=partially_resolved_count,
            issues_not_resolved=not_resolved_count,
            regressions_detected=regressions_count,
            rollback_executed=rollback_executed,
            resolution_details=resolution_details
        )
    
    def generate_resolution_report(self, summary: ResolutionSummary) -> str:
        """Generate a human-readable resolution report."""
        
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("AUTOMATED ISSUE RESOLUTION REPORT")
        report_lines.append("=" * 60)
        report_lines.append("")
        
        # Summary statistics
        report_lines.append("SUMMARY:")
        report_lines.append(f"  Total Issues Identified: {summary.total_issues_identified}")
        report_lines.append(f"  Issues Resolved: {summary.issues_resolved}")
        report_lines.append(f"  Issues Partially Resolved: {summary.issues_partially_resolved}")
        report_lines.append(f"  Issues Not Resolved: {summary.issues_not_resolved}")
        report_lines.append(f"  Regressions Detected: {summary.regressions_detected}")
        report_lines.append(f"  Rollback Executed: {'Yes' if summary.rollback_executed else 'No'}")
        report_lines.append("")
        
        # Success rate calculation
        if summary.total_issues_identified > 0:
            success_rate = (summary.issues_resolved / summary.total_issues_identified) * 100
            report_lines.append(f"SUCCESS RATE: {success_rate:.1f}%")
        else:
            report_lines.append("SUCCESS RATE: N/A (No issues identified)")
        
        report_lines.append("")
        
        # Detailed information
        report_lines.append("DETAILS:")
        for detail in summary.resolution_details:
            report_lines.append(f"  • {detail}")
        
        report_lines.append("")
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)