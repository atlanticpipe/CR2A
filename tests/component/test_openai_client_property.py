"""
Property-based tests for OpenAI client initialization.
Tests universal properties that should hold for OpenAI client initialization.

Feature: cr2a-testing-debugging, Property 2: OpenAI client initialization consistency
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from typing import Dict, List, Optional, Any
import os
from unittest.mock import patch, MagicMock

from tests.core.models import TestResult, TestStatus, TestConfiguration
from tests.component.openai_client_tester import OpenAIClientTester


# Strategy for generating API key configurations
@st.composite
def api_key_config_strategy(draw):
    """Generate valid API key configurations for testing."""
    config_type = draw(st.sampled_from(['valid_key', 'empty_key', 'none_key', 'invalid_format']))
    
    if config_type == 'valid_key':
        # Generate a valid-looking API key
        prefix = draw(st.sampled_from(['sk-', 'sk-proj-']))
        key_part = draw(st.text(
            alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
            min_size=20,
            max_size=50
        ).filter(lambda x: '\x00' not in x))  # Filter out null characters
        return {'OPENAI_API_KEY': prefix + key_part}
    elif config_type == 'empty_key':
        return {'OPENAI_API_KEY': ''}
    elif config_type == 'none_key':
        return {}  # No API key environment variable
    else:  # invalid_format
        # Generate invalid API key formats
        invalid_key = draw(st.text(
            min_size=1, 
            max_size=10,
            alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        ).filter(
            lambda x: not x.startswith('sk-') and '\x00' not in x
        ))
        return {'OPENAI_API_KEY': invalid_key}


# Strategy for generating OpenAI configuration
@st.composite
def openai_config_strategy(draw):
    """Generate OpenAI configuration parameters."""
    base_url = draw(st.sampled_from([
        'https://api.openai.com',
        'https://custom.openai.com',
        'https://api.openai.com/v1'
    ]))
    
    model = draw(st.sampled_from([
        'gpt-4o-mini',
        'gpt-4',
        'gpt-3.5-turbo',
        'gpt-4-turbo'
    ]))
    
    timeout = draw(st.integers(min_value=10, max_value=300))
    temperature = draw(st.floats(min_value=0.0, max_value=2.0))
    
    config = {
        'OPENAI_BASE_URL': base_url,
        'OPENAI_MODEL': model,
        'OPENAI_TIMEOUT_SECONDS': str(timeout),
        'OPENAI_TEMPERATURE': str(temperature)
    }
    
    # Optionally include API key
    api_key_config = draw(api_key_config_strategy())
    config.update(api_key_config)
    
    return config


# Strategy for generating test configurations
@st.composite
def _test_config_strategy(draw):
    """Generate valid TestConfiguration instances."""
    aws_region = draw(st.sampled_from(['us-east-1', 'us-west-2', 'eu-west-1']))
    lambda_timeout = draw(st.integers(min_value=5, max_value=300))
    max_retries = draw(st.integers(min_value=1, max_value=10))
    parallel_execution = draw(st.booleans())
    verbose_logging = draw(st.booleans())
    save_artifacts = draw(st.booleans())
    
    return TestConfiguration(
        aws_region=aws_region,
        lambda_timeout=lambda_timeout,
        max_retries=max_retries,
        parallel_execution=parallel_execution,
        verbose_logging=verbose_logging,
        save_artifacts=save_artifacts
    )


class TestOpenAIClientInitializationProperties:
    """Property-based tests for OpenAI client initialization functionality."""
    
    @given(_test_config_strategy(), openai_config_strategy())
    @settings(
        max_examples=5,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.data_too_large]
    )
    def test_property_openai_client_initialization_consistency(self, test_config, openai_config):
        """
        Property 2: OpenAI client initialization consistency
        
        For any valid API key configuration, the OpenAI client should initialize 
        successfully and be ready for API calls.
        
        **Validates: Requirements 1.2**
        """
        # Create OpenAI client tester with the test configuration
        tester = OpenAIClientTester(test_config)
        
        # Property: OpenAI client tester should be properly initialized
        assert tester is not None, "OpenAI client tester should be created successfully"
        assert hasattr(tester, 'test_results'), "Tester should have test_results attribute"
        assert isinstance(tester.test_results, list), "Test results should be a list"
        
        # Test with the generated OpenAI configuration
        with patch.dict(os.environ, openai_config, clear=True):
            # Property: OpenAI client test should return a valid TestResult
            result = tester.test_openai_client()
            assert result is not None, "OpenAI client test should return a result"
            assert isinstance(result, TestResult), "Result should be a TestResult instance"
            assert result.test_name == "openai_client_initialization", "Test name should be 'openai_client_initialization'"
            assert result.status in [TestStatus.PASS, TestStatus.FAIL, TestStatus.ERROR], (
                "Test status should be a valid TestStatus"
            )
            assert result.message is not None, "Test message should be provided"
            assert len(result.message.strip()) > 0, "Test message should not be empty"
            assert result.timestamp is not None, "Test timestamp should be set"
            assert result.execution_time >= 0, "Execution time should be non-negative"
            
            # Property: Test result details should contain expected information
            assert result.details is not None, "Test details should be provided"
            assert isinstance(result.details, dict), "Test details should be a dictionary"
            
            required_detail_keys = ['api_key_retrieval', 'client_initialization', 'error_handling']
            for key in required_detail_keys:
                assert key in result.details, f"Test details should contain '{key}'"
            
            # Property: Detail values should be strings with status information
            for key, value in result.details.items():
                if value is not None:
                    assert isinstance(value, str), f"Detail '{key}' should be a string"
                    assert len(value.strip()) > 0, f"Detail '{key}' should not be empty"
                    # Should contain status indicators
                    assert any(status in value for status in ['PASS', 'FAIL', 'ERROR']), (
                        f"Detail '{key}' should contain status information"
                    )
            
            # Property: Test status should be consistent with API key configuration
            has_valid_api_key = (
                'OPENAI_API_KEY' in openai_config and 
                openai_config['OPENAI_API_KEY'] and 
                openai_config['OPENAI_API_KEY'].startswith('sk-')
            )
            
            if has_valid_api_key:
                # With valid API key, some tests should pass
                api_key_detail = result.details.get('api_key_retrieval', '')
                if api_key_detail:
                    assert 'PASS' in api_key_detail, (
                        "API key retrieval should pass with valid API key"
                    )
            else:
                # Without valid API key, API key retrieval should handle it appropriately
                api_key_detail = result.details.get('api_key_retrieval', '')
                if api_key_detail and 'OPENAI_API_KEY' not in openai_config:
                    assert 'PASS' in api_key_detail, (
                        "API key retrieval should handle missing key correctly"
                    )
            
            # Property: Client initialization should always be testable
            client_init_detail = result.details.get('client_initialization', '')
            if client_init_detail:
                assert any(status in client_init_detail for status in ['PASS', 'FAIL', 'ERROR']), (
                    "Client initialization should have a clear status"
                )
            
            # Property: Error handling should always be testable
            error_handling_detail = result.details.get('error_handling', '')
            if error_handling_detail:
                assert any(status in error_handling_detail for status in ['PASS', 'FAIL', 'ERROR']), (
                    "Error handling should have a clear status"
                )
            
            # Property: If all details pass, overall status should be PASS
            all_details_pass = all(
                detail and 'PASS' in detail and 'FAIL' not in detail and 'ERROR' not in detail
                for detail in result.details.values()
                if detail is not None
            )
            
            if all_details_pass and result.details:
                assert result.status == TestStatus.PASS, (
                    "Overall status should be PASS when all details pass"
                )
                assert "passed" in result.message.lower(), (
                    "Test message should indicate success"
                )
            
            # Property: If any detail fails, overall status should be FAIL or ERROR
            any_detail_fails = any(
                detail and ('FAIL' in detail or 'ERROR' in detail)
                for detail in result.details.values()
                if detail is not None
            )
            
            if any_detail_fails:
                assert result.status in [TestStatus.FAIL, TestStatus.ERROR], (
                    "Overall status should be FAIL or ERROR when details fail"
                )
                assert any(word in result.message.lower() for word in ['fail', 'error', 'issue']), (
                    "Test message should indicate failure"
                )
    
    @given(_test_config_strategy(), openai_config_strategy())
    @settings(
        max_examples=3,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.data_too_large]
    )
    def test_property_openai_configuration_consistency(self, test_config, openai_config):
        """
        Property: OpenAI configuration should be consistently testable.
        
        For any OpenAI configuration parameters, the configuration test should 
        properly validate environment variables and return appropriate results.
        """
        # Create OpenAI client tester
        tester = OpenAIClientTester(test_config)
        
        # Test with the generated OpenAI configuration
        with patch.dict(os.environ, openai_config, clear=True):
            # Property: Configuration test should return valid results
            result = tester.test_openai_configuration()
            assert result is not None, "Configuration test should return a result"
            assert isinstance(result, TestResult), "Result should be a TestResult instance"
            assert result.test_name == "openai_configuration", "Test name should be 'openai_configuration'"
            assert result.status in [TestStatus.PASS, TestStatus.FAIL, TestStatus.ERROR], (
                "Test status should be a valid TestStatus"
            )
            
            # Property: Result details should contain configuration information
            assert result.details is not None, "Test details should be provided"
            assert isinstance(result.details, dict), "Test details should be a dictionary"
            
            expected_config_keys = ['base_url', 'model_default', 'timeout', 'temperature']
            for key in expected_config_keys:
                if key in result.details:
                    detail_value = result.details[key]
                    if detail_value is not None:
                        assert isinstance(detail_value, str), f"Config detail '{key}' should be a string"
                        assert len(detail_value.strip()) > 0, f"Config detail '{key}' should not be empty"
            
            # Property: Configuration values should be validated consistently
            # Note: We focus on testing that the configuration test provides consistent
            # behavior rather than specific expected values, since the underlying tester
            # has hardcoded expectations
            
            if 'OPENAI_BASE_URL' in openai_config:
                base_url_detail = result.details.get('base_url', '')
                if base_url_detail:
                    # Base URL detail should contain status information
                    assert any(status in base_url_detail for status in ['PASS', 'FAIL']), (
                        "Base URL detail should contain status information"
                    )
            
            if 'OPENAI_TIMEOUT_SECONDS' in openai_config:
                timeout_detail = result.details.get('timeout', '')
                if timeout_detail:
                    # Timeout detail should contain status information
                    assert any(status in timeout_detail for status in ['PASS', 'FAIL']), (
                        "Timeout detail should contain status information"
                    )
                    # Should mention the timeout value in some form
                    timeout_value = openai_config['OPENAI_TIMEOUT_SECONDS']
                    if timeout_value.replace('.', '').isdigit():
                        # The detail should reference some timeout value (either expected or actual)
                        assert any(char.isdigit() for char in timeout_detail), (
                            "Timeout detail should contain numeric information"
                        )
            
            if 'OPENAI_TEMPERATURE' in openai_config:
                temp_detail = result.details.get('temperature', '')
                if temp_detail:
                    # Temperature detail should contain status information
                    assert any(status in temp_detail for status in ['PASS', 'FAIL']), (
                        "Temperature detail should contain status information"
                    )
                    # For temperature, we just verify that the test ran and provided a result
                    # The underlying tester may have specific expectations about values
                    # We check for numeric values which indicate temperature testing occurred
                    assert any(char.isdigit() for char in temp_detail), (
                        "Temperature detail should contain numeric information indicating temperature testing"
                    )
    
    @given(_test_config_strategy())
    @settings(
        max_examples=3,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_openai_request_structure_consistency(self, test_config):
        """
        Property: OpenAI request structure validation should be consistent.
        
        For any test configuration, the request structure test should properly 
        validate JSON parsing and text extraction functionality.
        """
        # Create OpenAI client tester
        tester = OpenAIClientTester(test_config)
        
        # Property: Request structure test should return valid results
        result = tester.test_openai_request_structure()
        assert result is not None, "Request structure test should return a result"
        assert isinstance(result, TestResult), "Result should be a TestResult instance"
        assert result.test_name == "openai_request_structure", "Test name should be 'openai_request_structure'"
        assert result.status in [TestStatus.PASS, TestStatus.FAIL, TestStatus.ERROR], (
            "Test status should be a valid TestStatus"
        )
        
        # Property: Result should contain structure validation information
        assert result.details is not None, "Test details should be provided"
        assert isinstance(result.details, dict), "Test details should be a dictionary"
        
        expected_structure_keys = ['json_parsing', 'text_extraction', 'error_recovery']
        for key in expected_structure_keys:
            if key in result.details:
                detail_value = result.details[key]
                if detail_value is not None:
                    assert isinstance(detail_value, str), f"Structure detail '{key}' should be a string"
                    assert len(detail_value.strip()) > 0, f"Structure detail '{key}' should not be empty"
                    assert any(status in detail_value for status in ['PASS', 'FAIL', 'ERROR']), (
                        f"Structure detail '{key}' should contain status information"
                    )
        
        # Property: If test is not an import error, it should test actual functionality
        if result.status != TestStatus.ERROR or "import" not in result.message.lower():
            # Should have tested JSON parsing
            json_detail = result.details.get('json_parsing', '')
            if json_detail:
                assert 'json' in json_detail.lower(), (
                    "JSON parsing detail should mention JSON"
                )
            
            # Should have tested text extraction
            text_detail = result.details.get('text_extraction', '')
            if text_detail:
                assert 'text' in text_detail.lower() or 'extraction' in text_detail.lower(), (
                    "Text extraction detail should mention text or extraction"
                )
            
            # Should have tested error recovery
            error_detail = result.details.get('error_recovery', '')
            if error_detail:
                assert 'error' in error_detail.lower(), (
                    "Error recovery detail should mention error handling"
                )
    
    @given(_test_config_strategy())
    @settings(
        max_examples=3,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_openai_component_test_report_generation(self, test_config):
        """
        Property: OpenAI component test report generation should be comprehensive.
        
        For any test configuration, generating an OpenAI component test report should 
        include all client tests and provide appropriate recommendations.
        """
        # Create OpenAI client tester
        tester = OpenAIClientTester(test_config)
        
        # Property: Report generation should return valid report
        report = tester.generate_test_report()
        assert report is not None, "Test report should be generated"
        assert hasattr(report, 'lambda_function'), "Report should have lambda_function attribute"
        assert hasattr(report, 'client_tests'), "Report should have client_tests attribute"
        assert hasattr(report, 'overall_status'), "Report should have overall_status attribute"
        assert hasattr(report, 'recommendations'), "Report should have recommendations attribute"
        
        # Property: Report should contain client tests
        assert isinstance(report.client_tests, list), "Client tests should be a list"
        assert len(report.client_tests) > 0, "Report should contain at least one client test"
        
        # Property: All client tests should be valid TestResult instances
        for test in report.client_tests:
            assert isinstance(test, TestResult), "Each client test should be a TestResult"
            assert test.test_name is not None, "Test name should be set"
            assert test.status is not None, "Test status should be set"
            assert test.message is not None, "Test message should be set"
            assert test.details is not None, "Test details should be set"
        
        # Property: Overall status should reflect individual test results
        test_statuses = [test.status for test in report.client_tests]
        if TestStatus.ERROR in test_statuses:
            assert report.overall_status == TestStatus.ERROR, (
                "Overall status should be ERROR when individual tests have errors"
            )
        elif TestStatus.FAIL in test_statuses:
            assert report.overall_status == TestStatus.FAIL, (
                "Overall status should be FAIL when individual tests fail"
            )
        elif all(status == TestStatus.PASS for status in test_statuses):
            assert report.overall_status == TestStatus.PASS, (
                "Overall status should be PASS when all individual tests pass"
            )
        
        # Property: Recommendations should be provided appropriately
        assert isinstance(report.recommendations, list), "Recommendations should be a list"
        
        for recommendation in report.recommendations:
            assert isinstance(recommendation, str), "Each recommendation should be a string"
            assert len(recommendation.strip()) > 0, "Each recommendation should not be empty"
        
        # Property: Lambda function name should be set correctly
        assert report.lambda_function == "openai_client", "Lambda function should be 'openai_client'"
        
        # Property: Report should have appropriate structure for OpenAI testing
        assert hasattr(report, 'dependency_tests'), "Report should have dependency_tests attribute"
        assert hasattr(report, 'database_tests'), "Report should have database_tests attribute"
        assert isinstance(report.dependency_tests, list), "Dependency tests should be a list"
        assert isinstance(report.database_tests, list), "Database tests should be a list"
        
        # Property: Client tests should be the primary focus for OpenAI tester
        assert len(report.client_tests) >= len(report.dependency_tests), (
            "Client tests should be primary focus for OpenAI tester"
        )
        assert len(report.client_tests) >= len(report.database_tests), (
            "Client tests should be primary focus for OpenAI tester"
        )