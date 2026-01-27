# Design Document: OpenAI API Backend

## Overview

This design describes a minimal backend service that provides a simple HTTP interface for calling the OpenAI API. The service acts as a thin proxy layer, accepting input via a POST endpoint, forwarding it to OpenAI's chat completions API, and returning the response. The design prioritizes simplicity and getting a working foundation in place before adding any business logic.

The service will be implemented as a Node.js/Express application due to its simplicity for HTTP services and excellent OpenAI SDK support.

## Architecture

The system follows a simple three-layer architecture:

```
Client → HTTP Server → OpenAI API
```

**Components:**
1. **HTTP Server**: Express.js server that handles incoming requests
2. **OpenAI Client**: Official OpenAI SDK client for API communication
3. **Configuration Module**: Environment variable management
4. **Error Handler**: Centralized error handling and response formatting

**Flow:**
1. Client sends POST request with input text
2. Server validates request body
3. Server calls OpenAI API with input
4. Server receives OpenAI response
5. Server returns response to client

## Components and Interfaces

### HTTP Server Component

**Responsibilities:**
- Start HTTP server on configured port
- Define POST endpoint for accepting requests
- Parse JSON request bodies
- Route requests to appropriate handlers

**Interface:**
```javascript
// POST /api/chat
// Request body:
{
  "message": string,      // Required: The input text to send to OpenAI
  "model": string         // Optional: Override default model
}

// Success response (200):
{
  "response": string,     // The OpenAI completion text
  "model": string,        // The model used
  "usage": {              // Token usage information
    "prompt_tokens": number,
    "completion_tokens": number,
    "total_tokens": number
  }
}

// Error response (4xx/5xx):
{
  "error": string,        // Error message
  "details": string       // Optional: Additional error details
}
```

### OpenAI Client Component

**Responsibilities:**
- Initialize OpenAI SDK with API key
- Send chat completion requests
- Handle API responses and errors
- Manage API authentication

**Interface:**
```javascript
class OpenAIClient {
  constructor(apiKey, defaultModel)
  
  async sendMessage(message, model = null)
  // Returns: { response, model, usage }
  // Throws: Error with descriptive message on failure
}
```

### Configuration Module

**Responsibilities:**
- Load environment variables
- Validate required configuration
- Provide default values
- Fail fast if critical config is missing

**Interface:**
```javascript
const config = {
  openaiApiKey: string,      // Required: OPENAI_API_KEY
  port: number,              // Optional: PORT (default: 3000)
  defaultModel: string,      // Optional: OPENAI_MODEL (default: gpt-4)
  nodeEnv: string           // Optional: NODE_ENV (default: development)
}

function validateConfig()
// Throws: Error if required config is missing
```

### Error Handler Component

**Responsibilities:**
- Catch and format errors
- Map error types to HTTP status codes
- Log errors appropriately
- Return consistent error responses

**Error Mapping:**
- Missing/invalid request body → 400 Bad Request
- OpenAI authentication error → 401 Unauthorized
- OpenAI rate limit → 429 Too Many Requests
- OpenAI API error → 502 Bad Gateway
- Internal server error → 500 Internal Server Error

## Data Models

### Request Model
```javascript
{
  message: string,        // Required, non-empty
  model: string          // Optional, valid OpenAI model name
}
```

**Validation Rules:**
- `message` must be present and non-empty string
- `model` if provided must be a string

### Response Model
```javascript
{
  response: string,       // The completion text from OpenAI
  model: string,         // The model that was used
  usage: {
    prompt_tokens: number,
    completion_tokens: number,
    total_tokens: number
  }
}
```

### Error Model
```javascript
{
  error: string,         // Human-readable error message
  details: string        // Optional additional context
}
```


## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property 1: Valid Requests Are Processed

*For any* request body containing a non-empty "message" field, the backend service should accept the request and forward it to the OpenAI API without returning a 400 error.

**Validates: Requirements 1.2, 1.4**

### Property 2: Invalid Requests Return 400

*For any* request body missing the required "message" field or containing an empty message, the backend service should return a 400 Bad Request status code.

**Validates: Requirements 1.3**

### Property 3: OpenAI Requests Include Authentication

*For any* valid request processed by the backend service, the outgoing OpenAI API call should include the API key in the authorization header and the input message in the request body.

**Validates: Requirements 2.1, 2.2**

### Property 4: Successful Responses Preserve Essential Content

*For any* successful OpenAI API response, the backend service response should contain the completion text, model name, and usage information from the OpenAI response.

**Validates: Requirements 3.1, 3.3**

### Property 5: OpenAI Errors Are Propagated

*For any* error returned by the OpenAI API, the backend service should return an error response to the client with an appropriate HTTP status code (not 200).

**Validates: Requirements 3.2**

### Property 6: Responses Are Valid JSON

*For any* response (success or error) returned by the backend service, the response body should be valid JSON and include the Content-Type header "application/json".

**Validates: Requirements 3.4**

### Property 7: Errors Include Descriptive Messages

*For any* error response returned by the backend service, the response body should contain a non-empty "error" field with a descriptive message.

**Validates: Requirements 4.3, 4.4**

## Error Handling

The service implements a centralized error handling strategy:

**Error Categories:**

1. **Client Errors (4xx)**
   - Missing/invalid request body → 400 with validation message
   - Authentication failures → 401 with auth error message
   - Rate limiting → 429 with rate limit message

2. **Server Errors (5xx)**
   - OpenAI API errors → 502 with gateway error message
   - Internal errors → 500 with generic error message

**Error Handling Flow:**
```
Request → Validation → OpenAI Call → Response
            ↓             ↓            ↓
         400 Error    502 Error    Success
```

**Logging Strategy:**
- Log all errors with stack traces in development
- Log error messages only in production (no sensitive data)
- Include request ID for error tracking
- Log OpenAI API errors separately for monitoring

**Error Response Format:**
All errors follow the consistent Error Model format with descriptive messages that help clients understand what went wrong without exposing sensitive implementation details.

## Testing Strategy

The testing strategy employs both unit tests and property-based tests to ensure comprehensive coverage.

**Property-Based Testing:**
- Use a property-based testing library (fast-check for JavaScript/Node.js)
- Configure each property test to run minimum 100 iterations
- Each test references its corresponding design property
- Tag format: `Feature: openai-api-backend, Property N: [property text]`
- Property tests validate universal correctness across randomized inputs

**Unit Testing:**
- Test specific examples of valid and invalid requests
- Test edge cases: empty strings, missing fields, malformed JSON
- Test error conditions: network failures, API errors, rate limits
- Test configuration loading and validation
- Mock OpenAI API calls to avoid external dependencies

**Test Organization:**
```
tests/
  ├── unit/
  │   ├── config.test.js          # Configuration loading
  │   ├── validation.test.js      # Request validation
  │   ├── error-handler.test.js   # Error handling
  │   └── openai-client.test.js   # OpenAI client
  └── properties/
      ├── request-validation.property.test.js
      ├── response-format.property.test.js
      └── error-handling.property.test.js
```

**Testing Tools:**
- Jest or Mocha for test runner
- fast-check for property-based testing
- Supertest for HTTP endpoint testing
- Nock or MSW for mocking OpenAI API calls

**Coverage Goals:**
- Unit tests cover specific examples and edge cases
- Property tests cover universal behaviors across all inputs
- Together they provide comprehensive validation of correctness
