"""Schema Loader for loading and caching the output schema from configuration.

This module provides the SchemaLoader class that loads the comprehensive
8-section output schema from output_schemas_v1.json and provides methods
for extracting clause categories and generating prompt-friendly descriptions.
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Any


def get_resource_path(relative_path: str) -> Path:
    """Get absolute path to resource, works for dev and for PyInstaller.
    
    Args:
        relative_path: Relative path to the resource file.
        
    Returns:
        Absolute path to the resource.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable - use PyInstaller's temp folder
        base_path = Path(sys._MEIPASS)
    else:
        # Running as script - use project root
        base_path = Path(__file__).parent.parent
    
    return base_path / relative_path


class SchemaLoader:
    """Loads and caches the output schema from configuration.
    
    This class is responsible for loading the comprehensive output schema
    from the configuration file and providing methods to extract clause
    categories, generate prompt-friendly descriptions, and access schema
    definitions.
    
    Attributes:
        _schema_path: Path to the schema JSON file.
        _schema: Cached schema dictionary.
        _clause_categories: Cached clause categories organized by section.
    """
    
    # Section keys that contain clause blocks (excluding contract_overview and supplemental_operational_risks)
    CLAUSE_SECTIONS = [
        "administrative_and_commercial_terms",
        "technical_and_performance_terms",
        "legal_risk_and_enforcement",
        "regulatory_and_compliance_terms",
        "data_technology_and_deliverables",
    ]
    
    # All schema sections in order (based on what's defined in the schema properties)
    ALL_SECTIONS = [
        "contract_overview",
        "administrative_and_commercial_terms",
        "technical_and_performance_terms",
        "legal_risk_and_enforcement",
        "regulatory_and_compliance_terms",
        "data_technology_and_deliverables",
        "supplemental_operational_risks",
    ]
    
    # Minimum required sections for validation
    REQUIRED_SECTIONS = [
        "contract_overview",
        "administrative_and_commercial_terms",
        "technical_and_performance_terms",
        "legal_risk_and_enforcement",
        "regulatory_and_compliance_terms",
        "data_technology_and_deliverables",
        "supplemental_operational_risks",
    ]
    
    def __init__(self, schema_path: str = "config/output_schemas_v1.json"):
        """Initialize the SchemaLoader.
        
        Args:
            schema_path: Path to the schema JSON file. Defaults to
                config/output_schemas_v1.json.
        """
        self._schema_path = schema_path
        self._schema: Optional[Dict[str, Any]] = None
        self._clause_categories: Optional[Dict[str, List[str]]] = None
    
    def load_schema(self) -> Dict[str, Any]:
        """Load schema from file, caching for subsequent calls.
        
        Returns:
            The parsed schema dictionary.
            
        Raises:
            FileNotFoundError: If the schema file does not exist.
            json.JSONDecodeError: If the schema file contains invalid JSON.
            ValueError: If the schema is missing required sections.
        """
        if self._schema is not None:
            return self._schema
        
        # Use resource path helper to handle both dev and PyInstaller environments
        schema_path = get_resource_path(self._schema_path)
        
        if not schema_path.exists():
            raise FileNotFoundError(
                f"Schema file not found: {self._schema_path} (resolved to: {schema_path})"
            )
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            self._schema = json.load(f)
        
        # Validate required sections exist
        self._validate_schema_structure()
        
        return self._schema
    
    def _validate_schema_structure(self) -> None:
        """Validate that the schema has required sections.
        
        Raises:
            ValueError: If required sections are missing.
        """
        if self._schema is None:
            return
        
        properties = self._schema.get("properties", {})
        missing_sections = []
        
        for section in self.REQUIRED_SECTIONS:
            if section not in properties:
                missing_sections.append(section)
        
        if missing_sections:
            raise ValueError(
                f"Schema missing required sections: {', '.join(missing_sections)}"
            )
        
        # Validate $defs contains ClauseBlock
        defs = self._schema.get("$defs", {})
        if "ClauseBlock" not in defs:
            raise ValueError("Schema missing ClauseBlock definition in $defs")
    
    def get_clause_categories(self) -> Dict[str, List[str]]:
        """Extract clause category names organized by section.
        
        Returns:
            A dictionary mapping section names to lists of clause category names.
            For example:
            {
                "administrative_and_commercial_terms": [
                    "Contract Term, Renewal & Extensions",
                    "Bonding, Surety, & Insurance Obligations",
                    ...
                ],
                ...
            }
        """
        if self._clause_categories is not None:
            return self._clause_categories
        
        schema = self.load_schema()
        self._clause_categories = {}
        
        properties = schema.get("properties", {})
        
        for section_name in self.CLAUSE_SECTIONS:
            section_schema = properties.get(section_name, {})
            section_properties = section_schema.get("properties", {})
            
            # Extract category names (keys of the section properties)
            categories = list(section_properties.keys())
            self._clause_categories[section_name] = categories
        
        # Handle supplemental_operational_risks separately (it's an array)
        self._clause_categories["supplemental_operational_risks"] = []
        
        return self._clause_categories
    
    def get_schema_for_prompt(self) -> str:
        """Generate schema description suitable for AI prompt.
        
        Returns:
            A formatted string describing the schema structure that can be
            included in AI prompts to guide response generation.
        """
        schema = self.load_schema()
        clause_categories = self.get_clause_categories()
        clause_block_schema = self.get_clause_block_schema()
        
        lines = [
            "# Output Schema Structure",
            "",
            "Your response must be valid JSON matching the following structure:",
            "",
            "## Schema Version",
            "- schema_version: string matching pattern ^v1\\.\\d+\\.\\d+$ (e.g., 'v1.0.0')",
            "",
            "## Section I: Contract Overview",
            "Required fields:",
            "- Project Title: string (required)",
            "- Solicitation No.: string",
            "- Owner: string (required)",
            "- Contractor: string (required)",
            "- Scope: string (required)",
            "- General Risk Level: one of ['Low', 'Medium', 'High', 'Critical']",
            "- Bid Model: one of ['Lump Sum', 'Unit Price', 'Cost Plus', 'Time & Materials', 'GMP', 'Design-Build', 'Other']",
            "- Notes: string",
            "",
        ]
        
        # Add ClauseBlock structure
        lines.extend([
            "## ClauseBlock Structure",
            "Each clause category uses this structure:",
            "```json",
            "{",
            '  "Clause Language": "Verbatim or quoted clause text",',
            '  "Clause Summary": "Plain-English summary of the clause",',
            '  "Risk Triggers Identified": ["list", "of", "risk", "triggers"],',
            '  "Flow-Down Obligations": ["list", "of", "obligations"],',
            '  "Redline Recommendations": [',
            '    {',
            '      "action": "insert|replace|delete",',
            '      "text": "recommendation text",',
            '      "reference": "optional citation"',
            '    }',
            '  ],',
            '  "Harmful Language / Policy Conflicts": ["list", "of", "conflicts"]',
            "}",
            "```",
            "",
        ])
        
        # Add section descriptions with clause categories
        section_titles = {
            "administrative_and_commercial_terms": "Section II: Administrative & Commercial Terms",
            "technical_and_performance_terms": "Section III: Technical & Performance Terms",
            "legal_risk_and_enforcement": "Section IV: Legal Risk & Enforcement",
            "regulatory_and_compliance_terms": "Section V: Regulatory & Compliance Terms",
            "data_technology_and_deliverables": "Section VI: Data, Technology & Deliverables",
        }
        
        for section_name, title in section_titles.items():
            categories = clause_categories.get(section_name, [])
            lines.append(f"## {title}")
            lines.append(f"Clause categories ({len(categories)} total):")
            for category in categories:
                lines.append(f"- {category}")
            lines.append("")
        
        # Add supplemental operational risks
        lines.extend([
            "## Section VII: Supplemental Operational Risks",
            "An array of up to 9 ClauseBlock entries for additional risks not covered above.",
            "",
            "## Important Notes",
            "- Only include clause categories that are found in the contract",
            "- Omit clause categories that are not present (do not include empty values)",
            "- All ClauseBlock fields are required when a clause is included",
            "- Redline action must be one of: 'insert', 'replace', 'delete'",
        ])
        
        return "\n".join(lines)
    
    def get_clause_block_schema(self) -> Dict[str, Any]:
        """Return the ClauseBlock definition from $defs.
        
        Returns:
            The ClauseBlock schema definition dictionary.
            
        Raises:
            ValueError: If the schema has not been loaded or ClauseBlock
                is not defined.
        """
        schema = self.load_schema()
        
        defs = schema.get("$defs", {})
        clause_block = defs.get("ClauseBlock")
        
        if clause_block is None:
            raise ValueError("ClauseBlock definition not found in schema $defs")
        
        return clause_block
    
    def get_section_schema(self, section_name: str) -> Optional[Dict[str, Any]]:
        """Get the schema definition for a specific section.
        
        Args:
            section_name: The name of the section (e.g., 'administrative_and_commercial_terms').
            
        Returns:
            The section schema definition, or None if not found.
        """
        schema = self.load_schema()
        properties = schema.get("properties", {})
        return properties.get(section_name)
    
    def get_contract_overview_schema(self) -> Dict[str, Any]:
        """Get the contract_overview section schema.
        
        Returns:
            The contract_overview schema definition.
        """
        schema = self.load_schema()
        return schema.get("properties", {}).get("contract_overview", {})
    
    def get_enum_values(self, field_name: str) -> List[str]:
        """Get valid enum values for a specific field.
        
        Args:
            field_name: The field name ('risk_level', 'bid_model', or 'action').
            
        Returns:
            List of valid enum values for the field.
            
        Raises:
            ValueError: If the field name is not recognized.
        """
        schema = self.load_schema()
        
        if field_name == "risk_level":
            overview = schema.get("properties", {}).get("contract_overview", {})
            risk_level = overview.get("properties", {}).get("General Risk Level", {})
            return risk_level.get("enum", [])
        
        elif field_name == "bid_model":
            overview = schema.get("properties", {}).get("contract_overview", {})
            bid_model = overview.get("properties", {}).get("Bid Model", {})
            return bid_model.get("enum", [])
        
        elif field_name == "action":
            clause_block = self.get_clause_block_schema()
            redline_props = clause_block.get("properties", {}).get("Redline Recommendations", {})
            items = redline_props.get("items", {})
            action_prop = items.get("properties", {}).get("action", {})
            return action_prop.get("enum", [])
        
        else:
            raise ValueError(f"Unknown enum field: {field_name}")
