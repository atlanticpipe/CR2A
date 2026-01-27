/**
 * StorageManager - Handles localStorage operations for the application
 * Provides a simple interface for storing and retrieving configuration data
 */
class StorageManager {
  /**
   * Get a value from localStorage
   * @param {string} key - The key to retrieve
   * @returns {any} The parsed value, or null if not found
   */
  static get(key) {
    try {
      const value = localStorage.getItem(key);
      return value ? JSON.parse(value) : null;
    } catch (error) {
      console.error(`[StorageManager] Error getting key "${key}":`, error);
      return null;
    }
  }

  /**
   * Set a value in localStorage
   * @param {string} key - The key to store
   * @param {any} value - The value to store (will be JSON stringified)
   */
  static set(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.error(`[StorageManager] Error setting key "${key}":`, error);
      throw error;
    }
  }

  /**
   * Remove a value from localStorage
   * @param {string} key - The key to remove
   */
  static remove(key) {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error(`[StorageManager] Error removing key "${key}":`, error);
      throw error;
    }
  }

  /**
   * Clear all values from localStorage
   */
  static clear() {
    try {
      localStorage.clear();
    } catch (error) {
      console.error('[StorageManager] Error clearing storage:', error);
      throw error;
    }
  }
}

export default StorageManager;
