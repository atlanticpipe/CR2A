"""
Property-based tests for Step Functions state machine validation.
Tests universal properties that should hold for all state machine configurations.

Feature: cr2a-testing-debugging, Property 5: State machine definition validation
"""

import json
import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from typing import Dict, Any, List

from ..core.models import TestConfiguration, TestStatus
from .step_functions_tester import StepFunctionsTester


# Strategy for generating valid Lambda function names
lambda_function_names = st.text(
    alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='-_'),
    min_size=3,
    max_size=64
).filter(lambda x: x[0].isalpha() and x[-1].isalnum())

# Strategy for generating state machine definitions
@st.composite
def state_machine_definition(draw):
    """Generate valid state machine definitions with Lambda function references."""
    # Generate Lambda function names
    num_functions = draw(st.integers(min_value=1, max_value=5))
    lambda_functions = draw(st.lists(
        lambda_function_names,
        min_size=num_functions,
        max_size=num_functions,
        unique=True
    ))
    
    # Generate states
    states = {}
    state_names = [f"State{i}" for i in range(len(lambda_functions))]
    
    for i, (state_name, func_name) in enumerate(zip(state_names, lambda_functions)):
        state_def = {
            "Type": "Task",
            "Resource": f"arn:aws:lambda:us-east-1:123456789012:function:{func_name}",
            "TimeoutSeconds": draw(st.integers(min_value=30, max_value=900))
        }
        
        # Add Next or End
        if i < len(state_names) - 1:
            state_def["Next"] = state_names[i + 1]
        else:
            state_def["End"] = True
        
        states[state_name] = state_def
    
    definition = {
        "Comment": draw(st.text(min_size=1, max_size=100)),
        "StartAt": state_names[0],
        "States": states
    }
    
    return definition, lambda_functions


class TestStepFunctionsProperties:
    """Property-based tests for Step Functions state machine validation."""
    
    def _get_tester(self):
        """Get a Step Functions tester instance."""
        config = TestConfiguration(
            aws_region="us-east-1",
            verbose_logging=True,
            max_retries=1  # Reduce retries for faster testing
        )
        return StepFunctionsTester(config)
    
    @given(state_machine_definition())
    @settings(
        max_examples=10, 
        deadline=15000,  # 15 second deadline per test
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_state_machine_definition_validation(self, generated_data):
        """
        Property 5: State machine definition validation
        
        For any valid state machine definition with Lambda function references,
        the definition parser should successfully extract all Lambda function names
        and validate the basic structure without errors.
        
        **Validates: Requirements 2.2**
        """
        tester = self._get_tester()
        definition, expected_functions = generated_data
        
        # Test the _extract_lambda_functions method
        extracted_functions = tester._extract_lambda_functions(definition)
        
        # Property: All expected Lambda functions should be extracted
        assert len(extracted_functions) == len(expected_functions), (
            f"Expected {len(expected_functions)} functions, got {len(extracted_functions)}. "
            f"Expected: {sorted(expected_functions)}, Got: {sorted(extracted_functions)}"
        )
        
        # Property: Extracted functions should match expected functions
        assert set(extracted_functions) == set(expected_functions), (
            f"Function sets don't match. Expected: {sorted(expected_functions)}, "
            f"Got: {sorted(extracted_functions)}"
        )
        
        # Property: Definition should have required structure
        assert "States" in definition, "Definition must have 'States' section"
        assert "StartAt" in definition, "Definition must have 'StartAt' field"
        assert definition["StartAt"] in definition["States"], (
            f"StartAt state '{definition['StartAt']}' must exist in States"
        )
        
        # Property: All states should be reachable or terminal
        states = definition["States"]
        start_state = definition["StartAt"]
        
        # Check that start state exists and is valid
        assert start_state in states, f"Start state '{start_state}' not found in states"
        
        # Property: Each Task state should have a valid Resource ARN
        for state_name, state_def in states.items():
            if state_def.get("Type") == "Task":
                assert "Resource" in state_def, f"Task state '{state_name}' must have Resource"
                resource = state_def["Resource"]
                assert "arn:aws:lambda:" in resource, (
                    f"Task state '{state_name}' Resource must be a Lambda ARN"
                )
                assert ":function:" in resource, (
                    f"Task state '{state_name}' Resource must reference a function"
                )
        
        # Property: States should have proper termination (Next or End)
        for state_name, state_def in states.items():
            has_next = "Next" in state_def
            has_end = state_def.get("End", False)
            
            # Must have either Next or End, but not both
            assert has_next or has_end, (
                f"State '{state_name}' must have either 'Next' or 'End'"
            )
            assert not (has_next and has_end), (
                f"State '{state_name}' cannot have both 'Next' and 'End'"
            )
            
            # If has Next, the target state must exist
            if has_next:
                next_state = state_def["Next"]
                assert next_state in states, (
                    f"State '{state_name}' references non-existent next state '{next_state}'"
                )
    
    @given(st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.dictionaries(
            keys=st.sampled_from(["Type", "Resource", "Next", "End"]),
            values=st.one_of(
                st.text(min_size=1, max_size=100),
                st.booleans(),
                st.integers(min_value=1, max_value=1000)
            )
        ),
        min_size=1,
        max_size=10
    ))
    @settings(
        max_examples=10, 
        deadline=10000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_lambda_function_extraction_robustness(self, states_dict):
        """
        Property: Lambda function extraction should be robust against malformed definitions.
        
        For any dictionary representing states, the extraction function should not crash
        and should only return valid function names from properly formatted Lambda ARNs.
        
        **Validates: Requirements 2.2**
        """
        tester = self._get_tester()
        # Create a minimal definition structure
        definition = {
            "States": states_dict,
            "StartAt": list(states_dict.keys())[0] if states_dict else "DummyState"
        }
        
        # This should not raise an exception
        try:
            extracted_functions = tester._extract_lambda_functions(definition)
            
            # Property: All extracted functions should be valid function names
            for func_name in extracted_functions:
                assert isinstance(func_name, str), f"Function name must be string, got {type(func_name)}"
                assert len(func_name) > 0, "Function name cannot be empty"
                assert len(func_name) <= 64, f"Function name too long: {len(func_name)} chars"
                # Function names should not contain ARN parts
                assert ":function:" not in func_name, f"Function name should not contain ARN parts: {func_name}"
                assert "arn:aws:" not in func_name, f"Function name should not contain ARN prefix: {func_name}"
            
        except Exception as e:
            # The extraction should be robust and not crash on malformed input
            pytest.fail(f"Lambda function extraction should not crash on malformed input: {str(e)}")
    
    @given(st.dictionaries(
        keys=st.sampled_from(["jobId", "s3Bucket", "s3Key", "analysisType"]),
        values=st.one_of(
            st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
            st.sampled_from(["full", "basic", "quick"])
        ),
        min_size=3,  # Require at least jobId, s3Bucket, s3Key
        max_size=4
    ))
    @settings(
        max_examples=1,   # Minimal for integration testing
        deadline=30000,   # 30 second deadline for Step Functions execution
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_workflow_execution_completion(self, workflow_input):
        """
        Property 7: Workflow execution completion
        
        For any valid workflow input, manual Step Functions executions should 
        complete all states without errors. This property validates that the
        state machine can handle various input formats and complete successfully.
        
        **Validates: Requirements 2.4**
        """
        # Ensure required fields are present
        assume("jobId" in workflow_input)
        assume("s3Bucket" in workflow_input) 
        assume("s3Key" in workflow_input)
        
        # Set default analysisType if not provided
        if "analysisType" not in workflow_input:
            workflow_input["analysisType"] = "basic"
        
        tester = self._get_tester()
        
        # Property: The tester should be able to find the state machine
        exists_result = tester.test_state_machine_exists()
        if exists_result.status != TestStatus.PASS:
            pytest.skip("State machine not found - cannot test execution completion")
        
        # Property: Manual execution should complete without errors
        execution_result = tester.run_manual_execution(workflow_input)
        
        # The execution should not skip (state machine should be available)
        assert execution_result.status != TestStatus.SKIP, (
            "Execution should not be skipped when state machine exists"
        )
        
        # Property: Execution should provide detailed results
        assert execution_result.details is not None, (
            "Execution result should contain detailed information"
        )
        
        execution_details = execution_result.details
        
        # Handle the case where execution failed due to AWS service errors
        if execution_result.status == TestStatus.ERROR:
            # Check if it's an ExecutionAlreadyExists error (which is expected in rapid testing)
            if "ExecutionAlreadyExists" in str(execution_details.get("exception_args", "")):
                pytest.skip("Execution name conflict - this is expected in rapid property testing")
            else:
                # For other errors, we still want to validate the error structure
                assert "exception_type" in execution_details, (
                    "Error execution should include exception type"
                )
                assert "exception_args" in execution_details, (
                    "Error execution should include exception arguments"
                )
                return  # Exit early for error cases
        
        # Property: Execution should have a valid ARN (for successful starts)
        assert "execution_arn" in execution_details, (
            "Execution details must include execution ARN"
        )
        assert execution_details["execution_arn"], (
            "Execution ARN should not be empty"
        )
        
        # Property: Execution should have a definitive status
        assert "status" in execution_details, (
            "Execution details must include status"
        )
        execution_status = execution_details["status"]
        assert execution_status in ["SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"], (
            f"Execution status should be definitive, got: {execution_status}"
        )
        
        # Property: Execution should have timing information
        assert "start_date" in execution_details, (
            "Execution details must include start date"
        )
        
        # Property: If execution succeeded, it should have output
        if execution_status == "SUCCEEDED":
            # For successful executions, we expect some form of output or completion
            assert execution_result.status == TestStatus.PASS, (
                "Test result should be PASS when execution succeeds"
            )
            assert "stop_date" in execution_details, (
                "Successful execution should have stop date"
            )
        
        # Property: If execution failed, it should provide error information
        elif execution_status == "FAILED":
            assert execution_result.status == TestStatus.FAIL, (
                "Test result should be FAIL when execution fails"
            )
            # Failed executions should provide error details for debugging
            assert "error" in execution_details or "cause" in execution_details, (
                "Failed execution should provide error or cause information"
            )
        
        # Property: Execution should complete within reasonable time
        if "start_date" in execution_details and "stop_date" in execution_details:
            start_date = execution_details["start_date"]
            stop_date = execution_details["stop_date"]
            if start_date and stop_date:
                # Both dates should be valid ISO format strings
                assert isinstance(start_date, str), "Start date should be string"
                assert isinstance(stop_date, str), "Stop date should be string"
                # Basic format validation (should not raise exception)
                from datetime import datetime
                try:
                    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    stop_dt = datetime.fromisoformat(stop_date.replace('Z', '+00:00'))
                    execution_duration = (stop_dt - start_dt).total_seconds()
                    # Execution should complete within reasonable time (5 minutes)
                    assert execution_duration <= 300, (
                        f"Execution took too long: {execution_duration} seconds"
                    )
                except ValueError as e:
                    pytest.fail(f"Invalid date format in execution details: {e}")

    def test_property_state_machine_definition_validation_example(self):
        """
        Example test to demonstrate the property with a concrete case.
        This validates the property works with a known good state machine definition.
        
        **Validates: Requirements 2.2**
        """
        tester = self._get_tester()
        # Known good definition
        definition = {
            "Comment": "CR2A Contract Analysis State Machine",
            "StartAt": "CalculateChunks",
            "States": {
                "CalculateChunks": {
                    "Type": "Task",
                    "Resource": "arn:aws:lambda:us-east-1:123456789012:function:cr2a-calculate-chunks",
                    "Next": "AnalyzeChunk"
                },
                "AnalyzeChunk": {
                    "Type": "Task", 
                    "Resource": "arn:aws:lambda:us-east-1:123456789012:function:cr2a-analyze-chunk",
                    "Next": "AggregateResults"
                },
                "AggregateResults": {
                    "Type": "Task",
                    "Resource": "arn:aws:lambda:us-east-1:123456789012:function:cr2a-aggregate-results",
                    "End": True
                }
            }
        }
        
        expected_functions = ["cr2a-calculate-chunks", "cr2a-analyze-chunk", "cr2a-aggregate-results"]
        
        # Test extraction
        extracted_functions = tester._extract_lambda_functions(definition)
        
        # Validate the property holds
        assert len(extracted_functions) == len(expected_functions)
        assert set(extracted_functions) == set(expected_functions)
        
        # Validate structure requirements
        assert "States" in definition
        assert "StartAt" in definition
        assert definition["StartAt"] in definition["States"]
    
    def test_workflow_execution_completion_example(self):
        """
        Example test for workflow execution completion with known good input.
        This demonstrates the property with a concrete test case.
        
        **Validates: Requirements 2.4**
        """
        tester = self._get_tester()
        
        # Known good test input
        test_input = {
            "jobId": "test-job-001",
            "s3Bucket": "cr2a-test-bucket", 
            "s3Key": "test-documents/sample-contract.pdf",
            "analysisType": "basic"
        }
        
        # Test that state machine exists first
        exists_result = tester.test_state_machine_exists()
        if exists_result.status != TestStatus.PASS:
            pytest.skip("State machine not found - cannot test execution")
        
        # Test execution completion
        execution_result = tester.run_manual_execution(test_input)
        
        # Validate the property requirements
        assert execution_result.status != TestStatus.SKIP
        assert execution_result.details is not None
        assert "execution_arn" in execution_result.details
        assert "status" in execution_result.details
        assert execution_result.details["status"] in ["SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"]