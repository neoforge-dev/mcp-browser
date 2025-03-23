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