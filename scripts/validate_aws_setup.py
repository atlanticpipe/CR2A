#!/usr/bin/env python3
"""
AWS setup validation script for CR2A testing framework.
Validates that all required AWS resources are properly configured.
"""

import os
import json
import boto3
import logging
from typing import Dict, List, Optional, Any, Tuple
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AWSSetupValidator:
    """Validates AWS setup for CR2A testing framework."""
    
    def __init__(self, aws_region: str = "us-east-1"):
        """Initialize AWS setup validator."""
        self.aws_region = aws_region
        self.clients = {}
        
        # Expected resources
        self.expected_roles = [
            "cr2a-lambda-test-role",
            "cr2a-stepfunctions-test-role", 
            "cr2a-api-test-role"
        ]
        
        self.expected_log_groups = [
            "/aws/lambda/cr2a-dependency-test",
            "/aws/lambda/cr2a-openai-test",
            "/aws/lambda/cr2a-dynamodb-test",
            "/aws/stepfunctions/cr2a-contract-analysis",
            "/aws/apigateway/cr2a-test-api"
        ]
        
        self.expected_lambda_functions = [
            "cr2a-dependency-test",
            "cr2a-openai-test",
            "cr2a-dynamodb-test"
        ]
    
    def _get_client(self, service: str):
        """Get or create AWS client for service."""
        if service not in self.clients:
            try:
                self.clients[service] = boto3.client(service, region_name=self.aws_region)
                # Test client
                if service == 'iam':
                    self.clients[service].list_roles(MaxItems=1)
                elif service == 'logs':
                    self.clients[service].describe_log_groups(limit=1)
                elif service == 'lambda':
                    self.clients[service].list_functions(MaxItems=1)
                elif service == 'stepfunctions':
                    self.clients[service].list_state_machines(maxResults=1)
                elif service == 'apigateway':
                    self.clients[service].get_account()
                    
            except NoCredentialsError:
                logger.error("AWS credentials not found. Please configure AWS credentials.")
                raise
            except ClientError as e:
                logger.error(f"Failed to initialize {service} client: {e}")
                raise
        
        return self.clients[service]
    
    def validate_iam_roles(self) -> Dict[str, Any]:
        """Validate IAM roles and their policies."""
        iam_client = self._get_client('iam')
        results = {
            "roles": {},
            "overall_status": "UNKNOWN",
            "missing_roles": [],
            "policy_issues": []
        }
        
        for role_name in self.expected_roles:
            role_info = {
                "exists": False,
                "arn": None,
                "policies": [],
                "trust_policy_valid": False,
                "created_date": None
            }
            
            try:
                # Get role
                response = iam_client.get_role(RoleName=role_name)
                role = response['Role']
                
                role_info["exists"] = True
                role_info["arn"] = role['Arn']
                role_info["created_date"] = role['CreateDate'].isoformat()
                
                # Validate trust policy
                trust_policy = role['AssumeRolePolicyDocument']
                if self._validate_trust_policy(trust_policy, role_name):
                    role_info["trust_policy_valid"] = True
                
                # Get attached policies
                try:
                    policies_response = iam_client.list_attached_role_policies(RoleName=role_name)
                    role_info["policies"] = [
                        {
                            "name": policy['PolicyName'],
                            "arn": policy['PolicyArn']
                        }
                        for policy in policies_response['AttachedPolicies']
                    ]
                except ClientError as e:
                    logger.warning(f"Failed to list policies for role {role_name}: {e}")
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchEntity':
                    results["missing_roles"].append(role_name)
                else:
                    logger.error(f"Error checking role {role_name}: {e}")
            
            results["roles"][role_name] = role_info
        
        # Determine overall status
        existing_roles = [name for name, info in results["roles"].items() if info["exists"]]
        if len(existing_roles) == len(self.expected_roles):
            results["overall_status"] = "HEALTHY"
        elif len(existing_roles) > 0:
            results["overall_status"] = "PARTIAL"
        else:
            results["overall_status"] = "FAILED"
        
        return results
    
    def _validate_trust_policy(self, trust_policy: Dict[str, Any], role_name: str) -> bool:
        """Validate trust policy for a role."""
        try:
            statements = trust_policy.get('Statement', [])
            
            for statement in statements:
                if statement.get('Effect') == 'Allow':
                    principal = statement.get('Principal', {})
                    service = principal.get('Service', '')
                    
                    # Check expected service for each role type
                    if 'lambda' in role_name and 'lambda.amazonaws.com' in service:
                        return True
                    elif 'stepfunctions' in role_name and 'states.amazonaws.com' in service:
                        return True
                    elif 'api' in role_name and 'apigateway.amazonaws.com' in service:
                        return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Failed to validate trust policy for {role_name}: {e}")
            return False
    
    def validate_cloudwatch_logs(self) -> Dict[str, Any]:
        """Validate CloudWatch log groups."""
        logs_client = self._get_client('logs')
        results = {
            "log_groups": {},
            "overall_status": "UNKNOWN",
            "missing_log_groups": []
        }
        
        for log_group_name in self.expected_log_groups:
            log_group_info = {
                "exists": False,
                "arn": None,
                "retention_days": None,
                "size_bytes": 0,
                "creation_time": None
            }
            
            try:
                response = logs_client.describe_log_groups(
                    logGroupNamePrefix=log_group_name
                )
                
                # Find exact match
                matching_groups = [
                    lg for lg in response.get('logGroups', [])
                    if lg['logGroupName'] == log_group_name
                ]
                
                if matching_groups:
                    log_group = matching_groups[0]
                    log_group_info["exists"] = True
                    log_group_info["arn"] = log_group['arn']
                    log_group_info["retention_days"] = log_group.get('retentionInDays')
                    log_group_info["size_bytes"] = log_group.get('storedBytes', 0)
                    log_group_info["creation_time"] = datetime.fromtimestamp(
                        log_group['creationTime'] / 1000
                    ).isoformat()
                else:
                    results["missing_log_groups"].append(log_group_name)
                
            except ClientError as e:
                logger.error(f"Error checking log group {log_group_name}: {e}")
                results["missing_log_groups"].append(log_group_name)
            
            results["log_groups"][log_group_name] = log_group_info
        
        # Determine overall status
        existing_groups = [name for name, info in results["log_groups"].items() if info["exists"]]
        if len(existing_groups) == len(self.expected_log_groups):
            results["overall_status"] = "HEALTHY"
        elif len(existing_groups) > 0:
            results["overall_status"] = "PARTIAL"
        else:
            results["overall_status"] = "FAILED"
        
        return results
    
    def validate_lambda_functions(self) -> Dict[str, Any]:
        """Validate Lambda functions."""
        lambda_client = self._get_client('lambda')
        results = {
            "functions": {},
            "overall_status": "UNKNOWN",
            "missing_functions": []
        }
        
        for function_name in self.expected_lambda_functions:
            function_info = {
                "exists": False,
                "arn": None,
                "runtime": None,
                "handler": None,
                "memory_size": None,
                "timeout": None,
                "last_modified": None,
                "layers": []
            }
            
            try:
                response = lambda_client.get_function(FunctionName=function_name)
                config = response['Configuration']
                
                function_info["exists"] = True
                function_info["arn"] = config['FunctionArn']
                function_info["runtime"] = config['Runtime']
                function_info["handler"] = config['Handler']
                function_info["memory_size"] = config['MemorySize']
                function_info["timeout"] = config['Timeout']
                function_info["last_modified"] = config['LastModified']
                function_info["layers"] = [
                    layer['Arn'] for layer in config.get('Layers', [])
                ]
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    results["missing_functions"].append(function_name)
                else:
                    logger.error(f"Error checking function {function_name}: {e}")
                    results["missing_functions"].append(function_name)
            
            results["functions"][function_name] = function_info
        
        # Determine overall status
        existing_functions = [name for name, info in results["functions"].items() if info["exists"]]
        if len(existing_functions) == len(self.expected_lambda_functions):
            results["overall_status"] = "HEALTHY"
        elif len(existing_functions) > 0:
            results["overall_status"] = "PARTIAL"
        else:
            results["overall_status"] = "FAILED"
        
        return results
    
    def validate_step_functions(self) -> Dict[str, Any]:
        """Validate Step Functions state machines."""
        sf_client = self._get_client('stepfunctions')
        results = {
            "state_machines": {},
            "overall_status": "UNKNOWN",
            "cr2a_state_machine_exists": False
        }
        
        try:
            response = sf_client.list_state_machines()
            state_machines = response.get('stateMachines', [])
            
            # Look for CR2A state machine
            cr2a_sm = None
            for sm in state_machines:
                if 'cr2a' in sm['name'].lower():
                    cr2a_sm = sm
                    results["cr2a_state_machine_exists"] = True
                    break
            
            if cr2a_sm:
                sm_info = {
                    "name": cr2a_sm['name'],
                    "arn": cr2a_sm['stateMachineArn'],
                    "status": cr2a_sm['status'],
                    "creation_date": cr2a_sm['creationDate'].isoformat(),
                    "role_arn": None,
                    "definition_valid": False
                }
                
                # Get detailed information
                try:
                    details = sf_client.describe_state_machine(
                        stateMachineArn=cr2a_sm['stateMachineArn']
                    )
                    sm_info["role_arn"] = details.get('roleArn')
                    
                    # Validate definition
                    definition = json.loads(details['definition'])
                    if self._validate_state_machine_definition(definition):
                        sm_info["definition_valid"] = True
                    
                except Exception as e:
                    logger.warning(f"Failed to get state machine details: {e}")
                
                results["state_machines"]["cr2a-contract-analysis"] = sm_info
                results["overall_status"] = "HEALTHY" if sm_info["definition_valid"] else "PARTIAL"
            else:
                results["overall_status"] = "FAILED"
        
        except Exception as e:
            logger.error(f"Error validating Step Functions: {e}")
            results["overall_status"] = "FAILED"
        
        return results
    
    def _validate_state_machine_definition(self, definition: Dict[str, Any]) -> bool:
        """Validate state machine definition structure."""
        try:
            # Check basic structure
            if 'StartAt' not in definition or 'States' not in definition:
                return False
            
            # Check that states reference Lambda functions
            states = definition.get('States', {})
            lambda_states = []
            
            for state_name, state_def in states.items():
                if state_def.get('Type') == 'Task' and 'Resource' in state_def:
                    resource = state_def['Resource']
                    if 'lambda' in resource.lower():
                        lambda_states.append(state_name)
            
            # Should have at least one Lambda state
            return len(lambda_states) > 0
            
        except Exception as e:
            logger.warning(f"Failed to validate state machine definition: {e}")
            return False
    
    def validate_api_gateway(self) -> Dict[str, Any]:
        """Validate API Gateway configuration."""
        api_client = self._get_client('apigateway')
        results = {
            "account_settings": {},
            "apis": {},
            "overall_status": "UNKNOWN"
        }
        
        try:
            # Check account settings
            account = api_client.get_account()
            results["account_settings"] = {
                "cloudwatch_role_arn": account.get('cloudwatchRoleArn'),
                "throttle_burst_limit": account.get('throttleSettings', {}).get('burstLimit'),
                "throttle_rate_limit": account.get('throttleSettings', {}).get('rateLimit')
            }
            
            # List APIs
            apis_response = api_client.get_rest_apis()
            apis = apis_response.get('items', [])
            
            cr2a_apis = [api for api in apis if 'cr2a' in api['name'].lower()]
            
            for api in cr2a_apis:
                api_info = {
                    "id": api['id'],
                    "name": api['name'],
                    "description": api.get('description', ''),
                    "created_date": api['createdDate'].isoformat(),
                    "endpoint_configuration": api.get('endpointConfiguration', {}),
                    "stages": []
                }
                
                # Get stages
                try:
                    stages_response = api_client.get_stages(restApiId=api['id'])
                    api_info["stages"] = [
                        {
                            "name": stage['stageName'],
                            "deployment_id": stage['deploymentId'],
                            "created_date": stage['createdDate'].isoformat()
                        }
                        for stage in stages_response.get('item', [])
                    ]
                except Exception as e:
                    logger.warning(f"Failed to get stages for API {api['name']}: {e}")
                
                results["apis"][api['name']] = api_info
            
            # Determine status
            has_cloudwatch_role = bool(results["account_settings"]["cloudwatch_role_arn"])
            has_cr2a_apis = len(results["apis"]) > 0
            
            if has_cloudwatch_role and has_cr2a_apis:
                results["overall_status"] = "HEALTHY"
            elif has_cloudwatch_role or has_cr2a_apis:
                results["overall_status"] = "PARTIAL"
            else:
                results["overall_status"] = "FAILED"
        
        except Exception as e:
            logger.error(f"Error validating API Gateway: {e}")
            results["overall_status"] = "FAILED"
        
        return results
    
    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive validation of all AWS resources."""
        logger.info("Starting comprehensive AWS setup validation...")
        
        validation_results = {
            "timestamp": datetime.now().isoformat(),
            "region": self.aws_region,
            "iam_roles": {},
            "cloudwatch_logs": {},
            "lambda_functions": {},
            "step_functions": {},
            "api_gateway": {},
            "overall_status": "UNKNOWN",
            "recommendations": []
        }
        
        # Validate each component
        try:
            validation_results["iam_roles"] = self.validate_iam_roles()
        except Exception as e:
            logger.error(f"IAM validation failed: {e}")
            validation_results["iam_roles"]["overall_status"] = "ERROR"
        
        try:
            validation_results["cloudwatch_logs"] = self.validate_cloudwatch_logs()
        except Exception as e:
            logger.error(f"CloudWatch logs validation failed: {e}")
            validation_results["cloudwatch_logs"]["overall_status"] = "ERROR"
        
        try:
            validation_results["lambda_functions"] = self.validate_lambda_functions()
        except Exception as e:
            logger.error(f"Lambda functions validation failed: {e}")
            validation_results["lambda_functions"]["overall_status"] = "ERROR"
        
        try:
            validation_results["step_functions"] = self.validate_step_functions()
        except Exception as e:
            logger.error(f"Step Functions validation failed: {e}")
            validation_results["step_functions"]["overall_status"] = "ERROR"
        
        try:
            validation_results["api_gateway"] = self.validate_api_gateway()
        except Exception as e:
            logger.error(f"API Gateway validation failed: {e}")
            validation_results["api_gateway"]["overall_status"] = "ERROR"
        
        # Determine overall status and recommendations
        component_statuses = [
            validation_results["iam_roles"].get("overall_status", "ERROR"),
            validation_results["cloudwatch_logs"].get("overall_status", "ERROR"),
            validation_results["lambda_functions"].get("overall_status", "ERROR"),
            validation_results["step_functions"].get("overall_status", "ERROR"),
            validation_results["api_gateway"].get("overall_status", "ERROR")
        ]
        
        healthy_count = component_statuses.count("HEALTHY")
        partial_count = component_statuses.count("PARTIAL")
        failed_count = component_statuses.count("FAILED") + component_statuses.count("ERROR")
        
        if healthy_count == len(component_statuses):
            validation_results["overall_status"] = "HEALTHY"
        elif healthy_count + partial_count > failed_count:
            validation_results["overall_status"] = "PARTIAL"
        else:
            validation_results["overall_status"] = "FAILED"
        
        # Generate recommendations
        validation_results["recommendations"] = self._generate_recommendations(validation_results)
        
        logger.info(f"Validation completed. Overall status: {validation_results['overall_status']}")
        return validation_results
    
    def _generate_recommendations(self, validation_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # IAM recommendations
        iam_results = validation_results.get("iam_roles", {})
        if iam_results.get("missing_roles"):
            recommendations.append(
                f"Create missing IAM roles: {', '.join(iam_results['missing_roles'])}"
            )
        
        # CloudWatch recommendations
        logs_results = validation_results.get("cloudwatch_logs", {})
        if logs_results.get("missing_log_groups"):
            recommendations.append(
                f"Create missing log groups: {', '.join(logs_results['missing_log_groups'])}"
            )
        
        # Lambda recommendations
        lambda_results = validation_results.get("lambda_functions", {})
        if lambda_results.get("missing_functions"):
            recommendations.append(
                f"Deploy missing Lambda functions: {', '.join(lambda_results['missing_functions'])}"
            )
        
        # Step Functions recommendations
        sf_results = validation_results.get("step_functions", {})
        if not sf_results.get("cr2a_state_machine_exists"):
            recommendations.append("Deploy CR2A Step Functions state machine")
        
        # API Gateway recommendations
        api_results = validation_results.get("api_gateway", {})
        if not api_results.get("account_settings", {}).get("cloudwatch_role_arn"):
            recommendations.append("Configure API Gateway CloudWatch logging role")
        
        if not recommendations:
            recommendations.append("All AWS resources are properly configured")
        
        return recommendations


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate AWS setup for CR2A testing")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--component", choices=["iam", "logs", "lambda", "stepfunctions", "apigateway", "all"],
                       default="all", help="Component to validate")
    parser.add_argument("--output", choices=["text", "json"], default="text", help="Output format")
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = AWSSetupValidator(aws_region=args.region)
    
    if args.component == "all":
        results = validator.run_comprehensive_validation()
    elif args.component == "iam":
        results = {"iam_roles": validator.validate_iam_roles()}
    elif args.component == "logs":
        results = {"cloudwatch_logs": validator.validate_cloudwatch_logs()}
    elif args.component == "lambda":
        results = {"lambda_functions": validator.validate_lambda_functions()}
    elif args.component == "stepfunctions":
        results = {"step_functions": validator.validate_step_functions()}
    elif args.component == "apigateway":
        results = {"api_gateway": validator.validate_api_gateway()}
    
    if args.output == "json":
        print(json.dumps(results, indent=2, default=str))
    else:
        # Text output
        if "overall_status" in results:
            print(f"Overall Status: {results['overall_status']}")
            print(f"Region: {results.get('region', args.region)}")
            print(f"Timestamp: {results.get('timestamp', 'N/A')}")
            print()
        
        for component, data in results.items():
            if component in ["timestamp", "region", "overall_status", "recommendations"]:
                continue
            
            print(f"{component.upper().replace('_', ' ')}:")
            status = data.get("overall_status", "UNKNOWN")
            print(f"  Status: {status}")
            
            if component == "iam_roles" and "roles" in data:
                for role_name, role_info in data["roles"].items():
                    exists = "EXISTS" if role_info["exists"] else "MISSING"
                    print(f"    {role_name}: {exists}")
            
            elif component == "cloudwatch_logs" and "log_groups" in data:
                for log_group, log_info in data["log_groups"].items():
                    exists = "EXISTS" if log_info["exists"] else "MISSING"
                    print(f"    {log_group}: {exists}")
            
            elif component == "lambda_functions" and "functions" in data:
                for func_name, func_info in data["functions"].items():
                    exists = "EXISTS" if func_info["exists"] else "MISSING"
                    print(f"    {func_name}: {exists}")
            
            print()
        
        if "recommendations" in results:
            print("RECOMMENDATIONS:")
            for rec in results["recommendations"]:
                print(f"  - {rec}")


if __name__ == "__main__":
    main()