/**
 * Validation middleware for request body
 */
function validateRequest(req, res, next) {
  const { message } = req.body;

  // Check if message field exists
  if (message === undefined || message === null) {
    return res.status(400).json({
      error: 'Missing required field: message'
    });
  }

  // Check if message is a string
  if (typeof message !== 'string') {
    return res.status(400).json({
      error: 'Invalid field type: message must be a string'
    });
  }

  // Check if message is non-empty
  if (message.trim().length === 0) {
    return res.status(400).json({
      error: 'Invalid field value: message cannot be empty'
    });
  }

  // Validation passed, proceed to next middleware
  next();
}

module.exports = { validateRequest };
