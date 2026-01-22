/**
 * Tests for error-handler.js - Centralized error handling
 * Requirements: 14.4
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('ErrorHandler - Centralized Error Handling', () => {
  let ErrorHandler;
  let errorHandler;

  beforeEach(async () => {
    // Set up DOM structure
    document.body.innerHTML = '';

    // Mock notification system
    global.notify = {
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn()
    };

    // Load ErrorHandler class
    const errorHandlerPath = path.join(process.cwd(), 'frontend', 'error-handler.js');
    const errorHandlerCode = fs.readFileSync(errorHandlerPath, 'utf-8');
    
    // Execute the code to define ErrorHandler
    eval(errorHandlerCode);
    
    ErrorHandler = window.ErrorHandler;
    errorHandler = new ErrorHandler();
  });

  afterEach(() => {
    vi.clearAllMocks();
    if (errorHandler) {
      errorHandler.clearErrorLog();
    }
  });

  describe('Initialization', () => {
    it('should create ErrorHandler instance', () => {
      expect(errorHandler).toBeDefined();
      expect(errorHandler).toBeInstanceOf(ErrorHandler);
    });

    it('should initialize with empty error log', () => {
      expect(errorHandler.errorLog).toBeDefined();
      expect(Array.isArray(errorHandler.errorLog)).toBe(true);
      expect(errorHandler.errorLog.length).toBe(0);
    });

    it('should set max log size', () => {
      expect(errorHandler.maxLogSize).toBe(100);
    });

    it('should initialize retry attempts tracker', () => {
      expect(errorHandler.retryAttempts).toBeDefined();
      expect(typeof errorHandler.retryAttempts).toBe('object');
    });

    it('should set max retries', () => {
      expect(errorHandler.maxRetries).toBe(3);
    });
  });

  describe('Error Parsing', () => {
    it('should parse Error object', () => {
      const error = new Error('Test error');
      const errorInfo = errorHandler.parseError(error, 'Test Context');
      
      expect(errorInfo.message).toBe('Test error');
      expect(errorInfo.context).toBe('Test Context');
      expect(errorInfo.type).toBe('Error');
    });

    it('should parse string error', () => {
      const errorInfo = errorHandler.parseError('String error', 'Test Context');
      
      expect(errorInfo.message).toBe('String error');
      expect(errorInfo.context).toBe('Test Context');
    });

    it('should parse object with message property', () => {
      const error = { message: 'Object error' };
      const errorInfo = errorHandler.parseError(error, 'Test Context');
      
      expect(errorInfo.message).toBe('Object error');
    });

    it('should include timestamp', () => {
      const errorInfo = errorHandler.parseError('Test', 'Context');
      
      expect(errorInfo.timestamp).toBeDefined();
      expect(typeof errorInfo.timestamp).toBe('string');
    });

    it('should include technical details for Error objects', () => {
      const error = new Error('Test error');
      const errorInfo = errorHandler.parseError(error, 'Context');
      
      expect(errorInfo.technicalDetails).toBeDefined();
    });
  });

  describe('Error Classification - Network Errors', () => {
    it('should classify network errors', () => {
      const errorInfo = errorHandler.parseError('Network request failed', 'API');
      errorHandler.classifyError(errorInfo);
      
      expect(errorInfo.type).toBe('network');
      expect(errorInfo.severity).toBe('warning');
      expect(errorInfo.userMessage).toContain('Connection issue');
    });

    it('should provide recovery steps for network errors', () => {
      const errorInfo = errorHandler.parseError('Fetch timeout', 'API');
      errorHandler.classifyError(errorInfo);
      
      expect(errorInfo.recoverySteps.length).toBeGreaterThan(0);
      expect(errorInfo.recoverySteps.some(step => step.includes('internet'))).toBe(true);
    });
  });

  describe('Error Classification - API Errors', () => {
    it('should classify unauthorized API errors', () => {
      const errorInfo = errorHandler.parseError('401 unauthorized', 'OpenAI');
      errorHandler.classifyError(errorInfo);
      
      expect(errorInfo.type).toBe('api');
      expect(errorInfo.userMessage).toContain('API key');
    });

    it('should classify rate limit errors', () => {
      const errorInfo = errorHandler.parseError('429 rate limit exceeded', 'API');
      errorHandler.classifyError(errorInfo);
      
      expect(errorInfo.type).toBe('api');
      expect(errorInfo.userMessage).toContain('rate limit');
    });

    it('should classify quota errors', () => {
      const errorInfo = errorHandler.parseError('Insufficient quota', 'API');
      errorHandler.classifyError(errorInfo);
      
      expect(errorInfo.type).toBe('api');
      expect(errorInfo.userMessage).toContain('quota');
    });

    it('should provide recovery steps for API errors', () => {
      const errorInfo = errorHandler.parseError('Invalid API key', 'OpenAI');
      errorHandler.classifyError(errorInfo);
      
      expect(errorInfo.recoverySteps.length).toBeGreaterThan(0);
      expect(errorInfo.recoverySteps.some(step => step.includes('Settings'))).toBe(true);
    });
  });

  describe('Error Classification - File Errors', () => {
    it('should classify file size errors', () => {
      const errorInfo = errorHandler.parseError('File too large', 'Upload');
      errorHandler.classifyError(errorInfo);
      
      expect(errorInfo.type).toBe('file');
      expect(errorInfo.userMessage).toContain('too large');
    });

    it('should classify file format errors', () => {
      const errorInfo = errorHandler.parseError('Invalid file format', 'Parser');
      errorHandler.classifyError(errorInfo);
      
      expect(errorInfo.type).toBe('file');
      expect(errorInfo.userMessage).toContain('format');
    });

    it('should classify empty file errors', () => {
      const errorInfo = errorHandler.parseError('No text found in file', 'Parser');
      errorHandler.classifyError(errorInfo);
      
      expect(errorInfo.type).toBe('file');
      expect(errorInfo.userMessage).toContain('No text');
    });

    it('should provide recovery steps for file errors', () => {
      const errorInfo = errorHandler.parseError('File parse error', 'Parser');
      errorHandler.classifyError(errorInfo);
      
      expect(errorInfo.recoverySteps.length).toBeGreaterThan(0);
    });
  });

  describe('Error Classification - Validation Errors', () => {
    it('should classify validation errors', () => {
      const errorInfo = errorHandler.parseError('Validation failed: required field', 'Form');
      errorHandler.classifyError(errorInfo);
      
      expect(errorInfo.type).toBe('validation');
      expect(errorInfo.severity).toBe('warning');
    });

    it('should provide recovery steps for validation errors', () => {
      const errorInfo = errorHandler.parseError('Invalid input', 'Form');
      errorHandler.classifyError(errorInfo);
      
      expect(errorInfo.recoverySteps.length).toBeGreaterThan(0);
      expect(errorInfo.recoverySteps.some(step => step.includes('required'))).toBe(true);
    });
  });

  describe('Error Classification - Storage Errors', () => {
    it('should classify storage errors', () => {
      const errorInfo = errorHandler.parseError('LocalStorage quota exceeded', 'Storage');
      errorHandler.classifyError(errorInfo);
      
      expect(errorInfo.type).toBe('storage');
      expect(errorInfo.userMessage).toContain('storage');
    });
  });

  describe('Error Classification - Timeout Errors', () => {
    it('should classify timeout errors', () => {
      const errorInfo = errorHandler.parseError('Request timed out', 'API');
      errorHandler.classifyError(errorInfo);
      
      expect(errorInfo.type).toBe('timeout');
      expect(errorInfo.userMessage).toContain('too long');
    });
  });

  describe('Error Classification - Unknown Errors', () => {
    it('should classify unknown errors', () => {
      const errorInfo = errorHandler.parseError('Something weird happened', 'Unknown');
      errorHandler.classifyError(errorInfo);
      
      expect(errorInfo.type).toBe('unknown');
      expect(errorInfo.userMessage).toContain('unexpected');
    });

    it('should provide generic recovery steps for unknown errors', () => {
      const errorInfo = errorHandler.parseError('Mystery error', 'Unknown');
      errorHandler.classifyError(errorInfo);
      
      expect(errorInfo.recoverySteps.length).toBeGreaterThan(0);
      expect(errorInfo.recoverySteps.some(step => step.includes('Refresh'))).toBe(true);
    });
  });

  describe('Error Logging', () => {
    it('should log error to error log', () => {
      const error = new Error('Test error');
      errorHandler.handleError(error, 'Test Context');
      
      expect(errorHandler.errorLog.length).toBe(1);
      expect(errorHandler.errorLog[0].message).toBe('Test error');
    });

    it('should maintain max log size', () => {
      // Add more than max log size
      for (let i = 0; i < 105; i++) {
        errorHandler.handleError(`Error ${i}`, 'Test');
      }
      
      expect(errorHandler.errorLog.length).toBe(100);
    });

    it('should save recent errors to localStorage', () => {
      errorHandler.handleError('Test error', 'Context');
      
      const saved = localStorage.getItem('cr2a_error_log');
      expect(saved).toBeTruthy();
      
      const parsed = JSON.parse(saved);
      expect(Array.isArray(parsed)).toBe(true);
      expect(parsed.length).toBeGreaterThan(0);
    });

    it('should keep most recent errors first', () => {
      errorHandler.handleError('First error', 'Context');
      errorHandler.handleError('Second error', 'Context');
      
      expect(errorHandler.errorLog[0].message).toBe('Second error');
      expect(errorHandler.errorLog[1].message).toBe('First error');
    });
  });

  describe('Error Notification', () => {
    it('should show error notification', () => {
      const error = new Error('Test error');
      errorHandler.handleError(error, 'Test Context');
      
      expect(window.notify.error).toHaveBeenCalled();
    });

    it('should show warning notification for warning severity', () => {
      const error = new Error('Network error');
      errorHandler.handleError(error, 'Network');
      
      expect(window.notify.warning).toHaveBeenCalled();
    });

    it('should include recovery steps in notification', () => {
      const error = new Error('API key invalid');
      errorHandler.handleError(error, 'API', { showDetails: true });
      
      const call = window.notify.error.mock.calls[0];
      expect(call[0]).toContain('What to try:');
    });

    it('should not show details when showDetails is false', () => {
      const error = new Error('Test error');
      errorHandler.handleError(error, 'Test', { showDetails: false });
      
      const call = window.notify.error.mock.calls[0];
      expect(call[0]).not.toContain('What to try:');
    });
  });

  describe('Retry Mechanism', () => {
    it('should check if retry is allowed', () => {
      expect(errorHandler.shouldRetry('TestContext')).toBe(true);
    });

    it('should track retry attempts', () => {
      errorHandler.retryAttempts['TestContext'] = 2;
      expect(errorHandler.shouldRetry('TestContext')).toBe(true);
      
      errorHandler.retryAttempts['TestContext'] = 3;
      expect(errorHandler.shouldRetry('TestContext')).toBe(false);
    });

    it('should schedule retry with delay', async () => {
      let callCount = 0;
      const retryFn = async () => {
        callCount++;
        if (callCount < 2) throw new Error('Retry needed');
        return 'success';
      };
      
      const result = await errorHandler.scheduleRetry(retryFn, 'TestContext', 10);
      
      expect(result).toBe('success');
      expect(callCount).toBe(2);
    });

    it('should reset retry count on success', async () => {
      const retryFn = async () => 'success';
      
      await errorHandler.scheduleRetry(retryFn, 'TestContext', 10);
      
      expect(errorHandler.retryAttempts['TestContext']).toBe(0);
    });

    it('should show retry notification', async () => {
      let callCount = 0;
      const retryFn = async () => {
        callCount++;
        if (callCount < 2) throw new Error('Retry');
        return 'success';
      };
      
      await errorHandler.scheduleRetry(retryFn, 'TestContext', 10);
      
      expect(window.notify.info).toHaveBeenCalled();
    });
  });

  describe('Utility Methods', () => {
    it('should wrap async function with error handling', async () => {
      const fn = async () => {
        throw new Error('Test error');
      };
      
      const result = await errorHandler.wrap(fn, 'Test Context');
      
      expect(result).toBeDefined();
      expect(errorHandler.errorLog.length).toBe(1);
    });

    it('should return result from successful wrapped function', async () => {
      const fn = async () => 'success';
      
      const result = await errorHandler.wrap(fn, 'Test Context');
      
      expect(result).toBe('success');
    });

    it('should get error log', () => {
      errorHandler.handleError('Error 1', 'Context');
      errorHandler.handleError('Error 2', 'Context');
      
      const log = errorHandler.getErrorLog();
      
      expect(log.length).toBe(2);
      expect(Array.isArray(log)).toBe(true);
    });

    it('should clear error log', () => {
      errorHandler.handleError('Error', 'Context');
      expect(errorHandler.errorLog.length).toBe(1);
      
      errorHandler.clearErrorLog();
      
      expect(errorHandler.errorLog.length).toBe(0);
      expect(localStorage.getItem('cr2a_error_log')).toBeFalsy();
    });

    it('should get error statistics', () => {
      errorHandler.handleError('Network error', 'API');
      errorHandler.handleError('File too large', 'Upload');
      errorHandler.handleError('Another network error', 'API');
      
      const stats = errorHandler.getErrorStats();
      
      expect(stats.total).toBe(3);
      expect(stats.byType).toBeDefined();
      expect(stats.bySeverity).toBeDefined();
      expect(stats.recent).toBeDefined();
      expect(stats.recent.length).toBeLessThanOrEqual(5);
    });
  });

  describe('Global Error Handlers', () => {
    it('should setup global error handlers', () => {
      // Verify that error handler is listening for global errors
      expect(errorHandler).toBeDefined();
      
      // The setupGlobalErrorHandlers method should have been called during init
      // We can't easily test the actual event listeners, but we can verify the method exists
      expect(typeof errorHandler.setupGlobalErrorHandlers).toBe('function');
    });
  });

  describe('Error Information Structure', () => {
    it('should include all required fields in error info', () => {
      const error = new Error('Test');
      const errorInfo = errorHandler.parseError(error, 'Context');
      
      expect(errorInfo.timestamp).toBeDefined();
      expect(errorInfo.context).toBeDefined();
      expect(errorInfo.originalError).toBeDefined();
      expect(errorInfo.type).toBeDefined();
      expect(errorInfo.message).toBeDefined();
      expect(errorInfo.userMessage).toBeDefined();
      expect(errorInfo.technicalDetails).toBeDefined();
      expect(errorInfo.recoverySteps).toBeDefined();
      expect(errorInfo.severity).toBeDefined();
    });
  });
});
