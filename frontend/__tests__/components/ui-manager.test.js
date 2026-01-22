/**
 * Tests for ui-manager.js - UI state management and DOM manipulation
 * Requirements: 14.2
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('UIManager - UI State Management', () => {
  let UIManager;
  let uiManager;

  beforeEach(async () => {
    // Set up DOM structure
    document.body.innerHTML = '<main class="container"></main>';

    // Mock notify system
    global.notify = {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn()
    };

    // Load UIManager class by reading and evaluating the file
    const uiManagerPath = path.join(process.cwd(), 'frontend', 'ui-manager.js');
    const uiManagerCode = fs.readFileSync(uiManagerPath, 'utf-8');
    
    // Execute the code to define UIManager
    eval(uiManagerCode);
    
    UIManager = window.UIManager;
    uiManager = new UIManager();
  });

  afterEach(() => {
    vi.clearAllMocks();
    if (uiManager && uiManager.loadingOverlay) {
      uiManager.loadingOverlay.remove();
    }
    if (uiManager && uiManager.progressContainer) {
      uiManager.progressContainer.remove();
    }
  });

  describe('Initialization', () => {
    it('should create UIManager instance', () => {
      expect(uiManager).toBeDefined();
      expect(uiManager).toBeInstanceOf(UIManager);
    });

    it('should initialize with loading overlay', () => {
      expect(uiManager.loadingOverlay).toBeDefined();
      expect(uiManager.loadingOverlay.className).toBe('loading-overlay');
    });

    it('should create loading overlay in DOM', () => {
      const overlay = document.querySelector('.loading-overlay');
      expect(overlay).toBeTruthy();
    });

    it('should have loading spinner in overlay', () => {
      const spinner = uiManager.loadingOverlay.querySelector('.loading-spinner');
      expect(spinner).toBeTruthy();
    });

    it('should have loading text elements', () => {
      const text = uiManager.loadingOverlay.querySelector('.loading-text');
      const subtext = uiManager.loadingOverlay.querySelector('.loading-subtext');
      
      expect(text).toBeTruthy();
      expect(subtext).toBeTruthy();
    });
  });

  describe('Loading Overlay', () => {
    it('should show loading overlay', () => {
      uiManager.showLoading('Processing...', 'Please wait');
      
      expect(uiManager.loadingOverlay.classList.contains('active')).toBe(true);
      expect(document.body.style.overflow).toBe('hidden');
    });

    it('should hide loading overlay', () => {
      uiManager.showLoading();
      uiManager.hideLoading();
      
      expect(uiManager.loadingOverlay.classList.contains('active')).toBe(false);
      expect(document.body.style.overflow).toBe('');
    });

    it('should update loading text', () => {
      uiManager.showLoading('Initial text', 'Initial subtext');
      
      const textEl = uiManager.loadingOverlay.querySelector('.loading-text');
      const subtextEl = uiManager.loadingOverlay.querySelector('.loading-subtext');
      
      expect(textEl.textContent).toBe('Initial text');
      expect(subtextEl.textContent).toBe('Initial subtext');
    });

    it('should update loading text dynamically', () => {
      uiManager.showLoading();
      uiManager.updateLoadingText('Updated text', 'Updated subtext');
      
      const textEl = uiManager.loadingOverlay.querySelector('.loading-text');
      const subtextEl = uiManager.loadingOverlay.querySelector('.loading-subtext');
      
      expect(textEl.textContent).toBe('Updated text');
      expect(subtextEl.textContent).toBe('Updated subtext');
    });

    it('should update only main text when subtext is null', () => {
      uiManager.showLoading('Initial', 'Initial sub');
      uiManager.updateLoadingText('New text', null);
      
      const textEl = uiManager.loadingOverlay.querySelector('.loading-text');
      const subtextEl = uiManager.loadingOverlay.querySelector('.loading-subtext');
      
      expect(textEl.textContent).toBe('New text');
      expect(subtextEl.textContent).toBe('Initial sub');
    });
  });

  describe('Progress Tracking', () => {
    it('should show progress with steps', () => {
      const steps = ['Step 1', 'Step 2', 'Step 3'];
      uiManager.showProgress(steps, 0);
      
      expect(uiManager.progressContainer).toBeTruthy();
      expect(document.querySelector('.progress-container')).toBeTruthy();
    });

    it('should create progress steps in DOM', () => {
      const steps = ['Parse', 'Analyze', 'Export'];
      uiManager.showProgress(steps, 0);
      
      const stepElements = document.querySelectorAll('.progress-step');
      expect(stepElements.length).toBe(3);
    });

    it('should mark initial step as active', () => {
      const steps = ['Step 1', 'Step 2', 'Step 3'];
      uiManager.showProgress(steps, 0);
      
      const firstStep = document.querySelector('.progress-step[data-step="0"]');
      expect(firstStep.classList.contains('active')).toBe(true);
    });

    it('should update progress percentage', () => {
      const steps = ['Step 1', 'Step 2', 'Step 3', 'Step 4'];
      uiManager.showProgress(steps, 0);
      uiManager.updateProgress(2, 4);
      
      const percentage = document.querySelector('.progress-percentage');
      expect(percentage.textContent).toBe('50%');
    });

    it('should update progress bar width', () => {
      const steps = ['Step 1', 'Step 2'];
      uiManager.showProgress(steps, 0);
      uiManager.updateProgress(1, 2);
      
      const progressBar = document.querySelector('.progress-bar');
      expect(progressBar.style.width).toBe('50%');
    });

    it('should mark completed steps', () => {
      const steps = ['Step 1', 'Step 2', 'Step 3'];
      uiManager.showProgress(steps, 0);
      uiManager.updateProgress(2, 3);
      
      const step0 = document.querySelector('.progress-step[data-step="0"]');
      const step1 = document.querySelector('.progress-step[data-step="1"]');
      const step2 = document.querySelector('.progress-step[data-step="2"]');
      
      expect(step0.classList.contains('completed')).toBe(true);
      expect(step1.classList.contains('completed')).toBe(true);
      expect(step2.classList.contains('active')).toBe(true);
    });

    it('should show checkmark for completed steps', () => {
      const steps = ['Step 1', 'Step 2'];
      uiManager.showProgress(steps, 0);
      uiManager.updateProgress(1, 2);
      
      const step0Circle = document.querySelector('.progress-step[data-step="0"] .progress-step-circle');
      expect(step0Circle.textContent).toBe('✓');
    });

    it('should complete progress at 100%', () => {
      const steps = ['Step 1', 'Step 2'];
      uiManager.showProgress(steps, 0);
      uiManager.completeProgress();
      
      const percentage = document.querySelector('.progress-percentage');
      expect(percentage.textContent).toBe('100%');
    });

    it('should hide progress container', () => {
      const steps = ['Step 1'];
      uiManager.showProgress(steps, 0);
      uiManager.hideProgress();
      
      expect(uiManager.progressContainer.style.opacity).toBe('0');
    });

    it('should remove old progress container when showing new one', () => {
      uiManager.showProgress(['Step 1'], 0);
      const firstContainer = uiManager.progressContainer;
      
      uiManager.showProgress(['Step A', 'Step B'], 0);
      const secondContainer = uiManager.progressContainer;
      
      expect(firstContainer).not.toBe(secondContainer);
      expect(document.body.contains(firstContainer)).toBe(false);
    });
  });

  describe('Button States', () => {
    it('should set button to loading state', () => {
      const button = document.createElement('button');
      button.innerHTML = 'Submit';
      document.body.appendChild(button);
      
      uiManager.setButtonLoading(button, true);
      
      expect(button.classList.contains('btn-loading')).toBe(true);
      expect(button.disabled).toBe(true);
      expect(button.dataset.originalText).toBe('Submit');
    });

    it('should restore button from loading state', () => {
      const button = document.createElement('button');
      button.innerHTML = 'Submit';
      document.body.appendChild(button);
      
      uiManager.setButtonLoading(button, true);
      uiManager.setButtonLoading(button, false);
      
      expect(button.classList.contains('btn-loading')).toBe(false);
      expect(button.disabled).toBe(false);
      expect(button.innerHTML).toBe('Submit');
    });
  });

  describe('Form Validation UI', () => {
    it('should show field error', () => {
      const input = document.createElement('input');
      const container = document.createElement('div');
      container.appendChild(input);
      document.body.appendChild(container);
      
      uiManager.showFieldError(input, 'This field is required');
      
      expect(input.classList.contains('invalid')).toBe(true);
      const errorMsg = container.querySelector('.validation-message.error');
      expect(errorMsg).toBeTruthy();
      expect(errorMsg.textContent).toContain('This field is required');
    });

    it('should show field success', () => {
      const input = document.createElement('input');
      const container = document.createElement('div');
      container.appendChild(input);
      document.body.appendChild(container);
      
      uiManager.showFieldSuccess(input, 'Valid input');
      
      expect(input.classList.contains('valid')).toBe(true);
      const successMsg = container.querySelector('.validation-message.success');
      expect(successMsg).toBeTruthy();
    });

    it('should clear field validation', () => {
      const input = document.createElement('input');
      const container = document.createElement('div');
      container.appendChild(input);
      document.body.appendChild(container);
      
      uiManager.showFieldError(input, 'Error');
      uiManager.clearFieldValidation(input);
      
      expect(input.classList.contains('invalid')).toBe(false);
      expect(input.classList.contains('valid')).toBe(false);
      expect(container.querySelector('.validation-message')).toBeFalsy();
    });

    it('should update validation icon', () => {
      const input = document.createElement('input');
      const container = document.createElement('div');
      container.appendChild(input);
      document.body.appendChild(container);
      
      uiManager.updateValidationIcon(input, 'valid');
      
      const icon = container.querySelector('.validation-icon');
      expect(icon).toBeTruthy();
      expect(icon.textContent).toBe('✓');
    });

    it('should replace existing validation icon', () => {
      const input = document.createElement('input');
      const container = document.createElement('div');
      container.appendChild(input);
      document.body.appendChild(container);
      
      uiManager.updateValidationIcon(input, 'valid');
      uiManager.updateValidationIcon(input, 'invalid');
      
      const icons = container.querySelectorAll('.validation-icon');
      expect(icons.length).toBe(1);
      expect(icons[0].textContent).toBe('✕');
    });
  });

  describe('Modal Helpers', () => {
    it('should show modal', () => {
      const modal = document.createElement('div');
      modal.className = 'modal';
      document.body.appendChild(modal);
      
      uiManager.showModal(modal);
      
      expect(modal.classList.contains('active')).toBe(true);
      expect(document.body.style.overflow).toBe('hidden');
    });

    it('should hide modal', () => {
      const modal = document.createElement('div');
      modal.className = 'modal active';
      document.body.appendChild(modal);
      
      uiManager.hideModal(modal);
      
      expect(modal.classList.contains('active')).toBe(false);
      expect(document.body.style.overflow).toBe('');
    });
  });

  describe('File Upload UI', () => {
    it('should setup file upload zone with drag handlers', () => {
      const zone = document.createElement('div');
      const input = document.createElement('input');
      input.type = 'file';
      document.body.appendChild(zone);
      document.body.appendChild(input);
      
      uiManager.setupFileUploadZone(zone, input);
      
      // Trigger dragover
      const dragEvent = new Event('dragover', { bubbles: true, cancelable: true });
      zone.dispatchEvent(dragEvent);
      
      expect(zone.classList.contains('dragover')).toBe(true);
    });

    it('should remove dragover class on dragleave', () => {
      const zone = document.createElement('div');
      const input = document.createElement('input');
      document.body.appendChild(zone);
      document.body.appendChild(input);
      
      uiManager.setupFileUploadZone(zone, input);
      
      zone.classList.add('dragover');
      const leaveEvent = new Event('dragleave', { bubbles: true });
      zone.dispatchEvent(leaveEvent);
      
      expect(zone.classList.contains('dragover')).toBe(false);
    });

    it('should show file selected state', () => {
      const zone = document.createElement('div');
      zone.innerHTML = '<div class="file-upload-text">Drop file</div><div class="file-upload-icon">📄</div>';
      document.body.appendChild(zone);
      
      uiManager.showFileSelected(zone, 'test.pdf');
      
      const text = zone.querySelector('.file-upload-text');
      expect(text.textContent).toContain('test.pdf');
      expect(text.style.color).toBe('rgb(40, 167, 69)');
    });

    it('should reset file upload zone', () => {
      const zone = document.createElement('div');
      zone.innerHTML = '<div class="file-upload-text">Selected: test.pdf</div><div class="file-upload-icon">✓</div>';
      document.body.appendChild(zone);
      
      uiManager.resetFileUploadZone(zone);
      
      const text = zone.querySelector('.file-upload-text');
      expect(text.textContent).toBe('Drop your contract here or click to browse');
    });
  });
});
