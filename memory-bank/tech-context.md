# Technical Context - MCP Browser

## Core Stack
- **Language**: Python 3.12+
- **Framework**: FastAPI
- **Browser**: Playwright/Chromium
- **Container**: Docker
- **Security**: AppArmor
- **Server**: Uvicorn

## Key Dependencies
- **Runtime**: fastapi, playwright, uvicorn, websockets, psutil
- **Testing**: pytest, pytest-asyncio, pytest-timeout

## Dev Environment
- **Prereqs**: Python 3.12+, Docker
- **Setup**: `make build`
- **Run**: `docker-compose up -d`
- **Test**: `make test`

## Docker Setup
- Base: `mcr.microsoft.com/playwright:v1.50.0-noble`
- Entrypoint: `docker/xvfb-init.sh`
- Mounts: src/, tests/, config files
- Security: AppArmor profile

## Testing
- **Framework**: pytest
- **Timeout**: 300s
- **Fixtures**: browser_pool (session), browser_context (function)
- **Current Issue**: page.goto() timeout in Docker

## File Locations
- Source: src/
- Tests: tests/
- Docker: Dockerfile, docker-compose.yml, docker/
- Dependencies: pyproject.toml, requirements-test.txt

## Security Layers
- **Network**: Domain filtering, rate limiting
- **Container**: AppArmor, non-root, resource limits
- **Application**: Pydantic validation

## API Design
- **Request**: Pydantic models, validation
- **Response**: JSON (status, metadata, result)
- **Error**: HTTP codes, structured messages 