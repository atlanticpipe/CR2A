"""
Unit tests for ContractJSONLoader class.
"""

import json
import pytest
import tempfile
from pathlib import Path
from src.json_loader import ContractJSONLoader, ValidationError


@pytest.fixture
def json_loader():
    """Create a ContractJSONLoader instance."""
    return ContractJSONLoader()


@pytest.fixture
def valid_contract_data():
    """Create valid contract data structure."""
    return {
        "parties": {
            "buyer": {"name": "Acme Corp", "address": "123 Main St"},
            "seller": {"name": "Widget Inc", "address": "456 Oak Ave"}
        },
        "terms": {
            "payment_terms": "Net 30",
            "delivery": "FOB Destination"
        },
        "risks": [
            {"type": "financial", "description": "Payment default risk", "severity": "medium"},
            {"type": "operational", "description": "Delivery delay risk", "severity": "low"}
        ],
        "dates": {
            "effective_date": "2024-01-01",
            "expiration_date": "2025-01-01"
        },
        "financial_terms": {
            "total_value": 100000,
            "currency": "USD"
        }
    }


@pytest.fixture
def temp_json_file(valid_contract_data):
    """Create a temporary JSON file with valid contract data."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(valid_contract_data, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


class TestContractJSONLoader:
    """Test suite for ContractJSONLoader."""
    
    def test_initialization(self, json_loader):
        """Test that loader initializes correctly."""
        assert json_loader is not None
        assert hasattr(json_loader, 'load_file')
        assert hasattr(json_loader, 'validate_schema')
    
    def test_load_valid_file(self, json_loader, temp_json_file, valid_contract_data):
        """Test loading a valid JSON file."""
        data = json_loader.load_file(temp_json_file)
        
        assert data is not None
        assert data == valid_contract_data
        assert "parties" in data
        assert "terms" in data
        assert "risks" in data
        assert "dates" in data
        assert "financial_terms" in data
    
    def test_load_nonexistent_file(self, json_loader):
        """Test loading a file that doesn't exist."""
        with pytest.raises(FileNotFoundError) as exc_info:
            json_loader.load_file("nonexistent_file.json")
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_load_invalid_json(self, json_loader):
        """Test loading a file with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            f.write("{ invalid json content }")
            temp_path = f.name
        
        try:
            with pytest.raises(json.JSONDecodeError):
                json_loader.load_file(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_load_missing_required_fields(self, json_loader):
        """Test loading JSON with missing required fields."""
        incomplete_data = {
            "parties": {},
            "terms": {}
            # Missing: risks, dates, financial_terms
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(incomplete_data, f)
            temp_path = f.name
        
        try:
            with pytest.raises(ValidationError) as exc_info:
                json_loader.load_file(temp_path)
            
            assert "schema" in str(exc_info.value).lower()
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_load_wrong_field_types(self, json_loader):
        """Test loading JSON with wrong field types."""
        invalid_data = {
            "parties": {},
            "terms": {},
            "risks": "should be a list",  # Wrong type
            "dates": {},
            "financial_terms": {}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(invalid_data, f)
            temp_path = f.name
        
        try:
            with pytest.raises(ValidationError):
                json_loader.load_file(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_validate_schema_valid(self, json_loader, valid_contract_data):
        """Test schema validation with valid data."""
        assert json_loader.validate_schema(valid_contract_data) is True
    
    def test_validate_schema_not_dict(self, json_loader):
        """Test schema validation with non-dictionary root."""
        assert json_loader.validate_schema([]) is False
        assert json_loader.validate_schema("string") is False
        assert json_loader.validate_schema(None) is False
    
    def test_validate_schema_missing_fields(self, json_loader):
        """Test schema validation with missing fields."""
        incomplete_data = {
            "parties": {},
            "terms": {}
        }
        assert json_loader.validate_schema(incomplete_data) is False
    
    def test_get_schema_info(self, json_loader, valid_contract_data):
        """Test extracting schema information."""
        schema_info = json_loader.get_schema_info(valid_contract_data)
        
        assert schema_info["has_parties"] is True
        assert schema_info["has_terms"] is True
        assert schema_info["risk_count"] == 2
        assert schema_info["has_dates"] is True
        assert schema_info["has_financial_terms"] is True
        assert schema_info["total_fields"] == 5
    
    def test_load_directory_path(self, json_loader):
        """Test that loading a directory path raises appropriate error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(FileNotFoundError) as exc_info:
                json_loader.load_file(temp_dir)
            
            assert "not a file" in str(exc_info.value).lower()
