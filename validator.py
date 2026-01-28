"""
JSON Schema and Policy Validator for Contract Analysis Results

This module provides comprehensive validation for contract analysis output,
enforcing both JSON schema compliance and company-specific policy rules.
"""

import json
import os
import re
from typing import Dict, Tuple

import jsonschema


def load_schema() -> dict:
    """
    Load the JSON schema file for contract analysis validation.

    Returns:
        dict: The loaded JSON schema

    Raises:
        FileNotFoundError: If schema file doesn't exist
        json.JSONDecodeError: If schema file contains invalid JSON
    """
    schema_path = os.path.join(os.path.dirname(__file__), 'output_schemas_v1.json')

    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_policy_rules() -> dict:
    """
    Load the company policy validation rules.

    Returns:
        dict: The loaded policy rules

    Raises:
        FileNotFoundError: If policy file doesn't exist
        json.JSONDecodeError: If policy file contains invalid JSON
    """
    policy_path = os.path.join(os.path.dirname(__file__), 'validation_rules_v1.json')

    with open(policy_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_schema(json_data: dict) -> Tuple[bool, str]:
    """
    Validate JSON data against the contract analysis schema using Draft 2020-12.

    Args:
        json_data: The JSON data to validate

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
        - is_valid: True if validation passes, False otherwise
        - error_message: Empty string if valid, first error message if invalid
    """
    try:
        schema = load_schema()
        
        # Detect schema version and use appropriate validator
        schema_version = schema.get('$schema', '')
        
        if '2020-12' in schema_version:
            # Use Draft 2020-12 validator
            jsonschema.Draft202012Validator.check_schema(schema)
            validator = jsonschema.Draft202012Validator(schema)
        elif 'draft-07' in schema_version or 'draft/7' in schema_version:
            # Use Draft 7 validator for backward compatibility
            jsonschema.Draft7Validator.check_schema(schema)
            validator = jsonschema.Draft7Validator(schema)
        else:
            # Default to Draft 7 for backward compatibility
            jsonschema.Draft7Validator.check_schema(schema)
            validator = jsonschema.Draft7Validator(schema)
        
        errors = list(validator.iter_errors(json_data))

        if errors:
            # Return the first error message for fail-fast behavior
            first_error = errors[0]
            error_path = " -> ".join(str(part) for part in first_error.absolute_path) or "root"
            error_message = f"Schema validation failed: {first_error.message} at {error_path}"
            return False, error_message

        return True, ""

    except jsonschema.SchemaError as e:
        return False, f"Schema validation failed: Invalid schema definition - {str(e)}"
    except Exception as e:
        return False, f"Schema validation failed: Unexpected error - {str(e)}"


def validate_policy_rules(json_data: dict) -> Tuple[bool, str]:
    """
    Apply company-specific policy validation rules to the JSON data.

    Args:
        json_data: The validated JSON data to check against policy rules

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
        - is_valid: True if all policy rules pass, False otherwise
        - error_message: Empty string if valid, first error message if invalid
    """
    try:
        policy_rules = load_policy_rules()
        validation_config = policy_rules.get('validation', {})

        # Validate strict header requirements
        if validation_config.get('strict_string_match_headers', False):
            required_headers = validation_config.get('strict_headers', {}).get('headers', [])
            missing_headers = []

            for header in required_headers:
                if header not in json_data:
                    missing_headers.append(header)

            if missing_headers:
                return False, f"Policy validation failed: Missing required headers: {', '.join(missing_headers)}"

        # Validate mandatory field counts
        mandatory_fields = validation_config.get('mandatory_fields', {})
        if 'contract_overview_count' in mandatory_fields:
            expected_count = mandatory_fields['contract_overview_count']
            contract_overview = json_data.get('contract_overview', {})

            if len(contract_overview) != expected_count:
                return False, f"Policy validation failed: Contract overview must have exactly {expected_count} fields, found {len(contract_overview)}"

        # Validate clause requirements (at least one redline per clause)
        clause_requirements = validation_config.get('clause_requirements', {})
        if clause_requirements.get('min_one_redline', False):
            sections_with_clauses = [
                'administrative_and_commercial_terms',
                'technical_and_performance_terms',
                'legal_risk_and_enforcement',
                'regulatory_and_compliance_terms',
                'data_technology_and_deliverables'
            ]

            for section_name in sections_with_clauses:
                section_data = json_data.get(section_name, {})

                for clause_key, clause_data in section_data.items():
                    if not isinstance(clause_data, dict):
                        continue

                    redlines = clause_data.get('Redline Recommendations', [])
                    if not redlines:
                        return False, f"Policy validation failed: Clause '{clause_key}' must have at least one redline recommendation"

        return True, ""

    except Exception as e:
        return False, f"Policy validation failed: Unexpected error - {str(e)}"


def validate_analysis_result(json_data: dict) -> Tuple[bool, str]:
    """
    Main validation function that performs both schema and policy validation.

    This function implements fail-fast validation - it returns immediately
    on the first validation failure with a clear error message.

    Args:
        json_data: The JSON data to validate

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
        - is_valid: True if both schema and policy validation pass
        - error_message: Empty string if valid, first error message if invalid
    """
    # First validate against JSON schema
    is_valid, error_message = validate_schema(json_data)
    if not is_valid:
        return False, error_message

    # Then validate against company policy rules
    is_valid, error_message = validate_policy_rules(json_data)
    if not is_valid:
        return False, error_message

    # All validations passed
    return True, ""