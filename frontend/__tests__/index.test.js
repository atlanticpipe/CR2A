import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Index HTML Unit Tests', () => {
  const indexPath = path.join(process.cwd(), 'index.html');
  let htmlContent;

  it('should have an index.html file in the repository root', () => {
    expect(fs.existsSync(indexPath)).toBe(true);
    htmlContent = fs.readFileSync(indexPath, 'utf-8');
  });

  it('should have valid HTML5 structure', () => {
    htmlContent = fs.readFileSync(indexPath, 'utf-8');
    
    // Check for DOCTYPE
    expect(htmlContent).toContain('<!DOCTYPE html>');
    
    // Check for html tag with lang attribute
    expect(htmlContent).toMatch(/<html[^>]*lang="en"[^>]*>/);
    
    // Check for head and body tags
    expect(htmlContent).toContain('<head>');
    expect(htmlContent).toContain('</head>');
    expect(htmlContent).toContain('<body>');
    expect(htmlContent).toContain('</body>');
  });

  it('should have required meta tags present', () => {
    htmlContent = fs.readFileSync(indexPath, 'utf-8');
    
    // Check for UTF-8 charset
    expect(htmlContent).toMatch(/<meta[^>]*charset="UTF-8"[^>]*>/);
    
    // Check for viewport meta tag
    expect(htmlContent).toMatch(/<meta[^>]*name="viewport"[^>]*content="width=device-width, initial-scale=1.0"[^>]*>/);
    
    // Check for title tag
    expect(htmlContent).toContain('<title>CR2A - Contract Analysis Tool</title>');
  });

  it('should reference correct script file', () => {
    htmlContent = fs.readFileSync(indexPath, 'utf-8');
    
    // Check for script tag with correct src and type
    expect(htmlContent).toMatch(/<script[^>]*type="module"[^>]*src="app_integrated.js"[^>]*>/);
  });

  it('should have CSS files linked', () => {
    htmlContent = fs.readFileSync(indexPath, 'utf-8');
    
    // Check for styles.css
    expect(htmlContent).toMatch(/<link[^>]*rel="stylesheet"[^>]*href="frontend\/styles.css"[^>]*>/);
    
    // Check for ui-enhancements.css
    expect(htmlContent).toMatch(/<link[^>]*rel="stylesheet"[^>]*href="frontend\/ui-enhancements.css"[^>]*>/);
  });

  it('should have app container element', () => {
    htmlContent = fs.readFileSync(indexPath, 'utf-8');
    
    // Check for div with id="app"
    expect(htmlContent).toMatch(/<div[^>]*id="app"[^>]*>/);
  });
});
