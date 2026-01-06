"""
Step Functions state machine tester for CR2A integration testing.
Validates state machine existence, definition, and execution capabilities.
"""

import json
import time
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError

from ..core.base import BaseTestFramework
from ..core.models import TestResult, TestStatus, TestConfiguration
from ..core.interfaces import IntegrationTester


class StepFunctionsTester(BaseTestFramework):
    """Tester for Step Functions state machine validation and execution."""
    
    def __init__(self, config: TestConfiguration):
        super().__init__(config)
        self.state_machine_name = "cr2a-contract-analysis"
        self.state_machine_arn = None
    
    def test_state_machine_exists(self) -> TestResult:
        """Test Step Functions state machine existence and accessibility."""
        def _test_exists():
            sf_client = self.get_aws_client('stepfunctions')
            
            # List state machines to find our target
            response = sf_client.list_state_machines()
            state_machines = response.get('stateMachines', [])
            
            for sm in state_machines:
                if self.state_machine_name in sm['name']:
                    self.state_machine_arn = sm['stateMachineArn']
                    self.logger.info(f"Found state machine: {self.state_machine_arn}")
                    return True
            
            return False
        
        result = self.execute_test_with_timing(
            "test_state_machine_exists",
            lambda: self.retry_operation(_test_exists)
        )
        
        if result.status == TestStatus.PASS:
            result.message = f"State machine '{self.state_machine_name}' found and accessible"
            result.details = {"state_machine_arn": self.state_machine_arn}
        else:
            result.message = f"State machine '{self.state_machine_name}' not found or not accessible"
        
        return result
    
    def test_state_machine_definition(self) -> TestResult:
        """Test state machine definition validity and Lambda function references."""
        if not self.state_machine_arn:
            # Try to find the state machine first
            exists_result = self.test_state_machine_exists()
            if exists_result.status != TestStatus.PASS:
                return TestResult(
                    test_name="test_state_machine_definition",
                    status=TestStatus.SKIP,
                    message="Cannot test definition - state machine not found"
                )
        
        def _test_definition():
            sf_client = self.get_aws_client('stepfunctions')
            
            # Get state machine definition
            response = sf_client.describe_state_machine(stateMachineArn=self.state_machine_arn)
            definition_str = response['definition']
            
            try:
                definition = json.loads(definition_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in state machine definition: {str(e)}")
            
            # Validate basic structure
            if 'States' not in definition:
                raise ValueError("State machine definition missing 'States' section")
            
            if 'StartAt' not in definition:
                raise ValueError("State machine definition missing 'StartAt' field")
            
            # Check Lambda function references
            lambda_functions = self._extract_lambda_functions(definition)
            self.logger.info(f"Found Lambda functions in definition: {lambda_functions}")
            
            # Validate each Lambda function exists
            lambda_client = self.get_aws_client('lambda')
            for func_name in lambda_functions:
                try:
                    lambda_client.get_function(FunctionName=func_name)
                    self.logger.info(f"Lambda function '{func_name}' exists and is accessible")
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceNotFoundException':
                        raise ValueError(f"Lambda function '{func_name}' referenced in state machine but not found")
                    raise
            
            return {
                "definition_valid": True,
                "lambda_functions": lambda_functions,
                "states_count": len(definition['States'])
            }
        
        result = self.execute_test_with_timing(
            "test_state_machine_definition",
            lambda: self.retry_operation(_test_definition)
        )
        
        if result.status == TestStatus.PASS:
            result.message = "State machine definition is valid and all Lambda functions exist"
        
        return result
    
    def run_manual_execution(self, test_input: Dict[str, Any]) -> TestResult:
        """Run manual Step Functions execution with test input."""
        if not self.state_machine_arn:
            # Try to find the state machine first
            exists_result = self.test_state_machine_exists()
            if exists_result.status != TestStatus.PASS:
                return TestResult(
                    test_name="run_manual_execution",
                    status=TestStatus.SKIP,
                    message="Cannot run execution - state machine not found"
                )
        
        def _run_execution():
            sf_client = self.get_aws_client('stepfunctions')
            
            # Start execution with more unique name including microseconds
            import uuid
            execution_name = f"test-execution-{int(time.time())}-{uuid.uuid4().hex[:8]}"
            response = sf_client.start_execution(
                stateMachineArn=self.state_machine_arn,
                name=execution_name,
                input=json.dumps(test_input)
            )
            
            execution_arn = response['executionArn']
            self.logger.info(f"Started execution: {execution_arn}")
            
            # Wait for execution to complete (with timeout)
            max_wait_time = 300  # 5 minutes
            wait_interval = 5    # 5 seconds
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                execution_response = sf_client.describe_execution(executionArn=execution_arn)
                status = execution_response['status']
                
                if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
                    break
                
                time.sleep(wait_interval)
                elapsed_time += wait_interval
            
            # Get final execution details
            final_response = sf_client.describe_execution(executionArn=execution_arn)
            
            execution_details = {
                "execution_arn": execution_arn,
                "status": final_response['status'],
                "start_date": final_response['startDate'].isoformat(),
                "stop_date": final_response.get('stopDate', '').isoformat() if final_response.get('stopDate') else None,
                "output": final_response.get('output'),
                "error": final_response.get('error'),
                "cause": final_response.get('cause')
            }
            
            # Return a TestResult with the execution details
            execution_status = execution_details.get('status')
            if execution_status == 'SUCCEEDED':
                return TestResult(
                    test_name="run_manual_execution",
                    status=TestStatus.PASS,
                    message="Manual execution completed successfully",
                    details=execution_details
                )
            else:
                return TestResult(
                    test_name="run_manual_execution",
                    status=TestStatus.FAIL,
                    message=f"Manual execution failed with status: {execution_status}",
                    details=execution_details
                )
        
        result = self.execute_test_with_timing(
            "run_manual_execution",
            lambda: self.retry_operation(_run_execution)
        )
        
        return result
    
    def _extract_lambda_functions(self, definition: Dict[str, Any]) -> List[str]:
        """Extract Lambda function names from state machine definition."""
        lambda_functions = []
        
        def _extract_from_state(state_def: Dict[str, Any]):
            # Check for Lambda task
            if state_def.get('Type') == 'Task' and 'Resource' in state_def:
                resource = state_def['Resource']
                if 'lambda' in resource.lower() and 'function' in resource.lower():
                    # Extract function name from ARN
                    if ':function:' in resource:
                        func_name = resource.split(':function:')[-1]
                        # Remove any version/alias suffix
                        if ':' in func_name:
                            func_name = func_name.split(':')[0]
                        lambda_functions.append(func_name)
            
            # Check for parallel or choice states
            if 'Branches' in state_def:
                for branch in state_def['Branches']:
                    if 'States' in branch:
                        for branch_state in branch['States'].values():
                            _extract_from_state(branch_state)
            
            if 'Choices' in state_def:
                for choice in state_def['Choices']:
                    if 'Next' in choice:
                        # This would need the full definition to resolve
                        pass
        
        # Process all states
        for state_name, state_def in definition.get('States', {}).items():
            _extract_from_state(state_def)
        
        return list(set(lambda_functions))  # Remove duplicates
    
    def get_test_input_samples(self) -> List[Dict[str, Any]]:
        """Get sample test inputs for manual execution testing."""
        return [
            {
                "jobId": "test-job-001",
                "s3Bucket": "cr2a-test-bucket",
                "s3Key": "test-documents/sample-contract.pdf",
                "analysisType": "full"
            },
            {
                "jobId": "test-job-002",
                "s3Bucket": "cr2a-test-bucket",
                "s3Key": "test-documents/simple-contract.docx",
                "analysisType": "basic"
            }
        ]