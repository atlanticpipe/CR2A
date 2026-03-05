# API Response Fixtures

This directory contains mock OpenAI API response fixtures for testing the Unified CR2A Application. These fixtures simulate various API responses including successful analyses, partial responses, and error conditions.

## Success Response Fixtures

### `api_response_success_full.json`
**Purpose**: Complete, realistic contract analysis response with all fields populated.

**Contents**:
- Full contract metadata (25 pages, 2 parties, service agreement)
- 6 clauses covering payment, liability, termination, confidentiality, IP, and indemnification
- 4 risks with varying severity levels (critical to medium)
- 3 compliance issues (GDPR, SOX, CCPA)
- 3 redlining suggestions with detailed rationale

**Use Cases**:
- Testing complete analysis workflow
- Validating full data structure parsing
- Testing UI display of comprehensive results
- Integration testing with all components

### `api_response_success_minimal.json`
**Purpose**: Minimal valid response with only required fields.

**Contents**:
- Basic contract metadata (5 pages, 2 parties, consulting agreement)
- 2 simple clauses (payment and termination)
- 1 low-severity risk
- Empty compliance issues and redlining suggestions arrays

**Use Cases**:
- Testing minimal valid response handling
- Validating required vs optional field handling
- Testing UI with sparse data
- Edge case testing for empty arrays

### `api_response_empty_arrays.json`
**Purpose**: Valid response with all arrays empty.

**Contents**:
- Minimal metadata with unknown values
- All arrays (clauses, risks, compliance_issues, redlining_suggestions) are empty

**Use Cases**:
- Testing handling of contracts with no extractable information
- Validating empty state UI rendering
- Testing edge case where analysis produces no results

## Partial Response Fixtures

### `api_response_partial_missing_risks.json`
**Purpose**: Response missing the `risks` field entirely.

**Contents**:
- Complete metadata and clauses
- Compliance issues and redlining suggestions present
- **Missing**: `risks` field

**Use Cases**:
- Testing partial response handling
- Validating graceful degradation when fields are missing
- Testing error recovery for incomplete API responses

### `api_response_partial_missing_clauses.json`
**Purpose**: Response missing the `clauses` field entirely.

**Contents**:
- Complete metadata
- Risks and compliance issues present
- **Missing**: `clauses` field

**Use Cases**:
- Testing handling of missing critical data
- Validating that risks can reference unknown clauses
- Testing UI behavior when primary data is missing

### `api_response_partial_missing_metadata.json`
**Purpose**: Response missing the `contract_metadata` field entirely.

**Contents**:
- Clauses, risks present
- Empty compliance issues and redlining suggestions
- **Missing**: `contract_metadata` field

**Use Cases**:
- Testing handling of missing metadata
- Validating that analysis can proceed without metadata
- Testing error handling for incomplete responses

## Error Response Fixtures

### `api_error_rate_limit.json`
**Purpose**: Simulates OpenAI rate limit error (HTTP 429).

**Error Details**:
- Type: `rate_limit_error`
- Code: `rate_limit_exceeded`
- Status: 429
- Message: Instructs to retry after 60 seconds

**Use Cases**:
- Testing rate limit handling and exponential backoff
- Validating retry logic
- Testing user feedback during rate limiting

### `api_error_invalid_key.json`
**Purpose**: Simulates invalid API key error (HTTP 401).

**Error Details**:
- Type: `invalid_request_error`
- Code: `invalid_api_key`
- Status: 401
- Message: Provides link to API key management

**Use Cases**:
- Testing API key validation
- Validating authentication error handling
- Testing configuration error messages

### `api_error_network_timeout.json`
**Purpose**: Simulates network timeout error (HTTP 408).

**Error Details**:
- Type: `timeout_error`
- Code: `request_timeout`
- Status: 408
- Message: Suggests retry

**Use Cases**:
- Testing timeout handling
- Validating network error recovery
- Testing retry mechanisms

### `api_error_server_error.json`
**Purpose**: Simulates OpenAI server error (HTTP 500).

**Error Details**:
- Type: `server_error`
- Code: `internal_server_error`
- Status: 500
- Message: Generic server error message

**Use Cases**:
- Testing server error handling
- Validating error display to users
- Testing retry logic for transient errors

### `api_error_invalid_model.json`
**Purpose**: Simulates invalid model name error (HTTP 404).

**Error Details**:
- Type: `invalid_request_error`
- Code: `model_not_found`
- Status: 404
- Message: Model doesn't exist or no access

**Use Cases**:
- Testing model configuration validation
- Validating error handling for configuration issues
- Testing user feedback for invalid settings

### `api_error_context_length.json`
**Purpose**: Simulates context length exceeded error (HTTP 400).

**Error Details**:
- Type: `invalid_request_error`
- Code: `context_length_exceeded`
- Status: 400
- Message: Specifies token limit and actual usage

**Use Cases**:
- Testing handling of oversized contracts
- Validating context length management
- Testing error messages for large documents

## Malformed Response Fixtures

### `api_response_invalid_json.txt`
**Purpose**: Plain text that is not valid JSON.

**Contents**: Plain text string that will cause JSON parsing to fail.

**Use Cases**:
- Testing JSON parsing error handling
- Validating error messages for malformed responses
- Testing recovery from unexpected response formats

### `api_response_malformed_json.json`
**Purpose**: Valid JSON but with incorrect data types.

**Contents**:
- `page_count` is a string instead of integer
- `parties` is a string instead of array
- `contract_type` is a number instead of string
- `clauses` is a string instead of array
- Various type mismatches throughout

**Use Cases**:
- Testing type validation
- Validating schema enforcement
- Testing error handling for type mismatches

### `api_response_incomplete_json.json`
**Purpose**: Truncated JSON that is syntactically invalid.

**Contents**: JSON that is cut off mid-object, causing parsing to fail.

**Use Cases**:
- Testing handling of incomplete API responses
- Validating error recovery for network interruptions
- Testing JSON parsing error messages

## Usage in Tests

### Loading Fixtures

```python
import json
from pathlib import Path

def load_fixture(filename: str) -> dict:
    """Load a JSON fixture file."""
    fixture_path = Path(__file__).parent / filename
    with open(fixture_path, 'r') as f:
        return json.load(f)

# Example usage
success_response = load_fixture('api_response_success_full.json')
error_response = load_fixture('api_error_rate_limit.json')
```

### Mocking API Responses

```python
from unittest.mock import Mock, patch

def test_successful_analysis():
    """Test analysis with successful API response."""
    mock_response = load_fixture('api_response_success_full.json')
    
    with patch('openai.ChatCompletion.create') as mock_create:
        mock_create.return_value = Mock(
            choices=[Mock(message=Mock(content=json.dumps(mock_response)))]
        )
        
        # Test your analysis code here
        result = analyze_contract(contract_text)
        assert result['clauses'] is not None
```

### Testing Error Handling

```python
from openai import RateLimitError

def test_rate_limit_handling():
    """Test handling of rate limit errors."""
    with patch('openai.ChatCompletion.create') as mock_create:
        mock_create.side_effect = RateLimitError("Rate limit exceeded")
        
        # Test your error handling code here
        with pytest.raises(RateLimitError):
            analyze_contract(contract_text)
```

## Fixture Maintenance

When updating fixtures:

1. **Maintain Consistency**: Ensure all success fixtures follow the same schema
2. **Update Documentation**: Update this README when adding new fixtures
3. **Validate JSON**: Use `verify_fixtures.py` to validate all JSON files
4. **Test Coverage**: Ensure each fixture is used in at least one test
5. **Realistic Data**: Keep fixture data realistic and representative of actual contracts

## Validation

Run the fixture validation script to ensure all fixtures are valid:

```bash
python tests/fixtures/verify_fixtures.py
```

This will:
- Validate JSON syntax for all `.json` files
- Check schema compliance for success responses
- Verify error response structure
- Report any issues found

## Related Files

- `generate_test_contracts.py`: Generates sample contract files (PDF/DOCX)
- `verify_fixtures.py`: Validates all fixture files
- `README.md`: General fixtures documentation
