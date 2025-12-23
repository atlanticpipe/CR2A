/**
 * Environment Configuration for CR2A Frontend
 * Configure API endpoints and other runtime settings
 */

window.env = {
  // API Base URL
  // Local development: http://localhost:5000
  // Production: https://api.cr2a.atlanticpipe.us
  API_BASE_URL: process.env.API_BASE_URL || 'http://localhost:5000',

  // Feature flags
  FEATURES: {
    STREAMING_PROGRESS: true,
    PDF_EXPORT: false, // Set to true when PDF export implemented
    BATCH_UPLOAD: false, // Set to true when batch processing implemented
    CUSTOM_RULES: false, // Set to true when custom rules UI implemented
  },

  // UI Configuration
  UI: {
    THEME: 'light', // 'light' or 'dark'
    RESULT_PAGE_SIZE: 10,
    MAX_FILE_SIZE_MB: 500,
    ALLOWED_FILE_TYPES: ['pdf', 'docx', 'txt'],
  },

  // Timeout settings (milliseconds)
  TIMEOUTS: {
    ANALYSIS_MAX: 600000, // 10 minutes
    STREAM_HEARTBEAT: 30000, // 30 seconds
    API_CALL: 30000, // 30 seconds
  },

  // Logging
  DEBUG: false, // Set to true for verbose logging
  LOG_LEVEL: 'info', // 'debug', 'info', 'warn', 'error'
};

// Log configuration on load (development only)
if (window.env.DEBUG) {
  console.log('CR2A Frontend Configuration:', window.env);
}
