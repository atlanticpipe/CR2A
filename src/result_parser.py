"""
Result Parser Module

Handles parsing and validation of OpenAI API responses into AnalysisResult objects.
Provides robust handling of partial or malformed responses.

Supports both legacy simplified schema (AnalysisResult) and comprehensive 8-section
schema (ComprehensiveAnalysisResult).
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Type, TypeVar
from src.analysis_models import (
    AnalysisResult,
    ContractMetadata,
    Clause,
    Risk,
    ComplianceIssue,
    RedliningSuggestion,
    # Comprehensive schema models
    ComprehensiveAnalysisResult,
    ContractOverview,
    ClauseBlock,
    RedlineRecommendation,
    AdministrativeAndCommercialTerms,
    TechnicalAndPerformanceTerms,
    LegalRiskAndEnforcement,
    RegulatoryAndComplianceTerms,
    DataTechnologyAndDeliverables,
)
from src.schema_validator import SchemaValidator


logger = logging.getLogger(__name__)


class ResultParser:
    """
    Parses OpenAI API JSON responses into AnalysisResult objects.
    
    This class handles:
    - Parsing structured JSON responses
    - Validating required fields
    - Handling partial or malformed responses
    - Providing default values for missing fields
    """
    
    def __init__(self):
        """Initialize the result parser."""
        logger.debug("ResultParser initialized")
    
    def parse_api_response(
        self,
        api_response: Dict[str, Any],
        filename: str,
        file_size_bytes: int,
        page_count: Optional[int] = None
    ) -> AnalysisResult:
        """
        Parse OpenAI API JSON response into AnalysisResult.
        
        Args:
            api_response: JSON response from OpenAI API
            filename: Name of the analyzed contract file
            file_size_bytes: Size of the file in bytes
            page_count: Number of pages (optional)
        
        Returns:
            AnalysisResult object
        
        Raises:
            ValueError: If response is invalid or missing critical fields
        """
        logger.info("Parsing API response for file: %s", filename)
        
        try:
            # Create metadata
            metadata = self._parse_metadata(
                api_response,
                filename,
                file_size_bytes,
                page_count
            )
            
            # Parse clauses
            clauses = self._parse_clauses(api_response)
            logger.debug("Parsed %d clauses", len(clauses))
            
            # Parse risks
            risks = self._parse_risks(api_response)
            logger.debug("Parsed %d risks", len(risks))
            
            # Parse compliance issues
            compliance_issues = self._parse_compliance_issues(api_response)
            logger.debug("Parsed %d compliance issues", len(compliance_issues))
            
            # Parse redlining suggestions
            redlining_suggestions = self._parse_redlining_suggestions(api_response)
            logger.debug("Parsed %d redlining suggestions", len(redlining_suggestions))
            
            # Create analysis result
            result = AnalysisResult(
                metadata=metadata,
                clauses=clauses,
                risks=risks,
                compliance_issues=compliance_issues,
                redlining_suggestions=redlining_suggestions
            )
            
            # Validate the result
            if not result.validate_result():
                logger.warning("Analysis result validation failed, but continuing with partial result")
            
            logger.info("Successfully parsed analysis result")
            return result
            
        except Exception as e:
            logger.error("Failed to parse API response: %s", e, exc_info=True)
            raise ValueError(f"Failed to parse analysis result: {str(e)}") from e
    
    def _parse_metadata(
        self,
        api_response: Dict[str, Any],
        filename: str,
        file_size_bytes: int,
        page_count: Optional[int]
    ) -> ContractMetadata:
        """
        Parse contract metadata from API response.
        
        Args:
            api_response: API response dictionary
            filename: Contract filename
            file_size_bytes: File size in bytes
            page_count: Number of pages (optional)
        
        Returns:
            ContractMetadata object
        """
        # Try to get page count from API response if not provided
        if page_count is None:
            metadata_dict = api_response.get('contract_metadata', {})
            page_count = metadata_dict.get('page_count', 0)
        
        # Ensure page_count is at least 1 if we have a file
        if page_count == 0 and file_size_bytes > 0:
            page_count = 1
        
        return ContractMetadata(
            filename=filename,
            analyzed_at=datetime.now(),
            page_count=page_count,
            file_size_bytes=file_size_bytes
        )
    
    def _parse_clauses(self, api_response: Dict[str, Any]) -> List[Clause]:
        """
        Parse clauses from API response.
        
        Args:
            api_response: API response dictionary
        
        Returns:
            List of Clause objects
        """
        clauses = []
        clauses_data = api_response.get('clauses', [])
        
        if not isinstance(clauses_data, list):
            logger.warning("Clauses field is not a list, skipping")
            return clauses
        
        for idx, clause_data in enumerate(clauses_data):
            try:
                clause = self._parse_single_clause(clause_data, idx)
                if clause:
                    clauses.append(clause)
            except Exception as e:
                logger.warning("Failed to parse clause %d: %s", idx, e)
                continue
        
        return clauses
    
    def _parse_single_clause(
        self,
        clause_data: Dict[str, Any],
        index: int
    ) -> Optional[Clause]:
        """
        Parse a single clause from data.
        
        Args:
            clause_data: Clause data dictionary
            index: Index of the clause (for generating default ID)
        
        Returns:
            Clause object or None if parsing fails
        """
        if not isinstance(clause_data, dict):
            return None
        
        # Extract fields with defaults
        clause_id = clause_data.get('id', f'clause_{index + 1}')
        clause_type = clause_data.get('type', 'unknown')
        text = clause_data.get('text', '')
        page = clause_data.get('page', 0)
        risk_level = clause_data.get('risk_level', 'low')
        
        # Validate risk level
        if risk_level not in ['low', 'medium', 'high']:
            logger.warning("Invalid risk level '%s' for clause %s, defaulting to 'low'", 
                         risk_level, clause_id)
            risk_level = 'low'
        
        # Skip clauses with no text
        if not text:
            logger.warning("Skipping clause %s with empty text", clause_id)
            return None
        
        return Clause(
            id=clause_id,
            type=clause_type,
            text=text,
            page=page,
            risk_level=risk_level
        )
    
    def _parse_risks(self, api_response: Dict[str, Any]) -> List[Risk]:
        """
        Parse risks from API response.
        
        Args:
            api_response: API response dictionary
        
        Returns:
            List of Risk objects
        """
        risks = []
        risks_data = api_response.get('risks', [])
        
        if not isinstance(risks_data, list):
            logger.warning("Risks field is not a list, skipping")
            return risks
        
        for idx, risk_data in enumerate(risks_data):
            try:
                risk = self._parse_single_risk(risk_data, idx)
                if risk:
                    risks.append(risk)
            except Exception as e:
                logger.warning("Failed to parse risk %d: %s", idx, e)
                continue
        
        return risks
    
    def _parse_single_risk(
        self,
        risk_data: Dict[str, Any],
        index: int
    ) -> Optional[Risk]:
        """
        Parse a single risk from data.
        
        Args:
            risk_data: Risk data dictionary
            index: Index of the risk (for generating default ID)
        
        Returns:
            Risk object or None if parsing fails
        """
        if not isinstance(risk_data, dict):
            return None
        
        # Extract fields with defaults
        risk_id = risk_data.get('id', f'risk_{index + 1}')
        clause_id = risk_data.get('clause_id', '')
        severity = risk_data.get('severity', 'low')
        description = risk_data.get('description', '')
        recommendation = risk_data.get('recommendation', '')
        
        # Validate severity
        if severity not in ['low', 'medium', 'high', 'critical']:
            logger.warning("Invalid severity '%s' for risk %s, defaulting to 'low'", 
                         severity, risk_id)
            severity = 'low'
        
        # Skip risks with no description
        if not description:
            logger.warning("Skipping risk %s with empty description", risk_id)
            return None
        
        return Risk(
            id=risk_id,
            clause_id=clause_id,
            severity=severity,
            description=description,
            recommendation=recommendation
        )
    
    def _parse_compliance_issues(self, api_response: Dict[str, Any]) -> List[ComplianceIssue]:
        """
        Parse compliance issues from API response.
        
        Args:
            api_response: API response dictionary
        
        Returns:
            List of ComplianceIssue objects
        """
        compliance_issues = []
        issues_data = api_response.get('compliance_issues', [])
        
        if not isinstance(issues_data, list):
            logger.warning("Compliance issues field is not a list, skipping")
            return compliance_issues
        
        for idx, issue_data in enumerate(issues_data):
            try:
                issue = self._parse_single_compliance_issue(issue_data, idx)
                if issue:
                    compliance_issues.append(issue)
            except Exception as e:
                logger.warning("Failed to parse compliance issue %d: %s", idx, e)
                continue
        
        return compliance_issues
    
    def _parse_single_compliance_issue(
        self,
        issue_data: Dict[str, Any],
        index: int
    ) -> Optional[ComplianceIssue]:
        """
        Parse a single compliance issue from data.
        
        Args:
            issue_data: Compliance issue data dictionary
            index: Index of the issue (for generating default ID)
        
        Returns:
            ComplianceIssue object or None if parsing fails
        """
        if not isinstance(issue_data, dict):
            return None
        
        # Extract fields with defaults
        issue_id = issue_data.get('id', f'compliance_{index + 1}')
        regulation = issue_data.get('regulation', 'Unknown')
        issue = issue_data.get('issue', '')
        severity = issue_data.get('severity', 'low')
        
        # Validate severity
        if severity not in ['low', 'medium', 'high']:
            logger.warning("Invalid severity '%s' for compliance issue %s, defaulting to 'low'", 
                         severity, issue_id)
            severity = 'low'
        
        # Skip issues with no description
        if not issue:
            logger.warning("Skipping compliance issue %s with empty description", issue_id)
            return None
        
        return ComplianceIssue(
            id=issue_id,
            regulation=regulation,
            issue=issue,
            severity=severity
        )
    
    def _parse_redlining_suggestions(self, api_response: Dict[str, Any]) -> List[RedliningSuggestion]:
        """
        Parse redlining suggestions from API response.
        
        Args:
            api_response: API response dictionary
        
        Returns:
            List of RedliningSuggestion objects
        """
        suggestions = []
        suggestions_data = api_response.get('redlining_suggestions', [])
        
        if not isinstance(suggestions_data, list):
            logger.warning("Redlining suggestions field is not a list, skipping")
            return suggestions
        
        for idx, suggestion_data in enumerate(suggestions_data):
            try:
                suggestion = self._parse_single_redlining_suggestion(suggestion_data, idx)
                if suggestion:
                    suggestions.append(suggestion)
            except Exception as e:
                logger.warning("Failed to parse redlining suggestion %d: %s", idx, e)
                continue
        
        return suggestions
    
    def _parse_single_redlining_suggestion(
        self,
        suggestion_data: Dict[str, Any],
        index: int
    ) -> Optional[RedliningSuggestion]:
        """
        Parse a single redlining suggestion from data.
        
        Args:
            suggestion_data: Redlining suggestion data dictionary
            index: Index of the suggestion
        
        Returns:
            RedliningSuggestion object or None if parsing fails
        """
        if not isinstance(suggestion_data, dict):
            return None
        
        # Extract fields
        clause_id = suggestion_data.get('clause_id', '')
        original_text = suggestion_data.get('original_text', '')
        suggested_text = suggestion_data.get('suggested_text', '')
        rationale = suggestion_data.get('rationale', '')
        
        # Skip suggestions with missing required fields
        if not clause_id or not original_text or not suggested_text:
            logger.warning("Skipping redlining suggestion %d with missing required fields", index)
            return None
        
        return RedliningSuggestion(
            clause_id=clause_id,
            original_text=original_text,
            suggested_text=suggested_text,
            rationale=rationale
        )


# Type variable for section classes
T = TypeVar('T')


class ComprehensiveResultParser:
    """
    Parses API responses into ComprehensiveAnalysisResult objects.
    
    This class handles parsing of the comprehensive 8-section schema responses
    from the OpenAI API. It validates responses against the schema and converts
    them into strongly-typed Python dataclass objects.
    
    Validates: Requirements 4.1, 4.2
    
    Attributes:
        _validator: SchemaValidator instance for validating API responses.
    """
    
    # Mapping of section names to their dataclass types
    SECTION_CLASSES: Dict[str, Type] = {
        'administrative_and_commercial_terms': AdministrativeAndCommercialTerms,
        'technical_and_performance_terms': TechnicalAndPerformanceTerms,
        'legal_risk_and_enforcement': LegalRiskAndEnforcement,
        'regulatory_and_compliance_terms': RegulatoryAndComplianceTerms,
        'data_technology_and_deliverables': DataTechnologyAndDeliverables,
    }
    
    def __init__(self, schema_validator: SchemaValidator):
        """
        Initialize the ComprehensiveResultParser.
        
        Args:
            schema_validator: SchemaValidator instance for validating API responses.
        """
        self._validator = schema_validator
        logger.debug("ComprehensiveResultParser initialized with SchemaValidator")
    
    @staticmethod
    def detect_schema_format(data: Dict[str, Any]) -> str:
        """
        Detect whether data uses legacy or comprehensive schema format.
        
        Validates: Requirement 7.1
        
        This method identifies the schema format by checking for:
        1. Presence of schema_version field (comprehensive format)
        2. Presence of comprehensive section structure (contract_overview, 
           administrative_and_commercial_terms, etc.)
        3. Presence of legacy structure (clauses, risks, compliance_issues, 
           redlining_suggestions)
        
        Args:
            data: Dictionary containing analysis result data
        
        Returns:
            "comprehensive" if data uses the new 8-section schema,
            "legacy" if data uses the old simplified schema,
            "unknown" if format cannot be determined
        """
        # Check for schema_version field (strong indicator of comprehensive format)
        if 'schema_version' in data:
            logger.debug("Detected comprehensive format: schema_version field present")
            return "comprehensive"
        
        # Check for comprehensive section structure
        comprehensive_sections = [
            'contract_overview',
            'administrative_and_commercial_terms',
            'technical_and_performance_terms',
            'legal_risk_and_enforcement',
            'regulatory_and_compliance_terms',
            'data_technology_and_deliverables',
            'supplemental_operational_risks'
        ]
        
        # Count how many comprehensive sections are present
        comprehensive_count = sum(1 for section in comprehensive_sections if section in data)
        
        # If we have at least 3 comprehensive sections, it's likely comprehensive format
        if comprehensive_count >= 3:
            logger.debug("Detected comprehensive format: %d comprehensive sections found", 
                        comprehensive_count)
            return "comprehensive"
        
        # Check for legacy structure
        legacy_fields = ['clauses', 'risks', 'compliance_issues', 'redlining_suggestions']
        legacy_count = sum(1 for field in legacy_fields if field in data)
        
        # If we have at least 2 legacy fields, it's likely legacy format
        if legacy_count >= 2:
            logger.debug("Detected legacy format: %d legacy fields found", legacy_count)
            return "legacy"
        
        # Check for contract_metadata (legacy) vs metadata (comprehensive)
        if 'contract_metadata' in data:
            logger.debug("Detected legacy format: contract_metadata field present")
            return "legacy"
        
        # Cannot determine format
        logger.warning("Unable to determine schema format from data keys: %s", list(data.keys()))
        return "unknown"
    
    def parse_api_response(
        self,
        api_response: Dict[str, Any],
        filename: str,
        file_size_bytes: int,
        page_count: Optional[int] = None
    ) -> ComprehensiveAnalysisResult:
        """
        Parse and validate API response into ComprehensiveAnalysisResult object.
        
        This method parses the comprehensive 8-section schema response from the
        OpenAI API into a strongly-typed ComprehensiveAnalysisResult object.
        
        Validates: Requirements 4.1, 4.2, 6.2, 6.4
        
        Args:
            api_response: JSON response from OpenAI API matching output_schemas_v1.json
            filename: Name of the analyzed contract file
            file_size_bytes: Size of the file in bytes
            page_count: Number of pages (optional)
        
        Returns:
            ComprehensiveAnalysisResult object with all sections populated
        
        Raises:
            ValueError: If response is invalid or missing critical fields
        """
        logger.info("Parsing comprehensive API response for file: %s", filename)
        
        try:
            # Validate the response against the schema (Requirement 6.2)
            logger.debug("Validating API response against schema")
            validation_result = self._validator.validate(api_response)
            
            if not validation_result.is_valid:
                # Log validation errors (Requirement 6.2)
                logger.warning("Schema validation failed with %d error(s)", len(validation_result.errors))
                for error in validation_result.errors:
                    logger.warning("Validation error at '%s': %s (value: %s)", 
                                 error.path, error.message, error.value)
                
                # Continue processing on non-critical failures (Requirement 6.4)
                logger.info("Continuing with best-effort parsing despite validation errors")
            else:
                logger.debug("Schema validation passed successfully")
            
            # Log any warnings (Requirement 6.2)
            if validation_result.warnings:
                logger.debug("Schema validation produced %d warning(s)", len(validation_result.warnings))
                for warning in validation_result.warnings:
                    logger.debug("Validation warning: %s", warning)
            
            # Parse schema version
            schema_version = api_response.get('schema_version', 'v1.0.0')
            logger.debug("Schema version: %s", schema_version)
            
            # Parse Section I: Contract Overview (Requirement 4.1)
            contract_overview = self._parse_contract_overview(
                api_response.get('contract_overview', {})
            )
            logger.debug("Parsed contract overview")
            
            # Parse Section II-VI: Clause sections (Requirement 4.2)
            administrative_and_commercial_terms = self._parse_section(
                api_response.get('administrative_and_commercial_terms', {}),
                AdministrativeAndCommercialTerms
            )
            logger.debug("Parsed administrative_and_commercial_terms")
            
            technical_and_performance_terms = self._parse_section(
                api_response.get('technical_and_performance_terms', {}),
                TechnicalAndPerformanceTerms
            )
            logger.debug("Parsed technical_and_performance_terms")
            
            legal_risk_and_enforcement = self._parse_section(
                api_response.get('legal_risk_and_enforcement', {}),
                LegalRiskAndEnforcement
            )
            logger.debug("Parsed legal_risk_and_enforcement")
            
            regulatory_and_compliance_terms = self._parse_section(
                api_response.get('regulatory_and_compliance_terms', {}),
                RegulatoryAndComplianceTerms
            )
            logger.debug("Parsed regulatory_and_compliance_terms")
            
            data_technology_and_deliverables = self._parse_section(
                api_response.get('data_technology_and_deliverables', {}),
                DataTechnologyAndDeliverables
            )
            logger.debug("Parsed data_technology_and_deliverables")
            
            # Parse Section VII: Supplemental Operational Risks (list of ClauseBlocks)
            supplemental_operational_risks = self._parse_supplemental_risks(
                api_response.get('supplemental_operational_risks', [])
            )
            logger.debug("Parsed %d supplemental operational risks", len(supplemental_operational_risks))
            
            # Create metadata
            metadata = self._create_metadata(
                api_response,
                filename,
                file_size_bytes,
                page_count
            )
            
            # Create the comprehensive result
            result = ComprehensiveAnalysisResult(
                schema_version=schema_version,
                contract_overview=contract_overview,
                administrative_and_commercial_terms=administrative_and_commercial_terms,
                technical_and_performance_terms=technical_and_performance_terms,
                legal_risk_and_enforcement=legal_risk_and_enforcement,
                regulatory_and_compliance_terms=regulatory_and_compliance_terms,
                data_technology_and_deliverables=data_technology_and_deliverables,
                supplemental_operational_risks=supplemental_operational_risks,
                metadata=metadata
            )
            
            # Validate the result
            if not result.validate():
                logger.warning("ComprehensiveAnalysisResult validation failed, but continuing with partial result")
            
            logger.info("Successfully parsed comprehensive analysis result")
            return result
            
        except Exception as e:
            logger.error("Failed to parse comprehensive API response: %s", e, exc_info=True)
            raise ValueError(f"Failed to parse comprehensive analysis result: {str(e)}") from e
    
    def _parse_contract_overview(self, data: Dict[str, Any]) -> ContractOverview:
        """
        Parse Section I: Contract Overview with all 8 fields.
        
        Validates: Requirement 4.1
        
        Args:
            data: Dictionary containing contract overview data from API response.
                  Expects schema format keys (e.g., "Project Title", "Owner").
        
        Returns:
            ContractOverview object with all 8 fields populated.
            
        Raises:
            ValueError: If required fields are missing or have invalid values.
        """
        logger.debug("Parsing contract overview section")
        
        # Use ContractOverview.from_dict which handles both schema and Python formats
        try:
            return ContractOverview.from_dict(data)
        except (KeyError, ValueError) as e:
            logger.error("Failed to parse contract overview: %s", e)
            raise ValueError(f"Invalid contract overview data: {str(e)}") from e
    
    def _parse_clause_block(self, data: Dict[str, Any]) -> Optional[ClauseBlock]:
        """
        Parse a single ClauseBlock, returning None if empty/missing.
        
        Validates: Requirement 4.2
        
        Args:
            data: Dictionary containing clause block data from API response.
                  Expects schema format keys (e.g., "Clause Language", "Risk Triggers Identified").
        
        Returns:
            ClauseBlock object if data is valid, None if data is empty or invalid.
        """
        if not data or not isinstance(data, dict):
            return None
        
        # Check if the clause block has meaningful content
        clause_language = data.get('Clause Language', data.get('clause_language', ''))
        if not clause_language:
            logger.debug("Skipping clause block with empty clause language")
            return None
        
        try:
            return ClauseBlock.from_dict(data)
        except (KeyError, ValueError) as e:
            logger.warning("Failed to parse clause block: %s", e)
            return None
    
    def _parse_section(
        self,
        data: Dict[str, Any],
        section_class: Type[T]
    ) -> T:
        """
        Parse a section with multiple clause blocks.
        
        Validates: Requirement 4.2
        
        Args:
            data: Dictionary containing section data from API response.
                  Keys are clause category names, values are ClauseBlock dictionaries.
            section_class: The dataclass type for this section
                          (e.g., AdministrativeAndCommercialTerms).
        
        Returns:
            Instance of section_class with populated clause blocks.
        """
        if not data or not isinstance(data, dict):
            # Return empty section instance
            return section_class()
        
        try:
            return section_class.from_dict(data)
        except (KeyError, ValueError) as e:
            logger.warning("Failed to parse section %s: %s", section_class.__name__, e)
            # Return empty section instance on error
            return section_class()
    
    def _parse_supplemental_risks(
        self,
        data: List[Dict[str, Any]]
    ) -> List[ClauseBlock]:
        """
        Parse Section VII: Supplemental Operational Risks.
        
        Args:
            data: List of ClauseBlock dictionaries from API response.
        
        Returns:
            List of ClauseBlock objects.
        """
        if not data or not isinstance(data, list):
            return []
        
        result: List[ClauseBlock] = []
        for idx, item in enumerate(data):
            clause_block = self._parse_clause_block(item)
            if clause_block is not None:
                result.append(clause_block)
            else:
                logger.debug("Skipped invalid supplemental risk at index %d", idx)
        
        return result
    
    def _create_metadata(
        self,
        api_response: Dict[str, Any],
        filename: str,
        file_size_bytes: int,
        page_count: Optional[int]
    ) -> ContractMetadata:
        """
        Create ContractMetadata from API response and file information.
        
        Args:
            api_response: API response dictionary (may contain metadata hints)
            filename: Contract filename
            file_size_bytes: File size in bytes
            page_count: Number of pages (optional)
        
        Returns:
            ContractMetadata object
        """
        # Try to get page count from API response if not provided
        if page_count is None:
            metadata_dict = api_response.get('metadata', {})
            page_count = metadata_dict.get('page_count', 0)
        
        # Ensure page_count is at least 1 if we have a file
        if page_count == 0 and file_size_bytes > 0:
            page_count = 1
        
        return ContractMetadata(
            filename=filename,
            analyzed_at=datetime.now(),
            page_count=page_count,
            file_size_bytes=file_size_bytes
        )
    
    def convert_legacy_result(self, legacy: AnalysisResult) -> ComprehensiveAnalysisResult:
        """
        Convert legacy AnalysisResult to ComprehensiveAnalysisResult format.
        
        Validates: Requirements 7.2, 7.3
        
        This method performs best-effort mapping of legacy data to the comprehensive
        schema structure:
        
        1. Maps legacy clauses to appropriate schema sections based on clause type
        2. Maps legacy risks to risk_triggers_identified in relevant clause blocks
        3. Maps legacy redlining_suggestions to redline_recommendations
        4. Preserves all original data
        
        Args:
            legacy: AnalysisResult object in legacy format
        
        Returns:
            ComprehensiveAnalysisResult with data mapped to new schema structure
        """
        logger.info("Converting legacy AnalysisResult to ComprehensiveAnalysisResult")
        
        # Create default contract overview from available metadata
        contract_overview = ContractOverview(
            project_title=legacy.metadata.filename.replace('.pdf', '').replace('.docx', ''),
            solicitation_no="N/A",
            owner="Unknown",
            contractor="Unknown",
            scope="Converted from legacy analysis",
            general_risk_level=self._determine_overall_risk_level(legacy),
            bid_model="Other",
            notes=f"Converted from legacy format on {datetime.now().isoformat()}"
        )
        
        # Initialize empty section models
        administrative_and_commercial_terms = AdministrativeAndCommercialTerms()
        technical_and_performance_terms = TechnicalAndPerformanceTerms()
        legal_risk_and_enforcement = LegalRiskAndEnforcement()
        regulatory_and_compliance_terms = RegulatoryAndComplianceTerms()
        data_technology_and_deliverables = DataTechnologyAndDeliverables()
        supplemental_operational_risks: List[ClauseBlock] = []
        
        # Map legacy clauses to appropriate sections
        clause_mapping = self._map_legacy_clauses_to_sections(legacy)
        
        # Populate sections with mapped clauses
        administrative_and_commercial_terms = self._populate_section_from_mapping(
            clause_mapping.get('administrative_and_commercial_terms', {}),
            AdministrativeAndCommercialTerms
        )
        technical_and_performance_terms = self._populate_section_from_mapping(
            clause_mapping.get('technical_and_performance_terms', {}),
            TechnicalAndPerformanceTerms
        )
        legal_risk_and_enforcement = self._populate_section_from_mapping(
            clause_mapping.get('legal_risk_and_enforcement', {}),
            LegalRiskAndEnforcement
        )
        regulatory_and_compliance_terms = self._populate_section_from_mapping(
            clause_mapping.get('regulatory_and_compliance_terms', {}),
            RegulatoryAndComplianceTerms
        )
        data_technology_and_deliverables = self._populate_section_from_mapping(
            clause_mapping.get('data_technology_and_deliverables', {}),
            DataTechnologyAndDeliverables
        )
        
        # Add unmapped clauses to supplemental operational risks
        supplemental_operational_risks = clause_mapping.get('supplemental_operational_risks', [])
        
        # Create comprehensive result
        result = ComprehensiveAnalysisResult(
            schema_version="1.0.0-legacy-converted",
            contract_overview=contract_overview,
            administrative_and_commercial_terms=administrative_and_commercial_terms,
            technical_and_performance_terms=technical_and_performance_terms,
            legal_risk_and_enforcement=legal_risk_and_enforcement,
            regulatory_and_compliance_terms=regulatory_and_compliance_terms,
            data_technology_and_deliverables=data_technology_and_deliverables,
            supplemental_operational_risks=supplemental_operational_risks,
            metadata=legacy.metadata
        )
        
        logger.info("Successfully converted legacy result to comprehensive format")
        return result
    
    def _determine_overall_risk_level(self, legacy: AnalysisResult) -> str:
        """
        Determine overall risk level from legacy risks.
        
        Args:
            legacy: Legacy AnalysisResult
        
        Returns:
            Risk level string: "Low", "Medium", "High", or "Critical"
        """
        if not legacy.risks:
            return "Low"
        
        # Count risks by severity
        severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for risk in legacy.risks:
            severity = risk.severity.lower()
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        # Determine overall level based on highest severity risks
        if severity_counts['critical'] > 0:
            return "Critical"
        elif severity_counts['high'] >= 3:
            return "High"
        elif severity_counts['high'] > 0 or severity_counts['medium'] >= 3:
            return "High"
        elif severity_counts['medium'] > 0:
            return "Medium"
        else:
            return "Low"
    
    def _map_legacy_clauses_to_sections(
        self, 
        legacy: AnalysisResult
    ) -> Dict[str, Any]:
        """
        Map legacy clauses to comprehensive schema sections.
        
        Args:
            legacy: Legacy AnalysisResult
        
        Returns:
            Dictionary mapping section names to clause blocks or lists of clause blocks
        """
        # Initialize section mappings
        section_mappings: Dict[str, Dict[str, ClauseBlock]] = {
            'administrative_and_commercial_terms': {},
            'technical_and_performance_terms': {},
            'legal_risk_and_enforcement': {},
            'regulatory_and_compliance_terms': {},
            'data_technology_and_deliverables': {},
        }
        supplemental_risks: List[ClauseBlock] = []
        
        # Define mapping from legacy clause types to comprehensive schema fields
        clause_type_mapping = {
            # Administrative & Commercial
            'payment_terms': ('administrative_and_commercial_terms', 'retainage_progress_payments'),
            'termination': ('administrative_and_commercial_terms', 'termination_for_convenience'),
            'change_order': ('administrative_and_commercial_terms', 'change_orders'),
            'bonding': ('administrative_and_commercial_terms', 'bonding_surety_insurance'),
            'insurance': ('administrative_and_commercial_terms', 'bonding_surety_insurance'),
            
            # Technical & Performance
            'scope': ('technical_and_performance_terms', 'scope_of_work'),
            'schedule': ('technical_and_performance_terms', 'performance_schedule'),
            'warranty': ('technical_and_performance_terms', 'warranty'),
            'delay': ('technical_and_performance_terms', 'delays'),
            'deliverable': ('technical_and_performance_terms', 'deliverables'),
            
            # Legal Risk & Enforcement
            'liability': ('legal_risk_and_enforcement', 'limitations_of_liability'),
            'indemnification': ('legal_risk_and_enforcement', 'indemnification'),
            'dispute': ('legal_risk_and_enforcement', 'dispute_resolution'),
            'insurance_coverage': ('legal_risk_and_enforcement', 'insurance_coverage'),
            
            # Regulatory & Compliance
            'compliance': ('regulatory_and_compliance_terms', 'eeo_non_discrimination'),
            'wage': ('regulatory_and_compliance_terms', 'prevailing_wage'),
            'payroll': ('regulatory_and_compliance_terms', 'certified_payroll'),
            
            # Data & Technology
            'data': ('data_technology_and_deliverables', 'data_ownership'),
            'confidentiality': ('data_technology_and_deliverables', 'confidentiality'),
            'intellectual_property': ('data_technology_and_deliverables', 'intellectual_property'),
        }
        
        # Map each legacy clause to a section
        for clause in legacy.clauses:
            # Find related risks for this clause
            related_risks = [r for r in legacy.risks if r.clause_id == clause.id]
            
            # Find related redlining suggestions
            related_redlines = [rs for rs in legacy.redlining_suggestions if rs.clause_id == clause.id]
            
            # Create ClauseBlock from legacy clause
            clause_block = self._create_clause_block_from_legacy(
                clause, related_risks, related_redlines
            )
            
            # Determine which section this clause belongs to
            clause_type_lower = clause.type.lower()
            mapped = False
            
            for type_key, (section_name, field_name) in clause_type_mapping.items():
                if type_key in clause_type_lower:
                    section_mappings[section_name][field_name] = clause_block
                    mapped = True
                    break
            
            # If not mapped, add to supplemental operational risks
            if not mapped:
                supplemental_risks.append(clause_block)
        
        # Add any unmapped risks to supplemental operational risks
        unmapped_risks = [r for r in legacy.risks if not any(c.id == r.clause_id for c in legacy.clauses)]
        for risk in unmapped_risks:
            clause_block = ClauseBlock(
                clause_language=f"Risk identified: {risk.description}",
                clause_summary=risk.description,
                risk_triggers_identified=[risk.description],
                flow_down_obligations=[],
                redline_recommendations=[],
                harmful_language_policy_conflicts=[]
            )
            supplemental_risks.append(clause_block)
        
        # Add any unmapped compliance issues to supplemental operational risks
        for issue in legacy.compliance_issues:
            clause_block = ClauseBlock(
                clause_language=f"Compliance issue: {issue.issue}",
                clause_summary=f"{issue.regulation}: {issue.issue}",
                risk_triggers_identified=[issue.issue],
                flow_down_obligations=[],
                redline_recommendations=[],
                harmful_language_policy_conflicts=[issue.issue]
            )
            supplemental_risks.append(clause_block)
        
        return {
            **section_mappings,
            'supplemental_operational_risks': supplemental_risks
        }
    
    def _create_clause_block_from_legacy(
        self,
        clause: Clause,
        risks: List[Risk],
        redlines: List[RedliningSuggestion]
    ) -> ClauseBlock:
        """
        Create a ClauseBlock from legacy clause, risks, and redlining suggestions.
        
        Args:
            clause: Legacy Clause object
            risks: List of related Risk objects
            redlines: List of related RedliningSuggestion objects
        
        Returns:
            ClauseBlock with data mapped from legacy objects
        """
        # Extract risk triggers from risks
        risk_triggers = [r.description for r in risks]
        
        # Convert legacy redlining suggestions to redline recommendations
        redline_recommendations = []
        for redline in redlines:
            # Determine action based on text comparison
            if not redline.original_text:
                action = "insert"
            elif not redline.suggested_text:
                action = "delete"
            else:
                action = "replace"
            
            recommendation = RedlineRecommendation(
                action=action,
                text=redline.suggested_text if action != "delete" else redline.original_text,
                reference=redline.rationale if redline.rationale else None
            )
            redline_recommendations.append(recommendation)
        
        return ClauseBlock(
            clause_language=clause.text,
            clause_summary=f"{clause.type} clause (page {clause.page})",
            risk_triggers_identified=risk_triggers,
            flow_down_obligations=[],  # Not available in legacy format
            redline_recommendations=redline_recommendations,
            harmful_language_policy_conflicts=[]  # Not available in legacy format
        )
    
    def _populate_section_from_mapping(
        self,
        mapping: Dict[str, ClauseBlock],
        section_class: Type[T]
    ) -> T:
        """
        Populate a section dataclass from a mapping of field names to ClauseBlocks.
        
        Args:
            mapping: Dictionary mapping field names to ClauseBlock objects
            section_class: The section dataclass type to instantiate
        
        Returns:
            Instance of section_class with fields populated from mapping
        """
        # Create kwargs dict with mapped clause blocks
        kwargs = {field_name: clause_block for field_name, clause_block in mapping.items()}
        
        # Instantiate section with mapped fields
        return section_class(**kwargs)
