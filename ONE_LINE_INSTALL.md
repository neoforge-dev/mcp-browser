# MCP Browser One-Line Installation

## Mac Setup

To set up MCP Browser on your Mac with browser visualization for AI agents, run this command:

```bash
curl -sSL https://raw.githubusercontent.com/neoforge-dev/mcp-browser/main/install_one_line.sh | bash
```

## What This Does

This command:

1. Installs all required dependencies (including Homebrew if needed)
2. Sets up Docker and other prerequisites 
3. Configures MCP Browser with visualization support
4. Creates a browser test client for viewing and controlling the browser
5. Sets up WebSocket communication for real-time browser events
6. Provides configuration details for connecting your MCP client

## Requirements

- Mac running macOS
- Internet connection
- Administrator access

## Troubleshooting XQuartz Issues

If you encounter issues with XQuartz not starting properly during installation:

1. The installer will attempt to start XQuartz in several ways:
   - First by checking if it's already running
   - Then by trying to start it directly using the binary
   - Finally by opening the application

2. If automatic startup fails, you'll be prompted to start XQuartz manually:
   - Try running: `/Applications/Utilities/XQuartz.app/Contents/MacOS/X11`
   - Or open XQuartz from your Applications folder

3. Once XQuartz is running, press Enter to continue with the installation

## For iOS Development

For iOS app development as an MCP client:

1. Use the provided server URL, WebSocket endpoints, and secret generated during installation.
2. Implement WebSocket communication in your iOS app to connect to the MCP Browser server.
3. Utilize the API endpoints for browser control and event subscription.

## Manual Setup

If you prefer manual setup, you can:

1. Clone the repository: `git clone https://github.com/neoforge-dev/mcp-browser.git`
2. Navigate to the directory: `cd mcp-browser`
3. Run the installer: `./install.sh`

## Viewing and Testing

After installation, you can access:

- Test Client: `file:///Users/[username]/.mcp-browser/client/index.html`
- Server Status: `http://[mac-ip]:7665/api/status`

## Troubleshooting

If you encounter issues:

1. Check the installation log at `~/mcp-browser-install.log`
2. Ensure Docker is running properly
3. Check the Docker container logs: `cd ~/mcp-browser && docker-compose logs` 