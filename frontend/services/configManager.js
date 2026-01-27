import StorageManager from './storageManager.js';

/**
 * ConfigManager - Manages application configuration including API keys and LM Studio settings
 * Provides methods for getting and setting configuration values with defaults
 */
class ConfigManager {
  static CONFIG_KEY = 'cr2a_config';

  // Default values
  static DEFAULTS = {
    api_key: '',
    model: 'gpt-4-turbo-preview',
    lmstudio_base_url: 'http://localhost:1234',
    lmstudio_model_id: 'qwen2.5-7b-instruct',
    api_mode: 'openai'
  };

  /**
   * Get the entire configuration object
   * @returns {Object} The configuration object with defaults applied
   */
  static getConfig() {
    const config = StorageManager.get(this.CONFIG_KEY) || {};
    return { ...this.DEFAULTS, ...config };
  }

  /**
   * Save the entire configuration object
   * @param {Object} config - The configuration object to save
   */
  static setConfig(config) {
    StorageManager.set(this.CONFIG_KEY, config);
  }

  /**
   * Get the OpenAI API key
   * @returns {string} The API key or empty string
   */
  static getApiKey() {
    const config = this.getConfig();
    return config.api_key || '';
  }

  /**
   * Set the OpenAI API key
   * @param {string} key - The API key to store
   */
  static setApiKey(key) {
    const config = this.getConfig();
    config.api_key = key;
    this.setConfig(config);
  }

  /**
   * Check if an API key is configured
   * @returns {boolean} True if API key exists and is not empty
   */
  static hasApiKey() {
    const apiKey = this.getApiKey();
    return apiKey !== null && apiKey !== undefined && apiKey.trim() !== '';
  }

  /**
   * Get the OpenAI model name
   * @returns {string} The model name
   */
  static getModel() {
    const config = this.getConfig();
    return config.model || this.DEFAULTS.model;
  }

  /**
   * Set the OpenAI model name
   * @param {string} model - The model name to store
   */
  static setModel(model) {
    const config = this.getConfig();
    config.model = model;
    this.setConfig(config);
  }

  /**
   * Get the LM Studio base URL
   * @returns {string} The base URL
   */
  static getLMStudioBaseUrl() {
    const config = this.getConfig();
    return config.lmstudio_base_url || this.DEFAULTS.lmstudio_base_url;
  }

  /**
   * Set the LM Studio base URL
   * @param {string} url - The base URL to store
   */
  static setLMStudioBaseUrl(url) {
    const config = this.getConfig();
    config.lmstudio_base_url = url;
    this.setConfig(config);
  }

  /**
   * Get the LM Studio model ID
   * @returns {string} The model ID
   */
  static getLMStudioModelId() {
    const config = this.getConfig();
    return config.lmstudio_model_id || this.DEFAULTS.lmstudio_model_id;
  }

  /**
   * Set the LM Studio model ID
   * @param {string} id - The model ID to store
   */
  static setLMStudioModelId(id) {
    const config = this.getConfig();
    config.lmstudio_model_id = id;
    this.setConfig(config);
  }

  /**
   * Get the API mode (openai or lmstudio)
   * @returns {string} The API mode
   */
  static getApiMode() {
    const config = this.getConfig();
    return config.api_mode || this.DEFAULTS.api_mode;
  }

  /**
   * Set the API mode
   * @param {string} mode - The API mode ('openai' or 'lmstudio')
   */
  static setApiMode(mode) {
    if (mode !== 'openai' && mode !== 'lmstudio') {
      throw new Error(`Invalid API mode: ${mode}. Must be 'openai' or 'lmstudio'`);
    }
    const config = this.getConfig();
    config.api_mode = mode;
    this.setConfig(config);
  }
}

export default ConfigManager;
