// OpenAI Service - Direct API Integration
// Replaces AWS Lambda + API Gateway backend
// Supports both OpenAI cloud API and LM Studio local API

// Import JSON extraction utilities
import { extractJSON, validateCR2AFields } from './jsonExtractor.js';

class OpenAIService {
  constructor(apiKey, baseUrl = null, modelId = null) {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl || 'https://api.openai.com/v1';
    this.model = modelId || 'gpt-4-turbo-preview'; // or 'gpt-4' for more stable
    this.maxTokens = 4000;
    this.temperature = 0.3; // Lower for more consistent analysis
    this.timeout = 120000; // 120 seconds default timeout
    this.maxRetries = 2; // Default 2 retries (3 total attempts)
    this.retryDelay = 2000; // Default 2 seconds between retries
    
    // Performance monitoring metrics
    this._metrics = {
      successfulRequests: 0,
      failedRequests: 0,
      totalRequests: 0,
      requestHistory: []
    };
  }

  /**
   * Make HTTP request with retry logic and timeout enforcement
   * @param {string} url - The API endpoint URL
   * @param {object} options - Fetch options (method, headers, body)
   * @param {number} maxRetries - Maximum number of retry attempts (default: 2)
   * @returns {Promise<Response>} The fetch response
   * @private
   */
  async _makeRequestWithRetry(url, options, maxRetries = this.maxRetries) {
    let lastError = null;
    const totalAttempts = maxRetries + 1;

    for (let attempt = 1; attempt <= totalAttempts; attempt++) {
      try {
        console.log(`[API] Attempt ${attempt}/${totalAttempts}`);
        
        // Use provided signal if available (for streaming), otherwise create new AbortController
        const usingProvidedSignal = options.signal !== undefined;
        const controller = usingProvidedSignal ? null : new AbortController();
        const timeoutId = usingProvidedSignal ? null : setTimeout(() => controller.abort(), this.timeout);
        
        // Add signal to fetch options if not already provided
        const fetchOptions = usingProvidedSignal ? options : {
          ...options,
          signal: controller.signal
        };
        
        const startTime = Date.now();
        const response = await fetch(url, fetchOptions);
        const duration = Date.now() - startTime;
        
        // Clear timeout since request completed (only if we created it)
        if (timeoutId) {
          clearTimeout(timeoutId);
        }
        
        console.log(`[API] ✓ Success in ${duration}ms`);
        return response;
        
      } catch (error) {
        lastError = error;
        const errorType = error.name === 'AbortError' ? 'Timeout' : error.message;
        console.error(`[API] ✗ Attempt ${attempt} failed: ${errorType}`);
        
        // Handle timeout errors
        if (error.name === 'AbortError') {
          lastError = new Error(`Request timed out after ${this.timeout}ms`);
          lastError.name = 'TimeoutError';
        }
        
        // Don't retry on non-retryable errors
        if (error.name === 'ValidationError' || error.name === 'ConfigError') {
          console.error(`[API] Non-retryable error, aborting`);
          throw error;
        }
        
        // Retry with delay if attempts remain
        if (attempt < totalAttempts) {
          console.log(`[API] Retrying in ${this.retryDelay}ms...`);
          await new Promise(resolve => setTimeout(resolve, this.retryDelay));
        }
      }
    }
    
    // All attempts failed - throw the last error (preserving its type)
    throw lastError;
  }

  /**
   * Analyze a contract section with OpenAI or LM Studio
   * @param {string} contractText - Full contract text
   * @param {string} promptSection - Section-specific prompt
   * @param {object} metadata - Contract metadata
   * @returns {Promise<object>} Parsed and validated CR2A analysis result
   */
  async analyzeSection(contractText, promptSection, metadata = {}) {
    // Record start timestamp for performance monitoring
    const requestStartTime = Date.now();
    let success = false;
    let promptCharCount = 0;
    let responseCharCount = 0;
    
    try {
      const systemPrompt = this.buildSystemPrompt();
      const userPrompt = this.buildUserPrompt(contractText, promptSection, metadata);
      
      // Track prompt character count
      promptCharCount = systemPrompt.length + userPrompt.length;

      const requestBody = JSON.stringify({
        model: this.model,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt }
        ],
        temperature: this.temperature,
        max_tokens: this.maxTokens
      });

      // Log request character counts
      console.log(`[API] Request - Prompt: ${userPrompt.length} chars, System: ${systemPrompt.length} chars`);

      const response = await this._makeRequestWithRetry(
        `${this.baseUrl}/chat/completions`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.apiKey}`
          },
          body: requestBody
        }
      );

      if (!response.ok) {
        // Provide clear error messages for LM Studio connection failures
        if (this.baseUrl.includes('localhost') || this.baseUrl.includes('127.0.0.1')) {
          throw new Error(`Cannot connect to LM Studio at ${this.baseUrl}. Please ensure LM Studio is running and the server is started.`);
        }
        const error = await response.json();
        throw new Error(`API error: ${error.error?.message || response.statusText}`);
      }

      const data = await response.json();
      const rawContent = data.choices[0].message.content;
      
      // Track response character count
      responseCharCount = rawContent.length;

      // Log response character count
      console.log(`[API] Response: ${rawContent.length} chars`);

      // Use JSON extraction utilities to handle various response formats
      const parsedJSON = extractJSON(rawContent);
      
      // Validate that all required CR2A fields are present
      validateCR2AFields(parsedJSON);
      
      // Mark as successful
      success = true;

      return parsedJSON;

    } catch (error) {
      console.error('API call failed:', error);
      throw error;
    } finally {
      // Calculate and log duration on request completion
      const requestDuration = Date.now() - requestStartTime;
      
      // Update metrics
      this._metrics.totalRequests++;
      if (success) {
        this._metrics.successfulRequests++;
      } else {
        this._metrics.failedRequests++;
      }
      
      // Store request metrics in history
      const requestMetrics = {
        timestamp: requestStartTime,
        duration: requestDuration,
        promptCharCount,
        responseCharCount,
        success,
        endpoint: `${this.baseUrl}/chat/completions`
      };
      this._metrics.requestHistory.push(requestMetrics);
      
      // Log performance metrics
      console.log(`[Performance] Request completed in ${requestDuration}ms - Prompt: ${promptCharCount} chars, Response: ${responseCharCount} chars, Success: ${success}`);
      console.log(`[Performance] Total requests: ${this._metrics.totalRequests}, Successful: ${this._metrics.successfulRequests}, Failed: ${this._metrics.failedRequests}`);
    }
  }

  /**
   * Stream analysis for real-time progress display
   * @param {string} contractText - Full contract text
   * @param {string} promptSection - Section-specific prompt
   * @param {function} onChunk - Callback for each chunk
   * @param {object} metadata - Contract metadata
   * @returns {Promise<object>} Parsed and validated CR2A analysis result
   */
  async streamAnalysis(contractText, promptSection, onChunk, metadata = {}) {
    // Record start timestamp for performance monitoring
    const requestStartTime = Date.now();
    let success = false;
    let promptCharCount = 0;
    let responseCharCount = 0;
    
    // Create AbortController for timeout enforcement across entire streaming operation
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);
    
    try {
      const systemPrompt = this.buildSystemPrompt();
      const userPrompt = this.buildUserPrompt(contractText, promptSection, metadata);
      
      // Track prompt character count
      promptCharCount = systemPrompt.length + userPrompt.length;

      const requestBody = JSON.stringify({
        model: this.model,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt }
        ],
        temperature: this.temperature,
        max_tokens: this.maxTokens,
        stream: true
      });

      // Log request character counts
      console.log(`[API] Stream Request - Prompt: ${userPrompt.length} chars, System: ${systemPrompt.length} chars`);

      const response = await this._makeRequestWithRetry(
        `${this.baseUrl}/chat/completions`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.apiKey}`
          },
          body: requestBody,
          signal: controller.signal
        }
      );

      if (!response.ok) {
        // Provide clear error messages for LM Studio connection failures
        if (this.baseUrl.includes('localhost') || this.baseUrl.includes('127.0.0.1')) {
          throw new Error(`Cannot connect to LM Studio at ${this.baseUrl}. Please ensure LM Studio is running and the server is started.`);
        }
        throw new Error(`API error: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let fullContent = '';

      while (true) {
        // Check if aborted before reading next chunk
        if (controller.signal.aborted) {
          reader.cancel();
          throw new Error(`Request timed out after ${this.timeout}ms`);
        }
        
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;

            try {
              const parsed = JSON.parse(data);
              const content = parsed.choices[0]?.delta?.content;
              if (content) {
                fullContent += content;
                onChunk(content);
              }
            } catch (e) {
              // Skip malformed chunks
              console.warn('Skipped malformed chunk:', e);
            }
          }
        }
      }

      // Clear timeout since streaming completed successfully
      clearTimeout(timeoutId);
      
      // Track response character count
      responseCharCount = fullContent.length;

      // Log response character count
      console.log(`[API] Stream Response: ${fullContent.length} chars`);

      // After streaming completes, extract and validate JSON from the full content
      const parsedJSON = extractJSON(fullContent);
      validateCR2AFields(parsedJSON);
      
      // Mark as successful
      success = true;

      return parsedJSON;

    } catch (error) {
      // Clear timeout on error
      clearTimeout(timeoutId);
      
      // Convert AbortError to TimeoutError for consistency
      if (error.name === 'AbortError') {
        const timeoutError = new Error(`Request timed out after ${this.timeout}ms`);
        timeoutError.name = 'TimeoutError';
        console.error('Streaming failed:', timeoutError);
        throw timeoutError;
      }
      
      console.error('Streaming failed:', error);
      throw error;
    } finally {
      // Calculate and log duration on request completion
      const requestDuration = Date.now() - requestStartTime;
      
      // Update metrics
      this._metrics.totalRequests++;
      if (success) {
        this._metrics.successfulRequests++;
      } else {
        this._metrics.failedRequests++;
      }
      
      // Store request metrics in history
      const requestMetrics = {
        timestamp: requestStartTime,
        duration: requestDuration,
        promptCharCount,
        responseCharCount,
        success,
        endpoint: `${this.baseUrl}/chat/completions`,
        streaming: true
      };
      this._metrics.requestHistory.push(requestMetrics);
      
      // Log performance metrics
      console.log(`[Performance] Stream request completed in ${requestDuration}ms - Prompt: ${promptCharCount} chars, Response: ${responseCharCount} chars, Success: ${success}`);
      console.log(`[Performance] Total requests: ${this._metrics.totalRequests}, Successful: ${this._metrics.successfulRequests}, Failed: ${this._metrics.failedRequests}`);
    }
  }

  /**
   * Build system prompt for contract analysis with explicit JSON-only output requirements
   */
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

  /**
   * Build user prompt with contract text and section instructions
   */
  buildUserPrompt(contractText, promptSection, metadata) {
    const metadataStr = Object.entries(metadata)
      .map(([key, value]) => `${key}: ${value}`)
      .join('\n');

    return `${promptSection}

CONTRACT METADATA:
${metadataStr}

CONTRACT TEXT:
${contractText}

Please analyze this contract section according to the instructions above. Provide your analysis in the structured format specified.`;
  }

  /**
   * Test API key validity
   */
  async testConnection() {
    try {
      const response = await this._makeRequestWithRetry(
        `${this.baseUrl}/models`,
        {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${this.apiKey}`
          }
        },
        0 // No retries for connection test
      );

      return response.ok;
    } catch (error) {
      return false;
    }
  }

  /**
   * Get available models
   */
  async getModels() {
    try {
      const response = await this._makeRequestWithRetry(
        `${this.baseUrl}/models`,
        {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${this.apiKey}`
          }
        },
        0 // No retries for model listing
      );

      if (!response.ok) {
        throw new Error('Failed to fetch models');
      }

      const data = await response.json();
      return data.data
        .filter(model => model.id.startsWith('gpt'))
        .map(model => model.id);
    } catch (error) {
      console.error('Failed to get models:', error);
      return [];
    }
  }

  /**
   * Estimate token count (rough approximation)
   */
  estimateTokens(text) {
    // Rough estimate: ~4 characters per token
    return Math.ceil(text.length / 4);
  }

  /**
   * Check if text is within token limits
   */
  isWithinTokenLimit(text, maxTokens = 8000) {
    return this.estimateTokens(text) < maxTokens;
  }

  /**
   * Get performance metrics
   * @returns {object} Performance metrics including request counts and history
   */
  getMetrics() {
    return {
      ...this._metrics,
      requestHistory: [...this._metrics.requestHistory] // Return a copy
    };
  }

  /**
   * Reset performance metrics
   */
  resetMetrics() {
    this._metrics = {
      successfulRequests: 0,
      failedRequests: 0,
      totalRequests: 0,
      requestHistory: []
    };
  }
}

// Export for use in other modules
export default OpenAIService;
