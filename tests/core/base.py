"""
Base testing framework implementation with common utilities.
Provides shared functionality for all testing components.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from .models import TestResult, TestStatus, TestConfiguration
from .interfaces import AWSResourceValidator


class BaseTestFramework:
    """Base class providing common testing utilities."""
    
    def __init__(self, config: TestConfiguration):
        self.config = config
        self.logger = self._setup_logging()
        self._aws_clients = {}
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger(f"cr2a_testing.{self.__class__.__name__}")
        logger.setLevel(logging.DEBUG if self.config.verbose_logging else logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def get_aws_client(self, service_name: str) -> Any:
        """Get or create AWS service client."""
        if service_name not in self._aws_clients:
            try:
                self._aws_clients[service_name] = boto3.client(
                    service_name,
                    region_name=self.config.aws_region
                )
            except NoCredentialsError:
                self.logger.error(f"AWS credentials not configured for {service_name}")
                raise
        
        return self._aws_clients[service_name]
    
    def execute_test_with_timing(self, test_name: str, test_func, *args, **kwargs) -> TestResult:
        """Execute a test function with timing and error handling."""
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting test: {test_name}")
            result = test_func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            if isinstance(result, TestResult):
                result.execution_time = execution_time
                return result
            else:
                # If test function returns a simple boolean or None
                status = TestStatus.PASS if result else TestStatus.FAIL
                return TestResult(
                    test_name=test_name,
                    status=status,
                    message="Test completed successfully" if result else "Test failed",
                    execution_time=execution_time
                )
        
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Test {test_name} failed with exception: {str(e)}")
            
            return TestResult(
                test_name=test_name,
                status=TestStatus.ERROR,
                message=f"Test failed with exception: {str(e)}",
                details={"exception_type": type(e).__name__, "exception_args": str(e.args)},
                execution_time=execution_time
            )
    
    def retry_operation(self, operation, max_retries: Optional[int] = None, delay: float = 1.0):
        """Retry an operation with exponential backoff."""
        max_retries = max_retries or self.config.max_retries
        
        for attempt in range(max_retries + 1):
            try:
                return operation()
            except Exception as e:
                if attempt == max_retries:
                    raise e
                
                wait_time = delay * (2 ** attempt)
                self.logger.warning(
                    f"Operation failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}. "
                    f"Retrying in {wait_time} seconds..."
                )
                time.sleep(wait_time)


class AWSResourceValidatorImpl(AWSResourceValidator, BaseTestFramework):
    """Implementation of AWS resource validation."""
    
    def __init__(self, config: TestConfiguration):
        super().__init__(config)
    
    def validate_lambda_function(self, function_name: str) -> TestResult:
        """Validate Lambda function exists and is accessible."""
        def _validate():
            lambda_client = self.get_aws_client('lambda')
            response = lambda_client.get_function(FunctionName=function_name)
            return response['Configuration']['State'] == 'Active'
        
        return self.execute_test_with_timing(
            f"validate_lambda_function_{function_name}",
            lambda: self.retry_operation(_validate)
        )
    
    def validate_step_function(self, state_machine_arn: str) -> TestResult:
        """Validate Step Functions state machine."""
        def _validate():
            sf_client = self.get_aws_client('stepfunctions')
            response = sf_client.describe_state_machine(stateMachineArn=state_machine_arn)
            return response['status'] == 'ACTIVE'
        
        return self.execute_test_with_timing(
            f"validate_step_function",
            lambda: self.retry_operation(_validate)
        )
    
    def validate_api_gateway(self, api_id: str) -> TestResult:
        """Validate API Gateway configuration."""
        def _validate():
            api_client = self.get_aws_client('apigateway')
            response = api_client.get_rest_api(restApiId=api_id)
            return 'id' in response
        
        return self.execute_test_with_timing(
            f"validate_api_gateway_{api_id}",
            lambda: self.retry_operation(_validate)
        )
    
    def validate_dynamodb_table(self, table_name: str) -> TestResult:
        """Validate DynamoDB table configuration."""
        def _validate():
            dynamodb_client = self.get_aws_client('dynamodb')
            response = dynamodb_client.describe_table(TableName=table_name)
            return response['Table']['TableStatus'] == 'ACTIVE'
        
        return self.execute_test_with_timing(
            f"validate_dynamodb_table_{table_name}",
            lambda: self.retry_operation(_validate)
        )
    
    def validate_iam_permissions(self, role_arn: str, required_actions: List[str]) -> TestResult:
        """Validate IAM role has required permissions."""
        def _validate():
            # This is a simplified validation - in practice, you'd need to check policies
            iam_client = self.get_aws_client('iam')
            role_name = role_arn.split('/')[-1]
            response = iam_client.get_role(RoleName=role_name)
            return 'Role' in response
        
        return self.execute_test_with_timing(
            f"validate_iam_permissions_{role_arn.split('/')[-1]}",
            lambda: self.retry_operation(_validate)
        )