# CR2A Testing Framework Scripts

This directory contains deployment and configuration scripts for the CR2A testing and debugging framework.

## Scripts Overview

### Main CLI Interface
- **`cr2a_test_cli.py`** - Main command-line interface for the testing framework
- **`cr2a-test`** - Unix/Linux shell wrapper script
- **`cr2a-test.bat`** - Windows batch wrapper script

### Deployment Scripts
- **`deploy_lambda_tests.py`** - Deploy Lambda test functions to AWS
- **`manage_lambda_layers.py`** - Manage Lambda layers with dependencies

### Configuration Scripts
- **`configure_aws_resources.py`** - Set up IAM roles, policies, and CloudWatch log groups
- **`validate_aws_setup.py`** - Validate AWS resource configuration
- **`config_manager.py`** - Manage test framework configuration files

## Quick Start

### 1. Initial Setup
```bash
# Create sample configuration
./scripts/cr2a-test config create

# Set up all AWS resources and deploy functions
./scripts/cr2a-test quick-setup
```

### 2. Run Tests
```bash
# Run all tests with verbose output
./scripts/cr2a-test quick-test

# Run specific test phases
./scripts/cr2a-test test component
./scripts/cr2a-test test integration
```

### 3. Validate Setup
```bash
# Validate entire setup
./scripts/cr2a-test quick-validate

# Validate specific components
./scripts/cr2a-test validate --component iam
./scripts/cr2a-test validate --component lambda
```

## Detailed Usage

### Main CLI Commands

#### Test Commands
```bash
# Run component tests
python scripts/cr2a_test_cli.py test component --verbose

# Run integration tests
python scripts/cr2a_test_cli.py test integration --verbose

# Run all tests with report generation
python scripts/cr2a_test_cli.py test all --generate-report
```

#### Deployment Commands
```bash
# Deploy all Lambda functions with layer
python scripts/cr2a_test_cli.py deploy lambda

# Deploy specific function without layer
python scripts/cr2a_test_cli.py deploy lambda --function cr2a-dependency-test --no-layer

# Manage Lambda layers
python scripts/cr2a_test_cli.py layers create
python scripts/cr2a_test_cli.py layers list
python scripts/cr2a_test_cli.py layers cleanup --keep-versions 2
```

#### Setup Commands
```bash
# Set up all AWS resources
python scripts/cr2a_test_cli.py setup aws --resource all

# Set up specific resource types
python scripts/cr2a_test_cli.py setup aws --resource iam
python scripts/cr2a_test_cli.py setup aws --resource logs
```

#### Validation Commands
```bash
# Validate all components
python scripts/cr2a_test_cli.py validate --component all --verbose

# Validate specific components
python scripts/cr2a_test_cli.py validate --component iam
python scripts/cr2a_test_cli.py validate --component lambda
```

### Individual Script Usage

#### Lambda Deployment Manager
```bash
# Deploy all functions
python scripts/deploy_lambda_tests.py --action deploy

# Test deployed functions
python scripts/deploy_lambda_tests.py --action test

# Clean up functions
python scripts/deploy_lambda_tests.py --action cleanup
```

#### Lambda Layer Manager
```bash
# Create all layers
python scripts/manage_lambda_layers.py --action create

# List layer versions
python scripts/manage_lambda_layers.py --action list --layer cr2a-test-dependencies

# Clean up old versions
python scripts/manage_lambda_layers.py --action cleanup --keep 3
```

#### AWS Resource Configurator
```bash
# Set up all resources
python scripts/configure_aws_resources.py --action setup

# Validate configuration
python scripts/configure_aws_resources.py --action validate

# Clean up resources
python scripts/configure_aws_resources.py --action cleanup
```

#### Setup Validator
```bash
# Comprehensive validation
python scripts/validate_aws_setup.py --component all --output json

# Validate specific components
python scripts/validate_aws_setup.py --component iam --verbose
```

#### Configuration Manager
```bash
# Create sample configuration
python scripts/config_manager.py create --output my_config.json

# Validate configuration
python scripts/config_manager.py validate --config my_config.json

# Show current configuration
python scripts/config_manager.py show --config my_config.json

# Update configuration
python scripts/config_manager.py update --config my_config.json --key aws_region --value us-west-2
```

## Configuration

### Configuration File Format
The framework uses JSON configuration files with the following structure:

```json
{
  "aws_region": "us-east-1",
  "api_base_url": "https://your-api-gateway-url.amazonaws.com/prod",
  "verbose_logging": true,
  "test_timeout": 300,
  "max_retries": 3,
  "component_tests_enabled": true,
  "integration_tests_enabled": true,
  "lambda_runtime": "python3.12",
  "lambda_timeout": 60,
  "lambda_memory_size": 256,
  "generate_html_reports": true,
  "report_output_dir": "test-artifacts"
}
```

### Environment Variables
Configuration can be overridden using environment variables:

- `CR2A_AWS_REGION` - AWS region
- `CR2A_API_BASE_URL` - API Gateway base URL
- `CR2A_VERBOSE` - Enable verbose logging (true/false)
- `CR2A_TEST_TIMEOUT` - Test timeout in seconds
- `CR2A_MAX_RETRIES` - Maximum retry attempts
- `CR2A_LAMBDA_RUNTIME` - Lambda runtime version
- `CR2A_REPORT_DIR` - Report output directory

### Configuration File Locations
The framework searches for configuration files in this order:
1. File specified with `--config` parameter
2. `cr2a_test_config.json` in current directory
3. `config/cr2a_test_config.json`
4. `~/.cr2a/config.json`
5. `/etc/cr2a/config.json`

## AWS Resources Created

### IAM Roles
- `cr2a-lambda-test-role` - For Lambda test functions
- `cr2a-stepfunctions-test-role` - For Step Functions testing
- `cr2a-api-test-role` - For API Gateway testing

### CloudWatch Log Groups
- `/aws/lambda/cr2a-dependency-test`
- `/aws/lambda/cr2a-openai-test`
- `/aws/lambda/cr2a-dynamodb-test`
- `/aws/stepfunctions/cr2a-contract-analysis`
- `/aws/apigateway/cr2a-test-api`

### Lambda Functions
- `cr2a-dependency-test` - Tests package dependencies
- `cr2a-openai-test` - Tests OpenAI client functionality
- `cr2a-dynamodb-test` - Tests DynamoDB operations

### Lambda Layers
- `cr2a-test-dependencies` - Core dependencies for testing
- `cr2a-openai-layer` - OpenAI client dependencies

## Troubleshooting

### Common Issues

1. **AWS Credentials Not Found**
   ```bash
   # Configure AWS credentials
   aws configure
   # Or set environment variables
   export AWS_ACCESS_KEY_ID=your_key
   export AWS_SECRET_ACCESS_KEY=your_secret
   ```

2. **Python Dependencies Missing**
   ```bash
   # Install dependencies
   pip install -r requirements.txt
   # Or activate virtual environment
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   ```

3. **Lambda Function Deployment Fails**
   - Check IAM permissions for Lambda service
   - Verify AWS region is correct
   - Ensure Lambda layer size is under limits

4. **Test Failures**
   - Run validation to check AWS resource setup
   - Check CloudWatch logs for detailed error messages
   - Verify API Gateway endpoints are deployed

### Debug Mode
Enable debug logging for detailed troubleshooting:
```bash
python scripts/cr2a_test_cli.py --log-level DEBUG test all --verbose
```

### Log Files
- CLI operations: `cr2a_test_cli.log`
- Test results: `test-artifacts/` directory
- AWS CloudWatch: Various log groups listed above

## Contributing

When adding new scripts:
1. Follow the existing naming convention
2. Include comprehensive error handling
3. Add logging for debugging
4. Update this README with usage examples
5. Add command-line help text

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review CloudWatch logs for detailed error messages
3. Validate AWS resource configuration
4. Check configuration file format and values