const OpenAI = require('openai');

class OpenAIClient {
  constructor(apiKey, defaultModel = 'gpt-4') {
    if (!apiKey) {
      throw new Error('OpenAI API key is required');
    }
    
    this.client = new OpenAI({
      apiKey: apiKey
    });
    this.defaultModel = defaultModel;
  }

  async sendMessage(message, model = null) {
    try {
      const modelToUse = model || this.defaultModel;
      
      const completion = await this.client.chat.completions.create({
        model: modelToUse,
        messages: [
          {
            role: 'user',
            content: message
          }
        ]
      });

      return {
        response: completion.choices[0].message.content,
        model: completion.model,
        usage: {
          prompt_tokens: completion.usage.prompt_tokens,
          completion_tokens: completion.usage.completion_tokens,
          total_tokens: completion.usage.total_tokens
        }
      };
    } catch (error) {
      // Wrap and provide descriptive error messages
      if (error.status === 401) {
        throw new Error('OpenAI authentication failed: Invalid API key');
      } else if (error.status === 429) {
        throw new Error('OpenAI rate limit exceeded: Too many requests');
      } else if (error.code === 'ENOTFOUND' || error.code === 'ECONNREFUSED') {
        throw new Error('OpenAI API is unreachable: Network error');
      } else if (error.message) {
        throw new Error(`OpenAI API error: ${error.message}`);
      } else {
        throw new Error('OpenAI API error: Unknown error occurred');
      }
    }
  }
}

module.exports = OpenAIClient;
