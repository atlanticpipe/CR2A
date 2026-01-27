# Design Document: Frontend Assets Fix

## Overview

This design addresses the missing CSS files (`frontend/styles.css` and `frontend/ui-enhancements.css`) that prevent the CR2A application from loading properly. The solution involves creating comprehensive CSS files that implement a dark-themed, professional interface for the contract analysis tool. The design follows modern CSS best practices, uses CSS custom properties for theming, and ensures responsive layouts across different screen sizes.

## Architecture

### File Structure

```
frontend/
├── styles.css ..................... Core application styles
│   ├── CSS Variables (theme colors, spacing, typography)
│   ├── Reset & Base Styles
│   ├── Layout Components (containers, grids, flexbox)
│   ├── Form Elements (inputs, buttons, dropzones)
│   ├── Typography
│   └── Utility Classes
│
└── ui-enhancements.css ............ Enhanced UI components
    ├── Timeline Component
    ├── Pills & Badges (risk levels)
    ├── Notifications/Alerts
    ├── Loading States
    ├── Modals & Overlays
    ├── Animations & Transitions
    └── Responsive Adjustments
```

### Design System

The design uses a centralized theme system with CSS custom properties:

**Color Palette:**
- Primary: Blue tones for interactive elements
- Success: Green for positive states
- Warning: Orange for caution states
- Error: Red for error states
- Neutral: Gray scale for backgrounds and text

**Typography:**
- Font Family: System font stack (native OS fonts)
- Scale: Base 16px with modular scale for headings
- Line Heights: 1.5 for body, 1.2 for headings

**Spacing:**
- Base unit: 8px
- Scale: 4px, 8px, 16px, 24px, 32px, 48px, 64px

## Components and Interfaces

### 1. Core Styles (styles.css)

#### CSS Variables
```css
:root {
  /* Colors */
  --primary: #3b82f6;
  --success: #10b981;
  --warning: #f59e0b;
  --error: #ef4444;
  --bg-primary: #0f172a;
  --bg-secondary: #1e293b;
  --text-primary: #f1f5f9;
  --text-secondary: #94a3b8;
  
  /* Spacing */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  
  /* Typography */
  --font-body: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-mono: "SF Mono", Monaco, "Cascadia Code", monospace;
  
  /* Borders */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.2);
}
```

#### Reset & Base Styles
- CSS reset for consistent cross-browser rendering
- Box-sizing: border-box for all elements
- Smooth scrolling behavior
- Focus outline styles for accessibility

#### Layout Components
- Container: Max-width wrapper with responsive padding
- Grid: CSS Grid layouts for complex arrangements
- Flexbox: Flexible layouts for forms and components
- Section spacing and alignment

#### Form Elements
- Input fields: Styled text inputs with focus states
- Buttons: Primary, secondary, and disabled states
- Dropzone: Drag-and-drop file upload area with hover states
- Labels: Consistent label styling
- Validation states: Error and success indicators

#### Typography
- Heading styles (h1-h6)
- Body text styles
- Code and monospace text
- Link styles with hover states

### 2. UI Enhancements (ui-enhancements.css)

#### Timeline Component
```css
.timeline-row {
  display: flex;
  align-items: flex-start;
  gap: var(--space-md);
  padding: var(--space-md);
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--text-secondary);
  flex-shrink: 0;
}

.dot.active {
  background: var(--primary);
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.2);
}
```

#### Pills & Badges
```css
.pill {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
}

.pill.high {
  background: rgba(239, 68, 68, 0.1);
  color: var(--error);
}

.pill.medium {
  background: rgba(245, 158, 11, 0.1);
  color: var(--warning);
}

.pill.low {
  background: rgba(16, 185, 129, 0.1);
  color: var(--success);
}
```

#### Notifications
- Toast-style notifications
- Position: Top-right corner
- Types: Success, error, warning, info
- Auto-dismiss with animation
- Icon support

#### Loading States
- Button loading spinner
- Skeleton screens for content loading
- Progress indicators
- Disabled state styling

#### Modals & Overlays
- Modal backdrop with blur effect
- Modal container with animation
- Close button styling
- Responsive modal sizing

#### Animations & Transitions
- Fade in/out animations
- Slide animations for notifications
- Smooth transitions for interactive elements
- Loading spinner keyframes

## Data Models

### CSS Class Naming Convention

The design follows BEM (Block Element Modifier) naming convention:

```
.block {}
.block__element {}
.block--modifier {}
```

**Examples:**
- `.timeline-row` (block)
- `.timeline-row__dot` (element)
- `.timeline-row--active` (modifier)

### State Classes

- `.active` - Active/current state
- `.disabled` - Disabled state
- `.loading` - Loading state
- `.error` - Error state
- `.success` - Success state
- `.dragging` - Drag-over state

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: CSS Files Load Successfully
*For any* HTTP request to `frontend/styles.css` or `frontend/ui-enhancements.css`, the server should return a 200 status code and valid CSS content.
**Validates: Requirements 1.1, 1.2, 1.3**

### Property 2: Dark Theme Applied
*For any* page load, all background colors should use dark theme values (HSL lightness < 30%) and text colors should use light values (HSL lightness > 70%).
**Validates: Requirements 2.1**

### Property 3: Form Elements Styled Consistently
*For any* form element (input, button, select), the computed styles should include consistent border-radius, padding, and font-family values from CSS variables.
**Validates: Requirements 2.2**

### Property 4: Interactive Elements Have Focus States
*For any* interactive element (button, input, link), when focused, the element should have a visible outline or box-shadow that differs from the unfocused state.
**Validates: Requirements 2.4**

### Property 5: Risk Level Pills Display Correct Colors
*For any* risk level value (high, medium, low), the corresponding pill element should have a background color matching the defined color for that risk level.
**Validates: Requirements 3.4**

### Property 6: CSS Variables Defined
*For any* CSS custom property used in the stylesheets, it should be defined in the `:root` selector.
**Validates: Requirements 2.1, 2.2, 2.3**

### Property 7: Responsive Breakpoints Applied
*For any* viewport width below 768px, the layout should apply mobile-specific styles (single column, adjusted spacing).
**Validates: Requirements 4.3**

## Error Handling

### Missing CSS Files
- **Issue**: CSS files return 404
- **Solution**: Create both CSS files with complete styles
- **Fallback**: Browser default styles (degraded experience)

### CSS Syntax Errors
- **Issue**: Invalid CSS causes parsing errors
- **Solution**: Validate CSS syntax before deployment
- **Detection**: Browser DevTools console warnings

### CSS Variable Not Defined
- **Issue**: Reference to undefined CSS variable
- **Solution**: Ensure all variables defined in `:root`
- **Fallback**: Browser uses fallback value or ignores property

### Browser Compatibility
- **Issue**: CSS features not supported in older browsers
- **Solution**: Use widely-supported CSS features
- **Fallback**: Progressive enhancement approach

## Testing Strategy

### Unit Tests

**CSS Validation Tests:**
- Test that CSS files are valid (no syntax errors)
- Test that all CSS variables are defined
- Test that color values are valid hex/rgb/hsl

**Example Tests:**
```javascript
describe('CSS Files', () => {
  test('styles.css exists and is valid CSS', async () => {
    const response = await fetch('/frontend/styles.css');
    expect(response.status).toBe(200);
    const css = await response.text();
    expect(css).toContain(':root');
    expect(css).toContain('--primary');
  });

  test('ui-enhancements.css exists and is valid CSS', async () => {
    const response = await fetch('/frontend/ui-enhancements.css');
    expect(response.status).toBe(200);
    const css = await response.text();
    expect(css).toContain('.timeline-row');
    expect(css).toContain('.pill');
  });
});
```

**Visual Regression Tests:**
- Capture screenshots of key UI states
- Compare against baseline images
- Detect unintended visual changes

**Accessibility Tests:**
- Test color contrast ratios (WCAG AA compliance)
- Test focus indicators are visible
- Test keyboard navigation works

### Property-Based Tests

**Property Test 1: CSS Files Load Successfully**
```javascript
// Feature: frontend-assets-fix, Property 1: CSS Files Load Successfully
test('CSS files return 200 status', async () => {
  const files = ['frontend/styles.css', 'frontend/ui-enhancements.css'];
  
  for (const file of files) {
    const response = await fetch(`/${file}`);
    expect(response.status).toBe(200);
    expect(response.headers.get('content-type')).toContain('text/css');
  }
});
```

**Property Test 2: Dark Theme Applied**
```javascript
// Feature: frontend-assets-fix, Property 2: Dark Theme Applied
test('dark theme colors applied to body', () => {
  const body = document.body;
  const bgColor = window.getComputedStyle(body).backgroundColor;
  
  // Parse RGB and check lightness
  const rgb = bgColor.match(/\d+/g).map(Number);
  const lightness = (Math.max(...rgb) + Math.min(...rgb)) / 2 / 255;
  
  expect(lightness).toBeLessThan(0.3); // Dark background
});
```

**Property Test 3: Form Elements Styled Consistently**
```javascript
// Feature: frontend-assets-fix, Property 3: Form Elements Styled Consistently
test('form elements use consistent styling', () => {
  const inputs = document.querySelectorAll('input, button, select');
  const styles = Array.from(inputs).map(el => ({
    borderRadius: window.getComputedStyle(el).borderRadius,
    fontFamily: window.getComputedStyle(el).fontFamily
  }));
  
  // All should have border-radius defined
  styles.forEach(style => {
    expect(style.borderRadius).not.toBe('0px');
  });
  
  // All should use same font family
  const fontFamilies = new Set(styles.map(s => s.fontFamily));
  expect(fontFamilies.size).toBeLessThanOrEqual(2); // Allow for monospace
});
```

**Property Test 4: Interactive Elements Have Focus States**
```javascript
// Feature: frontend-assets-fix, Property 4: Interactive Elements Have Focus States
test('interactive elements have visible focus states', () => {
  const interactiveElements = document.querySelectorAll('button, input, a');
  
  interactiveElements.forEach(el => {
    el.focus();
    const focusedStyle = window.getComputedStyle(el);
    const outline = focusedStyle.outline;
    const boxShadow = focusedStyle.boxShadow;
    
    // Should have either outline or box-shadow when focused
    expect(outline !== 'none' || boxShadow !== 'none').toBe(true);
  });
});
```

**Property Test 5: Risk Level Pills Display Correct Colors**
```javascript
// Feature: frontend-assets-fix, Property 5: Risk Level Pills Display Correct Colors
test('risk level pills have correct colors', () => {
  const riskLevels = ['high', 'medium', 'low'];
  const expectedColors = {
    high: 'rgb(239, 68, 68)',
    medium: 'rgb(245, 158, 11)',
    low: 'rgb(16, 185, 129)'
  };
  
  riskLevels.forEach(level => {
    const pill = document.createElement('div');
    pill.className = `pill ${level}`;
    document.body.appendChild(pill);
    
    const color = window.getComputedStyle(pill).color;
    expect(color).toBe(expectedColors[level]);
    
    document.body.removeChild(pill);
  });
});
```

**Property Test 6: CSS Variables Defined**
```javascript
// Feature: frontend-assets-fix, Property 6: CSS Variables Defined
test('all CSS variables are defined in :root', async () => {
  const response = await fetch('/frontend/styles.css');
  const css = await response.text();
  
  // Extract all variable usages
  const usages = css.match(/var\(--[\w-]+\)/g) || [];
  const usedVars = usages.map(v => v.match(/--[\w-]+/)[0]);
  
  // Extract all variable definitions
  const rootBlock = css.match(/:root\s*{[^}]+}/s)[0];
  const definitions = rootBlock.match(/--[\w-]+:/g) || [];
  const definedVars = definitions.map(v => v.replace(':', ''));
  
  // All used variables should be defined
  usedVars.forEach(varName => {
    expect(definedVars).toContain(varName);
  });
});
```

**Property Test 7: Responsive Breakpoints Applied**
```javascript
// Feature: frontend-assets-fix, Property 7: Responsive Breakpoints Applied
test('mobile styles applied at small viewport', () => {
  // Set viewport to mobile size
  window.innerWidth = 375;
  window.dispatchEvent(new Event('resize'));
  
  const container = document.querySelector('.container');
  const style = window.getComputedStyle(container);
  
  // Should have mobile-specific padding
  const padding = parseInt(style.paddingLeft);
  expect(padding).toBeLessThanOrEqual(16); // Mobile padding
});
```

### Testing Configuration

- **Framework**: Vitest (already configured in project)
- **Test Location**: `frontend/__tests__/styles.test.js`
- **Minimum Iterations**: 100 per property test
- **Coverage Target**: 100% of CSS files

### Manual Testing Checklist

- [ ] Load application in Chrome, Firefox, Safari, Edge
- [ ] Verify dark theme applied correctly
- [ ] Test form interactions (focus, hover, active states)
- [ ] Test drag-and-drop file upload styling
- [ ] Verify timeline component renders correctly
- [ ] Test risk level pills display correct colors
- [ ] Verify notifications appear and animate correctly
- [ ] Test responsive layout at different screen sizes
- [ ] Verify loading states display correctly
- [ ] Test modal/overlay functionality
