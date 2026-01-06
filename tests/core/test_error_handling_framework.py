"""
Comprehensive test for the error handling and logging framework.
Tests both error logging system and error validation functionality.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock

from .error_logging import ErrorLoggingSystem, ErrorCategory, LogEntry
from .error_validation import ErrorHandlingValidator, ErrorTestType, ErrorValidationResult
from .models import TestConfiguration, TestResult, TestStatus


class TestErrorHandlingFramework:
    """Test suite for the complete error handling framework."""
    
    @pytest.fixture
    def test_config(self):
        """Test configuration fixture."""
        return TestConfiguration(
            aws_region="us-east-1",
            verbose_logging=True,
            save_artifacts=True
        )
    
    @pytest.fixture
    def mock_cloudwatch_client(self):
        """Mock CloudWatch client for testing."""
        client = Mock()
        
        # Mock paginator for log groups
        log_groups_paginator = Mock()
        log_groups_paginator.paginate.return_value = [
            {
                'logGroups': [
                    {'logGroupName': '/aws/lambda/cr2a-analyzer'},
                    {'logGroupName': '/aws/lambda/cr2a-get-metadata'},
                    {'logGroupName': '/aws/apigateway/cr2a-api'},
                ]
            }
        ]
        
        # Mock paginator for log events
        log_events_paginator = Mock()
        mock_events = [
            {
                'timestamp': int((datetime.now(timezone.utc) - timedelta(minutes=5)).timestamp() * 1000),
                'message': 'ERROR: ModuleNotFoundError: No module named "missing_package"',
                'logStreamName': 'test-stream'
            },
            {
                'timestamp': int((datetime.now(timezone.utc) - timedelta(minutes=3)).timestamp() * 1000),
                'message': 'ERROR: ValidationException: Reserved keyword "status" used in expression',
                'logStreamName': 'test-stream'
            },
            {
                'timestamp': int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp() * 1000),
                'message': 'INFO: Processing completed successfully',
                'logStreamName': 'test-stream'
            }
        ]
        log_events_paginator.paginate.return_value = [
            {'events': mock_events}
        ]
        
        # Configure get_paginator to return appropriate paginator based on operation
        def get_paginator(operation):
            if operation == 'describe_log_groups':
                return log_groups_paginator
            elif operation == 'filter_log_events':
                return log_events_paginator
            else:
                return Mock()
        
        client.get_paginator = get_paginator
        
        return client
    
    def test_error_logging_system_initialization(self, test_config):
        """Test error logging system initialization."""
        with patch('boto3.client') as mock_boto:
            mock_boto.return_value = Mock()
            
            logging_system = ErrorLoggingSystem(test_config)
            
            assert logging_system.config == test_config
            assert len(logging_system.error_patterns) > 0
            assert any(pattern.category == ErrorCategory.DEPENDENCY_ERROR 
                      for pattern in logging_system.error_patterns)
    
    def test_log_group_discovery(self, test_config, mock_cloudwatch_client):
        """Test CloudWatch log group discovery."""
        with patch('boto3.client', return_value=mock_cloudwatch_client):
            logging_system = ErrorLoggingSystem(test_config)
            log_groups = logging_system._get_cr2a_log_groups()
            
            assert len(log_groups) == 3
            assert '/aws/lambda/cr2a-analyzer' in log_groups
            assert '/aws/apigateway/cr2a-api' in log_groups
    
    def test_log_capture_and_parsing(self, test_config, mock_cloudwatch_client):
        """Test log capture and parsing functionality."""
        with patch('boto3.client', return_value=mock_cloudwatch_client):
            logging_system = ErrorLoggingSystem(test_config)
            
            start_time = datetime.now(timezone.utc) - timedelta(hours=1)
            end_time = datetime.now(timezone.utc)
            
            log_entries = logging_system.capture_logs(start_time, end_time)
            
            assert len(log_entries) > 0
            assert all(isinstance(entry, LogEntry) for entry in log_entries)
            
            # Check that error entries are properly parsed
            error_entries = [entry for entry in log_entries if entry.level == 'ERROR']
            assert len(error_entries) >= 2
    
    def test_error_pattern_analysis(self, test_config, mock_cloudwatch_client):
        """Test error pattern detection and analysis."""
        with patch('boto3.client', return_value=mock_cloudwatch_client):
            logging_system = ErrorLoggingSystem(test_config)
            
            # Create test log entries
            test_entries = [
                LogEntry(
                    timestamp=datetime.now(timezone.utc),
                    log_group='/aws/lambda/cr2a-test',
                    log_stream='test-stream',
                    message='ERROR: ModuleNotFoundError: No module named "test_package"',
                    level='ERROR',
                    component='cr2a-test',
                    raw_event={}
                ),
                LogEntry(
                    timestamp=datetime.now(timezone.utc),
                    log_group='/aws/lambda/cr2a-test',
                    log_stream='test-stream',
                    message='ERROR: ValidationException: Reserved keyword used',
                    level='ERROR',
                    component='cr2a-test',
                    raw_event={}
                )
            ]
            
            analyses = logging_system.analyze_errors(test_entries)
            
            assert ErrorCategory.DEPENDENCY_ERROR in analyses
            assert ErrorCategory.VALIDATION_ERROR in analyses
            
            dep_analysis = analyses[ErrorCategory.DEPENDENCY_ERROR]
            assert dep_analysis.count >= 1
            assert 'cr2a-test' in dep_analysis.affected_components
    
    def test_error_report_generation(self, test_config):
        """Test error report generation in different formats."""
        with patch('boto3.client') as mock_boto:
            mock_boto.return_value = Mock()
            
            logging_system = ErrorLoggingSystem(test_config)
            
            # Create mock analysis data
            from .error_logging import ErrorAnalysis
            mock_analyses = {
                ErrorCategory.DEPENDENCY_ERROR: ErrorAnalysis(
                    category=ErrorCategory.DEPENDENCY_ERROR,
                    count=5,
                    first_occurrence=datetime.now(timezone.utc) - timedelta(hours=2),
                    last_occurrence=datetime.now(timezone.utc) - timedelta(minutes=10),
                    affected_components={'cr2a-analyzer', 'cr2a-worker'},
                    sample_messages=['ModuleNotFoundError: No module named "test"'],
                    pattern_matches=['ModuleNotFoundError'],
                    suggested_fixes=['Update Lambda layer with missing dependencies']
                )
            }
            
            # Test JSON report
            json_report = logging_system.generate_error_report(mock_analyses, 'json')
            assert 'timestamp' in json_report
            assert 'DEPENDENCY_ERROR' in json_report
            
            # Test text report
            text_report = logging_system.generate_error_report(mock_analyses, 'text')
            assert 'CR2A Error Analysis Report' in text_report
            assert 'DEPENDENCY_ERROR' in text_report
    
    def test_error_validation_system_initialization(self, test_config):
        """Test error validation system initialization."""
        with patch('boto3.client') as mock_boto:
            mock_boto.return_value = Mock()
            
            validator = ErrorHandlingValidator(test_config)
            
            assert validator.config == test_config
            assert len(validator.error_test_cases) > 0
            
            # Check that we have different types of test cases
            component_tests = [tc for tc in validator.error_test_cases 
                             if tc.test_type == ErrorTestType.COMPONENT_ERROR]
            api_tests = [tc for tc in validator.error_test_cases 
                        if tc.test_type == ErrorTestType.API_ERROR]
            integration_tests = [tc for tc in validator.error_test_cases 
                               if tc.test_type == ErrorTestType.INTEGRATION_ERROR]
            
            assert len(component_tests) > 0
            assert len(api_tests) > 0
            assert len(integration_tests) > 0
    
    def test_component_error_validation(self, test_config):
        """Test component error validation functionality."""
        with patch('boto3.client') as mock_boto:
            mock_boto.return_value = Mock()
            
            validator = ErrorHandlingValidator(test_config)
            
            # Mock the test execution to simulate expected behavior
            with patch.object(validator, '_execute_error_test') as mock_execute:
                mock_result = ErrorValidationResult(
                    test_case=validator.error_test_cases[0],
                    success=True,
                    actual_error_type='ImportError',
                    actual_error_message='No module named "test"',
                    stack_trace='Mock stack trace',
                    response_time=0.1,
                    additional_details={}
                )
                mock_execute.return_value = mock_result
                
                results = validator.validate_component_error_handling()
                
                assert len(results) > 0
                assert all(isinstance(result, ErrorValidationResult) for result in results)
    
    def test_api_error_validation(self, test_config):
        """Test API error validation functionality."""
        with patch('boto3.client') as mock_boto:
            mock_boto.return_value = Mock()
            
            validator = ErrorHandlingValidator(test_config)
            
            # Mock requests to simulate API responses
            with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 400
                mock_response.json.return_value = {'detail': 'File too large'}
                mock_get.return_value = mock_response
                mock_post.return_value = mock_response
                
                with patch.object(validator, '_execute_error_test') as mock_execute:
                    mock_result = ErrorValidationResult(
                        test_case=validator.error_test_cases[0],
                        success=True,
                        actual_error_type='ValueError',
                        actual_error_message='File too large',
                        stack_trace=None,
                        response_time=0.2,
                        additional_details={}
                    )
                    mock_execute.return_value = mock_result
                    
                    results = validator.validate_api_error_handling()
                    
                    assert len(results) > 0
                    assert all(isinstance(result, ErrorValidationResult) for result in results)
    
    def test_validation_report_generation(self, test_config):
        """Test validation report generation."""
        with patch('boto3.client') as mock_boto:
            mock_boto.return_value = Mock()
            
            validator = ErrorHandlingValidator(test_config)
            
            # Create mock validation results
            mock_results = [
                ErrorValidationResult(
                    test_case=validator.error_test_cases[0],
                    success=True,
                    actual_error_type='ImportError',
                    actual_error_message='Expected error occurred',
                    stack_trace=None,
                    response_time=0.1,
                    additional_details={}
                ),
                ErrorValidationResult(
                    test_case=validator.error_test_cases[1],
                    success=False,
                    actual_error_type='ValueError',
                    actual_error_message='Unexpected error',
                    stack_trace='Mock stack trace',
                    response_time=0.2,
                    additional_details={}
                )
            ]
            
            # Test JSON report
            json_report = validator.generate_validation_report(mock_results, 'json')
            assert 'timestamp' in json_report
            assert 'total_tests' in json_report
            assert 'passed_tests' in json_report
            
            # Test text report
            text_report = validator.generate_validation_report(mock_results, 'text')
            assert 'CR2A Error Handling Validation Report' in text_report
            assert 'PASS' in text_report
            assert 'FAIL' in text_report
    
    def test_integrated_error_framework(self, test_config, mock_cloudwatch_client):
        """Test the integrated error handling framework."""
        with patch('boto3.client', return_value=mock_cloudwatch_client):
            # Test both systems working together
            logging_system = ErrorLoggingSystem(test_config)
            validator = ErrorHandlingValidator(test_config)
            
            # Test logging system
            logging_result = logging_system.test_error_logging_system()
            assert logging_result.status in [TestStatus.PASS, TestStatus.FAIL]
            
            # Test validation system
            validation_result = validator.test_error_validation_system()
            assert validation_result.status in [TestStatus.PASS, TestStatus.FAIL]
            
            # Both systems should be functional
            assert logging_result.status != TestStatus.ERROR
            assert validation_result.status != TestStatus.ERROR
    
    def test_error_pattern_matching(self, test_config):
        """Test error pattern matching accuracy."""
        with patch('boto3.client') as mock_boto:
            mock_boto.return_value = Mock()
            
            logging_system = ErrorLoggingSystem(test_config)
            
            test_messages = [
                ("ModuleNotFoundError: No module named 'test'", ErrorCategory.DEPENDENCY_ERROR),
                ("KeyError: 'OPENAI_API_KEY'", ErrorCategory.CONFIGURATION_ERROR),
                ("AccessDenied: User not authorized", ErrorCategory.PERMISSION_ERROR),
                ("ConnectionError: Failed to connect", ErrorCategory.NETWORK_ERROR),
                ("Task timed out after 30 seconds", ErrorCategory.TIMEOUT_ERROR),
                ("ValidationException: Invalid input", ErrorCategory.VALIDATION_ERROR),
            ]
            
            for message, expected_category in test_messages:
                # Create test log entry
                test_entry = LogEntry(
                    timestamp=datetime.now(timezone.utc),
                    log_group='/aws/lambda/test',
                    log_stream='test-stream',
                    message=f'ERROR: {message}',
                    level='ERROR',
                    component='test',
                    raw_event={}
                )
                
                analyses = logging_system.analyze_errors([test_entry])
                
                # Should detect the expected category
                assert expected_category in analyses
                assert analyses[expected_category].count >= 1


if __name__ == '__main__':
    pytest.main([__file__])