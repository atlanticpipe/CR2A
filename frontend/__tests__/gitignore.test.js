import { describe, it, expect } from 'vitest';
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

describe('Gitignore Unit Tests', () => {
  const gitignorePath = path.join(process.cwd(), '.gitignore');
  
  it('should have a .gitignore file in the repository root', () => {
    expect(fs.existsSync(gitignorePath)).toBe(true);
  });

  it('should exclude node_modules/ directory', () => {
    const gitignoreContent = fs.readFileSync(gitignorePath, 'utf-8');
    expect(gitignoreContent).toContain('node_modules/');
  });

  it('should exclude .env files', () => {
    const gitignoreContent = fs.readFileSync(gitignorePath, 'utf-8');
    expect(gitignoreContent).toContain('.env');
  });

  it('should exclude Python cache files', () => {
    const gitignoreContent = fs.readFileSync(gitignorePath, 'utf-8');
    expect(gitignoreContent).toContain('__pycache__/');
    expect(gitignoreContent).toContain('*.pyc');
  });

  it('should NOT exclude important source files', () => {
    // Test that important directories and files are not in gitignore
    const gitignoreContent = fs.readFileSync(gitignorePath, 'utf-8');
    
    // These should NOT be excluded
    expect(gitignoreContent).not.toContain('src/');
    expect(gitignoreContent).not.toContain('frontend/');
    expect(gitignoreContent).not.toContain('README.md');
    expect(gitignoreContent).not.toContain('package.json');
  });

  it('should verify node_modules/ is actually ignored by git', () => {
    try {
      const result = execSync('git check-ignore node_modules/test.js', { encoding: 'utf-8' });
      expect(result.trim()).toBe('node_modules/test.js');
    } catch (error) {
      // If git check-ignore returns non-zero, the file is not ignored
      throw new Error('node_modules/ is not being ignored by git');
    }
  });

  it('should verify .env files are actually ignored by git', () => {
    try {
      const result = execSync('git check-ignore .env', { encoding: 'utf-8' });
      expect(result.trim()).toBe('.env');
    } catch (error) {
      throw new Error('.env is not being ignored by git');
    }
  });

  it('should verify Python cache files are actually ignored by git', () => {
    try {
      const result = execSync('git check-ignore __pycache__/', { encoding: 'utf-8' });
      expect(result.trim()).toBe('__pycache__/');
    } catch (error) {
      throw new Error('__pycache__/ is not being ignored by git');
    }
  });
});
