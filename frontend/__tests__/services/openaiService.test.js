/**
 * Tests for OpenAI Service
 * Requirements: 13.2 - Unit tests for openaiService covering API calls, error handling, and response parsing
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { sampleOpenAIResponse, createMockFetchResponse } from '../fixtures.js';

// Import OpenAIService
const OpenAIService = (await import('../../services/openaiService.js')).default;

describe('OpenAIService', () => {
  let service;
  const testApiKey = 'test-api-key-12345';

  beforeEach(() => {
    service = new OpenAIService(testApiKey);
    // Reset fetch mock
    global.fetch = vi.fn();
  });

  describe('Initialization', () => {
    it('should initialize with API key and default settings', () => {
      expect(service.apiKey).toBe(testApiKey);
      expect(service.baseUrl).toBe('https://api.openai.com/v1');
      expect(service.model).toBeDefined();
      expect(service.maxTokens).toBeGreaterThan(0);
      expect(service.temperature).toBeGreaterThanOrEqual(0);
    });

    it('should have reasonable default temperature for analysis', () => {
      expect(service.temperature).toBeLessThanOrEqual(1);
      expect(service.temperature).toBeGreaterThanOrEqual(0);
    });
  });

  describe('Prompt Building', () => {
    it('should build system prompt for contract analysis', () => {
      const systemPrompt = service.buildSystemPrompt();
      
      expect(systemPrompt).toContain('contract');
      expect(systemPrompt).toContain('risk');
      expect(systemPrompt).toContain('analysis');
      expect(systemPrompt.length).toBeGreaterThan(50);
    });

    it('should build user prompt with contract text and metadata', () => {
      const contractText = 'Sample contract text';
      const promptSection = 'Analyze payment terms';
      const metadata = {
        contract_id: 'TEST-001',
        project_title: 'Test Project'
      };

      const userPrompt = service.buildUserPrompt(contractText, promptSection, metadata);

      expect(userPrompt).toContain(contractText);
      expect(userPrompt).toContain(promptSection);
      expect(userPrompt).toContain('TEST-001');
      expect(userPrompt).toContain('Test Project');
    });

    it('should handle empty metadata gracefully', () => {
      const userPrompt = service.buildUserPrompt('contract text', 'section', {});
      expect(userPrompt).toBeDefined();
      expect(userPrompt.length).toBeGreaterThan(0);
    });
  });

  describe('Section Analysis', () => {
    it('should make API call with correct parameters', async () => {
      global.fetch = vi.fn().mockResolvedValue(
        createMockFetchResponse(sampleOpenAIResponse, 200)
      );

      const contractText = 'Test contract';
      const promptSection = 'Test section';

      await service.analyzeSection(contractText, promptSection);

      expect(global.fetch).toHaveBeenCalledTimes(1);
      const callArgs = global.fetch.mock.calls[0];
      expect(callArgs[0]).toContain('/chat/completions');
      
      const requestBody = JSON.parse(callArgs[1].body);
      expect(requestBody.model).toBeDefined();
      expect(requestBody.messages).toHaveLength(2);
      expect(requestBody.messages[0].role).toBe('system');
      expect(requestBody.messages[1].role).toBe('user');
    });

    it('should include authorization header', async () => {
      global.fetch = vi.fn().mockResolvedValue(
        createMockFetchResponse(sampleOpenAIResponse, 200)
      );

      await service.analyzeSection('contract', 'section');

      const callArgs = global.fetch.mock.calls[0];
      const headers = callArgs[1].headers;
      expect(headers.Authorization).toBe(`Bearer ${testApiKey}`);
    });

    it('should return analysis result on success', async () => {
      global.fetch = vi.fn().mockResolvedValue(
        createMockFetchResponse(sampleOpenAIResponse, 200)
      );

      const result = await service.analyzeSection('contract', 'section');

      expect(result).toBeDefined();
      expect(typeof result).toBe('string');
    });

    it('should handle API errors gracefully', async () => {
      global.fetch = vi.fn().mockResolvedValue(
        createMockFetchResponse({ error: { message: 'API Error' } }, 400)
      );

      await expect(
        service.analyzeSection('contract', 'section')
      ).rejects.toThrow('OpenAI API error');
    });

    it('should handle network errors', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      await expect(
        service.analyzeSection('contract', 'section')
      ).rejects.toThrow('Network error');
    });
  });

  describe('Token Estimation', () => {
    it('should estimate token count for text', () => {
      const shortText = 'Hello world';
      const tokens = service.estimateTokens(shortText);
      expect(tokens).toBeGreaterThan(0);
      expect(tokens).toBeLessThan(shortText.length);
    });

    it('should estimate more tokens for longer text', () => {
      const shortText = 'Short';
      const longText = 'This is a much longer text with many more words and characters';
      
      const shortTokens = service.estimateTokens(shortText);
      const longTokens = service.estimateTokens(longText);
      
      expect(longTokens).toBeGreaterThan(shortTokens);
    });

    it('should check if text is within token limit', () => {
      const shortText = 'Short text';
      const longText = 'x'.repeat(50000);

      expect(service.isWithinTokenLimit(shortText, 1000)).toBe(true);
      expect(service.isWithinTokenLimit(longText, 1000)).toBe(false);
    });
  });

  describe('Connection Testing', () => {
    it('should return true for valid API key', async () => {
      global.fetch = vi.fn().mockResolvedValue(
        createMockFetchResponse({ data: [] }, 200)
      );

      const isValid = await service.testConnection();
      expect(isValid).toBe(true);
    });

    it('should return false for invalid API key', async () => {
      global.fetch = vi.fn().mockResolvedValue(
        createMockFetchResponse({ error: 'Invalid key' }, 401)
      );

      const isValid = await service.testConnection();
      expect(isValid).toBe(false);
    });

    it('should return false on network error', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      const isValid = await service.testConnection();
      expect(isValid).toBe(false);
    });
  });

  describe('Model Management', () => {
    it('should fetch available models', async () => {
      const mockModels = {
        data: [
          { id: 'gpt-4', object: 'model' },
          { id: 'gpt-3.5-turbo', object: 'model' },
          { id: 'davinci', object: 'model' }
        ]
      };

      global.fetch = vi.fn().mockResolvedValue(
        createMockFetchResponse(mockModels, 200)
      );

      const models = await service.getModels();
      
      expect(Array.isArray(models)).toBe(true);
      expect(models.length).toBeGreaterThan(0);
      models.forEach(model => {
        expect(model).toContain('gpt');
      });
    });

    it('should filter non-GPT models', async () => {
      const mockModels = {
        data: [
          { id: 'gpt-4', object: 'model' },
          { id: 'whisper-1', object: 'model' },
          { id: 'dall-e-3', object: 'model' }
        ]
      };

      global.fetch = vi.fn().mockResolvedValue(
        createMockFetchResponse(mockModels, 200)
      );

      const models = await service.getModels();
      
      expect(models).toHaveLength(1);
      expect(models[0]).toBe('gpt-4');
    });

    it('should return empty array on error', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('API error'));

      const models = await service.getModels();
      expect(models).toEqual([]);
    });
  });

  describe('Streaming Analysis', () => {
    it('should handle streaming responses', async () => {
      const chunks = ['data: {"choices":[{"delta":{"content":"Hello"}}]}\n'];
      const mockReader = {
        read: vi.fn()
          .mockResolvedValueOnce({ done: false, value: new TextEncoder().encode(chunks[0]) })
          .mockResolvedValueOnce({ done: true })
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        body: {
          getReader: () => mockReader
        }
      });

      const receivedChunks = [];
      const onChunk = (chunk) => receivedChunks.push(chunk);

      await service.streamAnalysis('contract', 'section', onChunk);

      expect(receivedChunks.length).toBeGreaterThan(0);
    });

    it('should handle streaming errors', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Server Error'
      });

      const onChunk = vi.fn();

      await expect(
        service.streamAnalysis('contract', 'section', onChunk)
      ).rejects.toThrow();
    });
  });
});
