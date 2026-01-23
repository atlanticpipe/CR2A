# Implementation Plan: LM Studio Migration

## Overview

This implementation plan breaks down the LM Studio migration into discrete, incremental tasks. Each task builds on previous work, with testing integrated throughout to catch issues early. The approach is surgical: modify the existing `OpenAIService` class and add configuration support, without rewriting the application.

## Tasks

- [ ] 1. Create JSON extraction utilities
  - Create `frontend/services/jsonExtractor.js` with multi-stage JSON extraction logic
  - Implement `extractJSON(text)` function that handles: direct parsing, markdown code block extraction, and pattern-based extraction
  - Implement `validateCR2AFields(jsonObject)` function that checks for all required fields
  - _Requirements: 4.1, 4.2, 4.3, 4.5_

- [ ] 1.1 Write property test for JSON extraction
  - **Property 4: JSON Extraction Robustness**
  - **Validates: Requirements 4.1, 4.2, 4.3**
  - Generate random JSON objects, wrap them in various formats (markdown, surrounding text, standalone)
  - Verify extraction succeeds for all valid JSON regardless of wrapping

- [ ] 1.2 Write unit tests for JSON extraction edge cases
  - Test empty response handling
  - Test malformed JSON responses
  - Test nested code blocks
  - Test JSON with special characters
  - _Requirements: 4.1, 4.2, 4.3_

- [ ] 2. Extend ConfigManager for LM Studio settings
  - Add methods to `frontend/services/configManager.js`: `getLMStudioBaseUrl()`, `setLMStudioBaseUrl(url)`, `getLMStudioModelId()`, `setLMStudioModelId(id)`, `getApiMode()`, `setApiMode(mode)`
  - Implement storage schema with fields: `lmstudio_base_url`, `lmstudio_model_id`, `api_mode`
  - Provide default values: `http://localhost:1234` for base URL, `qwen2.5-7b-instruct` for model ID
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [ ] 2.1 Write property test for configuration persistence
  - **Property 3: Configuration Persistence Round-Trip**
  - **Validates: Requirements 2.2**
  - Generate random configuration objects with various base URLs and model IDs
  - Verify saving then loading returns equivalent configuration

- [ ] 2.2 Write unit tests for ConfigManager
  - Test default values are returned when no config exists
  - Test configuration is persisted to localStorage
  - Test configuration is loaded on initialization
  - Test invalid configuration is rejected
  - _Requirements: 2.2, 2.3, 2.4_

- [ ] 3. Update OpenAIService for LM Studio support
  - Modify `frontend/services/openaiService.js` constructor to accept `baseUrl` and `modelId` parameters
  - Replace hardcoded `https://api.openai.com/v1` with configurable base URL
  - Update `analyzeSection()` to use JSON extraction utilities for response parsing
  - Update `streamAnalysis()` to use JSON extraction for streamed responses
  - Add `_extractJSON()` and `_validateCR2AFields()` private methods
  - _Requirements: 1.1, 1.2, 4.1, 4.2, 4.3, 4.5_

- [ ] 3.1 Write property test for configuration application
  - **Property 1: Configuration Values Are Applied**
  - **Validates: Requirements 1.1, 1.4**
  - Generate random base URLs
  - Create service instances with each URL
  - Verify each instance uses its configured URL for requests

- [ ] 3.2 Write property test for request format consistency
  - **Property 2: Request Format Consistency**
  - **Validates: Requirements 1.2, 3.3**
  - Generate random analysis requests with various contract texts and prompts
  - Intercept HTTP requests and validate payload structure matches OpenAI format
  - Verify all required fields (model, messages, temperature, max_tokens) are present

- [ ] 3.3 Write unit tests for OpenAIService modifications
  - Test service initializes with custom base URL
  - Test service initializes with default OpenAI URL when no config provided
  - Test analyzeSection() works with both OpenAI and LM Studio endpoints
  - Test response parsing handles various JSON formats
  - _Requirements: 1.1, 1.4, 3.1, 3.2, 3.3_

- [ ] 4. Implement retry logic with timeout
  - Add `_makeRequestWithRetry(url, options, maxRetries)` method to OpenAIService
  - Implement retry loop with 2-second delays between attempts
  - Add timeout enforcement using AbortController (default 120 seconds)
  - Add logging for each attempt (attempt number, duration, outcome)
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2_

- [ ] 4.1 Write property test for retry behavior
  - **Property 6: Retry Behavior**
  - **Validates: Requirements 6.1, 6.2**
  - Simulate random API failures
  - Verify service retries up to 3 times total with 2-second delays
  - Measure actual delay between attempts

- [ ] 4.2 Write property test for timeout enforcement
  - **Property 8: Timeout Enforcement**
  - **Validates: Requirements 7.1, 7.4**
  - Generate random timeout values
  - Simulate requests that exceed timeout
  - Verify requests are aborted and timeout errors are thrown

- [ ] 4.3 Write unit tests for retry and timeout logic
  - Test retry occurs on network errors
  - Test retry does not occur on validation errors
  - Test timeout aborts long-running requests
  - Test error message indicates timeout occurred
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 7.5_

- [ ] 5. Add performance monitoring
  - Add timestamp recording at request start in OpenAIService
  - Calculate and log duration on request completion
  - Log character counts for prompts and responses
  - Track successful vs failed request counts
  - _Requirements: 8.1, 8.2, 8.3, 8.5_

- [ ] 5.1 Write property test for request monitoring
  - **Property 7: Request Monitoring**
  - **Validates: Requirements 6.5, 8.1, 8.2, 8.3, 8.5**
  - Generate random API requests (successful and failed)
  - Capture logs for each request
  - Verify logs contain attempt number, timestamps, duration, character counts, and outcome

- [ ] 5.2 Write unit tests for performance monitoring
  - Test start timestamp is recorded
  - Test duration is calculated correctly
  - Test character counts are logged
  - Test success/failure counts are tracked
  - _Requirements: 8.1, 8.2, 8.3, 8.5_

- [ ] 6. Checkpoint - Ensure all backend tests pass
  - Run all unit tests and property tests for OpenAIService, ConfigManager, and JSON extraction
  - Verify all tests pass before proceeding to UI changes
  - Ask the user if questions arise

- [ ] 7. Enhance system prompt for JSON-only output
  - Update `buildSystemPrompt()` in OpenAIService to explicitly require JSON-only responses
  - Add prohibitions against markdown code blocks and explanatory text
  - Include exact JSON schema with all required fields
  - Specify valid risk_level values ("high", "moderate", "low")
  - Emphasize all fields must be strings
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 7.1 Write unit tests for system prompt content
  - Test prompt contains "valid JSON only" instruction
  - Test prompt prohibits markdown code blocks
  - Test prompt includes all required field names
  - Test prompt includes risk_level examples
  - Test prompt specifies string-only fields
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 8. Create Settings UI for LM Studio configuration
  - Add radio buttons to settings modal for API mode selection (OpenAI vs LM Studio)
  - Add input fields for LM Studio base URL and model ID
  - Add "Test Connection" button that calls `testConnection()` and displays result
  - Show/hide appropriate settings based on selected API mode
  - Wire up save button to persist configuration via ConfigManager
  - _Requirements: 2.1, 2.5_

- [ ] 8.1 Write unit tests for Settings UI
  - Test settings modal displays LM Studio fields
  - Test API mode selection shows/hides appropriate fields
  - Test save button persists configuration
  - Test test connection button displays server status
  - Test default values are populated correctly
  - _Requirements: 2.1, 2.4, 2.5_

- [ ] 9. Update app initialization to use configuration
  - Modify `initializeServices()` in `app_integrated.js` to read API mode from ConfigManager
  - Pass appropriate base URL and model ID to OpenAIService constructor based on API mode
  - Add error handling for missing or invalid configuration
  - _Requirements: 1.1, 1.4, 2.3, 3.5_

- [ ] 9.1 Write integration test for workflow with both APIs
  - Test workflow executes successfully with OpenAI configuration
  - Test workflow executes successfully with LM Studio configuration
  - Test switching between API modes works without errors
  - _Requirements: 3.4, 3.5_

- [ ] 10. Create test utilities for LM Studio validation
  - Create `tests/lmstudio-connection-test.js` that sends a simple request and validates JSON response
  - Create `tests/clause-analysis-test.js` that tests end-to-end clause analysis with sample data
  - Add clear success/failure indicators in test output
  - Make tests work with any OpenAI-compatible endpoint via configuration
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 10.1 Write property test for test utility portability
  - **Property 9: Test Utility Portability**
  - **Validates: Requirements 9.5**
  - Generate random OpenAI-compatible endpoint configurations
  - Run test utilities against each endpoint
  - Verify tests execute successfully regardless of endpoint

- [ ] 11. Checkpoint - End-to-end testing
  - Manually test with LM Studio: start server, configure app, upload contract, verify analysis
  - Manually test with OpenAI: switch API mode, verify analysis still works
  - Test error scenarios: LM Studio not running, invalid configuration, timeout
  - Ensure all tests pass, ask the user if questions arise

- [ ] 12. Create documentation
  - Create `LMSTUDIO_SETUP.md` with step-by-step setup instructions
  - Include recommended models and performance characteristics
  - Add troubleshooting section for common issues
  - Explain how to verify LM Studio is running correctly
  - Update `README.md` to reference LM Studio setup guide
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ] 12.1 Write unit tests for documentation completeness
  - Test LMSTUDIO_SETUP.md file exists
  - Test documentation includes model recommendations
  - Test documentation includes troubleshooting section
  - Test README.md links to setup guide
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ] 13. Final validation and cleanup
  - Run full test suite (unit tests + property tests)
  - Verify all correctness properties pass with 100+ iterations
  - Test with multiple contract samples
  - Verify performance meets benchmarks
  - Clean up any debug logging or temporary code

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties with 100+ iterations
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end workflows
- The implementation maintains backward compatibility with existing OpenAI integration
