# MCP Browser Examples

This directory contains example scripts and applications that demonstrate how to use various features of the MCP Browser.

## Available Examples

### 1. WebSocket Event Subscription

**File:** `event_subscription_example.py`

This example demonstrates how to use the WebSocket event subscription feature to receive real-time browser events. The script:

- Connects to the MCP Browser WebSocket events endpoint
- Subscribes to specific event types (PAGE, NETWORK, CONSOLE, DOM)
- Navigates to a test URL to generate events
- Receives and displays browser events in real-time
- Handles graceful shutdown and cleanup

**Usage:**

```bash
# Run with default settings
python event_subscription_example.py

# Or customize with options
python event_subscription_example.py --ws-url ws://localhost:7665/ws/browser/events --test-url https://example.com --timeout 120
```

**Command-line Options:**

- `--ws-url`: WebSocket URL (default: ws://localhost:7665/ws/browser/events)
- `--api-url`: API URL (default: http://localhost:7665)
- `--test-url`: URL to navigate to (default: https://example.com)
- `--timeout`: Timeout in seconds (default: 60)

**Requirements:**

- websockets
- asyncio
- aiohttp
- json

Install with:
```bash
pip install websockets aiohttp
```

## Running the Examples

Before running any examples, make sure the MCP Browser server is running:

```bash
# Go to the MCP Browser root directory
cd /path/to/mcp-browser

# Start the server
python src/main.py
```

Then, in a separate terminal, you can run any of the examples as described above.

## Creating Your Own Examples

Feel free to use these examples as a starting point for your own applications. The key patterns demonstrated include:

1. **API Interaction**: How to call the HTTP API endpoints
2. **WebSocket Communication**: How to establish WebSocket connections and handle messages
3. **Event Subscription**: How to subscribe to browser events and process them
4. **Error Handling**: How to handle errors and gracefully shutdown 