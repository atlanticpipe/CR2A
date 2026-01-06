"""
Integration test demonstrating the error handling and logging framework functionality.
This test shows how both systems work together to provide comprehensive error analysis.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from .error_logging import ErrorLoggingSystem, ErrorCategory
from .error_validation import ErrorHandlingValidator
from .models import TestConfiguration, TestStatus


def test_complete_error_framework_workflow():
    """Test the complete workflow of error logging and validation."""
    
    # Setup test configuration
    config = TestConfiguration(
        aws_region="us-east-1",
        verbose_logging=True,
        save_artifacts=True
    )
    
    # Mock AWS clients
    with patch('boto3.client') as mock_boto:
        mock_client = Mock()
        
        # Mock CloudWatch responses for error logging
        log_groups_paginator = Mock()
        log_groups_paginator.paginate.return_value = [
            {
                'logGroups': [
                    {'logGroupName': '/aws/lambda/cr2a-analyzer'},
                    {'logGroupName': '/aws/lambda/cr2a-worker'},
                ]
            }
        ]
        
        log_events_paginator = Mock()
        mock_events = [
            {
                'timestamp': int((datetime.now(timezone.utc) - timedelta(minutes=10)).timestamp() * 1000),
                'message': 'ERROR: ModuleNotFoundError: No module named "missing_package"',
                'logStreamName': 'test-stream-1'
            },
            {
                'timestamp': int((datetime.now(timezone.utc) - timedelta(minutes=8)).timestamp() * 1000),
                'message': 'ERROR: KeyError: OPENAI_API_KEY not found in environment',
                'logStreamName': 'test-stream-2'
            },
            {
                'timestamp': int((datetime.now(timezone.utc) - timedelta(minutes=5)).timestamp() * 1000),
                'message': 'ERROR: ValidationException: Reserved keyword "status" used in DynamoDB expression',
                'logStreamName': 'test-stream-3'
            },
            {
                'timestamp': int((datetime.now(timezone.utc) - timedelta(minutes=2)).timestamp() * 1000),
                'message': 'INFO: Processing completed successfully',
                'logStreamName': 'test-stream-4'
            }
        ]
        log_events_paginator.paginate.return_value = [
            {'events': mock_events}
        ]
        
        def get_paginator(operation):
            if operation == 'describe_log_groups':
                return log_groups_paginator
            elif operation == 'filter_log_events':
                return log_events_paginator
            else:
                return Mock()
        
        mock_client.get_paginator = get_paginator
        mock_boto.return_value = mock_client
        
        # Test error logging system
        logging_system = ErrorLoggingSystem(config)
        
        # Capture logs from the last hour
        start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        log_entries = logging_system.capture_logs(start_time=start_time)
        
        # Verify log capture
        assert len(log_entries) > 0
        error_entries = [entry for entry in log_entries if entry.level == 'ERROR']
        assert len(error_entries) >= 3  # We have 3 error messages in mock data
        
        # Analyze errors
        error_analyses = logging_system.analyze_errors(log_entries)
        
        # Verify error analysis
        assert len(error_analyses) > 0
        assert ErrorCategory.DEPENDENCY_ERROR in error_analyses
        assert ErrorCategory.CONFIGURATION_ERROR in error_analyses
        assert ErrorCategory.VALIDATION_ERROR in error_analyses
        
        # Check specific analysis details
        dep_analysis = error_analyses[ErrorCategory.DEPENDENCY_ERROR]
        assert dep_analysis.count >= 1
        assert len(dep_analysis.affected_components) > 0
        assert len(dep_analysis.suggested_fixes) > 0
        
        # Generate error report
        error_report = logging_system.generate_error_report(error_analyses, 'json')
        assert 'timestamp' in error_report
        assert 'total_errors' in error_report
        assert 'DEPENDENCY_ERROR' in error_report
        
        # Test error validation system
        validator = ErrorHandlingValidator(config)
        
        # Test the validation system functionality
        validation_result = validator.test_error_validation_system()
        
        # Verify validation system is functional
        assert validation_result.status in [TestStatus.PASS, TestStatus.FAIL]
        assert validation_result.status != TestStatus.ERROR
        assert 'Error validation system tested' in validation_result.message
        
        # Test logging system functionality
        logging_result = logging_system.test_error_logging_system()
        
        # Verify logging system is functional
        assert logging_result.status in [TestStatus.PASS, TestStatus.FAIL]
        assert logging_result.status != TestStatus.ERROR
        assert 'Error logging system functional' in logging_result.message
        
        print("✅ Complete error framework workflow test passed!")
        print(f"📊 Captured {len(log_entries)} log entries")
        print(f"🔍 Identified {len(error_analyses)} error categories")
        print(f"📝 Generated error report ({len(error_report)} characters)")
        print(f"✅ Error logging system: {logging_result.status.value}")
        print(f"✅ Error validation system: {validation_result.status.value}")


if __name__ == '__main__':
    test_complete_error_framework_workflow()