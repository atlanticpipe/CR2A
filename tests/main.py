"""
Main entry point for the CR2A testing framework.
Provides CLI interface and orchestration for all testing phases.
"""

import argparse
import sys
import os
from typing import List, Optional

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.core.config import ConfigurationManager
from tests.core.models import TestConfiguration, TestSuite
from tests.automation.automation_manager import CR2AAutomationManager


def main():
    """Main CLI entry point for the testing framework."""
    parser = argparse.ArgumentParser(
        description="CR2A Testing & Debugging Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m tests.main --component                    # Run component tests only
  python -m tests.main --integration                  # Run integration tests only
  python -m tests.main --full                        # Run complete test suite
  python -m tests.main --config custom_config.json   # Use custom configuration
  python -m tests.main --schedule                    # Start scheduled test execution
  python -m tests.main --historical-report           # Generate historical report
        """
    )
    
    # Test execution options
    parser.add_argument(
        '--component', 
        action='store_true',
        help='Run component isolation tests'
    )
    parser.add_argument(
        '--integration',
        action='store_true', 
        help='Run integration tests'
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='Run complete test suite (all phases)'
    )
    parser.add_argument(
        '--schedule',
        action='store_true',
        help='Start scheduled test execution daemon'
    )
    parser.add_argument(
        '--historical-report',
        action='store_true',
        help='Generate historical test report'
    )
    parser.add_argument(
        '--export-metrics',
        choices=['json', 'prometheus'],
        help='Export test metrics in specified format'
    )
    
    # Configuration options
    parser.add_argument(
        '--config',
        type=str,
        help='Path to test configuration file'
    )
    parser.add_argument(
        '--aws-region',
        type=str,
        default='us-east-1',
        help='AWS region for testing'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Enable parallel test execution'
    )
    
    # Output options
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./test-artifacts',
        help='Directory for test artifacts and reports'
    )
    parser.add_argument(
        '--format',
        choices=['console', 'json', 'html'],
        default='console',
        help='Output format for test results'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    if args.config:
        config = ConfigurationManager.load_from_file(args.config)
    else:
        config = ConfigurationManager.load_from_env()
    
    # Override config with CLI arguments
    if args.aws_region:
        config.aws_region = args.aws_region
    if args.verbose:
        config.verbose_logging = True
    if args.parallel:
        config.parallel_execution = True
    if args.output_dir:
        config.artifact_path = args.output_dir
    
    # Validate AWS credentials
    if not ConfigurationManager.validate_aws_credentials():
        print("ERROR: AWS credentials not found or invalid.")
        print("Please configure AWS credentials using:")
        print("  - AWS CLI: aws configure")
        print("  - Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
        print("  - IAM roles (if running on EC2)")
        sys.exit(1)
    
    # Determine which tests to run
    if not any([args.component, args.integration, args.full, args.schedule, 
                args.historical_report, args.export_metrics]):
        print("ERROR: Must specify at least one action")
        parser.print_help()
        sys.exit(1)
    
    print("CR2A Testing & Debugging Framework")
    print("=" * 50)
    print(f"AWS Region: {config.aws_region}")
    print(f"Output Directory: {config.artifact_path}")
    print(f"Verbose Logging: {config.verbose_logging}")
    print(f"Parallel Execution: {config.parallel_execution}")
    print()
    
    # Create output directory
    os.makedirs(config.artifact_path, exist_ok=True)
    
    # Initialize automation manager
    automation_manager = CR2AAutomationManager(config)
    
    try:
        # Handle different execution modes
        if args.schedule:
            print("Starting scheduled test execution daemon...")
            print("Press Ctrl+C to stop")
            
            # Default schedule configuration (can be made configurable)
            schedule_config = {
                'interval_type': 'hours',
                'interval_value': 1,
                'test_types': ['component', 'integration'],
                'start_time': '09:00'
            }
            
            automation_manager.schedule_tests(schedule_config)
            automation_manager.start_scheduler()
        
        elif args.historical_report:
            print("Generating historical test report...")
            report_path = automation_manager.generate_historical_report(days_back=7)
            if report_path:
                print(f"Historical report generated: {report_path}")
            else:
                print("No historical data found")
        
        elif args.export_metrics:
            print(f"Exporting test metrics in {args.export_metrics} format...")
            metrics_path = automation_manager.export_test_metrics(args.export_metrics)
            if metrics_path:
                print(f"Test metrics exported: {metrics_path}")
            else:
                print("No test data found for metrics export")
        
        else:
            # Determine test types to run
            test_types = []
            if args.component:
                test_types.append('component')
            if args.integration:
                test_types.append('integration')
            if args.full:
                test_types = ['component', 'integration']
            
            print(f"Running tests: {', '.join(test_types)}")
            
            # Run tests
            test_suites = automation_manager.run_tests(test_types, generate_reports=True)
            
            # Display console summary
            console_summary = automation_manager.reporter.generate_console_summary(test_suites)
            print(console_summary)
            
            # Determine exit code based on results
            summary = automation_manager.orchestrator.generate_summary_report(test_suites)
            if summary['overall_status'] in ['PASS', 'SKIP']:
                return 0
            else:
                return 1
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 0
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())