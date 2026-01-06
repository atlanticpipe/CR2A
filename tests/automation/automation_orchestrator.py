"""
Test orchestration system for the CR2A testing framework.
Coordinates execution of component, integration, and API tests.
"""

import asyncio
import concurrent.futures
import time
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from ..core.interfaces import TestOrchestrator
from ..core.models import TestConfiguration, TestSuite, TestResult, TestStatus
from ..core.base import BaseTestFramework

# Import test modules
from ..component.dependency_tester import DependencyTester
from ..component.openai_client_tester import OpenAIClientTester
from ..component.dynamodb_tester import DynamoDBTester
from ..integration.integration_tester import CR2AIntegrationTester
from ..integration.api_gateway_tester import APIGatewayTester
from ..integration.step_functions_tester import StepFunctionsTester
from ..integration.iam_permission_tester import IAMPermissionTester


class CR2ATestOrchestrator(TestOrchestrator, BaseTestFramework):
    """Main orchestrator for CR2A testing framework."""
    
    def __init__(self, config: TestConfiguration):
        super().__init__(config)
        self.logger = logging.getLogger("cr2a_testing.orchestrator")
        
        # Initialize test components
        self._component_testers = {
            'dependency': DependencyTester(config),
            'openai_client': OpenAIClientTester(config),
            'dynamodb': DynamoDBTester(config)
        }
        
        # Get API base URL from config or environment
        api_base_url = getattr(config, 'api_base_url', None) or os.environ.get('CR2A_API_BASE_URL', 'https://api.example.com')
        
        self._integration_testers = {
            'step_functions': StepFunctionsTester(config),
            'api_gateway': APIGatewayTester(config, api_base_url),
            'iam_permissions': IAMPermissionTester(config),
            'integration': CR2AIntegrationTester(config, api_base_url)
        }
    
    def run_component_tests(self, config: TestConfiguration) -> TestSuite:
        """Execute all component tests."""
        self.logger.info("Starting component test execution")
        start_time = time.time()
        
        all_tests = []
        
        # Run dependency tests
        try:
            dependency_tester = self._component_testers['dependency']
            dependency_result = dependency_tester.test_dependencies()
            all_tests.append(dependency_result)
        except Exception as e:
            self.logger.error(f"Dependency test failed: {str(e)}")
            all_tests.append(TestResult(
                test_name="dependency_test",
                status=TestStatus.ERROR,
                message=f"Failed to run dependency test: {str(e)}"
            ))
        
        # Run OpenAI client tests
        try:
            openai_tester = self._component_testers['openai_client']
            openai_result = openai_tester.test_openai_client()
            all_tests.append(openai_result)
        except Exception as e:
            self.logger.error(f"OpenAI client test failed: {str(e)}")
            all_tests.append(TestResult(
                test_name="openai_client_test",
                status=TestStatus.ERROR,
                message=f"Failed to run OpenAI client test: {str(e)}"
            ))
        
        # Run DynamoDB tests
        try:
            dynamodb_tester = self._component_testers['dynamodb']
            dynamodb_result = dynamodb_tester.test_dynamodb_operations()
            all_tests.append(dynamodb_result)
        except Exception as e:
            self.logger.error(f"DynamoDB test failed: {str(e)}")
            all_tests.append(TestResult(
                test_name="dynamodb_test",
                status=TestStatus.ERROR,
                message=f"Failed to run DynamoDB test: {str(e)}"
            ))
        
        # Determine overall status
        overall_status = self._determine_overall_status(all_tests)
        execution_time = time.time() - start_time
        
        component_suite = TestSuite(
            name="Component Tests",
            description="Isolated testing of individual Lambda function components",
            tests=all_tests,
            overall_status=overall_status,
            execution_time=execution_time
        )
        
        self.logger.info(f"Component tests completed in {execution_time:.2f}s with status: {overall_status.value}")
        return component_suite
    
    def run_integration_tests(self, config: TestConfiguration) -> TestSuite:
        """Execute all integration tests."""
        self.logger.info("Starting integration test execution")
        start_time = time.time()
        
        all_tests = []
        
        # Run Step Functions tests
        try:
            sf_tester = self._integration_testers['step_functions']
            sf_exists_result = sf_tester.test_state_machine_exists()
            all_tests.append(sf_exists_result)
            
            # Only run execution test if state machine exists
            if sf_exists_result.status == TestStatus.PASS:
                sf_execution_result = sf_tester.run_manual_execution({
                    "bucket": "test-bucket",
                    "key": "test-document.pdf"
                })
                all_tests.append(sf_execution_result)
        except Exception as e:
            self.logger.error(f"Step Functions test failed: {str(e)}")
            all_tests.append(TestResult(
                test_name="step_functions_test",
                status=TestStatus.ERROR,
                message=f"Failed to run Step Functions test: {str(e)}"
            ))
        
        # Run API Gateway tests
        try:
            api_tester = self._integration_testers['api_gateway']
            api_result = api_tester.test_api_endpoints()
            all_tests.append(api_result)
        except Exception as e:
            self.logger.error(f"API Gateway test failed: {str(e)}")
            all_tests.append(TestResult(
                test_name="api_gateway_test",
                status=TestStatus.ERROR,
                message=f"Failed to run API Gateway test: {str(e)}"
            ))
        
        # Run IAM permission tests
        try:
            iam_tester = self._integration_testers['iam_permissions']
            iam_result = iam_tester.test_execution_permissions()
            all_tests.append(iam_result)
        except Exception as e:
            self.logger.error(f"IAM permission test failed: {str(e)}")
            all_tests.append(TestResult(
                test_name="iam_permissions_test",
                status=TestStatus.ERROR,
                message=f"Failed to run IAM permission test: {str(e)}"
            ))
        
        # Determine overall status
        overall_status = self._determine_overall_status(all_tests)
        execution_time = time.time() - start_time
        
        integration_suite = TestSuite(
            name="Integration Tests",
            description="Testing component interactions and workflow orchestration",
            tests=all_tests,
            overall_status=overall_status,
            execution_time=execution_time
        )
        
        self.logger.info(f"Integration tests completed in {execution_time:.2f}s with status: {overall_status.value}")
        return integration_suite
    
    def run_full_test_suite(self, config: TestConfiguration) -> List[TestSuite]:
        """Execute complete test suite with all phases."""
        self.logger.info("Starting full test suite execution")
        start_time = time.time()
        
        test_suites = []
        
        # Phase 1: Component Tests
        self.logger.info("Phase 1: Component Isolation Testing")
        component_suite = self.run_component_tests(config)
        test_suites.append(component_suite)
        
        # Only proceed to integration tests if component tests pass
        if component_suite.overall_status in [TestStatus.PASS, TestStatus.SKIP]:
            # Phase 2: Integration Tests
            self.logger.info("Phase 2: Integration Testing")
            integration_suite = self.run_integration_tests(config)
            test_suites.append(integration_suite)
        else:
            self.logger.warning("Skipping integration tests due to component test failures")
            integration_suite = TestSuite(
                name="Integration Tests",
                description="Skipped due to component test failures",
                tests=[],
                overall_status=TestStatus.SKIP,
                execution_time=0.0
            )
            test_suites.append(integration_suite)
        
        total_execution_time = time.time() - start_time
        self.logger.info(f"Full test suite completed in {total_execution_time:.2f}s")
        
        return test_suites
    
    def run_parallel_tests(self, config: TestConfiguration) -> List[TestSuite]:
        """Execute tests in parallel where possible."""
        self.logger.info("Starting parallel test execution")
        
        if not config.parallel_execution:
            return self.run_full_test_suite(config)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # Submit component tests
            component_future = executor.submit(self.run_component_tests, config)
            
            # Wait for component tests to complete before starting integration tests
            component_suite = component_future.result()
            
            if component_suite.overall_status in [TestStatus.PASS, TestStatus.SKIP]:
                integration_future = executor.submit(self.run_integration_tests, config)
                integration_suite = integration_future.result()
            else:
                integration_suite = TestSuite(
                    name="Integration Tests",
                    description="Skipped due to component test failures",
                    tests=[],
                    overall_status=TestStatus.SKIP,
                    execution_time=0.0
                )
        
        return [component_suite, integration_suite]
    
    def run_scheduled_tests(self, schedule_config: Dict[str, Any]) -> List[TestSuite]:
        """Execute tests based on scheduling configuration."""
        self.logger.info(f"Running scheduled tests with config: {schedule_config}")
        
        # Extract schedule parameters
        test_types = schedule_config.get('test_types', ['component', 'integration'])
        interval = schedule_config.get('interval_minutes', 60)
        max_runs = schedule_config.get('max_runs', 1)
        
        all_results = []
        
        for run_number in range(max_runs):
            self.logger.info(f"Scheduled test run {run_number + 1}/{max_runs}")
            
            if 'component' in test_types and 'integration' in test_types:
                results = self.run_full_test_suite(self.config)
            elif 'component' in test_types:
                results = [self.run_component_tests(self.config)]
            elif 'integration' in test_types:
                results = [self.run_integration_tests(self.config)]
            else:
                self.logger.warning("No valid test types specified in schedule")
                continue
            
            all_results.extend(results)
            
            # Wait for next run if not the last one
            if run_number < max_runs - 1:
                self.logger.info(f"Waiting {interval} minutes for next scheduled run")
                time.sleep(interval * 60)
        
        return all_results
    
    def generate_summary_report(self, test_suites: List[TestSuite]) -> Dict[str, Any]:
        """Generate summary report across all test suites."""
        total_tests = sum(len(suite.tests) for suite in test_suites)
        total_passed = sum(
            len([test for test in suite.tests if test.status == TestStatus.PASS])
            for suite in test_suites
        )
        total_failed = sum(
            len([test for test in suite.tests if test.status == TestStatus.FAIL])
            for suite in test_suites
        )
        total_errors = sum(
            len([test for test in suite.tests if test.status == TestStatus.ERROR])
            for suite in test_suites
        )
        total_skipped = sum(
            len([test for test in suite.tests if test.status == TestStatus.SKIP])
            for suite in test_suites
        )
        
        total_execution_time = sum(suite.execution_time for suite in test_suites)
        
        # Determine overall status
        if total_errors > 0:
            overall_status = TestStatus.ERROR
        elif total_failed > 0:
            overall_status = TestStatus.FAIL
        elif total_passed > 0:
            overall_status = TestStatus.PASS
        else:
            overall_status = TestStatus.SKIP
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': overall_status.value,
            'total_test_suites': len(test_suites),
            'total_tests': total_tests,
            'total_passed': total_passed,
            'total_failed': total_failed,
            'total_errors': total_errors,
            'total_skipped': total_skipped,
            'pass_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0.0,
            'total_execution_time': total_execution_time,
            'test_suites': [
                {
                    'name': suite.name,
                    'status': suite.overall_status.value,
                    'test_count': len(suite.tests),
                    'pass_rate': suite.get_pass_rate(),
                    'execution_time': suite.execution_time
                }
                for suite in test_suites
            ]
        }
        
        return summary
    
    def _determine_overall_status(self, test_results: List[TestResult]) -> TestStatus:
        """Determine overall status from a list of test results."""
        if not test_results:
            return TestStatus.SKIP
        
        # Check for errors first
        if any(test.status == TestStatus.ERROR for test in test_results):
            return TestStatus.ERROR
        
        # Check for failures
        if any(test.status == TestStatus.FAIL for test in test_results):
            return TestStatus.FAIL
        
        # Check if all are skipped
        if all(test.status == TestStatus.SKIP for test in test_results):
            return TestStatus.SKIP
        
        # If we have at least one pass and no failures/errors
        if any(test.status == TestStatus.PASS for test in test_results):
            return TestStatus.PASS
        
        return TestStatus.SKIP