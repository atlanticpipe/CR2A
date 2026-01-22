/**
 * Global test setup for Vitest
 * 
 * This file runs before all tests and sets up the testing environment.
 */

// Mock browser APIs that might not be available in test environment
global.localStorage = {
  data: {},
  getItem(key) {
    return this.data[key] || null;
  },
  setItem(key, value) {
    this.data[key] = value;
  },
  removeItem(key) {
    delete this.data[key];
  },
  clear() {
    this.data = {};
  }
};

global.sessionStorage = {
  data: {},
  getItem(key) {
    return this.data[key] || null;
  },
  setItem(key, value) {
    this.data[key] = value;
  },
  removeItem(key) {
    delete this.data[key];
  },
  clear() {
    this.data = {};
  }
};

// Mock console methods to reduce noise in tests (optional)
// Uncomment if you want to suppress console output during tests
// global.console = {
//   ...console,
//   log: vi.fn(),
//   debug: vi.fn(),
//   info: vi.fn(),
//   warn: vi.fn(),
//   error: vi.fn(),
// };

// Setup and teardown hooks
beforeEach(() => {
  // Clear storage before each test
  localStorage.clear();
  sessionStorage.clear();
});

afterEach(() => {
  // Cleanup after each test
  localStorage.clear();
  sessionStorage.clear();
});
