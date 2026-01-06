"""
Property-based tests for DynamoDB operations.
Tests universal properties that should hold for DynamoDB write operations and reserved keyword handling.

Feature: cr2a-testing-debugging, Property 3: DynamoDB operation safety
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from typing import Dict, List, Optional, Any
import uuid
import json
from datetime import datetime

from tests.core.models import TestResult, TestStatus, TestConfiguration
from tests.component.dynamodb_tester import DynamoDBTester


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


# Strategy for generating DynamoDB attribute names
@st.composite
def dynamodb_attribute_strategy(draw):
    """Generate valid DynamoDB attribute names including reserved keywords."""
    # Mix of regular attributes and reserved keywords
    regular_attributes = draw(st.lists(
        st.text(min_size=1, max_size=20).filter(
            lambda x: x.isidentifier() and not x.startswith('_')
        ),
        min_size=1,
        max_size=5
    ))
    
    # Some known reserved keywords
    reserved_keywords = ['status', 'type', 'name', 'value', 'data', 'count', 'size', 'order']
    selected_reserved = draw(st.lists(
        st.sampled_from(reserved_keywords),
        min_size=0,
        max_size=3
    ))
    
    return list(set(regular_attributes + selected_reserved))


# Strategy for generating DynamoDB item data
@st.composite
def dynamodb_item_strategy(draw):
    """Generate valid DynamoDB item data."""
    item_id = str(uuid.uuid4())
    
    # Generate various attribute types
    string_attrs = draw(st.dictionaries(
        st.text(min_size=1, max_size=10).filter(lambda x: x.isidentifier()),
        st.text(min_size=1, max_size=50),
        min_size=0,
        max_size=3
    ))
    
    number_attrs = draw(st.dictionaries(
        st.text(min_size=1, max_size=10).filter(lambda x: x.isidentifier()),
        st.integers(min_value=0, max_value=1000),
        min_size=0,
        max_size=3
    ))
    
    # Combine into DynamoDB format
    item = {'id': {'S': item_id}}
    
    for key, value in string_attrs.items():
        item[key] = {'S': str(value)}
    
    for key, value in number_attrs.items():
        item[key] = {'N': str(value)}
    
    return item


class TestDynamoDBOperationProperties:
    """Property-based tests for DynamoDB operation functionality."""
    
    @given(_test_config_strategy())
    @settings(
        max_examples=3,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_dynamodb_operation_safety(self, test_config):
        """
        Property 3: DynamoDB operation safety
        
        For any data payload and table operation, the DynamoDB tester should 
        complete write operations without encountering reserved keyword conflicts.
        
        **Validates: Requirements 1.3**
        """
        # Create DynamoDB tester with the test configuration
        tester = DynamoDBTester(test_config, table_name="cr2a-test-table")
        
        # Property: DynamoDB tester should be properly initialized
        assert tester is not None, "DynamoDB tester should be created successfully"
        assert tester.table_name is not None, "Table name should be set"
        assert len(tester.table_name.strip()) > 0, "Table name should not be empty"
        assert tester.dynamodb is not None, "DynamoDB client should be initialized"
        assert tester.RESERVED_KEYWORDS is not None, "Reserved keywords should be loaded"
        assert len(tester.RESERVED_KEYWORDS) > 0, "Reserved keywords list should not be empty"
        
        # Property: Basic write operation should return valid TestResult
        basic_result = tester.test_basic_write_operation()
        assert basic_result is not None, "Basic write test should return a result"
        assert isinstance(basic_result, TestResult), "Result should be a TestResult instance"
        assert basic_result.test_name == "dynamodb_basic_write", "Test name should be 'dynamodb_basic_write'"
        assert basic_result.status in [TestStatus.PASS, TestStatus.FAIL, TestStatus.ERROR], (
            "Test status should be a valid TestStatus"
        )
        assert basic_result.message is not None, "Test message should be provided"
        assert len(basic_result.message.strip()) > 0, "Test message should not be empty"
        assert basic_result.timestamp is not None, "Test timestamp should be set"
        assert basic_result.execution_time >= 0, "Execution time should be non-negative"
        
        # Property: Basic write result should contain appropriate details
        if basic_result.status == TestStatus.PASS:
            assert basic_result.details is not None, "Successful test should have details"
            assert isinstance(basic_result.details, dict), "Details should be a dictionary"
            assert 'item_id' in basic_result.details, "Details should contain item ID"
            assert isinstance(basic_result.details['item_id'], str), "Item ID should be a string"
            assert len(basic_result.details['item_id']) > 0, "Item ID should not be empty"
        
        # Property: Reserved keyword handling should return valid TestResult
        keyword_result = tester.test_reserved_keyword_handling()
        assert keyword_result is not None, "Reserved keyword test should return a result"
        assert isinstance(keyword_result, TestResult), "Result should be a TestResult instance"
        assert keyword_result.test_name == "dynamodb_reserved_keywords", (
            "Test name should be 'dynamodb_reserved_keywords'"
        )
        assert keyword_result.status in [TestStatus.PASS, TestStatus.FAIL, TestStatus.ERROR], (
            "Test status should be a valid TestStatus"
        )
        
        # Property: Reserved keyword test should handle mapping correctly
        if keyword_result.status == TestStatus.PASS:
            assert keyword_result.details is not None, "Successful test should have details"
            assert 'reserved_keywords_tested' in keyword_result.details, (
                "Details should contain tested keywords"
            )
            assert 'expression_attribute_names' in keyword_result.details, (
                "Details should contain attribute name mapping"
            )
            
            tested_keywords = keyword_result.details['reserved_keywords_tested']
            assert isinstance(tested_keywords, list), "Tested keywords should be a list"
            assert len(tested_keywords) > 0, "Should test at least one reserved keyword"
            
            mapping = keyword_result.details['expression_attribute_names']
            assert isinstance(mapping, dict), "Attribute mapping should be a dictionary"
            assert len(mapping) > 0, "Should have at least one attribute mapping"
            
            # Property: All tested keywords should be in the reserved keywords set
            for keyword in tested_keywords:
                assert keyword in tester.RESERVED_KEYWORDS, (
                    f"Tested keyword '{keyword}' should be in reserved keywords set"
                )
        
        # Property: Safe attribute mapping should return valid TestResult
        mapping_result = tester.test_safe_attribute_mapping()
        assert mapping_result is not None, "Safe mapping test should return a result"
        assert isinstance(mapping_result, TestResult), "Result should be a TestResult instance"
        assert mapping_result.test_name == "dynamodb_safe_attribute_mapping", (
            "Test name should be 'dynamodb_safe_attribute_mapping'"
        )
        assert mapping_result.status in [TestStatus.PASS, TestStatus.FAIL, TestStatus.ERROR], (
            "Test status should be a valid TestStatus"
        )
        
        # Property: Safe mapping test should provide keyword information
        if mapping_result.status == TestStatus.PASS:
            assert mapping_result.details is not None, "Successful test should have details"
            if 'keywords_tested' in mapping_result.details:
                keywords_tested = mapping_result.details['keywords_tested']
                assert isinstance(keywords_tested, list), "Keywords tested should be a list"
                assert len(keywords_tested) > 0, "Should test at least one keyword"
                
                # Property: All tested keywords should be valid reserved keywords
                for keyword in keywords_tested:
                    assert isinstance(keyword, str), "Keyword should be a string"
                    assert len(keyword.strip()) > 0, "Keyword should not be empty"
                    assert keyword in tester.RESERVED_KEYWORDS, (
                        f"Keyword '{keyword}' should be in reserved keywords set"
                    )
        
        # Property: Error detection should return valid TestResult
        error_result = tester.test_error_detection_and_handling()
        assert error_result is not None, "Error detection test should return a result"
        assert isinstance(error_result, TestResult), "Result should be a TestResult instance"
        assert error_result.test_name == "dynamodb_error_detection", (
            "Test name should be 'dynamodb_error_detection'"
        )
        assert error_result.status in [TestStatus.PASS, TestStatus.FAIL, TestStatus.ERROR], (
            "Test status should be a valid TestStatus"
        )
        
        # Property: Error detection should identify error types
        if error_result.status == TestStatus.PASS:
            assert error_result.details is not None, "Successful test should have details"
            assert 'errors_detected' in error_result.details, "Details should contain detected errors"
            
            errors_detected = error_result.details['errors_detected']
            assert isinstance(errors_detected, list), "Detected errors should be a list"
            assert len(errors_detected) > 0, "Should detect at least one error type"
            
            # Property: Each detected error should have required fields
            for error in errors_detected:
                assert isinstance(error, dict), "Each error should be a dictionary"
                assert 'error_type' in error, "Error should have error_type"
                assert 'description' in error, "Error should have description"
                assert 'detected' in error, "Error should have detected flag"
                
                assert isinstance(error['error_type'], str), "Error type should be a string"
                assert len(error['error_type'].strip()) > 0, "Error type should not be empty"
                assert isinstance(error['description'], str), "Description should be a string"
                assert len(error['description'].strip()) > 0, "Description should not be empty"
                assert isinstance(error['detected'], bool), "Detected should be a boolean"
    
    @given(_test_config_strategy())
    @settings(
        max_examples=3,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_safe_attribute_mapping_generation(self, test_config):
        """
        Property: Safe attribute mapping should handle any list of attributes.
        
        For any list of attribute names, the safe mapping function should 
        correctly identify reserved keywords and generate appropriate mappings.
        """
        # Create DynamoDB tester
        tester = DynamoDBTester(test_config)
        
        # Test with various attribute combinations
        test_attributes = ['id', 'name', 'status', 'type', 'value', 'custom_attr', 'user_data']
        
        # Property: Safe mapping function should return valid mapping
        mapping = tester.get_safe_attribute_name_mapping(test_attributes)
        assert mapping is not None, "Mapping should be returned"
        assert isinstance(mapping, dict), "Mapping should be a dictionary"
        
        # Property: Mapping should only contain reserved keywords
        for placeholder, original_attr in mapping.items():
            assert isinstance(placeholder, str), "Placeholder should be a string"
            assert isinstance(original_attr, str), "Original attribute should be a string"
            assert placeholder.startswith('#attr_'), "Placeholder should follow naming convention"
            assert original_attr in test_attributes, "Original attribute should be from input list"
            assert original_attr.lower() in tester.RESERVED_KEYWORDS, (
                f"Mapped attribute '{original_attr}' should be a reserved keyword"
            )
        
        # Property: Non-reserved keywords should not be in mapping
        for attr in test_attributes:
            if attr.lower() not in tester.RESERVED_KEYWORDS:
                assert attr not in mapping.values(), (
                    f"Non-reserved attribute '{attr}' should not be in mapping"
                )
        
        # Property: All reserved keywords from input should be mapped
        for attr in test_attributes:
            if attr.lower() in tester.RESERVED_KEYWORDS:
                assert attr in mapping.values(), (
                    f"Reserved keyword '{attr}' should be in mapping"
                )
    
    @given(_test_config_strategy())
    @settings(
        max_examples=3,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_all_tests_execution(self, test_config):
        """
        Property: Running all tests should return comprehensive results.
        
        For any test configuration, running all DynamoDB tests should return 
        a complete set of test results with proper structure and information.
        """
        # Create DynamoDB tester
        tester = DynamoDBTester(test_config)
        
        # Property: All tests should return valid results list
        all_results = tester.run_all_tests()
        assert all_results is not None, "All tests should return results"
        assert isinstance(all_results, list), "Results should be a list"
        assert len(all_results) > 0, "Should return at least one test result"
        
        # Property: Each result should be a valid TestResult
        expected_test_names = [
            'dynamodb_basic_write',
            'dynamodb_reserved_keywords', 
            'dynamodb_safe_attribute_mapping',
            'dynamodb_error_detection'
        ]
        
        assert len(all_results) == len(expected_test_names), (
            f"Should return {len(expected_test_names)} test results"
        )
        
        for i, result in enumerate(all_results):
            assert isinstance(result, TestResult), f"Result {i} should be a TestResult instance"
            assert result.test_name is not None, f"Result {i} should have a test name"
            assert result.status is not None, f"Result {i} should have a status"
            assert result.message is not None, f"Result {i} should have a message"
            assert result.timestamp is not None, f"Result {i} should have a timestamp"
            assert result.execution_time >= 0, f"Result {i} should have non-negative execution time"
            
            # Property: Test name should match expected pattern
            assert result.test_name in expected_test_names, (
                f"Test name '{result.test_name}' should be in expected names"
            )
        
        # Property: All expected test names should be present
        result_names = [result.test_name for result in all_results]
        for expected_name in expected_test_names:
            assert expected_name in result_names, (
                f"Expected test '{expected_name}' should be in results"
            )
        
        # Property: Test results should have unique names
        assert len(set(result_names)) == len(result_names), (
            "All test results should have unique names"
        )
    
    @given(_test_config_strategy())
    @settings(
        max_examples=3,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_reserved_keywords_completeness(self, test_config):
        """
        Property: Reserved keywords set should be comprehensive and valid.
        
        For any DynamoDB tester instance, the reserved keywords set should 
        contain expected DynamoDB reserved words and be properly formatted.
        """
        # Create DynamoDB tester
        tester = DynamoDBTester(test_config)
        
        # Property: Reserved keywords should be a non-empty set
        assert tester.RESERVED_KEYWORDS is not None, "Reserved keywords should be defined"
        assert len(tester.RESERVED_KEYWORDS) > 0, "Reserved keywords should not be empty"
        
        # Property: Reserved keywords should contain known DynamoDB reserved words
        known_reserved = ['status', 'type', 'name', 'value', 'data', 'count', 'size', 'order', 'key']
        for keyword in known_reserved:
            assert keyword in tester.RESERVED_KEYWORDS, (
                f"Known reserved keyword '{keyword}' should be in reserved keywords set"
            )
        
        # Property: All reserved keywords should be valid strings
        for keyword in tester.RESERVED_KEYWORDS:
            assert isinstance(keyword, str), "Each reserved keyword should be a string"
            assert len(keyword.strip()) > 0, "Each reserved keyword should not be empty"
            assert keyword == keyword.lower(), "Reserved keywords should be lowercase"
            assert keyword.isalpha(), "Reserved keywords should contain only alphabetic characters"
        
        # Property: Reserved keywords should be unique
        keywords_list = list(tester.RESERVED_KEYWORDS)
        assert len(keywords_list) == len(set(keywords_list)), (
            "Reserved keywords should be unique (no duplicates)"
        )
        
        # Property: Reserved keywords should include common SQL/DynamoDB terms
        common_terms = ['select', 'from', 'where', 'and', 'or', 'not', 'null', 'true', 'false']
        found_common = [term for term in common_terms if term in tester.RESERVED_KEYWORDS]
        assert len(found_common) > 0, (
            f"Should contain some common SQL terms, found: {found_common}"
        )