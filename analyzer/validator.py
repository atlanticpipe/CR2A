import json
import os
import re
import sys
from typing import Dict, Tuple

import jsonschema


def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller.
    
    Args:
        relative_path: Relative path to the resource file.
        
    Returns:
        Absolute path to the resource.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable - use PyInstaller's temp folder
        base_path = sys._MEIPASS
    else:
        # Running as script - use directory of this file
        base_path = os.path.dirname(__file__)
    
    return os.path.join(base_path, relative_path)


def load_schema() -> dict:
    schema_path = get_resource_path('config/output_schemas_v1.json')

    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_policy_rules() -> dict:
    policy_path = get_resource_path('config/validation_rules_v1.json')

    with open(policy_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_schema(json_data: dict) -> Tuple[bool, str]:
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