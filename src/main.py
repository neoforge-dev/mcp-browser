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
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Body, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
import uvicorn
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

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
    """Get the current status of the MCP Browser"""
    browser_status = "disabled (headless mode)" if HEADLESS_MODE else "running" if browser else "initializing"
    return {"status": "ok", "browser": browser_status}

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