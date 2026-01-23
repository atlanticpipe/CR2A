import { describe, it, expect } from 'vitest';
import { execSync } from 'child_process';
import * as fc from 'fast-check';

/**
 * Feature: add-gitignore-and-index
 * Property 1: Gitignore excludes all specified artifact types
 * Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
 */
describe('Gitignore Property-Based Tests', () => {
  
  it('Property 1: Gitignore excludes all specified artifact types', { timeout: 30000 }, () => {
    // Define generators for different types of files that should be ignored
    const nodeArtifacts = fc.oneof(
      fc.constant('node_modules/package.js'),
      fc.constant('node_modules/lib/index.js'),
      fc.constant('npm-debug.log'),
      fc.constant('yarn-error.log')
    );

    const pythonArtifacts = fc.oneof(
      fc.constant('__pycache__/module.pyc'),
      fc.constant('src/__pycache__/test.pyc'),
      fc.constant('test.pyc'),
      fc.constant('module.pyo'),
      fc.constant('script.pyd'),
      fc.constant('package.egg-info/PKG-INFO')
    );

    const virtualEnvs = fc.oneof(
      fc.constant('venv/bin/python'),
      fc.constant('env/lib/site-packages'),
      fc.constant('.venv/Scripts/activate'),
      fc.constant('ENV/include/python.h')
    );

    const buildOutputs = fc.oneof(
      fc.constant('dist/bundle.js'),
      fc.constant('build/output.js'),
      fc.constant('.next/cache/webpack'),
      fc.constant('out/index.html')
    );

    const envFiles = fc.oneof(
      fc.constant('.env'),
      fc.constant('.env.local'),
      fc.constant('.env.development.local'),
      fc.constant('.env.test.local'),
      fc.constant('.env.production.local')
    );

    const ideFiles = fc.oneof(
      fc.constant('.vscode/settings.json'),
      fc.constant('.idea/workspace.xml'),
      fc.constant('test.swp'),
      fc.constant('file.swo')
    );

    const osFiles = fc.oneof(
      fc.constant('.DS_Store'),
      fc.constant('Thumbs.db'),
      fc.constant('desktop.ini')
    );

    const logFiles = fc.oneof(
      fc.constant('error.log'),
      fc.constant('logs/app.log'),
      fc.constant('temp.tmp'),
      fc.constant('.cache/data')
    );

    const coverageFiles = fc.oneof(
      fc.constant('coverage/lcov.info'),
      fc.constant('.nyc_output/coverage.json'),
      fc.constant('htmlcov/index.html'),
      fc.constant('.coverage')
    );

    // Combine all artifact generators
    const ignoredFileGenerator = fc.oneof(
      nodeArtifacts,
      pythonArtifacts,
      virtualEnvs,
      buildOutputs,
      envFiles,
      ideFiles,
      osFiles,
      logFiles,
      coverageFiles
    );

    // Property: For any file matching gitignore patterns, git check-ignore should return true
    fc.assert(
      fc.property(ignoredFileGenerator, (filePath) => {
        try {
          const result = execSync(`git check-ignore "${filePath}"`, { 
            encoding: 'utf-8',
            stdio: ['pipe', 'pipe', 'pipe']
          });
          // If git check-ignore succeeds, it returns the file path
          expect(result.trim()).toBe(filePath);
          return true;
        } catch (error) {
          // If git check-ignore fails (exit code 1), the file is NOT ignored
          throw new Error(`File "${filePath}" should be ignored but is not`);
        }
      }),
      { numRuns: 100 } // Run minimum 100 iterations as specified
    );
  });
});
