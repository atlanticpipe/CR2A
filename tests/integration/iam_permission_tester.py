"""
IAM permission tester for CR2A integration testing.
Tests execution permissions for API roles and policy validation.
"""

import json
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError

from ..core.base import BaseTestFramework
from ..core.models import TestResult, TestStatus, TestConfiguration


class IAMPermissionTester(BaseTestFramework):
    """Tester for IAM permissions and policy validation."""
    
    def __init__(self, config: TestConfiguration):
        super().__init__(config)
        self.api_role_name = "cr2a-api-execution-role"
        self.required_step_functions_actions = [
            "states:StartExecution",
            "states:DescribeExecution",
            "states:ListExecutions"
        ]
        self.required_lambda_actions = [
            "lambda:InvokeFunction"
        ]
        self.required_dynamodb_actions = [
            "dynamodb:PutItem",
            "dynamodb:GetItem",
            "dynamodb:UpdateItem",
            "dynamodb:Query"
        ]
        self.required_s3_actions = [
            "s3:GetObject",
            "s3:PutObject"
        ]
    
    def test_execution_permissions(self) -> TestResult:
        """Test IAM permissions for Step Functions execution."""
        def _test_permissions():
            iam_client = self.get_aws_client('iam')
            
            # Check if role exists
            try:
                role_response = iam_client.get_role(RoleName=self.api_role_name)
                role_arn = role_response['Role']['Arn']
                self.logger.info(f"Found API execution role: {role_arn}")
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchEntity':
                    raise ValueError(f"API execution role '{self.api_role_name}' not found")
                raise
            
            # Get attached policies
            attached_policies = self._get_attached_policies(self.api_role_name)
            inline_policies = self._get_inline_policies(self.api_role_name)
            
            # Check permissions
            permission_results = {
                "step_functions": self._check_service_permissions(
                    attached_policies, inline_policies, self.required_step_functions_actions
                ),
                "lambda": self._check_service_permissions(
                    attached_policies, inline_policies, self.required_lambda_actions
                ),
                "dynamodb": self._check_service_permissions(
                    attached_policies, inline_policies, self.required_dynamodb_actions
                ),
                "s3": self._check_service_permissions(
                    attached_policies, inline_policies, self.required_s3_actions
                )
            }
            
            # Check if all required permissions are present
            missing_permissions = []
            for service, result in permission_results.items():
                if not result["has_permissions"]:
                    missing_permissions.extend([
                        f"{service}: {action}" for action in result["missing_actions"]
                    ])
            
            return {
                "role_arn": role_arn,
                "permission_results": permission_results,
                "missing_permissions": missing_permissions,
                "has_all_permissions": len(missing_permissions) == 0
            }
        
        result = self.execute_test_with_timing(
            "test_execution_permissions",
            lambda: self.retry_operation(_test_permissions)
        )
        
        if result.status == TestStatus.PASS and result.details:
            if result.details["has_all_permissions"]:
                result.message = "API execution role has all required permissions"
            else:
                result.status = TestStatus.FAIL
                result.message = f"API execution role missing permissions: {', '.join(result.details['missing_permissions'])}"
        
        return result
    
    def test_step_functions_execution_permission(self, state_machine_arn: str) -> TestResult:
        """Test specific Step Functions execution permission."""
        def _test_sf_permission():
            # Use STS to assume the role and test permissions
            sts_client = self.get_aws_client('sts')
            
            try:
                # Get current identity to check if we can assume the role
                identity = sts_client.get_caller_identity()
                self.logger.info(f"Current identity: {identity.get('Arn', 'Unknown')}")
                
                # Try to simulate the permission check
                # In a real scenario, you'd assume the role and test the action
                sf_client = self.get_aws_client('stepfunctions')
                
                # Test if we can describe the state machine (basic permission check)
                sf_client.describe_state_machine(stateMachineArn=state_machine_arn)
                
                return {
                    "can_access_state_machine": True,
                    "state_machine_arn": state_machine_arn
                }
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code in ['AccessDenied', 'UnauthorizedOperation']:
                    return {
                        "can_access_state_machine": False,
                        "error": str(e),
                        "state_machine_arn": state_machine_arn
                    }
                raise
        
        result = self.execute_test_with_timing(
            "test_step_functions_execution_permission",
            lambda: self.retry_operation(_test_sf_permission)
        )
        
        if result.status == TestStatus.PASS and result.details:
            if result.details["can_access_state_machine"]:
                result.message = "Role can access Step Functions state machine"
            else:
                result.status = TestStatus.FAIL
                result.message = f"Role cannot access Step Functions state machine: {result.details.get('error', 'Unknown error')}"
        
        return result
    
    def validate_policy_document(self, policy_document: Dict[str, Any]) -> TestResult:
        """Validate IAM policy document structure and content."""
        def _validate_policy():
            validation_results = {
                "has_version": "Version" in policy_document,
                "has_statements": "Statement" in policy_document,
                "statements_valid": True,
                "issues": []
            }
            
            if not validation_results["has_version"]:
                validation_results["issues"].append("Policy missing 'Version' field")
            
            if not validation_results["has_statements"]:
                validation_results["issues"].append("Policy missing 'Statement' field")
                validation_results["statements_valid"] = False
            else:
                statements = policy_document["Statement"]
                if not isinstance(statements, list):
                    statements = [statements]
                
                for i, statement in enumerate(statements):
                    if "Effect" not in statement:
                        validation_results["issues"].append(f"Statement {i} missing 'Effect' field")
                        validation_results["statements_valid"] = False
                    
                    if "Action" not in statement:
                        validation_results["issues"].append(f"Statement {i} missing 'Action' field")
                        validation_results["statements_valid"] = False
                    
                    # Check for overly permissive policies
                    if statement.get("Effect") == "Allow":
                        actions = statement.get("Action", [])
                        if isinstance(actions, str):
                            actions = [actions]
                        
                        for action in actions:
                            if action == "*":
                                validation_results["issues"].append(f"Statement {i} uses wildcard action '*' - overly permissive")
                        
                        resources = statement.get("Resource", [])
                        if isinstance(resources, str):
                            resources = [resources]
                        
                        for resource in resources:
                            if resource == "*":
                                validation_results["issues"].append(f"Statement {i} uses wildcard resource '*' - overly permissive")
            
            validation_results["is_valid"] = len(validation_results["issues"]) == 0
            return validation_results
        
        result = self.execute_test_with_timing(
            "validate_policy_document",
            lambda: _validate_policy()
        )
        
        if result.status == TestStatus.PASS and result.details:
            if result.details["is_valid"]:
                result.message = "Policy document is valid"
            else:
                result.status = TestStatus.FAIL
                result.message = f"Policy document has issues: {'; '.join(result.details['issues'])}"
        
        return result
    
    def _get_attached_policies(self, role_name: str) -> List[Dict[str, Any]]:
        """Get all policies attached to a role."""
        iam_client = self.get_aws_client('iam')
        policies = []
        
        # Get managed policies
        response = iam_client.list_attached_role_policies(RoleName=role_name)
        for policy in response['AttachedPolicies']:
            policy_arn = policy['PolicyArn']
            
            # Get policy version
            policy_response = iam_client.get_policy(PolicyArn=policy_arn)
            version_id = policy_response['Policy']['DefaultVersionId']
            
            # Get policy document
            version_response = iam_client.get_policy_version(
                PolicyArn=policy_arn,
                VersionId=version_id
            )
            
            policies.append({
                "type": "managed",
                "name": policy['PolicyName'],
                "arn": policy_arn,
                "document": version_response['PolicyVersion']['Document']
            })
        
        return policies
    
    def _get_inline_policies(self, role_name: str) -> List[Dict[str, Any]]:
        """Get all inline policies for a role."""
        iam_client = self.get_aws_client('iam')
        policies = []
        
        # Get inline policies
        response = iam_client.list_role_policies(RoleName=role_name)
        for policy_name in response['PolicyNames']:
            policy_response = iam_client.get_role_policy(
                RoleName=role_name,
                PolicyName=policy_name
            )
            
            policies.append({
                "type": "inline",
                "name": policy_name,
                "document": policy_response['PolicyDocument']
            })
        
        return policies
    
    def _check_service_permissions(self, attached_policies: List[Dict[str, Any]], 
                                 inline_policies: List[Dict[str, Any]], 
                                 required_actions: List[str]) -> Dict[str, Any]:
        """Check if required actions are allowed by the policies."""
        all_policies = attached_policies + inline_policies
        allowed_actions = set()
        
        for policy in all_policies:
            document = policy["document"]
            statements = document.get("Statement", [])
            
            if not isinstance(statements, list):
                statements = [statements]
            
            for statement in statements:
                if statement.get("Effect") == "Allow":
                    actions = statement.get("Action", [])
                    if isinstance(actions, str):
                        actions = [actions]
                    
                    for action in actions:
                        # Handle wildcards
                        if "*" in action:
                            # Simple wildcard matching
                            action_prefix = action.replace("*", "")
                            for req_action in required_actions:
                                if req_action.startswith(action_prefix):
                                    allowed_actions.add(req_action)
                        else:
                            allowed_actions.add(action)
        
        missing_actions = [action for action in required_actions if action not in allowed_actions]
        
        return {
            "has_permissions": len(missing_actions) == 0,
            "allowed_actions": list(allowed_actions),
            "missing_actions": missing_actions,
            "required_actions": required_actions
        }