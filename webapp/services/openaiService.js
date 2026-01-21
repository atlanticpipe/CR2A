// OpenAI Service - Direct API Integration
// Replaces AWS Lambda + API Gateway backend

class OpenAIService {
  constructor(apiKey) {
    this.apiKey = apiKey;
    this.baseUrl = 'https://api.openai.com/v1';
    this.model = 'gpt-4-turbo-preview'; // or 'gpt-4' for more stable
    this.maxTokens = 4000;
    this.temperature = 0.3; // Lower for more consistent analysis
  }

  /**
   * Analyze a contract section with OpenAI
   * @param {string} contractText - Full contract text
   * @param {string} promptSection - Section-specific prompt
   * @param {object} metadata - Contract metadata
   * @returns {Promise<string>} Analysis result
   */
  async analyzeSection(contractText, promptSection, metadata = {}) {
    try {
      const systemPrompt = this.buildSystemPrompt();
      const userPrompt = this.buildUserPrompt(contractText, promptSection, metadata);

      const response = await fetch(`${this.baseUrl}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.apiKey}`
        },
        body: JSON.stringify({
          model: this.model,
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: userPrompt }
          ],
          temperature: this.temperature,
          max_tokens: this.maxTokens
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(`OpenAI API error: ${error.error?.message || response.statusText}`);
      }

      const data = await response.json();
      return data.choices[0].message.content;

    } catch (error) {
      console.error('OpenAI API call failed:', error);
      throw error;
    }
  }

  /**
   * Stream analysis for real-time progress display
   * @param {string} contractText - Full contract text
   * @param {string} promptSection - Section-specific prompt
   * @param {function} onChunk - Callback for each chunk
   * @param {object} metadata - Contract metadata
   */
  async streamAnalysis(contractText, promptSection, onChunk, metadata = {}) {
    try {
      const systemPrompt = this.buildSystemPrompt();
      const userPrompt = this.buildUserPrompt(contractText, promptSection, metadata);

      const response = await fetch(`${this.baseUrl}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.apiKey}`
        },
        body: JSON.stringify({
          model: this.model,
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: userPrompt }
          ],
          temperature: this.temperature,
          max_tokens: this.maxTokens,
          stream: true
        })
      });

      if (!response.ok) {
        throw new Error(`OpenAI API error: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
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
                onChunk(content);
              }
            } catch (e) {
              // Skip malformed chunks
              console.warn('Skipped malformed chunk:', e);
            }
          }
        }
      }

    } catch (error) {
      console.error('Streaming failed:', error);
      throw error;
    }
  }

  /**
   * Build system prompt for contract analysis
   */
  buildSystemPrompt() {
    return `You are an expert contract analyst specializing in risk assessment and compliance validation for Atlantic Pipe Services. Your role is to:

1. Analyze contracts against company policies and industry standards
2. Identify risks across administrative, technical, legal, regulatory, and data categories
3. Provide clear, actionable risk assessments
4. Follow the CR2A analysis framework strictly
5. Output structured data in the exact format requested

Be thorough, precise, and conservative in risk assessment. When in doubt, flag potential issues for human review.`;
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
      const response = await fetch(`${this.baseUrl}/models`, {
        headers: {
          'Authorization': `Bearer ${this.apiKey}`
        }
      });

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
      const response = await fetch(`${this.baseUrl}/models`, {
        headers: {
          'Authorization': `Bearer ${this.apiKey}`
        }
      });

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
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = OpenAIService;
}
