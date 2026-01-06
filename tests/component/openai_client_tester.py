"""
Component tester for OpenAI client initialization and connectivity.
Tests OpenAI client with various API key configurations and connection scenarios.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from unittest.mock import patch, MagicMock

from tests.core.base import BaseTestFramework
from tests.core.interfaces import ComponentTester
from tests.core.models import TestResult, TestStatus, ComponentTestReport, TestConfiguration


class OpenAIClientTester(BaseTestFramework, ComponentTester):
    """Tests OpenAI client initialization and connectivity."""
    
    def __init__(self, config: TestConfiguration):
        super().__init__(config)
        self.test_results: List[TestResult] = []
    
    def test_dependencies(self) -> TestResult:
        """Test Lambda layer dependencies and package imports."""
        # This is implemented in the dependency tester
        return TestResult(
            test_name="test_dependencies",
            status=TestStatus.SKIP,
            message="Dependency testing handled by dedicated dependency tester"
        )
    
    def test_openai_client(self) -> TestResult:
        """Test OpenAI client initialization with various API key configurations."""
        def _test_openai_client():
            try:
                # Import OpenAI client functionality
                from src.services.openai_client import _get_api_key, OpenAIClientError, _call_openai
                
                test_results = {
                    "api_key_retrieval": None,
                    "client_initialization": None,
                    "error_handling": None
                }
                
                # Test 1: API key retrieval
                try:
                    # Test with environment variable
                    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key-123'}):
                        api_key = _get_api_key()
                        if api_key == 'test-key-123':
                            test_results["api_key_retrieval"] = "PASS: Environment variable retrieval works"
                        else:
                            test_results["api_key_retrieval"] = f"FAIL: Expected 'test-key-123', got '{api_key}'"
                    
                    # Test with no API key
                    with patch.dict(os.environ, {}, clear=True):
                        api_key = _get_api_key()
                        if api_key is None:
                            test_results["api_key_retrieval"] += " | PASS: Handles missing API key correctly"
                        else:
                            test_results["api_key_retrieval"] += f" | FAIL: Expected None, got '{api_key}'"
                
                except Exception as e:
                    test_results["api_key_retrieval"] = f"ERROR: {str(e)}"
                
                # Test 2: Client initialization patterns
                try:
                    # Test OpenAI client error creation
                    error = OpenAIClientError("TestCategory", "Test message")
                    if error.category == "TestCategory" and str(error) == "Test message":
                        test_results["client_initialization"] = "PASS: OpenAIClientError creation works"
                    else:
                        test_results["client_initialization"] = "FAIL: OpenAIClientError not working correctly"
                
                except Exception as e:
                    test_results["client_initialization"] = f"ERROR: {str(e)}"
                
                # Test 3: Error handling patterns
                try:
                    # Test that client functions handle missing API keys appropriately
                    with patch.dict(os.environ, {}, clear=True):
                        try:
                            from src.services.openai_client import refine_cr2a
                            # This should raise an OpenAIClientError for missing API key
                            refine_cr2a({})
                            test_results["error_handling"] = "FAIL: Should have raised error for missing API key"
                        except OpenAIClientError as e:
                            if "OPENAI_API_KEY" in str(e) or "ValidationError" in e.category:
                                test_results["error_handling"] = "PASS: Correctly handles missing API key"
                            else:
                                test_results["error_handling"] = f"FAIL: Wrong error type: {e.category} - {str(e)}"
                        except Exception as e:
                            test_results["error_handling"] = f"FAIL: Unexpected error type: {type(e).__name__} - {str(e)}"
                
                except Exception as e:
                    test_results["error_handling"] = f"ERROR: {str(e)}"
                
                # Determine overall result
                failures = [k for k, v in test_results.items() if v and ("FAIL" in v or "ERROR" in v)]
                
                if failures:
                    return TestResult(
                        test_name="openai_client_initialization",
                        status=TestStatus.FAIL,
                        message=f"OpenAI client tests failed: {len(failures)} issues found",
                        details=test_results
                    )
                else:
                    return TestResult(
                        test_name="openai_client_initialization",
                        status=TestStatus.PASS,
                        message="OpenAI client initialization tests passed",
                        details=test_results
                    )
            
            except ImportError as e:
                return TestResult(
                    test_name="openai_client_initialization",
                    status=TestStatus.ERROR,
                    message=f"Cannot import OpenAI client modules: {str(e)}",
                    details={"import_error": str(e)}
                )
            except Exception as e:
                return TestResult(
                    test_name="openai_client_initialization",
                    status=TestStatus.ERROR,
                    message=f"Unexpected error during OpenAI client testing: {str(e)}",
                    details={"error": str(e), "error_type": type(e).__name__}
                )
        
        return self.execute_test_with_timing("test_openai_client", _test_openai_client)
    
    def test_dynamodb_operations(self) -> TestResult:
        """Test DynamoDB operations and reserved keyword handling."""
        # This is implemented in the DynamoDB operations tester
        return TestResult(
            test_name="test_dynamodb_operations",
            status=TestStatus.SKIP,
            message="DynamoDB operations testing handled by dedicated DynamoDB tester"
        )
    
    def test_openai_configuration(self) -> TestResult:
        """Test OpenAI configuration and environment variables."""
        def _test_configuration():
            config_tests = {
                "base_url": None,
                "model_default": None,
                "timeout": None,
                "temperature": None
            }
            
            try:
                # Test default configuration values
                with patch.dict(os.environ, {}, clear=True):
                    from src.services.openai_client import OPENAI_BASE, OPENAI_MODEL_DEFAULT
                    
                    if OPENAI_BASE == "https://api.openai.com":
                        config_tests["base_url"] = "PASS: Default base URL correct"
                    else:
                        config_tests["base_url"] = f"FAIL: Expected 'https://api.openai.com', got '{OPENAI_BASE}'"
                    
                    if OPENAI_MODEL_DEFAULT == "gpt-4o-mini":
                        config_tests["model_default"] = "PASS: Default model correct"
                    else:
                        config_tests["model_default"] = f"FAIL: Expected 'gpt-4o-mini', got '{OPENAI_MODEL_DEFAULT}'"
                
                # Test environment variable overrides
                test_timeout = os.getenv('OPENAI_TIMEOUT_SECONDS', '120')
                test_temperature = os.getenv('OPENAI_TEMPERATURE', '0.5')
                
                with patch.dict(os.environ, {
                    'OPENAI_BASE_URL': 'https://custom.openai.com',
                    'OPENAI_MODEL': 'gpt-4',
                    'OPENAI_TIMEOUT_SECONDS': test_timeout,
                    'OPENAI_TEMPERATURE': test_temperature
                }):
                    # Re-import to get updated values
                    import importlib
                    import src.services.openai_client
                    importlib.reload(src.services.openai_client)
                    
                    if src.services.openai_client.OPENAI_BASE == "https://custom.openai.com":
                        config_tests["base_url"] += " | PASS: Environment override works"
                    else:
                        config_tests["base_url"] += f" | FAIL: Override failed, got '{src.services.openai_client.OPENAI_BASE}'"
                
                # Test timeout and temperature parsing
                timeout_val = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))
                temp_val = float(os.getenv("OPENAI_TEMPERATURE", "0"))
                
                # Validate timeout is within reasonable range (5-600 seconds)
                if 5 <= timeout_val <= 600:
                    config_tests["timeout"] = f"PASS: Timeout parsing works ({timeout_val}s)"
                else:
                    config_tests["timeout"] = f"FAIL: Timeout {timeout_val}s outside valid range (5-600s)"
                
                # Validate temperature is within OpenAI's valid range (0.0-2.0)
                if 0.0 <= temp_val <= 2.0:
                    config_tests["temperature"] = f"PASS: Temperature parsing works ({temp_val})"
                else:
                    config_tests["temperature"] = f"FAIL: Temperature {temp_val} outside valid range (0.0-2.0)"
            
            except Exception as e:
                for key in config_tests:
                    if config_tests[key] is None:
                        config_tests[key] = f"ERROR: {str(e)}"
            
            # Determine result
            failures = [k for k, v in config_tests.items() if v and ("FAIL" in v or "ERROR" in v)]
            
            if failures:
                return TestResult(
                    test_name="openai_configuration",
                    status=TestStatus.FAIL,
                    message=f"OpenAI configuration issues: {len(failures)} problems found",
                    details=config_tests
                )
            else:
                return TestResult(
                    test_name="openai_configuration",
                    status=TestStatus.PASS,
                    message="OpenAI configuration tests passed",
                    details=config_tests
                )
        
        return self.execute_test_with_timing("test_openai_configuration", _test_configuration)
    
    def test_openai_request_structure(self) -> TestResult:
        """Test OpenAI request structure and payload formatting."""
        def _test_request_structure():
            try:
                from src.services.openai_client import _parse_json_payload, _extract_text
                
                structure_tests = {
                    "json_parsing": None,
                    "text_extraction": None,
                    "error_recovery": None
                }
                
                # Test JSON parsing
                try:
                    # Valid JSON
                    valid_json = '{"test": "value", "number": 42}'
                    parsed = _parse_json_payload(valid_json)
                    if parsed == {"test": "value", "number": 42}:
                        structure_tests["json_parsing"] = "PASS: Valid JSON parsing works"
                    else:
                        structure_tests["json_parsing"] = f"FAIL: Parsing incorrect, got {parsed}"
                    
                    # JSON with trailing comma (should be fixed)
                    trailing_comma_json = '{"test": "value", "number": 42,}'
                    try:
                        parsed = _parse_json_payload(trailing_comma_json)
                        structure_tests["json_parsing"] += " | PASS: Trailing comma recovery works"
                    except Exception:
                        structure_tests["json_parsing"] += " | FAIL: Trailing comma recovery failed"
                
                except Exception as e:
                    structure_tests["json_parsing"] = f"ERROR: {str(e)}"
                
                # Test text extraction
                try:
                    # Test Responses API format
                    responses_format = {
                        "output": [{
                            "content": [{"type": "text", "text": "extracted text"}]
                        }]
                    }
                    extracted = _extract_text(responses_format)
                    if extracted == "extracted text":
                        structure_tests["text_extraction"] = "PASS: Responses API text extraction works"
                    else:
                        structure_tests["text_extraction"] = f"FAIL: Expected 'extracted text', got '{extracted}'"
                    
                    # Test Chat API format
                    chat_format = {
                        "choices": [{
                            "message": {"content": "chat response"}
                        }]
                    }
                    extracted = _extract_text(chat_format)
                    if extracted == "chat response":
                        structure_tests["text_extraction"] += " | PASS: Chat API text extraction works"
                    else:
                        structure_tests["text_extraction"] += f" | FAIL: Expected 'chat response', got '{extracted}'"
                
                except Exception as e:
                    structure_tests["text_extraction"] = f"ERROR: {str(e)}"
                
                # Test error recovery
                try:
                    # Invalid JSON should raise OpenAIClientError
                    from src.services.openai_client import OpenAIClientError
                    try:
                        _parse_json_payload('{"invalid": json}')
                        structure_tests["error_recovery"] = "FAIL: Should have raised error for invalid JSON"
                    except OpenAIClientError as e:
                        if "ProcessingError" in e.category:
                            structure_tests["error_recovery"] = "PASS: Correctly handles invalid JSON"
                        else:
                            structure_tests["error_recovery"] = f"FAIL: Wrong error category: {e.category}"
                    except Exception as e:
                        structure_tests["error_recovery"] = f"FAIL: Wrong exception type: {type(e).__name__}"
                
                except Exception as e:
                    structure_tests["error_recovery"] = f"ERROR: {str(e)}"
                
                # Determine result
                failures = [k for k, v in structure_tests.items() if v and ("FAIL" in v or "ERROR" in v)]
                
                if failures:
                    return TestResult(
                        test_name="openai_request_structure",
                        status=TestStatus.FAIL,
                        message=f"OpenAI request structure issues: {len(failures)} problems found",
                        details=structure_tests
                    )
                else:
                    return TestResult(
                        test_name="openai_request_structure",
                        status=TestStatus.PASS,
                        message="OpenAI request structure tests passed",
                        details=structure_tests
                    )
            
            except ImportError as e:
                return TestResult(
                    test_name="openai_request_structure",
                    status=TestStatus.ERROR,
                    message=f"Cannot import OpenAI client functions: {str(e)}",
                    details={"import_error": str(e)}
                )
            except Exception as e:
                return TestResult(
                    test_name="openai_request_structure",
                    status=TestStatus.ERROR,
                    message=f"Unexpected error during request structure testing: {str(e)}",
                    details={"error": str(e), "error_type": type(e).__name__}
                )
        
        return self.execute_test_with_timing("test_openai_request_structure", _test_request_structure)
    
    def generate_test_report(self) -> ComponentTestReport:
        """Generate comprehensive component test report."""
        # Run all OpenAI client tests
        client_test = self.test_openai_client()
        config_test = self.test_openai_configuration()
        structure_test = self.test_openai_request_structure()
        
        all_tests = [client_test, config_test, structure_test]
        
        # Determine overall status
        failed_tests = [t for t in all_tests if t.status == TestStatus.FAIL]
        error_tests = [t for t in all_tests if t.status == TestStatus.ERROR]
        
        if error_tests:
            overall_status = TestStatus.ERROR
        elif failed_tests:
            overall_status = TestStatus.FAIL
        else:
            overall_status = TestStatus.PASS
        
        # Generate recommendations
        recommendations = []
        if failed_tests:
            recommendations.append("Fix OpenAI client configuration issues before deployment")
        if any("api key" in t.message.lower() for t in failed_tests):
            recommendations.append("Ensure OPENAI_API_KEY environment variable is properly configured")
        if any("import" in t.message.lower() for t in error_tests):
            recommendations.append("Verify OpenAI package is installed in Lambda layer")
        
        return ComponentTestReport(
            lambda_function="openai_client",
            dependency_tests=[],  # Handled by other testers
            client_tests=all_tests,
            database_tests=[],  # Handled by other testers
            overall_status=overall_status,
            recommendations=recommendations
        )


def create_lambda_openai_test_function() -> str:
    """
    Create a Lambda function that can be deployed to test OpenAI client in the actual Lambda environment.
    Returns the function code as a string.
    """
    return '''
import json
import os
from typing import Dict, Any

def lambda_handler(event, context):
    """
    Lambda function to test OpenAI client functionality in the actual Lambda environment.
    """
    results = {
        'openai_import': None,
        'api_key_access': None,
        'client_creation': None,
        'environment_info': {
            'openai_base_url': os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com'),
            'openai_model': os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
            'has_api_key': bool(os.environ.get('OPENAI_API_KEY')),
            'has_secret_arn': bool(os.environ.get('OPENAI_SECRET_ARN'))
        }
    }
    
    # Test OpenAI import
    try:
        from src.services.openai_client import _get_api_key, OpenAIClientError
        results['openai_import'] = 'SUCCESS: OpenAI client modules imported'
    except ImportError as e:
        results['openai_import'] = f'FAIL: Import error - {str(e)}'
        return {'statusCode': 500, 'body': json.dumps(results)}
    except Exception as e:
        results['openai_import'] = f'ERROR: Unexpected error - {str(e)}'
        return {'statusCode': 500, 'body': json.dumps(results)}
    
    # Test API key retrieval
    try:
        api_key = _get_api_key()
        if api_key:
            results['api_key_access'] = 'SUCCESS: API key retrieved (length: {})'.format(len(api_key))
        else:
            results['api_key_access'] = 'FAIL: No API key available'
    except Exception as e:
        results['api_key_access'] = f'ERROR: API key retrieval failed - {str(e)}'
    
    # Test client error handling
    try:
        error = OpenAIClientError("TestCategory", "Test message")
        if error.category == "TestCategory":
            results['client_creation'] = 'SUCCESS: OpenAI client error handling works'
        else:
            results['client_creation'] = 'FAIL: OpenAI client error handling broken'
    except Exception as e:
        results['client_creation'] = f'ERROR: Client creation test failed - {str(e)}'
    
    return {
        'statusCode': 200,
        'body': json.dumps(results, indent=2)
    }
'''


if __name__ == "__main__":
    # Example usage for local testing
    config = TestConfiguration(
        aws_region="us-east-1",
        verbose_logging=True
    )
    
    tester = OpenAIClientTester(config)
    report = tester.generate_test_report()
    
    print(f"OpenAI Client Test Report - Overall Status: {report.overall_status.value}")
    print(f"Tests Run: {len(report.client_tests)}")
    
    for test in report.client_tests:
        print(f"  {test.test_name}: {test.status.value} - {test.message}")
    
    if report.recommendations:
        print("\nRecommendations:")
        for rec in report.recommendations:
            print(f"  - {rec}")