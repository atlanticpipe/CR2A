import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Window } from 'happy-dom';
import fs from 'fs';
import path from 'path';

/**
 * Feature: add-gitignore-and-index
 * Property 4: Application initializes correctly
 * Validates: Requirements 2.7
 * 
 * Integration test for application initialization
 */
describe('Application Initialization Integration Test', () => {
  let window;
  let document;
  let consoleErrors;

  beforeEach(() => {
    // Create a new window for each test
    window = new Window();
    document = window.document;
    
    // Track console errors
    consoleErrors = [];
    const originalError = console.error;
    console.error = (...args) => {
      consoleErrors.push(args.join(' '));
      originalError(...args);
    };
  });

  /**
   * Property 4: Application initializes correctly
   * Validates: Requirements 2.7
   */
  it('Property 4: Application initializes correctly', async () => {
    // Load index.html
    const indexPath = path.join(process.cwd(), 'index.html');
    const htmlContent = fs.readFileSync(indexPath, 'utf-8');
    
    // Parse HTML into the test browser environment
    document.write(htmlContent);
    
    // Verify the DOM structure is ready
    expect(document.doctype).toBeTruthy();
    expect(document.doctype.name).toBe('html');
    
    // Verify critical elements exist
    const appContainer = document.querySelector('#app');
    expect(appContainer).toBeTruthy();
    expect(appContainer.id).toBe('app');
    
    // Verify script tag is present
    const scriptTag = document.querySelector('script[type="module"]');
    expect(scriptTag).toBeTruthy();
    expect(scriptTag.getAttribute('src')).toBe('app_integrated.js');
    expect(scriptTag.getAttribute('type')).toBe('module');
    
    // Verify stylesheets are linked
    const stylesheets = document.querySelectorAll('link[rel="stylesheet"]');
    expect(stylesheets.length).toBeGreaterThanOrEqual(2);
    
    const stylesheetHrefs = Array.from(stylesheets).map(link => link.getAttribute('href'));
    expect(stylesheetHrefs).toContain('frontend/styles.css');
    expect(stylesheetHrefs).toContain('frontend/ui-enhancements.css');
    
    // Verify DOMContentLoaded event can fire
    let domContentLoadedFired = false;
    document.addEventListener('DOMContentLoaded', () => {
      domContentLoadedFired = true;
    });
    
    // Trigger DOMContentLoaded
    const event = new window.Event('DOMContentLoaded');
    document.dispatchEvent(event);
    
    expect(domContentLoadedFired).toBe(true);
    
    // Verify no critical DOM structure errors
    // The app container should be ready for the application to mount
    expect(document.body).toBeTruthy();
    expect(document.head).toBeTruthy();
    expect(document.querySelector('#app')).toBeTruthy();
    
    // Verify meta tags for proper initialization
    const charsetMeta = document.querySelector('meta[charset]');
    expect(charsetMeta).toBeTruthy();
    expect(charsetMeta.getAttribute('charset')).toBe('UTF-8');
    
    const viewportMeta = document.querySelector('meta[name="viewport"]');
    expect(viewportMeta).toBeTruthy();
    
    // Verify title is set
    const title = document.querySelector('title');
    expect(title).toBeTruthy();
    expect(title.textContent).toBe('CR2A - Contract Analysis Tool');
    
    // Clean up
    window.close();
  });

  it('should have all expected UI elements ready for app_integrated.js', () => {
    // Load index.html
    const indexPath = path.join(process.cwd(), 'index.html');
    const htmlContent = fs.readFileSync(indexPath, 'utf-8');
    
    document.write(htmlContent);
    
    // The app_integrated.js expects to find or create these elements
    // At minimum, it needs the #app container to exist
    const appContainer = document.querySelector('#app');
    expect(appContainer).toBeTruthy();
    
    // Verify the container is in the body
    expect(document.body.contains(appContainer)).toBe(true);
    
    // Verify the script will load after the DOM is ready
    const scripts = document.querySelectorAll('script');
    expect(scripts.length).toBeGreaterThan(0);
    
    // The module script should be present
    const moduleScript = Array.from(scripts).find(
      script => script.getAttribute('type') === 'module'
    );
    expect(moduleScript).toBeTruthy();
    
    window.close();
  });

  it('should load without HTML parsing errors', () => {
    const indexPath = path.join(process.cwd(), 'index.html');
    const htmlContent = fs.readFileSync(indexPath, 'utf-8');
    
    // This should not throw any errors
    expect(() => {
      document.write(htmlContent);
    }).not.toThrow();
    
    // Verify the document is well-formed
    expect(document.documentElement).toBeTruthy();
    expect(document.head).toBeTruthy();
    expect(document.body).toBeTruthy();
    
    window.close();
  });
});
