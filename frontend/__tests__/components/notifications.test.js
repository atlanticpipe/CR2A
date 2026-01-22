/**
 * Tests for notifications.js - Toast notification system
 * Requirements: 14.3
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('NotificationManager - Toast Notifications', () => {
  let NotificationManager;
  let notificationManager;

  beforeEach(async () => {
    // Set up DOM structure
    document.body.innerHTML = '';

    // Load NotificationManager class
    const notificationPath = path.join(process.cwd(), 'frontend', 'notifications.js');
    const notificationCode = fs.readFileSync(notificationPath, 'utf-8');
    
    // Execute the code to define NotificationManager
    eval(notificationCode);
    
    NotificationManager = window.NotificationManager;
    notificationManager = new NotificationManager();
  });

  afterEach(() => {
    vi.clearAllMocks();
    if (notificationManager) {
      notificationManager.closeAll();
    }
  });

  describe('Initialization', () => {
    it('should create NotificationManager instance', () => {
      expect(notificationManager).toBeDefined();
      expect(notificationManager).toBeInstanceOf(NotificationManager);
    });

    it('should create toast container in DOM', () => {
      const container = document.querySelector('.toast-container');
      expect(container).toBeTruthy();
    });

    it('should initialize with empty notifications array', () => {
      expect(notificationManager.notifications).toBeDefined();
      expect(Array.isArray(notificationManager.notifications)).toBe(true);
      expect(notificationManager.notifications.length).toBe(0);
    });

    it('should reuse existing container if present', () => {
      const existingContainer = document.querySelector('.toast-container');
      const newManager = new NotificationManager();
      const container = document.querySelector('.toast-container');
      
      expect(container).toBe(existingContainer);
    });
  });

  describe('Show Notification', () => {
    it('should show info notification', () => {
      const toast = notificationManager.show('Test message', 'info', 0);
      
      expect(toast).toBeTruthy();
      expect(toast.classList.contains('toast')).toBe(true);
      expect(toast.classList.contains('toast-info')).toBe(true);
    });

    it('should show success notification', () => {
      const toast = notificationManager.show('Success!', 'success', 0);
      
      expect(toast.classList.contains('toast-success')).toBe(true);
    });

    it('should show error notification', () => {
      const toast = notificationManager.show('Error!', 'error', 0);
      
      expect(toast.classList.contains('toast-error')).toBe(true);
    });

    it('should show warning notification', () => {
      const toast = notificationManager.show('Warning!', 'warning', 0);
      
      expect(toast.classList.contains('toast-warning')).toBe(true);
    });

    it('should add notification to container', () => {
      notificationManager.show('Test', 'info', 0);
      
      const toasts = notificationManager.container.querySelectorAll('.toast');
      expect(toasts.length).toBe(1);
    });

    it('should add notification to notifications array', () => {
      notificationManager.show('Test', 'info', 0);
      
      expect(notificationManager.notifications.length).toBe(1);
    });

    it('should include message in toast', () => {
      const toast = notificationManager.show('Test message', 'info', 0);
      const message = toast.querySelector('.toast-message');
      
      expect(message).toBeTruthy();
      expect(message.textContent).toBe('Test message');
    });

    it('should include custom title when provided', () => {
      const toast = notificationManager.show('Message', 'info', 0, 'Custom Title');
      const title = toast.querySelector('.toast-title');
      
      expect(title).toBeTruthy();
      expect(title.textContent).toBe('Custom Title');
    });

    it('should use default title when not provided', () => {
      const toast = notificationManager.show('Message', 'success', 0);
      const title = toast.querySelector('.toast-title');
      
      expect(title).toBeTruthy();
      expect(title.textContent).toBe('Success');
    });

    it('should include close button', () => {
      const toast = notificationManager.show('Test', 'info', 0);
      const closeBtn = toast.querySelector('.toast-close');
      
      expect(closeBtn).toBeTruthy();
      expect(closeBtn.getAttribute('aria-label')).toBe('Close notification');
    });

    it('should include appropriate icon', () => {
      const successToast = notificationManager.show('Success', 'success', 0);
      const errorToast = notificationManager.show('Error', 'error', 0);
      
      const successIcon = successToast.querySelector('.toast-icon');
      const errorIcon = errorToast.querySelector('.toast-icon');
      
      expect(successIcon.textContent).toBe('✓');
      expect(errorIcon.textContent).toBe('✕');
    });
  });

  describe('Toast Icons', () => {
    it('should return correct icon for success', () => {
      const icon = notificationManager.getIcon('success');
      expect(icon).toBe('✓');
    });

    it('should return correct icon for error', () => {
      const icon = notificationManager.getIcon('error');
      expect(icon).toBe('✕');
    });

    it('should return correct icon for warning', () => {
      const icon = notificationManager.getIcon('warning');
      expect(icon).toBe('⚠');
    });

    it('should return correct icon for info', () => {
      const icon = notificationManager.getIcon('info');
      expect(icon).toBe('ℹ');
    });

    it('should return default icon for unknown type', () => {
      const icon = notificationManager.getIcon('unknown');
      expect(icon).toBe('ℹ');
    });
  });

  describe('Default Titles', () => {
    it('should return correct title for success', () => {
      const title = notificationManager.getDefaultTitle('success');
      expect(title).toBe('Success');
    });

    it('should return correct title for error', () => {
      const title = notificationManager.getDefaultTitle('error');
      expect(title).toBe('Error');
    });

    it('should return correct title for warning', () => {
      const title = notificationManager.getDefaultTitle('warning');
      expect(title).toBe('Warning');
    });

    it('should return correct title for info', () => {
      const title = notificationManager.getDefaultTitle('info');
      expect(title).toBe('Info');
    });
  });

  describe('Close Notification', () => {
    it('should close notification', () => {
      const toast = notificationManager.show('Test', 'info', 0);
      notificationManager.close(toast);
      
      expect(toast.classList.contains('toast-exit')).toBe(true);
    });

    it('should remove notification from array', (done) => {
      const toast = notificationManager.show('Test', 'info', 0);
      expect(notificationManager.notifications.length).toBe(1);
      
      notificationManager.close(toast);
      
      // Wait for removal animation
      setTimeout(() => {
        expect(notificationManager.notifications.length).toBe(0);
        done();
      }, 350);
    });

    it('should close notification when close button is clicked', () => {
      const toast = notificationManager.show('Test', 'info', 0);
      const closeBtn = toast.querySelector('.toast-close');
      
      closeBtn.click();
      
      expect(toast.classList.contains('toast-exit')).toBe(true);
    });
  });

  describe('Close All Notifications', () => {
    it('should close all notifications', () => {
      notificationManager.show('Test 1', 'info', 0);
      notificationManager.show('Test 2', 'success', 0);
      notificationManager.show('Test 3', 'error', 0);
      
      expect(notificationManager.notifications.length).toBe(3);
      
      notificationManager.closeAll();
      
      // All should have exit class
      notificationManager.notifications.forEach(toast => {
        expect(toast.classList.contains('toast-exit')).toBe(true);
      });
    });
  });

  describe('Convenience Methods', () => {
    it('should show success notification via convenience method', () => {
      const toast = notificationManager.success('Success message', null, 0);
      
      expect(toast.classList.contains('toast-success')).toBe(true);
      expect(toast.querySelector('.toast-message').textContent).toBe('Success message');
    });

    it('should show error notification via convenience method', () => {
      const toast = notificationManager.error('Error message', null, 0);
      
      expect(toast.classList.contains('toast-error')).toBe(true);
      expect(toast.querySelector('.toast-message').textContent).toBe('Error message');
    });

    it('should show warning notification via convenience method', () => {
      const toast = notificationManager.warning('Warning message', null, 0);
      
      expect(toast.classList.contains('toast-warning')).toBe(true);
      expect(toast.querySelector('.toast-message').textContent).toBe('Warning message');
    });

    it('should show info notification via convenience method', () => {
      const toast = notificationManager.info('Info message', null, 0);
      
      expect(toast.classList.contains('toast-info')).toBe(true);
      expect(toast.querySelector('.toast-message').textContent).toBe('Info message');
    });

    it('should use custom title in convenience methods', () => {
      const toast = notificationManager.success('Message', 'Custom Success', 0);
      const title = toast.querySelector('.toast-title');
      
      expect(title.textContent).toBe('Custom Success');
    });
  });

  describe('Auto-close Behavior', () => {
    it('should not auto-close when duration is 0', (done) => {
      const toast = notificationManager.show('Test', 'info', 0);
      
      setTimeout(() => {
        expect(toast.classList.contains('toast-exit')).toBe(false);
        expect(notificationManager.notifications.length).toBe(1);
        done();
      }, 100);
    });

    it('should auto-close after specified duration', (done) => {
      const toast = notificationManager.show('Test', 'info', 100);
      
      setTimeout(() => {
        expect(toast.classList.contains('toast-exit')).toBe(true);
        done();
      }, 150);
    });
  });

  describe('Multiple Notifications', () => {
    it('should handle multiple notifications simultaneously', () => {
      notificationManager.show('First', 'info', 0);
      notificationManager.show('Second', 'success', 0);
      notificationManager.show('Third', 'error', 0);
      
      expect(notificationManager.notifications.length).toBe(3);
      
      const toasts = notificationManager.container.querySelectorAll('.toast');
      expect(toasts.length).toBe(3);
    });

    it('should maintain order of notifications', () => {
      notificationManager.show('First', 'info', 0);
      notificationManager.show('Second', 'success', 0);
      
      const toasts = notificationManager.container.querySelectorAll('.toast');
      expect(toasts[0].querySelector('.toast-message').textContent).toBe('First');
      expect(toasts[1].querySelector('.toast-message').textContent).toBe('Second');
    });
  });

  describe('Toast Activation', () => {
    it('should add active class after creation', (done) => {
      const toast = notificationManager.show('Test', 'info', 0);
      
      // Active class is added after a small delay
      setTimeout(() => {
        expect(toast.classList.contains('active')).toBe(true);
        done();
      }, 50);
    });
  });
});
