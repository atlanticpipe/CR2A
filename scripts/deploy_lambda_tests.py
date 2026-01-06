#!/usr/bin/env python3
"""
Lambda deployment scripts for CR2A testing framework.
Deploys test functions to AWS Lambda for component isolation testing.
"""

import os
import json
import zipfile
import tempfile
import shutil
import boto3
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError, NoCredentialsError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LambdaDeploymentManager:
    """Manages deployment of test functions to AWS Lambda."""
    
    def __init__(self, aws_region: str = "us-east-1"):
        """Initialize Lambda deployment manager."""
        self.aws_region = aws_region
        self.lambda_client = None
        self.iam_client = None
        self.logs_client = None
        
        # Test function configurations
        self.test_functions = {
            "cr2a-dependency-test": {
                "description": "Tests Lambda layer dependencies and package imports",
                "handler": "lambda_function.lambda_handler",
                "runtime": "python3.12",
                "timeout": 60,
                "memory_size": 256,
                "environment_variables": {
                    "TEST_TYPE": "dependency",
                    "LOG_LEVEL": "INFO"
                }
            },
            "cr2a-openai-test": {
                "description": "Tests OpenAI client initialization and connectivity",
                "handler": "lambda_function.lambda_handler", 
                "runtime": "python3.12",
                "timeout": 60,
                "memory_size": 256,
                "environment_variables": {
                    "TEST_TYPE": "openai",
                    "LOG_LEVEL": "INFO"
                }
            },
            "cr2a-dynamodb-test": {
                "description": "Tests DynamoDB operations and reserved keyword handling",
                "handler": "lambda_function.lambda_handler",
                "runtime": "python3.12", 
                "timeout": 60,
                "memory_size": 256,
                "environment_variables": {
                    "TEST_TYPE": "dynamodb",
                    "LOG_LEVEL": "INFO"
                }
            }
        }
    
    def _initialize_clients(self):
        """Initialize AWS clients with error handling."""
        try:
            self.lambda_client = boto3.client('lambda', region_name=self.aws_region)
            self.iam_client = boto3.client('iam', region_name=self.aws_region)
            self.logs_client = boto3.client('logs', region_name=self.aws_region)
            
            # Test credentials
            self.lambda_client.list_functions(MaxItems=1)
            logger.info(f"AWS clients initialized successfully for region: {self.aws_region}")
            
        except NoCredentialsError:
            logger.error("AWS credentials not found. Please configure AWS credentials.")
            raise
        except ClientError as e:
            logger.error(f"Failed to initialize AWS clients: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error initializing AWS clients: {e}")
            raise
    
    def create_lambda_layer(self, layer_name: str, requirements_file: str = "requirements-core.txt") -> Optional[str]:
        """Create Lambda layer with required dependencies."""
        if not self.lambda_client:
            self._initialize_clients()
        
        logger.info(f"Creating Lambda layer: {layer_name}")
        
        try:
            # Create temporary directory for layer contents
            with tempfile.TemporaryDirectory() as temp_dir:
                layer_dir = Path(temp_dir) / "python"
                layer_dir.mkdir(parents=True)
                
                # Install packages to layer directory
                if Path(requirements_file).exists():
                    logger.info(f"Installing packages from {requirements_file}")
                    import subprocess
                    result = subprocess.run([
                        "pip", "install", "-r", requirements_file, 
                        "-t", str(layer_dir), "--no-deps"
                    ], capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        logger.warning(f"pip install had issues: {result.stderr}")
                        # Try without --no-deps
                        result = subprocess.run([
                            "pip", "install", "-r", requirements_file, 
                            "-t", str(layer_dir)
                        ], capture_output=True, text=True)
                        
                        if result.returncode != 0:
                            logger.error(f"Failed to install packages: {result.stderr}")
                            return None
                
                # Create layer zip file
                layer_zip_path = Path(temp_dir) / f"{layer_name}.zip"
                with zipfile.ZipFile(layer_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(layer_dir):
                        for file in files:
                            file_path = Path(root) / file
                            arcname = file_path.relative_to(Path(temp_dir))
                            zipf.write(file_path, arcname)
                
                # Upload layer to AWS
                with open(layer_zip_path, 'rb') as zip_file:
                    response = self.lambda_client.publish_layer_version(
                        LayerName=layer_name,
                        Description=f"Dependencies for CR2A testing framework",
                        Content={'ZipFile': zip_file.read()},
                        CompatibleRuntimes=['python3.12'],
                        CompatibleArchitectures=['x86_64']
                    )
                
                layer_arn = response['LayerVersionArn']
                logger.info(f"Layer created successfully: {layer_arn}")
                return layer_arn
                
        except Exception as e:
            logger.error(f"Failed to create Lambda layer {layer_name}: {e}")
            return None
    
    def create_test_function_code(self, test_type: str) -> str:
        """Generate Lambda function code for specific test type."""
        if test_type == "dependency":
            return self._get_dependency_test_code()
        elif test_type == "openai":
            return self._get_openai_test_code()
        elif test_type == "dynamodb":
            return self._get_dynamodb_test_code()
        else:
            raise ValueError(f"Unknown test type: {test_type}")
    
    def _get_dependency_test_code(self) -> str:
        """Get dependency test Lambda function code."""
        return '''
import json
import importlib
import sys
import os
from typing import Dict, List, Any

def lambda_handler(event, context):
    """Lambda function to test package dependencies."""
    required_packages = event.get('required_packages', [
        'boto3', 'botocore', 'openai', 'requests', 'json', 'os', 'logging'
    ])
    
    results = {
        'successful_imports': [],
        'failed_imports': [],
        'environment_info': {
            'python_version': sys.version,
            'lambda_task_root': os.environ.get('LAMBDA_TASK_ROOT'),
            'lambda_runtime_dir': os.environ.get('LAMBDA_RUNTIME_DIR'),
            'python_path': sys.path[:5]  # First 5 paths only
        }
    }
    
    for package_name in required_packages:
        try:
            if package_name in sys.builtin_module_names:
                module = importlib.import_module(package_name)
                results['successful_imports'].append({
                    'package': package_name,
                    'version': getattr(module, '__version__', 'built-in'),
                    'location': 'built-in'
                })
            else:
                module = importlib.import_module(package_name)
                results['successful_imports'].append({
                    'package': package_name,
                    'version': getattr(module, '__version__', 'unknown'),
                    'location': getattr(module, '__file__', 'unknown')[:100]  # Truncate long paths
                })
        except ImportError as e:
            results['failed_imports'].append({
                'package': package_name,
                'error': str(e),
                'error_type': 'ImportError'
            })
        except Exception as e:
            results['failed_imports'].append({
                'package': package_name,
                'error': str(e),
                'error_type': type(e).__name__
            })
    
    return {
        'statusCode': 200,
        'body': json.dumps(results, indent=2)
    }
'''
    
    def _get_openai_test_code(self) -> str:
        """Get OpenAI test Lambda function code."""
        return '''
import json
import os
from typing import Dict, Any

def lambda_handler(event, context):
    """Lambda function to test OpenAI client functionality."""
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
        import openai
        results['openai_import'] = 'SUCCESS: OpenAI package imported'
    except ImportError as e:
        results['openai_import'] = f'FAIL: Import error - {str(e)}'
        return {'statusCode': 500, 'body': json.dumps(results)}
    except Exception as e:
        results['openai_import'] = f'ERROR: Unexpected error - {str(e)}'
        return {'statusCode': 500, 'body': json.dumps(results)}
    
    # Test API key retrieval
    try:
        api_key = os.environ.get('OPENAI_API_KEY')
        if api_key:
            results['api_key_access'] = f'SUCCESS: API key retrieved (length: {len(api_key)})'
        else:
            results['api_key_access'] = 'FAIL: No API key available'
    except Exception as e:
        results['api_key_access'] = f'ERROR: API key retrieval failed - {str(e)}'
    
    # Test client creation
    try:
        client = openai.OpenAI(api_key=api_key or "test-key")
        results['client_creation'] = 'SUCCESS: OpenAI client created'
    except Exception as e:
        results['client_creation'] = f'ERROR: Client creation failed - {str(e)}'
    
    return {
        'statusCode': 200,
        'body': json.dumps(results, indent=2)
    }
'''
    
    def _get_dynamodb_test_code(self) -> str:
        """Get DynamoDB test Lambda function code."""
        return '''
import json
import boto3
import os
from typing import Dict, Any
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    """Lambda function to test DynamoDB operations."""
    results = {
        'dynamodb_import': None,
        'client_creation': None,
        'table_operations': None,
        'reserved_keywords': None,
        'environment_info': {
            'aws_region': os.environ.get('AWS_REGION', 'us-east-1'),
            'table_name': event.get('table_name', 'cr2a-test-table')
        }
    }
    
    # Test DynamoDB import
    try:
        import boto3
        results['dynamodb_import'] = 'SUCCESS: boto3 imported'
    except ImportError as e:
        results['dynamodb_import'] = f'FAIL: Import error - {str(e)}'
        return {'statusCode': 500, 'body': json.dumps(results)}
    
    # Test client creation
    try:
        dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
        results['client_creation'] = 'SUCCESS: DynamoDB client created'
    except Exception as e:
        results['client_creation'] = f'ERROR: Client creation failed - {str(e)}'
        return {'statusCode': 500, 'body': json.dumps(results)}
    
    # Test table operations (if table exists)
    table_name = event.get('table_name', 'cr2a-test-table')
    try:
        table = dynamodb.Table(table_name)
        table.load()  # This will raise an exception if table doesn't exist
        results['table_operations'] = f'SUCCESS: Table {table_name} accessible'
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            results['table_operations'] = f'INFO: Table {table_name} not found (expected for test)'
        else:
            results['table_operations'] = f'ERROR: Table access failed - {str(e)}'
    except Exception as e:
        results['table_operations'] = f'ERROR: Unexpected table error - {str(e)}'
    
    # Test reserved keyword handling
    try:
        # Test common reserved keywords that cause issues
        reserved_keywords = ['status', 'type', 'data', 'timestamp', 'size', 'name']
        safe_attributes = {}
        
        for keyword in reserved_keywords:
            # Test attribute name mapping
            safe_name = f"#{keyword}"
            safe_attributes[safe_name] = keyword
        
        results['reserved_keywords'] = f'SUCCESS: Mapped {len(safe_attributes)} reserved keywords'
    except Exception as e:
        results['reserved_keywords'] = f'ERROR: Reserved keyword handling failed - {str(e)}'
    
    return {
        'statusCode': 200,
        'body': json.dumps(results, indent=2)
    }
'''
    
    def deploy_test_function(self, function_name: str, layer_arn: Optional[str] = None) -> bool:
        """Deploy a test function to AWS Lambda."""
        if not self.lambda_client:
            self._initialize_clients()
        
        if function_name not in self.test_functions:
            logger.error(f"Unknown test function: {function_name}")
            return False
        
        config = self.test_functions[function_name]
        test_type = config["environment_variables"]["TEST_TYPE"]
        
        logger.info(f"Deploying test function: {function_name}")
        
        try:
            # Create function code
            function_code = self.create_test_function_code(test_type)
            
            # Create deployment package
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write function code
                function_file = Path(temp_dir) / "lambda_function.py"
                with open(function_file, 'w') as f:
                    f.write(function_code)
                
                # Create zip file
                zip_path = Path(temp_dir) / f"{function_name}.zip"
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(function_file, "lambda_function.py")
                
                # Prepare function configuration
                function_config = {
                    'FunctionName': function_name,
                    'Runtime': config['runtime'],
                    'Role': self._get_or_create_lambda_role(),
                    'Handler': config['handler'],
                    'Description': config['description'],
                    'Timeout': config['timeout'],
                    'MemorySize': config['memory_size'],
                    'Environment': {
                        'Variables': config['environment_variables']
                    }
                }
                
                # Add layer if provided
                if layer_arn:
                    function_config['Layers'] = [layer_arn]
                
                # Read zip file
                with open(zip_path, 'rb') as zip_file:
                    function_config['Code'] = {'ZipFile': zip_file.read()}
                
                # Check if function exists
                try:
                    self.lambda_client.get_function(FunctionName=function_name)
                    # Function exists, update it
                    logger.info(f"Updating existing function: {function_name}")
                    
                    # Update function code
                    self.lambda_client.update_function_code(
                        FunctionName=function_name,
                        ZipFile=function_config['Code']['ZipFile']
                    )
                    
                    # Update function configuration
                    config_update = {k: v for k, v in function_config.items() 
                                   if k not in ['FunctionName', 'Code']}
                    self.lambda_client.update_function_configuration(**config_update)
                    
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceNotFoundException':
                        # Function doesn't exist, create it
                        logger.info(f"Creating new function: {function_name}")
                        self.lambda_client.create_function(**function_config)
                    else:
                        raise
                
                logger.info(f"Function {function_name} deployed successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to deploy function {function_name}: {e}")
            return False
    
    def _get_or_create_lambda_role(self) -> str:
        """Get or create IAM role for Lambda functions."""
        role_name = "cr2a-lambda-test-role"
        
        try:
            # Try to get existing role
            response = self.iam_client.get_role(RoleName=role_name)
            role_arn = response['Role']['Arn']
            logger.info(f"Using existing IAM role: {role_arn}")
            return role_arn
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                # Role doesn't exist, create it
                logger.info(f"Creating IAM role: {role_name}")
                return self._create_lambda_role(role_name)
            else:
                raise
    
    def _create_lambda_role(self, role_name: str) -> str:
        """Create IAM role for Lambda functions."""
        # Trust policy for Lambda
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        # Create role
        response = self.iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="IAM role for CR2A Lambda test functions"
        )
        
        role_arn = response['Role']['Arn']
        
        # Attach basic Lambda execution policy
        self.iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )
        
        # Attach DynamoDB access policy for testing
        self.iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn='arn:aws:iam::aws:policy/AmazonDynamoDBReadOnlyAccess'
        )
        
        logger.info(f"Created IAM role: {role_arn}")
        return role_arn
    
    def deploy_all_test_functions(self, create_layer: bool = True) -> Dict[str, bool]:
        """Deploy all test functions to AWS Lambda."""
        results = {}
        layer_arn = None
        
        # Create layer if requested
        if create_layer:
            layer_arn = self.create_lambda_layer("cr2a-test-dependencies")
            if not layer_arn:
                logger.warning("Failed to create Lambda layer, deploying functions without layer")
        
        # Deploy each test function
        for function_name in self.test_functions.keys():
            success = self.deploy_test_function(function_name, layer_arn)
            results[function_name] = success
        
        return results
    
    def test_deployed_functions(self) -> Dict[str, Any]:
        """Test all deployed Lambda functions."""
        if not self.lambda_client:
            self._initialize_clients()
        
        results = {}
        
        for function_name in self.test_functions.keys():
            logger.info(f"Testing deployed function: {function_name}")
            
            try:
                # Invoke function with test payload
                test_payload = {
                    "test_mode": True,
                    "required_packages": ["boto3", "json", "os"]
                }
                
                response = self.lambda_client.invoke(
                    FunctionName=function_name,
                    InvocationType='RequestResponse',
                    Payload=json.dumps(test_payload)
                )
                
                # Parse response
                response_payload = json.loads(response['Payload'].read())
                
                results[function_name] = {
                    "status": "SUCCESS" if response['StatusCode'] == 200 else "FAILED",
                    "status_code": response['StatusCode'],
                    "response": response_payload
                }
                
            except Exception as e:
                results[function_name] = {
                    "status": "ERROR",
                    "error": str(e)
                }
                logger.error(f"Failed to test function {function_name}: {e}")
        
        return results
    
    def cleanup_test_functions(self) -> Dict[str, bool]:
        """Remove all deployed test functions."""
        if not self.lambda_client:
            self._initialize_clients()
        
        results = {}
        
        for function_name in self.test_functions.keys():
            try:
                self.lambda_client.delete_function(FunctionName=function_name)
                results[function_name] = True
                logger.info(f"Deleted function: {function_name}")
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    results[function_name] = True  # Already deleted
                    logger.info(f"Function {function_name} already deleted")
                else:
                    results[function_name] = False
                    logger.error(f"Failed to delete function {function_name}: {e}")
            except Exception as e:
                results[function_name] = False
                logger.error(f"Unexpected error deleting function {function_name}: {e}")
        
        return results


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy CR2A Lambda test functions")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--action", choices=["deploy", "test", "cleanup"], 
                       default="deploy", help="Action to perform")
    parser.add_argument("--no-layer", action="store_true", 
                       help="Skip creating Lambda layer")
    parser.add_argument("--function", help="Deploy specific function only")
    
    args = parser.parse_args()
    
    # Initialize deployment manager
    manager = LambdaDeploymentManager(aws_region=args.region)
    
    if args.action == "deploy":
        if args.function:
            # Deploy specific function
            success = manager.deploy_test_function(args.function)
            if success:
                print(f"Successfully deployed {args.function}")
            else:
                print(f"Failed to deploy {args.function}")
        else:
            # Deploy all functions
            results = manager.deploy_all_test_functions(create_layer=not args.no_layer)
            
            print("Deployment Results:")
            for function_name, success in results.items():
                status = "SUCCESS" if success else "FAILED"
                print(f"  {function_name}: {status}")
    
    elif args.action == "test":
        results = manager.test_deployed_functions()
        
        print("Test Results:")
        for function_name, result in results.items():
            print(f"  {function_name}: {result['status']}")
            if result['status'] == "ERROR":
                print(f"    Error: {result['error']}")
    
    elif args.action == "cleanup":
        results = manager.cleanup_test_functions()
        
        print("Cleanup Results:")
        for function_name, success in results.items():
            status = "SUCCESS" if success else "FAILED"
            print(f"  {function_name}: {status}")


if __name__ == "__main__":
    main()