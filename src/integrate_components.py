#!/usr/bin/env python3
"""
Integration script for MCP Browser components

This script updates the main.py file to use the BrowserPool, error handling,
and authentication components we've implemented.
"""

import os
import sys
import asyncio
import logging
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp-browser-integration")

async def main():
    """Main integration function"""
    logger.info("Starting MCP Browser component integration")
    
    # Get paths
    script_dir = os.path.dirname(os.path.realpath(__file__))
    main_file = os.path.join(script_dir, "main.py")
    integration_file = os.path.join(script_dir, "integration.py")
    browser_pool_file = os.path.join(script_dir, "browser_pool.py")
    error_handler_file = os.path.join(script_dir, "error_handler.py")
    
    # Verify all files exist
    for file in [main_file, integration_file, browser_pool_file, error_handler_file]:
        if not os.path.exists(file):
            logger.error(f"Required file not found: {file}")
            return 1
    
    # Install component imports in main.py
    logger.info("Installing component imports in main.py")
    await install_imports(main_file)
    
    # Replace existing browser initialization with BrowserPool
    logger.info("Replacing browser initialization with BrowserPool")
    await replace_browser_init(main_file)
    
    # Apply error handling to critical endpoints
    logger.info("Applying error handling to critical endpoints")
    await apply_error_handling(main_file)
    
    # Update auth system to use new components
    logger.info("Updating auth system")
    await update_auth_system(main_file)
    
    # Add token refresh endpoint
    logger.info("Adding token refresh endpoint")
    await add_token_refresh(main_file)
    
    # Add rate limiting
    logger.info("Adding rate limiting")
    await add_rate_limiting(main_file)
    
    logger.info("MCP Browser component integration completed successfully")
    return 0

async def install_imports(main_file: str):
    """
    Install required imports in the main application file
    
    Args:
        main_file: Path to main.py
    """
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Prepare the new imports to add
    new_imports = """
# Component integration imports
from integration import browser_manager, auth_manager, configure_app, handle_exceptions, with_retry, DEFAULT_RETRY_CONFIG
from error_handler import MCPBrowserException, ErrorCode, RetryConfig
"""
    
    # Add imports after the last import statement
    import_section_end = content.rfind("import") + content[content.rfind("import"):].find('\n') + 1
    updated_content = content[:import_section_end] + new_imports + content[import_section_end:]
    
    with open(main_file, 'w') as f:
        f.write(updated_content)
    
    logger.info("Component imports added to main.py")

async def replace_browser_init(main_file: str):
    """
    Replace existing browser initialization with BrowserPool integration and lifespan events
    
    Args:
        main_file: Path to main.py
    """
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Check if file already contains lifespan context manager
    if "asynccontextmanager" in content and "@asynccontextmanager" in content:
        logger.info("File already contains lifespan context manager")
        return
    
    # Add imports for asynccontextmanager if needed
    if "from contextlib import asynccontextmanager" not in content:
        if "from typing import" in content:
            content = content.replace(
                "from typing import", 
                "from typing import AsyncGenerator, "
            )
        else:
            # Add imports near the top after other imports
            import_end = content.find("# Configure logging")
            if import_end == -1:
                import_end = content.find("import ")
                import_end = content.find("\n", import_end) + 1
            
            content = (
                content[:import_end] + 
                "from contextlib import asynccontextmanager\n" + 
                "from typing import AsyncGenerator\n" + 
                content[import_end:]
            )
    
    # Look for app initialization
    app_init_start = content.find("app = FastAPI(")
    if app_init_start == -1:
        logger.error("Could not find FastAPI app initialization")
        return
    
    app_init_end = content.find(")", app_init_start)
    if app_init_end == -1:
        logger.error("Could not determine end of FastAPI app initialization")
        return
    
    # Create lifespan function
    lifespan_code = """
# Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    \"\"\"Lifespan context manager for startup and shutdown events\"\"\"
    global app_state
    app_state = {}
    
    # Configure the app with integration components
    configure_app(app)
    
    # Initialize MCP client for tool registration
    if os.environ.get("MCP_SERVER_URL") and os.environ.get("MCP_API_KEY"):
        app_state["mcp_client"] = MCPClient(
            model_name=os.environ.get("MCP_MODEL_NAME", "mcp-browser"),
            server_url=os.environ.get("MCP_SERVER_URL"),
            api_key=os.environ.get("MCP_API_KEY")
        )
        
        try:
            await app_state["mcp_client"].register_tools()
            logger.info("MCP tools registered successfully")
        except Exception as e:
            logger.error(f"Failed to register MCP tools: {str(e)}")
    else:
        logger.warning("MCP_SERVER_URL or MCP_API_KEY not set, skipping MCP tool registration")
    
    # Initialize event subscriptions
    app_state["subscriptions"] = {}
    
    logger.info("MCP Browser server started")
    
    yield  # Run the application
    
    # Cleanup on shutdown
    
    # Close MCP client
    if app_state.get("mcp_client"):
        await app_state["mcp_client"].close()
        
    # Clear subscriptions
    app_state["subscriptions"] = {}
    
    logger.info("MCP Browser server shut down")

"""
    
    # Find a good insertion point for the lifespan function
    # Look for # App state or some other clear marker before app initialization
    app_state_pos = content.find("# App state")
    if app_state_pos == -1:
        # Insert after imports but before app initialization
        app_state_pos = content.find("# Configure logging")
        if app_state_pos == -1:
            app_state_pos = app_init_start
        else:
            # Find the next section after logging config
            next_section = content.find("#", app_state_pos + 15)
            if next_section != -1 and next_section < app_init_start:
                app_state_pos = next_section
            else:
                app_state_pos = app_init_start
    
    # Insert lifespan code before app initialization
    content = content[:app_state_pos] + lifespan_code + content[app_state_pos:]
    
    # Update app initialization to use lifespan
    app_init_content = content[app_init_start:app_init_end+1]
    if "lifespan=lifespan" not in app_init_content:
        # Check if there's a comma at the end of the last parameter
        if app_init_content.rstrip().endswith(","):
            new_app_init = app_init_content.rstrip() + "\n    lifespan=lifespan\n)"
        else:
            new_app_init = app_init_content.rstrip()[:-1] + ",\n    lifespan=lifespan\n)"
        
        # Replace app initialization
        content = content[:app_init_start] + new_app_init + content[app_init_end+1:]
    
    # Remove old @app.on_event handlers that we've replaced with lifespan
    startup_event_pos = content.find('@app.on_event("startup")')
    if startup_event_pos != -1:
        # Find the end of the startup_event function
        function_start = content.find("async def startup_event", startup_event_pos)
        if function_start != -1:
            # Find the end of the function by looking for the next function or class
            next_func = content.find("@app", function_start + 30)
            if next_func == -1:
                next_func = content.find("def ", function_start + 30)
            if next_func == -1:
                next_func = content.find("class ", function_start + 30)
            
            if next_func != -1:
                # Remove the startup event handler
                content = content[:startup_event_pos] + content[next_func:]
    
    shutdown_event_pos = content.find('@app.on_event("shutdown")')
    if shutdown_event_pos != -1:
        # Find the end of the shutdown_event function
        function_start = content.find("async def shutdown_event", shutdown_event_pos)
        if function_start != -1:
            # Find the end of the function by looking for the next function or class
            next_func = content.find("@app", function_start + 30)
            if next_func == -1:
                next_func = content.find("def ", function_start + 30)
            if next_func == -1:
                next_func = content.find("class ", function_start + 30)
            
            if next_func != -1:
                # Remove the shutdown event handler
                content = content[:shutdown_event_pos] + content[next_func:]
    
    # Write updated content back to file
    with open(main_file, 'w') as f:
        f.write(content)
    
    logger.info("Updated main.py with lifespan event handlers and browser integration")

async def apply_error_handling(main_file: str):
    """
    Apply error handling to critical endpoints
    
    Args:
        main_file: Path to main.py
    """
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Identify critical browser endpoints to apply error handling
    endpoints = [
        "@app.post(\"/api/browser/navigate\")",
        "@app.post(\"/api/browser/back\")",
        "@app.post(\"/api/browser/forward\")",
        "@app.post(\"/api/browser/refresh\")",
        "@app.post(\"/api/browser/click\")",
        "@app.post(\"/api/browser/type\")",
        "@app.post(\"/api/browser/select\")",
        "@app.post(\"/api/browser/fill_form\")",
        "@app.post(\"/api/browser/screenshot\")",
        "@app.post(\"/api/browser/extract_text\")",
        "@app.post(\"/api/browser/check_visibility\")",
        "@app.post(\"/api/browser/wait_for_selector\")",
        "@app.post(\"/api/browser/evaluate\")",
        "@app.post(\"/api/screenshots/capture\")",
        "@app.post(\"/api/dom/extract\")",
        "@app.post(\"/api/css/analyze\")",
        "@app.post(\"/api/accessibility/test\")",
        "@app.post(\"/api/responsive/test\")"
    ]
    
    updated_content = content
    
    # Add the handle_exceptions decorator to each endpoint
    for endpoint in endpoints:
        endpoint_pos = updated_content.find(endpoint)
        if endpoint_pos == -1:
            logger.warning(f"Could not find endpoint: {endpoint}")
            continue
        
        # Check if handle_exceptions is already applied
        prev_lines = updated_content[max(0, endpoint_pos - 100):endpoint_pos].splitlines()
        if any("@handle_exceptions" in line for line in prev_lines[-3:]):
            logger.info(f"handle_exceptions already applied to {endpoint}")
            continue
        
        # Add the decorator
        updated_content = updated_content[:endpoint_pos] + "@handle_exceptions\n" + updated_content[endpoint_pos:]
    
    with open(main_file, 'w') as f:
        f.write(updated_content)
    
    logger.info("Error handling applied to critical endpoints")

async def update_auth_system(main_file: str):
    """
    Update authentication system to use the integrated auth manager
    
    Args:
        main_file: Path to main.py
    """
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Find existing auth function implementations that need to be updated
    functions_to_update = [
        "def create_access_token",
        "async def get_current_user",
        "async def get_current_active_user",
        "def has_permission",
        "async def get_token_from_query",
        "async def verify_websocket_token"
    ]
    
    updated_content = content
    
    # Comment out each function and replace with a reference to auth_manager
    for func in functions_to_update:
        func_pos = updated_content.find(func)
        if func_pos == -1:
            logger.warning(f"Could not find function: {func}")
            continue
        
        # Find function start
        function_start = updated_content.rfind("\n", 0, func_pos) + 1
        
        # Find function end (next function def or class def)
        next_func = updated_content.find("def ", func_pos + len(func))
        next_class = updated_content.find("class ", func_pos + len(func))
        if next_func == -1 and next_class == -1:
            function_end = len(updated_content)
        elif next_func == -1:
            function_end = next_class
        elif next_class == -1:
            function_end = next_func
        else:
            function_end = min(next_func, next_class)
        
        # Find the indentation before the function
        func_lines = updated_content[function_start:function_end].splitlines()
        
        # Comment out the entire function
        commented_function = "# Auth system now managed by auth_manager\n"
        commented_function += "# " + "\n# ".join(func_lines)
        
        # Replace the function with commented version
        updated_content = updated_content[:function_start] + commented_function + updated_content[function_end:]
    
    with open(main_file, 'w') as f:
        f.write(updated_content)
    
    logger.info("Auth system updated to use auth_manager")

async def add_token_refresh(main_file: str):
    """
    Add token refresh endpoint
    
    Args:
        main_file: Path to main.py
    """
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Find a good place to add the token refresh endpoint (after the login endpoint)
    login_endpoint = content.find("@app.post(\"/token\"")
    if login_endpoint == -1:
        logger.warning("Could not find login endpoint to add token refresh")
        return
    
    # Find the end of the login endpoint function
    login_function_end = content.find("@app", login_endpoint + 1)
    if login_function_end == -1:
        logger.warning("Could not determine end of login function")
        return
    
    # New refresh token endpoint code
    refresh_endpoint = """

@app.post("/token/refresh", response_model=Token)
@handle_exceptions
async def refresh_access_token(refresh_token: str = Body(...)):
    """
    Refresh an access token using a refresh token
    
    Args:
        refresh_token: Valid refresh token
        
    Returns:
        New access token
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        # Verify the refresh token
        payload = await auth_manager.decode_token(refresh_token)
        
        # Check if it's actually a refresh token
        if not payload.get("refresh"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not a refresh token"
            )
            
        # Check username
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
            
        # Get permissions from the refresh token
        permissions = payload.get("permissions", [])
        
        # Create a new access token
        access_token = await auth_manager.create_access_token(
            data={"sub": username, "permissions": permissions}
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    except (JWTError, MCPBrowserException) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )
"""
    
    # Add the refresh endpoint after the login endpoint
    updated_content = content[:login_function_end] + refresh_endpoint + content[login_function_end:]
    
    with open(main_file, 'w') as f:
        f.write(updated_content)
    
    logger.info("Token refresh endpoint added")

async def add_rate_limiting(main_file: str):
    """
    Add rate limiting to sensitive endpoints
    
    Args:
        main_file: Path to main.py
    """
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Add rate limiting imports and middleware
    imports_end = content.find("# Component integration imports") + content[content.find("# Component integration imports"):].find('\n') + 1
    
    rate_limit_imports = """
# Rate limiting
from fastapi import Depends, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
"""
    
    updated_content = content[:imports_end] + rate_limit_imports + content[imports_end:]
    
    # Add limiter initialization before the app creation
    app_creation = updated_content.find("app = FastAPI(")
    if app_creation == -1:
        logger.warning("Could not find FastAPI app creation")
        return
    
    limiter_init = """
# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
"""
    
    updated_content = updated_content[:app_creation] + limiter_init + updated_content[app_creation:]
    
    # Add middleware configuration after app creation
    app_created_end = updated_content.find("app = FastAPI(") + updated_content[updated_content.find("app = FastAPI("):].find(')') + 1
    
    middleware_config = """

# Add rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=os.environ.get("ALLOWED_HOSTS", "*").split(",")
)
"""
    
    updated_content = updated_content[:app_created_end] + middleware_config + updated_content[app_created_end:]
    
    # Add rate limiting to sensitive endpoints
    sensitive_endpoints = [
        "@app.post(\"/token\"",
        "@app.post(\"/token/refresh\"",
    ]
    
    for endpoint in sensitive_endpoints:
        endpoint_pos = updated_content.find(endpoint)
        if endpoint_pos == -1:
            logger.warning(f"Could not find endpoint: {endpoint}")
            continue
        
        # Check if rate limiting is already applied
        prev_lines = updated_content[max(0, endpoint_pos - 100):endpoint_pos].splitlines()
        if any("@limiter.limit" in line for line in prev_lines[-3:]):
            logger.info(f"Rate limiting already applied to {endpoint}")
            continue
        
        # Add the rate limiter
        updated_content = updated_content[:endpoint_pos] + '@limiter.limit("5/minute")\n' + updated_content[endpoint_pos:]
    
    with open(main_file, 'w') as f:
        f.write(updated_content)
    
    logger.info("Rate limiting added to sensitive endpoints")

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Integration cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Integration failed: {str(e)}", exc_info=True)
        sys.exit(1) 