# Test Suite

Unit and integration tests for the Contract Analysis Tool.

## Running Tests

### Run all tests:
```cmd
python -m pytest tests/
```

### Run specific test file:
```cmd
python -m pytest tests/test_extract.py
```

### Run with verbose output:
```cmd
python -m pytest tests/ -v
```

### Run with coverage:
```cmd
python -m pytest tests/ --cov=. --cov-report=html
```

## Test Files

- **test_extract.py** - Tests for PDF/DOCX text extraction
- **test_validator.py** - Tests for schema and policy validation
- **test_integration.py** - End-to-end integration tests (TODO)

## Adding New Tests

1. Create a new file: `test_<module_name>.py`
2. Import unittest and the module to test
3. Create test class inheriting from `unittest.TestCase`
4. Add test methods starting with `test_`
5. Run tests to verify

## Test Coverage

Current coverage:
- extract.py: Basic validation tests
- validator.py: Schema and policy validation tests
- Integration: TODO

Target coverage: 80%+
