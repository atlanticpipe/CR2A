#!/usr/bin/env python3
"""
Demo script for the CR2A error handling and logging framework.
Shows how to use both error logging and validation systems.
"""

import sys
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.core.error_logging import ErrorLoggingSystem
from tests.core.error_validation import ErrorHandlingValidator
from tests.core.models import TestConfiguration


def main():
    """Demonstrate the error handling framework."""
    print("🔧 CR2A Error Handling & Logging Framework Demo")
    print("=" * 50)
    
    # Setup configuration
    config = TestConfiguration(
        aws_region="us-east-1",
        verbose_logging=False,  # Reduce noise for demo
        save_artifacts=True
    )
    
    try:
        # Initialize systems
        print("📋 Initializing error logging system...")
        logging_system = ErrorLoggingSystem(config)
        
        print("📋 Initializing error validation system...")
        validator = ErrorHandlingValidator(config)
        
        print("✅ Both systems initialized successfully!")
        print()
        
        # Test error logging system
        print("🔍 Testing error logging system...")
        logging_result = logging_system.test_error_logging_system()
        print(f"   Status: {logging_result.status.value}")
        print(f"   Message: {logging_result.message}")
        if logging_result.details:
            print(f"   Details: {logging_result.details}")
        print()
        
        # Test error validation system
        print("🔍 Testing error validation system...")
        validation_result = validator.test_error_validation_system()
        print(f"   Status: {validation_result.status.value}")
        print(f"   Message: {validation_result.message}")
        if validation_result.details:
            print(f"   Details: {validation_result.details}")
        print()
        
        # Show error patterns
        print("📊 Available error patterns:")
        for i, pattern in enumerate(logging_system.error_patterns[:5], 1):
            print(f"   {i}. {pattern.category.value}: {pattern.description}")
        print(f"   ... and {len(logging_system.error_patterns) - 5} more patterns")
        print()
        
        # Show test cases
        print("🧪 Available error test cases:")
        component_tests = [tc for tc in validator.error_test_cases 
                          if tc.test_type.value == 'COMPONENT_ERROR']
        api_tests = [tc for tc in validator.error_test_cases 
                    if tc.test_type.value == 'API_ERROR']
        integration_tests = [tc for tc in validator.error_test_cases 
                           if tc.test_type.value == 'INTEGRATION_ERROR']
        
        print(f"   Component Tests: {len(component_tests)}")
        print(f"   API Tests: {len(api_tests)}")
        print(f"   Integration Tests: {len(integration_tests)}")
        print()
        
        # Example usage
        print("💡 Example usage:")
        print("   # Capture logs from the last hour")
        print("   start_time = datetime.now(timezone.utc) - timedelta(hours=1)")
        print("   log_entries = logging_system.capture_logs(start_time=start_time)")
        print()
        print("   # Analyze errors")
        print("   error_analyses = logging_system.analyze_errors(log_entries)")
        print()
        print("   # Generate report")
        print("   report = logging_system.generate_error_report(error_analyses)")
        print()
        print("   # Validate error handling")
        print("   component_results = validator.validate_component_error_handling()")
        print("   api_results = validator.validate_api_error_handling()")
        print()
        
        print("✅ Demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())