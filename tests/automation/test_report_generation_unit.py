"""
Unit tests for CR2A test report generation.
Tests specific report formats and edge cases for the test reporting system.

Requirements: 6.4 - Test report generation with pass/fail status
"""

import json
import os
import tempfile
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, mock_open
from xml.etree.ElementTree import fromstring

from .automation_reporter import CR2ATestReporter, ReportExporter
from ..core.models import TestSuite, TestResult, TestStatus


class TestReportGeneration:
    """Unit tests for report generation functionality."""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def sample_test_suites(self):
        """Create sample test suites for testing."""
        # Create test results with different statuses
        passing_test = TestResult(
            test_name="test_dependency_import",
            status=TestStatus.PASS,
            message="All dependencies imported successfully",
            execution_time=0.5,
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        )
        
        failing_test = TestResult(
            test_name="test_openai_connection",
            status=TestStatus.FAIL,
            message="OpenAI API key invalid",
            details={"error_code": "401", "api_endpoint": "https://api.openai.com"},
            execution_time=1.2,
            timestamp=datetime(2024, 1, 1, 12, 0, 1, tzinfo=timezone.utc)
        )
        
        error_test = TestResult(
            test_name="test_dynamodb_write",
            status=TestStatus.ERROR,
            message="DynamoDB table not found",
            details={"exception": "ResourceNotFoundException", "table": "cr2a-jobs"},
            execution_time=0.8,
            timestamp=datetime(2024, 1, 1, 12, 0, 2, tzinfo=timezone.utc)
        )
        
        skipped_test = TestResult(
            test_name="test_optional_feature",
            status=TestStatus.SKIP,
            message="Feature not enabled in configuration",
            execution_time=0.0,
            timestamp=datetime(2024, 1, 1, 12, 0, 3, tzinfo=timezone.utc)
        )
        
        # Create test suites
        component_suite = TestSuite(
            name="Component Tests",
            description="Individual component isolation tests",
            tests=[passing_test, failing_test],
            overall_status=TestStatus.FAIL,
            execution_time=1.7,
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        )
        
        integration_suite = TestSuite(
            name="Integration Tests",
            description="Component interaction and workflow tests",
            tests=[error_test, skipped_test],
            overall_status=TestStatus.ERROR,
            execution_time=0.8,
            timestamp=datetime(2024, 1, 1, 12, 1, 0, tzinfo=timezone.utc)
        )
        
        return [component_suite, integration_suite]
    
    @pytest.fixture
    def empty_test_suite(self):
        """Create empty test suite for edge case testing."""
        return TestSuite(
            name="Empty Suite",
            description="Test suite with no tests",
            tests=[],
            overall_status=TestStatus.SKIP,
            execution_time=0.0
        )
    
    def test_html_report_generation_basic(self, temp_output_dir, sample_test_suites):
        """Test basic HTML report generation with valid test suites."""
        reporter = CR2ATestReporter(output_dir=temp_output_dir)
        
        # Generate HTML report
        output_path = reporter.generate_html_report(sample_test_suites, "test_report.html")
        
        # Verify file was created
        assert os.path.exists(output_path)
        assert output_path.endswith("test_report.html")
        
        # Read and verify HTML content
        with open(output_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Check for essential HTML structure
        assert "<!DOCTYPE html>" in html_content
        assert "<title>CR2A Test Report</title>" in html_content
        assert "Component Tests" in html_content
        assert "Integration Tests" in html_content
        
        # Check for test results
        assert "test_dependency_import" in html_content
        assert "test_openai_connection" in html_content
        assert "All dependencies imported successfully" in html_content
        assert "OpenAI API key invalid" in html_content
        
        # Check for status indicators
        assert "pass" in html_content.lower()
        assert "fail" in html_content.lower()
        assert "error" in html_content.lower()
        assert "skip" in html_content.lower()
    
    def test_html_report_generation_empty_suite(self, temp_output_dir, empty_test_suite):
        """Test HTML report generation with empty test suite."""
        reporter = CR2ATestReporter(output_dir=temp_output_dir)
        
        output_path = reporter.generate_html_report([empty_test_suite], "empty_report.html")
        
        assert os.path.exists(output_path)
        
        with open(output_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Should still generate valid HTML
        assert "<!DOCTYPE html>" in html_content
        assert "Empty Suite" in html_content
        assert "Test suite with no tests" in html_content
    
    def test_json_report_generation_basic(self, temp_output_dir, sample_test_suites):
        """Test basic JSON report generation with valid test suites."""
        reporter = CR2ATestReporter(output_dir=temp_output_dir)
        
        # Generate JSON report
        output_path = reporter.generate_json_report(sample_test_suites, "test_report.json")
        
        # Verify file was created
        assert os.path.exists(output_path)
        assert output_path.endswith("test_report.json")
        
        # Read and verify JSON content
        with open(output_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        # Check JSON structure
        assert "timestamp" in report_data
        assert "summary" in report_data
        assert "test_suites" in report_data
        
        # Check summary data
        summary = report_data["summary"]
        assert summary["total_suites"] == 2
        assert summary["total_tests"] == 4
        assert summary["total_passed"] == 1
        assert summary["total_failed"] == 1
        assert summary["total_errors"] == 1
        assert summary["total_skipped"] == 1
        assert summary["overall_status"] == "ERROR"  # Due to error test
        
        # Check test suite data
        test_suites = report_data["test_suites"]
        assert len(test_suites) == 2
        
        component_suite = test_suites[0]
        assert component_suite["name"] == "Component Tests"
        assert component_suite["overall_status"] == "FAIL"
        assert len(component_suite["tests"]) == 2
        
        # Check individual test data
        first_test = component_suite["tests"][0]
        assert first_test["test_name"] == "test_dependency_import"
        assert first_test["status"] == "PASS"
        assert first_test["message"] == "All dependencies imported successfully"
        assert first_test["execution_time"] == 0.5
    
    def test_json_report_generation_with_details(self, temp_output_dir, sample_test_suites):
        """Test JSON report generation includes test details."""
        reporter = CR2ATestReporter(output_dir=temp_output_dir)
        
        output_path = reporter.generate_json_report(sample_test_suites, "detailed_report.json")
        
        with open(output_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        # Find test with details
        component_suite = report_data["test_suites"][0]
        failing_test = component_suite["tests"][1]  # Second test is the failing one
        
        assert failing_test["test_name"] == "test_openai_connection"
        assert failing_test["details"] is not None
        assert failing_test["details"]["error_code"] == "401"
        assert failing_test["details"]["api_endpoint"] == "https://api.openai.com"
    
    def test_console_summary_generation(self, temp_output_dir, sample_test_suites):
        """Test console summary generation."""
        reporter = CR2ATestReporter(output_dir=temp_output_dir)
        
        # Generate console summary
        console_output = reporter.generate_console_summary(sample_test_suites)
        
        # Check console output content
        assert "CR2A TESTING FRAMEWORK - SUMMARY REPORT" in console_output
        assert "OVERALL SUMMARY:" in console_output
        assert "Status: ERROR" in console_output
        assert "Test Suites: 2" in console_output
        assert "Total Tests: 4" in console_output
        assert "Passed: 1 (25.0%)" in console_output
        assert "Failed: 1" in console_output
        assert "Errors: 1" in console_output
        assert "Skipped: 1" in console_output
        
        # Check test suite details
        assert "TEST SUITE DETAILS:" in console_output
        assert "Component Tests" in console_output
        assert "Integration Tests" in console_output
        
        # Check failed test details
        assert "Failed/Error Tests:" in console_output
        assert "test_openai_connection: OpenAI API key invalid" in console_output
        assert "test_dynamodb_write: DynamoDB table not found" in console_output
        
        # Verify console summary file was created
        console_file = os.path.join(temp_output_dir, "console_summary.txt")
        assert os.path.exists(console_file)
    
    def test_console_summary_all_passing(self, temp_output_dir):
        """Test console summary with all passing tests."""
        # Create all passing test suite
        passing_tests = [
            TestResult("test_1", TestStatus.PASS, "Success", execution_time=0.1),
            TestResult("test_2", TestStatus.PASS, "Success", execution_time=0.2)
        ]
        
        passing_suite = TestSuite(
            name="All Passing",
            description="All tests pass",
            tests=passing_tests,
            overall_status=TestStatus.PASS,
            execution_time=0.3
        )
        
        reporter = CR2ATestReporter(output_dir=temp_output_dir)
        console_output = reporter.generate_console_summary([passing_suite])
        
        assert "Status: PASS" in console_output
        assert "Passed: 2 (100.0%)" in console_output
        assert "Failed: 0" in console_output
        assert "Failed/Error Tests:" not in console_output  # No failed tests section
    
    def test_all_reports_generation(self, temp_output_dir, sample_test_suites):
        """Test generation of all report formats at once."""
        reporter = CR2ATestReporter(output_dir=temp_output_dir)
        
        # Generate all reports
        report_paths = reporter.generate_all_reports(sample_test_suites, "comprehensive_test")
        
        # Verify all report types were generated
        assert "html" in report_paths
        assert "json" in report_paths
        assert "console" in report_paths
        
        # Verify files exist
        assert os.path.exists(report_paths["html"])
        assert os.path.exists(report_paths["json"])
        assert os.path.exists(report_paths["console"])
        
        # Verify file names
        assert "comprehensive_test.html" in report_paths["html"]
        assert "comprehensive_test.json" in report_paths["json"]
        assert "console_summary.txt" in report_paths["console"]
    
    def test_summary_stats_calculation(self, temp_output_dir, sample_test_suites):
        """Test summary statistics calculation accuracy."""
        reporter = CR2ATestReporter(output_dir=temp_output_dir)
        
        summary = reporter._calculate_summary_stats(sample_test_suites)
        
        assert summary["total_suites"] == 2
        assert summary["total_tests"] == 4
        assert summary["total_passed"] == 1
        assert summary["total_failed"] == 1
        assert summary["total_errors"] == 1
        assert summary["total_skipped"] == 1
        assert summary["pass_rate"] == 25.0  # 1 out of 4 tests passed
        assert summary["total_time"] == 2.5  # 1.7 + 0.8
        assert summary["overall_status"] == "ERROR"  # Highest priority status
    
    def test_summary_stats_edge_cases(self, temp_output_dir):
        """Test summary statistics with edge cases."""
        reporter = CR2ATestReporter(output_dir=temp_output_dir)
        
        # Test with empty test suites
        empty_summary = reporter._calculate_summary_stats([])
        assert empty_summary["total_suites"] == 0
        assert empty_summary["total_tests"] == 0
        assert empty_summary["pass_rate"] == 0.0
        assert empty_summary["overall_status"] == "SKIP"
        
        # Test with only skipped tests
        skipped_test = TestResult("test_skip", TestStatus.SKIP, "Skipped", execution_time=0.0)
        skipped_suite = TestSuite("Skip Suite", "All skipped", [skipped_test], TestStatus.SKIP, 0.0)
        
        skip_summary = reporter._calculate_summary_stats([skipped_suite])
        assert skip_summary["overall_status"] == "SKIP"
        assert skip_summary["pass_rate"] == 0.0
    
    def test_status_symbol_mapping(self, temp_output_dir):
        """Test status symbol mapping for console output."""
        reporter = CR2ATestReporter(output_dir=temp_output_dir)
        
        assert reporter._get_status_symbol(TestStatus.PASS) == "✓"
        assert reporter._get_status_symbol(TestStatus.FAIL) == "✗"
        assert reporter._get_status_symbol(TestStatus.ERROR) == "⚠"
        assert reporter._get_status_symbol(TestStatus.SKIP) == "○"
    
    @patch('builtins.open', new_callable=mock_open)
    def test_html_report_file_write_error(self, mock_file, temp_output_dir, sample_test_suites):
        """Test HTML report generation handles file write errors."""
        mock_file.side_effect = IOError("Permission denied")
        
        reporter = CR2ATestReporter(output_dir=temp_output_dir)
        
        with pytest.raises(IOError):
            reporter.generate_html_report(sample_test_suites, "error_report.html")
    
    @patch('builtins.open', new_callable=mock_open)
    def test_json_report_file_write_error(self, mock_file, temp_output_dir, sample_test_suites):
        """Test JSON report generation handles file write errors."""
        mock_file.side_effect = IOError("Disk full")
        
        reporter = CR2ATestReporter(output_dir=temp_output_dir)
        
        with pytest.raises(IOError):
            reporter.generate_json_report(sample_test_suites, "error_report.json")
    
    def test_comprehensive_report_no_existing_data(self, temp_output_dir):
        """Test comprehensive report generation with no existing test data."""
        reporter = CR2ATestReporter(output_dir=temp_output_dir)
        
        # Generate comprehensive report with no existing data
        report_path = reporter.generate_comprehensive_report()
        
        # Should create a placeholder report
        assert report_path is not None
        assert os.path.exists(report_path)
        
        # Verify placeholder content
        with open(report_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        assert "No test data available" in html_content
        assert "Run tests first to generate comprehensive report" in html_content


class TestReportExporter:
    """Unit tests for report export functionality."""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def sample_test_suites(self):
        """Create sample test suites for export testing."""
        test1 = TestResult("test_export_1", TestStatus.PASS, "Success", execution_time=0.1)
        test2 = TestResult("test_export_2", TestStatus.FAIL, "Failed", execution_time=0.2)
        
        suite = TestSuite(
            name="Export Test Suite",
            description="Test suite for export functionality",
            tests=[test1, test2],
            overall_status=TestStatus.FAIL,
            execution_time=0.3
        )
        
        return [suite]
    
    def test_csv_export(self, temp_output_dir, sample_test_suites):
        """Test CSV export functionality."""
        exporter = ReportExporter(output_dir=temp_output_dir)
        
        csv_path = exporter.export_to_csv(sample_test_suites, "test_results.csv")
        
        assert os.path.exists(csv_path)
        assert csv_path.endswith("test_results.csv")
        
        # Read and verify CSV content
        with open(csv_path, 'r', encoding='utf-8') as f:
            csv_content = f.read()
        
        # Check CSV headers
        assert "test_suite,test_name,status,message,execution_time,timestamp" in csv_content
        
        # Check CSV data
        assert "Export Test Suite,test_export_1,PASS,Success,0.1" in csv_content
        assert "Export Test Suite,test_export_2,FAIL,Failed,0.2" in csv_content
    
    def test_junit_xml_export(self, temp_output_dir, sample_test_suites):
        """Test JUnit XML export functionality."""
        exporter = ReportExporter(output_dir=temp_output_dir)
        
        xml_path = exporter.export_junit_xml(sample_test_suites, "junit_results.xml")
        
        assert os.path.exists(xml_path)
        assert xml_path.endswith("junit_results.xml")
        
        # Read and verify XML content
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # Parse XML to verify structure
        root = fromstring(xml_content)
        
        assert root.tag == "testsuites"
        assert root.get("name") == "CR2A Testing Framework"
        assert root.get("tests") == "2"
        assert root.get("failures") == "1"
        assert root.get("errors") == "0"
        
        # Check testsuite element
        testsuite = root.find("testsuite")
        assert testsuite is not None
        assert testsuite.get("name") == "Export Test Suite"
        assert testsuite.get("tests") == "2"
        assert testsuite.get("failures") == "1"
        
        # Check testcase elements
        testcases = testsuite.findall("testcase")
        assert len(testcases) == 2
        
        # Check passing test
        passing_test = testcases[0]
        assert passing_test.get("name") == "test_export_1"
        assert passing_test.get("classname") == "Export_Test_Suite"
        assert len(passing_test) == 0  # No failure/error elements
        
        # Check failing test
        failing_test = testcases[1]
        assert failing_test.get("name") == "test_export_2"
        failure_element = failing_test.find("failure")
        assert failure_element is not None
        assert failure_element.get("message") == "Failed"
    
    def test_junit_xml_export_with_errors_and_skips(self, temp_output_dir):
        """Test JUnit XML export with error and skip statuses."""
        error_test = TestResult("test_error", TestStatus.ERROR, "System error", 
                               details={"exception": "RuntimeError"}, execution_time=0.1)
        skip_test = TestResult("test_skip", TestStatus.SKIP, "Not applicable", execution_time=0.0)
        
        suite = TestSuite(
            name="Mixed Status Suite",
            description="Suite with various test statuses",
            tests=[error_test, skip_test],
            overall_status=TestStatus.ERROR,
            execution_time=0.1
        )
        
        exporter = ReportExporter(output_dir=temp_output_dir)
        xml_path = exporter.export_junit_xml([suite], "mixed_results.xml")
        
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        root = fromstring(xml_content)
        testsuite = root.find("testsuite")
        
        assert testsuite.get("errors") == "1"
        
        testcases = testsuite.findall("testcase")
        
        # Check error test
        error_testcase = testcases[0]
        error_element = error_testcase.find("error")
        assert error_element is not None
        assert error_element.get("message") == "System error"
        assert "RuntimeError" in error_element.text
        
        # Check skipped test
        skip_testcase = testcases[1]
        skipped_element = skip_testcase.find("skipped")
        assert skipped_element is not None
        assert skipped_element.get("message") == "Not applicable"
    
    @patch('builtins.open', new_callable=mock_open)
    def test_csv_export_file_error(self, mock_file, temp_output_dir, sample_test_suites):
        """Test CSV export handles file write errors."""
        mock_file.side_effect = IOError("Cannot write file")
        
        exporter = ReportExporter(output_dir=temp_output_dir)
        
        with pytest.raises(IOError):
            exporter.export_to_csv(sample_test_suites, "error.csv")
    
    @patch('builtins.open', new_callable=mock_open)
    def test_junit_xml_export_file_error(self, mock_file, temp_output_dir, sample_test_suites):
        """Test JUnit XML export handles file write errors."""
        mock_file.side_effect = IOError("Cannot write file")
        
        exporter = ReportExporter(output_dir=temp_output_dir)
        
        with pytest.raises(IOError):
            exporter.export_junit_xml(sample_test_suites, "error.xml")