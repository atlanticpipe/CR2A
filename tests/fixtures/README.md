# Test Fixtures for CR2A Application

This directory contains sample contract files, API response fixtures, and malformed files for testing the CR2A application.

## Valid Contract Files

### PDF Contracts
- `contract_1page.pdf` - Single page contract (~11 KB)
- `contract_10pages.pdf` - 10-page contract (~18 KB)
- `contract_25pages.pdf` - 25-page contract (~45 KB)
- `contract_50pages.pdf` - 50-page contract (~85 KB)

### DOCX Contracts
- `contract_1page.docx` - Single page contract (~39 KB)
- `contract_10pages.docx` - 10-page contract (~40 KB)
- `contract_25pages.docx` - 25-page contract (~41 KB)
- `contract_50pages.docx` - 50-page contract (~43 KB)

All valid contracts contain realistic service agreement text with multiple clauses including:
- Services and scope
- Term and termination
- Compensation and payment
- Intellectual property
- Confidentiality
- Warranties and disclaimers
- Limitation of liability
- Indemnification
- General provisions

## API Response Fixtures

Mock OpenAI API responses for testing analysis workflow. See `API_FIXTURES_README.md` for detailed documentation.

### Success Responses
- `api_response_success_full.json` - Complete analysis with all fields
- `api_response_success_minimal.json` - Minimal valid response
- `api_response_empty_arrays.json` - Valid response with empty arrays

### Partial Responses
- `api_response_partial_missing_risks.json` - Missing risks field
- `api_response_partial_missing_clauses.json` - Missing clauses field
- `api_response_partial_missing_metadata.json` - Missing metadata field

### Error Responses
- `api_error_rate_limit.json` - Rate limit error (HTTP 429)
- `api_error_invalid_key.json` - Invalid API key (HTTP 401)
- `api_error_network_timeout.json` - Network timeout (HTTP 408)
- `api_error_server_error.json` - Server error (HTTP 500)
- `api_error_invalid_model.json` - Invalid model (HTTP 404)
- `api_error_context_length.json` - Context length exceeded (HTTP 400)

### Malformed Responses
- `api_response_invalid_json.txt` - Plain text (not JSON)
- `api_response_malformed_json.json` - Wrong data types
- `api_response_incomplete_json.json` - Truncated JSON

## Malformed Files for Error Testing

### Fake Format Files
- `malformed_fake.pdf` - Plain text file with .pdf extension (not a real PDF)
- `malformed_fake.docx` - Plain text file with .docx extension (not a real DOCX)

### Empty Files
- `empty.pdf` - Empty file with .pdf extension
- `empty.docx` - Empty file with .docx extension

### Corrupted Files
- `corrupted.pdf` - Partial PDF file with only header (incomplete/corrupted)

### Unsupported Format
- `contract.txt` - Valid contract text in unsupported .txt format

## Other Files

- `sample_contract.txt` - Original sample contract text file
- `generate_test_contracts.py` - Script used to generate contract test files
- `verify_fixtures.py` - Script to validate all fixtures
- `API_FIXTURES_README.md` - Detailed documentation for API response fixtures

## Usage in Tests

These fixtures are used to test:

1. **File Format Validation** (Property 1)
   - Valid formats: PDF and DOCX files should be accepted
   - Invalid formats: TXT and other formats should be rejected

2. **Text Extraction** (Property 6)
   - Valid files should extract non-empty text
   - Malformed files should handle errors gracefully

3. **Analysis Result Structure** (Property 7)
   - API responses should contain all required fields
   - Partial responses should be handled gracefully

4. **Error Handling** (Property 10)
   - Empty files should trigger appropriate error messages
   - Corrupted files should be handled without crashing
   - Fake format files should be detected and rejected
   - API errors should be handled with appropriate retry logic

5. **Performance Testing** (Property 28)
   - 50-page contracts should be analyzed within 60 seconds
   - Various sizes test scalability

## Validating Fixtures

To validate all fixtures (contract files and API responses), run:

```bash
python tests/fixtures/verify_fixtures.py
```

This will:
- Verify all PDF and DOCX files can be read
- Check malformed files raise appropriate errors
- Validate file sizes are within expected ranges
- Validate JSON syntax for all API response fixtures
- Check schema compliance for success responses
- Verify error response structure

## Regenerating Contract Fixtures

To regenerate contract test fixtures, run:

```bash
python tests/fixtures/generate_test_contracts.py
```

This will recreate all PDF, DOCX, and malformed files with fresh content.

## Dependencies

The generation and verification scripts require:
- `reportlab` - For PDF generation
- `python-docx` - For DOCX generation and reading
- `PyPDF2` - For PDF reading

Install with:
```bash
pip install reportlab python-docx PyPDF2
```
