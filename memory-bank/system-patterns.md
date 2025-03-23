# System Architecture & Patterns for MCP Browser

## System Architecture

The MCP Browser is built as a FastAPI application that acts as a bridge between client applications and a headless browser powered by Playwright. The architecture follows a modular design with several key components:

1. **HTTP API Layer**: REST endpoints for browser control and data extraction
2. **WebSocket Layer**: Real-time communication for events and interactive sessions
3. **Browser Control Layer**: Manages browser instances using Playwright
4. **Error Handling Layer**: Consistent error handling and reporting
5. **Data Processing Layer**: Processes and formats browser data for clients

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

### 5. REST API Design

The REST API follows a consistent pattern:
- Resource-oriented endpoints (e.g., `/api/browser/navigate`, `/api/browser/screenshot`)
- Query parameters for GET requests
- JSON bodies for POST requests
- Consistent response structure with success/error indicators

### 6. WebSocket Event Architecture

The WebSocket event system follows a publish-subscribe pattern:
1. **Connection Management**: 
   - Clients connect to the WebSocket endpoint
   - Connections are stored in a global connection pool
   - Disconnections clean up associated resources

2. **Subscription Management**:
   - Clients subscribe to specific event types
   - Subscriptions are stored with filters and client identifiers
   - Unsubscribing removes handlers and cleans up resources

3. **Event Broadcasting**:
   - Events are captured from browser actions
   - Events are filtered based on subscription criteria
   - Matching events are sent to subscribed clients

4. **Event Filtering**:
   - URL pattern matching using regular expressions
   - Page ID matching for specific page monitoring
   - Extensible filter mechanism for future criteria

### 7. Browser Control Pattern

The browser control layer follows a facade pattern:
- Encapsulates complex Playwright interactions
- Provides a simplified interface for common operations
- Handles browser lifecycle management
- Implements error recovery mechanisms

### 8. Error Handling Pattern

All API endpoints follow a consistent error handling approach:
- Try-except blocks with specific exception types
- Structured error responses with error codes and messages
- Detailed logging for debugging
- Graceful degradation when possible

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

## Component Relationships

1. **Browser Initialization Flow**:
   - FastAPI app starts
   - Playwright browser is launched
   - Global variables are initialized
   - API endpoints are registered

2. **Page Management Flow**:
   - Browser context is created
   - Pages are created within context
   - Pages are tracked in a global registry
   - Events are attached to pages

3. **Event Flow**:
   - Browser or page events occur
   - Events are captured by event handlers
   - Events are processed and formatted
   - Events are broadcast to subscribed clients

4. **Resource Cleanup Flow**:
   - WebSocket connections close
   - Subscriptions are removed
   - Page resources are released
   - Browser context is cleaned up when no longer needed

## Data Models

1. **Request Models**:
   - NavigateRequest: URL and navigation options
   - ClickRequest: Selector and click options
   - EvaluateRequest: JavaScript expression and arguments

2. **Response Models**:
   - StandardResponse: Success indicator and result/error data
   - ScreenshotResponse: Image data and metadata
   - ElementDataResponse: Element properties and attributes

3. **Event Models**:
   - EventType: Enumeration of event categories
   - EventName: Enumeration of specific event names
   - EventSubscriptionModel: Subscription details and filters
   - BrowserEvent: Event data structure for broadcasting

## Technical Decisions

1. **FastAPI for API Framework**:
   - Asynchronous request handling
   - Built-in WebSocket support
   - Automatic OpenAPI documentation
   - Pydantic integration for request/response validation

2. **Playwright for Browser Automation**:
   - Cross-browser support
   - Modern browser capabilities
   - Powerful selector engine
   - Asynchronous API design

3. **Asynchronous Architecture**:
   - Non-blocking I/O for all operations
   - Efficient handling of multiple concurrent requests
   - Support for long-running operations
   - Scalable event broadcasting

4. **JSON for Data Exchange**:
   - Human-readable for debugging
   - Compatible with all client technologies
   - Schema validation with Pydantic
   - Native browser support for WebSocket communication 