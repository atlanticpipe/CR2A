#!/usr/bin/env python3
"""
Unit tests for validator.py module

Tests JSON schema validation and policy rule checking.
"""

import unittest
import os
import json
from pathlib import Path
import sys

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import validator


class TestValidatorModule(unittest.TestCase):
    """Test cases for validator module"""
    
    def test_load_schema(self):
        """Test that schema file can be loaded"""
        try:
            schema = validator.load_schema()
            self.assertIsInstance(schema, dict, "Schema should be a dictionary")
            self.assertIn('$schema', schema, "Schema should have $schema field")
            self.assertIn('required', schema, "Schema should have required field")
        except FileNotFoundError:
            self.skipTest("Schema file not found - expected in parent directory")
    
    def test_load_policy_rules(self):
        """Test that policy rules file can be loaded"""
        try:
            rules = validator.load_policy_rules()
            self.assertIsInstance(rules, dict, "Rules should be a dictionary")
            self.assertIn('validation', rules, "Rules should have validation field")
        except FileNotFoundError:
            self.skipTest("Policy rules file not found - expected in parent directory")
    
    def test_validate_schema_with_valid_data(self):
        """Test schema validation with valid data structure"""
        valid_data = {
            "schema_version": "v1.0",
            "contract_overview": {
                "Project Title": "Test Project",
                "Solicitation No.": "TEST-001",
                "Owner": "Test Owner",
                "Contractor": "Test Contractor",
                "Scope": "Test Scope",
                "General Risk Level": "Low",
                "Bid Model": "Test Model",
                "Notes": "Test Notes"
            },
            "administrative_and_commercial_terms": {},
            "technical_and_performance_terms": {},
            "legal_risk_and_enforcement": {},
            "regulatory_and_compliance_terms": {},
            "data_technology_and_deliverables": {},
            "supplemental_operational_risks": [],
            "final_analysis": {
                "summary": []
            }
        }
        
        try:
            is_valid, error_msg = validator.validate_schema(valid_data)
            self.assertTrue(is_valid, f"Valid data should pass validation: {error_msg}")
        except FileNotFoundError:
            self.skipTest("Schema file not found")
    
    def test_validate_schema_with_invalid_data(self):
        """Test schema validation with invalid data structure"""
        invalid_data = {
            "schema_version": "v1.0"
            # Missing required fields
        }
        
        try:
            is_valid, error_msg = validator.validate_schema(invalid_data)
            self.assertFalse(is_valid, "Invalid data should fail validation")
            self.assertIsInstance(error_msg, str, "Error message should be a string")
            self.assertTrue(len(error_msg) > 0, "Error message should not be empty")
        except FileNotFoundError:
            self.skipTest("Schema file not found")


if __name__ == '__main__':
    unittest.main()
