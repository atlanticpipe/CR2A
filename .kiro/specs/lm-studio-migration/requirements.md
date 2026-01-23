# Requirements Document

## Introduction

This specification defines the requirements for migrating the CR2A contract analysis application from OpenAI's cloud API to a local LM Studio instance. The migration will enable offline contract analysis with zero API costs while maintaining all existing functionality including PDF parsing, section detection, clause analysis, and CR2A JSON output generation.

## Glossary

- **CR2A**: Contract Risk Assessment and Analysis - the structured JSON output format for contract analysis
- **LM_Studio**: A desktop application that runs large language models locally and provides an OpenAI-compatible API server
- **OpenAI_Service**: The existing JavaScript class that handles communication with OpenAI's API
- **Contract_Analysis_Workflow**: The end-to-end process of uploading a PDF, extracting text, analyzing clauses, and generating CR2A output
- **API_Endpoint**: The HTTP URL where the language model API is accessible
- **Model_ID**: The identifier for the specific language model loaded in LM Studio
- **System_Prompt**: The instructions that define the AI's role and output format requirements
- **Clause**: A distinct section or provision within a contract that requires individual analysis

## Requirements

### Requirement 1: Local API Integration

**User Story:** As a contract analyst, I want the application to use a local LM Studio instance instead of OpenAI's cloud API, so that I can analyze contracts offline without incurring API costs.

#### Acceptance Criteria

1. WHEN the application initializes, THE OpenAI_Service SHALL connect to a configurable local API endpoint instead of https://api.openai.com/v1
2. WHEN making analysis requests, THE OpenAI_Service SHALL use the LM Studio API format (OpenAI-compatible) at the configured endpoint
3. WHEN the local API endpoint is not reachable, THE OpenAI_Service SHALL provide a clear error message indicating LM Studio is not running
4. WHERE the user has configured a custom LM Studio URL, THE OpenAI_Service SHALL use that URL instead of the default localhost:1234
5. THE OpenAI_Service SHALL support both streaming and non-streaming analysis modes with LM Studio

### Requirement 2: Configuration Management

**User Story:** As a user, I want to configure the LM Studio connection settings through the application UI, so that I can easily switch between different models or API endpoints.

#### Acceptance Criteria

1. WHEN the user opens the settings modal, THE application SHALL display fields for LM Studio base URL and model ID
2. WHEN the user saves LM Studio configuration, THE application SHALL persist these settings to local storage
3. WHEN the application starts, THE application SHALL load LM Studio configuration from local storage if available
4. THE application SHALL provide default values of "http://localhost:1234" for base URL and "qwen2.5-7b-instruct" for model ID
5. WHEN the user clicks "Test Connection", THE application SHALL verify the LM Studio server is reachable and display the result

### Requirement 3: Backward Compatibility

**User Story:** As a developer, I want to maintain the existing OpenAI_Service interface, so that no changes are required to the workflow controller or other dependent code.

#### Acceptance Criteria

1. THE OpenAI_Service SHALL maintain all existing public methods (analyzeSection, streamAnalysis, testConnection)
2. THE OpenAI_Service SHALL accept the same parameters as the current implementation
3. THE OpenAI_Service SHALL return responses in the same format as the current OpenAI implementation
4. WHEN switching from OpenAI to LM Studio, THE Contract_Analysis_Workflow SHALL function without modification
5. THE OpenAI_Service SHALL handle both OpenAI API keys (for cloud) and LM Studio endpoints (for local) based on configuration

### Requirement 4: JSON Response Validation

**User Story:** As a contract analyst, I want the system to ensure LM Studio responses are valid JSON matching the CR2A schema, so that analysis results are always properly structured.

#### Acceptance Criteria

1. WHEN LM Studio returns a response, THE OpenAI_Service SHALL validate it is parseable JSON
2. IF the response contains markdown code blocks, THE OpenAI_Service SHALL extract the JSON content from within the code blocks
3. IF the response is not valid JSON, THE OpenAI_Service SHALL attempt to extract JSON objects using pattern matching
4. WHEN JSON extraction fails after all attempts, THE OpenAI_Service SHALL throw a descriptive error indicating the response format issue
5. THE OpenAI_Service SHALL validate that required CR2A fields are present in the parsed JSON response

### Requirement 5: Enhanced System Prompt

**User Story:** As a system administrator, I want the system prompt to explicitly require JSON-only output, so that local models consistently return properly formatted responses.

#### Acceptance Criteria

1. THE System_Prompt SHALL explicitly state that responses must be valid JSON only
2. THE System_Prompt SHALL prohibit markdown code blocks, explanations, or any text outside the JSON structure
3. THE System_Prompt SHALL specify the exact JSON schema with all required fields
4. THE System_Prompt SHALL include examples of valid risk_level values ("high", "moderate", "low")
5. THE System_Prompt SHALL emphasize that all fields must be strings (no arrays or nested objects)

### Requirement 6: Error Handling and Retry Logic

**User Story:** As a contract analyst, I want the system to automatically retry failed requests, so that temporary issues don't interrupt my analysis workflow.

#### Acceptance Criteria

1. WHEN an LM Studio API call fails, THE OpenAI_Service SHALL retry up to 2 additional times
2. WHEN retrying, THE OpenAI_Service SHALL wait 2 seconds between attempts
3. WHEN all retry attempts fail, THE OpenAI_Service SHALL throw an error with details from the last attempt
4. WHEN a timeout occurs, THE OpenAI_Service SHALL treat it as a failed attempt and retry
5. THE OpenAI_Service SHALL log each attempt number and outcome for debugging purposes

### Requirement 7: Request Timeout Management

**User Story:** As a user, I want requests to timeout after a reasonable period, so that the application doesn't hang indefinitely if LM Studio becomes unresponsive.

#### Acceptance Criteria

1. WHEN making an API request to LM Studio, THE OpenAI_Service SHALL enforce a 120-second timeout
2. IF a request exceeds the timeout, THE OpenAI_Service SHALL abort the request and throw a timeout error
3. WHERE streaming is enabled, THE OpenAI_Service SHALL apply the timeout to the entire stream duration
4. THE timeout duration SHALL be configurable through environment variables or settings
5. WHEN a timeout occurs, THE error message SHALL clearly indicate the request timed out

### Requirement 8: Performance Monitoring

**User Story:** As a developer, I want to track API call performance metrics, so that I can identify bottlenecks and optimize the analysis workflow.

#### Acceptance Criteria

1. WHEN an API call starts, THE OpenAI_Service SHALL record the start timestamp
2. WHEN an API call completes, THE OpenAI_Service SHALL calculate and log the duration
3. THE OpenAI_Service SHALL log the character count of both the request prompt and response
4. WHEN analysis completes, THE application SHALL display total analysis time and average time per clause
5. THE OpenAI_Service SHALL track and report the number of successful vs failed requests

### Requirement 9: Development and Testing Support

**User Story:** As a developer, I want test utilities to verify LM Studio integration, so that I can validate the migration without processing full contracts.

#### Acceptance Criteria

1. THE application SHALL provide a test script that sends a simple request to LM Studio and validates the response
2. THE test script SHALL verify JSON parsing, required field presence, and response format
3. THE application SHALL include a sample clause analysis test that validates end-to-end functionality
4. WHEN running tests, THE test utilities SHALL provide clear success/failure indicators
5. THE test utilities SHALL work with any OpenAI-compatible API endpoint (not just LM Studio)

### Requirement 10: Documentation and Setup Instructions

**User Story:** As a new user, I want clear setup instructions for LM Studio, so that I can quickly get the application running locally.

#### Acceptance Criteria

1. THE repository SHALL include a LMSTUDIO_SETUP.md file with step-by-step setup instructions
2. THE documentation SHALL specify recommended models and their performance characteristics
3. THE documentation SHALL include troubleshooting steps for common issues
4. THE documentation SHALL explain how to verify LM Studio is running correctly
5. THE README.md SHALL be updated to reference the LM Studio setup guide
