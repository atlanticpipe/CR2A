// Configuration Manager for CR2A GitHub Pages Edition

class ConfigManager {
  static STORAGE_KEYS = {
    API_KEY: 'openai_api_key',
    MODEL: 'openai_model',
    THEME: 'app_theme',
    LAST_ANALYSIS: 'last_analysis_result'
  };

  static DEFAULT_MODEL = 'gpt-4-turbo-preview';

  /**
   * Save OpenAI API key
   */
  static saveApiKey(key) {
    if (!key || !key.startsWith('sk-')) {
      throw new Error('Invalid API key format');
    }
    localStorage.setItem(this.STORAGE_KEYS.API_KEY, key);
  }

  /**
   * Get OpenAI API key
   */
  static getApiKey() {
    return localStorage.getItem(this.STORAGE_KEYS.API_KEY);
  }

  /**
   * Clear API key
   */
  static clearApiKey() {
    localStorage.removeItem(this.STORAGE_KEYS.API_KEY);
  }

  /**
   * Check if API key exists
   */
  static hasApiKey() {
    const key = this.getApiKey();
    return key && key.startsWith('sk-');
  }

  /**
   * Save model preference
   */
  static saveModel(model) {
    localStorage.setItem(this.STORAGE_KEYS.MODEL, model);
  }

  /**
   * Get model preference
   */
  static getModel() {
    return localStorage.getItem(this.STORAGE_KEYS.MODEL) || this.DEFAULT_MODEL;
  }

  /**
   * Save theme preference
   */
  static saveTheme(theme) {
    localStorage.setItem(this.STORAGE_KEYS.THEME, theme);
    document.documentElement.setAttribute('data-theme', theme);
  }

  /**
   * Get theme preference
   */
  static getTheme() {
    return localStorage.getItem(this.STORAGE_KEYS.THEME) || 'light';
  }

  /**
   * Save analysis result
   */
  static saveAnalysis(result) {
    try {
      localStorage.setItem(
        this.STORAGE_KEYS.LAST_ANALYSIS, 
        JSON.stringify(result)
      );
    } catch (error) {
      console.error('Failed to save analysis:', error);
    }
  }

  /**
   * Get last analysis
   */
  static getLastAnalysis() {
    try {
      const data = localStorage.getItem(this.STORAGE_KEYS.LAST_ANALYSIS);
      return data ? JSON.parse(data) : null;
    } catch (error) {
      console.error('Failed to retrieve analysis:', error);
      return null;
    }
  }

  /**
   * Clear all stored data
   */
  static clearAll() {
    Object.values(this.STORAGE_KEYS).forEach(key => {
      localStorage.removeItem(key);
    });
  }

  /**
   * Export configuration
   */
  static exportConfig() {
    return {
      model: this.getModel(),
      theme: this.getTheme(),
      hasApiKey: this.hasApiKey(),
      version: '2.0.0-github-pages'
    };
  }
}

// Apply theme on load
document.documentElement.setAttribute('data-theme', ConfigManager.getTheme());
