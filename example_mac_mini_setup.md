# Setting up an MCP Browser on Mac Mini

This guide demonstrates how to set up the MCP Browser on a Mac Mini with a single command, allowing Claude or other MCP clients to visualize and test web frontends.

## Quick Start (One-Line Installation)

Simply run this command in your terminal on the Mac Mini:

```bash
curl -sSL https://raw.githubusercontent.com/neoforge-dev/mcp-browser/main/install_one_line.sh | bash
```

## What Gets Installed

The one-line installer will:

1. Install required dependencies (Git, Docker, Python, XQuartz)
2. Clone the MCP Browser repository
3. Configure environment settings
4. Start the MCP Browser server in Docker
5. Create a browser test client for visualization

## Testing the Installation

After installation completes, you'll see connection details displayed:

```
========================================
      MCP Browser Installation Complete
========================================

Server URL: http://192.168.1.x:7665
API Status: http://192.168.1.x:7665/api/status
WebSocket:  ws://192.168.1.x:7665/ws
Event WS:   ws://192.168.1.x:7665/ws/browser/events

Test Client: file:///Users/username/.mcp-browser/client/index.html

Connection Details:
MCP Secret: abcd1234efgh5678...

Connect your MCP client to this Mac using:
IP: 192.168.1.x
Port: 7665
Secret: abcd1234efgh5678...
```

## Connecting Claude or Other MCP Clients

You can connect Claude or other MCP clients to the server using the displayed IP, port, and secret. The server provides:

1. RESTful API for browser control
2. WebSocket API for real-time events
3. Visual browser interface for testing

## For iOS Development

To develop an iOS app as an MCP client:

1. Connect to the WebSocket endpoint: `ws://mac-ip:7665/ws/browser/events`
2. Subscribe to browser events using the WebSocket protocol
3. Use the REST API endpoints to control the browser

## Troubleshooting

If you encounter issues:

1. Check the installation log: `~/mcp-browser-install.log`
2. Verify Docker is running: `docker ps`
3. Check server logs: `cd ~/mcp-browser && docker-compose logs`
4. Restart the server: `cd ~/mcp-browser && docker-compose restart` 