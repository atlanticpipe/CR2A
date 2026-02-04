"""
Schema Validator Module

This module provides validation functionality for API responses against the
output_schemas_v1.json schema. It includes dataclasses for representing
validation results and errors, as well as the SchemaValidator class for
performing validation.

Validates: Requirements 6.1, 6.2, 6.3, 6.5, 6.6, 6.7
"""

from dataclasses import dataclass, field
from typing import List, Any, Dict, Optional, TYPE_CHECKING

import jsonschema
from jsonschema import Draft202012Validator, Draft7Validator

if TYPE_CHECKING:
    from src.schema_loader import SchemaLoader


@dataclass
class ValidationError:
    """
    A specific validation error.
    
    Represents a single validation failure with information about where
    the error occurred and what went wrong.
    
    Attributes:
        path: JSON path to the field that failed validation (e.g., "contract_overview.general_risk_level")
        message: Human-readable description of the validation error
        value: The actual value that failed validation
    """
    path: str
    message: str
    value: Any
    
    def __str__(self) -> str:
        """Return a human-readable string representation of the error."""
        return f"ValidationError at '{self.path}': {self.message} (got: {self.value!r})"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation with path, message, and value
        """
        return {
            'path': self.path,
            'message': self.message,
            'value': self.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ValidationError':
        """
        Create a ValidationError from a dictionary.
        
        Args:
            data: Dictionary containing path, message, and value
            
        Returns:
            ValidationError instance
        """
        return cls(
            path=data['path'],
            message=data['message'],
            value=data.get('value')
        )


@dataclass
class ValidationResult:
    """
    Result of schema validation.
    
    Contains the overall validation status along with any errors and warnings
    that were encountered during validation.
    
    Attributes:
        is_valid: True if the response passed validation, False otherwise
        errors: List of validation errors that caused validation to fail
        warnings: List of warning messages for non-critical issues
    """
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def __str__(self) -> str:
        """Return a human-readable string representation of the result."""
        if self.is_valid:
            warning_count = len(self.warnings)
            if warning_count > 0:
                return f"ValidationResult: VALID with {warning_count} warning(s)"
            return "ValidationResult: VALID"
        else:
            error_count = len(self.errors)
            return f"ValidationResult: INVALID with {error_count} error(s)"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation with is_valid, errors, and warnings
        """
        return {
            'is_valid': self.is_valid,
            'errors': [error.to_dict() for error in self.errors],
            'warnings': self.warnings
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ValidationResult':
        """
        Create a ValidationResult from a dictionary.
        
        Args:
            data: Dictionary containing is_valid, errors, and warnings
            
        Returns:
            ValidationResult instance
        """
        errors = [
            ValidationError.from_dict(e) if isinstance(e, dict) else e
            for e in data.get('errors', [])
        ]
        return cls(
            is_valid=data['is_valid'],
            errors=errors,
            warnings=data.get('warnings', [])
        )
    
    def add_error(self, path: str, message: str, value: Any = None) -> None:
        """
        Add a validation error and mark the result as invalid.
        
        Args:
            path: JSON path to the field that failed validation
            message: Human-readable description of the error
            value: The actual value that failed validation
        """
        self.errors.append(ValidationError(path=path, message=message, value=value))
        self.is_valid = False
    
    def add_warning(self, message: str) -> None:
        """
        Add a warning message without affecting validity.
        
        Args:
            message: Human-readable warning message
        """
        self.warnings.append(message)
    
    def merge(self, other: 'ValidationResult') -> None:
        """
        Merge another ValidationResult into this one.
        
        Combines errors and warnings from both results. If either result
        is invalid, the merged result will be invalid.
        
        Args:
            other: Another ValidationResult to merge into this one
        """
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.is_valid:
            self.is_valid = False


class SchemaValidator:
    """
    Validates API responses against the output schema.
    
    This class uses the jsonschema library to validate API responses against
    the comprehensive output_schemas_v1.json schema. It provides methods for
    full response validation, single clause block validation, and enum field
    validation.
    
    Validates: Requirements 6.1, 6.2, 6.5, 6.6, 6.7
    
    Attributes:
        _schema_loader: SchemaLoader instance for loading the schema.
        _validator: Cached jsonschema validator instance.
        _enum_values: Cached enum values for validation.
    """
    
    # Valid enum values for each field type
    RISK_LEVEL_VALUES = ["Low", "Medium", "High", "Critical"]
    BID_MODEL_VALUES = ["Lump Sum", "Unit Price", "Cost Plus", "Time & Materials", "GMP", "Design-Build", "Other"]
    ACTION_VALUES = ["insert", "replace", "delete"]
    
    def __init__(self, schema_loader: 'SchemaLoader'):
        """
        Initialize the SchemaValidator.
        
        Args:
            schema_loader: SchemaLoader instance for loading the schema.
                The schema is loaded at initialization per Requirement 6.1.
        """
        self._schema_loader = schema_loader
        self._validator: Optional[jsonschema.Validator] = None
        self._schema: Optional[Dict[str, Any]] = None
        self._enum_values: Dict[str, List[str]] = {
            'risk_level': self.RISK_LEVEL_VALUES,
            'bid_model': self.BID_MODEL_VALUES,
            'action': self.ACTION_VALUES,
        }
        
        # Load schema at initialization (Requirement 6.1)
        self._initialize_validator()
    
    def _initialize_validator(self) -> None:
        """
        Initialize the jsonschema validator with the loaded schema.
        
        Loads the schema from the SchemaLoader and creates the appropriate
        validator based on the schema version.
        
        Raises:
            FileNotFoundError: If the schema file cannot be found.
            json.JSONDecodeError: If the schema file contains invalid JSON.
            ValueError: If the schema is missing required sections.
        """
        self._schema = self._schema_loader.load_schema()
        
        # Detect schema version and use appropriate validator
        schema_version = self._schema.get('$schema', '')
        
        if '2020-12' in schema_version:
            # Use Draft 2020-12 validator
            self._validator = Draft202012Validator(self._schema)
        elif 'draft-07' in schema_version or 'draft/7' in schema_version:
            # Use Draft 7 validator for backward compatibility
            self._validator = Draft7Validator(self._schema)
        else:
            # Default to Draft 2020-12 for newer schemas
            self._validator = Draft202012Validator(self._schema)
    
    def validate(self, response: Dict[str, Any]) -> ValidationResult:
        """
        Validate response against schema, returning detailed results.
        
        Validates the entire API response against the output_schemas_v1.json
        schema. Returns a ValidationResult containing all errors and warnings.
        
        Validates: Requirement 6.2
        
        Args:
            response: The API response dictionary to validate.
            
        Returns:
            ValidationResult with is_valid status, errors list, and warnings list.
        """
        result = ValidationResult(is_valid=True)
        
        if self._validator is None:
            result.add_error(
                path="",
                message="Schema validator not initialized",
                value=None
            )
            return result
        
        # Collect all validation errors
        errors = list(self._validator.iter_errors(response))
        
        for error in errors:
            # Build the path string from the error's absolute path
            path_parts = [str(part) for part in error.absolute_path]
            path = ".".join(path_parts) if path_parts else "root"
            
            # Get the value that caused the error
            value = error.instance
            
            # Add the error to the result
            result.add_error(
                path=path,
                message=error.message,
                value=value
            )
        
        # Add warnings for non-critical issues (e.g., empty arrays)
        self._add_warnings(response, result)
        
        return result
    
    def _add_warnings(self, response: Dict[str, Any], result: ValidationResult) -> None:
        """
        Add warnings for non-critical issues in the response.
        
        Args:
            response: The API response dictionary.
            result: The ValidationResult to add warnings to.
        """
        # Check for empty supplemental_operational_risks
        supplemental = response.get('supplemental_operational_risks', [])
        if isinstance(supplemental, list) and len(supplemental) == 0:
            result.add_warning("supplemental_operational_risks is empty")
        
        # Check for empty arrays in clause blocks
        sections_to_check = [
            'administrative_and_commercial_terms',
            'technical_and_performance_terms',
            'legal_risk_and_enforcement',
            'regulatory_and_compliance_terms',
            'data_technology_and_deliverables',
        ]
        
        for section_name in sections_to_check:
            section = response.get(section_name, {})
            if isinstance(section, dict):
                for clause_name, clause_block in section.items():
                    if isinstance(clause_block, dict):
                        # Check for empty redline recommendations
                        redlines = clause_block.get('Redline Recommendations', [])
                        if isinstance(redlines, list) and len(redlines) == 0:
                            result.add_warning(
                                f"{section_name}.{clause_name} has no redline recommendations"
                            )
    
    def validate_clause_block(self, block: Dict[str, Any]) -> List[str]:
        """
        Validate a single clause block, returning list of errors.
        
        Validates a ClauseBlock dictionary against the ClauseBlock schema
        definition from $defs.
        
        Args:
            block: The clause block dictionary to validate.
            
        Returns:
            List of error message strings. Empty list if valid.
        """
        errors: List[str] = []
        
        if not isinstance(block, dict):
            errors.append("Clause block must be a dictionary")
            return errors
        
        # Get the ClauseBlock schema from $defs
        clause_block_schema = self._schema_loader.get_clause_block_schema()
        
        # Create a validator for the ClauseBlock schema
        schema_version = self._schema.get('$schema', '') if self._schema else ''
        
        if '2020-12' in schema_version:
            validator = Draft202012Validator(clause_block_schema)
        else:
            validator = Draft7Validator(clause_block_schema)
        
        # Collect validation errors
        for error in validator.iter_errors(block):
            path_parts = [str(part) for part in error.absolute_path]
            path = ".".join(path_parts) if path_parts else "root"
            errors.append(f"{path}: {error.message}")
        
        # Additional validation for redline actions
        redlines = block.get('Redline Recommendations', [])
        if isinstance(redlines, list):
            for i, redline in enumerate(redlines):
                if isinstance(redline, dict):
                    action = redline.get('action')
                    if action and not self.validate_enum_field(action, 'action'):
                        errors.append(
                            f"Redline Recommendations[{i}].action: "
                            f"'{action}' is not a valid action. "
                            f"Must be one of: {', '.join(self.ACTION_VALUES)}"
                        )
        
        return errors
    
    def validate_enum_field(self, value: str, field_name: str) -> bool:
        """
        Validate enum fields like risk_level, bid_model, action.
        
        Validates that the given value is a valid enum value for the
        specified field type.
        
        Validates: Requirements 6.5, 6.6, 6.7
        
        Args:
            value: The value to validate.
            field_name: The field name ('risk_level', 'bid_model', or 'action').
            
        Returns:
            True if the value is valid for the field, False otherwise.
            
        Raises:
            ValueError: If the field_name is not recognized.
        """
        if field_name not in self._enum_values:
            raise ValueError(
                f"Unknown enum field: {field_name}. "
                f"Valid fields are: {', '.join(self._enum_values.keys())}"
            )
        
        valid_values = self._enum_values[field_name]
        return value in valid_values
    
    def get_valid_enum_values(self, field_name: str) -> List[str]:
        """
        Get the list of valid enum values for a field.
        
        Args:
            field_name: The field name ('risk_level', 'bid_model', or 'action').
            
        Returns:
            List of valid enum values for the field.
            
        Raises:
            ValueError: If the field_name is not recognized.
        """
        if field_name not in self._enum_values:
            raise ValueError(
                f"Unknown enum field: {field_name}. "
                f"Valid fields are: {', '.join(self._enum_values.keys())}"
            )
        
        return self._enum_values[field_name].copy()
