# CR2A Testing & Debugging Framework

A comprehensive testing and debugging framework for the CR2A (Contract Review and Analysis) application. This framework provides systematic component isolation, integration testing, and automated issue resolution across the entire AWS-based pipeline.

## Overview

The framework follows a layered testing strategy:
1. **Component Isolation** → Test individual Lambda functions independently
2. **Integration Testing** → Test component interactions and workflows  
3. **End-to-End Validation** → Test complete analysis workflows
4. **Automated Issue Resolution** → Systematically fix identified problems

## Directory Structure

```
tests/
├── core/                   # Core framework components
│   ├── models.py          # Data models for test results and issues
│   ├── interfaces.py      # Abstract base classes and protocols
│   ├── base.py           # Base testing framework with common utilities
│   └── config.py         # Configuration management
├── component/             # Component isolation testing modules
├── integration/           # Integration testing modules
├── automation/            # Test automation and orchestration
├── resolution/            # Automated issue resolution modules
├── main.py               # CLI entry point
└── README.md             # This file
```

## Installation

1. Install the testing dependencies:
```bash
pip install -r requirements-testing.txt
```

2. Configure AWS credentials (one of the following):
```bash
# AWS CLI
aws configure

# Environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1

# Or use IAM roles if running on EC2
```

## Usage

### Command Line Interface

```bash
# Run component tests only
python -m tests.main --component

# Run integration tests only  
python -m tests.main --integration

# Run complete test suite
python -m tests.main --full

# Use custom configuration
python -m tests.main --config custom_config.json --verbose

# Specify output directory
python -m tests.main --full --output-dir ./my-test-results
```

### Configuration

The framework can be configured via:

1. **Configuration file** (test_config.json):
```json
{
  "aws_region": "us-east-1",
  "lambda_timeout": 30,
  "max_retries": 3,
  "parallel_execution": false,
  "verbose_logging": true,
  "save_artifacts": true,
  "artifact_path": "./test-artifacts"
}
```

2. **Environment variables**:
- `AWS_REGION`: AWS region for testing
- `LAMBDA_TIMEOUT`: Lambda function timeout
- `MAX_RETRIES`: Maximum retry attempts
- `PARALLEL_EXECUTION`: Enable parallel test execution
- `VERBOSE_LOGGING`: Enable verbose logging
- `SAVE_ARTIFACTS`: Save test artifacts
- `ARTIFACT_PATH`: Directory for test artifacts

3. **CR2A Resource Names** (environment variables):
- `CR2A_STATE_MACHINE_NAME`: Step Functions state machine name
- `CR2A_API_GATEWAY_ID`: API Gateway ID
- `CR2A_API_LAMBDA`: API Lambda function name
- `CR2A_ANALYZER_LAMBDA`: Analyzer Lambda function name
- `CR2A_LLM_REFINE_LAMBDA`: LLM Refine Lambda function name
- `CR2A_JOBS_TABLE`: DynamoDB jobs table name
- `CR2A_RESULTS_TABLE`: DynamoDB results table name
- `CR2A_DOCUMENTS_BUCKET`: S3 documents bucket name
- `CR2A_RESULTS_BUCKET`: S3 results bucket name

### Running Tests with Pytest

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_framework_setup.py -v

# Run tests with coverage
pytest tests/ --cov=tests --cov-report=html

# Run only component tests
pytest tests/ -m component

# Run only integration tests  
pytest tests/ -m integration

# Run property-based tests
pytest tests/ -m property
```

## Test Markers

The framework uses pytest markers to categorize tests:

- `@pytest.mark.component`: Component isolation tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.property`: Property-based tests
- `@pytest.mark.slow`: Slow running tests
- `@pytest.mark.aws`: Tests requiring AWS credentials
- `@pytest.mark.unit`: Unit tests

## Development

### Adding New Tests

1. **Component Tests**: Add to `tests/component/`
2. **Integration Tests**: Add to `tests/integration/`
3. **Property-Based Tests**: Use Hypothesis library with appropriate markers

### Core Interfaces

The framework provides abstract base classes for consistent implementation:

- `ComponentTester`: For component isolation testing
- `IntegrationTester`: For integration testing
- `IssueResolver`: For automated issue resolution
- `TestOrchestrator`: For test orchestration
- `TestReporter`: For test reporting
- `AWSResourceValidator`: For AWS resource validation

### Data Models

Key data models include:

- `TestResult`: Individual test result with execution details
- `TestSuite`: Collection of related tests with metadata
- `Issue`: Identified issue with resolution guidance
- `ResolutionResult`: Result of applying an automated fix
- `TestConfiguration`: Configuration for test execution

## Property-Based Testing

The framework uses Hypothesis for property-based testing to validate universal properties across randomized inputs. Each property test:

- Runs minimum 100 iterations
- References design document properties
- Uses tag format: `Feature: cr2a-testing-debugging, Property {number}: {property_text}`

## Error Handling

The framework provides comprehensive error handling:

- **Component Test Errors**: Dependency imports, client initialization, database operations
- **Integration Test Errors**: State machine validation, permission validation, workflow execution
- **API Test Errors**: Endpoint availability, response validation, CORS configuration

## Logging

Structured logging is provided throughout the framework:

- Configurable log levels (DEBUG, INFO, WARNING, ERROR)
- Timestamped log entries
- Component-specific loggers
- CloudWatch integration for AWS resources

## Contributing

1. Follow the existing code structure and patterns
2. Add appropriate test markers
3. Include docstrings for all public methods
4. Update this README for significant changes
5. Ensure all tests pass before submitting changes

## License

This testing framework is part of the CR2A application and follows the same licensing terms.