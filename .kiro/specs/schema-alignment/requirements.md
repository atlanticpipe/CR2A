# Requirements Document

## Introduction

This document specifies the requirements for aligning the contract analysis system to use the comprehensive 8-section output schema defined in `output_schemas_v1.json`. Currently, the OpenAI client uses a simplified schema that does not match the comprehensive schema, resulting in loss of detailed clause analysis capabilities including risk triggers, flow-down obligations, and structured redline recommendations.

## Glossary

- **Schema**: The JSON structure defining the expected format of contract analysis output
- **ClauseBlock**: A reusable structure containing clause language, summary, risk triggers, flow-down obligations, redline recommendations, and harmful language/policy conflicts
- **OpenAI_Client**: The module responsible for building prompts and communicating with the OpenAI API
- **Result_Parser**: The module that transforms API responses into internal data models
- **Analysis_Models**: Python dataclasses representing the contract analysis result structure
- **Contract_Extractor**: The module that uses regex patterns to identify and extract relevant sections from contracts
- **Redline_Recommendation**: A structured suggestion with action (insert/replace/delete), text, and optional reference
- **Flow_Down_Obligation**: A contractual requirement that must be passed to subcontractors
- **Risk_Trigger**: A specific condition or language that indicates potential risk

## Requirements

### Requirement 1: Comprehensive Schema Integration in OpenAI Client

**User Story:** As a contract analyst, I want the AI to analyze contracts using the comprehensive 8-section schema, so that I receive detailed clause-by-clause analysis with risk triggers, flow-down obligations, and actionable redline recommendations.

#### Acceptance Criteria

1. WHEN the OpenAI_Client builds a user message, THE System SHALL include the complete schema structure from output_schemas_v1.json with all 8 sections
2. WHEN the OpenAI_Client builds a system message, THE System SHALL instruct the AI to analyze contracts according to the ClauseBlock structure for each clause category
3. THE OpenAI_Client SHALL load the schema from the config/output_schemas_v1.json file rather than using a hardcoded simplified schema
4. WHEN a clause category is not found in the contract, THE System SHALL omit that clause from the response rather than including empty values
5. THE OpenAI_Client SHALL request JSON output that validates against the output_schemas_v1.json schema

### Requirement 2: ClauseBlock Data Model Support

**User Story:** As a developer, I want the analysis models to support the ClauseBlock structure, so that all clause analysis data can be properly stored and accessed.

#### Acceptance Criteria

1. THE Analysis_Models SHALL define a ClauseBlock dataclass with fields for Clause Language, Clause Summary, Risk Triggers Identified, Flow-Down Obligations, Redline Recommendations, and Harmful Language/Policy Conflicts
2. THE Analysis_Models SHALL define a RedlineRecommendation dataclass with action (insert/replace/delete), text, and optional reference fields
3. WHEN a ClauseBlock is serialized to JSON, THE System SHALL produce output matching the ClauseBlock schema definition
4. WHEN a ClauseBlock is deserialized from JSON, THE System SHALL correctly populate all fields including nested arrays
5. THE Analysis_Models SHALL support the contract_overview section with all 8 required fields (Project Title, Solicitation No., Owner, Contractor, Scope, General Risk Level, Bid Model, Notes)

### Requirement 3: Section-Based Analysis Result Structure

**User Story:** As a contract analyst, I want analysis results organized by the 8 schema sections, so that I can easily navigate to specific clause categories.

#### Acceptance Criteria

1. THE Analysis_Models SHALL define section dataclasses for administrative_and_commercial_terms (16 clause types), technical_and_performance_terms (17 clause types), legal_risk_and_enforcement (13 clause types), regulatory_and_compliance_terms (8 clause types), data_technology_and_deliverables (7 clause types), and supplemental_operational_risks (up to 9 entries)
2. THE AnalysisResult dataclass SHALL contain fields for all 8 schema sections plus schema_version
3. WHEN serializing an AnalysisResult to JSON, THE System SHALL produce output that validates against output_schemas_v1.json
4. WHEN deserializing JSON to an AnalysisResult, THE System SHALL correctly map all sections and their clause blocks

### Requirement 4: Result Parser Schema Alignment

**User Story:** As a developer, I want the result parser to correctly parse the comprehensive schema response, so that all clause analysis data is properly extracted.

#### Acceptance Criteria

1. WHEN the Result_Parser receives an API response, THE System SHALL parse the contract_overview section with all 8 fields
2. WHEN the Result_Parser receives an API response, THE System SHALL parse each section's clause blocks into the corresponding dataclass
3. WHEN a clause block contains redline recommendations, THE System SHALL parse each recommendation with its action, text, and optional reference
4. IF a section or clause is missing from the API response, THEN THE Result_Parser SHALL handle the absence gracefully without raising errors
5. WHEN parsing risk triggers or flow-down obligations, THE System SHALL preserve the array structure with all string items

### Requirement 5: Contract Extractor Pattern Alignment

**User Story:** As a contract analyst, I want the contract extractor to identify all 61+ clause categories from the schema, so that relevant sections are properly extracted for analysis.

#### Acceptance Criteria

1. THE Contract_Extractor SHALL define regex patterns for all clause categories in administrative_and_commercial_terms (16 categories)
2. THE Contract_Extractor SHALL define regex patterns for all clause categories in technical_and_performance_terms (17 categories)
3. THE Contract_Extractor SHALL define regex patterns for all clause categories in legal_risk_and_enforcement (13 categories)
4. THE Contract_Extractor SHALL define regex patterns for all clause categories in regulatory_and_compliance_terms (8 categories)
5. THE Contract_Extractor SHALL define regex patterns for all clause categories in data_technology_and_deliverables (7 categories)
6. WHEN extracting sections, THE Contract_Extractor SHALL map extracted text to the corresponding schema clause category names

### Requirement 6: Schema Validation

**User Story:** As a developer, I want API responses validated against the schema, so that malformed responses are detected and handled appropriately.

#### Acceptance Criteria

1. THE System SHALL load and parse the output_schemas_v1.json schema at initialization
2. WHEN an API response is received, THE System SHALL validate it against the loaded schema
3. IF validation fails, THEN THE System SHALL log the validation errors with specific field paths
4. IF validation fails on non-critical fields, THEN THE System SHALL continue processing with available data
5. THE System SHALL validate that risk levels match the enum values (Low, Medium, High, Critical)
6. THE System SHALL validate that bid models match the enum values (Lump Sum, Unit Price, Cost Plus, Time & Materials, GMP, Design-Build, Other)
7. THE System SHALL validate that redline actions match the enum values (insert, replace, delete)

### Requirement 7: Backward Compatibility

**User Story:** As a user with existing analysis results, I want the system to handle both old and new schema formats, so that my historical data remains accessible.

#### Acceptance Criteria

1. WHEN loading an analysis result, THE System SHALL detect whether it uses the old simplified schema or the new comprehensive schema
2. IF an old-format result is loaded, THEN THE System SHALL convert it to the new format with best-effort mapping
3. THE System SHALL preserve all data from old-format results during conversion
4. WHEN displaying results, THE System SHALL handle both formats without errors
