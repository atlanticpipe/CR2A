/**
 * Test fixtures and utilities for JavaScript tests
 * 
 * This module provides reusable test data and helper functions.
 */

/**
 * Sample contract text for testing file parsing
 */
export const sampleContractText = `
CONTRACT AGREEMENT

This agreement is made between Party A and Party B.

TERMS AND CONDITIONS:
1. Payment terms: Net 30 days
2. Delivery schedule: As specified in Appendix A
3. Warranty period: 12 months from delivery

SIGNATURES:
Party A: _______________
Party B: _______________
`.trim();

/**
 * Sample structured analysis response for testing
 */
export const sampleAnalysisResponse = {
  findings: [
    {
      item_name: "Payment Terms",
      risk_level: "Low",
      description: "Standard payment terms of Net 30 days",
      recommendation: "No changes needed"
    },
    {
      item_name: "Warranty Period",
      risk_level: "Medium",
      description: "12-month warranty may be insufficient",
      recommendation: "Consider extending to 24 months"
    }
  ],
  summary: "Overall contract appears standard with minor recommendations"
};

/**
 * Sample OpenAI API response for testing
 */
export const sampleOpenAIResponse = {
  id: "chatcmpl-test123",
  object: "chat.completion",
  created: 1234567890,
  model: "gpt-4",
  choices: [
    {
      index: 0,
      message: {
        role: "assistant",
        content: JSON.stringify(sampleAnalysisResponse)
      },
      finish_reason: "stop"
    }
  ],
  usage: {
    prompt_tokens: 100,
    completion_tokens: 50,
    total_tokens: 150
  }
};

/**
 * Create a mock File object for testing file uploads
 */
export function createMockFile(content, filename = 'test.txt', type = 'text/plain') {
  const blob = new Blob([content], { type });
  blob.name = filename;
  return blob;
}

/**
 * Create a mock DOM element for testing UI components
 */
export function createMockElement(tag = 'div', attributes = {}) {
  const element = document.createElement(tag);
  Object.entries(attributes).forEach(([key, value]) => {
    if (key === 'className') {
      element.className = value;
    } else if (key === 'innerHTML') {
      element.innerHTML = value;
    } else {
      element.setAttribute(key, value);
    }
  });
  return element;
}

/**
 * Wait for a condition to be true (useful for async testing)
 */
export async function waitFor(condition, timeout = 5000, interval = 100) {
  const startTime = Date.now();
  while (Date.now() - startTime < timeout) {
    if (await condition()) {
      return true;
    }
    await new Promise(resolve => setTimeout(resolve, interval));
  }
  throw new Error(`Timeout waiting for condition after ${timeout}ms`);
}

/**
 * Create a mock fetch response
 */
export function createMockFetchResponse(data, status = 200, statusText = 'OK') {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText,
    json: async () => data,
    text: async () => JSON.stringify(data),
    headers: new Headers({
      'Content-Type': 'application/json'
    })
  };
}

/**
 * Create a mock streaming response for testing SSE
 */
export function createMockStreamResponse(chunks) {
  const encoder = new TextEncoder();
  let index = 0;
  
  return {
    ok: true,
    status: 200,
    body: {
      getReader() {
        return {
          async read() {
            if (index >= chunks.length) {
              return { done: true };
            }
            const chunk = encoder.encode(chunks[index++]);
            return { done: false, value: chunk };
          }
        };
      }
    }
  };
}

/**
 * Mock localStorage for tests that need it
 */
export function mockLocalStorage() {
  const storage = {};
  return {
    getItem: (key) => storage[key] || null,
    setItem: (key, value) => { storage[key] = value; },
    removeItem: (key) => { delete storage[key]; },
    clear: () => { Object.keys(storage).forEach(key => delete storage[key]); },
    get length() { return Object.keys(storage).length; },
    key: (index) => Object.keys(storage)[index] || null
  };
}

/**
 * Create a mock progress callback for testing
 */
export function createMockProgressCallback() {
  const calls = [];
  const callback = (progress) => {
    calls.push(progress);
  };
  callback.calls = calls;
  callback.getLastCall = () => calls[calls.length - 1];
  callback.getCallCount = () => calls.length;
  callback.reset = () => { calls.length = 0; };
  return callback;
}

/**
 * Sample PDF export configuration for testing
 */
export const samplePDFConfig = {
  title: "CR2A Analysis Report",
  contractId: "TEST-001",
  date: "2024-01-01",
  findings: sampleAnalysisResponse.findings,
  summary: sampleAnalysisResponse.summary
};
