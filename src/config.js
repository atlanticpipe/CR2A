require('dotenv').config();

const config = {
  openaiApiKey: process.env.OPENAI_API_KEY,
  port: parseInt(process.env.PORT, 10) || 3000,
  defaultModel: process.env.OPENAI_MODEL || 'gpt-4',
  nodeEnv: process.env.NODE_ENV || 'development'
};

function validateConfig() {
  if (!config.openaiApiKey) {
    throw new Error('OPENAI_API_KEY environment variable is required but not set');
  }
}

module.exports = { config, validateConfig };
