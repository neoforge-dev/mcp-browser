#!/usr/bin/env python3
"""
MCP Browser - A browser interface for MCP (Model Control Protocol)
"""
import os
import sys
import asyncio
import logging
import signal
import yaml
import json
import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp-browser")

# Simple MCP Client implementation
class MCPClient:
    """Simple MCP client implementation for browser functionality"""
    
    def __init__(self, model_name, server_url, api_key):
        self.model_name = model_name
        self.server_url = server_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
        logger.info(f"MCPClient initialized for {model_name} at {server_url}")
    
    async def close(self):
        """Close the client session"""
        if hasattr(self, 'session'):
            self.session.close()
        logger.info("MCPClient closed")
    
    async def send_command(self, command, data=None):
        """Send a command to the MCP server"""
        try:
            url = f"{self.server_url}/api/{command}"
            response = self.session.post(
                url,
                json=data or {}
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error sending command to MCP server: {e}")
            return {"error": str(e)}

# Get MCP Secret from environment
MCP_SECRET = os.environ.get("MCP_SECRET", "")
if not MCP_SECRET:
    logger.warning("MCP_SECRET not set. Some functionality may be limited.")

# Get server port from environment or use default
SERVER_PORT = int(os.environ.get("SERVER_PORT", "7665"))

# Check if running in headless mode
HEADLESS_MODE = os.environ.get("PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD", "0") == "1"
if HEADLESS_MODE:
    logger.info("Running in headless-only mode")

app = FastAPI(title="MCP Browser")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Playwright browser instance
browser = None
browser_context = None
playwright = None

# MCP Client
mcp_client = None

# WebSocket connections
active_connections = []

@app.on_event("startup")
async def startup_event():
    """Initialize browser and MCP client on startup"""
    global browser, browser_context, mcp_client, playwright
    
    # Initialize Playwright only if not in headless mode
    if not HEADLESS_MODE:
        try:
            logger.info("Initializing Playwright browser...")
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=True)
            browser_context = await browser.new_context()
            logger.info("Playwright browser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Playwright browser: {e}")
            logger.error("Browser features will be unavailable")
    else:
        logger.info("Skipping Playwright browser initialization in headless mode")
    
    # Initialize MCP client
    if MCP_SECRET:
        try:
            logger.info("Initializing MCP client...")
            mcp_client = MCPClient(
                model_name="browser-agent",
                server_url="http://localhost:7665",
                api_key=MCP_SECRET
            )
            logger.info("MCP client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize MCP client: {e}")
    else:
        logger.warning("Skipping MCP client initialization due to missing MCP_SECRET")
    
    logger.info("MCP Browser initialization complete")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    global browser, browser_context, mcp_client, playwright
    
    logger.info("Shutting down MCP Browser...")
    
    # Close all WebSocket connections
    for connection in active_connections:
        await connection.close()
    
    # Close browser
    if browser_context:
        await browser_context.close()
    if browser:
        await browser.close()
    if playwright:
        await playwright.stop()
    
    # Close MCP client
    if mcp_client:
        await mcp_client.close()
    
    logger.info("MCP Browser shutdown complete")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Return the main page HTML"""
    browser_status = "disabled (headless mode)" if HEADLESS_MODE else "initializing..."
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MCP Browser</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #333;
            }}
            #status {{
                margin: 20px 0;
                padding: 10px;
                background-color: #f0f0f0;
                border-radius: 5px;
            }}
            #terminal {{
                background-color: #1e1e1e;
                color: #f0f0f0;
                padding: 10px;
                border-radius: 5px;
                min-height: 200px;
                max-height: 400px;
                overflow-y: auto;
                font-family: monospace;
            }}
            .url-form {{
                margin: 20px 0;
                display: flex;
            }}
            .url-form input[type="text"] {{
                flex-grow: 1;
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px 0 0 4px;
            }}
            .url-form button {{
                padding: 8px 16px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 0 4px 4px 0;
                cursor: pointer;
            }}
            .url-form button:hover {{
                background-color: #45a049;
            }}
            .headless-warning {{
                background-color: #fff3cd;
                color: #856404;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 20px;
                display: {'' if HEADLESS_MODE else 'none'};
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>MCP Browser</h1>
            
            <div class="headless-warning">
                <strong>Note:</strong> Running in headless mode. Browser functionality is limited.
            </div>
            
            <div id="status">Status: Initializing...</div>
            
            <div class="url-form">
                <input type="text" id="url-input" placeholder="Enter URL to navigate" value="https://example.com">
                <button id="navigate-btn" {'' if not HEADLESS_MODE else 'disabled'}>Go</button>
            </div>
            
            <h2>Terminal Output</h2>
            <div id="terminal"></div>
        </div>

        <script>
            const terminal = document.getElementById('terminal');
            const status = document.getElementById('status');
            const urlInput = document.getElementById('url-input');
            const navigateBtn = document.getElementById('navigate-btn');
            
            // Connect to WebSocket
            const ws = new WebSocket(`ws://${{window.location.host}}/ws`);
            
            ws.onopen = () => {{
                status.innerText = 'Status: Connected';
                terminal.innerHTML += '<div>WebSocket connection established</div>';
            }};
            
            ws.onmessage = (event) => {{
                const data = JSON.parse(event.data);
                terminal.innerHTML += `<div>${{data.message}}</div>`;
                terminal.scrollTop = terminal.scrollHeight;
            }};
            
            ws.onclose = () => {{
                status.innerText = 'Status: Disconnected';
                terminal.innerHTML += '<div>WebSocket connection closed</div>';
            }};
            
            // URL navigation
            navigateBtn.addEventListener('click', () => {{
                const url = urlInput.value;
                if (url) {{
                    terminal.innerHTML += `<div>Navigating to: ${{url}}</div>`;
                    ws.send(JSON.stringify({{ action: 'navigate', url: url }}));
                }}
            }});
        </script>
    </body>
    </html>
    """

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # Send initial message
        await websocket.send_json({"message": "Connected to MCP Browser"})
        
        # Send headless mode notice if applicable
        if HEADLESS_MODE:
            await websocket.send_json({"message": "NOTE: Running in headless mode. Browser functionality is limited."})
        
        # Process incoming messages
        while True:
            data = await websocket.receive_text()
            try:
                json_data = json.loads(data)
                
                # Handle navigation
                if json_data.get('action') == 'navigate':
                    url = json_data.get('url')
                    if HEADLESS_MODE:
                        await websocket.send_json({"message": "Browser navigation is disabled in headless mode"})
                    elif url and browser_context:
                        try:
                            page = await browser_context.new_page()
                            await websocket.send_json({"message": f"Navigating to {url}..."})
                            await page.goto(url)
                            title = await page.title()
                            await websocket.send_json({"message": f"Loaded page: {title}"})
                        except Exception as e:
                            await websocket.send_json({"message": f"Error navigating: {str(e)}"})
                    else:
                        await websocket.send_json({"message": "Error: Missing URL or browser not initialized"})
                else:
                    await websocket.send_json({"message": f"Received: {data}"})
            except json.JSONDecodeError:
                await websocket.send_json({"message": f"Received (not JSON): {data}"})
    
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)

@app.get("/api/status")
async def get_status():
    """Return the status of the browser and MCP client"""
    return {
        "browser": "disabled" if HEADLESS_MODE else ("running" if browser else "not running"),
        "headless_mode": HEADLESS_MODE,
        "mcp": "connected" if mcp_client else "not connected"
    }

async def shutdown_gracefully():
    """Shutdown the application gracefully"""
    logger.info("Received shutdown signal. Shutting down...")
    await asyncio.sleep(0.5)  # Give FastAPI a moment to complete current requests
    sys.exit(0)

def handle_signal(sig, frame):
    """Handle process signals"""
    logger.info(f"Received signal {sig}")
    asyncio.create_task(shutdown_gracefully())

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Start the server
    logger.info(f"Starting MCP Browser server on port {SERVER_PORT}...")
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT) 