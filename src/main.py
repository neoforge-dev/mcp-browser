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
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Body, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
import uvicorn
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Callable, Set, Union
import time
from enum import Enum
from contextlib import asynccontextmanager
import httpx
import re
import datetime
import base64
import aiofiles
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp-browser")

# Event type and subscription models
class EventType(str, Enum):
    """Types of browser events"""
    PAGE = "PAGE"
    DOM = "DOM"
    CONSOLE = "CONSOLE"
    NETWORK = "NETWORK"

class EventName(str, Enum):
    """Specific event names"""
    # Page events
    PAGE_LOAD = "page.load"
    PAGE_ERROR = "page.error"
    PAGE_LIFECYCLE = "page.lifecycle"
    
    # DOM events
    DOM_MUTATION = "dom.mutation"
    DOM_ATTRIBUTE = "dom.attribute"
    DOM_CHILD = "dom.child"
    
    # Console events
    CONSOLE_LOG = "console.log"
    CONSOLE_ERROR = "console.error"
    CONSOLE_WARNING = "console.warning"
    
    # Network events
    NETWORK_REQUEST = "network.request"
    NETWORK_RESPONSE = "network.response"
    NETWORK_ERROR = "network.error"

class EventSubscriptionModel(BaseModel):
    """Model for event subscriptions"""
    subscription_id: str
    client_id: str
    event_types: List[str]
    filters: Optional[Dict[str, Any]] = None
    created_at: float = Field(default_factory=time.time)

class BrowserEvent(BaseModel):
    """Model for browser events"""
    type: EventType
    event: str
    timestamp: float = Field(default_factory=time.time)
    page_id: Optional[str] = None
    data: Dict[str, Any]

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

    # MCP Protocol Extensions for browser operations
    async def register_tools(self):
        """Register browser tools with the MCP server"""
        try:
            # Browser Navigation Tools
            await self.register_tool(
                name="browser_navigate",
                description="Navigate to a URL in the browser",
                parameters=[
                    {"name": "url", "type": "string", "description": "The URL to navigate to", "required": True},
                    {"name": "wait_until", "type": "string", "description": "Wait until event (load, domcontentloaded, networkidle)", "required": False},
                    {"name": "timeout", "type": "integer", "description": "Timeout in milliseconds", "required": False}
                ]
            )
            
            await self.register_tool(
                name="browser_back",
                description="Navigate back in the browser history",
                parameters=[
                    {"name": "wait_until", "type": "string", "description": "Wait until event (load, domcontentloaded, networkidle)", "required": False}
                ]
            )
            
            await self.register_tool(
                name="browser_forward", 
                description="Navigate forward in the browser history",
                parameters=[
                    {"name": "wait_until", "type": "string", "description": "Wait until event (load, domcontentloaded, networkidle)", "required": False}
                ]
            )
            
            await self.register_tool(
                name="browser_refresh",
                description="Refresh the current page",
                parameters=[
                    {"name": "wait_until", "type": "string", "description": "Wait until event (load, domcontentloaded, networkidle)", "required": False}
                ]
            )
            
            # DOM Manipulation Tools
            await self.register_tool(
                name="browser_click",
                description="Click on an element in the page",
                parameters=[
                    {"name": "selector", "type": "string", "description": "CSS selector for the element to click", "required": True},
                    {"name": "wait_for_navigation", "type": "boolean", "description": "Whether to wait for navigation after click", "required": False}
                ]
            )
            
            await self.register_tool(
                name="browser_type",
                description="Type text into an element",
                parameters=[
                    {"name": "selector", "type": "string", "description": "CSS selector for the element to type into", "required": True},
                    {"name": "text", "type": "string", "description": "Text to type", "required": True},
                    {"name": "delay", "type": "integer", "description": "Delay between keypresses in milliseconds", "required": False}
                ]
            )
            
            await self.register_tool(
                name="browser_select",
                description="Select an option from a dropdown",
                parameters=[
                    {"name": "selector", "type": "string", "description": "CSS selector for the select element", "required": True},
                    {"name": "value", "type": "string", "description": "Value to select", "required": True}
                ]
            )
            
            await self.register_tool(
                name="browser_fill_form",
                description="Fill multiple form fields at once",
                parameters=[
                    {"name": "form_data", "type": "object", "description": "Object with selector-value pairs for form fields", "required": True}
                ]
            )
            
            # Visual Analysis Tools
            await self.register_tool(
                name="browser_screenshot",
                description="Take a screenshot of the current page or element",
                parameters=[
                    {"name": "selector", "type": "string", "description": "CSS selector for the element to screenshot (optional)", "required": False},
                    {"name": "full_page", "type": "boolean", "description": "Whether to take a full page screenshot", "required": False},
                    {"name": "format", "type": "string", "description": "Image format (png or jpeg)", "required": False}
                ]
            )
            
            await self.register_tool(
                name="browser_extract_text",
                description="Extract text content from an element or page",
                parameters=[
                    {"name": "selector", "type": "string", "description": "CSS selector for the element (optional)", "required": False}
                ]
            )
            
            await self.register_tool(
                name="browser_check_visibility",
                description="Check if an element is visible on the page",
                parameters=[
                    {"name": "selector", "type": "string", "description": "CSS selector for the element", "required": True}
                ]
            )
            
            await self.register_tool(
                name="browser_wait_for_selector",
                description="Wait for an element to appear on the page",
                parameters=[
                    {"name": "selector", "type": "string", "description": "CSS selector for the element", "required": True},
                    {"name": "timeout", "type": "integer", "description": "Timeout in milliseconds", "required": False},
                    {"name": "state", "type": "string", "description": "State to wait for (visible, hidden, attached, detached)", "required": False}
                ]
            )
            
            # Advanced Browser Tools
            await self.register_tool(
                name="browser_evaluate",
                description="Evaluate JavaScript code in the browser context",
                parameters=[
                    {"name": "expression", "type": "string", "description": "JavaScript expression to evaluate", "required": True}
                ]
            )
            
            await self.register_tool(
                name="browser_get_url",
                description="Get the current page URL",
                parameters=[]
            )
            
            await self.register_tool(
                name="browser_get_title",
                description="Get the current page title",
                parameters=[]
            )
            
            logger.info("Registered browser tools with MCP server")
            return {"success": True}
        except Exception as e:
            logger.error(f"Error registering browser tools: {e}")
            return {"error": str(e)}
    
    async def register_tool(self, name, description, parameters):
        """Register a single tool with the MCP server"""
        try:
            tool_data = {
                "name": name,
                "description": description,
                "parameters": parameters
            }
            return await self.send_command("register_tool", tool_data)
        except Exception as e:
            logger.error(f"Error registering tool {name}: {e}")
            return {"error": str(e)}

# Get MCP Secret from environment
MCP_SECRET = os.environ.get("MCP_SECRET", "")
if not MCP_SECRET:
    logger.warning("MCP_SECRET not set. Some functionality may be limited.")

# Get server port from environment or use default
SERVER_PORT = int(os.environ.get("SERVER_PORT", "7665"))

# Set output directory
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output"))
os.makedirs(OUTPUT_DIR, exist_ok=True)
logger.info(f"Output directory: {OUTPUT_DIR}")

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

# Event subscriptions
event_connections = {}  # client_id -> WebSocket connection
active_subscriptions = {}  # subscription_id -> EventSubscriptionModel
subscription_handlers = {}  # event_name -> list of subscription_ids

# Event utility functions
async def broadcast_event(event: BrowserEvent):
    """Broadcast event to all subscribed clients"""
    # Find subscriptions for this event
    event_key = event.event
    if event_key not in subscription_handlers:
        return
    
    # Get subscriptions for this event
    subscription_ids = subscription_handlers.get(event_key, [])
    if not subscription_ids:
        return
    
    for sub_id in subscription_ids:
        subscription = active_subscriptions.get(sub_id)
        if not subscription:
            continue
        
        # Check filters if they exist
        if subscription.filters:
            if not _matches_filters(event, subscription.filters):
                continue
        
        # Send event to subscribed client
        websocket = event_connections.get(subscription.client_id)
        if websocket:
            try:
                await websocket.send_json(event.dict())
            except Exception as e:
                logger.error(f"Error sending event to client {subscription.client_id}: {e}")

def _matches_filters(event: BrowserEvent, filters: Dict[str, Any]) -> bool:
    """Check if event matches the filters"""
    # URL pattern matching
    if 'url_pattern' in filters and event.data.get('url'):
        import fnmatch
        if not fnmatch.fnmatch(event.data['url'], filters['url_pattern']):
            return False
    
    # Page ID matching
    if 'page_id' in filters and event.page_id:
        if event.page_id != filters['page_id']:
            return False
    
    # Additional custom filters can be added here
    
    return True

async def add_subscription(subscription: EventSubscriptionModel):
    """Add a new subscription"""
    subscription_id = subscription.subscription_id
    active_subscriptions[subscription_id] = subscription
    
    # Register subscription for each event type
    for event_type in subscription.event_types:
        if event_type not in subscription_handlers:
            subscription_handlers[event_type] = []
        subscription_handlers[event_type].append(subscription_id)
    
    return subscription_id

async def remove_subscription(subscription_id: str):
    """Remove a subscription"""
    if subscription_id not in active_subscriptions:
        return False
    
    subscription = active_subscriptions.pop(subscription_id)
    
    # Remove from event handlers
    for event_type in subscription.event_types:
        if event_type in subscription_handlers:
            if subscription_id in subscription_handlers[event_type]:
                subscription_handlers[event_type].remove(subscription_id)
    
    return True

# Define request models
class ViewportModel(BaseModel):
    width: int = 1280
    height: int = 800

class ScreenshotRequest(BaseModel):
    url: str
    viewport: Optional[ViewportModel] = None
    full_page: bool = True
    format: str = "png"
    quality: Optional[int] = None
    wait_until: str = "networkidle"

class DomExtractionRequest(BaseModel):
    url: str
    selector: Optional[str] = None
    include_styles: bool = False
    include_attributes: bool = True

class CssAnalysisRequest(BaseModel):
    url: str
    selector: str
    properties: Optional[List[str]] = None
    check_accessibility: bool = False

class AccessibilityTestRequest(BaseModel):
    url: str
    standard: str = "wcag2aa"  # Default to WCAG 2.0 AA
    include_html: bool = True
    selectors: Optional[List[str]] = None
    include_warnings: bool = True

class ResponsiveTestRequest(BaseModel):
    url: str
    viewports: List[Dict[str, int]] = [
        {"width": 375, "height": 667},   # Mobile
        {"width": 768, "height": 1024},  # Tablet
        {"width": 1366, "height": 768},  # Laptop
        {"width": 1920, "height": 1080}  # Desktop
    ]
    compare_elements: bool = True
    include_screenshots: bool = True
    selectors: Optional[List[str]] = None
    waiting_time: Optional[int] = None

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
            
            # Set up page event listeners for any new pages
            browser_context.on("page", handle_new_page)
            
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
            
            # Register MCP browser tools
            logger.info("Registering MCP browser tools...")
            await mcp_client.register_tools()
            
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
    """Get the status of the service"""
    return {"status": "ok", "browser": "initialized" if browser else "not_initialized"}

# MCP Browser Tools API Endpoints

# Browser Navigation Tools
@app.post("/api/browser/navigate")
async def browser_navigate(
    url: str,
    wait_until: str = "networkidle",
    timeout: int = 30000
):
    """Navigate to a URL in the browser"""
    if not browser or not browser_context:
        raise HTTPException(status_code=500, detail="Browser not initialized")
    
    try:
        pages = browser_context.pages
        if not pages or len(pages) == 0:
            # Create a new page if none exists
            page = await browser_context.new_page()
        else:
            page = pages[0]
        
        response = await page.goto(url, timeout=timeout, wait_until=wait_until)
        
        return {
            "success": True,
            "url": page.url,
            "title": await page.title(),
            "status": response.status if response else None
        }
    except Exception as e:
        logger.error(f"Error navigating to {url}: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/browser/back")
async def browser_back(
    wait_until: str = "networkidle"
):
    """Navigate back in the browser history"""
    if not browser or not browser_context:
        raise HTTPException(status_code=500, detail="Browser not initialized")
    
    try:
        pages = browser_context.pages
        if not pages or len(pages) == 0:
            return {"success": False, "error": "No browser pages open"}
        
        page = pages[0]
        await page.go_back(wait_until=wait_until)
        
        return {
            "success": True,
            "url": page.url,
            "title": await page.title()
        }
    except Exception as e:
        logger.error(f"Error navigating back: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/browser/forward")
async def browser_forward(
    wait_until: str = "networkidle"
):
    """Navigate forward in the browser history"""
    if not browser or not browser_context:
        raise HTTPException(status_code=500, detail="Browser not initialized")
    
    try:
        pages = browser_context.pages
        if not pages or len(pages) == 0:
            return {"success": False, "error": "No browser pages open"}
        
        page = pages[0]
        await page.go_forward(wait_until=wait_until)
        
        return {
            "success": True,
            "url": page.url,
            "title": await page.title()
        }
    except Exception as e:
        logger.error(f"Error navigating forward: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/browser/refresh")
async def browser_refresh(
    wait_until: str = "networkidle"
):
    """Refresh the current page"""
    if not browser or not browser_context:
        raise HTTPException(status_code=500, detail="Browser not initialized")
    
    try:
        pages = browser_context.pages
        if not pages or len(pages) == 0:
            return {"success": False, "error": "No browser pages open"}
        
        page = pages[0]
        await page.reload(wait_until=wait_until)
        
        return {
            "success": True,
            "url": page.url,
            "title": await page.title()
        }
    except Exception as e:
        logger.error(f"Error refreshing page: {e}")
        return {"success": False, "error": str(e)}

# DOM Manipulation Tools
@app.post("/api/browser/click")
async def browser_click(
    selector: str,
    button: str = "left",
    delay: int = 0,
    click_count: int = 1,
    position_x: Optional[int] = None,
    position_y: Optional[int] = None,
    modifiers: Optional[List[str]] = None,
    force: bool = False,
    no_wait_after: bool = False,
    strict: bool = False,
    timeout: int = 30000
):
    """Click on an element in the page"""
    if not browser or not browser_context:
        raise HTTPException(status_code=500, detail="Browser not initialized")
    
    position = {"x": position_x, "y": position_y} if position_x is not None and position_y is not None else None
    
    try:
        pages = browser_context.pages
        if not pages or len(pages) == 0:
            return {"success": False, "error": "No browser pages open"}
        
        page = pages[0]
        
        await page.click(
            selector,
            button=button,
            delay=delay,
            click_count=click_count,
            position=position,
            modifiers=modifiers,
            force=force,
            no_wait_after=no_wait_after,
            strict=strict,
            timeout=timeout
        )
        return {"success": True, "message": f"Clicked element: {selector}"}
    except Exception as e:
        logger.error(f"Error clicking element: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/browser/type")
async def browser_type(
    selector: str,
    text: str,
    delay: Optional[int] = None
):
    """Type text into an element"""
    if not browser or not browser_context:
        raise HTTPException(status_code=500, detail="Browser not initialized")
    
    try:
        pages = browser_context.pages
        if not pages or len(pages) == 0:
            return {"success": False, "error": "No browser pages open"}
        
        page = pages[0]
        await page.fill(selector, "")  # Clear the field first
        
        if delay is not None:
            await page.type(selector, text, delay=delay)
        else:
            await page.type(selector, text)
        
        return {
            "success": True,
            "selector": selector,
            "text": text
        }
    except Exception as e:
        logger.error(f"Error typing into element {selector}: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/browser/select")
async def browser_select(
    selector: str,
    value: str
):
    """Select an option from a dropdown"""
    if not browser or not browser_context:
        raise HTTPException(status_code=500, detail="Browser not initialized")
    
    try:
        pages = browser_context.pages
        if not pages or len(pages) == 0:
            return {"success": False, "error": "No browser pages open"}
        
        page = pages[0]
        await page.select_option(selector, value=value)
        
        return {
            "success": True,
            "selector": selector,
            "value": value
        }
    except Exception as e:
        logger.error(f"Error selecting option from element {selector}: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/browser/fill_form")
async def browser_fill_form(
    form_data: Dict[str, str]
):
    """Fill multiple form fields at once"""
    if not browser or not browser_context:
        raise HTTPException(status_code=500, detail="Browser not initialized")
    
    try:
        pages = browser_context.pages
        if not pages or len(pages) == 0:
            return {"success": False, "error": "No browser pages open"}
        
        page = pages[0]
        results = {}
        
        for selector, value in form_data.items():
            try:
                await page.fill(selector, value)
                results[selector] = {"success": True, "value": value}
            except Exception as e:
                results[selector] = {"success": False, "error": str(e)}
        
        return {
            "success": True,
            "results": results
        }
    except Exception as e:
        logger.error(f"Error filling form: {e}")
        return {"success": False, "error": str(e)}

# Visual Analysis Tools
@app.post("/api/browser/screenshot")
async def browser_screenshot(
    selector: Optional[str] = None,
    full_page: bool = False,
    quality: Optional[int] = None,
    omit_background: bool = False,
    timeout: int = 30000,
    type: str = "png",
    path: Optional[str] = None
):
    """Take a screenshot of the page or element"""
    if not browser or not browser_context:
        raise HTTPException(status_code=500, detail="Browser not initialized")
    
    try:
        pages = browser_context.pages
        if not pages or len(pages) == 0:
            return {"success": False, "error": "No browser pages open"}
        
        page = pages[0]
        
        if not path:
            # Generate a filename based on timestamp
            timestamp = int(time.time())
            filename = f"screenshot_{timestamp}.{type}"
            path = os.path.join(OUTPUT_DIR, filename)
        
        if selector:
            element = await page.query_selector(selector)
            if not element:
                return {"success": False, "error": f"Element not found: {selector}"}
            
            # Element screenshots don't support full_page parameter
            element_screenshot_options = {
                "path": path,
                "omit_background": omit_background,
                "timeout": timeout,
                "type": type
            }
            
            if quality is not None and type == "jpeg":
                element_screenshot_options["quality"] = quality
                
            await element.screenshot(**element_screenshot_options)
        else:
            # Page screenshots can use full_page parameter
            page_screenshot_options = {
                "path": path,
                "full_page": full_page,
                "omit_background": omit_background,
                "timeout": timeout,
                "type": type
            }
            
            if quality is not None and type == "jpeg":
                page_screenshot_options["quality"] = quality
                
            await page.screenshot(**page_screenshot_options)
        
        return {
            "success": True,
            "path": path,
            "full_page": full_page if not selector else None,
            "selector": selector
        }
    except Exception as e:
        logger.error(f"Error taking screenshot: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/browser/extract_text")
async def browser_extract_text(
    selector: Optional[str] = None
):
    """Extract text content from an element or page"""
    if not browser or not browser_context:
        raise HTTPException(status_code=500, detail="Browser not initialized")
    
    try:
        pages = browser_context.pages
        if not pages or len(pages) == 0:
            return {"success": False, "error": "No browser pages open"}
        
        page = pages[0]
        
        if selector:
            element = await page.query_selector(selector)
            if not element:
                return {"success": False, "error": f"Element not found: {selector}"}
            text = await element.text_content()
        else:
            text = await page.content()
        
        return {
            "success": True,
            "text": text,
            "selector": selector
        }
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/browser/check_visibility")
async def browser_check_visibility(
    selector: str,
    strict: bool = False,
    timeout: int = 30000
):
    """Check if an element is visible on the page"""
    if not browser or not browser_context:
        raise HTTPException(status_code=500, detail="Browser not initialized")
    
    try:
        pages = browser_context.pages
        if not pages or len(pages) == 0:
            return {"success": False, "error": "No browser pages open"}
        
        page = pages[0]
        
        is_visible = await page.is_visible(selector, strict=strict, timeout=timeout)
        return {"success": True, "visible": is_visible, "selector": selector}
    except Exception as e:
        logger.error(f"Error checking visibility: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/browser/wait_for_selector")
async def browser_wait_for_selector(
    selector: str,
    state: str = "visible",
    strict: bool = False,
    timeout: int = 30000
):
    """Wait for an element to appear on the page"""
    if not browser or not browser_context:
        raise HTTPException(status_code=500, detail="Browser not initialized")
    
    try:
        pages = browser_context.pages
        if not pages or len(pages) == 0:
            return {"success": False, "error": "No browser pages open"}
        
        page = pages[0]
        
        element = await page.wait_for_selector(selector, state=state, strict=strict, timeout=timeout)
        if element:
            return {"success": True, "selector": selector, "state": state}
        else:
            return {"success": False, "error": f"Element not found: {selector}"}
    except Exception as e:
        logger.error(f"Error waiting for selector: {e}")
        return {"success": False, "error": str(e)}

# Advanced Browser Tools
@app.post("/api/browser/evaluate")
async def browser_evaluate(
    expression: str,
    arg: Optional[str] = None
):
    """Evaluate JavaScript expression in the browser"""
    if not browser or not browser_context:
        raise HTTPException(status_code=500, detail="Browser not initialized")
    
    try:
        pages = browser_context.pages
        if not pages or len(pages) == 0:
            return {"success": False, "error": "No browser pages open"}
        
        page = pages[0]
        
        if arg:
            result = await page.evaluate(expression, arg)
        else:
            result = await page.evaluate(expression)
        
        return {
            "success": True,
            "result": result,
            "expression": expression
        }
    except Exception as e:
        logger.error(f"Error evaluating JavaScript: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/browser/get_url")
async def browser_get_url():
    """Get the current page URL"""
    if not browser or not browser_context:
        raise HTTPException(status_code=500, detail="Browser not initialized")
    
    try:
        pages = browser_context.pages
        if not pages or len(pages) == 0:
            return {"success": False, "error": "No browser pages open"}
        
        page = pages[0]
        url = page.url
        
        return {
            "success": True,
            "url": url
        }
    except Exception as e:
        logger.error(f"Error getting URL: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/browser/get_title")
async def browser_get_title():
    """Get the current page title"""
    if not browser or not browser_context:
        raise HTTPException(status_code=500, detail="Browser not initialized")
    
    try:
        pages = browser_context.pages
        if not pages or len(pages) == 0:
            return {"success": False, "error": "No browser pages open"}
        
        page = pages[0]
        title = await page.title()
        
        return {
            "success": True,
            "title": title
        }
    except Exception as e:
        logger.error(f"Error getting title: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/screenshots/capture")
async def capture_screenshot(
    request: Optional[ScreenshotRequest] = None,
    url: Optional[str] = Query(None),
    full_page: bool = Query(True),
    format: str = Query("png"),
    quality: Optional[int] = Query(None),
    wait_until: str = Query("networkidle"),
    viewport: Optional[Dict[str, int]] = Body(None)
):
    """
    Capture a screenshot of a web page
    
    Args:
        url: The URL to navigate to
        viewport: The viewport size (width and height)
        full_page: Whether to capture the full page or just the viewport
        format: The image format (png or jpeg)
        quality: The image quality (for jpeg only)
        wait_until: When to consider navigation finished
    
    Returns:
        The screenshot as base64 encoded string
    """
    global browser, browser_context
    
    # Combine query params and request body
    params = {}
    if request:
        params = request.dict()
    else:
        params = {
            "url": url,
            "full_page": full_page,
            "format": format,
            "quality": quality,
            "wait_until": wait_until
        }
        if viewport:
            params["viewport"] = viewport
        else:
            params["viewport"] = {"width": 1280, "height": 800}
    
    if not params.get("url"):
        return {"error": "URL is required"}
    
    if HEADLESS_MODE or not browser:
        return {"error": "Browser functionality is disabled or not initialized"}
    
    try:
        # Create a new page
        page = await browser_context.new_page()
        
        # Set viewport size
        await page.set_viewport_size({"width": params["viewport"]["width"], "height": params["viewport"]["height"]})
        
        # Navigate to the URL
        await page.goto(params["url"], wait_until=params["wait_until"])
        
        # Capture screenshot
        screenshot_options = {
            "full_page": params["full_page"],
            "type": params["format"]
        }
        
        if params["format"] == "jpeg" and params["quality"] is not None:
            screenshot_options["quality"] = params["quality"]
            
        screenshot_base64 = await page.screenshot(**screenshot_options)
        
        # Close the page
        await page.close()
        
        import base64
        screenshot_base64_str = base64.b64encode(screenshot_base64).decode('utf-8')
        
        return {
            "success": True,
            "screenshot": screenshot_base64_str,
            "format": params["format"],
            "viewport": params["viewport"],
            "url": params["url"]
        }
    except Exception as e:
        logger.error(f"Error capturing screenshot: {e}")
        return {"error": str(e)}

@app.post("/api/dom/extract")
async def extract_dom(
    request: Optional[DomExtractionRequest] = None,
    url: Optional[str] = Query(None),
    selector: Optional[str] = Query(None),
    include_styles: bool = Query(False),
    include_attributes: bool = Query(True)
):
    """
    Extract DOM elements from a web page
    
    Args:
        url: The URL to navigate to
        selector: CSS selector for elements to extract (if None, extracts entire DOM)
        include_styles: Whether to include computed styles
        include_attributes: Whether to include element attributes
    
    Returns:
        Dictionary with DOM information
    """
    global browser, browser_context
    
    # Combine query params and request body
    params = {}
    if request:
        params = request.dict()
    else:
        params = {
            "url": url,
            "selector": selector,
            "include_styles": include_styles,
            "include_attributes": include_attributes
        }
    
    if not params.get("url"):
        return {"error": "URL is required"}
    
    if HEADLESS_MODE or not browser:
        return {"error": "Browser functionality is disabled or not initialized"}
    
    try:
        # Create a new page
        page = await browser_context.new_page()
        
        # Navigate to the URL
        await page.goto(params["url"], wait_until="networkidle")
        
        # Extract DOM information based on selector
        if params["selector"]:
            # Make sure the selector exists
            try:
                await page.wait_for_selector(params["selector"], timeout=5000)
            except Exception as e:
                await page.close()
                return {"error": f"Selector not found: {params['selector']}"}
                
            # Extract DOM information for the selected elements
            selector_js = params["selector"]
            include_styles_js = params["include_styles"]
            include_attributes_js = params["include_attributes"]
            
            script = f"""
            () => {{
                const selector = '{selector_js}';
                const includeStyles = {str(include_styles_js).lower()};
                const includeAttributes = {str(include_attributes_js).lower()};
                
                const elements = Array.from(document.querySelectorAll(selector));
                return elements.map(el => {{
                    const rect = el.getBoundingClientRect();
                    const result = {{
                        tagName: el.tagName.toLowerCase(),
                        textContent: el.textContent.trim(),
                        isVisible: rect.width > 0 && rect.height > 0,
                        boundingBox: {{
                            x: rect.x,
                            y: rect.y,
                            width: rect.width,
                            height: rect.height
                        }},
                        innerHTML: el.innerHTML
                    }};
                    
                    if (includeAttributes) {{
                        result.attributes = {{}};
                        Array.from(el.attributes).forEach(attr => {{
                            result.attributes[attr.name] = attr.value;
                        }});
                    }}
                    
                    if (includeStyles) {{
                        result.styles = {{}};
                        const computedStyle = window.getComputedStyle(el);
                        for (let i = 0; i < computedStyle.length; i++) {{
                            const prop = computedStyle[i];
                            result.styles[prop] = computedStyle.getPropertyValue(prop);
                        }}
                    }}
                    
                    return result;
                }});
            }}
            """
            # Pass the script without additional parameters
            dom_info = await page.evaluate(script)
        else:
            # Extract entire DOM structure
            include_styles_js = params["include_styles"]
            include_attributes_js = params["include_attributes"]
            
            script = f"""
            () => {{
                const includeStyles = {str(include_styles_js).lower()};
                const includeAttributes = {str(include_attributes_js).lower()};
                
                function processNode(node) {{
                    if (node.nodeType === Node.TEXT_NODE) {{
                        return {{
                            type: 'text',
                            content: node.textContent.trim()
                        }};
                    }}
                    
                    if (node.nodeType === Node.ELEMENT_NODE) {{
                        const result = {{
                            type: 'element',
                            tagName: node.tagName.toLowerCase(),
                            children: Array.from(node.childNodes).map(processNode).filter(n => {{
                                // Filter out empty text nodes
                                return !(n.type === 'text' && n.content === '');
                            }})
                        }};
                        
                        if (includeAttributes) {{
                            result.attributes = {{}};
                            Array.from(node.attributes).forEach(attr => {{
                                result.attributes[attr.name] = attr.value;
                            }});
                        }}
                        
                        if (includeStyles) {{
                            result.styles = {{}};
                            const computedStyle = window.getComputedStyle(node);
                            // Include only the most relevant styles to avoid huge output
                            const relevantStyles = [
                                'display', 'position', 'width', 'height', 'margin', 'padding',
                                'color', 'background-color', 'font-size', 'font-family'
                            ];
                            relevantStyles.forEach(prop => {{
                                result.styles[prop] = computedStyle.getPropertyValue(prop);
                            }});
                        }}
                        
                        return result;
                    }}
                    
                    return null;
                }}
                
                return processNode(document.documentElement);
            }}
            """
            # Pass the script without additional parameters
            dom_info = await page.evaluate(script)
        
        # Close the page
        await page.close()
        
        return {
            "success": True,
            "url": params["url"],
            "dom": dom_info
        }
    except Exception as e:
        logger.error(f"Error extracting DOM: {e}")
        return {"error": str(e)}

@app.post("/api/css/analyze")
async def analyze_css(
    request: Optional[CssAnalysisRequest] = None,
    url: Optional[str] = Query(None),
    selector: Optional[str] = Query(None),
    check_accessibility: bool = Query(False),
    properties: Optional[List[str]] = Body(None)
):
    """
    Analyze CSS properties for selected elements
    
    Args:
        url: The URL to navigate to
        selector: CSS selector for elements to analyze
        properties: List of specific CSS properties to analyze (if None, returns most common properties)
        check_accessibility: Whether to include accessibility-related checks
    
    Returns:
        Dictionary with CSS analysis results
    """
    global browser, browser_context
    
    # Combine query params and request body
    params = {}
    if request:
        params = request.dict()
    else:
        params = {
            "url": url,
            "selector": selector,
            "properties": properties,
            "check_accessibility": check_accessibility
        }
    
    if not params.get("url"):
        return {"error": "URL is required"}
    
    if not params.get("selector"):
        return {"error": "Selector is required"}
    
    if HEADLESS_MODE or not browser:
        return {"error": "Browser functionality is disabled or not initialized"}
    
    try:
        # Create a new page
        page = await browser_context.new_page()
        
        # Navigate to the URL
        await page.goto(params["url"], wait_until="networkidle")
        
        # Make sure the selector exists
        try:
            await page.wait_for_selector(params["selector"], timeout=5000)
        except Exception as e:
            await page.close()
            return {"error": f"Selector not found: {params['selector']}"}
        
        # If no specific properties requested, use a default set of important properties
        if not params["properties"]:
            params["properties"] = [
                "display", "position", "width", "height", "margin", "padding",
                "color", "background-color", "font-size", "font-family", "font-weight",
                "border", "box-shadow", "text-align", "flex", "grid",
                "opacity", "z-index", "overflow", "transition"
            ]
            
        # Extract CSS information for the selected elements
        selector_js = params["selector"]
        properties_js = params["properties"] or []
        check_accessibility_js = params["check_accessibility"]
        
        # Convert properties list to JavaScript array string
        properties_js_str = json.dumps(properties_js)
        
        script = f"""
        () => {{
            const selector = '{selector_js}';
            const properties = {properties_js_str};
            const checkAccessibility = {str(check_accessibility_js).lower()};
            
            const elements = Array.from(document.querySelectorAll(selector));
            const results = elements.map(el => {{
                const computedStyle = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                
                // Basic element info
                const result = {{
                    tagName: el.tagName.toLowerCase(),
                    textContent: el.textContent.trim(),
                    isVisible: rect.width > 0 && rect.height > 0,
                    boundingBox: {{
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height
                    }},
                    styles: {{}}
                }};
                
                // Get the requested CSS properties
                properties.forEach(prop => {{
                    result.styles[prop] = computedStyle.getPropertyValue(prop);
                }});
                
                // If accessibility checks are requested
                if (checkAccessibility) {{
                    result.accessibility = {{
                        colorContrast: null,  // Will be filled in below if possible
                        hasAltText: null,
                        hasAriaLabel: Boolean(el.getAttribute('aria-label')),
                        isFocusable: el.tabIndex >= 0
                    }};
                    
                    // Check for alt text on images
                    if (el.tagName.toLowerCase() === 'img') {{
                        result.accessibility.hasAltText = Boolean(el.getAttribute('alt'));
                    }}
                    
                    // Color contrast calculation (simplified version)
                    const bgColor = computedStyle.getPropertyValue('background-color');
                    const textColor = computedStyle.getPropertyValue('color');
                    if (bgColor && textColor) {{
                        // Here we'd normally calculate contrast ratio
                        // This is simplified to just record the colors for later analysis
                        result.accessibility.backgroundColor = bgColor;
                        result.accessibility.textColor = textColor;
                    }}
                }}
                
                return result;
            }});
            
            return results;
        }}
        """
        # Pass the script without additional parameters
        css_info = await page.evaluate(script)
        
        # Close the page
        await page.close()
        
        return {
            "success": True,
            "url": params["url"],
            "selector": params["selector"],
            "elements": css_info,
            "count": len(css_info)
        }
    except Exception as e:
        logger.error(f"Error analyzing CSS: {e}")
        return {"error": str(e)}

@app.post("/api/accessibility/test")
async def test_accessibility(
    request: Optional[AccessibilityTestRequest] = None,
    url: Optional[str] = Query(None),
    standard: str = Query("wcag2aa"),
    include_html: bool = Query(True),
    include_warnings: bool = Query(True),
    selectors: Optional[List[str]] = Body(None)
):
    """Test a web page for accessibility issues"""
    global browser_context
    
    # Handle both request body and query parameters
    if request is not None:
        url = request.url
        standard = request.standard
        include_html = request.include_html
        include_warnings = request.include_warnings
        selectors = request.selectors
    
    if not url:
        return JSONResponse(
            status_code=400,
            content={"error": "URL is required"}
        )
    
    if HEADLESS_MODE:
        return JSONResponse(
            status_code=503,
            content={"error": "Browser features are disabled in headless mode"}
        )
    
    if not browser_context:
        return JSONResponse(
            status_code=503,
            content={"error": "Browser is not initialized"}
        )
    
    # Valid standards
    valid_standards = ["wcag2a", "wcag2aa", "wcag2aaa", "wcag21aa", "section508"]
    if standard not in valid_standards:
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid standard. Valid options are: {', '.join(valid_standards)}"}
        )
    
    # Set up the timestamp for output files
    timestamp = int(time.time())
    output_file = f"output/accessibility_test_{timestamp}.json"
    
    try:
        # Create a new page
        page = await browser_context.new_page()
        
        try:
            # Navigate to the page
            logger.info(f"Navigating to {url} for accessibility testing")
            await page.goto(url, wait_until="networkidle")
            
            # Run accessibility audit with axe-core
            # This JavaScript function uses axe-core to perform accessibility checks
            accessibility_results = await page.evaluate(f"""
            async () => {{
                // Inject axe-core library if not already present
                if (!window.axe) {{
                    const axeSource = await fetch(
                        'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.7.0/axe.min.js'
                    ).then(response => response.text());
                    
                    const scriptElement = document.createElement('script');
                    scriptElement.textContent = axeSource;
                    document.head.appendChild(scriptElement);
                    
                    // Wait for axe to be fully loaded
                    await new Promise(resolve => {{
                        if (window.axe) {{
                            resolve();
                        }} else {{
                            scriptElement.onload = resolve;
                        }}
                    }});
                }}
                
                // Configure the axe options
                const options = {{
                    runOnly: {{
                        type: 'tag',
                        values: ['{standard}']
                    }},
                    resultTypes: ['violations', 'incomplete'],
                    elementRef: {str(include_html).lower()},
                    selectors: {json.dumps(selectors) if selectors else 'false'}
                }};
                
                if ({str(include_warnings).lower()}) {{
                    options.resultTypes.push('warnings');
                }}
                
                // Run the accessibility audit
                return await axe.run(document, options);
            }}
            """)
            
            # Process the results
            if accessibility_results:
                # Save results to file
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                
                with open(output_file, "w") as f:
                    json.dump(accessibility_results, f, indent=2)
                
                # Prepare the response
                response = {
                    "url": url,
                    "timestamp": timestamp,
                    "standard": standard,
                    "results": accessibility_results,
                    "output_file": output_file
                }
                
                return response
            else:
                return JSONResponse(
                    status_code=500,
                    content={"error": "Failed to retrieve accessibility results"}
                )
                
        except Exception as e:
            logger.error(f"Error testing accessibility: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Error testing accessibility: {str(e)}"}
            )
        finally:
            # Close the page to free resources
            await page.close()
            
    except Exception as e:
        logger.error(f"Error creating browser page: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error creating browser page: {str(e)}"}
        )

@app.post("/api/responsive/test")
async def test_responsive(
    request: Optional[ResponsiveTestRequest] = None,
    url: Optional[str] = Query(None),
    include_screenshots: bool = Query(True),
    compare_elements: bool = Query(True),
    waiting_time: Optional[int] = Query(None),
    viewports: Optional[List[Dict[str, int]]] = Body(None),
    selectors: Optional[List[str]] = Body(None)
):
    """Test a web page across different viewport sizes to analyze responsive behavior"""
    global browser_context
    
    # Handle both request body and query parameters
    if request is not None:
        url = request.url
        include_screenshots = request.include_screenshots
        compare_elements = request.compare_elements
        waiting_time = request.waiting_time
        viewports = request.viewports
        selectors = request.selectors
    
    if not url:
        return JSONResponse(
            status_code=400,
            content={"error": "URL is required"}
        )
    
    if HEADLESS_MODE:
        return JSONResponse(
            status_code=503,
            content={"error": "Browser features are disabled in headless mode"}
        )
    
    if not browser_context:
        return JSONResponse(
            status_code=503,
            content={"error": "Browser is not initialized"}
        )
    
    # Default viewports if not provided
    if not viewports:
        viewports = [
            {"width": 375, "height": 667},   # Mobile
            {"width": 768, "height": 1024},  # Tablet
            {"width": 1366, "height": 768},  # Laptop
            {"width": 1920, "height": 1080}  # Desktop
        ]
    
    # Set up the timestamp for output files
    timestamp = int(time.time())
    output_dir = f"output/responsive/{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    results_file = f"{output_dir}/responsive_test_{timestamp}.json"
    
    results = {
        "url": url,
        "timestamp": timestamp,
        "viewports": viewports,
        "viewport_results": [],
        "element_comparison": None,
        "output_directory": output_dir
    }
    
    try:
        # We'll create a new page for each viewport to ensure a clean test
        for i, viewport in enumerate(viewports):
            viewport_name = f"{viewport['width']}x{viewport['height']}"
            logger.info(f"Testing {url} at viewport {viewport_name}")
            
            # Create a new page with the specified viewport
            page = await browser_context.new_page()
            await page.set_viewport_size(viewport)
            
            try:
                # Navigate to the URL
                await page.goto(url, wait_until="networkidle")
                
                # Wait additional time if specified
                if waiting_time:
                    await asyncio.sleep(waiting_time / 1000)  # Convert to seconds
                
                # Capture a screenshot if requested
                screenshot_path = None
                if include_screenshots:
                    screenshot_path = f"{output_dir}/screenshot_{viewport_name}.png"
                    await page.screenshot(path=screenshot_path, full_page=True)
                
                # Extract element metrics if specified
                elements_data = None
                if selectors:
                    # Extract information about the specified elements
                    selectors_json = json.dumps(selectors)
                    elements_data = await page.evaluate(f"""
                    () => {{
                        const selectors = {selectors_json};
                        return selectors.map(selector => {{
                            const elements = Array.from(document.querySelectorAll(selector));
                            return {{
                                selector: selector,
                                count: elements.length,
                                elements: elements.map(el => {{
                                    const rect = el.getBoundingClientRect();
                                    return {{
                                        tagName: el.tagName.toLowerCase(),
                                        id: el.id || null,
                                        classes: Array.from(el.classList),
                                        boundingBox: {{
                                            x: rect.x,
                                            y: rect.y,
                                            width: rect.width,
                                            height: rect.height,
                                            top: rect.top,
                                            right: rect.right,
                                            bottom: rect.bottom,
                                            left: rect.left
                                        }},
                                        isVisible: rect.width > 0 && rect.height > 0 && 
                                                   window.getComputedStyle(el).display !== 'none' && 
                                                   window.getComputedStyle(el).visibility !== 'hidden',
                                        computedStyle: {{
                                            display: window.getComputedStyle(el).display,
                                            position: window.getComputedStyle(el).position,
                                            float: window.getComputedStyle(el).float,
                                            flexbox: window.getComputedStyle(el).flex !== '',
                                            grid: window.getComputedStyle(el).display.includes('grid'),
                                            media: window.matchMedia(`(max-width: ${{window.innerWidth}}px)`).matches
                                        }}
                                    }};
                                }})
                            }};
                        }});
                    }}
                    """)
                
                # Extract overall page metrics
                page_metrics = await page.evaluate("""
                () => {
                    return {
                        documentWidth: document.documentElement.scrollWidth,
                        documentHeight: document.documentElement.scrollHeight,
                        viewportWidth: window.innerWidth,
                        viewportHeight: window.innerHeight,
                        mediaQueries: Array.from(document.styleSheets)
                            .filter(sheet => {
                                try {
                                    return sheet.cssRules;
                                } catch (e) {
                                    return false;
                                }
                            })
                            .flatMap(sheet => Array.from(sheet.cssRules))
                            .filter(rule => rule.type === CSSRule.MEDIA_RULE)
                            .map(rule => rule.conditionText || rule.media.mediaText)
                            .filter(text => text.includes('width') || text.includes('height'))
                            .filter((text, index, self) => self.indexOf(text) === index),
                        horizontalScrollPresent: document.documentElement.scrollWidth > window.innerWidth,
                        textOverflows: Array.from(document.querySelectorAll('*'))
                            .filter(el => {
                                const style = window.getComputedStyle(el);
                                return el.scrollWidth > el.clientWidth && 
                                       style.overflow === 'hidden' && 
                                       style.textOverflow === 'ellipsis' &&
                                       el.textContent.trim().length > 0;
                            }).length,
                        touchTargetSizes: Array.from(document.querySelectorAll('button, a, [role="button"], input, select, textarea'))
                            .filter(el => {
                                const rect = el.getBoundingClientRect();
                                return rect.width > 0 && rect.height > 0 && (rect.width < 44 || rect.height < 44);
                            }).length
                    };
                }
                """)
                
                # Add the results for this viewport
                viewport_result = {
                    "viewport": viewport,
                    "viewport_name": viewport_name,
                    "page_metrics": page_metrics,
                    "elements_data": elements_data,
                    "screenshot_path": screenshot_path
                }
                
                results["viewport_results"].append(viewport_result)
                
            except Exception as e:
                logger.error(f"Error testing viewport {viewport_name}: {e}")
                results["viewport_results"].append({
                    "viewport": viewport,
                    "viewport_name": viewport_name,
                    "error": str(e)
                })
            finally:
                # Close the page
                await page.close()
        
        # Perform element comparison across viewports if requested
        if compare_elements and selectors and len(results["viewport_results"]) > 1:
            # Extract element data from each viewport
            viewport_elements = {}
            for viewport_result in results["viewport_results"]:
                if "elements_data" in viewport_result and viewport_result["elements_data"]:
                    viewport_elements[viewport_result["viewport_name"]] = viewport_result["elements_data"]
            
            # Compare elements across viewports
            element_comparison = {}
            for selector_index, selector in enumerate(selectors):
                selector_comparison = {
                    "selector": selector,
                    "differences": [],
                    "responsive_issues": []
                }
                
                # Check for differences in element counts
                element_counts = {}
                for viewport_name, elements_data in viewport_elements.items():
                    if selector_index < len(elements_data):
                        element_counts[viewport_name] = elements_data[selector_index]["count"]
                
                if len(set(element_counts.values())) > 1:
                    selector_comparison["differences"].append({
                        "type": "element_count",
                        "description": "Element count varies across viewports",
                        "counts": element_counts
                    })
                
                # Check for visibility changes
                for viewport_name, elements_data in viewport_elements.items():
                    if selector_index < len(elements_data):
                        selector_data = elements_data[selector_index]
                        for element_index, element in enumerate(selector_data["elements"]):
                            # Create a key for this specific element
                            element_key = f"{selector}-{element_index}"
                            
                            # Check if this element is in all viewports
                            all_viewport_visibility = {}
                            for vp_name, vp_elements in viewport_elements.items():
                                if selector_index < len(vp_elements) and element_index < len(vp_elements[selector_index]["elements"]):
                                    all_viewport_visibility[vp_name] = vp_elements[selector_index]["elements"][element_index]["isVisible"]
                            
                            # If visibility changes across viewports, it might be responsive behavior
                            if len(set(all_viewport_visibility.values())) > 1:
                                selector_comparison["responsive_issues"].append({
                                    "element_key": element_key,
                                    "issue": "visibility_change",
                                    "description": "Element visibility changes across viewports",
                                    "visibility": all_viewport_visibility
                                })
                
                element_comparison[selector] = selector_comparison
            
            results["element_comparison"] = element_comparison
        
        # Save results to file
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        
        return results
            
    except Exception as e:
        logger.error(f"Error in responsive testing: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error in responsive testing: {str(e)}"}
        )

@app.websocket("/ws/browser/events")
async def websocket_browser_events(websocket: WebSocket):
    """WebSocket endpoint for browser events"""
    await websocket.accept()
    
    # Generate unique client ID
    client_id = f"client_{int(time.time())}_{id(websocket)}"
    event_connections[client_id] = websocket
    
    try:
        # Send initial connection message
        await websocket.send_json({"type": "connection", "client_id": client_id, "status": "connected"})
        
        # Process incoming messages (subscription requests)
        while True:
            try:
                data = await websocket.receive_json()
                action = data.get("action")
                
                if action == "subscribe":
                    # Create subscription from request
                    subscription_data = data.get("subscription", {})
                    subscription = EventSubscriptionModel(
                        subscription_id=subscription_data.get("subscription_id", f"sub_{int(time.time())}_{id(websocket)}"),
                        client_id=client_id,
                        event_types=subscription_data.get("event_types", []),
                        filters=subscription_data.get("filters")
                    )
                    
                    # Add subscription
                    await add_subscription(subscription)
                    await websocket.send_json({
                        "type": "subscription_response",
                        "status": "subscribed",
                        "subscription_id": subscription.subscription_id,
                        "event_types": subscription.event_types
                    })
                
                elif action == "unsubscribe":
                    # Remove subscription
                    subscription_id = data.get("subscription_id")
                    if subscription_id:
                        success = await remove_subscription(subscription_id)
                        await websocket.send_json({
                            "type": "subscription_response",
                            "status": "unsubscribed" if success else "not_found",
                            "subscription_id": subscription_id
                        })
                
                elif action == "list_subscriptions":
                    # List all active subscriptions for this client
                    client_subscriptions = [
                        sub.dict() for sub_id, sub in active_subscriptions.items()
                        if sub.client_id == client_id
                    ]
                    await websocket.send_json({
                        "type": "subscription_list",
                        "subscriptions": client_subscriptions
                    })
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown action: {action}"
                    })
            
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON message"
                })
    
    except WebSocketDisconnect:
        # Clean up client subscriptions on disconnect
        client_subscriptions = [
            sub_id for sub_id, sub in active_subscriptions.items()
            if sub.client_id == client_id
        ]
        for sub_id in client_subscriptions:
            await remove_subscription(sub_id)
        
        if client_id in event_connections:
            del event_connections[client_id]
    
    except Exception as e:
        logger.error(f"WebSocket error in browser events: {e}")
        if client_id in event_connections:
            del event_connections[client_id]

# API endpoints for subscription management
@app.post("/api/browser/events/subscribe")
async def subscribe_to_events(subscription: EventSubscriptionModel):
    """Subscribe to browser events"""
    if not browser or not browser_context:
        raise HTTPException(status_code=500, detail="Browser not initialized")
    
    try:
        subscription_id = await add_subscription(subscription)
        return {
            "success": True,
            "subscription_id": subscription_id,
            "message": f"Subscribed to events: {', '.join(subscription.event_types)}"
        }
    except Exception as e:
        logger.error(f"Error subscribing to events: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/browser/events/subscriptions")
async def list_subscriptions(client_id: str):
    """List active event subscriptions for a client"""
    if not browser or not browser_context:
        raise HTTPException(status_code=500, detail="Browser not initialized")
    
    try:
        # Find all subscriptions for this client
        client_subscriptions = [
            sub.dict() for sub_id, sub in active_subscriptions.items()
            if sub.client_id == client_id
        ]
        return {
            "success": True,
            "client_id": client_id,
            "subscriptions": client_subscriptions,
            "count": len(client_subscriptions)
        }
    except Exception as e:
        logger.error(f"Error listing subscriptions: {e}")
        return {"success": False, "error": str(e)}

@app.delete("/api/browser/events/unsubscribe")
async def unsubscribe_from_events(subscription_id: str):
    """Unsubscribe from browser events"""
    if not browser or not browser_context:
        raise HTTPException(status_code=500, detail="Browser not initialized")
    
    try:
        success = await remove_subscription(subscription_id)
        if success:
            return {
                "success": True,
                "subscription_id": subscription_id,
                "message": "Unsubscribed successfully"
            }
        else:
            return {
                "success": False,
                "subscription_id": subscription_id,
                "error": "Subscription not found"
            }
    except Exception as e:
        logger.error(f"Error unsubscribing from events: {e}")
        return {"success": False, "error": str(e)}

async def shutdown_gracefully():
    """Shutdown the application gracefully"""
    logger.info("Received shutdown signal. Shutting down...")
    await asyncio.sleep(0.5)  # Give FastAPI a moment to complete current requests
    sys.exit(0)

def handle_signal(sig, frame):
    """Handle process signals"""
    logger.info(f"Received signal {sig}")
    asyncio.create_task(shutdown_gracefully())

# Browser event handling functions
async def handle_new_page(page):
    """Set up event listeners for a new page"""
    logger.info(f"New page created: {page}")
    
    # Assign a unique ID to the page for event tracking
    page_id = f"page_{int(time.time())}_{id(page)}"
    
    # Set up page event listeners
    await setup_page_event_listeners(page, page_id)
    
    # Emit page creation event
    await emit_page_event(page_id, EventName.PAGE_LIFECYCLE, {
        "url": page.url,
        "lifecycle": "created",
        "timestamp": time.time()
    })

async def setup_page_event_listeners(page, page_id):
    """Set up all event listeners for a page"""
    # Page lifecycle events
    page.on("load", lambda: asyncio.create_task(
        emit_page_event(page_id, EventName.PAGE_LIFECYCLE, {
            "url": page.url,
            "lifecycle": "load",
            "timestamp": time.time()
        })
    ))
    
    page.on("domcontentloaded", lambda: asyncio.create_task(
        emit_page_event(page_id, EventName.PAGE_LIFECYCLE, {
            "url": page.url,
            "lifecycle": "domcontentloaded",
            "timestamp": time.time()
        })
    ))
    
    # Console events
    page.on("console", lambda msg: asyncio.create_task(
        emit_console_event(page_id, msg)
    ))
    
    # Page error events
    page.on("pageerror", lambda err: asyncio.create_task(
        emit_page_event(page_id, EventName.PAGE_ERROR, {
            "url": page.url,
            "error": str(err),
            "timestamp": time.time()
        })
    ))
    
    # Network events
    page.on("request", lambda request: asyncio.create_task(
        emit_network_event(page_id, EventName.NETWORK_REQUEST, request)
    ))
    
    page.on("response", lambda response: asyncio.create_task(
        emit_network_event(page_id, EventName.NETWORK_RESPONSE, response)
    ))
    
    page.on("requestfailed", lambda request: asyncio.create_task(
        emit_network_event(page_id, EventName.NETWORK_ERROR, request)
    ))
    
    # Set up DOM mutation observer
    await page.evaluate("""() => {
        window.__mcp_dom_observer = new MutationObserver((mutations) => {
            const events = [];
            
            for (const mutation of mutations) {
                if (mutation.type === 'childList') {
                    events.push({
                        type: 'dom.child',
                        target: mutation.target.tagName,
                        addedNodes: mutation.addedNodes.length,
                        removedNodes: mutation.removedNodes.length
                    });
                } else if (mutation.type === 'attributes') {
                    events.push({
                        type: 'dom.attribute',
                        target: mutation.target.tagName,
                        attributeName: mutation.attributeName,
                        oldValue: mutation.oldValue
                    });
                } else if (mutation.type === 'characterData') {
                    events.push({
                        type: 'dom.mutation',
                        target: mutation.target.parentNode ? mutation.target.parentNode.tagName : 'TEXT',
                        oldValue: mutation.oldValue
                    });
                }
            }
            
            if (events.length > 0) {
                window.__mcp_dom_events = window.__mcp_dom_events || [];
                window.__mcp_dom_events.push(...events);
            }
        });
        
        window.__mcp_dom_observer.observe(document.documentElement, {
            childList: true,
            attributes: true,
            characterData: true,
            subtree: true,
            attributeOldValue: true,
            characterDataOldValue: true
        });
        
        window.__mcp_dom_events = [];
    }""")
    
    # Set up interval to poll for DOM events
    asyncio.create_task(poll_dom_events(page, page_id))

async def poll_dom_events(page, page_id):
    """Poll for accumulated DOM events"""
    try:
        while True:
            # Only poll while the page is still active
            if page.is_closed():
                break
                
            # Get accumulated DOM events
            dom_events = await page.evaluate("""() => {
                const events = window.__mcp_dom_events || [];
                window.__mcp_dom_events = [];
                return events;
            }""")
            
            # Emit each DOM event
            for event in dom_events:
                event_type = event.get("type", "dom.mutation")
                await emit_dom_event(page_id, event_type, event)
                
            # Wait before polling again
            await asyncio.sleep(0.5)  # Poll every 500ms
    except Exception as e:
        logger.error(f"Error polling DOM events: {e}")

# Event emission functions
async def emit_page_event(page_id, event_name, data):
    """Emit a page-related event"""
    event = BrowserEvent(
        type=EventType.PAGE,
        event=event_name,
        page_id=page_id,
        data=data
    )
    await broadcast_event(event)

async def emit_console_event(page_id, console_msg):
    """Emit a console event"""
    event_type = EventName.CONSOLE_LOG
    
    # Map console message type to event type
    if console_msg.type == "error":
        event_type = EventName.CONSOLE_ERROR
    elif console_msg.type == "warning":
        event_type = EventName.CONSOLE_WARNING
    
    event = BrowserEvent(
        type=EventType.CONSOLE,
        event=event_type,
        page_id=page_id,
        data={
            "type": console_msg.type,
            "text": console_msg.text,
            "location": {
                "url": console_msg.location.get("url", ""),
                "lineNumber": console_msg.location.get("lineNumber", 0),
                "columnNumber": console_msg.location.get("columnNumber", 0)
            } if hasattr(console_msg, "location") else {}
        }
    )
    await broadcast_event(event)

async def emit_network_event(page_id, event_name, request_or_response):
    """Emit a network event"""
    data = {}
    
    # Handle both request and response objects
    if event_name == EventName.NETWORK_REQUEST:
        data = {
            "url": request_or_response.url,
            "method": request_or_response.method,
            "headers": request_or_response.headers,
            "resourceType": request_or_response.resource_type
        }
    elif event_name == EventName.NETWORK_RESPONSE:
        data = {
            "url": request_or_response.url,
            "status": request_or_response.status,
            "statusText": request_or_response.status_text,
            "headers": request_or_response.headers
        }
    elif event_name == EventName.NETWORK_ERROR:
        data = {
            "url": request_or_response.url,
            "method": request_or_response.method,
            "resourceType": request_or_response.resource_type,
            "error": str(request_or_response.failure())
        }
    
    event = BrowserEvent(
        type=EventType.NETWORK,
        event=event_name,
        page_id=page_id,
        data=data
    )
    await broadcast_event(event)

async def emit_dom_event(page_id, event_name, data):
    """Emit a DOM event"""
    event = BrowserEvent(
        type=EventType.DOM,
        event=event_name,
        page_id=page_id,
        data=data
    )
    await broadcast_event(event)

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Start the server
    logger.info(f"Starting MCP Browser server on port {SERVER_PORT}...")
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT) 