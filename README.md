# MCP Browser

A headless browser interface for the Model Control Protocol (MCP).

## Features

- Headless browser automation using Playwright
- Web UI for browser interaction
- WebSocket communication for real-time updates
- Integration with MCP for AI agents

## Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) for dependency management
- Docker (for containerized usage)

## Local Development

### Setup with uv

```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-browser.git
cd mcp-browser

# Install dependencies
uv venv .venv
source .venv/bin/activate
uv pip install -e .

# Install Playwright browsers
python -m playwright install
```

### Running Locally

For a simple test without Xvfb:

```bash
./simple_test.sh
```

For a full test with Xvfb (requires X11):

```bash
./test_local.sh
```

## Docker Deployment

Build and run using Docker Compose:

```bash
# Set your MCP secret
export MCP_SECRET=your_secret_key

# Build and run
docker-compose up --build
```

Or use the provided script:

```bash
./run.sh
```

## Configuration

The following environment variables can be set:

- `MCP_SECRET`: Secret key for MCP authentication
- `SERVER_PORT`: Port to run the server on (default: 7665)
- `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD`: Set to 1 to skip browser download and run in headless-only mode

## API Endpoints

- `GET /`: Web UI
- `GET /api/status`: Get browser and MCP client status
- `WebSocket /ws`: WebSocket endpoint for real-time communication

## License

MIT
