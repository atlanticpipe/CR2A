// Storage Manager - LocalStorage utilities

class StorageManager {
  static MAX_SIZE_MB = 5; // Browser localStorage limit is typically 5-10MB

  /**
   * Store data with compression
   */
  static set(key, value) {
    try {
      const serialized = JSON.stringify(value);
      const sizeMB = new Blob([serialized]).size / (1024 * 1024);

      if (sizeMB > this.MAX_SIZE_MB) {
        throw new Error(\`Data too large: \${sizeMB.toFixed(2)}MB (max: \${this.MAX_SIZE_MB}MB)\`);
      }

      localStorage.setItem(key, serialized);
      return true;
    } catch (error) {
      console.error('Storage error:', error);
      return false;
    }
  }

  /**
   * Retrieve stored data
   */
  static get(key, defaultValue = null) {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch (error) {
      console.error('Retrieval error:', error);
      return defaultValue;
    }
  }

  /**
   * Remove item
   */
  static remove(key) {
    localStorage.removeItem(key);
  }

  /**
   * Check if key exists
   */
  static has(key) {
    return localStorage.getItem(key) !== null;
  }

  /**
   * Clear all storage
   */
  static clear() {
    localStorage.clear();
  }

  /**
   * Get storage size
   */
  static getStorageSize() {
    let total = 0;
    for (let key in localStorage) {
      if (localStorage.hasOwnProperty(key)) {
        total += localStorage[key].length + key.length;
      }
    }
    return {
      bytes: total,
      kb: (total / 1024).toFixed(2),
      mb: (total / (1024 * 1024)).toFixed(2)
    };
  }

  /**
   * List all keys
   */
  static keys() {
    return Object.keys(localStorage);
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = StorageManager;
}
