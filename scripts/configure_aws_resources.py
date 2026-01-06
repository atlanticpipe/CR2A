#!/usr/bin/env python3
"""
AWS resource configuration script for CR2A testing framework.
Sets up IAM roles, policies, CloudWatch log groups, and other required resources.
"""

import os
import json
import boto3
import logging
import time
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError, NoCredentialsError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AWSResourceConfigurator:
    """Configures AWS resources for CR2A testing framework."""
    
    def __init__(self, aws_region: str = "us-east-1"):
        """Initialize AWS resource configurator."""
        self.aws_region = aws_region
        self.iam_client = None
        self.logs_client = None
        self.stepfunctions_client = None
        self.apigateway_client = None
        
        # Resource configurations
        self.iam_roles = {
            "cr2a-lambda-test-role": {
                "description": "IAM role for CR2A Lambda test functions",
                "trust_policy": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "lambda.amazonaws.com"},
                            "Action": "sts:AssumeRole"
                        }
                    ]
                },
                "managed_policies": [
                    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                    "arn:aws:iam::aws:policy/AmazonDynamoDBReadOnlyAccess",
                    "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
                ]
            },
            "cr2a-stepfunctions-test-role": {
                "description": "IAM role for CR2A Step Functions testing",
                "trust_policy": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "states.amazonaws.com"},
                            "Action": "sts:AssumeRole"
                        }
                    ]
                },
                "managed_policies": [
                    "arn:aws:iam::aws:policy/service-role/AWSLambdaRole",
                    "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
                ]
            },
            "cr2a-api-test-role": {
                "description": "IAM role for CR2A API Gateway testing",
                "trust_policy": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "apigateway.amazonaws.com"},
                            "Action": "sts:AssumeRole"
                        }
                    ]
                },
                "managed_policies": [
                    "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs",
                    "arn:aws:iam::aws:policy/AWSStepFunctionsFullAccess"
                ]
            }
        }
        
        self.log_groups = [
            "/aws/lambda/cr2a-dependency-test",
            "/aws/lambda/cr2a-openai-test", 
            "/aws/lambda/cr2a-dynamodb-test",
            "/aws/stepfunctions/cr2a-contract-analysis",
            "/aws/apigateway/cr2a-test-api"
        ]
    
    def _initialize_clients(self):
        """Initialize AWS clients."""
        try:
            self.iam_client = boto3.client('iam', region_name=self.aws_region)
            self.logs_client = boto3.client('logs', region_name=self.aws_region)
            self.stepfunctions_client = boto3.client('stepfunctions', region_name=self.aws_region)
            self.apigateway_client = boto3.client('apigateway', region_name=self.aws_region)
            
            # Test credentials
            self.iam_client.list_roles(MaxItems=1)
            logger.info(f"AWS clients initialized for region: {self.aws_region}")
            
        except NoCredentialsError:
            logger.error("AWS credentials not found. Please configure AWS credentials.")
            raise
        except ClientError as e:
            logger.error(f"Failed to initialize AWS clients: {e}")
            raise
    
    def create_iam_role(self, role_name: str) -> Optional[str]:
        """Create IAM role with policies."""
        if not self.iam_client:
            self._initialize_clients()
        
        if role_name not in self.iam_roles:
            logger.error(f"Unknown role configuration: {role_name}")
            return None
        
        config = self.iam_roles[role_name]
        
        try:
            # Check if role already exists
            try:
                response = self.iam_client.get_role(RoleName=role_name)
                role_arn = response['Role']['Arn']
                logger.info(f"IAM role already exists: {role_arn}")
                
                # Update trust policy if needed
                self.iam_client.update_assume_role_policy(
                    RoleName=role_name,
                    PolicyDocument=json.dumps(config['trust_policy'])
                )
                
                # Ensure managed policies are attached
                for policy_arn in config['managed_policies']:
                    try:
                        self.iam_client.attach_role_policy(
                            RoleName=role_name,
                            PolicyArn=policy_arn
                        )
                    except ClientError as e:
                        if e.response['Error']['Code'] != 'EntityAlreadyExists':
                            logger.warning(f"Failed to attach policy {policy_arn}: {e}")
                
                return role_arn
                
            except ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchEntity':
                    raise
            
            # Create new role
            logger.info(f"Creating IAM role: {role_name}")
            
            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(config['trust_policy']),
                Description=config['description']
            )
            
            role_arn = response['Role']['Arn']
            logger.info(f"Created IAM role: {role_arn}")
            
            # Wait for role to be available
            time.sleep(10)
            
            # Attach managed policies
            for policy_arn in config['managed_policies']:
                try:
                    self.iam_client.attach_role_policy(
                        RoleName=role_name,
                        PolicyArn=policy_arn
                    )
                    logger.info(f"Attached policy {policy_arn} to role {role_name}")
                except ClientError as e:
                    logger.error(f"Failed to attach policy {policy_arn}: {e}")
            
            return role_arn
            
        except Exception as e:
            logger.error(f"Failed to create IAM role {role_name}: {e}")
            return None
    
    def create_custom_policies(self) -> Dict[str, Optional[str]]:
        """Create custom IAM policies for CR2A testing."""
        policies = {}
        
        # Custom policy for Step Functions execution
        stepfunctions_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "states:StartExecution",
                        "states:DescribeExecution",
                        "states:StopExecution",
                        "states:ListExecutions",
                        "states:DescribeStateMachine"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "lambda:InvokeFunction"
                    ],
                    "Resource": "arn:aws:lambda:*:*:function:cr2a-*"
                }
            ]
        }
        
        # Custom policy for testing framework
        testing_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DescribeLogGroups",
                        "logs:DescribeLogStreams",
                        "logs:FilterLogEvents"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                        "dynamodb:DescribeTable"
                    ],
                    "Resource": "arn:aws:dynamodb:*:*:table/cr2a-*"
                }
            ]
        }
        
        policy_configs = {
            "CR2AStepFunctionsTestPolicy": stepfunctions_policy,
            "CR2ATestingFrameworkPolicy": testing_policy
        }
        
        for policy_name, policy_document in policy_configs.items():
            try:
                # Check if policy exists
                try:
                    response = self.iam_client.get_policy(
                        PolicyArn=f"arn:aws:iam::{self._get_account_id()}:policy/{policy_name}"
                    )
                    policies[policy_name] = response['Policy']['Arn']
                    logger.info(f"Policy already exists: {policy_name}")
                    continue
                except ClientError as e:
                    if e.response['Error']['Code'] != 'NoSuchEntity':
                        raise
                
                # Create policy
                response = self.iam_client.create_policy(
                    PolicyName=policy_name,
                    PolicyDocument=json.dumps(policy_document),
                    Description=f"Custom policy for CR2A testing framework - {policy_name}"
                )
                
                policies[policy_name] = response['Policy']['Arn']
                logger.info(f"Created policy: {policy_name}")
                
            except Exception as e:
                logger.error(f"Failed to create policy {policy_name}: {e}")
                policies[policy_name] = None
        
        return policies
    
    def _get_account_id(self) -> str:
        """Get AWS account ID."""
        try:
            sts_client = boto3.client('sts')
            response = sts_client.get_caller_identity()
            return response['Account']
        except Exception as e:
            logger.error(f"Failed to get account ID: {e}")
            return "000000000000"  # Fallback
    
    def create_cloudwatch_log_groups(self) -> Dict[str, bool]:
        """Create CloudWatch log groups for CR2A components."""
        if not self.logs_client:
            self._initialize_clients()
        
        results = {}
        
        for log_group_name in self.log_groups:
            try:
                # Check if log group exists
                try:
                    self.logs_client.describe_log_groups(
                        logGroupNamePrefix=log_group_name,
                        limit=1
                    )
                    
                    # Check if exact match exists
                    response = self.logs_client.describe_log_groups(
                        logGroupNamePrefix=log_group_name
                    )
                    
                    exists = any(lg['logGroupName'] == log_group_name 
                               for lg in response.get('logGroups', []))
                    
                    if exists:
                        logger.info(f"Log group already exists: {log_group_name}")
                        results[log_group_name] = True
                        continue
                        
                except ClientError:
                    pass  # Log group doesn't exist
                
                # Create log group
                self.logs_client.create_log_group(
                    logGroupName=log_group_name,
                    tags={
                        'Project': 'CR2A',
                        'Component': 'Testing',
                        'Environment': 'Test'
                    }
                )
                
                # Set retention policy (30 days)
                self.logs_client.put_retention_policy(
                    logGroupName=log_group_name,
                    retentionInDays=30
                )
                
                logger.info(f"Created log group: {log_group_name}")
                results[log_group_name] = True
                
            except Exception as e:
                logger.error(f"Failed to create log group {log_group_name}: {e}")
                results[log_group_name] = False
        
        return results
    
    def validate_step_functions_permissions(self) -> Dict[str, Any]:
        """Validate Step Functions permissions and configuration."""
        if not self.stepfunctions_client:
            self._initialize_clients()
        
        validation_results = {
            "state_machines": [],
            "execution_role_valid": False,
            "lambda_invoke_permissions": []
        }
        
        try:
            # List state machines
            response = self.stepfunctions_client.list_state_machines()
            state_machines = response.get('stateMachines', [])
            
            for sm in state_machines:
                if 'cr2a' in sm['name'].lower():
                    validation_results["state_machines"].append({
                        "name": sm['name'],
                        "arn": sm['stateMachineArn'],
                        "status": sm['status']
                    })
            
            # Check execution role for cr2a-contract-analysis if it exists
            cr2a_sm = next((sm for sm in state_machines 
                           if sm['name'] == 'cr2a-contract-analysis'), None)
            
            if cr2a_sm:
                try:
                    sm_details = self.stepfunctions_client.describe_state_machine(
                        stateMachineArn=cr2a_sm['stateMachineArn']
                    )
                    
                    role_arn = sm_details.get('roleArn')
                    if role_arn:
                        # Validate role exists and has correct permissions
                        role_name = role_arn.split('/')[-1]
                        try:
                            self.iam_client.get_role(RoleName=role_name)
                            validation_results["execution_role_valid"] = True
                        except ClientError:
                            validation_results["execution_role_valid"] = False
                    
                except Exception as e:
                    logger.warning(f"Failed to validate state machine role: {e}")
            
        except Exception as e:
            logger.error(f"Failed to validate Step Functions permissions: {e}")
        
        return validation_results
    
    def setup_api_gateway_logging(self) -> bool:
        """Set up API Gateway logging configuration."""
        if not self.apigateway_client:
            self._initialize_clients()
        
        try:
            # Get account settings
            try:
                account = self.apigateway_client.get_account()
                current_role = account.get('cloudwatchRoleArn')
                
                if current_role:
                    logger.info(f"API Gateway CloudWatch role already configured: {current_role}")
                    return True
                    
            except ClientError:
                pass  # Account settings not configured
            
            # Create or get API Gateway CloudWatch role
            role_arn = self.create_iam_role("cr2a-api-test-role")
            if not role_arn:
                logger.error("Failed to create API Gateway role")
                return False
            
            # Update account settings
            self.apigateway_client.update_account(
                patchOps=[
                    {
                        'op': 'replace',
                        'path': '/cloudwatchRoleArn',
                        'value': role_arn
                    }
                ]
            )
            
            logger.info("Configured API Gateway CloudWatch logging")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup API Gateway logging: {e}")
            return False
    
    def validate_resource_configuration(self) -> Dict[str, Any]:
        """Validate all AWS resource configurations."""
        validation_results = {
            "iam_roles": {},
            "log_groups": {},
            "step_functions": {},
            "api_gateway": {},
            "overall_status": "UNKNOWN"
        }
        
        # Validate IAM roles
        for role_name in self.iam_roles.keys():
            try:
                response = self.iam_client.get_role(RoleName=role_name)
                validation_results["iam_roles"][role_name] = {
                    "exists": True,
                    "arn": response['Role']['Arn'],
                    "created": response['Role']['CreateDate'].isoformat()
                }
            except ClientError:
                validation_results["iam_roles"][role_name] = {
                    "exists": False,
                    "arn": None,
                    "created": None
                }
        
        # Validate log groups
        for log_group in self.log_groups:
            try:
                response = self.logs_client.describe_log_groups(
                    logGroupNamePrefix=log_group
                )
                exists = any(lg['logGroupName'] == log_group 
                           for lg in response.get('logGroups', []))
                validation_results["log_groups"][log_group] = exists
            except Exception:
                validation_results["log_groups"][log_group] = False
        
        # Validate Step Functions
        validation_results["step_functions"] = self.validate_step_functions_permissions()
        
        # Validate API Gateway
        try:
            account = self.apigateway_client.get_account()
            validation_results["api_gateway"]["cloudwatch_role"] = account.get('cloudwatchRoleArn')
        except Exception:
            validation_results["api_gateway"]["cloudwatch_role"] = None
        
        # Determine overall status
        iam_ok = all(role['exists'] for role in validation_results["iam_roles"].values())
        logs_ok = all(validation_results["log_groups"].values())
        
        if iam_ok and logs_ok:
            validation_results["overall_status"] = "HEALTHY"
        elif iam_ok or logs_ok:
            validation_results["overall_status"] = "PARTIAL"
        else:
            validation_results["overall_status"] = "FAILED"
        
        return validation_results
    
    def setup_all_resources(self) -> Dict[str, Any]:
        """Set up all AWS resources for CR2A testing."""
        results = {
            "iam_roles": {},
            "custom_policies": {},
            "log_groups": {},
            "api_gateway_logging": False
        }
        
        logger.info("Setting up AWS resources for CR2A testing framework...")
        
        # Create custom policies first
        results["custom_policies"] = self.create_custom_policies()
        
        # Create IAM roles
        for role_name in self.iam_roles.keys():
            role_arn = self.create_iam_role(role_name)
            results["iam_roles"][role_name] = role_arn
        
        # Create CloudWatch log groups
        results["log_groups"] = self.create_cloudwatch_log_groups()
        
        # Setup API Gateway logging
        results["api_gateway_logging"] = self.setup_api_gateway_logging()
        
        logger.info("AWS resource setup completed")
        return results
    
    def cleanup_resources(self) -> Dict[str, bool]:
        """Clean up AWS resources created for testing."""
        results = {}
        
        logger.info("Cleaning up AWS resources...")
        
        # Delete IAM roles
        for role_name in self.iam_roles.keys():
            try:
                # Detach managed policies
                for policy_arn in self.iam_roles[role_name]['managed_policies']:
                    try:
                        self.iam_client.detach_role_policy(
                            RoleName=role_name,
                            PolicyArn=policy_arn
                        )
                    except ClientError:
                        pass  # Policy might not be attached
                
                # Delete role
                self.iam_client.delete_role(RoleName=role_name)
                results[f"role_{role_name}"] = True
                logger.info(f"Deleted IAM role: {role_name}")
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchEntity':
                    results[f"role_{role_name}"] = True  # Already deleted
                else:
                    results[f"role_{role_name}"] = False
                    logger.error(f"Failed to delete role {role_name}: {e}")
        
        # Delete log groups
        for log_group in self.log_groups:
            try:
                self.logs_client.delete_log_group(logGroupName=log_group)
                results[f"log_group_{log_group.replace('/', '_')}"] = True
                logger.info(f"Deleted log group: {log_group}")
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    results[f"log_group_{log_group.replace('/', '_')}"] = True  # Already deleted
                else:
                    results[f"log_group_{log_group.replace('/', '_')}"] = False
                    logger.error(f"Failed to delete log group {log_group}: {e}")
        
        return results


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Configure AWS resources for CR2A testing")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--action", choices=["setup", "validate", "cleanup"], 
                       default="setup", help="Action to perform")
    parser.add_argument("--resource", choices=["iam", "logs", "stepfunctions", "apigateway", "all"],
                       default="all", help="Specific resource type to configure")
    
    args = parser.parse_args()
    
    # Initialize configurator
    configurator = AWSResourceConfigurator(aws_region=args.region)
    
    if args.action == "setup":
        if args.resource == "all":
            results = configurator.setup_all_resources()
            
            print("AWS Resource Setup Results:")
            print(f"IAM Roles:")
            for role_name, role_arn in results["iam_roles"].items():
                status = "SUCCESS" if role_arn else "FAILED"
                print(f"  {role_name}: {status}")
            
            print(f"Log Groups:")
            for log_group, success in results["log_groups"].items():
                status = "SUCCESS" if success else "FAILED"
                print(f"  {log_group}: {status}")
            
            print(f"API Gateway Logging: {'SUCCESS' if results['api_gateway_logging'] else 'FAILED'}")
            
        elif args.resource == "iam":
            for role_name in configurator.iam_roles.keys():
                role_arn = configurator.create_iam_role(role_name)
                status = "SUCCESS" if role_arn else "FAILED"
                print(f"IAM Role {role_name}: {status}")
        
        elif args.resource == "logs":
            results = configurator.create_cloudwatch_log_groups()
            print("CloudWatch Log Groups:")
            for log_group, success in results.items():
                status = "SUCCESS" if success else "FAILED"
                print(f"  {log_group}: {status}")
    
    elif args.action == "validate":
        results = configurator.validate_resource_configuration()
        
        print(f"Resource Validation Results - Overall Status: {results['overall_status']}")
        
        print("IAM Roles:")
        for role_name, info in results["iam_roles"].items():
            status = "EXISTS" if info["exists"] else "MISSING"
            print(f"  {role_name}: {status}")
        
        print("Log Groups:")
        for log_group, exists in results["log_groups"].items():
            status = "EXISTS" if exists else "MISSING"
            print(f"  {log_group}: {status}")
        
        print("Step Functions:")
        sf_info = results["step_functions"]
        print(f"  State Machines Found: {len(sf_info['state_machines'])}")
        print(f"  Execution Role Valid: {sf_info['execution_role_valid']}")
    
    elif args.action == "cleanup":
        results = configurator.cleanup_resources()
        
        print("Cleanup Results:")
        for resource, success in results.items():
            status = "SUCCESS" if success else "FAILED"
            print(f"  {resource}: {status}")


if __name__ == "__main__":
    main()