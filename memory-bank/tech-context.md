# Technical Context for MCP Browser

## Core Technologies

### Programming Languages & Frameworks
- **Python 3.13+**: Primary development language
- **FastAPI**: Modern, high-performance web framework for APIs
- **Playwright**: Browser automation framework from Microsoft
- **Docker**: Containerization technology for consistent environments
- **WebSockets**: For real-time communication between agents and browser

### Infrastructure
- **Docker Compose**: For local development and simple deployments
- **Xvfb**: Virtual framebuffer for headless browser rendering
- **AppArmor**: Linux security module for application isolation
- **uv**: Fast Python package manager and installer

### Browser Technologies
- **Chromium**: Primary browser engine
- **WebKit/Firefox**: Secondary browser engines (optional support)
- **X11**: X Window System for display server
- **HTTPS/SSL**: For secure communication

## Development Environment

### Prerequisites
- Python 3.13+
- Docker and Docker Compose
- uv package manager
- (Optional) Xvfb or XQuartz for local testing

### Project Structure
```
mcp-browser/
├── docker/                 # Docker-related files
│   ├── apparmor/           # AppArmor security profiles
│   └── xvfb-init.sh        # Xvfb initialization script
├── src/                    # Source code
│   ├── __init__.py         # Package initialization 
│   └── main.py             # Main application code
├── tests/                  # Test suite
├── .dockerignore           # Docker ignore patterns
├── .env.example            # Environment variable templates
├── .gitignore              # Git ignore patterns
├── Dockerfile              # Docker build definition
├── docker-compose.yml      # Docker Compose configuration
├── pyproject.toml          # Python project metadata
├── README.md               # Project documentation
├── run.sh                  # Deployment script
└── simple_test.sh          # Local testing script
```

## Technical Constraints

1. **Hardware Requirements**:
   - Designed to run on modest hardware (older Mac/Linux PCs)
   - Memory optimization for headless operation (90% less RAM than full browsers)

2. **Security Constraints**:
   - Non-root execution is mandatory
   - AppArmor profiles must be configured properly
   - Resource limits enforced at container level

3. **Network Constraints**:
   - SSH tunneling for remote access
   - Secure WebSocket communication
   - Port controls and exposure management

## Key Dependencies

- **mcp**: Model Control Protocol for agent communication
- **fastapi**: Web framework for API endpoints
- **playwright**: Browser automation library
- **uvicorn**: ASGI server for FastAPI
- **pyyaml**: YAML parsing for configuration
- **python-jose**: JWT support for authentication
- **passlib**: Password hashing for security
- **bcrypt**: Secure password hashing algorithm
- **requests**: HTTP client library

## Monitoring Tools

- **NetData**: Real-time metrics collection
- **Loki + Grafana**: Log aggregation and visualization
- **cAdvisor**: Container resource monitoring

## Deployment Strategy

1. **Local Development**: Docker Compose with volume mounts
2. **Production**: Docker containers with resource constraints
3. **Scaling Strategy**: Horizontal scaling with container orchestration

## Security Architecture

1. **Web Security**: HTTPS, Rate limiting
2. **Container Security**: AppArmor, Non-root user, Resource limits
3. **Authentication**: JWT tokens, Environment-based secrets
4. **Browser Isolation**: Xvfb sandboxing, Container isolation 