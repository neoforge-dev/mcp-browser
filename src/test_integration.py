#!/usr/bin/env python3
"""
Integration Test for MCP Browser Components

This script tests that all components work together properly.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("integration-test")

# Import our components
from browser_pool import browser_pool, initialize_browser_pool, close_browser_pool
from error_handler import (
    MCPBrowserException, ErrorCode, RetryConfig, with_retry, handle_exceptions, DEFAULT_RETRY_CONFIG
)
from integration import browser_manager, auth_manager

async def test_browser_pool():
    """Test the browser pool component"""
    logger.info("Testing browser pool...")
    
    # Initialize browser pool
    await initialize_browser_pool(max_browsers=2)
    
    # Get a browser instance
    browser = await browser_pool.get_browser()
    assert browser is not None, "Failed to get browser instance"
    logger.info(f"Got browser instance: {browser.id}")
    
    # Create a context
    context_id = "test-context"
    context = await browser.create_context(context_id)
    assert context is not None, "Failed to create browser context"
    logger.info(f"Created browser context: {context_id}")
    
    # Close the context
    await browser.close_context(context_id)
    logger.info(f"Closed browser context: {context_id}")
    
    # Get another browser (should reuse the instance)
    browser2 = await browser_pool.get_browser()
    assert browser2 is not None, "Failed to get second browser instance"
    logger.info(f"Got second browser instance: {browser2.id}")
    
    # Close browser pool
    await close_browser_pool()
    logger.info("Browser pool test passed")
    
async def test_error_handler():
    """Test the error handler component"""
    logger.info("Testing error handler...")
    
    # Test creating an exception
    try:
        raise MCPBrowserException(
            error_code=ErrorCode.BROWSER_ELEMENT_NOT_FOUND,
            message="Test error message",
            details=[{"field": "selector", "message": "Element not found", "code": "404"}]
        )
    except MCPBrowserException as e:
        # Convert to response
        response = e.to_response()
        assert response.error_code == ErrorCode.BROWSER_ELEMENT_NOT_FOUND.value, "Wrong error code"
        assert response.message == "Test error message", "Wrong error message"
        logger.info(f"Exception properly created: {response.error_code} - {response.message}")
    
    # Test retry mechanism
    retry_count = 0
    
    async def failing_func():
        nonlocal retry_count
        retry_count += 1
        if retry_count < 3:
            raise MCPBrowserException(
                error_code=ErrorCode.BROWSER_TIMEOUT,
                message=f"Timeout error (attempt {retry_count})"
            )
        return "Success"
    
    result = await with_retry(
        failing_func,
        retry_config=RetryConfig(max_retries=3, initial_delay=0.1, max_delay=0.5)
    )
    
    assert result == "Success", "Retry mechanism failed"
    assert retry_count == 3, f"Wrong retry count: {retry_count}"
    logger.info(f"Retry mechanism worked properly after {retry_count} attempts")
    
    # Test decorator
    @handle_exceptions
    async def test_decorator():
        raise MCPBrowserException(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Validation error"
        )
    
    try:
        await test_decorator()
        assert False, "Decorator did not raise exception"
    except Exception as e:
        assert hasattr(e, "status_code"), "Exception not converted to HTTP exception"
        logger.info("Exception decorator works properly")
    
    logger.info("Error handler test passed")

async def test_integration():
    """Test the integration component"""
    logger.info("Testing integration...")
    
    # Test browser manager
    await browser_manager.initialize(max_browsers=2)
    
    # Create a session
    session_id = "test-session"
    context = await browser_manager.create_browser_context(session_id, "test-user")
    assert context is not None, "Failed to create browser context"
    logger.info(f"Created browser context for session: {session_id}")
    
    # Get the context
    session_info = await browser_manager.get_browser_context(session_id)
    assert session_info is not None, "Failed to get browser context"
    assert session_info["user_id"] == "test-user", "Wrong user ID"
    logger.info(f"Got browser context for session: {session_id}")
    
    # Close the context
    await browser_manager.close_browser_context(session_id)
    logger.info(f"Closed browser context for session: {session_id}")
    
    # Test auth manager
    username = "admin"
    user = await auth_manager.get_user(username)
    assert user is not None, "Failed to get user"
    assert user.username == username, "Wrong username"
    logger.info(f"Got user: {user.username}")
    
    # Test token creation and decoding
    token_data = {"sub": username, "permissions": user.permissions}
    access_token = await auth_manager.create_access_token(token_data)
    assert access_token is not None, "Failed to create access token"
    logger.info(f"Created access token")
    
    # Decode token
    payload = await auth_manager.decode_token(access_token)
    assert payload["sub"] == username, "Wrong username in token"
    logger.info(f"Decoded token: {payload['sub']}")
    
    # Test permission check
    has_permission = auth_manager.has_permission(user, "browser:full")
    assert has_permission, "User should have permission"
    logger.info(f"User has permission: browser:full")
    
    # Clean up
    await browser_manager.shutdown()
    logger.info("Integration test passed")

async def main():
    """Run all tests"""
    try:
        logger.info("Starting integration tests...")
        
        # Run tests
        await test_browser_pool()
        await test_error_handler()
        await test_integration()
        
        logger.info("All tests passed!")
        return 0
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 