# Technical Context - MCP Browser (Optimized)

## Core Stack

*   **Language**: Python 3.13+
*   **Framework**: FastAPI (>=0.108.0)
*   **Browser**: Playwright (>=1.51.0) with Chromium
*   **Container**: Docker (+Compose)
*   **Display**: Xvfb
*   **Security**: AppArmor
*   **Comms**: WebSockets (websockets >=15.0.1), Uvicorn (>=0.24.0)
*   **Packaging**: uv, pyproject.toml

## Key Dependencies (Check `pyproject.toml` for full list)

*   **Runtime**: `fastapi`, `playwright`, `uvicorn`, `websockets`, `psutil`, `pydantic`, `docker`
*   **Testing**: `pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-timeout`

## Dev Environment

*   **Prereqs**: Python 3.13+, Docker, uv
*   **Setup**: `uv venv .venv && source .venv/bin/activate && uv pip install -e . && uv pip install -r requirements-test.txt`
*   **Run (Docker)**: `docker-compose up -d`
*   **Test**: `pytest tests/` or `make test`

## Constraints & Considerations

*   Python >= 3.13 required.
*   Resource target: < 300MB RAM per browser instance.
*   Security layers (AppArmor, non-root, resource limits, network isolation) are critical.

## Deployment

*   Docker Compose (`docker-compose.yml`).
*   Config via `.env` file.

## Testing

*   `pytest` framework.
*   Unit, Integration, E2E tests.
*   Key plugins: `pytest-asyncio`, `pytest-cov`, `pytest-timeout`.
*   Current Issue: Tests involving `page.goto` are timing out; requires further investigation (see `active-context.md`).

## Monitoring Stack (Planned)

*   **System**: NetData
*   **Logs**: Loki + Grafana
*   **Containers**: cAdvisor

## Security Layers

*   **Network**: SSH Tunnel (optional), Firewall rules, Rate Limiting (FastAPI middleware).
*   **Application**: JWT Auth (planned), Input validation (Pydantic).
*   **Container**: AppArmor profiles (`docker/apparmor/`), Non-root user, Docker resource quotas.
*   **Browser**: Isolated contexts, Xvfb sandbox, Network restrictions (via `BrowserPool` config).

## API Design Principles

*   **Request**: Pydantic models for validation, required `url`.
*   **Response**: Consistent JSON structure (status, metadata, result/file ref).
*   **Error**: Standard HTTP codes, detailed JSON body, server-side logging.
*   **Docs**: Auto-generated via FastAPI (OpenAPI).

## Testing Strategy

*   **Framework**: Pytest
*   **Types**: Unit, Integration (mocking), E2E (real sites).
*   **Tools**: `pytest-asyncio`, `pytest-cov`, `pytest-timeout`.

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

## Technologies Used

### Core Technologies

- **Python 3.13+**: Primary programming language
- **FastAPI**: Web framework for building APIs
- **Playwright**: Browser automation library
- **Pydantic**: Data validation and settings management
- **Uvicorn**: ASGI server implementation
- **WebSockets**: Protocol for real-time communication
- **asyncio**: Asynchronous I/O library for concurrent code

### Supporting Libraries

- **websockets**: Python library for WebSocket client/server implementation
- **uuid**: Library for generating unique identifiers
- **aiohttp**: Asynchronous HTTP client/server framework
- **json**: JSON encoding/decoding
- **httpx**: Fully asynchronous HTTP client
- **aiofiles**: Asynchronous file operations

### Development Tools

- **uv**: Fast Python package installer
- **Docker**: Containerization
- **Xvfb**: Virtual framebuffer for X11 (for headless environments)
- **pytest**: Testing framework
- **autopep8**: Code formatter

## Development Setup

The project requires:

1. Python 3.13 or higher
2. uv for dependency management
3. Playwright browsers installed

Setup commands:
```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e .
python -m playwright install
```

## Technical Constraints

1. **Browser Compatibility**: The system targets Chromium-based browsers for consistent behavior.
2. **Memory Usage**: Browser automation is memory-intensive, requiring at least 2GB RAM.
3. **Event Broadcasting**: WebSocket connections for event subscriptions require consideration for scaling.
4. **Asynchronous Architecture**: All components must be designed to work in an asynchronous environment.

## Dependencies

### Core Dependencies

```
fastapi>=0.97.0
playwright>=1.40.0
uvicorn>=0.22.0
pydantic>=2.0.0
websockets>=11.0.3
```

### Test Dependencies

```
pytest>=7.0.0
httpx>=0.24.1
pytest-asyncio>=0.21.1
```

## Configuration

Key environment variables:
- `SERVER_PORT`: Web server port (default: 7665)
- `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD`: Skip browser download for headless mode
- `MCP_SECRET`: Secret key for MCP authentication

## Deployment

The application supports:
1. Local development environment
2. Docker containerized deployment
3. Production deployment with appropriate scaling

## Third-Party Integrations

The system is designed to integrate with:
1. **MCP**: For AI agent communication
2. **External services**: Via the HTTP API
3. **Client applications**: Via WebSockets and HTTP API 