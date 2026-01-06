#!/usr/bin/env python3
"""
Configuration management for CR2A testing framework.
Handles loading, saving, and validating configuration files.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class CR2ATestConfig:
    """Configuration for CR2A testing framework."""
    
    # AWS Configuration
    aws_region: str = "us-east-1"
    aws_profile: Optional[str] = None
    
    # API Configuration
    api_base_url: Optional[str] = None
    api_timeout: int = 30
    
    # Test Configuration
    verbose_logging: bool = True
    test_timeout: int = 300
    max_retries: int = 3
    parallel_execution: bool = False
    
    # Component Test Configuration
    component_tests_enabled: bool = True
    dependency_test_packages: List[str] = None
    openai_test_enabled: bool = True
    dynamodb_test_enabled: bool = True
    
    # Integration Test Configuration
    integration_tests_enabled: bool = True
    stepfunctions_test_enabled: bool = True
    api_gateway_test_enabled: bool = True
    
    # Deployment Configuration
    lambda_runtime: str = "python3.12"
    lambda_timeout: int = 60
    lambda_memory_size: int = 256
    create_lambda_layers: bool = True
    
    # Reporting Configuration
    generate_html_reports: bool = True
    generate_json_reports: bool = True
    report_output_dir: str = "test-artifacts"
    open_reports_automatically: bool = False
    
    # CloudWatch Configuration
    log_retention_days: int = 30
    enable_detailed_logging: bool = True
    
    def __post_init__(self):
        """Initialize default values after creation."""
        if self.dependency_test_packages is None:
            self.dependency_test_packages = [
                "boto3", "botocore", "openai", "requests", 
                "json", "os", "logging", "pathlib"
            ]


class ConfigManager:
    """Manages configuration for CR2A testing framework."""
    
    def __init__(self):
        """Initialize configuration manager."""
        self.default_config_paths = [
            "cr2a_test_config.json",
            "config/cr2a_test_config.json",
            os.path.expanduser("~/.cr2a/config.json"),
            "/etc/cr2a/config.json"
        ]
    
    def load_config(self, config_path: Optional[str] = None) -> CR2ATestConfig:
        """Load configuration from file or create default."""
        if config_path:
            # Load from specific path
            if Path(config_path).exists():
                return self._load_from_file(config_path)
            else:
                logger.warning(f"Config file not found: {config_path}")
                return self._create_default_config()
        
        # Search for config in default locations
        for path in self.default_config_paths:
            if Path(path).exists():
                logger.info(f"Loading configuration from {path}")
                return self._load_from_file(path)
        
        # No config found, create default
        logger.info("No configuration file found, using defaults")
        return self._create_default_config()
    
    def _load_from_file(self, config_path: str) -> CR2ATestConfig:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            # Validate and create config object
            return self._create_config_from_dict(config_data)
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file {config_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            raise
    
    def _create_config_from_dict(self, config_data: Dict[str, Any]) -> CR2ATestConfig:
        """Create configuration object from dictionary."""
        # Filter out unknown keys and create config
        valid_keys = set(CR2ATestConfig.__annotations__.keys())
        filtered_data = {k: v for k, v in config_data.items() if k in valid_keys}
        
        return CR2ATestConfig(**filtered_data)
    
    def _create_default_config(self) -> CR2ATestConfig:
        """Create default configuration."""
        return CR2ATestConfig()
    
    def save_config(self, config: CR2ATestConfig, config_path: str) -> bool:
        """Save configuration to file."""
        try:
            # Ensure directory exists
            config_dir = Path(config_path).parent
            config_dir.mkdir(parents=True, exist_ok=True)
            
            # Convert to dictionary and save
            config_dict = asdict(config)
            
            with open(config_path, 'w') as f:
                json.dump(config_dict, f, indent=2, default=str)
            
            logger.info(f"Configuration saved to {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving config to {config_path}: {e}")
            return False
    
    def validate_config(self, config: CR2ATestConfig) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []
        
        # Validate AWS region
        valid_regions = [
            "us-east-1", "us-east-2", "us-west-1", "us-west-2",
            "eu-west-1", "eu-west-2", "eu-central-1", "ap-southeast-1",
            "ap-southeast-2", "ap-northeast-1"
        ]
        
        if config.aws_region not in valid_regions:
            issues.append(f"Invalid AWS region: {config.aws_region}")
        
        # Validate timeouts
        if config.test_timeout <= 0:
            issues.append("Test timeout must be positive")
        
        if config.api_timeout <= 0:
            issues.append("API timeout must be positive")
        
        if config.lambda_timeout <= 0 or config.lambda_timeout > 900:
            issues.append("Lambda timeout must be between 1 and 900 seconds")
        
        # Validate memory size
        valid_memory_sizes = [128, 256, 512, 1024, 2048, 3008]
        if config.lambda_memory_size not in valid_memory_sizes:
            issues.append(f"Invalid Lambda memory size: {config.lambda_memory_size}")
        
        # Validate retry count
        if config.max_retries < 0 or config.max_retries > 10:
            issues.append("Max retries must be between 0 and 10")
        
        # Validate log retention
        valid_retention_days = [1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653]
        if config.log_retention_days not in valid_retention_days:
            issues.append(f"Invalid log retention days: {config.log_retention_days}")
        
        # Validate output directory
        if not config.report_output_dir:
            issues.append("Report output directory cannot be empty")
        
        # Validate API base URL if provided
        if config.api_base_url:
            if not (config.api_base_url.startswith('http://') or config.api_base_url.startswith('https://')):
                issues.append("API base URL must start with http:// or https://")
        
        return issues
    
    def create_sample_config(self, output_path: str = "cr2a_test_config.json") -> bool:
        """Create a sample configuration file."""
        sample_config = CR2ATestConfig(
            aws_region="us-east-1",
            api_base_url="https://your-api-gateway-url.amazonaws.com/prod",
            verbose_logging=True,
            test_timeout=300,
            max_retries=3,
            component_tests_enabled=True,
            integration_tests_enabled=True,
            generate_html_reports=True,
            report_output_dir="test-artifacts"
        )
        
        return self.save_config(sample_config, output_path)
    
    def update_config(self, config: CR2ATestConfig, updates: Dict[str, Any]) -> CR2ATestConfig:
        """Update configuration with new values."""
        config_dict = asdict(config)
        config_dict.update(updates)
        
        return self._create_config_from_dict(config_dict)
    
    def get_environment_overrides(self) -> Dict[str, Any]:
        """Get configuration overrides from environment variables."""
        overrides = {}
        
        # Map environment variables to config keys
        env_mappings = {
            'CR2A_AWS_REGION': 'aws_region',
            'CR2A_AWS_PROFILE': 'aws_profile',
            'CR2A_API_BASE_URL': 'api_base_url',
            'CR2A_API_TIMEOUT': 'api_timeout',
            'CR2A_VERBOSE': 'verbose_logging',
            'CR2A_TEST_TIMEOUT': 'test_timeout',
            'CR2A_MAX_RETRIES': 'max_retries',
            'CR2A_PARALLEL': 'parallel_execution',
            'CR2A_LAMBDA_RUNTIME': 'lambda_runtime',
            'CR2A_LAMBDA_TIMEOUT': 'lambda_timeout',
            'CR2A_LAMBDA_MEMORY': 'lambda_memory_size',
            'CR2A_REPORT_DIR': 'report_output_dir',
            'CR2A_LOG_RETENTION': 'log_retention_days'
        }
        
        for env_var, config_key in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert to appropriate type
                if config_key in ['api_timeout', 'test_timeout', 'max_retries', 'lambda_timeout', 'lambda_memory_size', 'log_retention_days']:
                    try:
                        overrides[config_key] = int(value)
                    except ValueError:
                        logger.warning(f"Invalid integer value for {env_var}: {value}")
                elif config_key in ['verbose_logging', 'parallel_execution']:
                    overrides[config_key] = value.lower() in ['true', '1', 'yes', 'on']
                else:
                    overrides[config_key] = value
        
        return overrides
    
    def load_config_with_overrides(self, config_path: Optional[str] = None) -> CR2ATestConfig:
        """Load configuration with environment variable overrides."""
        # Load base configuration
        config = self.load_config(config_path)
        
        # Apply environment overrides
        env_overrides = self.get_environment_overrides()
        if env_overrides:
            logger.info(f"Applying environment overrides: {list(env_overrides.keys())}")
            config = self.update_config(config, env_overrides)
        
        # Validate final configuration
        issues = self.validate_config(config)
        if issues:
            logger.warning("Configuration validation issues:")
            for issue in issues:
                logger.warning(f"  - {issue}")
        
        return config
    
    def print_config(self, config: CR2ATestConfig):
        """Print configuration in a readable format."""
        print("=== CR2A Test Configuration ===")
        print()
        
        print("AWS Configuration:")
        print(f"  Region: {config.aws_region}")
        print(f"  Profile: {config.aws_profile or 'default'}")
        print()
        
        print("API Configuration:")
        print(f"  Base URL: {config.api_base_url or 'not configured'}")
        print(f"  Timeout: {config.api_timeout}s")
        print()
        
        print("Test Configuration:")
        print(f"  Verbose Logging: {config.verbose_logging}")
        print(f"  Test Timeout: {config.test_timeout}s")
        print(f"  Max Retries: {config.max_retries}")
        print(f"  Parallel Execution: {config.parallel_execution}")
        print()
        
        print("Component Tests:")
        print(f"  Enabled: {config.component_tests_enabled}")
        print(f"  OpenAI Test: {config.openai_test_enabled}")
        print(f"  DynamoDB Test: {config.dynamodb_test_enabled}")
        print(f"  Test Packages: {len(config.dependency_test_packages)} packages")
        print()
        
        print("Integration Tests:")
        print(f"  Enabled: {config.integration_tests_enabled}")
        print(f"  Step Functions: {config.stepfunctions_test_enabled}")
        print(f"  API Gateway: {config.api_gateway_test_enabled}")
        print()
        
        print("Deployment Configuration:")
        print(f"  Lambda Runtime: {config.lambda_runtime}")
        print(f"  Lambda Timeout: {config.lambda_timeout}s")
        print(f"  Lambda Memory: {config.lambda_memory_size}MB")
        print(f"  Create Layers: {config.create_lambda_layers}")
        print()
        
        print("Reporting Configuration:")
        print(f"  HTML Reports: {config.generate_html_reports}")
        print(f"  JSON Reports: {config.generate_json_reports}")
        print(f"  Output Directory: {config.report_output_dir}")
        print(f"  Auto-open Reports: {config.open_reports_automatically}")


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="CR2A Test Configuration Manager")
    parser.add_argument("action", choices=["create", "validate", "show", "update"], 
                       help="Action to perform")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--output", help="Output file path (for create action)")
    parser.add_argument("--key", help="Configuration key to update")
    parser.add_argument("--value", help="Configuration value to set")
    
    args = parser.parse_args()
    
    manager = ConfigManager()
    
    if args.action == "create":
        output_path = args.output or "cr2a_test_config.json"
        if manager.create_sample_config(output_path):
            print(f"✅ Sample configuration created: {output_path}")
        else:
            print(f"❌ Failed to create configuration file")
    
    elif args.action == "validate":
        config = manager.load_config_with_overrides(args.config)
        issues = manager.validate_config(config)
        
        if issues:
            print("❌ Configuration validation failed:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("✅ Configuration is valid")
    
    elif args.action == "show":
        config = manager.load_config_with_overrides(args.config)
        manager.print_config(config)
    
    elif args.action == "update":
        if not args.key or not args.value:
            print("❌ --key and --value required for update action")
            return
        
        config = manager.load_config_with_overrides(args.config)
        
        # Convert value to appropriate type
        value = args.value
        if args.key in ['api_timeout', 'test_timeout', 'max_retries', 'lambda_timeout', 'lambda_memory_size', 'log_retention_days']:
            try:
                value = int(value)
            except ValueError:
                print(f"❌ Invalid integer value: {value}")
                return
        elif args.key in ['verbose_logging', 'parallel_execution', 'component_tests_enabled', 'integration_tests_enabled']:
            value = value.lower() in ['true', '1', 'yes', 'on']
        
        # Update configuration
        updates = {args.key: value}
        updated_config = manager.update_config(config, updates)
        
        # Save updated configuration
        config_path = args.config or "cr2a_test_config.json"
        if manager.save_config(updated_config, config_path):
            print(f"✅ Configuration updated: {args.key} = {value}")
        else:
            print(f"❌ Failed to save configuration")


if __name__ == "__main__":
    main()