# System Architecture & Patterns for MCP Browser

## System Architecture

```
┌─────────────────┐      ┌──────────────────┐
│                 │      │                  │
│  L3 AI Agent    │◄────►│  MCP Protocol    │
│  (Claude)       │      │                  │
│                 │      └────────┬─────────┘
└─────────────────┘               │
                                  ▼
┌─────────────────┐      ┌──────────────────┐
│                 │      │                  │
│  SSH Tunnel     │◄────►│  MCP Browser     │
│  (Security)     │      │  Service         │
│                 │      │                  │
└─────────────────┘      └────────┬─────────┘
                                  │
                                  ▼
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│                 │      │                  │      │                 │
│  Docker         │◄────►│  Playwright      │◄────►│  Xvfb Virtual   │
│  Container      │      │  Automation      │      │  Display        │
│                 │      │                  │      │                 │
└─────────────────┘      └────────┬─────────┘      └─────────────────┘
                                  │
                         ┌────────┴─────────┐
                         │                  │
                         │  Headless        │
                         │  Chromium        │
                         │                  │
                         └──────────────────┘
```

## Key Components

### 1. MCP Browser Service (FastAPI Application)
The central service that provides REST and WebSocket APIs for controlling the browser. 

**Responsibilities**:
- Manage browser sessions
- Process incoming MCP commands
- Return browser outputs to agents
- Log all operations
- Handle security and authentication

### 2. Playwright Automation Engine
Engine responsible for browser control and automation.

**Responsibilities**:
- Launch and manage browser instances
- Execute browser actions (navigation, clicks, etc.)
- Capture screenshots and DOM states
- Handle browser errors and timeouts

### 3. Xvfb Virtual Display
Virtual framebuffer that provides a display server for the headless browser.

**Responsibilities**:
- Provide X11 display environment for browser
- Isolate rendering from physical displays
- Enable screenshot and visual operations

### 4. Docker Container
Isolated environment for running the MCP Browser stack.

**Responsibilities**:
- Provide consistent execution environment
- Enforce security boundaries
- Manage resources and limits
- Enable easy deployment

### 5. SSH Tunnel
Secure connection for remote access to the service.

**Responsibilities**:
- Encrypt communications between agent and service
- Provide authentication layer
- Enable remote connections securely

## Design Patterns

### 1. Microservice Architecture
- Each component has a single responsibility
- Components communicate via well-defined interfaces
- Services can be deployed and scaled independently

### 2. Command Pattern
- Browser operations are represented as commands
- Commands are serialized, validated, and executed
- Results are returned in standardized formats

### 3. Observer Pattern
- WebSockets provide real-time updates on browser state
- Clients can subscribe to specific browser events
- Push notifications reduce polling and improve responsiveness

### 4. Factory Pattern
- Browser instances are created via factory methods
- Configuration parameters determine browser capabilities
- Resource management is centralized

## Data Flow

1. AI Agent sends command via MCP Protocol
2. MCP Browser Service receives and validates command
3. Command is translated to Playwright operations
4. Playwright executes operations in Headless Chromium
5. Results (screenshots, DOM, etc.) are captured
6. Results are formatted and returned to AI Agent
7. All operations are logged for monitoring

## Security Architecture

### Defense-in-Depth Strategy

1. **Network Level**:
   - SSH Tunnel encrypts all traffic
   - Firewall rules limit exposed ports
   - Rate limiting prevents abuse

2. **Application Level**:
   - JWT authentication for API access
   - Input validation for all parameters
   - Sanitization of all browser inputs

3. **Container Level**:
   - AppArmor profiles limit capabilities
   - Non-root user execution
   - Resource quotas prevent DoS

4. **Browser Level**:
   - Isolated browser context for each session
   - No persistent storage access
   - Restricted network access

## Key Technical Decisions

1. **Playwright over Puppeteer/Selenium**:
   - More reliable automation with fewer flaky tests
   - Better cross-browser support
   - Modern async/await API design
   - Better performance characteristics

2. **Headless Chromium as Primary Engine**:
   - Best compatibility with modern web applications
   - Excellent rendering performance
   - Strong developer tools API
   - Regular security updates

3. **Docker Containerization**:
   - Consistent environment across deployments
   - Security isolation
   - Simplified dependency management
   - Easy scaling and replication

4. **FastAPI Framework**:
   - High performance async capabilities
   - Automatic OpenAPI documentation
   - Type checking and validation
   - WebSocket support built-in

5. **Xvfb for Display**:
   - Lightweight virtual framebuffer
   - No GPU requirements
   - Works on headless servers
   - Long-established stability 

## API Endpoints

### Screenshot Capture API

**Endpoint:** `/api/screenshots/capture`

**Implementation Details:**
- Uses Playwright's screenshot functionality
- Supports both viewport and full-page screenshots
- Image format options: PNG (default) and JPEG with quality settings
- Configurable viewport dimensions
- Optional waiting mechanisms (load, networkidle, domcontentloaded)
- Results stored in `/output/screenshots/` with timestamp-based naming

**Request Parameters:**
```json
{
  "url": "https://example.com",
  "viewport": {"width": 1280, "height": 800},
  "fullPage": true,
  "format": "png",
  "quality": 90,
  "waitUntil": "networkidle",
  "selectors": ["#header", ".main-content"]
}
```

### DOM Extraction API

**Endpoint:** `/api/dom/extract`

**Implementation Details:**
- Implemented using Playwright's page.evaluate() function
- JavaScript execution in the browser context to extract DOM
- Supports full page or selector-targeted extraction
- Optional attribute and style inclusion
- Format options: HTML source or processed JSON
- Results stored in `/output/dom/` with timestamp-based naming

**Request Parameters:**
```json
{
  "url": "https://example.com",
  "selector": "#main-content",
  "includeAttributes": true,
  "includeStyles": true,
  "outputFormat": "json"
}
```

### CSS Analysis API

**Endpoint:** `/api/css/analyze`

**Implementation Details:**
- Uses Playwright for browser automation
- JavaScript execution to compute styles
- Optional property filtering
- Accessibility checks for color contrast
- Element positioning and visibility information
- Results stored in `/output/css/` with timestamp-based naming

**Request Parameters:**
```json
{
  "url": "https://example.com",
  "selectors": [".nav-item", "#main-content h1"],
  "properties": ["color", "font-size", "background-color"],
  "includeAccessibility": true,
  "includePositioning": true
}
```

### Accessibility Testing API

**Endpoint:** `/api/accessibility/test`

**Implementation Details:**
- Integration with axe-core for accessibility testing
- Multiple standard support (WCAG, Section 508)
- Selector-based testing capabilities
- Detailed violation reporting with HTML context
- Results stored in `/output/accessibility/` with timestamp-based naming

**Request Parameters:**
```json
{
  "url": "https://example.com",
  "standard": "wcag21aa",
  "selectors": ["#main-content", "nav"],
  "includeHtmlContext": true,
  "tags": ["color-contrast", "aria", "forms"]
}
```

### Responsive Design Testing API  

**Endpoint:** `/api/responsive/test`

**Implementation Details:**
- Multi-viewport testing infrastructure
- Element comparison across viewport sizes
- Media query analysis through JavaScript execution
- Touch target size validation for mobile viewports
- Screenshot capture at each viewport size
- Detailed metrics and responsive issue reporting
- Results stored in `/output/responsive/` with timestamp-based naming

**Request Parameters:**
```json
{
  "url": "https://example.com",
  "viewports": [
    {"name": "mobile", "width": 375, "height": 667},
    {"name": "tablet", "width": 768, "height": 1024},
    {"name": "desktop", "width": 1440, "height": 900}
  ],
  "selectors": [".nav-menu", "#hero-section", ".product-card"],
  "captureScreenshots": true,
  "analyzeMediaQueries": true,
  "checkTouchTargets": true
}
```

## Integration Patterns

### Browser Automation

The MCP Browser uses Playwright for browser automation with the following patterns:

1. **Browser Context Management**:
   - Single browser instance with multiple contexts
   - Context isolation for security and reliability
   - Custom viewport and user agent configuration

2. **Page Navigation Flow**:
   - Standard navigation with timeout and error handling
   - Wait until options (load, networkidle, domcontentloaded)
   - Navigation state verification

3. **JavaScript Execution**:
   - In-browser evaluation for DOM and CSS operations
   - Serialization of complex objects
   - Error handling for script execution

4. **Resource Management**:
   - Output organization by feature
   - Timestamp-based naming for artifacts
   - Cleanup routines for temporary files 