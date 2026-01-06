"""
Basic tests to verify the testing framework setup is working correctly.
"""

import pytest
from tests.core.models import TestResult, TestStatus, TestConfiguration
from tests.core.config import ConfigurationManager


def test_test_result_creation():
    """Test that TestResult objects can be created properly."""
    result = TestResult(
        test_name="test_example",
        status=TestStatus.PASS,
        message="Test passed successfully"
    )
    
    assert result.test_name == "test_example"
    assert result.status == TestStatus.PASS
    assert result.message == "Test passed successfully"
    assert result.timestamp is not None
    assert result.execution_time == 0.0


def test_test_configuration_defaults():
    """Test that TestConfiguration has proper defaults."""
    config = TestConfiguration()
    
    assert config.aws_region == "us-east-1"
    assert config.lambda_timeout == 30
    assert config.max_retries == 3
    assert config.parallel_execution is False
    assert config.verbose_logging is True
    assert config.save_artifacts is True
    assert config.artifact_path == "./test-artifacts"


def test_configuration_manager_load_from_env():
    """Test that ConfigurationManager can load from environment."""
    config = ConfigurationManager.load_from_env()
    
    assert isinstance(config, TestConfiguration)
    assert config.aws_region is not None


def test_cr2a_resource_names():
    """Test that CR2A resource names can be retrieved."""
    resources = ConfigurationManager.get_cr2a_resource_names()
    
    assert 'state_machine_name' in resources
    assert 'lambda_functions' in resources
    assert 'dynamodb_tables' in resources
    assert 's3_buckets' in resources
    
    assert resources['state_machine_name'] == 'cr2a-contract-analysis'
    assert 'api' in resources['lambda_functions']
    assert 'analyzer' in resources['lambda_functions']