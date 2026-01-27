/**
 * Centralized error handler middleware
 * Maps error types to HTTP status codes and formats error responses consistently
 */
function errorHandler(err, req, res, next) {
  // Default to 500 Internal Server Error
  let statusCode = 500;
  let errorMessage = 'An unexpected error occurred';
  let details = null;

  // Map specific error types to status codes
  if (err.message) {
    const message = err.message.toLowerCase();
    
    // Authentication errors
    if (message.includes('authentication failed') || message.includes('invalid api key')) {
      statusCode = 401;
      errorMessage = 'Authentication failed';
      details = 'Invalid or missing API key';
    }
    // Rate limit errors
    else if (message.includes('rate limit')) {
      statusCode = 429;
      errorMessage = 'Rate limit exceeded';
      details = 'Too many requests to OpenAI API';
    }
    // OpenAI API errors (gateway errors)
    else if (message.includes('openai api') || message.includes('unreachable')) {
      statusCode = 502;
      errorMessage = 'Bad Gateway';
      details = err.message;
    }
    // Validation errors (should be handled by validation middleware, but just in case)
    else if (message.includes('validation') || message.includes('invalid') || message.includes('missing')) {
      statusCode = 400;
      errorMessage = 'Bad Request';
      details = err.message;
    }
    // Generic errors with descriptive messages
    else {
      errorMessage = err.message;
    }
  }

  // Format error response consistently
  const errorResponse = {
    error: errorMessage
  };

  // Include details if available
  if (details) {
    errorResponse.details = details;
  }

  // Send error response
  res.status(statusCode).json(errorResponse);
}

module.exports = { errorHandler };
