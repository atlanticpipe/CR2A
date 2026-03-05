"""
Unit tests for ContractDataStore class.
"""

import pytest
from src.data_store import ContractDataStore


@pytest.fixture
def data_store():
    """Create a ContractDataStore instance."""
    return ContractDataStore()


@pytest.fixture
def sample_contract_data():
    """Create sample contract data for testing."""
    return {
        "parties": {
            "buyer": {
                "name": "Acme Corp",
                "address": "123 Main St",
                "contact": {
                    "email": "buyer@acme.com",
                    "phone": "555-1234"
                }
            },
            "seller": {
                "name": "Widget Inc",
                "address": "456 Oak Ave"
            }
        },
        "terms": {
            "payment_terms": "Net 30",
            "delivery": "FOB Destination",
            "warranty": "1 year"
        },
        "risks": [
            {"type": "financial", "description": "Payment default risk", "severity": "medium"},
            {"type": "operational", "description": "Delivery delay risk", "severity": "low"},
            {"type": "legal", "description": "Compliance risk", "severity": "high"}
        ],
        "dates": {
            "effective_date": "2024-01-01",
            "expiration_date": "2025-01-01",
            "renewal_date": "2024-12-01"
        },
        "financial_terms": {
            "total_value": 100000,
            "currency": "USD",
            "payment_schedule": "monthly"
        }
    }


class TestContractDataStore:
    """Test suite for ContractDataStore."""
    
    def test_initialization(self, data_store):
        """Test that data store initializes correctly."""
        assert data_store is not None
        assert data_store.data == {}
        assert data_store.schema_map == {}
        assert data_store.is_loaded() is False
    
    def test_load_data(self, data_store, sample_contract_data):
        """Test loading data into the store."""
        data_store.load_data(sample_contract_data)
        
        assert data_store.is_loaded() is True
        assert data_store.data == sample_contract_data
        assert len(data_store.schema_map) > 0
    
    def test_get_field_top_level(self, data_store, sample_contract_data):
        """Test retrieving top-level fields."""
        data_store.load_data(sample_contract_data)
        
        parties = data_store.get_field("parties")
        assert parties is not None
        assert "buyer" in parties
        assert "seller" in parties
    
    def test_get_field_nested(self, data_store, sample_contract_data):
        """Test retrieving nested fields with dot notation."""
        data_store.load_data(sample_contract_data)
        
        buyer_name = data_store.get_field("parties.buyer.name")
        assert buyer_name == "Acme Corp"
        
        buyer_email = data_store.get_field("parties.buyer.contact.email")
        assert buyer_email == "buyer@acme.com"
        
        payment_terms = data_store.get_field("terms.payment_terms")
        assert payment_terms == "Net 30"
    
    def test_get_field_array_index(self, data_store, sample_contract_data):
        """Test retrieving array elements by index."""
        data_store.load_data(sample_contract_data)
        
        first_risk = data_store.get_field("risks[0]")
        assert first_risk is not None
        assert first_risk["type"] == "financial"
        
        second_risk_type = data_store.get_field("risks[1].type")
        assert second_risk_type == "operational"
    
    def test_get_field_nonexistent(self, data_store, sample_contract_data):
        """Test retrieving non-existent fields returns None."""
        data_store.load_data(sample_contract_data)
        
        result = data_store.get_field("nonexistent.field")
        assert result is None
        
        result = data_store.get_field("parties.buyer.nonexistent")
        assert result is None
    
    def test_get_field_empty_path(self, data_store, sample_contract_data):
        """Test that empty field path returns None."""
        data_store.load_data(sample_contract_data)
        
        result = data_store.get_field("")
        assert result is None
    
    def test_search_fields_by_path(self, data_store, sample_contract_data):
        """Test searching fields by path keywords."""
        data_store.load_data(sample_contract_data)
        
        results = data_store.search_fields(["buyer"])
        assert len(results) > 0
        
        # Check that buyer-related fields are in results
        paths = [path for path, _ in results]
        assert any("buyer" in path.lower() for path in paths)
    
    def test_search_fields_by_value(self, data_store, sample_contract_data):
        """Test searching fields by value content."""
        data_store.load_data(sample_contract_data)
        
        results = data_store.search_fields(["Acme"])
        assert len(results) > 0
        
        # Check that the buyer name field is in results
        found = False
        for path, value in results:
            if "Acme" in str(value):
                found = True
                break
        assert found is True
    
    def test_search_fields_multiple_keywords(self, data_store, sample_contract_data):
        """Test searching with multiple keywords."""
        data_store.load_data(sample_contract_data)
        
        results = data_store.search_fields(["payment", "terms"])
        assert len(results) > 0
    
    def test_search_fields_case_insensitive(self, data_store, sample_contract_data):
        """Test that search is case-insensitive."""
        data_store.load_data(sample_contract_data)
        
        results_lower = data_store.search_fields(["acme"])
        results_upper = data_store.search_fields(["ACME"])
        results_mixed = data_store.search_fields(["AcMe"])
        
        assert len(results_lower) > 0
        assert len(results_upper) > 0
        assert len(results_mixed) > 0
    
    def test_search_fields_no_keywords(self, data_store, sample_contract_data):
        """Test that searching with no keywords returns empty list."""
        data_store.load_data(sample_contract_data)
        
        results = data_store.search_fields([])
        assert results == []
    
    def test_search_fields_no_matches(self, data_store, sample_contract_data):
        """Test searching with keywords that don't match anything."""
        data_store.load_data(sample_contract_data)
        
        results = data_store.search_fields(["nonexistent", "keywords"])
        assert len(results) == 0
    
    def test_get_all_data(self, data_store, sample_contract_data):
        """Test retrieving all data."""
        data_store.load_data(sample_contract_data)
        
        all_data = data_store.get_all_data()
        assert all_data == sample_contract_data
    
    def test_get_field_paths(self, data_store, sample_contract_data):
        """Test retrieving all field paths."""
        data_store.load_data(sample_contract_data)
        
        paths = data_store.get_field_paths()
        assert len(paths) > 0
        assert "parties" in paths
        assert "parties.buyer.name" in paths
        assert "terms.payment_terms" in paths
    
    def test_clear(self, data_store, sample_contract_data):
        """Test clearing the data store."""
        data_store.load_data(sample_contract_data)
        assert data_store.is_loaded() is True
        
        data_store.clear()
        assert data_store.is_loaded() is False
        assert data_store.data == {}
        assert data_store.schema_map == {}
    
    def test_schema_map_building(self, data_store, sample_contract_data):
        """Test that schema map is built correctly."""
        data_store.load_data(sample_contract_data)
        
        # Check that schema map contains expected paths
        assert len(data_store.schema_map) > 0
        
        # Verify some key paths exist in schema map (case-insensitive)
        schema_keys_lower = [k.lower() for k in data_store.schema_map.keys()]
        assert "parties" in schema_keys_lower
        assert "parties.buyer" in schema_keys_lower
        assert "parties.buyer.name" in schema_keys_lower
        assert "risks" in schema_keys_lower
    
    def test_empty_data_operations(self, data_store):
        """Test operations on empty data store."""
        # Before loading any data
        assert data_store.get_field("any.field") is None
        assert data_store.search_fields(["keyword"]) == []
        assert data_store.get_all_data() == {}
        assert data_store.get_field_paths() == []
