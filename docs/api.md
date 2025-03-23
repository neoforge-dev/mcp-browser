# MCP Browser API Documentation

## Frontend Analysis Endpoints

### Screenshot Capture

**Endpoint:** `POST /api/screenshots/capture`

Captures a screenshot of a web page with configurable options.

**Parameters:**
- `url` (string, required): The URL of the page to capture
- `viewport` (object, optional): The viewport size, default: `{"width": 1280, "height": 800}`
- `full_page` (boolean, optional): Whether to capture the full page or just the viewport, default: `true`
- `format` (string, optional): Image format, options: "png" or "jpeg", default: "png"
- `quality` (integer, optional): Image quality for JPEG format (1-100), default: None
- `wait_until` (string, optional): When to consider navigation finished, default: "networkidle"

**Example Request:**
```json
{
  "url": "https://example.com",
  "viewport": {
    "width": 1920,
    "height": 1080
  },
  "full_page": true,
  "format": "png",
  "wait_until": "networkidle"
}
```

**Example Response:**
```json
{
  "success": true,
  "screenshot": "base64_encoded_image_data...",
  "format": "png",
  "viewport": {
    "width": 1920,
    "height": 1080
  },
  "url": "https://example.com"
}
```

### DOM Extraction

**Endpoint:** `POST /api/dom/extract`

Extracts DOM elements from a web page with optional style computation.

**Parameters:**
- `url` (string, required): The URL of the page to analyze
- `selector` (string, optional): CSS selector for elements to extract, if not provided extracts entire DOM
- `include_styles` (boolean, optional): Whether to include computed styles, default: `false`
- `include_attributes` (boolean, optional): Whether to include element attributes, default: `true`

**Example Request:**
```json
{
  "url": "https://example.com",
  "selector": "h1",
  "include_styles": true,
  "include_attributes": true
}
```

**Example Response:**
```json
{
  "success": true,
  "url": "https://example.com",
  "dom": [
    {
      "tagName": "h1",
      "textContent": "Example Domain",
      "isVisible": true,
      "boundingBox": {
        "x": 192,
        "y": 192,
        "width": 896,
        "height": 38
      },
      "attributes": {
        "class": "heading"
      },
      "styles": {
        "color": "rgb(0, 0, 0)",
        "font-size": "32px",
        "margin": "0px"
      }
    }
  ]
}
```

### CSS Analysis

**Endpoint:** `POST /api/css/analyze`

Analyzes CSS properties of selected elements on a web page.

**Parameters:**
- `url` (string, required): The URL of the page to analyze
- `selector` (string, required): CSS selector for elements to analyze
- `properties` (array, optional): Specific CSS properties to analyze, if not provided returns most common properties
- `check_accessibility` (boolean, optional): Whether to include accessibility checks, default: `false`

**Example Request:**
```json
{
  "url": "https://example.com",
  "selector": "p",
  "properties": ["color", "font-size", "margin", "padding"],
  "check_accessibility": true
}
```

**Example Response:**
```json
{
  "success": true,
  "url": "https://example.com",
  "selector": "p",
  "elements": [
    {
      "tagName": "p",
      "textContent": "This domain is for use in illustrative examples in documents.",
      "isVisible": true,
      "boundingBox": {
        "x": 192,
        "y": 240,
        "width": 896,
        "height": 72
      },
      "styles": {
        "color": "rgb(0, 0, 0)",
        "font-size": "16px",
        "margin": "16px 0px",
        "padding": "0px"
      },
      "accessibility": {
        "colorContrast": null,
        "hasAltText": null,
        "hasAriaLabel": false,
        "isFocusable": false,
        "backgroundColor": "rgb(255, 255, 255)",
        "textColor": "rgb(0, 0, 0)"
      }
    }
  ],
  "count": 1
}
```

### Accessibility Testing

**Endpoint:** `POST /api/accessibility/test`

Tests a web page for accessibility issues using axe-core.

**Parameters:**
- `url` (string, required): The URL of the page to test
- `standard` (string, optional): Accessibility standard to test against, options: "wcag2a", "wcag2aa", "wcag2aaa", "wcag21aa", "section508", default: "wcag2aa"
- `include_html` (boolean, optional): Whether to include HTML context in results, default: `true`
- `include_warnings` (boolean, optional): Whether to include warnings in results, default: `true`
- `selectors` (array, optional): List of CSS selectors to test, if not provided tests the entire page

**Example Request:**
```json
{
  "url": "https://example.com",
  "standard": "wcag2aa",
  "include_html": true,
  "include_warnings": true,
  "selectors": ["main", "nav"]
}
```

**Example Response:**
```json
{
  "url": "https://example.com",
  "timestamp": 1742762305,
  "standard": "wcag2aa",
  "results": {
    "testEngine": {
      "name": "axe-core",
      "version": "4.7.0"
    },
    "violations": [
      {
        "id": "color-contrast",
        "impact": "serious",
        "nodes": [
          {
            "html": "<p style=\"color: #999\">Low contrast text</p>",
            "target": ["p:nth-child(2)"],
            "failureSummary": "Element has insufficient color contrast"
          }
        ]
      }
    ],
    "passes": [...],
    "incomplete": [...],
    "inapplicable": [...]
  },
  "output_file": "output/accessibility_test_1742762305.json"
}
```

### Responsive Design Testing

**Endpoint:** `POST /api/responsive/test`

Tests a web page across different viewport sizes to analyze responsive behavior.

**Parameters:**
- `url` (string, required): The URL of the page to test
- `viewports` (array, optional): List of viewport sizes to test, default:
  ```
  [
    {"width": 375, "height": 667},   # Mobile
    {"width": 768, "height": 1024},  # Tablet
    {"width": 1366, "height": 768},  # Laptop
    {"width": 1920, "height": 1080}  # Desktop
  ]
  ```
- `compare_elements` (boolean, optional): Whether to compare elements across viewports, default: `true`
- `include_screenshots` (boolean, optional): Whether to capture screenshots at each viewport, default: `true`
- `selectors` (array, optional): List of CSS selectors to test, required for element comparison
- `waiting_time` (integer, optional): Additional time to wait after page load in milliseconds, default: `null`

**Example Request:**
```json
{
  "url": "https://example.com",
  "viewports": [
    {"width": 375, "height": 667},
    {"width": 1366, "height": 768}
  ],
  "selectors": ["h1", "p", ".navigation"],
  "include_screenshots": true,
  "compare_elements": true
}
```

**Example Response:**
```json
{
  "url": "https://example.com",
  "timestamp": 1742762418,
  "viewports": [
    {"width": 375, "height": 667},
    {"width": 1366, "height": 768}
  ],
  "viewport_results": [
    {
      "viewport": {"width": 375, "height": 667},
      "viewport_name": "375x667",
      "page_metrics": {
        "documentWidth": 375,
        "documentHeight": 667,
        "viewportWidth": 375,
        "viewportHeight": 667,
        "mediaQueries": ["(max-width: 768px)"],
        "horizontalScrollPresent": false,
        "textOverflows": 0,
        "touchTargetSizes": 2
      },
      "elements_data": [...],
      "screenshot_path": "output/responsive/1742762418/screenshot_375x667.png"
    },
    {
      "viewport": {"width": 1366, "height": 768},
      "viewport_name": "1366x768",
      "page_metrics": {...},
      "elements_data": [...],
      "screenshot_path": "output/responsive/1742762418/screenshot_1366x768.png"
    }
  ],
  "element_comparison": {
    "h1": {
      "selector": "h1",
      "differences": [],
      "responsive_issues": []
    },
    "p": {
      "selector": "p",
      "differences": [],
      "responsive_issues": [
        {
          "element_key": "p-0",
          "issue": "visibility_change",
          "description": "Element visibility changes across viewports",
          "visibility": {
            "375x667": false,
            "1366x768": true
          }
        }
      ]
    }
  },
  "output_directory": "output/responsive/1742762418"
}
```

## WebSocket Interface

The MCP Browser provides a WebSocket interface for real-time communication with the browser.

**Endpoint:** `WebSocket /ws`

**Supported Actions:**
- `navigate`: Navigate to a URL
  ```json
  {
    "action": "navigate",
    "url": "https://example.com"
  }
  ``` 