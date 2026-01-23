# Design Document: LM Studio Migration

## Overview

This design describes the migration of the CR2A contract analysis application from OpenAI's cloud API to a local LM Studio instance. The migration is implemented as a minimal, surgical change to the existing `OpenAIService` class, replacing the API endpoint and adding robust JSON validation while maintaining complete backward compatibility with the existing workflow.

The core principle is **swap, don't rewrite**: we change only the HTTP endpoint and add validation logic, keeping all existing prompts, schemas, templates, and workflow orchestration intact.

### Key Design Decisions

1. **In-place modification**: Update the existing `OpenAIService` class rather than creating a new adapter, minimizing code changes
2. **Configuration-based switching**: Use settings to toggle between OpenAI cloud and LM Studio local endpoints
3. **Enhanced JSON validation**: Add multi-stage JSON extraction to handle local model response variations
4. **Explicit prompting**: Strengthen system prompts to ensure consistent JSON-only output from local models
5. **Graceful degradation**: Maintain error handling and retry logic for reliability

## Architecture

### Current Architecture

```
User Browser
    ↓
app_integrated.js (UI Controller)
    ↓
WorkflowController (Orchestration)
    ↓
OpenAIService (API Client) → https://api.openai.com/v1/chat/completions
    ↓
PromptBuilder (Prompt Assembly)
```

### New Architecture

```
User Browser
    ↓
app_integrated.js (UI Controller)
    ↓
WorkflowController (Orchestration)
    ↓
OpenAIService (API Client) → http://localhost:1234/v1/chat/completions (LM Studio)
    ↓                          OR
    ↓                       → https://api.openai.com/v1/chat/completions (OpenAI)
    ↓
PromptBuilder (Prompt Assembly)
```

The architecture remains identical except for the API endpoint destination. The `OpenAIService` class becomes endpoint-agnostic, supporting both cloud and local APIs through configuration.

## Components and Interfaces

### 1. OpenAIService (Modified)

**Purpose**: HTTP client for language model API calls, supporting both OpenAI cloud and LM Studio local endpoints.

**Key Changes**:
- Constructor accepts `baseUrl` parameter (defaults to OpenAI or reads from config)
- Remove hardcoded `https://api.openai.com/v1` base URL
- Add JSON extraction and validation logic
- Add configurable timeout support
- Enhance error messages for local API failures

**Interface** (unchanged):

```javascript
class OpenAIService {
  constructor(apiKey, baseUrl = null, modelId = null)
  
  async analyzeSection(contractText, promptSection, metadata = {})
  async streamAnalysis(contractText, promptSection, onChunk, metadata = {})
  async testConnection()
  async getModels()
  
  buildSystemPrompt()
  buildUserPrompt(contractText, promptSection, metadata)
  estimateTokens(text)
  isWithinTokenLimit(text, maxTokens = 8000)
}
```

**New Internal Methods**:

```javascript
// Extract JSON from potentially malformed responses
_extractJSON(responseText)

// Validate required CR2A fields are present
_validateCR2AFields(jsonObject)

// Make HTTP request with timeout and retry
_makeRequestWithRetry(url, options, maxRetries = 2)
```

### 2. ConfigManager (Modified)

**Purpose**: Manage application configuration including API keys and LM Studio settings.

**New Methods**:

```javascript
class ConfigManager {
  // Existing methods
  static getApiKey()
  static setApiKey(key)
  static hasApiKey()
  static getModel()
  static setModel(model)
  
  // New methods for LM Studio
  static getLMStudioBaseUrl()
  static setLMStudioBaseUrl(url)
  static getLMStudioModelId()
  static setLMStudioModelId(modelId)
  static getApiMode() // Returns 'openai' or 'lmstudio'
  static setApiMode(mode)
}
```

**Storage Schema**:

```javascript
{
  "api_key": "sk-...",           // OpenAI API key (optional)
  "model": "gpt-4-turbo-preview", // OpenAI model
  "lmstudio_base_url": "http://localhost:1234",
  "lmstudio_model_id": "qwen2.5-7b-instruct",
  "api_mode": "lmstudio"         // 'openai' or 'lmstudio'
}
```

### 3. Settings UI (Modified)

**Purpose**: Allow users to configure LM Studio connection settings.

**New UI Elements**:

```html
<div class="settings-section">
  <h3>API Configuration</h3>
  
  <label>
    <input type="radio" name="api-mode" value="openai" />
    OpenAI Cloud API
  </label>
  
  <label>
    <input type="radio" name="api-mode" value="lmstudio" />
    LM Studio Local API
  </label>
  
  <!-- OpenAI Settings (shown when api-mode = 'openai') -->
  <div id="openai-settings">
    <label>API Key:
      <input type="password" id="openai-api-key" />
    </label>
    <label>Model:
      <select id="openai-model">
        <option>gpt-4-turbo-preview</option>
        <option>gpt-4</option>
        <option>gpt-3.5-turbo</option>
      </select>
    </label>
  </div>
  
  <!-- LM Studio Settings (shown when api-mode = 'lmstudio') -->
  <div id="lmstudio-settings">
    <label>Base URL:
      <input type="text" id="lmstudio-url" value="http://localhost:1234" />
    </label>
    <label>Model ID:
      <input type="text" id="lmstudio-model" value="qwen2.5-7b-instruct" />
    </label>
    <button id="test-lmstudio-connection">Test Connection</button>
    <span id="connection-status"></span>
  </div>
</div>
```

### 4. System Prompt (Enhanced)

**Purpose**: Ensure local models return valid JSON in the exact CR2A format.

**Current Prompt Issues**:
- Doesn't explicitly prohibit markdown code blocks
- Doesn't specify exact JSON structure
- Doesn't emphasize JSON-only output

**Enhanced Prompt**:

```javascript
buildSystemPrompt() {
  return `You are an expert contract analyst specializing in risk assessment and compliance validation for Atlantic Pipe Services.

CRITICAL OUTPUT REQUIREMENT: You MUST respond with ONLY valid JSON. Do NOT include:
- Markdown code blocks (no \`\`\`json)
- Explanations before or after the JSON
- Any text outside the JSON structure
- Comments within the JSON

When analyzing a contract clause, respond with EXACTLY this JSON structure:

{
  "Clause Summary": "one-sentence summary of what this clause does",
  "Risk Triggers Identified": "bullet-point list of specific risks or concerning language",
  "Flow-Down Obligations": "what obligations must flow down to subcontractors, if any",
  "Redline Recommendations": "specific language changes to mitigate risk (exact phrase changes)",
  "Harmful Language / Policy Conflicts": "any language that conflicts with company policy or standard terms",
  "risk_level": "high"
}

FIELD REQUIREMENTS:
- All fields must be present (no omissions)
- All values must be strings (no arrays, no nested objects)
- "risk_level" must be exactly one of: "high", "moderate", "low"
- Use bullet points (- ) for lists within string fields
- Be thorough but concise

Your analysis should:
1. Identify risks across administrative, technical, legal, regulatory, and data categories
2. Provide clear, actionable risk assessments
3. Follow the CR2A analysis framework strictly
4. Be conservative in risk assessment - when in doubt, flag for human review

Output ONLY the JSON. No markdown. No explanation.`;
}
```

## Data Models

### Configuration Data Model

```javascript
// Stored in localStorage as 'cr2a_config'
interface CR2AConfig {
  api_key?: string;              // OpenAI API key (optional if using LM Studio)
  model?: string;                // OpenAI model name
  lmstudio_base_url: string;     // LM Studio API endpoint
  lmstudio_model_id: string;     // Model identifier in LM Studio
  api_mode: 'openai' | 'lmstudio'; // Which API to use
  timeout_ms?: number;           // Request timeout (default: 120000)
  max_retries?: number;          // Retry attempts (default: 2)
}
```

### API Request Model

```javascript
// Request payload (OpenAI-compatible format)
interface ChatCompletionRequest {
  model: string;                 // Model identifier
  messages: Array<{
    role: 'system' | 'user' | 'assistant';
    content: string;
  }>;
  temperature: number;           // Sampling temperature (0.0-1.0)
  max_tokens: number;            // Maximum response tokens
  stream?: boolean;              // Enable streaming responses
}
```

### API Response Model

```javascript
// Response from LM Studio or OpenAI
interface ChatCompletionResponse {
  choices: Array<{
    message: {
      content: string;           // The actual response text
    };
    finish_reason: string;
  }>;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}
```

### CR2A Analysis Model

```javascript
// Expected structure from LLM response
interface CR2AClauseAnalysis {
  "Clause Summary": string;
  "Risk Triggers Identified": string;
  "Flow-Down Obligations": string;
  "Redline Recommendations": string;
  "Harmful Language / Policy Conflicts": string;
  "risk_level": "high" | "moderate" | "low";
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property 1: Configuration Values Are Applied

*For any* OpenAI_Service instance created with a custom base URL, all API requests from that instance should use the configured base URL instead of the default endpoint.

**Validates: Requirements 1.1, 1.4**

### Property 2: Request Format Consistency

*For any* analysis request made through OpenAI_Service, the HTTP request payload should conform to the OpenAI chat completions API format (model, messages array with role/content, temperature, max_tokens).

**Validates: Requirements 1.2, 3.3**

### Property 3: Configuration Persistence Round-Trip

*For any* valid configuration object (containing base URL, model ID, API mode), saving the configuration to storage and then loading it should return an equivalent configuration object.

**Validates: Requirements 2.2**

### Property 4: JSON Extraction Robustness

*For any* response string containing valid JSON (whether wrapped in markdown code blocks, surrounded by explanatory text, or standalone), the JSON extraction logic should successfully parse and return the JSON object.

**Validates: Requirements 4.1, 4.2, 4.3**

### Property 5: Required Fields Validation

*For any* parsed JSON response from clause analysis, either all required CR2A fields ("Clause Summary", "Risk Triggers Identified", "Flow-Down Obligations", "Redline Recommendations", "Harmful Language / Policy Conflicts", "risk_level") must be present, or a validation error must be thrown.

**Validates: Requirements 4.5**

### Property 6: Retry Behavior

*For any* API request that fails with a retryable error, the service should attempt the request up to 3 times total (1 initial + 2 retries) with a 2-second delay between attempts.

**Validates: Requirements 6.1, 6.2**

### Property 7: Request Monitoring

*For any* API request (successful or failed), the service should log the attempt number, start timestamp, duration, character counts for prompt and response, and final outcome.

**Validates: Requirements 6.5, 8.1, 8.2, 8.3, 8.5**

### Property 8: Timeout Enforcement

*For any* API request with a configured timeout value, if the request duration exceeds the timeout, the request should be aborted and a timeout error should be thrown.

**Validates: Requirements 7.1, 7.4**

### Property 9: Test Utility Portability

*For any* OpenAI-compatible API endpoint (LM Studio, OpenAI, or other compatible services), the test utilities should successfully execute and validate responses when configured to use that endpoint.

**Validates: Requirements 9.5**

## Error Handling

### Error Categories

1. **Connection Errors**
   - LM Studio server not running
   - Network connectivity issues
   - Invalid base URL configuration
   - **Handling**: Provide clear error message indicating LM Studio status, suggest checking server is running

2. **Timeout Errors**
   - Request exceeds configured timeout (default 120s)
   - Streaming response stalls
   - **Handling**: Abort request, throw timeout error, trigger retry logic

3. **Response Format Errors**
   - Response is not valid JSON
   - JSON missing required fields
   - Invalid risk_level value
   - **Handling**: Attempt multi-stage JSON extraction, validate fields, throw descriptive error if all attempts fail

4. **API Errors**
   - Model not found in LM Studio
   - Invalid request parameters
   - Server error (500)
   - **Handling**: Log error details, retry if appropriate, provide actionable error message to user

5. **Configuration Errors**
   - Missing required configuration
   - Invalid URL format
   - Conflicting settings
   - **Handling**: Validate configuration on load, provide defaults, show configuration UI with error indicators

### Error Recovery Strategy

```javascript
async function makeRequestWithRetry(url, options, maxRetries = 2) {
  let lastError = null;
  
  for (let attempt = 1; attempt <= maxRetries + 1; attempt++) {
    try {
      console.log(`[API] Attempt ${attempt}/${maxRetries + 1}`);
      
      const startTime = Date.now();
      const response = await fetchWithTimeout(url, options, this.timeout);
      const duration = Date.now() - startTime;
      
      console.log(`[API] ✓ Success in ${duration}ms`);
      return response;
      
    } catch (error) {
      lastError = error;
      console.error(`[API] ✗ Attempt ${attempt} failed:`, error.message);
      
      // Don't retry on certain errors
      if (error.name === 'ValidationError' || error.name === 'ConfigError') {
        throw error;
      }
      
      // Retry with delay
      if (attempt < maxRetries + 1) {
        console.log(`[API] Retrying in 2 seconds...`);
        await sleep(2000);
      }
    }
  }
  
  // All attempts failed
  throw new Error(`Request failed after ${maxRetries + 1} attempts: ${lastError.message}`);
}
```

### User-Facing Error Messages

| Error Type | User Message | Action |
|------------|--------------|--------|
| LM Studio not running | "Cannot connect to LM Studio. Please ensure LM Studio is running and the server is started." | Show link to setup guide |
| Timeout | "Request timed out after 120 seconds. The model may be too slow or unresponsive." | Suggest using a faster model |
| Invalid JSON | "The model returned an invalid response format. Please try again or check the system prompt." | Log raw response for debugging |
| Missing fields | "The analysis is incomplete. Required fields are missing from the response." | Show which fields are missing |
| Configuration error | "Invalid LM Studio configuration. Please check your settings." | Open settings modal |

## Testing Strategy

### Dual Testing Approach

This feature requires both **unit tests** and **property-based tests** to ensure comprehensive coverage:

- **Unit tests**: Verify specific examples, edge cases, and error conditions
- **Property tests**: Verify universal properties across all inputs

Both types of tests are complementary and necessary. Unit tests catch concrete bugs in specific scenarios, while property tests verify general correctness across a wide range of inputs.

### Property-Based Testing Configuration

We will use **fast-check** (already in package.json) for property-based testing in JavaScript:

```javascript
import fc from 'fast-check';
import { describe, it, expect } from 'vitest';

// Example property test
describe('OpenAIService Properties', () => {
  it('Property 1: Configuration values are applied', () => {
    fc.assert(
      fc.property(
        fc.webUrl(), // Generate random URLs
        (baseUrl) => {
          const service = new OpenAIService('test-key', baseUrl);
          // Verify the service uses the configured URL
          expect(service.baseUrl).toBe(baseUrl);
        }
      ),
      { numRuns: 100 } // Run 100 iterations
    );
  });
});
```

Each property test must:
- Run a minimum of **100 iterations** (due to randomization)
- Reference its design document property in a comment
- Use the tag format: `// Feature: lm-studio-migration, Property N: [property text]`

### Unit Testing Focus

Unit tests should focus on:

1. **Specific Examples**
   - Test connection with default localhost:1234
   - Test connection with custom URL
   - Test with OpenAI cloud endpoint

2. **Edge Cases**
   - Empty response handling
   - Malformed JSON responses
   - Missing required fields
   - Invalid risk_level values

3. **Error Conditions**
   - Connection refused (LM Studio not running)
   - Timeout scenarios
   - Network errors
   - Invalid configuration

4. **Integration Points**
   - Settings UI saves and loads configuration
   - Workflow controller works with both OpenAI and LM Studio
   - Test connection button provides accurate status

### Test Files Structure

```
tests/
├── unit/
│   ├── openai-service.test.js          # Unit tests for OpenAIService
│   ├── config-manager.test.js          # Unit tests for ConfigManager
│   ├── json-extraction.test.js         # Unit tests for JSON parsing
│   └── settings-ui.test.js             # Unit tests for settings UI
├── properties/
│   ├── configuration.property.test.js  # Property tests for configuration
│   ├── json-extraction.property.test.js # Property tests for JSON handling
│   ├── retry-logic.property.test.js    # Property tests for retry behavior
│   └── timeout.property.test.js        # Property tests for timeout handling
└── integration/
    ├── lmstudio-connection.test.js     # Integration test with mock LM Studio
    └── end-to-end-workflow.test.js     # Full workflow test
```

### Manual Testing Checklist

Before considering the migration complete, manually verify:

1. ✅ LM Studio server starts and shows model loaded
2. ✅ Settings UI displays LM Studio configuration fields
3. ✅ Test Connection button correctly reports server status
4. ✅ Upload a sample contract PDF
5. ✅ Analysis completes successfully with LM Studio
6. ✅ All CR2A fields are present in the output
7. ✅ Risk levels are assigned correctly
8. ✅ Download report works
9. ✅ Switch to OpenAI mode and verify it still works
10. ✅ Error messages are clear when LM Studio is not running

### Performance Benchmarks

Expected performance with LM Studio (Qwen2.5-7B on typical hardware):

- First request (cold start): 5-10 seconds
- Subsequent requests: 30-60 seconds per clause
- 50-clause contract: ~25-50 minutes total
- 100-clause contract: ~50-100 minutes total

Performance can be improved by:
- Using a smaller model (Phi-3-mini, Qwen2.5-3B)
- Using GPU acceleration
- Reducing max_tokens if responses are verbose
- Lowering temperature for faster sampling

## Implementation Notes

### Minimal Change Principle

The implementation should follow these guidelines:

1. **Modify, don't replace**: Update the existing `OpenAIService` class rather than creating a new one
2. **Preserve interfaces**: Keep all public method signatures unchanged
3. **Add, don't remove**: Add new functionality (JSON extraction, retry logic) without removing existing code
4. **Configuration over code**: Use settings to control behavior rather than code branches
5. **Backward compatible**: Ensure existing OpenAI integration continues to work

### Code Organization

```
frontend/services/
├── openaiService.js          # Modified: add LM Studio support
├── configManager.js          # Modified: add LM Studio config methods
├── jsonExtractor.js          # New: JSON extraction utilities
└── apiClient.js              # New: HTTP client with timeout/retry

app_integrated.js             # Modified: initialize with config
index.html                    # Modified: add LM Studio settings UI
```

### Migration Path

For users migrating from OpenAI to LM Studio:

1. Install and start LM Studio
2. Load a model (recommended: Qwen2.5-7B-Instruct)
3. Start the API server in LM Studio
4. Open CR2A application
5. Go to Settings
6. Select "LM Studio Local API"
7. Verify default URL (http://localhost:1234)
8. Click "Test Connection" to verify
9. Save settings
10. Upload and analyze a contract

The application will now use LM Studio for all analysis requests.

### Rollback Strategy

If issues arise with LM Studio:

1. Open Settings
2. Select "OpenAI Cloud API"
3. Enter OpenAI API key
4. Save settings
5. Application reverts to OpenAI

No code changes or reinstallation required.
