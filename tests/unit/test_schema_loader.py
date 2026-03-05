"""
Unit tests for SchemaLoader component.

Tests the SchemaLoader class that loads and caches the output schema
from configuration, including error handling and clause category extraction.

Requirements: 1.3
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
import tempfile
import os

from src.schema_loader import SchemaLoader


class TestSchemaLoaderInit:
    """Tests for SchemaLoader initialization."""
    
    def test_default_schema_path(self):
        """Test that default schema path is set correctly."""
        loader = SchemaLoader()
        assert loader._schema_path == "config/output_schemas_v1.json"
    
    def test_custom_schema_path(self):
        """Test that custom schema path can be provided."""
        loader = SchemaLoader(schema_path="custom/path/schema.json")
        assert loader._schema_path == "custom/path/schema.json"
    
    def test_initial_cache_is_none(self):
        """Test that schema cache is initially None."""
        loader = SchemaLoader()
        assert loader._schema is None
        assert loader._clause_categories is None


class TestLoadSchema:
    """Tests for SchemaLoader.load_schema() method."""
    
    def test_load_valid_schema_file(self):
        """Test loading a valid schema file returns parsed JSON."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        schema = loader.load_schema()
        
        # Verify schema is loaded
        assert schema is not None
        assert isinstance(schema, dict)
        
        # Verify key schema properties exist
        assert "$schema" in schema
        assert "properties" in schema
        assert "$defs" in schema
        
        # Verify required sections exist
        assert "contract_overview" in schema["properties"]
        assert "administrative_and_commercial_terms" in schema["properties"]
        assert "technical_and_performance_terms" in schema["properties"]
        assert "legal_risk_and_enforcement" in schema["properties"]
        assert "regulatory_and_compliance_terms" in schema["properties"]
        assert "data_technology_and_deliverables" in schema["properties"]
        assert "supplemental_operational_risks" in schema["properties"]
        
        # Verify ClauseBlock definition exists
        assert "ClauseBlock" in schema["$defs"]
    
    def test_schema_is_cached(self):
        """Test that schema is cached after first load."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        # First load
        schema1 = loader.load_schema()
        
        # Second load should return cached version
        schema2 = loader.load_schema()
        
        # Should be the same object (cached)
        assert schema1 is schema2
    
    def test_error_handling_for_missing_file(self):
        """Test that FileNotFoundError is raised for missing schema file."""
        loader = SchemaLoader(schema_path="nonexistent/path/schema.json")
        
        with pytest.raises(FileNotFoundError) as exc_info:
            loader.load_schema()
        
        assert "Schema file not found" in str(exc_info.value)
        assert "nonexistent/path/schema.json" in str(exc_info.value)
    
    def test_error_handling_for_invalid_json(self):
        """Test that json.JSONDecodeError is raised for invalid JSON."""
        # Create a temporary file with invalid JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json content }")
            temp_path = f.name
        
        try:
            loader = SchemaLoader(schema_path=temp_path)
            
            with pytest.raises(json.JSONDecodeError):
                loader.load_schema()
        finally:
            os.unlink(temp_path)
    
    def test_error_handling_for_missing_required_sections(self):
        """Test that ValueError is raised when required sections are missing."""
        # Create a temporary file with valid JSON but missing required sections
        incomplete_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "properties": {
                "contract_overview": {}
                # Missing other required sections
            },
            "$defs": {
                "ClauseBlock": {}
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(incomplete_schema, f)
            temp_path = f.name
        
        try:
            loader = SchemaLoader(schema_path=temp_path)
            
            with pytest.raises(ValueError) as exc_info:
                loader.load_schema()
            
            assert "Schema missing required sections" in str(exc_info.value)
        finally:
            os.unlink(temp_path)
    
    def test_error_handling_for_missing_clause_block_definition(self):
        """Test that ValueError is raised when ClauseBlock definition is missing."""
        # Create a schema with all sections but missing ClauseBlock
        schema_without_clause_block = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "properties": {
                "contract_overview": {},
                "administrative_and_commercial_terms": {},
                "technical_and_performance_terms": {},
                "legal_risk_and_enforcement": {},
                "regulatory_and_compliance_terms": {},
                "data_technology_and_deliverables": {},
                "supplemental_operational_risks": {}
            },
            "$defs": {}  # Missing ClauseBlock
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(schema_without_clause_block, f)
            temp_path = f.name
        
        try:
            loader = SchemaLoader(schema_path=temp_path)
            
            with pytest.raises(ValueError) as exc_info:
                loader.load_schema()
            
            assert "ClauseBlock" in str(exc_info.value)
        finally:
            os.unlink(temp_path)


class TestGetClauseCategories:
    """Tests for SchemaLoader.get_clause_categories() method."""
    
    def test_clause_category_extraction(self):
        """Test that clause categories are correctly extracted for each section."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        categories = loader.get_clause_categories()
        
        # Verify categories is a dictionary
        assert isinstance(categories, dict)
        
        # Verify all clause sections are present
        assert "administrative_and_commercial_terms" in categories
        assert "technical_and_performance_terms" in categories
        assert "legal_risk_and_enforcement" in categories
        assert "regulatory_and_compliance_terms" in categories
        assert "data_technology_and_deliverables" in categories
        assert "supplemental_operational_risks" in categories
    
    def test_administrative_and_commercial_terms_categories(self):
        """Test that administrative_and_commercial_terms has 16 categories."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        categories = loader.get_clause_categories()
        admin_categories = categories["administrative_and_commercial_terms"]
        
        assert len(admin_categories) == 16
        
        # Verify some expected category names
        assert "Contract Term, Renewal & Extensions" in admin_categories
        assert "Bonding, Surety, & Insurance Obligations" in admin_categories
        assert "Change Orders, Scope Adjustments & Modifications" in admin_categories
    
    def test_technical_and_performance_terms_categories(self):
        """Test that technical_and_performance_terms has 17 categories."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        categories = loader.get_clause_categories()
        tech_categories = categories["technical_and_performance_terms"]
        
        assert len(tech_categories) == 17
        
        # Verify some expected category names
        assert "Scope of Work (Work Inclusions, Exclusions & Defined Deliverables)" in tech_categories
        assert "Warranty, Guarantee & Defects Liability Periods" in tech_categories
    
    def test_legal_risk_and_enforcement_categories(self):
        """Test that legal_risk_and_enforcement has 13 categories."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        categories = loader.get_clause_categories()
        legal_categories = categories["legal_risk_and_enforcement"]
        
        assert len(legal_categories) == 13
        
        # Verify some expected category names
        assert "Indemnification, Defense & Hold Harmless Provisions" in legal_categories
        assert "Dispute Resolution (Mediation, Arbitration, Litigation)" in legal_categories
    
    def test_regulatory_and_compliance_terms_categories(self):
        """Test that regulatory_and_compliance_terms has 8 categories."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        categories = loader.get_clause_categories()
        reg_categories = categories["regulatory_and_compliance_terms"]
        
        assert len(reg_categories) == 8
        
        # Verify some expected category names
        assert "Certified Payroll, Recordkeeping & Reporting Obligations" in reg_categories
        assert "Prevailing Wage, Davis-Bacon & Federal/State Wage Compliance" in reg_categories
    
    def test_data_technology_and_deliverables_categories(self):
        """Test that data_technology_and_deliverables has 7 categories."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        categories = loader.get_clause_categories()
        data_categories = categories["data_technology_and_deliverables"]
        
        assert len(data_categories) == 7
        
        # Verify some expected category names
        assert "Data Ownership, Access & Rights to Digital Deliverables" in data_categories
        assert "Cybersecurity Standards, Breach Notification & IT System Use Policies" in data_categories
    
    def test_supplemental_operational_risks_is_empty_list(self):
        """Test that supplemental_operational_risks returns empty list (it's an array type)."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        categories = loader.get_clause_categories()
        
        assert categories["supplemental_operational_risks"] == []
    
    def test_clause_categories_are_cached(self):
        """Test that clause categories are cached after first extraction."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        # First call
        categories1 = loader.get_clause_categories()
        
        # Second call should return cached version
        categories2 = loader.get_clause_categories()
        
        # Should be the same object (cached)
        assert categories1 is categories2


class TestGetSchemaForPrompt:
    """Tests for SchemaLoader.get_schema_for_prompt() method."""
    
    def test_returns_non_empty_string(self):
        """Test that get_schema_for_prompt returns a non-empty string."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        prompt_schema = loader.get_schema_for_prompt()
        
        assert isinstance(prompt_schema, str)
        assert len(prompt_schema) > 0
    
    def test_contains_schema_structure_header(self):
        """Test that prompt contains schema structure header."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        prompt_schema = loader.get_schema_for_prompt()
        
        assert "# Output Schema Structure" in prompt_schema
    
    def test_contains_clause_block_structure(self):
        """Test that prompt contains ClauseBlock structure description."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        prompt_schema = loader.get_schema_for_prompt()
        
        assert "ClauseBlock Structure" in prompt_schema
        assert "Clause Language" in prompt_schema
        assert "Clause Summary" in prompt_schema
        assert "Risk Triggers Identified" in prompt_schema
        assert "Flow-Down Obligations" in prompt_schema
        assert "Redline Recommendations" in prompt_schema
    
    def test_contains_all_section_titles(self):
        """Test that prompt contains all section titles."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        prompt_schema = loader.get_schema_for_prompt()
        
        assert "Contract Overview" in prompt_schema
        assert "Administrative & Commercial Terms" in prompt_schema
        assert "Technical & Performance Terms" in prompt_schema
        assert "Legal Risk & Enforcement" in prompt_schema
        assert "Regulatory & Compliance Terms" in prompt_schema
        assert "Data, Technology & Deliverables" in prompt_schema
        assert "Supplemental Operational Risks" in prompt_schema
    
    def test_contains_enum_values(self):
        """Test that prompt contains enum values for risk level and bid model."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        prompt_schema = loader.get_schema_for_prompt()
        
        # Risk levels
        assert "Low" in prompt_schema
        assert "Medium" in prompt_schema
        assert "High" in prompt_schema
        assert "Critical" in prompt_schema
        
        # Bid models
        assert "Lump Sum" in prompt_schema
        assert "Unit Price" in prompt_schema
        
        # Redline actions
        assert "insert" in prompt_schema
        assert "replace" in prompt_schema
        assert "delete" in prompt_schema
    
    def test_contains_important_notes(self):
        """Test that prompt contains important notes about schema usage."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        prompt_schema = loader.get_schema_for_prompt()
        
        assert "Important Notes" in prompt_schema
        assert "omit" in prompt_schema.lower() or "Omit" in prompt_schema


class TestGetClauseBlockSchema:
    """Tests for SchemaLoader.get_clause_block_schema() method."""
    
    def test_returns_clause_block_definition(self):
        """Test that get_clause_block_schema returns the ClauseBlock definition."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        clause_block = loader.get_clause_block_schema()
        
        assert isinstance(clause_block, dict)
        assert "type" in clause_block
        assert clause_block["type"] == "object"
    
    def test_clause_block_has_required_properties(self):
        """Test that ClauseBlock definition has all required properties."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        clause_block = loader.get_clause_block_schema()
        
        assert "properties" in clause_block
        properties = clause_block["properties"]
        
        # Verify all required ClauseBlock properties exist
        assert "Clause Language" in properties
        assert "Clause Summary" in properties
        assert "Risk Triggers Identified" in properties
        assert "Flow-Down Obligations" in properties
        assert "Redline Recommendations" in properties
        assert "Harmful Language / Policy Conflicts" in properties
    
    def test_clause_block_has_required_fields_list(self):
        """Test that ClauseBlock definition specifies required fields."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        clause_block = loader.get_clause_block_schema()
        
        assert "required" in clause_block
        required = clause_block["required"]
        
        assert "Clause Language" in required
        assert "Clause Summary" in required
        assert "Risk Triggers Identified" in required
        assert "Flow-Down Obligations" in required
        assert "Redline Recommendations" in required
        assert "Harmful Language / Policy Conflicts" in required


class TestGetEnumValues:
    """Tests for SchemaLoader.get_enum_values() method."""
    
    def test_get_risk_level_enum_values(self):
        """Test that correct risk level enum values are returned."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        risk_levels = loader.get_enum_values("risk_level")
        
        assert isinstance(risk_levels, list)
        assert len(risk_levels) == 4
        assert "Low" in risk_levels
        assert "Medium" in risk_levels
        assert "High" in risk_levels
        assert "Critical" in risk_levels
    
    def test_get_bid_model_enum_values(self):
        """Test that correct bid model enum values are returned."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        bid_models = loader.get_enum_values("bid_model")
        
        assert isinstance(bid_models, list)
        assert len(bid_models) == 7
        assert "Lump Sum" in bid_models
        assert "Unit Price" in bid_models
        assert "Cost Plus" in bid_models
        assert "Time & Materials" in bid_models
        assert "GMP" in bid_models
        assert "Design-Build" in bid_models
        assert "Other" in bid_models
    
    def test_get_action_enum_values(self):
        """Test that correct redline action enum values are returned."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        actions = loader.get_enum_values("action")
        
        assert isinstance(actions, list)
        assert len(actions) == 3
        assert "insert" in actions
        assert "replace" in actions
        assert "delete" in actions
    
    def test_unknown_field_raises_error(self):
        """Test that unknown field name raises ValueError."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        with pytest.raises(ValueError) as exc_info:
            loader.get_enum_values("unknown_field")
        
        assert "Unknown enum field" in str(exc_info.value)
        assert "unknown_field" in str(exc_info.value)


class TestGetSectionSchema:
    """Tests for SchemaLoader.get_section_schema() method."""
    
    def test_get_administrative_section_schema(self):
        """Test getting administrative_and_commercial_terms section schema."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        section = loader.get_section_schema("administrative_and_commercial_terms")
        
        assert section is not None
        assert isinstance(section, dict)
        assert "properties" in section
    
    def test_get_nonexistent_section_returns_none(self):
        """Test that getting nonexistent section returns None."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        section = loader.get_section_schema("nonexistent_section")
        
        assert section is None


class TestGetContractOverviewSchema:
    """Tests for SchemaLoader.get_contract_overview_schema() method."""
    
    def test_returns_contract_overview_schema(self):
        """Test that contract_overview schema is returned."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        overview = loader.get_contract_overview_schema()
        
        assert isinstance(overview, dict)
        assert "properties" in overview
    
    def test_contract_overview_has_required_fields(self):
        """Test that contract_overview schema has all 8 required fields."""
        loader = SchemaLoader(schema_path="config/output_schemas_v1.json")
        
        overview = loader.get_contract_overview_schema()
        properties = overview.get("properties", {})
        
        assert "Project Title" in properties
        assert "Solicitation No." in properties
        assert "Owner" in properties
        assert "Contractor" in properties
        assert "Scope" in properties
        assert "General Risk Level" in properties
        assert "Bid Model" in properties
        assert "Notes" in properties


class TestSchemaLoaderConstants:
    """Tests for SchemaLoader class constants."""
    
    def test_clause_sections_constant(self):
        """Test that CLAUSE_SECTIONS contains expected sections."""
        assert "administrative_and_commercial_terms" in SchemaLoader.CLAUSE_SECTIONS
        assert "technical_and_performance_terms" in SchemaLoader.CLAUSE_SECTIONS
        assert "legal_risk_and_enforcement" in SchemaLoader.CLAUSE_SECTIONS
        assert "regulatory_and_compliance_terms" in SchemaLoader.CLAUSE_SECTIONS
        assert "data_technology_and_deliverables" in SchemaLoader.CLAUSE_SECTIONS
        assert len(SchemaLoader.CLAUSE_SECTIONS) == 5
    
    def test_all_sections_constant(self):
        """Test that ALL_SECTIONS contains all 7 sections."""
        assert "contract_overview" in SchemaLoader.ALL_SECTIONS
        assert "administrative_and_commercial_terms" in SchemaLoader.ALL_SECTIONS
        assert "technical_and_performance_terms" in SchemaLoader.ALL_SECTIONS
        assert "legal_risk_and_enforcement" in SchemaLoader.ALL_SECTIONS
        assert "regulatory_and_compliance_terms" in SchemaLoader.ALL_SECTIONS
        assert "data_technology_and_deliverables" in SchemaLoader.ALL_SECTIONS
        assert "supplemental_operational_risks" in SchemaLoader.ALL_SECTIONS
        assert len(SchemaLoader.ALL_SECTIONS) == 7
    
    def test_required_sections_constant(self):
        """Test that REQUIRED_SECTIONS contains all required sections."""
        assert len(SchemaLoader.REQUIRED_SECTIONS) == 7
        for section in SchemaLoader.REQUIRED_SECTIONS:
            assert section in SchemaLoader.ALL_SECTIONS
