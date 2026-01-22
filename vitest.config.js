import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    // Test environment
    environment: 'happy-dom',
    
    // Global test setup
    globals: true,
    
    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'tests/',
        'frontend/__tests__/',
        '**/*.test.js',
        '**/*.spec.js',
        'vitest.config.js',
        'coverage/',
        '.venv/',
        '__pycache__/',
        '*.config.js'
      ],
      // Minimum coverage thresholds (80% as per requirements)
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80
      }
    },
    
    // Test file patterns
    include: [
      'frontend/__tests__/**/*.test.js',
      'frontend/__tests__/**/*.spec.js',
      'tests/**/*.test.js',
      'tests/**/*.spec.js'
    ],
    
    // Test timeout
    testTimeout: 10000,
    
    // Setup files
    setupFiles: ['./frontend/__tests__/setup.js']
  }
});
