# Implementation Plan: Schema Alignment

## Overview

This implementation plan aligns the contract analysis system with the comprehensive 8-section output schema. Tasks are organized to build foundational components first (data models, schema loader), then update dependent components (OpenAI client, result parser), and finally add validation and backward compatibility.

## Tasks

- [x] 1. Create comprehensive data models
  - [x] 1.1 Create RedlineRecommendation dataclass in src/analysis_models.py
    - Add fields: action (str), text (str), reference (Optional[str])
    - Implement to_dict() and from_dict() methods
    - Validate action is one of: insert, replace, delete
    - _Requirements: 2.2_

  - [x] 1.2 Create ClauseBlock dataclass in src/analysis_models.py
    - Add fields: clause_language, clause_summary, risk_triggers_identified, flow_down_obligations, redline_recommendations, harmful_language_policy_conflicts
    - Implement to_dict() and from_dict() methods with nested RedlineRecommendation handling
    - _Requirements: 2.1_

  - [ ]* 1.3 Write property test for ClauseBlock round-trip serialization
    - **Property 3: ClauseBlock Round-Trip Serialization**
    - **Validates: Requirements 2.3, 2.4**

  - [x] 1.4 Create ContractOverview dataclass in src/analysis_models.py
    - Add all 8 fields: project_title, solicitation_no, owner, contractor, scope, general_risk_level, bid_model, notes
    - Implement to_dict() and from_dict() methods
    - Map field names to schema format (e.g., project_title -> "Project Title")
    - _Requirements: 2.5_

  - [x] 1.5 Create section dataclasses in src/analysis_models.py
    - Create AdministrativeAndCommercialTerms with 16 Optional[ClauseBlock] fields
    - Create TechnicalAndPerformanceTerms with 17 Optional[ClauseBlock] fields
    - Create LegalRiskAndEnforcement with 13 Optional[ClauseBlock] fields
    - Create RegulatoryAndComplianceTerms with 8 Optional[ClauseBlock] fields
    - Create DataTechnologyAndDeliverables with 7 Optional[ClauseBlock] fields
    - Implement to_dict() and from_dict() for each, omitting None values
    - _Requirements: 3.1_

  - [x] 1.6 Create ComprehensiveAnalysisResult dataclass in src/analysis_models.py
    - Add fields for schema_version, contract_overview, all 6 section models, supplemental_operational_risks (List[ClauseBlock]), and metadata
    - Implement to_dict() and from_dict() methods
    - _Requirements: 3.2_

  - [ ]* 1.7 Write property test for ComprehensiveAnalysisResult round-trip serialization
    - **Property 4: ComprehensiveAnalysisResult Round-Trip Serialization**
    - **Validates: Requirements 3.3, 3.4**

- [x] 2. Checkpoint - Ensure data model tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Implement schema loader component
  - [x] 3.1 Create SchemaLoader class in src/schema_loader.py
    - Implement __init__ with schema_path parameter defaulting to config/output_schemas_v1.json
    - Implement load_schema() to load and cache schema from file
    - Implement get_clause_categories() to extract category names by section
    - Implement get_schema_for_prompt() to generate prompt-friendly schema description
    - Implement get_clause_block_schema() to return ClauseBlock definition
    - _Requirements: 1.3_

  - [ ]* 3.2 Write property test for schema loading consistency
    - **Property 1: Schema Loading Consistency**
    - **Validates: Requirements 1.3**

  - [x] 3.3 Write unit tests for SchemaLoader
    - Test loading valid schema file
    - Test error handling for missing file
    - Test clause category extraction
    - _Requirements: 1.3_

- [x] 4. Implement schema validator component
  - [x] 4.1 Create ValidationResult and ValidationError dataclasses in src/schema_validator.py
    - ValidationResult: is_valid (bool), errors (List[ValidationError]), warnings (List[str])
    - ValidationError: path (str), message (str), value (Any)
    - _Requirements: 6.3_

  - [x] 4.2 Create SchemaValidator class in src/schema_validator.py
    - Implement __init__ with SchemaLoader dependency
    - Implement validate() to validate response against schema using jsonschema library
    - Implement validate_clause_block() for single block validation
    - Implement validate_enum_field() for risk_level, bid_model, action validation
    - _Requirements: 6.1, 6.2_

  - [ ]* 4.3 Write property test for enum validation
    - **Property 11: Enum Value Validation**
    - **Validates: Requirements 6.5, 6.6, 6.7**

  - [ ]* 4.4 Write property test for validation error field paths
    - **Property 9: Validation Error Field Paths**
    - **Validates: Requirements 6.3**

- [x] 5. Checkpoint - Ensure schema loader and validator tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Update OpenAI client for comprehensive schema
  - [x] 6.1 Integrate SchemaLoader into OpenAIClient in src/openai_fallback_client.py
    - Add SchemaLoader as dependency in __init__
    - Load schema on initialization
    - _Requirements: 1.3_

  - [x] 6.2 Update _build_system_message() in src/openai_fallback_client.py
    - Include instructions for ClauseBlock structure analysis
    - Specify all 8 sections to analyze
    - Instruct to omit clauses not found rather than including empty values
    - _Requirements: 1.2, 1.4_

  - [x] 6.3 Update _build_user_message() in src/openai_fallback_client.py
    - Replace hardcoded simplified schema with comprehensive schema from SchemaLoader
    - Include all 8 section structures with their clause categories
    - Include ClauseBlock structure with all fields
    - _Requirements: 1.1, 1.5_

  - [ ]* 6.4 Write property test for user message section coverage
    - **Property 2: User Message Section Coverage**
    - **Validates: Requirements 1.1**

- [x] 7. Update result parser for comprehensive schema
  - [x] 7.1 Create ComprehensiveResultParser class in src/result_parser.py
    - Implement __init__ with SchemaValidator dependency
    - Implement parse_api_response() to parse comprehensive schema responses
    - _Requirements: 4.1, 4.2_

  - [x] 7.2 Implement section parsing methods in ComprehensiveResultParser
    - Implement _parse_contract_overview() for Section I
    - Implement _parse_clause_block() for individual clause blocks
    - Implement _parse_section() generic method for section parsing
    - Handle missing sections/clauses gracefully (return None)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 7.3 Write property test for comprehensive response parsing
    - **Property 5: Comprehensive Response Parsing**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.5**

  - [ ]* 7.4 Write property test for graceful handling of missing data
    - **Property 6: Graceful Handling of Missing Data**
    - **Validates: Requirements 4.4**

  - [ ]* 7.5 Write property test for graceful degradation on non-critical failures
    - **Property 10: Graceful Degradation on Non-Critical Failures**
    - **Validates: Requirements 6.4**

- [x] 8. Checkpoint - Ensure OpenAI client and parser tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Update contract extractor patterns
  - [x] 9.1 Define comprehensive pattern registry in analyzer/contract_extractor.py
    - Add patterns for all 16 administrative_and_commercial_terms categories
    - Add patterns for all 17 technical_and_performance_terms categories
    - Add patterns for all 13 legal_risk_and_enforcement categories
    - Add patterns for all 8 regulatory_and_compliance_terms categories
    - Add patterns for all 7 data_technology_and_deliverables categories
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 9.2 Create ComprehensiveContractExtractor class in analyzer/contract_extractor.py
    - Implement extract_for_schema_section() to extract text for a specific section
    - Implement create_focused_contract() organized by schema sections
    - Map extracted text to schema clause category names
    - _Requirements: 5.6_

  - [ ]* 9.3 Write property test for section extraction category mapping
    - **Property 7: Section Extraction Category Mapping**
    - **Validates: Requirements 5.6**

  - [x] 9.4 Write unit tests for pattern coverage
    - Verify all 61+ clause categories have patterns defined
    - Test pattern matching against sample contract text
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 10. Implement backward compatibility
  - [x] 10.1 Implement schema format detection in src/result_parser.py
    - Add detect_schema_format() method to identify legacy vs comprehensive format
    - Check for schema_version field and section structure
    - _Requirements: 7.1_

  - [ ]* 10.2 Write property test for schema format detection
    - **Property 12: Schema Format Detection**
    - **Validates: Requirements 7.1**

  - [x] 10.3 Implement legacy conversion in src/result_parser.py
    - Add convert_legacy_result() method to ComprehensiveResultParser
    - Map legacy clauses to appropriate schema sections based on type
    - Map legacy risks to risk_triggers_identified in relevant clause blocks
    - Map legacy redlining_suggestions to redline_recommendations
    - Preserve all original data
    - _Requirements: 7.2, 7.3_

  - [ ]* 10.4 Write property test for legacy conversion data preservation
    - **Property 13: Legacy Conversion Data Preservation**
    - **Validates: Requirements 7.3**

  - [x] 10.5 Update display/rendering code for dual format support
    - Ensure UI components handle both AnalysisResult and ComprehensiveAnalysisResult
    - Add format detection before rendering
    - _Requirements: 7.4_

  - [ ]* 10.6 Write property test for dual format display compatibility
    - **Property 14: Dual Format Display Compatibility**
    - **Validates: Requirements 7.4**

- [x] 11. Checkpoint - Ensure backward compatibility tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Integration and validation
  - [x] 12.1 Integrate SchemaValidator into parsing pipeline
    - Call validator before parsing API response
    - Log validation warnings/errors
    - Continue processing on non-critical failures
    - _Requirements: 6.2, 6.4_

  - [ ]* 12.2 Write property test for schema validation execution
    - **Property 8: Schema Validation Execution**
    - **Validates: Requirements 6.2**

  - [x] 12.3 Write integration tests for end-to-end flow
    - Test complete flow from contract text through analysis to result
    - Test with sample contracts containing various clause types
    - Verify output validates against schema
    - _Requirements: 1.1, 3.3, 6.2_

- [x] 13. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using the `hypothesis` library
- Unit tests validate specific examples and edge cases
- The implementation builds foundational components first (data models, schema loader) before updating dependent components
