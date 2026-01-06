"""
Component tester for Lambda layer dependencies.
Tests package imports and version verification for CR2A Lambda functions.
"""

import importlib
import importlib.util
import logging
import os
import sys
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from tests.core.base import BaseTestFramework
from tests.core.interfaces import ComponentTester
from tests.core.models import TestResult, TestStatus, ComponentTestReport, TestConfiguration


class DependencyTester(BaseTestFramework, ComponentTester):
    """Tests Lambda layer dependencies and package imports."""
    
    def __init__(self, config: TestConfiguration):
        super().__init__(config)
        self.required_packages = self._load_required_packages()
        self.test_results: List[TestResult] = []
    
    def _load_required_packages(self) -> Dict[str, Optional[str]]:
        """Load required packages from requirements files."""
        packages = {}
        
        # Load core requirements
        try:
            requirements_path = Path("requirements-core.txt")
            if requirements_path.exists():
                with open(requirements_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '==' in line:
                                name, version = line.split('==', 1)
                                packages[name.strip()] = version.strip()
                            else:
                                packages[line.strip()] = None
        except Exception as e:
            self.logger.warning(f"Could not load requirements-core.txt: {e}")
        
        # Add critical packages that must be available
        critical_packages = {
            'boto3': None,
            'botocore': None,
            'openai': None,
            'requests': None,
            'json': None,  # Built-in module
            'os': None,    # Built-in module
            'logging': None,  # Built-in module
        }
        
        for pkg, version in critical_packages.items():
            if pkg not in packages:
                packages[pkg] = version
        
        return packages
    
    def test_dependencies(self) -> TestResult:
        """Test Lambda layer dependencies and package imports."""
        def _test_all_dependencies():
            failed_imports = []
            version_mismatches = []
            successful_imports = []
            
            for package_name, expected_version in self.required_packages.items():
                try:
                    # Test import
                    if package_name in sys.builtin_module_names:
                        # Built-in module
                        module = importlib.import_module(package_name)
                        successful_imports.append(package_name)
                    else:
                        # External package
                        spec = importlib.util.find_spec(package_name)
                        if spec is None:
                            failed_imports.append(f"{package_name}: Module not found")
                            continue
                        
                        module = importlib.import_module(package_name)
                        successful_imports.append(package_name)
                        
                        # Check version if specified
                        if expected_version:
                            actual_version = getattr(module, '__version__', None)
                            if actual_version and actual_version != expected_version:
                                version_mismatches.append(
                                    f"{package_name}: expected {expected_version}, got {actual_version}"
                                )
                
                except ImportError as e:
                    failed_imports.append(f"{package_name}: {str(e)}")
                except Exception as e:
                    failed_imports.append(f"{package_name}: Unexpected error - {str(e)}")
            
            # Determine test result
            if failed_imports:
                return TestResult(
                    test_name="dependency_imports",
                    status=TestStatus.FAIL,
                    message=f"Failed to import {len(failed_imports)} packages",
                    details={
                        "failed_imports": failed_imports,
                        "version_mismatches": version_mismatches,
                        "successful_imports": successful_imports,
                        "total_packages": len(self.required_packages)
                    }
                )
            elif version_mismatches:
                return TestResult(
                    test_name="dependency_imports",
                    status=TestStatus.FAIL,
                    message=f"Version mismatches found for {len(version_mismatches)} packages",
                    details={
                        "failed_imports": failed_imports,
                        "version_mismatches": version_mismatches,
                        "successful_imports": successful_imports,
                        "total_packages": len(self.required_packages)
                    }
                )
            else:
                return TestResult(
                    test_name="dependency_imports",
                    status=TestStatus.PASS,
                    message=f"Successfully imported all {len(successful_imports)} required packages",
                    details={
                        "failed_imports": failed_imports,
                        "version_mismatches": version_mismatches,
                        "successful_imports": successful_imports,
                        "total_packages": len(self.required_packages)
                    }
                )
        
        return self.execute_test_with_timing("test_dependencies", _test_all_dependencies)
    
    def test_openai_client(self) -> TestResult:
        """Test OpenAI client initialization with various API key configurations."""
        # This is implemented in the OpenAI client tester
        return TestResult(
            test_name="test_openai_client",
            status=TestStatus.SKIP,
            message="OpenAI client testing handled by dedicated OpenAI tester"
        )
    
    def test_dynamodb_operations(self) -> TestResult:
        """Test DynamoDB operations and reserved keyword handling."""
        # This is implemented in the DynamoDB operations tester
        return TestResult(
            test_name="test_dynamodb_operations",
            status=TestStatus.SKIP,
            message="DynamoDB operations testing handled by dedicated DynamoDB tester"
        )
    
    def test_lambda_layer_structure(self) -> TestResult:
        """Test Lambda layer directory structure and permissions."""
        def _test_layer_structure():
            issues = []
            
            # Check if we're in a Lambda-like environment
            lambda_task_root = os.environ.get('LAMBDA_TASK_ROOT')
            lambda_runtime_dir = os.environ.get('LAMBDA_RUNTIME_DIR')
            
            if lambda_task_root:
                # We're in a Lambda environment
                layer_paths = [
                    '/opt/python',
                    '/opt/python/lib/python3.12/site-packages',
                    '/var/runtime'
                ]
                
                for path in layer_paths:
                    path_obj = Path(path)
                    if not path_obj.exists():
                        issues.append(f"Lambda layer path does not exist: {path}")
                    elif not path_obj.is_dir():
                        issues.append(f"Lambda layer path is not a directory: {path}")
            else:
                # Local development environment - check local structure
                local_paths = [
                    'python/lib/python3.12/site-packages',
                    '.venv/lib/python3.12/site-packages'
                ]
                
                found_valid_path = False
                for path in local_paths:
                    path_obj = Path(path)
                    if path_obj.exists() and path_obj.is_dir():
                        found_valid_path = True
                        break
                
                if not found_valid_path:
                    issues.append("No valid Python package directory found in local environment")
            
            if issues:
                return TestResult(
                    test_name="lambda_layer_structure",
                    status=TestStatus.FAIL,
                    message=f"Lambda layer structure issues: {len(issues)} problems found",
                    details={"issues": issues}
                )
            else:
                return TestResult(
                    test_name="lambda_layer_structure",
                    status=TestStatus.PASS,
                    message="Lambda layer structure is valid",
                    details={"lambda_task_root": lambda_task_root, "lambda_runtime_dir": lambda_runtime_dir}
                )
        
        return self.execute_test_with_timing("test_lambda_layer_structure", _test_layer_structure)
    
    def test_critical_imports(self) -> TestResult:
        """Test imports of critical packages used by CR2A Lambda functions."""
        def _test_critical_imports():
            critical_modules = [
                'json',
                'os',
                'logging',
                'boto3',
                'botocore',
                'requests'
            ]
            
            failed_imports = []
            successful_imports = []
            
            for module_name in critical_modules:
                try:
                    importlib.import_module(module_name)
                    successful_imports.append(module_name)
                except ImportError as e:
                    failed_imports.append(f"{module_name}: {str(e)}")
                except Exception as e:
                    failed_imports.append(f"{module_name}: Unexpected error - {str(e)}")
            
            if failed_imports:
                return TestResult(
                    test_name="critical_imports",
                    status=TestStatus.FAIL,
                    message=f"Failed to import {len(failed_imports)} critical modules",
                    details={
                        "failed_imports": failed_imports,
                        "successful_imports": successful_imports
                    }
                )
            else:
                return TestResult(
                    test_name="critical_imports",
                    status=TestStatus.PASS,
                    message=f"Successfully imported all {len(successful_imports)} critical modules",
                    details={
                        "failed_imports": failed_imports,
                        "successful_imports": successful_imports
                    }
                )
        
        return self.execute_test_with_timing("test_critical_imports", _test_critical_imports)
    
    def generate_test_report(self) -> ComponentTestReport:
        """Generate comprehensive component test report."""
        # Run all dependency tests
        dependency_test = self.test_dependencies()
        layer_structure_test = self.test_lambda_layer_structure()
        critical_imports_test = self.test_critical_imports()
        
        all_tests = [dependency_test, layer_structure_test, critical_imports_test]
        
        # Determine overall status
        failed_tests = [t for t in all_tests if t.status == TestStatus.FAIL]
        error_tests = [t for t in all_tests if t.status == TestStatus.ERROR]
        
        if error_tests:
            overall_status = TestStatus.ERROR
        elif failed_tests:
            overall_status = TestStatus.FAIL
        else:
            overall_status = TestStatus.PASS
        
        # Generate recommendations
        recommendations = []
        if failed_tests:
            recommendations.append("Fix failed dependency imports before deploying Lambda functions")
        if any("version mismatch" in t.message.lower() for t in failed_tests):
            recommendations.append("Update Lambda layer with correct package versions")
        if any("layer structure" in t.test_name for t in failed_tests):
            recommendations.append("Verify Lambda layer directory structure and permissions")
        
        return ComponentTestReport(
            lambda_function="dependency_layer",
            dependency_tests=all_tests,
            client_tests=[],  # Handled by other testers
            database_tests=[],  # Handled by other testers
            overall_status=overall_status,
            recommendations=recommendations
        )


def create_lambda_test_function() -> str:
    """
    Create a Lambda function that can be deployed to test dependencies in the actual Lambda environment.
    Returns the function code as a string.
    """
    return '''
import json
import importlib
import sys
import os
from typing import Dict, List, Any

def lambda_handler(event, context):
    """
    Lambda function to test package dependencies in the actual Lambda environment.
    """
    required_packages = event.get('required_packages', [
        'boto3', 'botocore', 'openai', 'requests', 'json', 'os', 'logging'
    ])
    
    results = {
        'successful_imports': [],
        'failed_imports': [],
        'environment_info': {
            'python_version': sys.version,
            'lambda_task_root': os.environ.get('LAMBDA_TASK_ROOT'),
            'lambda_runtime_dir': os.environ.get('LAMBDA_RUNTIME_DIR'),
            'python_path': sys.path
        }
    }
    
    for package_name in required_packages:
        try:
            if package_name in sys.builtin_module_names:
                module = importlib.import_module(package_name)
                results['successful_imports'].append({
                    'package': package_name,
                    'version': getattr(module, '__version__', 'built-in'),
                    'location': getattr(module, '__file__', 'built-in')
                })
            else:
                module = importlib.import_module(package_name)
                results['successful_imports'].append({
                    'package': package_name,
                    'version': getattr(module, '__version__', 'unknown'),
                    'location': getattr(module, '__file__', 'unknown')
                })
        except ImportError as e:
            results['failed_imports'].append({
                'package': package_name,
                'error': str(e),
                'error_type': 'ImportError'
            })
        except Exception as e:
            results['failed_imports'].append({
                'package': package_name,
                'error': str(e),
                'error_type': type(e).__name__
            })
    
    return {
        'statusCode': 200,
        'body': json.dumps(results, indent=2)
    }
'''


if __name__ == "__main__":
    # Example usage for local testing
    import os
    
    config = TestConfiguration(
        aws_region="us-east-1",
        verbose_logging=True
    )
    
    tester = DependencyTester(config)
    report = tester.generate_test_report()
    
    print(f"Dependency Test Report - Overall Status: {report.overall_status.value}")
    print(f"Tests Run: {len(report.dependency_tests)}")
    
    for test in report.dependency_tests:
        print(f"  {test.test_name}: {test.status.value} - {test.message}")
    
    if report.recommendations:
        print("\nRecommendations:")
        for rec in report.recommendations:
            print(f"  - {rec}")