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

## Technologies Used

### Core Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.9+ | Primary programming language |
| FastAPI | 0.95.0+ | Web framework for API development |
| Uvicorn | 0.22.0+ | ASGI server for FastAPI |
| Playwright | 1.32.0+ | Browser automation for web page analysis |
| Docker | 20.10.0+ | Containerization for consistent environments |
| Xvfb | 1.20.0+ | Virtual framebuffer for headless browser |

### Frontend Analysis Dependencies

| Technology | Version | Purpose |
|------------|---------|---------|
| axe-core | 4.7.0+ | Accessibility testing and standards compliance |
| PIL (Pillow) | 9.5.0+ | Image processing for screenshots |
| BeautifulSoup | 4.12.0+ | HTML parsing and DOM operations |
| pydantic | 1.10.7+ | Data validation and settings management |
| pytest | 7.3.1+ | Test framework for API validation |

### Support Tools

| Technology | Version | Purpose |
|------------|---------|---------|
| GitHub Actions | N/A | CI/CD platform for automated testing |
| pre-commit | 3.3.1+ | Git hooks for code quality |
| black | 23.3.0+ | Code formatting |
| flake8 | 6.0.0+ | Code linting |
| mypy | 1.3.0+ | Static type checking |

## Development Environment

### Local Development Setup

1. **Prerequisites**:
   - Docker and Docker Compose
   - Python 3.9+
   - Git

2. **Environment Initialization**:
   ```bash
   # Clone repository
   git clone https://github.com/your-org/mcp-browser.git
   cd mcp-browser
   
   # Build and start Docker containers
   docker-compose up -d
   
   # Run the API server
   python -m scripts.run
   ```

3. **Testing Environment**:
   ```bash
   # Run tests
   pytest tests/
   
   # Run tests with coverage
   pytest --cov=app tests/
   ```

### Docker Environment

The Docker setup includes:

1. **Base Image**: Python 3.9-slim
2. **Browser Layer**: Playwright browsers installation
3. **Virtual Display**: Xvfb configuration
4. **Application Layer**: Application code and dependencies
5. **Output Volumes**: Mounted volumes for persistent output

The Dockerfile implements multi-stage building to minimize image size.

## API Design

### Request/Response Patterns

All API endpoints follow a consistent pattern:

1. **Request Structure**:
   - Required parameters: `url` (the target website)
   - Optional parameters: endpoint-specific configuration
   - Validation: Pydantic models for type safety

2. **Response Structure**:
   - Status information
   - Execution metadata (timing, browser info)
   - Result data in JSON format
   - File references for generated artifacts

3. **Error Handling**:
   - HTTP status codes for error categories
   - Detailed error messages in response body
   - Logging for debugging purposes

### API Data Flow

```
Request → Validation → Browser Setup → Page Navigation → Analysis → Result Processing → Response
```

### Authentication and Security

Current implementation uses:

1. API keys for basic authentication
2. Rate limiting by client IP
3. Input validation for all parameters
4. Timeout controls for browser operations
5. Resource limits in Docker container

## Testing Framework

The testing framework includes:

1. **Unit Tests**: Testing individual components and utilities
2. **Integration Tests**: Testing API endpoints with mock server
3. **End-to-End Tests**: Testing complete workflows with real websites
4. **Performance Tests**: Testing response times and resource usage

Test data includes a set of reference websites with known properties. 