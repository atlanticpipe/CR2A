# Testing Infrastructure

This directory contains the testing infrastructure for the CR2A repository.

## Overview

The testing infrastructure supports both Python and JavaScript testing with comprehensive coverage reporting.

### Python Testing
- **Framework**: pytest with hypothesis for property-based testing
- **Coverage**: coverage.py with 80% minimum threshold
- **Configuration**: pytest.ini

### JavaScript Testing
- **Framework**: Vitest with happy-dom for DOM testing
- **Coverage**: V8 coverage with 80% minimum threshold
- **Configuration**: vitest.config.js

## Running Tests

### Python Tests
```bash
# Run all Python tests
pytest

# Run with coverage report
pytest --cov=src --cov=cleanup_repo --cov-report=term-missing --cov-report=html:coverage/python --cov-fail-under=80

# Run specific test file
pytest tests/test_cleanup.py

# Run tests with specific marker
pytest -m unit
pytest -m property
```

### JavaScript Tests
```bash
# Install dependencies first
npm install

# Run all JavaScript tests
npm test

# Run tests in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage

# Run with UI
npm run test:ui
```


## Test Structure

### Python Tests
- `test_cleanup.py` - Tests for cleanup functionality
- `conftest.py` - Shared fixtures and utilities
- `setup.js` - JavaScript test setup

### JavaScript Tests (to be created)
- `frontend/services/*.test.js` - Service tests
- `frontend/*.test.js` - UI component tests

## Fixtures and Utilities

### Python Fixtures (conftest.py)
- `temp_repo` - Clean temporary repository
- `temp_repo_with_artifacts` - Repository with test artifacts
- `temp_repo_with_duplicates` - Repository with duplicate files
- `temp_repo_with_backups` - Repository with backup files
- `safety_checker` - Configured SafetyChecker instance
- `file_scanner` - Configured FileScanner instance
- `sample_removal_results` - Sample test data

### JavaScript Fixtures (fixtures.js)
- `sampleContractText` - Sample contract for testing
- `sampleAnalysisResponse` - Sample API response
- `createMockFile()` - Create mock File objects
- `createMockElement()` - Create mock DOM elements
- `waitFor()` - Async condition waiting
- `createMockFetchResponse()` - Mock fetch responses

## Coverage Requirements

Both Python and JavaScript tests must maintain **80% minimum coverage** as specified in requirements.

### Viewing Coverage Reports

**Python**:
```bash
# Generate HTML report
pytest --cov --cov-report=html
# Open coverage/python/index.html in browser
```

**JavaScript**:
```bash
# Generate coverage report
npm run test:coverage
# Open coverage/index.html in browser
```

## Writing Tests

### Python Unit Tests
```python
def test_example(temp_repo):
    # Use fixtures for setup
    file = temp_repo / "test.txt"
    file.write_text("content")
    
    # Test your code
    assert file.exists()
```

### Python Property Tests
```python
from hypothesis import given, strategies as st

@given(st.text())
def test_property_example(text):
    # Test universal properties
    assert len(text) >= 0
```

### JavaScript Unit Tests
```javascript
import { describe, it, expect } from 'vitest';

describe('Component', () => {
  it('should work correctly', () => {
    expect(true).toBe(true);
  });
});
```

## Test Markers

Python tests can be marked with:
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.property` - Property-based tests
- `@pytest.mark.slow` - Slow-running tests
