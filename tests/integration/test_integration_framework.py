"""
Test script to verify the integration testing framework functionality.
This can be run to validate the framework setup without requiring AWS resources.
"""

import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from tests.core.models import TestConfiguration
from tests.integration import CR2AIntegrationTester


def test_integration_framework_initialization():
    """Test that the integration framework can be initialized properly."""
    config = TestConfiguration(
        aws_region="us-east-1",
        verbose_logging=True
    )
    
    # Test without API URL (should work but skip API tests)
    tester = CR2AIntegrationTester(config)
    assert tester is not None
    assert tester.step_functions_tester is not None
    assert tester.iam_tester is not None
    assert tester.api_tester is None  # Should be None without API URL
    
    print("✓ Integration framework initialization test passed")
    
    # Test with API URL
    tester_with_api = CR2AIntegrationTester(config, "https://api.example.com")
    assert tester_with_api.api_tester is not None
    
    print("✓ Integration framework with API initialization test passed")


def test_component_tester_initialization():
    """Test that individual component testers can be initialized."""
    config = TestConfiguration(
        aws_region="us-east-1",
        verbose_logging=True
    )
    
    from tests.integration import StepFunctionsTester, IAMPermissionTester, APIGatewayTester
    
    # Test Step Functions tester
    sf_tester = StepFunctionsTester(config)
    assert sf_tester is not None
    assert sf_tester.state_machine_name == "cr2a-contract-analysis"
    
    print("✓ Step Functions tester initialization test passed")
    
    # Test IAM tester
    iam_tester = IAMPermissionTester(config)
    assert iam_tester is not None
    assert iam_tester.api_role_name == "cr2a-api-execution-role"
    
    print("✓ IAM permission tester initialization test passed")
    
    # Test API Gateway tester
    api_tester = APIGatewayTester(config, "https://api.example.com")
    assert api_tester is not None
    assert api_tester.api_base_url == "https://api.example.com"
    
    print("✓ API Gateway tester initialization test passed")


def test_test_input_samples():
    """Test that test input samples are properly formatted."""
    config = TestConfiguration()
    
    from tests.integration import StepFunctionsTester
    sf_tester = StepFunctionsTester(config)
    
    samples = sf_tester.get_test_input_samples()
    assert len(samples) > 0
    
    for sample in samples:
        assert "jobId" in sample
        assert "s3Bucket" in sample
        assert "s3Key" in sample
        assert "analysisType" in sample
    
    print("✓ Test input samples validation test passed")


if __name__ == "__main__":
    print("Running integration framework tests...")
    
    try:
        test_integration_framework_initialization()
        test_component_tester_initialization()
        test_test_input_samples()
        
        print("\n✅ All integration framework tests passed!")
        print("The integration testing framework is ready for use.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        sys.exit(1)