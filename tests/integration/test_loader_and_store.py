"""
Integration tests for ContractJSONLoader and ContractDataStore working together.
"""

import json
import pytest
import tempfile
from pathlib import Path
from src.json_loader import ContractJSONLoader
from src.data_store import ContractDataStore


@pytest.fixture
def sample_contract_json_file():
    """Create a temporary JSON file with sample contract data."""
    data = {
        "parties": {
            "buyer": {
                "name": "Acme Corporation",
                "address": "123 Business St, New York, NY 10001",
                "contact": {
                    "email": "contracts@acme.com",
                    "phone": "555-0100"
                }
            },
            "seller": {
                "name": "Widget Manufacturing Inc",
                "address": "456 Industrial Blvd, Chicago, IL 60601",
                "contact": {
                    "email": "sales@widget.com",
                    "phone": "555-0200"
                }
            }
        },
        "terms": {
            "payment_terms": "Net 30 days from invoice date",
            "delivery": "FOB Destination",
            "warranty": "12 months parts and labor",
            "liability_cap": "Total contract value"
        },
        "risks": [
            {
                "type": "financial",
                "description": "Payment default risk due to buyer's credit rating",
                "severity": "medium",
                "mitigation": "Require letter of credit"
            },
            {
                "type": "operational",
                "description": "Delivery delays due to supply chain issues",
                "severity": "low",
                "mitigation": "Build in buffer time"
            },
            {
                "type": "legal",
                "description": "Compliance with export regulations",
                "severity": "high",
                "mitigation": "Legal review required"
            }
        ],
        "dates": {
            "effective_date": "2024-01-15",
            "expiration_date": "2025-01-14",
            "renewal_date": "2024-12-15",
            "first_delivery": "2024-02-01"
        },
        "financial_terms": {
            "total_value": 250000,
            "currency": "USD",
            "payment_schedule": "Monthly installments",
            "deposit_required": 50000,
            "late_payment_penalty": "1.5% per month"
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(data, f, indent=2)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


class TestLoaderAndStoreIntegration:
    """Integration tests for JSON loader and data store."""
    
    def test_load_and_query_workflow(self, sample_contract_json_file):
        """Test the complete workflow: load JSON -> store data -> query fields."""
        # Step 1: Load JSON file
        loader = ContractJSONLoader()
        contract_data = loader.load_file(sample_contract_json_file)
        
        assert contract_data is not None
        
        # Step 2: Load data into store
        store = ContractDataStore()
        store.load_data(contract_data)
        
        assert store.is_loaded() is True
        
        # Step 3: Query various fields
        buyer_name = store.get_field("parties.buyer.name")
        assert buyer_name == "Acme Corporation"
        
        seller_email = store.get_field("parties.seller.contact.email")
        assert seller_email == "sales@widget.com"
        
        payment_terms = store.get_field("terms.payment_terms")
        assert "Net 30" in payment_terms
        
        total_value = store.get_field("financial_terms.total_value")
        assert total_value == 250000
        
        # Step 4: Query array elements
        first_risk = store.get_field("risks[0]")
        assert first_risk["type"] == "financial"
        
        high_risk_severity = store.get_field("risks[2].severity")
        assert high_risk_severity == "high"
    
    def test_search_across_loaded_data(self, sample_contract_json_file):
        """Test searching for keywords across loaded contract data."""
        # Load and store data
        loader = ContractJSONLoader()
        contract_data = loader.load_file(sample_contract_json_file)
        
        store = ContractDataStore()
        store.load_data(contract_data)
        
        # Search for buyer-related information
        buyer_results = store.search_fields(["buyer"])
        assert len(buyer_results) > 0
        
        # Search for financial information
        financial_results = store.search_fields(["payment", "financial"])
        assert len(financial_results) > 0
        
        # Search for risk information
        risk_results = store.search_fields(["risk"])
        assert len(risk_results) > 0
    
    def test_schema_validation_and_field_access(self, sample_contract_json_file):
        """Test that schema validation ensures all required fields are accessible."""
        # Load with validation
        loader = ContractJSONLoader()
        contract_data = loader.load_file(sample_contract_json_file)
        
        # Verify schema info
        schema_info = loader.get_schema_info(contract_data)
        assert schema_info["has_parties"] is True
        assert schema_info["has_terms"] is True
        assert schema_info["risk_count"] == 3
        assert schema_info["has_dates"] is True
        assert schema_info["has_financial_terms"] is True
        
        # Load into store
        store = ContractDataStore()
        store.load_data(contract_data)
        
        # Verify all required top-level fields are accessible
        assert store.get_field("parties") is not None
        assert store.get_field("terms") is not None
        assert store.get_field("risks") is not None
        assert store.get_field("dates") is not None
        assert store.get_field("financial_terms") is not None
    
    def test_reload_different_data(self, sample_contract_json_file):
        """Test that store can be cleared and reloaded with different data."""
        # Load first dataset
        loader = ContractJSONLoader()
        contract_data = loader.load_file(sample_contract_json_file)
        
        store = ContractDataStore()
        store.load_data(contract_data)
        
        original_buyer = store.get_field("parties.buyer.name")
        assert original_buyer == "Acme Corporation"
        
        # Clear store
        store.clear()
        assert store.is_loaded() is False
        
        # Create new data
        new_data = {
            "parties": {"buyer": {"name": "New Company"}, "seller": {"name": "Another Seller"}},
            "terms": {},
            "risks": [],
            "dates": {},
            "financial_terms": {}
        }
        
        # Load new data
        store.load_data(new_data)
        assert store.is_loaded() is True
        
        new_buyer = store.get_field("parties.buyer.name")
        assert new_buyer == "New Company"
        assert new_buyer != original_buyer
    
    def test_field_paths_after_loading(self, sample_contract_json_file):
        """Test that all field paths are available after loading."""
        loader = ContractJSONLoader()
        contract_data = loader.load_file(sample_contract_json_file)
        
        store = ContractDataStore()
        store.load_data(contract_data)
        
        field_paths = store.get_field_paths()
        
        # Verify key paths exist
        assert "parties" in field_paths
        assert "parties.buyer" in field_paths
        assert "parties.buyer.name" in field_paths
        assert "parties.seller.contact.email" in field_paths
        assert "terms.payment_terms" in field_paths
        assert "financial_terms.total_value" in field_paths
        
        # Verify we have a reasonable number of paths
        assert len(field_paths) > 20  # Should have many nested paths
