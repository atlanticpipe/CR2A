# Design Document

## Overview

This design specifies the creation of two essential project files: a `.gitignore` file to manage version control exclusions and an `index.html` file to serve as the web application entry point. The `.gitignore` will follow industry best practices for Node.js and Python projects, while the `index.html` will provide a proper HTML5 structure that loads the existing `app_integrated.js` application.

## Architecture

### File Structure

```
CR2A/
├── .gitignore ...................... Git exclusion rules
├── index.html ...................... Web application entry point
├── app_integrated.js ............... Main application logic (existing)
├── frontend/ ....................... Frontend components (existing)
├── src/ ............................ Backend code (existing)
└── node_modules/ ................... Dependencies (excluded from Git)
```

### Design Decisions

1. **Gitignore Placement**: Root-level `.gitignore` applies to entire repository
2. **Index Location**: Root-level `index.html` serves as primary entry point
3. **Script Loading**: Use module type for ES6 compatibility with `app_integrated.js`
4. **Responsive Design**: Include viewport meta tag for mobile compatibility

## Components and Interfaces

### Component 1: Gitignore File

**Purpose**: Exclude unnecessary files from version control

**Content Categories**:
1. **Node.js artifacts**: `node_modules/`, `npm-debug.log`, `package-lock.json` (optional)
2. **Python artifacts**: `__pycache__/`, `*.pyc`, `*.pyo`, `*.pyd`, `*.egg-info/`
3. **Virtual environments**: `venv/`, `env/`, `.venv/`, `ENV/`
4. **Build outputs**: `dist/`, `build/`, `.next/`, `out/`
5. **Environment files**: `.env`, `.env.local`, `.env.*.local`
6. **IDE files**: `.vscode/`, `.idea/`, `*.swp`, `*.swo`
7. **OS files**: `.DS_Store`, `Thumbs.db`, `desktop.ini`
8. **Logs and temp**: `*.log`, `logs/`, `*.tmp`, `.cache/`
9. **Test coverage**: `coverage/`, `.nyc_output/`, `htmlcov/`, `.coverage`

**Pattern Syntax**:
- `directory/` - Excludes entire directory
- `*.ext` - Excludes all files with extension
- `!file` - Negates exclusion (includes file)
- `**/pattern` - Matches in any directory

### Component 2: Index HTML File

**Purpose**: Serve as web application entry point

**Structure**:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CR2A - Contract Analysis Tool</title>
  <link rel="stylesheet" href="frontend/styles.css">
  <link rel="stylesheet" href="frontend/ui-enhancements.css">
</head>
<body>
  <div id="app"></div>
  <script type="module" src="app_integrated.js"></script>
</body>
</html>
```

**Key Elements**:
1. **DOCTYPE**: HTML5 declaration
2. **Language**: `lang="en"` for accessibility
3. **Charset**: UTF-8 for international character support
4. **Viewport**: Responsive design meta tag
5. **Title**: Descriptive application name
6. **Stylesheets**: Links to existing CSS files
7. **App Container**: `<div id="app">` for application mounting
8. **Script**: Module type for ES6 import/export support

**Integration Points**:
- `app_integrated.js` expects DOM to be loaded (uses `DOMContentLoaded` event)
- Application looks for specific DOM elements (form, dropzone, etc.)
- CSS files provide styling and theme support

## Data Models

### Gitignore Pattern Model

```
Pattern {
  path: string           // File or directory path
  type: enum             // "file", "directory", "extension", "wildcard"
  negated: boolean       // Whether pattern is negated (!)
  recursive: boolean     // Whether pattern uses ** syntax
}
```

### HTML Document Model

```
HTMLDocument {
  doctype: "html"
  html: {
    lang: "en"
    head: {
      charset: "UTF-8"
      viewport: "width=device-width, initial-scale=1.0"
      title: string
      stylesheets: string[]
    }
    body: {
      container: {
        id: "app"
      }
      scripts: {
        src: string
        type: "module"
      }[]
    }
  }
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Gitignore excludes all specified artifact types

*For any* file or directory matching a pattern in the `.gitignore` file, Git SHALL NOT track that file or directory in version control.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7**

### Property 2: Index HTML is valid HTML5

*For any* HTML5 validator, the `index.html` file SHALL pass validation without errors.

**Validates: Requirements 2.1, 2.6**

### Property 3: Index HTML references correct resources

*For any* resource reference (stylesheet, script) in `index.html`, the referenced file SHALL exist in the repository at the specified path.

**Validates: Requirements 2.2**

### Property 4: Application initializes correctly

*For any* browser loading `index.html`, the application SHALL initialize without console errors and the `DOMContentLoaded` event SHALL trigger the application logic in `app_integrated.js`.

**Validates: Requirements 2.7**

## Error Handling

### Gitignore Errors

**Missing Gitignore**:
- **Symptom**: Unwanted files tracked in Git
- **Detection**: `git status` shows `node_modules/`, `__pycache__/`, etc.
- **Resolution**: Create `.gitignore` file with appropriate patterns

**Invalid Patterns**:
- **Symptom**: Patterns don't match intended files
- **Detection**: Files still tracked despite gitignore entry
- **Resolution**: Test patterns with `git check-ignore -v <file>`

### Index HTML Errors

**Missing Index File**:
- **Symptom**: 404 error when accessing root URL
- **Detection**: Browser shows "File not found"
- **Resolution**: Create `index.html` in repository root

**Script Loading Errors**:
- **Symptom**: Application doesn't initialize
- **Detection**: Console shows "Failed to load resource" or module errors
- **Resolution**: Verify script path and module type attribute

**Missing DOM Elements**:
- **Symptom**: Application fails to find expected elements
- **Detection**: Console shows "Cannot read property of null"
- **Resolution**: Ensure `app_integrated.js` creates required DOM structure or add elements to `index.html`

**CSS Not Loading**:
- **Symptom**: Unstyled content
- **Detection**: Visual inspection shows no styling
- **Resolution**: Verify CSS file paths and ensure files exist

## Testing Strategy

### Dual Testing Approach

This feature will use both unit tests and property-based tests to ensure comprehensive coverage:

- **Unit tests**: Verify specific examples, edge cases, and error conditions
- **Property tests**: Verify universal properties across all inputs

### Unit Testing

**Gitignore Tests**:
1. Test that `node_modules/` is excluded
2. Test that `.env` files are excluded
3. Test that Python cache files are excluded
4. Test that IDE files are excluded
5. Test that important files (src/, frontend/, README.md) are NOT excluded

**Index HTML Tests**:
1. Test that HTML structure is valid
2. Test that required meta tags are present
3. Test that script references correct file
4. Test that CSS files are linked
5. Test that app container element exists

### Property-Based Testing

We will use **fast-check** (JavaScript property-based testing library) for property tests. Each test will run a minimum of 100 iterations.

**Property Test 1: Gitignore Pattern Matching**
- **Property**: For any file path matching a gitignore pattern, Git should not track it
- **Generator**: Generate random file paths (node_modules/*, *.pyc, .env, etc.)
- **Assertion**: `git check-ignore` returns true for generated paths
- **Tag**: Feature: add-gitignore-and-index, Property 1: Gitignore excludes all specified artifact types
- **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7**

**Property Test 2: HTML Validation**
- **Property**: For any HTML5 validator, index.html passes validation
- **Generator**: N/A (single file)
- **Assertion**: HTML validator returns no errors
- **Tag**: Feature: add-gitignore-and-index, Property 2: Index HTML is valid HTML5
- **Validates: Requirements 2.1, 2.6**

**Property Test 3: Resource Reference Integrity**
- **Property**: For any resource reference in index.html, the file exists
- **Generator**: Extract all href/src attributes from HTML
- **Assertion**: Each referenced file exists in filesystem
- **Tag**: Feature: add-gitignore-and-index, Property 3: Index HTML references correct resources
- **Validates: Requirements 2.2**

**Property Test 4: Application Initialization**
- **Property**: For any browser, application initializes without errors
- **Generator**: N/A (single test scenario)
- **Assertion**: No console errors after DOMContentLoaded
- **Tag**: Feature: add-gitignore-and-index, Property 4: Application initializes correctly
- **Validates: Requirements 2.7**

### Test Configuration

```javascript
// vitest.config.js
export default {
  test: {
    environment: 'happy-dom',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html']
    }
  }
}
```

### Manual Testing

1. **Gitignore Verification**:
   ```bash
   # Create test files
   touch node_modules/test.js
   touch .env
   mkdir -p __pycache__ && touch __pycache__/test.pyc
   
   # Verify they're ignored
   git status
   # Should NOT show these files
   ```

2. **Index HTML Verification**:
   ```bash
   # Start local server
   python3 -m http.server 8000
   
   # Open browser to http://localhost:8000
   # Verify:
   # - Page loads without errors
   # - Console shows "🚀 CR2A v2.0.0-github-pages"
   # - Application UI renders correctly
   ```

3. **Resource Loading**:
   ```bash
   # Check browser network tab
   # Verify all resources load (200 status):
   # - frontend/styles.css
   # - frontend/ui-enhancements.css
   # - app_integrated.js
   ```

## Implementation Notes

### Gitignore Best Practices

1. **Order matters**: More specific patterns should come before general ones
2. **Comments**: Use `#` for explanatory comments
3. **Negation**: Use `!` to include files that would otherwise be excluded
4. **Testing**: Use `git check-ignore -v <file>` to test patterns

### Index HTML Best Practices

1. **Semantic HTML**: Use appropriate HTML5 elements
2. **Accessibility**: Include `lang` attribute and proper meta tags
3. **Performance**: Load scripts at end of body or use `defer`/`async`
4. **Module Support**: Use `type="module"` for ES6 modules

### Integration Considerations

1. **Existing Application**: `app_integrated.js` already handles DOM manipulation
2. **Minimal HTML**: Keep `index.html` minimal since app creates its own structure
3. **CSS Loading**: Ensure CSS loads before JavaScript for proper styling
4. **GitHub Pages**: Both files work with GitHub Pages deployment
