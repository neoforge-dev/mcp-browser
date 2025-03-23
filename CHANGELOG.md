# Changelog

## [0.2.0] - 2025-03-23

### Added
- Implemented Accessibility Testing API
  - Added `/api/accessibility/test` endpoint that analyzes web pages for accessibility issues
  - Support for multiple standards (WCAG 2.0 A/AA/AAA, WCAG 2.1 AA, Section 508)
  - Integration with axe-core for comprehensive accessibility testing
  - Element-specific testing with selectors
  - Detailed violation, warning, and incomplete results
  - HTML context inclusion for better debugging

- Implemented Responsive Design Testing API
  - Added `/api/responsive/test` endpoint that tests web pages across different viewport sizes
  - Support for multiple viewport testing (mobile, tablet, laptop, desktop)
  - Element comparison across viewport sizes to detect responsive layout issues
  - Media query analysis to identify breakpoints
  - Touch target size validation for mobile-friendly testing
  - Screenshots captured at each viewport size for visual comparison
  - Detailed metrics and responsive issue reporting

- Added API documentation in `docs/api.md`
- Created example scripts in `docs/examples/`
- Added GitHub PR template

### Fixed
- JavaScript boolean values in Playwright page.evaluate() functions
- Fixed proper output directory structure for API test results
- Improved error handling in API endpoints

## [0.1.0] - 2025-03-22

### Added
- Implemented core browser automation infrastructure
- Created Screenshot Capture API
  - Added `/api/screenshots/capture` endpoint with configurable options
  - Support for different viewport sizes
  - Full page and viewport-only screenshots
  - Multiple image formats (PNG/JPEG) and quality options

- Implemented DOM Extraction API
  - Added `/api/dom/extract` endpoint for DOM structure analysis
  - Support for CSS selector targeting
  - Optional style computation and attribute extraction

- Implemented CSS Analysis API
  - Added `/api/css/analyze` endpoint for CSS property analysis
  - Detailed style property extraction
  - Optional accessibility checking
  - Element visibility and positioning information

- Created testing framework with automated test scripts
- Set up Docker containerization with Playwright and Xvfb
- Established WebSocket interface for real-time communication
- Created comprehensive documentation in Memory Bank 