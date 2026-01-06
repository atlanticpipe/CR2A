"""
Property-based tests for CR2A test automation framework.
Tests comprehensive test automation capabilities across all test types.

Feature: cr2a-testing-debugging, Property 15: Comprehensive test automation
Validates: Requirements 6.1, 6.2, 6.3
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from typing import List, Dict, Any
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock

from ..core.models import TestConfiguration, TestSuite, TestResult, TestStatus
from ..automation.automation_manager import CR2AAutomationManager
from ..automation.automation_orchestrator import CR2ATestOrchestrator


class TestAutomationProperty:
    """Property-based tests for test automation framework."""
    
    def setup_method(self):
        """Set up test environment for each test method."""
        # Create temporary directory for test artifacts
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test configuration
        self.test_config = TestConfiguration(
            aws_region="us-east-1",
            lambda_timeout=30,
            max_retries=3,
            parallel_execution=False,
            verbose_logging=False,  # Reduce noise in tests
            save_artifacts=True,
            artifact_path=self.temp_dir,
            api_base_url="https://test-api.example.com"
        )
    
    def teardown_method(self):
        """Clean up test environment after each test method."""
        # Clean up temporary directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @given(
        test_types=st.lists(
            st.sampled_from(['component', 'integration']),
            min_size=1,
            max_size=2,
            unique=True
        ),
        generate_reports=st.booleans()
    )
    @settings(max_examples=100, deadline=None)
    def test_comprehensive_test_automation_execution(self, test_types: List[str], generate_reports: bool):
        """
        Property 15: Comprehensive test automation
        
        For any valid test type configuration, the automation system should execute 
        the appropriate test functions and workflows according to the specified types.
        
        **Validates: Requirements 6.1, 6.2, 6.3**
        """
        # Mock the underlying test components to avoid actual AWS calls
        with patch('tests.automation.automation_orchestrator.DependencyTester') as mock_dep_tester, \
             patch('tests.automation.automation_orchestrator.OpenAIClientTester') as mock_openai_tester, \
             patch('tests.automation.automation_orchestrator.DynamoDBTester') as mock_db_tester, \
             patch('tests.automation.automation_orchestrator.StepFunctionsTester') as mock_sf_tester, \
             patch('tests.automation.automation_orchestrator.APIGatewayTester') as mock_api_tester, \
             patch('tests.automation.automation_orchestrator.IAMPermissionTester') as mock_iam_tester, \
             patch('tests.automation.automation_orchestrator.CR2AIntegrationTester') as mock_int_tester:
            
            # Configure mock component testers
            self._setup_component_mocks(mock_dep_tester, mock_openai_tester, mock_db_tester)
            
            # Configure mock integration testers  
            self._setup_integration_mocks(mock_sf_tester, mock_api_tester, mock_iam_tester, mock_int_tester)
            
            # Create automation manager
            automation_manager = CR2AAutomationManager(self.test_config)
            
            # Execute tests based on specified types
            test_suites = automation_manager.run_tests(test_types, generate_reports)
            
            # Verify that test suites were returned
            assert isinstance(test_suites, list), "Test automation should return a list of test suites"
            assert len(test_suites) > 0, "Test automation should execute at least one test suite"
            
            # Verify test execution based on requirements
            if 'component' in test_types:
                # Requirement 6.1: Execute automated Lambda test functions
                component_suite = self._find_suite_by_name(test_suites, "Component Tests")
                assert component_suite is not None, "Component tests should be executed when requested"
                assert len(component_suite.tests) > 0, "Component test suite should contain test results"
                
                # Verify Lambda test functions were called
                mock_dep_tester.assert_called()
                mock_openai_tester.assert_called()
                mock_db_tester.assert_called()
            
            if 'integration' in test_types:
                # Requirement 6.2: Execute automated Step Functions test workflows
                # Requirement 6.3: Execute automated HTTP request sequences (API tests are part of integration)
                integration_suite = self._find_suite_by_name(test_suites, "Integration Tests")
                assert integration_suite is not None, "Integration tests should be executed when requested"
                assert len(integration_suite.tests) > 0, "Integration test suite should contain test results"
                
                # Verify Step Functions test workflows were called
                mock_sf_tester.assert_called()
                mock_iam_tester.assert_called()
                
                # Verify API Gateway tester was called for HTTP request sequences
                mock_api_tester.assert_called()
            
            # Verify all test suites have proper structure
            for suite in test_suites:
                assert isinstance(suite, TestSuite), "Each result should be a TestSuite instance"
                assert suite.name, "Each test suite should have a name"
                assert suite.description, "Each test suite should have a description"
                assert isinstance(suite.tests, list), "Each test suite should contain a list of tests"
                assert isinstance(suite.overall_status, TestStatus), "Each test suite should have a status"
                assert suite.execution_time >= 0, "Execution time should be non-negative"
                
                # Verify individual test results
                for test in suite.tests:
                    assert isinstance(test, TestResult), "Each test should be a TestResult instance"
                    assert test.test_name, "Each test should have a name"
                    assert test.message, "Each test should have a message"
                    assert isinstance(test.status, TestStatus), "Each test should have a status"
                    assert test.execution_time >= 0, "Test execution time should be non-negative"
            
            # Verify report generation if requested
            if generate_reports:
                # Check that report files were created in the artifacts directory
                artifact_files = os.listdir(self.temp_dir)
                if len(test_suites) > 0:  # Only check if tests were actually run
                    assert any(f.endswith('.html') for f in artifact_files), \
                        "HTML report should be generated when reports are requested"
                    assert any(f.endswith('.json') for f in artifact_files), \
                        "JSON report should be generated when reports are requested"
    
    @given(
        schedule_config=st.fixed_dictionaries({
            'interval_type': st.sampled_from(['hours', 'days']),
            'interval_value': st.integers(min_value=1, max_value=24),
            'test_types': st.lists(
                st.sampled_from(['component', 'integration']),
                min_size=1,
                max_size=2,
                unique=True
            ),
            'start_time': st.sampled_from(['09:00', '12:00', '18:00'])
        })
    )
    @settings(max_examples=50, deadline=None)
    def test_scheduled_test_automation(self, schedule_config: Dict[str, Any]):
        """
        Property: Scheduled test automation configuration
        
        For any valid schedule configuration, the automation system should 
        properly configure scheduled test execution without errors.
        
        **Validates: Requirements 6.1, 6.2, 6.3 (scheduled execution)**
        """
        # Mock the underlying components
        with patch('tests.automation.automation_orchestrator.DependencyTester'), \
             patch('tests.automation.automation_orchestrator.OpenAIClientTester'), \
             patch('tests.automation.automation_orchestrator.DynamoDBTester'), \
             patch('tests.automation.automation_orchestrator.StepFunctionsTester'), \
             patch('tests.automation.automation_orchestrator.APIGatewayTester'), \
             patch('tests.automation.automation_orchestrator.IAMPermissionTester'), \
             patch('tests.automation.automation_orchestrator.CR2AIntegrationTester'):
            
            # Create automation manager
            automation_manager = CR2AAutomationManager(self.test_config)
            
            # Test scheduling configuration
            try:
                automation_manager.schedule_tests(schedule_config)
                
                # Verify scheduling was configured without errors
                assert len(automation_manager._scheduled_jobs) > 0, \
                    "Scheduled jobs should be created for valid configuration"
                
                # Clean up scheduled jobs
                automation_manager.clear_scheduled_tests()
                assert len(automation_manager._scheduled_jobs) == 0, \
                    "Scheduled jobs should be cleared properly"
                
            except Exception as e:
                pytest.fail(f"Scheduling should not fail for valid configuration: {e}")
    
    @given(
        trigger_config=st.fixed_dictionaries({
            'trigger_type': st.sampled_from(['manual', 'webhook', 'file_change']),
            'test_types': st.lists(
                st.sampled_from(['component', 'integration']),
                min_size=1,
                max_size=2,
                unique=True
            )
        })
    )
    @settings(max_examples=50, deadline=None)
    def test_triggered_test_automation(self, trigger_config: Dict[str, Any]):
        """
        Property: Triggered test automation execution
        
        For any valid trigger configuration, the automation system should 
        execute tests and include trigger metadata in results.
        
        **Validates: Requirements 6.1, 6.2, 6.3 (triggered execution)**
        """
        # Mock the underlying components
        with patch('tests.automation.automation_orchestrator.DependencyTester') as mock_dep_tester, \
             patch('tests.automation.automation_orchestrator.OpenAIClientTester') as mock_openai_tester, \
             patch('tests.automation.automation_orchestrator.DynamoDBTester') as mock_db_tester, \
             patch('tests.automation.automation_orchestrator.StepFunctionsTester') as mock_sf_tester, \
             patch('tests.automation.automation_orchestrator.APIGatewayTester') as mock_api_tester, \
             patch('tests.automation.automation_orchestrator.IAMPermissionTester') as mock_iam_tester, \
             patch('tests.automation.automation_orchestrator.CR2AIntegrationTester') as mock_int_tester:
            
            # Configure mocks
            self._setup_component_mocks(mock_dep_tester, mock_openai_tester, mock_db_tester)
            self._setup_integration_mocks(mock_sf_tester, mock_api_tester, mock_iam_tester, mock_int_tester)
            
            # Create automation manager
            automation_manager = CR2AAutomationManager(self.test_config)
            
            # Execute triggered tests
            test_suites = automation_manager.run_triggered_tests(trigger_config)
            
            # Verify test execution
            assert isinstance(test_suites, list), "Triggered tests should return a list of test suites"
            assert len(test_suites) > 0, "Triggered tests should execute at least one test suite"
            
            # Verify trigger metadata is included
            for suite in test_suites:
                assert hasattr(suite, 'metadata'), "Test suites should include trigger metadata"
                assert 'trigger_type' in suite.metadata, "Trigger type should be recorded in metadata"
                assert suite.metadata['trigger_type'] == trigger_config['trigger_type'], \
                    "Trigger type should match the configuration"
                assert 'trigger_time' in suite.metadata, "Trigger time should be recorded in metadata"
    
    def _setup_component_mocks(self, mock_dep_tester, mock_openai_tester, mock_db_tester):
        """Set up mock component testers with realistic return values."""
        # Mock dependency tester
        mock_dep_instance = Mock()
        mock_dep_instance.test_dependencies.return_value = TestResult(
            test_name="dependency_test",
            status=TestStatus.PASS,
            message="All dependencies imported successfully",
            execution_time=0.5
        )
        mock_dep_tester.return_value = mock_dep_instance
        
        # Mock OpenAI client tester
        mock_openai_instance = Mock()
        mock_openai_instance.test_openai_client.return_value = TestResult(
            test_name="openai_client_test",
            status=TestStatus.PASS,
            message="OpenAI client initialized successfully",
            execution_time=0.3
        )
        mock_openai_tester.return_value = mock_openai_instance
        
        # Mock DynamoDB tester
        mock_db_instance = Mock()
        mock_db_instance.test_dynamodb_operations.return_value = TestResult(
            test_name="dynamodb_test",
            status=TestStatus.PASS,
            message="DynamoDB operations completed successfully",
            execution_time=0.7
        )
        mock_db_tester.return_value = mock_db_instance
    
    def _setup_integration_mocks(self, mock_sf_tester, mock_api_tester, mock_iam_tester, mock_int_tester):
        """Set up mock integration testers with realistic return values."""
        # Mock Step Functions tester
        mock_sf_instance = Mock()
        mock_sf_instance.test_state_machine_exists.return_value = TestResult(
            test_name="step_functions_exists_test",
            status=TestStatus.PASS,
            message="State machine exists and is accessible",
            execution_time=0.4
        )
        mock_sf_instance.run_manual_execution.return_value = TestResult(
            test_name="step_functions_execution_test",
            status=TestStatus.PASS,
            message="Manual execution completed successfully",
            execution_time=2.1
        )
        mock_sf_tester.return_value = mock_sf_instance
        
        # Mock API Gateway tester
        mock_api_instance = Mock()
        mock_api_instance.test_api_endpoints.return_value = TestResult(
            test_name="api_gateway_test",
            status=TestStatus.PASS,
            message="API endpoints responding correctly",
            execution_time=1.2
        )
        mock_api_tester.return_value = mock_api_instance
        
        # Mock IAM permission tester
        mock_iam_instance = Mock()
        mock_iam_instance.test_execution_permissions.return_value = TestResult(
            test_name="iam_permissions_test",
            status=TestStatus.PASS,
            message="IAM permissions validated successfully",
            execution_time=0.6
        )
        mock_iam_tester.return_value = mock_iam_instance
        
        # Mock integration tester
        mock_int_instance = Mock()
        mock_int_tester.return_value = mock_int_instance
    
    def _find_suite_by_name(self, test_suites: List[TestSuite], name: str) -> TestSuite:
        """Find a test suite by name in the list of test suites."""
        for suite in test_suites:
            if suite.name == name:
                return suite
        return None


# Additional property tests for specific automation scenarios
class TestAutomationEdgeCases:
    """Property tests for edge cases in test automation."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_config = TestConfiguration(
            artifact_path=self.temp_dir,
            verbose_logging=False
        )
    
    def teardown_method(self):
        """Clean up test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @given(
        empty_test_types=st.just([]),
        invalid_test_types=st.lists(
            st.text(min_size=1).filter(lambda x: x not in ['component', 'integration']),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=20, deadline=None)
    def test_automation_handles_invalid_configurations(self, empty_test_types, invalid_test_types):
        """
        Property: Automation system handles invalid configurations gracefully
        
        For any invalid test type configuration, the automation system should 
        handle the error gracefully without crashing.
        """
        with patch('tests.automation.automation_orchestrator.DependencyTester'), \
             patch('tests.automation.automation_orchestrator.OpenAIClientTester'), \
             patch('tests.automation.automation_orchestrator.DynamoDBTester'), \
             patch('tests.automation.automation_orchestrator.StepFunctionsTester'), \
             patch('tests.automation.automation_orchestrator.APIGatewayTester'), \
             patch('tests.automation.automation_orchestrator.IAMPermissionTester'), \
             patch('tests.automation.automation_orchestrator.CR2AIntegrationTester'):
            
            automation_manager = CR2AAutomationManager(self.test_config)
            
            # Test empty test types
            result = automation_manager.run_tests(empty_test_types, generate_reports=False)
            assert isinstance(result, list), "Should return empty list for empty test types"
            
            # Test invalid test types
            result = automation_manager.run_tests(invalid_test_types, generate_reports=False)
            assert isinstance(result, list), "Should handle invalid test types gracefully"
    
    @given(
        parallel_execution=st.booleans(),
        max_retries=st.integers(min_value=0, max_value=5),
        lambda_timeout=st.integers(min_value=1, max_value=300)
    )
    @settings(max_examples=30, deadline=None)
    def test_automation_configuration_flexibility(self, parallel_execution, max_retries, lambda_timeout):
        """
        Property: Automation system adapts to different configuration parameters
        
        For any valid configuration parameters, the automation system should 
        execute tests according to the specified configuration.
        """
        config = TestConfiguration(
            parallel_execution=parallel_execution,
            max_retries=max_retries,
            lambda_timeout=lambda_timeout,
            artifact_path=self.temp_dir,
            verbose_logging=False
        )
        
        with patch('tests.automation.automation_orchestrator.DependencyTester') as mock_dep_tester, \
             patch('tests.automation.automation_orchestrator.OpenAIClientTester') as mock_openai_tester, \
             patch('tests.automation.automation_orchestrator.DynamoDBTester') as mock_db_tester:
            
            # Set up basic mocks
            mock_dep_instance = Mock()
            mock_dep_instance.test_dependencies.return_value = TestResult(
                test_name="test", status=TestStatus.PASS, message="Success", execution_time=0.1
            )
            mock_dep_tester.return_value = mock_dep_instance
            
            mock_openai_instance = Mock()
            mock_openai_instance.test_openai_client.return_value = TestResult(
                test_name="test", status=TestStatus.PASS, message="Success", execution_time=0.1
            )
            mock_openai_tester.return_value = mock_openai_instance
            
            mock_db_instance = Mock()
            mock_db_instance.test_dynamodb_operations.return_value = TestResult(
                test_name="test", status=TestStatus.PASS, message="Success", execution_time=0.1
            )
            mock_db_tester.return_value = mock_db_instance
            
            # Create orchestrator with custom configuration
            orchestrator = CR2ATestOrchestrator(config)
            
            # Execute component tests
            result = orchestrator.run_component_tests(config)
            
            # Verify execution completed successfully
            assert isinstance(result, TestSuite), "Should return TestSuite for valid configuration"
            assert result.overall_status in [TestStatus.PASS, TestStatus.FAIL, TestStatus.ERROR, TestStatus.SKIP], \
                "Should have valid test status"
