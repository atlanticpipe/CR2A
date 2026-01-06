"""
Main automation manager for the CR2A testing framework.
Coordinates test orchestration, scheduling, and reporting.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import schedule
import time

from .automation_orchestrator import CR2ATestOrchestrator
from .automation_reporter import CR2ATestReporter, ReportExporter
from ..core.models import TestConfiguration, TestSuite
from ..core.config import ConfigurationManager


class CR2AAutomationManager:
    """Main automation manager for coordinating all testing activities."""
    
    def __init__(self, config: TestConfiguration):
        self.config = config
        self.logger = logging.getLogger("cr2a_testing.automation_manager")
        
        # Initialize components
        self.orchestrator = CR2ATestOrchestrator(config)
        self.reporter = CR2ATestReporter(config.artifact_path)
        self.exporter = ReportExporter(config.artifact_path)
        
        # Scheduling state
        self._scheduled_jobs = []
        self._is_running = False
    
    def run_tests(self, test_types: List[str] = None, generate_reports: bool = True) -> List[TestSuite]:
        """Run tests based on specified types."""
        if test_types is None:
            test_types = ['component', 'integration']
        
        self.logger.info(f"Starting test execution with types: {test_types}")
        
        test_suites = []
        
        try:
            if 'component' in test_types and 'integration' in test_types:
                # Run full test suite
                test_suites = self.orchestrator.run_full_test_suite(self.config)
            elif 'component' in test_types:
                # Run only component tests
                component_suite = self.orchestrator.run_component_tests(self.config)
                test_suites = [component_suite]
            elif 'integration' in test_types:
                # Run only integration tests
                integration_suite = self.orchestrator.run_integration_tests(self.config)
                test_suites = [integration_suite]
            else:
                self.logger.warning(f"No valid test types specified: {test_types}")
                return []
            
            # Generate reports if requested
            if generate_reports and test_suites:
                self._generate_all_reports(test_suites)
            
            # Log summary
            summary = self.orchestrator.generate_summary_report(test_suites)
            self.logger.info(f"Test execution completed. Overall status: {summary['overall_status']}")
            
            return test_suites
            
        except Exception as e:
            self.logger.error(f"Test execution failed: {str(e)}")
            raise
    
    def schedule_tests(self, schedule_config: Dict[str, Any]) -> None:
        """Schedule automated test execution."""
        self.logger.info(f"Setting up test scheduling with config: {schedule_config}")
        
        # Clear existing schedules
        self.clear_scheduled_tests()
        
        # Parse schedule configuration
        interval_type = schedule_config.get('interval_type', 'hours')  # hours, days, weeks
        interval_value = schedule_config.get('interval_value', 1)
        test_types = schedule_config.get('test_types', ['component', 'integration'])
        start_time = schedule_config.get('start_time', '09:00')  # HH:MM format
        
        # Create scheduled job
        if interval_type == 'hours':
            job = schedule.every(interval_value).hours.do(
                self._scheduled_test_run, test_types
            )
        elif interval_type == 'days':
            job = schedule.every(interval_value).days.at(start_time).do(
                self._scheduled_test_run, test_types
            )
        elif interval_type == 'weeks':
            day_of_week = schedule_config.get('day_of_week', 'monday')
            job = getattr(schedule.every(interval_value), day_of_week).at(start_time).do(
                self._scheduled_test_run, test_types
            )
        else:
            raise ValueError(f"Unsupported interval type: {interval_type}")
        
        self._scheduled_jobs.append(job)
        self.logger.info(f"Scheduled test execution every {interval_value} {interval_type}")
    
    def start_scheduler(self) -> None:
        """Start the test scheduler daemon."""
        if self._is_running:
            self.logger.warning("Scheduler is already running")
            return
        
        self._is_running = True
        self.logger.info("Starting test scheduler daemon")
        
        try:
            while self._is_running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            self.logger.info("Scheduler stopped by user")
        finally:
            self._is_running = False
    
    def stop_scheduler(self) -> None:
        """Stop the test scheduler daemon."""
        self.logger.info("Stopping test scheduler daemon")
        self._is_running = False
    
    def clear_scheduled_tests(self) -> None:
        """Clear all scheduled test jobs."""
        for job in self._scheduled_jobs:
            schedule.cancel_job(job)
        self._scheduled_jobs.clear()
        self.logger.info("Cleared all scheduled test jobs")
    
    def run_triggered_tests(self, trigger_config: Dict[str, Any]) -> List[TestSuite]:
        """Run tests based on external triggers (webhooks, file changes, etc.)."""
        self.logger.info(f"Running triggered tests with config: {trigger_config}")
        
        trigger_type = trigger_config.get('trigger_type', 'manual')
        test_types = trigger_config.get('test_types', ['component', 'integration'])
        
        # Add trigger metadata to test configuration
        trigger_metadata = {
            'trigger_type': trigger_type,
            'trigger_time': datetime.now().isoformat(),
            'trigger_config': trigger_config
        }
        
        # Run tests
        test_suites = self.run_tests(test_types, generate_reports=True)
        
        # Add trigger metadata to test results
        for suite in test_suites:
            if not hasattr(suite, 'metadata'):
                suite.metadata = {}
            suite.metadata.update(trigger_metadata)
        
        return test_suites
    
    def generate_historical_report(self, days_back: int = 7) -> str:
        """Generate a historical report of test results."""
        self.logger.info(f"Generating historical report for last {days_back} days")
        
        # This would typically read from a test results database
        # For now, we'll look for JSON reports in the artifacts directory
        historical_data = self._collect_historical_data(days_back)
        
        if not historical_data:
            self.logger.warning("No historical data found")
            return ""
        
        # Generate historical report
        report_path = os.path.join(
            self.config.artifact_path,
            f"historical_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        )
        
        self._generate_historical_html_report(historical_data, report_path)
        
        self.logger.info(f"Historical report generated: {report_path}")
        return report_path
    
    def export_test_metrics(self, format_type: str = 'json') -> str:
        """Export test metrics for external monitoring systems."""
        self.logger.info(f"Exporting test metrics in {format_type} format")
        
        # Collect recent test data
        historical_data = self._collect_historical_data(days_back=1)
        
        if not historical_data:
            self.logger.warning("No recent test data found for metrics export")
            return ""
        
        # Calculate metrics
        metrics = self._calculate_test_metrics(historical_data)
        
        # Export based on format
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format_type == 'json':
            metrics_path = os.path.join(
                self.config.artifact_path,
                f"test_metrics_{timestamp}.json"
            )
            with open(metrics_path, 'w') as f:
                json.dump(metrics, f, indent=2)
        
        elif format_type == 'prometheus':
            metrics_path = os.path.join(
                self.config.artifact_path,
                f"test_metrics_{timestamp}.prom"
            )
            self._export_prometheus_metrics(metrics, metrics_path)
        
        else:
            raise ValueError(f"Unsupported metrics format: {format_type}")
        
        self.logger.info(f"Test metrics exported: {metrics_path}")
        return metrics_path
    
    def _scheduled_test_run(self, test_types: List[str]) -> None:
        """Internal method for scheduled test execution."""
        try:
            self.logger.info(f"Running scheduled tests: {test_types}")
            test_suites = self.run_tests(test_types, generate_reports=True)
            
            # Send notifications if configured
            self._send_notifications(test_suites)
            
        except Exception as e:
            self.logger.error(f"Scheduled test run failed: {str(e)}")
    
    def _generate_all_reports(self, test_suites: List[TestSuite]) -> Dict[str, str]:
        """Generate all report formats."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"cr2a_test_report_{timestamp}"
        
        # Generate standard reports
        report_paths = self.reporter.generate_all_reports(test_suites, base_filename)
        
        # Generate additional exports
        csv_path = self.exporter.export_to_csv(test_suites, f"{base_filename}.csv")
        junit_path = self.exporter.export_junit_xml(test_suites, f"{base_filename}.xml")
        
        report_paths['csv'] = csv_path
        report_paths['junit'] = junit_path
        
        return report_paths
    
    def _collect_historical_data(self, days_back: int) -> List[Dict[str, Any]]:
        """Collect historical test data from artifacts directory."""
        historical_data = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Look for JSON report files
        for filename in os.listdir(self.config.artifact_path):
            if filename.startswith('cr2a_test_report_') and filename.endswith('.json'):
                file_path = os.path.join(self.config.artifact_path, filename)
                
                # Check file modification time
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_mtime >= cutoff_date:
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            historical_data.append(data)
                    except Exception as e:
                        self.logger.warning(f"Failed to read historical data from {filename}: {str(e)}")
        
        return sorted(historical_data, key=lambda x: x.get('timestamp', ''))
    
    def _generate_historical_html_report(self, historical_data: List[Dict[str, Any]], output_path: str) -> None:
        """Generate HTML report for historical test data."""
        # This would generate a comprehensive historical report
        # For now, we'll create a simple summary
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>CR2A Historical Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .summary {{ background: #f8f9fa; padding: 15px; margin-bottom: 20px; }}
                .data-point {{ margin: 10px 0; padding: 10px; border-left: 3px solid #007bff; }}
            </style>
        </head>
        <body>
            <h1>CR2A Historical Test Report</h1>
            <div class="summary">
                <h2>Summary</h2>
                <p>Historical data points: {len(historical_data)}</p>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <div class="data">
                <h2>Test Execution History</h2>
        """
        
        for data in historical_data:
            summary = data.get('summary', {})
            html_content += f"""
                <div class="data-point">
                    <strong>Timestamp:</strong> {data.get('timestamp', 'Unknown')}<br>
                    <strong>Status:</strong> {summary.get('overall_status', 'Unknown')}<br>
                    <strong>Tests:</strong> {summary.get('total_tests', 0)} 
                    (Pass Rate: {summary.get('pass_rate', 0):.1f}%)<br>
                    <strong>Execution Time:</strong> {summary.get('total_time', 0):.2f}s
                </div>
            """
        
        html_content += """
            </div>
        </body>
        </html>
        """
        
        with open(output_path, 'w') as f:
            f.write(html_content)
    
    def _calculate_test_metrics(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate test metrics from historical data."""
        if not historical_data:
            return {}
        
        # Calculate basic metrics
        total_runs = len(historical_data)
        successful_runs = sum(1 for data in historical_data 
                            if data.get('summary', {}).get('overall_status') == 'PASS')
        
        avg_pass_rate = sum(data.get('summary', {}).get('pass_rate', 0) 
                          for data in historical_data) / total_runs if total_runs > 0 else 0
        
        avg_execution_time = sum(data.get('summary', {}).get('total_time', 0) 
                               for data in historical_data) / total_runs if total_runs > 0 else 0
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_runs': total_runs,
            'successful_runs': successful_runs,
            'success_rate': (successful_runs / total_runs * 100) if total_runs > 0 else 0,
            'average_pass_rate': avg_pass_rate,
            'average_execution_time': avg_execution_time,
            'data_points': len(historical_data)
        }
    
    def _export_prometheus_metrics(self, metrics: Dict[str, Any], output_path: str) -> None:
        """Export metrics in Prometheus format."""
        prometheus_content = f"""# HELP cr2a_test_runs_total Total number of test runs
# TYPE cr2a_test_runs_total counter
cr2a_test_runs_total {metrics.get('total_runs', 0)}

# HELP cr2a_test_success_rate Test success rate percentage
# TYPE cr2a_test_success_rate gauge
cr2a_test_success_rate {metrics.get('success_rate', 0)}

# HELP cr2a_test_pass_rate Average test pass rate percentage
# TYPE cr2a_test_pass_rate gauge
cr2a_test_pass_rate {metrics.get('average_pass_rate', 0)}

# HELP cr2a_test_execution_time_seconds Average test execution time in seconds
# TYPE cr2a_test_execution_time_seconds gauge
cr2a_test_execution_time_seconds {metrics.get('average_execution_time', 0)}
"""
        
        with open(output_path, 'w') as f:
            f.write(prometheus_content)
    
    def _send_notifications(self, test_suites: List[TestSuite]) -> None:
        """Send notifications about test results (placeholder for future implementation)."""
        # This would integrate with notification systems like Slack, email, etc.
        summary = self.orchestrator.generate_summary_report(test_suites)
        self.logger.info(f"Test notification: Status={summary['overall_status']}, "
                        f"Pass Rate={summary['pass_rate']:.1f}%")