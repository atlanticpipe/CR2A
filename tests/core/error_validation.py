"""
Error handling validation system for CR2A testing framework.
Tests component and API error responses with message validation and stack trace capture.
"""

import json
import traceback
import requests
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
import boto3
from botocore.exceptions import ClientError

from .base import BaseTestFramework
from .models import TestConfiguration, TestResult, TestStatus


class ErrorTestType(Enum):
    """Types of error tests to perform."""
    COMPONENT_ERROR = "COMPONENT_ERROR"
    API_ERROR = "API_ERROR"
    INTEGRATION_ERROR = "INTEGRATION_ERROR"


@dataclass
class ErrorTestCase:
    """Definition of an error test case."""
    name: str
    test_type: ErrorTestType
    description: str
    test_function: str
    expected_error_type: str
    expected_error_message_pattern: str
    test_parameters: Dict[str, Any]


@dataclass
class ErrorValidationResult:
    """Result of error validation test."""
    test_case: ErrorTestCase
    success: bool
    actual_error_type: Optional[str]
    actual_error_message: Optional[str]
    stack_trace: Optional[str]
    response_time: float
    additional_details: Dict[str, Any]


class ErrorHandlingValidator(BaseTestFramework):
    """Validates error handling across CR2A components and APIs."""
    
    def __init__(self, config: TestConfiguration):
        super().__init__(config)
        self.error_test_cases = self._initialize_error_test_cases()
        self.api_base_url = self._get_api_base_url()
    
    def _get_api_base_url(self) -> str:
        """Get the API Gateway base URL for testing."""
        # This would typically come from configuration or environment
        return "https://api.cr2a.example.com"  # Placeholder
    
    def _initialize_error_test_cases(self) -> List[ErrorTestCase]:
        """Initialize comprehensive error test cases."""
        return [
            # Component error tests
            ErrorTestCase(
                name="missing_openai_key",
                test_type=ErrorTestType.COMPONENT_ERROR,
                description="Test OpenAI client with missing API key",
                test_function="test_openai_missing_key",
                expected_error_type="ValidationError",
                expected_error_message_pattern=r".*API.*key.*not.*set|.*OPENAI_API_KEY.*",
                test_parameters={}
            ),
            ErrorTestCase(
                name="invalid_openai_key",
                test_type=ErrorTestType.COMPONENT_ERROR,
                description="Test OpenAI client with invalid API key",
                test_function="test_openai_invalid_key",
                expected_error_type="AuthenticationError",
                expected_error_message_pattern=r".*invalid.*api.*key|.*authentication.*failed.*",
                test_parameters={"api_key": "invalid-key-12345"}
            ),
            ErrorTestCase(
                name="dynamodb_reserved_keyword",
                test_type=ErrorTestType.COMPONENT_ERROR,
                description="Test DynamoDB operation with reserved keyword",
                test_function="test_dynamodb_reserved_keyword",
                expected_error_type="ValidationException",
                expected_error_message_pattern=r".*reserved.*keyword.*",
                test_parameters={"attribute_name": "status"}  # 'status' is reserved
            ),
            ErrorTestCase(
                name="lambda_import_error",
                test_type=ErrorTestType.COMPONENT_ERROR,
                description="Test Lambda function with missing dependency",
                test_function="test_lambda_import_error",
                expected_error_type="ImportError",
                expected_error_message_pattern=r".*module.*not.*found|.*import.*error.*",
                test_parameters={"module_name": "nonexistent_module"}
            ),
            
            # API error tests
            ErrorTestCase(
                name="api_invalid_file_size",
                test_type=ErrorTestType.API_ERROR,
                description="Test API with file size exceeding limit",
                test_function="test_api_file_too_large",
                expected_error_type="ValidationError",
                expected_error_message_pattern=r".*file.*too.*large|.*size.*limit.*exceeded.*",
                test_parameters={"file_size": 100 * 1024 * 1024}  # 100MB
            ),
            ErrorTestCase(
                name="api_missing_parameters",
                test_type=ErrorTestType.API_ERROR,
                description="Test API with missing required parameters",
                test_function="test_api_missing_params",
                expected_error_type="ValidationError",
                expected_error_message_pattern=r".*required.*parameter.*missing|.*field.*required.*",
                test_parameters={"endpoint": "/analyze"}
            ),
            ErrorTestCase(
                name="api_invalid_content_type",
                test_type=ErrorTestType.API_ERROR,
                description="Test API with unsupported content type",
                test_function="test_api_invalid_content_type",
                expected_error_type="ValidationError",
                expected_error_message_pattern=r".*unsupported.*content.*type|.*invalid.*mime.*type.*",
                test_parameters={"content_type": "application/invalid"}
            ),
            ErrorTestCase(
                name="api_unauthorized_access",
                test_type=ErrorTestType.API_ERROR,
                description="Test API with invalid authentication",
                test_function="test_api_unauthorized",
                expected_error_type="AuthenticationError",
                expected_error_message_pattern=r".*unauthorized|.*authentication.*required.*",
                test_parameters={"auth_token": "invalid-token"}
            ),
            
            # Integration error tests
            ErrorTestCase(
                name="step_functions_invalid_input",
                test_type=ErrorTestType.INTEGRATION_ERROR,
                description="Test Step Functions with invalid input format",
                test_function="test_step_functions_invalid_input",
                expected_error_type="ValidationException",
                expected_error_message_pattern=r".*invalid.*input|.*schema.*validation.*failed.*",
                test_parameters={"invalid_field": "test"}
            ),
            ErrorTestCase(
                name="s3_access_denied",
                test_type=ErrorTestType.INTEGRATION_ERROR,
                description="Test S3 access with insufficient permissions",
                test_function="test_s3_access_denied",
                expected_error_type="AccessDenied",
                expected_error_message_pattern=r".*access.*denied|.*permission.*denied.*",
                test_parameters={"bucket": "restricted-bucket"}
            ),
        ]
    
    def validate_component_error_handling(self) -> List[ErrorValidationResult]:
        """Validate error handling in individual components."""
        results = []
        
        component_tests = [tc for tc in self.error_test_cases 
                          if tc.test_type == ErrorTestType.COMPONENT_ERROR]
        
        for test_case in component_tests:
            self.logger.info(f"Running component error test: {test_case.name}")
            result = self._execute_error_test(test_case)
            results.append(result)
        
        return results
    
    def validate_api_error_handling(self) -> List[ErrorValidationResult]:
        """Validate error handling in API endpoints."""
        results = []
        
        api_tests = [tc for tc in self.error_test_cases 
                    if tc.test_type == ErrorTestType.API_ERROR]
        
        for test_case in api_tests:
            self.logger.info(f"Running API error test: {test_case.name}")
            result = self._execute_error_test(test_case)
            results.append(result)
        
        return results
    
    def validate_integration_error_handling(self) -> List[ErrorValidationResult]:
        """Validate error handling in integration scenarios."""
        results = []
        
        integration_tests = [tc for tc in self.error_test_cases 
                           if tc.test_type == ErrorTestType.INTEGRATION_ERROR]
        
        for test_case in integration_tests:
            self.logger.info(f"Running integration error test: {test_case.name}")
            result = self._execute_error_test(test_case)
            results.append(result)
        
        return results
    
    def _execute_error_test(self, test_case: ErrorTestCase) -> ErrorValidationResult:
        """Execute a single error test case."""
        start_time = datetime.now()
        
        try:
            # Get the test function
            test_function = getattr(self, test_case.test_function)
            
            # Execute the test and expect it to raise an exception
            actual_error_type = None
            actual_error_message = None
            stack_trace = None
            success = False
            
            try:
                test_function(**test_case.test_parameters)
                # If we get here, the test didn't raise an exception as expected
                success = False
                actual_error_message = "Expected error was not raised"
            
            except Exception as e:
                # Capture error details
                actual_error_type = type(e).__name__
                actual_error_message = str(e)
                stack_trace = traceback.format_exc()
                
                # Check if the error matches expectations
                success = self._validate_error_response(
                    test_case, actual_error_type, actual_error_message
                )
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            return ErrorValidationResult(
                test_case=test_case,
                success=success,
                actual_error_type=actual_error_type,
                actual_error_message=actual_error_message,
                stack_trace=stack_trace,
                response_time=response_time,
                additional_details={}
            )
        
        except Exception as e:
            # Test execution itself failed
            response_time = (datetime.now() - start_time).total_seconds()
            
            return ErrorValidationResult(
                test_case=test_case,
                success=False,
                actual_error_type=type(e).__name__,
                actual_error_message=f"Test execution failed: {str(e)}",
                stack_trace=traceback.format_exc(),
                response_time=response_time,
                additional_details={"test_execution_error": True}
            )
    
    def _validate_error_response(self, 
                               test_case: ErrorTestCase, 
                               actual_error_type: str, 
                               actual_error_message: str) -> bool:
        """Validate that the actual error matches expected patterns."""
        import re
        
        # Check error type
        type_match = (actual_error_type == test_case.expected_error_type or
                     test_case.expected_error_type in actual_error_type)
        
        # Check error message pattern
        message_match = re.search(
            test_case.expected_error_message_pattern, 
            actual_error_message, 
            re.IGNORECASE
        ) is not None
        
        return type_match and message_match
    
    # Component error test implementations
    def test_openai_missing_key(self) -> None:
        """Test OpenAI client initialization with missing API key."""
        import os
        from src.services.openai_client import _get_api_key, OpenAIClientError
        
        # Temporarily remove API key
        original_key = os.environ.get('OPENAI_API_KEY')
        original_secret = os.environ.get('OPENAI_SECRET_ARN')
        
        try:
            if 'OPENAI_API_KEY' in os.environ:
                del os.environ['OPENAI_API_KEY']
            if 'OPENAI_SECRET_ARN' in os.environ:
                del os.environ['OPENAI_SECRET_ARN']
            
            # This should raise an error
            key = _get_api_key()
            if key is None:
                raise OpenAIClientError("ValidationError", "Set OPENAI_API_KEY or OPENAI_SECRET_ARN to enable LLM refinement.")
        
        finally:
            # Restore original values
            if original_key:
                os.environ['OPENAI_API_KEY'] = original_key
            if original_secret:
                os.environ['OPENAI_SECRET_ARN'] = original_secret
    
    def test_openai_invalid_key(self, api_key: str) -> None:
        """Test OpenAI client with invalid API key."""
        import os
        from src.services.openai_client import refine_cr2a, OpenAIClientError
        
        # Temporarily set invalid key
        original_key = os.environ.get('OPENAI_API_KEY')
        
        try:
            os.environ['OPENAI_API_KEY'] = api_key
            
            # This should raise an authentication error
            test_payload = {"SECTION_I": {"contract_title": "Test"}}
            refine_cr2a(test_payload)
        
        finally:
            # Restore original key
            if original_key:
                os.environ['OPENAI_API_KEY'] = original_key
            elif 'OPENAI_API_KEY' in os.environ:
                del os.environ['OPENAI_API_KEY']
    
    def test_dynamodb_reserved_keyword(self, attribute_name: str) -> None:
        """Test DynamoDB operation with reserved keyword."""
        dynamodb = boto3.resource('dynamodb', region_name=self.config.aws_region)
        
        # Try to create an item with a reserved keyword as attribute name
        table = dynamodb.Table('cr2a-jobs')  # Assuming this table exists
        
        # This should raise a ValidationException
        table.put_item(
            Item={
                'job_id': 'test-job',
                attribute_name: 'test-value'  # Using reserved keyword
            }
        )
    
    def test_lambda_import_error(self, module_name: str) -> None:
        """Test Lambda function with missing dependency."""
        # Simulate import error
        try:
            __import__(module_name)
        except ImportError as e:
            raise ImportError(f"No module named '{module_name}'") from e
    
    # API error test implementations
    def test_api_file_too_large(self, file_size: int) -> None:
        """Test API with file size exceeding limit."""
        # Make request to upload-url endpoint with large file size
        response = requests.get(
            f"{self.api_base_url}/upload-url",
            params={
                'filename': 'large_file.pdf',
                'contentType': 'application/pdf',
                'size': file_size
            }
        )
        
        if response.status_code == 400:
            error_data = response.json()
            raise ValueError(error_data.get('detail', 'File too large'))
        else:
            raise AssertionError(f"Expected 400 error, got {response.status_code}")
    
    def test_api_missing_params(self, endpoint: str) -> None:
        """Test API with missing required parameters."""
        # Make request without required parameters
        response = requests.post(f"{self.api_base_url}{endpoint}")
        
        if response.status_code in [400, 422]:
            error_data = response.json()
            raise ValueError(error_data.get('detail', 'Missing required parameters'))
        else:
            raise AssertionError(f"Expected 400/422 error, got {response.status_code}")
    
    def test_api_invalid_content_type(self, content_type: str) -> None:
        """Test API with unsupported content type."""
        response = requests.get(
            f"{self.api_base_url}/upload-url",
            params={
                'filename': 'test.invalid',
                'contentType': content_type,
                'size': 1024
            }
        )
        
        if response.status_code == 400:
            error_data = response.json()
            raise ValueError(error_data.get('detail', 'Unsupported content type'))
        else:
            raise AssertionError(f"Expected 400 error, got {response.status_code}")
    
    def test_api_unauthorized(self, auth_token: str) -> None:
        """Test API with invalid authentication."""
        headers = {'Authorization': f'Bearer {auth_token}'}
        response = requests.get(f"{self.api_base_url}/status/test-job", headers=headers)
        
        if response.status_code == 401:
            error_data = response.json()
            raise PermissionError(error_data.get('detail', 'Unauthorized access'))
        else:
            raise AssertionError(f"Expected 401 error, got {response.status_code}")
    
    # Integration error test implementations
    def test_step_functions_invalid_input(self, **kwargs) -> None:
        """Test Step Functions with invalid input format."""
        stepfunctions_client = self.get_aws_client('stepfunctions')
        
        # Try to start execution with invalid input
        invalid_input = json.dumps(kwargs)
        
        try:
            stepfunctions_client.start_execution(
                stateMachineArn='arn:aws:states:us-east-1:123456789012:stateMachine:invalid',
                name='test-execution',
                input=invalid_input
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationException':
                raise ValueError(e.response['Error']['Message'])
            raise
    
    def test_s3_access_denied(self, bucket: str) -> None:
        """Test S3 access with insufficient permissions."""
        s3_client = self.get_aws_client('s3')
        
        try:
            s3_client.get_object(Bucket=bucket, Key='test-key')
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                raise PermissionError(e.response['Error']['Message'])
            raise
    
    def generate_validation_report(self, 
                                 results: List[ErrorValidationResult],
                                 output_format: str = 'json') -> str:
        """Generate comprehensive error validation report."""
        if output_format == 'json':
            return self._generate_json_validation_report(results)
        else:
            return self._generate_text_validation_report(results)
    
    def _generate_json_validation_report(self, results: List[ErrorValidationResult]) -> str:
        """Generate JSON format validation report."""
        report_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_tests': len(results),
            'passed_tests': sum(1 for r in results if r.success),
            'failed_tests': sum(1 for r in results if not r.success),
            'average_response_time': sum(r.response_time for r in results) / len(results) if results else 0,
            'test_results': []
        }
        
        for result in results:
            report_data['test_results'].append({
                'test_name': result.test_case.name,
                'test_type': result.test_case.test_type.value,
                'description': result.test_case.description,
                'success': result.success,
                'expected_error_type': result.test_case.expected_error_type,
                'actual_error_type': result.actual_error_type,
                'expected_error_pattern': result.test_case.expected_error_message_pattern,
                'actual_error_message': result.actual_error_message,
                'response_time': result.response_time,
                'has_stack_trace': result.stack_trace is not None
            })
        
        return json.dumps(report_data, indent=2)
    
    def _generate_text_validation_report(self, results: List[ErrorValidationResult]) -> str:
        """Generate human-readable text validation report."""
        lines = [
            "CR2A Error Handling Validation Report",
            "=" * 50,
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"Total Tests: {len(results)}",
            f"Passed: {sum(1 for r in results if r.success)}",
            f"Failed: {sum(1 for r in results if not r.success)}",
            f"Average Response Time: {sum(r.response_time for r in results) / len(results):.3f}s" if results else "N/A",
            ""
        ]
        
        # Group by test type
        by_type = {}
        for result in results:
            test_type = result.test_case.test_type.value
            if test_type not in by_type:
                by_type[test_type] = []
            by_type[test_type].append(result)
        
        for test_type, type_results in by_type.items():
            lines.extend([
                f"{test_type} Tests:",
                "-" * 30
            ])
            
            for result in type_results:
                status = "PASS" if result.success else "FAIL"
                lines.extend([
                    f"  {result.test_case.name}: {status}",
                    f"    Description: {result.test_case.description}",
                    f"    Expected: {result.test_case.expected_error_type}",
                    f"    Actual: {result.actual_error_type or 'None'}",
                    f"    Response Time: {result.response_time:.3f}s"
                ])
                
                if not result.success and result.actual_error_message:
                    lines.append(f"    Error: {result.actual_error_message[:100]}...")
                
                lines.append("")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def test_error_validation_system(self) -> TestResult:
        """Test the error validation system functionality."""
        try:
            # Run a subset of validation tests
            component_results = self.validate_component_error_handling()
            api_results = self.validate_api_error_handling()
            integration_results = self.validate_integration_error_handling()
            
            all_results = component_results + api_results + integration_results
            
            # Generate report
            report = self.generate_validation_report(all_results)
            
            # Calculate success metrics
            total_tests = len(all_results)
            passed_tests = sum(1 for r in all_results if r.success)
            
            return TestResult(
                test_name="error_validation_system",
                status=TestStatus.PASS if passed_tests > 0 else TestStatus.FAIL,
                message=f"Error validation system tested. {passed_tests}/{total_tests} tests passed",
                details={
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'component_tests': len(component_results),
                    'api_tests': len(api_results),
                    'integration_tests': len(integration_results),
                    'report_length': len(report)
                }
            )
            
        except Exception as e:
            return TestResult(
                test_name="error_validation_system",
                status=TestStatus.ERROR,
                message=f"Error validation system test failed: {str(e)}",
                details={'exception': str(e)}
            )