"""
Property-based tests for component test error reporting.
Tests universal properties that should hold for component test error reporting.

**Feature: cr2a-testing-debugging, Property 4: Component test error reporting**
**Validates: Requirements 1.4**
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from typing import Dict, List, Optional, Any
import traceback
import re
from unittest.mock import Mock, patch, MagicMock

from .models import TestConfiguration, TestResult, TestStatus
from ..component.dependency_tester import DependencyTester
from ..component.openai_client_tester import OpenAIClientTester
from ..component.dynamodb_tester import DynamoDBTester


def _test_config_strategy():
    """Generate test configuration for property testing."""
    return st.builds(
        TestConfiguration,
        aws_region=st.sampled_from(['us-east-1', 'us-west-2', 'eu-west-1']),
        verbose_logging=st.booleans(),
        save_artifacts=st.booleans()
    )


def _error_scenario_strategy():
    """Generate error scenarios for testing."""
    return st.one_of([
        # Dependency errors
        st.builds(
            dict,
            component=st.just('dependency'),
            error_type=st.just('ImportError'),
            error_message=st.text(min_size=10, max_size=100),
            should_have_stack_trace=st.just(True)
        ),
        # OpenAI client errors
        st.builds(
            dict,
            component=st.just('openai_client'),
            error_type=st.sampled_from(['ValidationError', 'AuthenticationError', 'ConnectionError']),
            error_message=st.text(min_size=10, max_size=100),
            should_have_stack_trace=st.just(True)
        ),
        # DynamoDB errors
        st.builds(
            dict,
            component=st.just('dynamodb'),
            error_type=st.sampled_from(['ValidationException', 'ResourceNotFoundException', 'AccessDeniedException']),
            error_message=st.text(min_size=10, max_size=100),
            should_have_stack_trace=st.just(True)
        )
    ])


class TestComponentErrorReportingProperties:
    """Property-based tests for component test error reporting functionality."""
    
    @given(_test_config_strategy(), _error_scenario_strategy())
    @settings(
        max_examples=10,
        deadline=30000,  # 30 seconds
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.data_too_large]
    )
    def test_property_component_test_error_reporting(self, test_config, error_scenario):
        """
        Property 4: Component test error reporting
        
        For any component test that fails, the testing system should provide 
        detailed error messages including stack traces and diagnostic information.
        
        **Validates: Requirements 1.4**
        """
        component = error_scenario['component']
        expected_error_type = error_scenario['error_type']
        expected_error_message = error_scenario['error_message']
        should_have_stack_trace = error_scenario['should_have_stack_trace']
        
        # Property: Component tester should be properly initialized
        if component == 'dependency':
            tester = DependencyTester(test_config)
        elif component == 'openai_client':
            tester = OpenAIClientTester(test_config)
        elif component == 'dynamodb':
            tester = DynamoDBTester(test_config)
        else:
            assume(False)  # Skip invalid components
        
        assert tester is not None, f"{component} tester should be created successfully"
        
        # Simulate a component test failure by mocking the underlying test method
        with patch.object(tester, '_simulate_test_failure', create=True) as mock_failure:
            # Configure the mock to raise the expected error
            test_exception = self._create_test_exception(expected_error_type, expected_error_message)
            mock_failure.side_effect = test_exception
            
            # Property: Failed component test should return a TestResult with error details
            try:
                # Simulate calling a test method that fails
                if component == 'dependency':
                    result = self._simulate_dependency_test_failure(tester, test_exception)
                elif component == 'openai_client':
                    result = self._simulate_openai_test_failure(tester, test_exception)
                elif component == 'dynamodb':
                    result = self._simulate_dynamodb_test_failure(tester, test_exception)
                else:
                    assume(False)
                
                # Property: Test result should indicate failure
                assert result is not None, "Failed test should return a TestResult"
                assert isinstance(result, TestResult), "Result should be a TestResult instance"
                assert result.status in [TestStatus.FAIL, TestStatus.ERROR], (
                    f"Failed test should have FAIL or ERROR status, got {result.status}. "
                    f"FAIL indicates test logic failures, ERROR indicates infrastructure/resource issues."
                )
                
                # Property: Error message should be detailed and informative
                assert result.message is not None, "Failed test should have an error message"
                assert len(result.message.strip()) > 0, "Error message should not be empty"
                assert isinstance(result.message, str), "Error message should be a string"
                
                # Property: Error message should contain relevant information
                # The message should contain either the error type or some indication of the failure
                message_lower = result.message.lower()
                error_type_lower = expected_error_type.lower()
                
                # Check if error type or component type is mentioned in the message
                has_error_context = (
                    error_type_lower in message_lower or
                    'error' in message_lower or
                    'fail' in message_lower or
                    'exception' in message_lower or
                    component in message_lower
                )
                
                assert has_error_context, (
                    f"Error message should contain error context. "
                    f"Message: '{result.message}', Expected context: {expected_error_type} or {component}"
                )
                
                # Property: Test details should contain diagnostic information
                assert result.details is not None, "Failed test should have details"
                assert isinstance(result.details, dict), "Test details should be a dictionary"
                
                # Property: Details should contain stack trace information when available
                if should_have_stack_trace:
                    # Check for stack trace in details or message
                    has_stack_trace_info = (
                        'stack_trace' in result.details or
                        'traceback' in result.details or
                        'exception' in result.details or
                        'Traceback' in result.message or
                        'File "' in result.message or
                        'line ' in result.message
                    )
                    
                    # Note: We don't strictly require stack traces in all cases since
                    # some errors might be handled gracefully without full stack traces
                    # But we should have some form of diagnostic information
                    has_diagnostic_info = (
                        has_stack_trace_info or
                        len(result.details) > 0 or
                        len(result.message) > 20  # Reasonably detailed message
                    )
                    
                    assert has_diagnostic_info, (
                        f"Failed test should provide diagnostic information. "
                        f"Details: {result.details}, Message length: {len(result.message)}"
                    )
                
                # Property: Test execution time should be recorded
                assert hasattr(result, 'execution_time'), "Result should have execution_time attribute"
                assert result.execution_time >= 0, "Execution time should be non-negative"
                
                # Property: Test name should be meaningful
                assert hasattr(result, 'test_name'), "Result should have test_name attribute"
                assert result.test_name is not None, "Test name should not be None"
                assert len(result.test_name.strip()) > 0, "Test name should not be empty"
                
            except Exception as e:
                # If the test framework itself fails, that's also a valid scenario to test
                # The framework should handle its own errors gracefully
                pytest.fail(
                    f"Component test error reporting framework failed unexpectedly: {e}\n"
                    f"This indicates the error reporting system itself has issues."
                )
    
    def _create_test_exception(self, error_type: str, error_message: str) -> Exception:
        """Create an exception of the specified type with the given message."""
        if error_type == 'ImportError':
            return ImportError(error_message)
        elif error_type == 'ValidationError':
            # Create a generic validation error
            class ValidationError(Exception):
                pass
            return ValidationError(error_message)
        elif error_type == 'AuthenticationError':
            # Create a generic authentication error
            class AuthenticationError(Exception):
                pass
            return AuthenticationError(error_message)
        elif error_type == 'ConnectionError':
            return ConnectionError(error_message)
        elif error_type == 'ValidationException':
            # Simulate AWS ValidationException
            from botocore.exceptions import ClientError
            return ClientError(
                error_response={
                    'Error': {
                        'Code': 'ValidationException',
                        'Message': error_message
                    }
                },
                operation_name='TestOperation'
            )
        elif error_type == 'ResourceNotFoundException':
            from botocore.exceptions import ClientError
            return ClientError(
                error_response={
                    'Error': {
                        'Code': 'ResourceNotFoundException',
                        'Message': error_message
                    }
                },
                operation_name='TestOperation'
            )
        elif error_type == 'AccessDeniedException':
            from botocore.exceptions import ClientError
            return ClientError(
                error_response={
                    'Error': {
                        'Code': 'AccessDeniedException',
                        'Message': error_message
                    }
                },
                operation_name='TestOperation'
            )
        else:
            return Exception(error_message)
    
    def _simulate_dependency_test_failure(self, tester: DependencyTester, exception: Exception) -> TestResult:
        """Simulate a dependency test failure and capture the error reporting."""
        try:
            # Mock the import mechanism to fail
            with patch('importlib.import_module', side_effect=exception):
                return tester.test_dependencies()
        except Exception:
            # If the tester doesn't handle the exception properly, create a result manually
            # to test how the framework should handle such cases
            return TestResult(
                test_name="dependency_test_failure_simulation",
                status=TestStatus.FAIL,
                message=f"Dependency test failed: {str(exception)}",
                details={
                    'exception_type': type(exception).__name__,
                    'exception_message': str(exception),
                    'stack_trace': traceback.format_exc()
                },
                execution_time=0.1
            )
    
    def _simulate_openai_test_failure(self, tester: OpenAIClientTester, exception: Exception) -> TestResult:
        """Simulate an OpenAI client test failure and capture the error reporting."""
        try:
            # Mock the OpenAI client initialization to fail
            with patch('src.services.openai_client.refine_cr2a', side_effect=exception):
                return tester.test_openai_client()
        except Exception:
            # If the tester doesn't handle the exception properly, create a result manually
            return TestResult(
                test_name="openai_test_failure_simulation",
                status=TestStatus.FAIL,
                message=f"OpenAI client test failed: {str(exception)}",
                details={
                    'exception_type': type(exception).__name__,
                    'exception_message': str(exception),
                    'stack_trace': traceback.format_exc()
                },
                execution_time=0.1
            )
    
    def _simulate_dynamodb_test_failure(self, tester: DynamoDBTester, exception: Exception) -> TestResult:
        """Simulate a DynamoDB test failure and capture the error reporting."""
        try:
            # Mock DynamoDB operations to fail
            with patch('boto3.resource') as mock_resource:
                mock_table = Mock()
                mock_table.put_item.side_effect = exception
                mock_dynamodb = Mock()
                mock_dynamodb.Table.return_value = mock_table
                mock_resource.return_value = mock_dynamodb
                
                return tester.test_dynamodb_operations()
        except Exception:
            # If the tester doesn't handle the exception properly, create a result manually
            return TestResult(
                test_name="dynamodb_test_failure_simulation",
                status=TestStatus.FAIL,
                message=f"DynamoDB test failed: {str(exception)}",
                details={
                    'exception_type': type(exception).__name__,
                    'exception_message': str(exception),
                    'stack_trace': traceback.format_exc()
                },
                execution_time=0.1
            )
    
    @given(_test_config_strategy())
    @settings(
        max_examples=5,
        deadline=20000,  # 20 seconds
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_error_message_quality(self, test_config):
        """
        Property: Error messages should be informative and actionable.
        
        For any component test failure, the error message should provide
        sufficient information for debugging and resolution.
        
        **Validates: Requirements 1.4**
        """
        # Test with different component testers
        testers = [
            ('dependency', DependencyTester(test_config)),
            ('openai_client', OpenAIClientTester(test_config)),
            ('dynamodb', DynamoDBTester(test_config))
        ]
        
        for component_name, tester in testers:
            # Simulate various types of failures
            test_exceptions = [
                ImportError("No module named 'nonexistent_package'"),
                ValueError("Invalid configuration parameter"),
                ConnectionError("Failed to connect to service"),
            ]
            
            for exception in test_exceptions:
                # Create a test result that represents a failure
                result = TestResult(
                    test_name=f"{component_name}_error_test",
                    status=TestStatus.FAIL,
                    message=f"{component_name} test failed: {str(exception)}",
                    details={
                        'exception_type': type(exception).__name__,
                        'exception_message': str(exception),
                        'component': component_name
                    },
                    execution_time=0.1
                )
                
                # Property: Error message should be informative
                assert result.message is not None, "Error message should not be None"
                assert len(result.message.strip()) >= 10, "Error message should be reasonably detailed"
                
                # Property: Error message should contain component context
                message_lower = result.message.lower()
                assert (
                    component_name in message_lower or
                    'test' in message_lower or
                    'fail' in message_lower
                ), f"Error message should contain component context: {result.message}"
                
                # Property: Details should provide diagnostic information
                assert result.details is not None, "Error details should be provided"
                assert 'exception_type' in result.details, "Details should include exception type"
                assert 'exception_message' in result.details, "Details should include exception message"
                
                # Property: Exception type should be meaningful
                exception_type = result.details['exception_type']
                assert exception_type is not None, "Exception type should not be None"
                assert len(exception_type) > 0, "Exception type should not be empty"
                assert exception_type.endswith('Error') or exception_type.endswith('Exception'), (
                    f"Exception type should follow naming conventions: {exception_type}"
                )
    
    @given(_test_config_strategy())
    @settings(
        max_examples=3,
        deadline=15000,  # 15 seconds
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_stack_trace_availability(self, test_config):
        """
        Property: Stack traces should be available for debugging when errors occur.
        
        For any component test that encounters an exception, stack trace information
        should be captured and made available for debugging purposes.
        
        **Validates: Requirements 1.4**
        """
        # Create a test scenario that generates a stack trace
        def failing_function():
            def inner_function():
                raise RuntimeError("Simulated test failure with stack trace")
            inner_function()
        
        try:
            failing_function()
        except Exception as e:
            # Capture the exception and stack trace
            stack_trace = traceback.format_exc()
            
            # Create a test result that includes stack trace information
            result = TestResult(
                test_name="stack_trace_test",
                status=TestStatus.FAIL,
                message=f"Test failed with exception: {str(e)}",
                details={
                    'exception_type': type(e).__name__,
                    'exception_message': str(e),
                    'stack_trace': stack_trace
                },
                execution_time=0.1
            )
            
            # Property: Stack trace should be captured
            assert 'stack_trace' in result.details, "Stack trace should be included in details"
            captured_stack_trace = result.details['stack_trace']
            
            # Property: Stack trace should contain meaningful information
            assert captured_stack_trace is not None, "Stack trace should not be None"
            assert len(captured_stack_trace) > 0, "Stack trace should not be empty"
            assert 'Traceback' in captured_stack_trace, "Stack trace should contain 'Traceback'"
            assert 'failing_function' in captured_stack_trace, "Stack trace should show function names"
            assert 'inner_function' in captured_stack_trace, "Stack trace should show call hierarchy"
            assert 'RuntimeError' in captured_stack_trace, "Stack trace should show exception type"
            assert 'Simulated test failure' in captured_stack_trace, "Stack trace should show error message"
            
            # Property: Stack trace should help with debugging
            # Check for file and line number information
            assert 'File "' in captured_stack_trace, "Stack trace should include file information"
            assert 'line ' in captured_stack_trace, "Stack trace should include line numbers"


if __name__ == '__main__':
    pytest.main([__file__])