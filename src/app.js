const express = require('express');
const { validateRequest } = require('./validation');
const { errorHandler } = require('./error-handler');

/**
 * Create and configure Express application
 * @param {OpenAIClient} openaiClient - Initialized OpenAI client instance
 * @returns {express.Application} Configured Express app
 */
function createApp(openaiClient) {
  const app = express();

  // Add JSON body parser middleware
  app.use(express.json());

  // POST /api/chat endpoint
  app.post('/api/chat', validateRequest, async (req, res, next) => {
    try {
      const { message, model } = req.body;
      
      // Call OpenAI client with message
      const result = await openaiClient.sendMessage(message, model);
      
      // Return formatted response
      res.json({
        response: result.response,
        model: result.model,
        usage: result.usage
      });
    } catch (error) {
      next(error);
    }
  });

  // Configure error handler (must be last)
  app.use(errorHandler);

  return app;
}

module.exports = { createApp };
