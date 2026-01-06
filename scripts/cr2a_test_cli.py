#!/usr/bin/env python3
"""
Main CLI interface for CR2A testing and debugging framework.
Provides command-line interface for running different test phases and managing configuration.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import testing framework components
try:
    from tests.automation.automation_manager import CR2AAutomationManager
    from tests.automation.automation_orchestrator import CR2ATestOrchestrator
    from tests.automation.automation_reporter import CR2ATestReporter
    from tests.core.config import TestConfiguration
    from tests.core.models import TestStatus
    
    # Import deployment and configuration scripts
    from scripts.deploy_lambda_tests import LambdaDeploymentManager
    from scripts.configure_aws_resources import AWSResourceConfigurator
    from scripts.validate_aws_setup import AWSSetupValidator
    from scripts.manage_lambda_layers import LambdaLayerManager
    
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure you're running from the project root directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cr2a_test_cli.log')
    ]
)
logger = logging.getLogger(__name__)


class CR2ATestCLI:
    """Main CLI interface for CR2A testing framework."""
    
    def __init__(self):
        """Initialize CLI interface."""
        self.config = None
        self.automation_manager = None
        self.deployment_manager = None
        self.resource_configurator = None
        self.setup_validator = None
        self.layer_manager = None
    
    def _load_configuration(self, config_file: Optional[str] = None, aws_region: str = "us-east-1") -> TestConfiguration:
        """Load test configuration."""
        if config_file and Path(config_file).exists():
            logger.info(f"Loading configuration from {config_file}")
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            return TestConfiguration(
                aws_region=config_data.get('aws_region', aws_region),
                api_base_url=config_data.get('api_base_url'),
                verbose_logging=config_data.get('verbose_logging', True),
                test_timeout=config_data.get('test_timeout', 300),
                max_retries=config_data.get('max_retries', 3)
            )
        else:
            logger.info("Using default configuration")
            return TestConfiguration(
                aws_region=aws_region,
                verbose_logging=True
            )
    
    def _initialize_managers(self, config: TestConfiguration):
        """Initialize all manager instances."""
        self.config = config
        self.automation_manager = CR2AAutomationManager(config)
        self.deployment_manager = LambdaDeploymentManager(config.aws_region)
        self.resource_configurator = AWSResourceConfigurator(config.aws_region)
        self.setup_validator = AWSSetupValidator(config.aws_region)
        self.layer_manager = LambdaLayerManager(config.aws_region)
    
    def run_component_tests(self, args) -> int:
        """Run component isolation tests."""
        logger.info("Starting component tests...")
        
        try:
            results = self.automation_manager.run_component_tests()
            
            # Display results
            print("\n=== COMPONENT TEST RESULTS ===")
            for component, report in results.items():
                status_color = self._get_status_color(report.overall_status)
                print(f"{component}: {status_color}{report.overall_status.value}{self._reset_color()}")
                
                if args.verbose:
                    all_tests = report.dependency_tests + report.client_tests + report.database_tests
                    for test in all_tests:
                        test_color = self._get_status_color(test.status)
                        print(f"  {test.test_name}: {test_color}{test.status.value}{self._reset_color()} - {test.message}")
                
                if report.recommendations:
                    print("  Recommendations:")
                    for rec in report.recommendations:
                        print(f"    - {rec}")
            
            # Return appropriate exit code
            failed_components = [name for name, report in results.items() 
                               if report.overall_status == TestStatus.FAIL]
            return 1 if failed_components else 0
            
        except Exception as e:
            logger.error(f"Component tests failed: {e}")
            print(f"Error running component tests: {e}")
            return 1
    
    def run_integration_tests(self, args) -> int:
        """Run integration tests."""
        logger.info("Starting integration tests...")
        
        try:
            results = self.automation_manager.run_integration_tests()
            
            # Display results
            print("\n=== INTEGRATION TEST RESULTS ===")
            status_color = self._get_status_color(results.overall_status)
            print(f"Overall Status: {status_color}{results.overall_status.value}{self._reset_color()}")
            
            if args.verbose:
                all_tests = (results.state_machine_tests + results.api_endpoint_tests + 
                           results.workflow_tests + results.permission_tests)
                
                for test in all_tests:
                    test_color = self._get_status_color(test.status)
                    print(f"  {test.test_name}: {test_color}{test.status.value}{self._reset_color()} - {test.message}")
            
            if results.identified_issues:
                print("\nIdentified Issues:")
                for issue in results.identified_issues:
                    severity_color = self._get_severity_color(issue.severity)
                    print(f"  {severity_color}{issue.severity.value}{self._reset_color()} - {issue.component}: {issue.description}")
                    if args.verbose and issue.resolution_steps:
                        print("    Resolution steps:")
                        for step in issue.resolution_steps:
                            print(f"      - {step}")
            
            return 1 if results.overall_status == TestStatus.FAIL else 0
            
        except Exception as e:
            logger.error(f"Integration tests failed: {e}")
            print(f"Error running integration tests: {e}")
            return 1
    
    def run_all_tests(self, args) -> int:
        """Run all test phases in sequence."""
        logger.info("Starting comprehensive test run...")
        
        print("=== CR2A COMPREHENSIVE TEST EXECUTION ===")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Region: {self.config.aws_region}")
        print()
        
        # Phase 1: Component Tests
        print("Phase 1: Component Tests")
        print("-" * 30)
        component_result = self.run_component_tests(args)
        
        if component_result != 0 and not args.continue_on_failure:
            print("\nComponent tests failed. Stopping execution.")
            print("Use --continue-on-failure to proceed despite failures.")
            return component_result
        
        print()
        
        # Phase 2: Integration Tests
        print("Phase 2: Integration Tests")
        print("-" * 30)
        integration_result = self.run_integration_tests(args)
        
        if integration_result != 0 and not args.continue_on_failure:
            print("\nIntegration tests failed. Stopping execution.")
            return integration_result
        
        print()
        
        # Phase 3: Generate comprehensive report
        if args.generate_report:
            print("Phase 3: Generating Comprehensive Report")
            print("-" * 40)
            self.generate_test_report(args)
        
        # Determine overall result
        overall_result = max(component_result, integration_result)
        
        print("\n=== EXECUTION SUMMARY ===")
        if overall_result == 0:
            print("✅ All tests passed successfully")
        else:
            print("❌ Some tests failed")
        
        return overall_result
    
    def deploy_test_functions(self, args) -> int:
        """Deploy Lambda test functions."""
        logger.info("Deploying Lambda test functions...")
        
        try:
            # Create layer if requested
            layer_arn = None
            if not args.no_layer:
                print("Creating Lambda layer...")
                layer_arn = self.deployment_manager.create_lambda_layer("cr2a-test-dependencies")
                if layer_arn:
                    print(f"✅ Layer created: {layer_arn}")
                else:
                    print("⚠️  Layer creation failed, deploying without layer")
            
            # Deploy functions
            if args.function:
                print(f"Deploying function: {args.function}")
                success = self.deployment_manager.deploy_test_function(args.function, layer_arn)
                if success:
                    print(f"✅ Function {args.function} deployed successfully")
                    return 0
                else:
                    print(f"❌ Function {args.function} deployment failed")
                    return 1
            else:
                print("Deploying all test functions...")
                results = self.deployment_manager.deploy_all_test_functions(create_layer=not args.no_layer)
                
                print("\nDeployment Results:")
                failed_functions = []
                for function_name, success in results.items():
                    status = "✅ SUCCESS" if success else "❌ FAILED"
                    print(f"  {function_name}: {status}")
                    if not success:
                        failed_functions.append(function_name)
                
                return 1 if failed_functions else 0
        
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            print(f"Error during deployment: {e}")
            return 1
    
    def setup_aws_resources(self, args) -> int:
        """Set up AWS resources."""
        logger.info("Setting up AWS resources...")
        
        try:
            if args.resource == "all":
                print("Setting up all AWS resources...")
                results = self.resource_configurator.setup_all_resources()
                
                print("\nSetup Results:")
                print("IAM Roles:")
                for role_name, role_arn in results["iam_roles"].items():
                    status = "✅ SUCCESS" if role_arn else "❌ FAILED"
                    print(f"  {role_name}: {status}")
                
                print("Log Groups:")
                for log_group, success in results["log_groups"].items():
                    status = "✅ SUCCESS" if success else "❌ FAILED"
                    print(f"  {log_group}: {status}")
                
                api_status = "✅ SUCCESS" if results["api_gateway_logging"] else "❌ FAILED"
                print(f"API Gateway Logging: {api_status}")
                
                # Check if any failures occurred
                failed_roles = [name for name, arn in results["iam_roles"].items() if not arn]
                failed_logs = [name for name, success in results["log_groups"].items() if not success]
                
                return 1 if (failed_roles or failed_logs or not results["api_gateway_logging"]) else 0
            
            elif args.resource == "iam":
                print("Setting up IAM roles...")
                for role_name in self.resource_configurator.iam_roles.keys():
                    role_arn = self.resource_configurator.create_iam_role(role_name)
                    status = "✅ SUCCESS" if role_arn else "❌ FAILED"
                    print(f"  {role_name}: {status}")
                return 0
            
            elif args.resource == "logs":
                print("Setting up CloudWatch log groups...")
                results = self.resource_configurator.create_cloudwatch_log_groups()
                
                failed_logs = []
                for log_group, success in results.items():
                    status = "✅ SUCCESS" if success else "❌ FAILED"
                    print(f"  {log_group}: {status}")
                    if not success:
                        failed_logs.append(log_group)
                
                return 1 if failed_logs else 0
            
        except Exception as e:
            logger.error(f"AWS resource setup failed: {e}")
            print(f"Error setting up AWS resources: {e}")
            return 1
    
    def validate_setup(self, args) -> int:
        """Validate AWS setup."""
        logger.info("Validating AWS setup...")
        
        try:
            if args.component == "all":
                results = self.setup_validator.run_comprehensive_validation()
                
                print(f"=== AWS SETUP VALIDATION ===")
                print(f"Overall Status: {self._get_status_color_text(results['overall_status'])}")
                print(f"Region: {results['region']}")
                print(f"Timestamp: {results['timestamp']}")
                print()
                
                # Display component results
                components = ["iam_roles", "cloudwatch_logs", "lambda_functions", "step_functions", "api_gateway"]
                for component in components:
                    if component in results:
                        data = results[component]
                        status = data.get("overall_status", "UNKNOWN")
                        print(f"{component.replace('_', ' ').title()}: {self._get_status_color_text(status)}")
                        
                        if args.verbose:
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
                if results.get("recommendations"):
                    print("Recommendations:")
                    for rec in results["recommendations"]:
                        print(f"  - {rec}")
                
                return 0 if results["overall_status"] in ["HEALTHY", "PARTIAL"] else 1
            
            else:
                # Validate specific component
                if args.component == "iam":
                    results = {"iam_roles": self.setup_validator.validate_iam_roles()}
                elif args.component == "logs":
                    results = {"cloudwatch_logs": self.setup_validator.validate_cloudwatch_logs()}
                elif args.component == "lambda":
                    results = {"lambda_functions": self.setup_validator.validate_lambda_functions()}
                elif args.component == "stepfunctions":
                    results = {"step_functions": self.setup_validator.validate_step_functions()}
                elif args.component == "apigateway":
                    results = {"api_gateway": self.setup_validator.validate_api_gateway()}
                
                # Display results
                for component, data in results.items():
                    status = data.get("overall_status", "UNKNOWN")
                    print(f"{component.replace('_', ' ').title()}: {self._get_status_color_text(status)}")
                
                return 0
        
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            print(f"Error during validation: {e}")
            return 1
    
    def generate_test_report(self, args) -> int:
        """Generate comprehensive test report."""
        logger.info("Generating test report...")
        
        try:
            # Create test reporter
            reporter = CR2ATestReporter(self.config.artifact_path)
            
            # Generate report
            report_path = reporter.generate_comprehensive_report()
            
            if report_path:
                print(f"✅ Test report generated: {report_path}")
                
                if args.open_report:
                    import webbrowser
                    webbrowser.open(f"file://{report_path}")
                
                return 0
            else:
                print("❌ Failed to generate test report")
                return 1
        
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            print(f"Error generating report: {e}")
            return 1
    
    def manage_layers(self, args) -> int:
        """Manage Lambda layers."""
        logger.info(f"Managing Lambda layers: {args.layer_action}")
        
        try:
            if args.layer_action == "create":
                if args.layer:
                    layer_arn = self.layer_manager.create_or_update_layer(args.layer)
                    if layer_arn:
                        print(f"✅ Layer created/updated: {layer_arn}")
                        return 0
                    else:
                        print(f"❌ Failed to create/update layer: {args.layer}")
                        return 1
                else:
                    results = self.layer_manager.create_all_layers()
                    
                    print("Layer Creation Results:")
                    failed_layers = []
                    for layer_name, layer_arn in results.items():
                        if layer_arn:
                            print(f"  ✅ {layer_name}: {layer_arn}")
                        else:
                            print(f"  ❌ {layer_name}: FAILED")
                            failed_layers.append(layer_name)
                    
                    return 1 if failed_layers else 0
            
            elif args.layer_action == "list":
                if args.layer:
                    versions = self.layer_manager.list_layer_versions(args.layer)
                    print(f"Versions for layer {args.layer}:")
                    for version in versions:
                        print(f"  Version {version['Version']}: {version['LayerVersionArn']}")
                else:
                    print("Available layers:")
                    for layer_name in self.layer_manager.layer_configs.keys():
                        versions = self.layer_manager.list_layer_versions(layer_name)
                        print(f"  {layer_name}: {len(versions)} versions")
                
                return 0
            
            elif args.layer_action == "cleanup":
                if args.layer:
                    deleted = self.layer_manager.cleanup_old_versions(args.layer, args.keep_versions)
                    print(f"✅ Cleaned up {deleted} old versions of {args.layer}")
                else:
                    total_deleted = 0
                    for layer_name in self.layer_manager.layer_configs.keys():
                        deleted = self.layer_manager.cleanup_old_versions(layer_name, args.keep_versions)
                        total_deleted += deleted
                    print(f"✅ Cleaned up {total_deleted} old layer versions total")
                
                return 0
        
        except Exception as e:
            logger.error(f"Layer management failed: {e}")
            print(f"Error managing layers: {e}")
            return 1
    
    def _get_status_color(self, status: TestStatus) -> str:
        """Get ANSI color code for test status."""
        if status == TestStatus.PASS:
            return '\033[92m'  # Green
        elif status == TestStatus.FAIL:
            return '\033[91m'  # Red
        elif status == TestStatus.ERROR:
            return '\033[95m'  # Magenta
        elif status == TestStatus.SKIP:
            return '\033[93m'  # Yellow
        else:
            return '\033[94m'  # Blue
    
    def _get_status_color_text(self, status: str) -> str:
        """Get colored status text."""
        if status == "HEALTHY":
            return f'\033[92m{status}\033[0m'  # Green
        elif status in ["FAILED", "ERROR"]:
            return f'\033[91m{status}\033[0m'  # Red
        elif status == "PARTIAL":
            return f'\033[93m{status}\033[0m'  # Yellow
        else:
            return f'\033[94m{status}\033[0m'  # Blue
    
    def _get_severity_color(self, severity) -> str:
        """Get ANSI color code for issue severity."""
        if hasattr(severity, 'value'):
            severity_val = severity.value
        else:
            severity_val = str(severity)
        
        if severity_val == "CRITICAL":
            return '\033[91m'  # Red
        elif severity_val == "HIGH":
            return '\033[95m'  # Magenta
        elif severity_val == "MEDIUM":
            return '\033[93m'  # Yellow
        else:
            return '\033[94m'  # Blue
    
    def _reset_color(self) -> str:
        """Get ANSI reset code."""
        return '\033[0m'


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="CR2A Testing and Debugging Framework CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python cr2a_test_cli.py test all --verbose
  
  # Run only component tests
  python cr2a_test_cli.py test component
  
  # Deploy Lambda functions
  python cr2a_test_cli.py deploy lambda --no-layer
  
  # Set up AWS resources
  python cr2a_test_cli.py setup aws --resource all
  
  # Validate setup
  python cr2a_test_cli.py validate --component all --verbose
  
  # Generate test report
  python cr2a_test_cli.py report --open
        """
    )
    
    # Global options
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                       default="INFO", help="Logging level")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument("phase", choices=["component", "integration", "all"], 
                           help="Test phase to run")
    test_parser.add_argument("--continue-on-failure", action="store_true",
                           help="Continue execution even if tests fail")
    test_parser.add_argument("--generate-report", action="store_true",
                           help="Generate comprehensive report after tests")
    
    # Deploy command
    deploy_parser = subparsers.add_parser("deploy", help="Deploy resources")
    deploy_parser.add_argument("resource", choices=["lambda", "layers"], 
                             help="Resource type to deploy")
    deploy_parser.add_argument("--function", help="Specific Lambda function to deploy")
    deploy_parser.add_argument("--no-layer", action="store_true", 
                             help="Skip creating Lambda layer")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Set up AWS resources")
    setup_parser.add_argument("target", choices=["aws"], help="Setup target")
    setup_parser.add_argument("--resource", choices=["iam", "logs", "stepfunctions", "apigateway", "all"],
                            default="all", help="Resource type to set up")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate setup")
    validate_parser.add_argument("--component", choices=["iam", "logs", "lambda", "stepfunctions", "apigateway", "all"],
                               default="all", help="Component to validate")
    validate_parser.add_argument("--output", choices=["text", "json"], default="text", help="Output format")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate test report")
    report_parser.add_argument("--open", action="store_true", help="Open report in browser")
    
    # Layer management command
    layer_parser = subparsers.add_parser("layers", help="Manage Lambda layers")
    layer_parser.add_argument("layer_action", choices=["create", "list", "cleanup"], 
                            help="Layer management action")
    layer_parser.add_argument("--layer", help="Specific layer name")
    layer_parser.add_argument("--keep-versions", type=int, default=3, 
                            help="Number of versions to keep during cleanup")
    
    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Initialize CLI
    cli = CR2ATestCLI()
    
    try:
        # Load configuration
        config = cli._load_configuration(args.config, args.region)
        cli._initialize_managers(config)
        
        # Execute command
        if args.command == "test":
            if args.phase == "component":
                return cli.run_component_tests(args)
            elif args.phase == "integration":
                return cli.run_integration_tests(args)
            elif args.phase == "all":
                return cli.run_all_tests(args)
        
        elif args.command == "deploy":
            if args.resource == "lambda":
                return cli.deploy_test_functions(args)
            elif args.resource == "layers":
                return cli.manage_layers(args)
        
        elif args.command == "setup":
            if args.target == "aws":
                return cli.setup_aws_resources(args)
        
        elif args.command == "validate":
            return cli.validate_setup(args)
        
        elif args.command == "report":
            return cli.generate_test_report(args)
        
        elif args.command == "layers":
            return cli.manage_layers(args)
        
        else:
            parser.print_help()
            return 1
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())