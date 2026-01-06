"""
Test reporting system for the CR2A testing framework.
Generates detailed test reports in multiple formats (HTML, JSON, console).
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any
from jinja2 import Template
import logging

from ..core.interfaces import TestReporter
from ..core.models import TestSuite, TestResult, TestStatus
from ..core.base import BaseTestFramework


class CR2ATestReporter(TestReporter):
    """Implementation of test reporting for CR2A testing framework."""
    
    def __init__(self, output_dir: str = "./test-artifacts"):
        self.output_dir = output_dir
        self.logger = logging.getLogger("cr2a_testing.reporter")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_html_report(self, test_suites: List[TestSuite], output_path: str) -> str:
        """Generate HTML test report."""
        self.logger.info(f"Generating HTML report at {output_path}")
        
        # Calculate summary statistics
        summary = self._calculate_summary_stats(test_suites)
        
        # HTML template
        html_template = Template("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CR2A Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .summary-card { background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; }
        .summary-card h3 { margin: 0 0 10px 0; color: #333; }
        .summary-card .value { font-size: 24px; font-weight: bold; }
        .pass { color: #28a745; }
        .fail { color: #dc3545; }
        .error { color: #fd7e14; }
        .skip { color: #6c757d; }
        .test-suite { margin-bottom: 30px; border: 1px solid #dee2e6; border-radius: 6px; }
        .test-suite-header { background: #e9ecef; padding: 15px; border-bottom: 1px solid #dee2e6; }
        .test-suite-header h2 { margin: 0; color: #333; }
        .test-suite-meta { font-size: 14px; color: #666; margin-top: 5px; }
        .test-results { padding: 15px; }
        .test-result { display: flex; justify-content: space-between; align-items: center; padding: 10px; margin-bottom: 10px; border-radius: 4px; }
        .test-result.pass { background: #d4edda; border-left: 4px solid #28a745; }
        .test-result.fail { background: #f8d7da; border-left: 4px solid #dc3545; }
        .test-result.error { background: #ffeaa7; border-left: 4px solid #fd7e14; }
        .test-result.skip { background: #e2e3e5; border-left: 4px solid #6c757d; }
        .test-name { font-weight: bold; }
        .test-message { font-size: 14px; color: #666; margin-top: 5px; }
        .test-details { font-size: 12px; color: #888; }
        .execution-time { font-size: 12px; color: #666; }
        .footer { text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>CR2A Testing Framework Report</h1>
            <p>Generated on {{ timestamp }}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Overall Status</h3>
                <div class="value {{ summary.overall_status.lower() }}">{{ summary.overall_status }}</div>
            </div>
            <div class="summary-card">
                <h3>Test Suites</h3>
                <div class="value">{{ summary.total_suites }}</div>
            </div>
            <div class="summary-card">
                <h3>Total Tests</h3>
                <div class="value">{{ summary.total_tests }}</div>
            </div>
            <div class="summary-card">
                <h3>Pass Rate</h3>
                <div class="value pass">{{ "%.1f"|format(summary.pass_rate) }}%</div>
            </div>
            <div class="summary-card">
                <h3>Execution Time</h3>
                <div class="value">{{ "%.2f"|format(summary.total_time) }}s</div>
            </div>
        </div>
        
        {% for suite in test_suites %}
        <div class="test-suite">
            <div class="test-suite-header">
                <h2>{{ suite.name }}</h2>
                <div class="test-suite-meta">
                    {{ suite.description }} | 
                    Status: <span class="{{ suite.overall_status.value.lower() }}">{{ suite.overall_status.value }}</span> | 
                    Tests: {{ suite.tests|length }} | 
                    Pass Rate: {{ "%.1f"|format(suite.get_pass_rate()) }}% | 
                    Time: {{ "%.2f"|format(suite.execution_time) }}s
                </div>
            </div>
            <div class="test-results">
                {% for test in suite.tests %}
                <div class="test-result {{ test.status.value.lower() }}">
                    <div>
                        <div class="test-name">{{ test.test_name }}</div>
                        <div class="test-message">{{ test.message }}</div>
                        {% if test.details %}
                        <div class="test-details">Details: {{ test.details }}</div>
                        {% endif %}
                    </div>
                    <div class="execution-time">{{ "%.3f"|format(test.execution_time) }}s</div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endfor %}
        
        <div class="footer">
            <p>CR2A Testing Framework - Contract Review and Analysis Testing Suite</p>
        </div>
    </div>
</body>
</html>
        """)
        
        # Render the template
        html_content = html_template.render(
            test_suites=test_suites,
            summary=summary,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        
        # Write to file
        full_path = os.path.join(self.output_dir, output_path)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"HTML report generated successfully at {full_path}")
        return full_path
    
    def generate_json_report(self, test_suites: List[TestSuite], output_path: str) -> str:
        """Generate JSON test report."""
        self.logger.info(f"Generating JSON report at {output_path}")
        
        # Convert test suites to serializable format
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": self._calculate_summary_stats(test_suites),
            "test_suites": []
        }
        
        for suite in test_suites:
            suite_data = {
                "name": suite.name,
                "description": suite.description,
                "overall_status": suite.overall_status.value,
                "execution_time": suite.execution_time,
                "timestamp": suite.timestamp.isoformat() if suite.timestamp else None,
                "pass_rate": suite.get_pass_rate(),
                "tests": []
            }
            
            for test in suite.tests:
                test_data = {
                    "test_name": test.test_name,
                    "status": test.status.value,
                    "message": test.message,
                    "details": test.details,
                    "execution_time": test.execution_time,
                    "timestamp": test.timestamp.isoformat() if test.timestamp else None
                }
                suite_data["tests"].append(test_data)
            
            report_data["test_suites"].append(suite_data)
        
        # Write to file
        full_path = os.path.join(self.output_dir, output_path)
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"JSON report generated successfully at {full_path}")
        return full_path
    
    def generate_console_summary(self, test_suites: List[TestSuite]) -> str:
        """Generate console-friendly test summary."""
        summary = self._calculate_summary_stats(test_suites)
        
        lines = []
        lines.append("=" * 80)
        lines.append("CR2A TESTING FRAMEWORK - SUMMARY REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("")
        
        # Overall summary
        lines.append("OVERALL SUMMARY:")
        lines.append(f"  Status: {summary['overall_status']}")
        lines.append(f"  Test Suites: {summary['total_suites']}")
        lines.append(f"  Total Tests: {summary['total_tests']}")
        lines.append(f"  Passed: {summary['total_passed']} ({summary['pass_rate']:.1f}%)")
        lines.append(f"  Failed: {summary['total_failed']}")
        lines.append(f"  Errors: {summary['total_errors']}")
        lines.append(f"  Skipped: {summary['total_skipped']}")
        lines.append(f"  Total Time: {summary['total_time']:.2f}s")
        lines.append("")
        
        # Test suite details
        lines.append("TEST SUITE DETAILS:")
        lines.append("-" * 80)
        
        for suite in test_suites:
            status_symbol = self._get_status_symbol(suite.overall_status)
            lines.append(f"{status_symbol} {suite.name}")
            lines.append(f"    Description: {suite.description}")
            lines.append(f"    Status: {suite.overall_status.value}")
            lines.append(f"    Tests: {len(suite.tests)} | Pass Rate: {suite.get_pass_rate():.1f}% | Time: {suite.execution_time:.2f}s")
            
            # Show failed/error tests
            failed_tests = [test for test in suite.tests if test.status in [TestStatus.FAIL, TestStatus.ERROR]]
            if failed_tests:
                lines.append("    Failed/Error Tests:")
                for test in failed_tests:
                    test_symbol = self._get_status_symbol(test.status)
                    lines.append(f"      {test_symbol} {test.test_name}: {test.message}")
            
            lines.append("")
        
        lines.append("=" * 80)
        
        console_output = "\n".join(lines)
        
        # Also save to file
        console_file = os.path.join(self.output_dir, "console_summary.txt")
        with open(console_file, 'w', encoding='utf-8') as f:
            f.write(console_output)
        
        return console_output
    
    def generate_all_reports(self, test_suites: List[TestSuite], base_filename: str = None) -> Dict[str, str]:
        """Generate all report formats and return file paths."""
        if base_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"cr2a_test_report_{timestamp}"
        
        report_paths = {}
        
        # Generate HTML report
        html_path = self.generate_html_report(test_suites, f"{base_filename}.html")
        report_paths['html'] = html_path
        
        # Generate JSON report
        json_path = self.generate_json_report(test_suites, f"{base_filename}.json")
        report_paths['json'] = json_path
        
        # Generate console summary
        console_summary = self.generate_console_summary(test_suites)
        report_paths['console'] = os.path.join(self.output_dir, "console_summary.txt")
        
        self.logger.info(f"All reports generated successfully in {self.output_dir}")
        return report_paths
    
    def generate_comprehensive_report(self) -> str:
        """Generate comprehensive test report with all available test data."""
        self.logger.info("Generating comprehensive test report...")
        
        # Try to load existing test results from artifacts directory
        test_suites = []
        
        # Look for recent test result files
        import glob
        json_files = glob.glob(os.path.join(self.output_dir, "cr2a_test_report_*.json"))
        
        if json_files:
            # Use the most recent report file
            latest_file = max(json_files, key=os.path.getctime)
            self.logger.info(f"Loading test data from {latest_file}")
            
            try:
                with open(latest_file, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                
                # Convert JSON data back to TestSuite objects
                from ..core.models import TestSuite, TestResult, TestStatus
                
                for suite_data in report_data.get("test_suites", []):
                    tests = []
                    for test_data in suite_data.get("tests", []):
                        test_result = TestResult(
                            test_name=test_data["test_name"],
                            status=TestStatus(test_data["status"]),
                            message=test_data["message"],
                            details=test_data.get("details"),
                            execution_time=test_data.get("execution_time", 0.0)
                        )
                        if test_data.get("timestamp"):
                            test_result.timestamp = datetime.fromisoformat(test_data["timestamp"])
                        tests.append(test_result)
                    
                    test_suite = TestSuite(
                        name=suite_data["name"],
                        description=suite_data["description"],
                        tests=tests,
                        overall_status=TestStatus(suite_data["overall_status"]),
                        execution_time=suite_data["execution_time"]
                    )
                    if suite_data.get("timestamp"):
                        test_suite.timestamp = datetime.fromisoformat(suite_data["timestamp"])
                    
                    test_suites.append(test_suite)
                    
            except Exception as e:
                self.logger.warning(f"Failed to load existing test data: {e}")
        
        # If no existing data, create a placeholder suite
        if not test_suites:
            self.logger.info("No existing test data found, creating placeholder report")
            from ..core.models import TestSuite, TestResult, TestStatus
            
            placeholder_test = TestResult(
                test_name="No test data available",
                status=TestStatus.SKIP,
                message="Run tests first to generate comprehensive report",
                execution_time=0.0
            )
            
            placeholder_suite = TestSuite(
                name="CR2A Test Framework",
                description="No test results available - run tests to populate this report",
                tests=[placeholder_test],
                overall_status=TestStatus.SKIP,
                execution_time=0.0
            )
            
            test_suites = [placeholder_suite]
        
        # Generate all report formats
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"comprehensive_report_{timestamp}"
        
        report_paths = self.generate_all_reports(test_suites, base_filename)
        
        # Return the HTML report path as the primary output
        html_path = report_paths.get('html')
        if html_path and os.path.exists(html_path):
            self.logger.info(f"Comprehensive report generated: {html_path}")
            return html_path
        else:
            self.logger.error("Failed to generate comprehensive HTML report")
            return None
    
    def _calculate_summary_stats(self, test_suites: List[TestSuite]) -> Dict[str, Any]:
        """Calculate summary statistics across all test suites."""
        total_tests = sum(len(suite.tests) for suite in test_suites)
        total_passed = sum(
            len([test for test in suite.tests if test.status == TestStatus.PASS])
            for suite in test_suites
        )
        total_failed = sum(
            len([test for test in suite.tests if test.status == TestStatus.FAIL])
            for suite in test_suites
        )
        total_errors = sum(
            len([test for test in suite.tests if test.status == TestStatus.ERROR])
            for suite in test_suites
        )
        total_skipped = sum(
            len([test for test in suite.tests if test.status == TestStatus.SKIP])
            for suite in test_suites
        )
        
        total_time = sum(suite.execution_time for suite in test_suites)
        
        # Determine overall status
        if total_errors > 0:
            overall_status = "ERROR"
        elif total_failed > 0:
            overall_status = "FAIL"
        elif total_passed > 0:
            overall_status = "PASS"
        else:
            overall_status = "SKIP"
        
        pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0.0
        
        return {
            "overall_status": overall_status,
            "total_suites": len(test_suites),
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_errors": total_errors,
            "total_skipped": total_skipped,
            "pass_rate": pass_rate,
            "total_time": total_time
        }
    
    def _get_status_symbol(self, status: TestStatus) -> str:
        """Get console symbol for test status."""
        symbols = {
            TestStatus.PASS: "✓",
            TestStatus.FAIL: "✗",
            TestStatus.ERROR: "⚠",
            TestStatus.SKIP: "○"
        }
        return symbols.get(status, "?")


class ReportExporter:
    """Utility class for exporting reports to different formats and destinations."""
    
    def __init__(self, output_dir: str = "./test-artifacts"):
        self.output_dir = output_dir
        self.logger = logging.getLogger("cr2a_testing.report_exporter")
    
    def export_to_csv(self, test_suites: List[TestSuite], filename: str = "test_results.csv") -> str:
        """Export test results to CSV format."""
        import csv
        
        csv_path = os.path.join(self.output_dir, filename)
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'test_suite', 'test_name', 'status', 'message', 
                'execution_time', 'timestamp'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for suite in test_suites:
                for test in suite.tests:
                    writer.writerow({
                        'test_suite': suite.name,
                        'test_name': test.test_name,
                        'status': test.status.value,
                        'message': test.message,
                        'execution_time': test.execution_time,
                        'timestamp': test.timestamp.isoformat() if test.timestamp else ''
                    })
        
        self.logger.info(f"CSV export completed: {csv_path}")
        return csv_path
    
    def export_junit_xml(self, test_suites: List[TestSuite], filename: str = "junit_results.xml") -> str:
        """Export test results in JUnit XML format for CI/CD integration."""
        from xml.etree.ElementTree import Element, SubElement, tostring
        from xml.dom import minidom
        
        # Create root testsuites element
        testsuites = Element('testsuites')
        testsuites.set('name', 'CR2A Testing Framework')
        testsuites.set('timestamp', datetime.now().isoformat())
        
        total_tests = 0
        total_failures = 0
        total_errors = 0
        total_time = 0.0
        
        for suite in test_suites:
            testsuite = SubElement(testsuites, 'testsuite')
            testsuite.set('name', suite.name)
            testsuite.set('tests', str(len(suite.tests)))
            testsuite.set('time', str(suite.execution_time))
            testsuite.set('timestamp', suite.timestamp.isoformat() if suite.timestamp else '')
            
            suite_failures = 0
            suite_errors = 0
            
            for test in suite.tests:
                testcase = SubElement(testsuite, 'testcase')
                testcase.set('name', test.test_name)
                testcase.set('time', str(test.execution_time))
                testcase.set('classname', suite.name.replace(' ', '_'))
                
                if test.status == TestStatus.FAIL:
                    failure = SubElement(testcase, 'failure')
                    failure.set('message', test.message)
                    if test.details:
                        failure.text = str(test.details)
                    suite_failures += 1
                elif test.status == TestStatus.ERROR:
                    error = SubElement(testcase, 'error')
                    error.set('message', test.message)
                    if test.details:
                        error.text = str(test.details)
                    suite_errors += 1
                elif test.status == TestStatus.SKIP:
                    skipped = SubElement(testcase, 'skipped')
                    skipped.set('message', test.message)
            
            testsuite.set('failures', str(suite_failures))
            testsuite.set('errors', str(suite_errors))
            
            total_tests += len(suite.tests)
            total_failures += suite_failures
            total_errors += suite_errors
            total_time += suite.execution_time
        
        testsuites.set('tests', str(total_tests))
        testsuites.set('failures', str(total_failures))
        testsuites.set('errors', str(total_errors))
        testsuites.set('time', str(total_time))
        
        # Pretty print XML
        rough_string = tostring(testsuites, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ")
        
        # Write to file
        xml_path = os.path.join(self.output_dir, filename)
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        
        self.logger.info(f"JUnit XML export completed: {xml_path}")
        return xml_path