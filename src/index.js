const { config, validateConfig } = require('./config');
const OpenAIClient = require('./openai-client');
const { createApp } = require('./app');

/**
 * Server entry point
 * Loads configuration, initializes OpenAI client, and starts the Express server
 */
async function startServer() {
  try {
    // Validate configuration
    validateConfig();

    // Initialize OpenAI client
    const openaiClient = new OpenAIClient(config.openaiApiKey, config.defaultModel);

    // Create Express app
    const app = createApp(openaiClient);

    // Start server
    const server = app.listen(config.port, () => {
      console.log(`Server started successfully on port ${config.port}`);
      console.log(`Environment: ${config.nodeEnv}`);
      console.log(`Using model: ${config.defaultModel}`);
    });

    // Handle graceful shutdown
    process.on('SIGTERM', () => {
      console.log('SIGTERM signal received: closing HTTP server');
      server.close(() => {
        console.log('HTTP server closed');
      });
    });

    process.on('SIGINT', () => {
      console.log('SIGINT signal received: closing HTTP server');
      server.close(() => {
        console.log('HTTP server closed');
        process.exit(0);
      });
    });

  } catch (error) {
    // Catch configuration errors and other startup failures
    console.error('Failed to start server:');
    console.error(error.message);
    process.exit(1);
  }
}

// Start the server
startServer();
