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
import psutil
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
    
    # Initialize browser pool with small limits for testing
    await initialize_browser_pool(max_browsers=2)
    
    try:
        # Get a browser instance
        browser = await browser_pool.get_browser()
        assert browser is not None, "Failed to get browser instance"
        assert browser.browser is not None, "Browser not initialized"
        assert browser.process is not None, "Browser process not tracked"
        logger.info(f"Got browser instance: {browser.id}")
        
        # Check resource monitoring
        metrics = browser_pool._get_browser_metrics(browser)
        assert "memory_percent" in metrics, "Memory metrics not available"
        assert "cpu_percent" in metrics, "CPU metrics not available"
        logger.info(f"Browser metrics: Memory={metrics['memory_percent']:.1f}%, CPU={metrics['cpu_percent']:.1f}%")
        
        # Create multiple contexts to test resource limits
        contexts = []
        for i in range(3):
            try:
                context = await browser.create_context(f"test-context-{i}")
                contexts.append(context)
                logger.info(f"Created context {i}")
            except MCPBrowserException as e:
                if e.error_code == ErrorCode.RESOURCE_LIMIT_EXCEEDED:
                    logger.info("Resource limit correctly enforced")
                    break
                raise
        
        # Clean up contexts
        for i, context in enumerate(contexts):
            await browser.close_context(f"test-context-{i}")
            logger.info(f"Closed context {i}")
        
        # Get another browser (should reuse the instance due to max_browsers=2)
        browser2 = await browser_pool.get_browser()
        assert browser2 is not None, "Failed to get second browser instance"
        assert len(browser_pool.browsers) <= 2, "Browser pool limit exceeded"
        logger.info(f"Got second browser instance: {browser2.id}")
        
        # Test cleanup of idle browsers
        await asyncio.sleep(2)
        await browser_pool._cleanup_idle_browsers()
        assert len(browser_pool.browsers) < 2, "Idle browsers not cleaned up"
        logger.info("Idle browser cleanup successful")
        
    finally:
        # Clean up
        await close_browser_pool()
        logger.info("Browser pool test passed")

async def test_resource_limits():
    """Test resource limit enforcement"""
    logger.info("Testing resource limits...")
    
    # Initialize browser pool with strict limits
    await initialize_browser_pool(max_browsers=1)
    browser_pool.max_memory_percent = 20.0  # Set low memory limit for testing
    
    try:
        # Get initial browser
        browser = await browser_pool.get_browser()
        assert browser is not None, "Failed to get browser instance"
        logger.info(f"Got initial browser: {browser.id}")
        
        # Try to exceed memory limit
        try:
            # Create contexts until we hit the limit
            contexts = []
            for i in range(10):  # Try to create more contexts than reasonable
                context = await browser.create_context(f"test-context-{i}")
                contexts.append((i, context))
                logger.info(f"Created context {i}")
                
                # Check memory usage
                metrics = browser_pool._get_browser_metrics(browser)
                logger.info(f"Memory usage: {metrics['memory_percent']:.1f}%")
                
                if metrics['memory_percent'] > browser_pool.max_memory_percent:
                    logger.info("Memory limit reached")
                    break
            
        except MCPBrowserException as e:
            assert e.error_code in [
                ErrorCode.RESOURCE_LIMIT_EXCEEDED,
                ErrorCode.BROWSER_INITIALIZATION_FAILED
            ], f"Unexpected error: {e.error_code}"
            logger.info("Resource limit correctly enforced")
        
        finally:
            # Clean up contexts
            if 'contexts' in locals():
                for i, context in contexts:
                    try:
                        await browser.close_context(f"test-context-{i}")
                    except Exception as e:
                        logger.warning(f"Error closing context {i}: {e}")
    
    finally:
        # Clean up
        await close_browser_pool()
        logger.info("Resource limits test passed")

async def test_error_handling():
    """Test error handling in browser operations"""
    logger.info("Testing error handling...")
    
    # Initialize browser pool
    await initialize_browser_pool(max_browsers=1)
    
    try:
        # Test invalid context operations
        try:
            browser = await browser_pool.get_browser()
            await browser.close_context("nonexistent-context")
        except MCPBrowserException as e:
            assert e.error_code == ErrorCode.RESOURCE_NOT_FOUND, "Wrong error code"
            logger.info("Invalid context handling passed")
        
        # Test resource cleanup on failure
        browser_count = len(browser_pool.browsers)
        try:
            # Force an error by closing browser then trying to use it
            await browser_pool.close_browser(browser.id)
            await browser.create_context("test-context")
        except MCPBrowserException as e:
            assert e.error_code in [
                ErrorCode.BROWSER_INITIALIZATION_FAILED,
                ErrorCode.CONTEXT_CREATION_FAILED
            ], "Wrong error code"
            assert len(browser_pool.browsers) == browser_count - 1, "Resource not cleaned up"
            logger.info("Resource cleanup on failure passed")
        
        # Test retry mechanism
        @with_retry(RetryConfig(max_retries=2, delay=0.1))
        async def failing_operation():
            raise MCPBrowserException(
                error_code=ErrorCode.NETWORK_ERROR,
                message="Simulated network error"
            )
        
        try:
            await failing_operation()
        except MCPBrowserException as e:
            assert e.error_code == ErrorCode.NETWORK_ERROR, "Wrong error code"
            logger.info("Retry mechanism passed")
    
    finally:
        # Clean up
        await close_browser_pool()
        logger.info("Error handling test passed")

async def test_memory_monitoring():
    """Test browser memory monitoring and limits"""
    logger.info("Testing memory monitoring...")
    
    await initialize_browser_pool(max_browsers=1)
    browser_pool.max_memory_percent = 50.0  # Set memory limit to 50%
    
    try:
        browser = await browser_pool.get_browser()
        assert browser is not None, "Failed to get browser instance"
        
        # Create a context and navigate to a memory-intensive page
        context = await browser.create_context("test-memory")
        page = await context.new_page()
        
        # Monitor memory usage
        initial_metrics = browser_pool._get_browser_metrics(browser)
        logger.info(f"Initial memory usage: {initial_metrics['memory_percent']:.1f}%")
        
        # Load a page that will use memory
        await page.goto("https://example.com")
        
        # Check memory metrics after load
        load_metrics = browser_pool._get_browser_metrics(browser)
        logger.info(f"Memory usage after load: {load_metrics['memory_percent']:.1f}%")
        
        assert load_metrics["memory_percent"] > 0, "Memory metrics not working"
        
        # Cleanup should reduce memory usage
        await browser.close_context("test-memory")
        await asyncio.sleep(1)  # Give time for cleanup
        
        final_metrics = browser_pool._get_browser_metrics(browser)
        logger.info(f"Final memory usage: {final_metrics['memory_percent']:.1f}%")
        
        assert final_metrics["memory_percent"] < load_metrics["memory_percent"], \
            "Memory not cleaned up properly"
            
    finally:
        await close_browser_pool()
        logger.info("Memory monitoring test passed")

async def test_process_monitoring():
    """Test browser process monitoring and cleanup"""
    logger.info("Testing process monitoring...")
    
    await initialize_browser_pool(max_browsers=2)
    
    try:
        # Get initial system process count
        initial_process_count = len(psutil.Process().children(recursive=True))
        
        # Create multiple browser instances
        browser1 = await browser_pool.get_browser()
        browser2 = await browser_pool.get_browser()
        
        # Verify processes are tracked
        assert browser1.process is not None, "Browser 1 process not tracked"
        assert browser2.process is not None, "Browser 2 process not tracked"
        
        # Verify process count increased
        current_process_count = len(psutil.Process().children(recursive=True))
        assert current_process_count > initial_process_count, "Browser processes not created"
        
        # Close one browser
        await browser_pool.close_browser(browser1.id)
        
        # Verify process was cleaned up
        after_close_count = len(psutil.Process().children(recursive=True))
        assert after_close_count < current_process_count, "Browser process not cleaned up"
        
        # Verify remaining browser still works
        context = await browser2.create_context("test-process")
        await browser2.close_context("test-process")
        
    finally:
        await close_browser_pool()
        logger.info("Process monitoring test passed")

async def test_cleanup_on_error():
    """Test resource cleanup when errors occur"""
    logger.info("Testing cleanup on error...")
    
    await initialize_browser_pool(max_browsers=1)
    
    try:
        browser = await browser_pool.get_browser()
        
        # Create a context
        context = await browser.create_context("test-error")
        
        try:
            # Simulate an error during page operation
            page = await context.new_page()
            await page.goto("https://nonexistent.example.com")
        except Exception as e:
            logger.info(f"Expected error occurred: {str(e)}")
            
            # Verify context is still tracked
            assert "test-error" in browser.contexts, "Context lost after error"
            
            # Cleanup should still work
            await browser.close_context("test-error")
            assert "test-error" not in browser.contexts, "Context not cleaned up after error"
            
    finally:
        await close_browser_pool()
        logger.info("Cleanup on error test passed")

async def test_integration():
    """Test the integration component"""
    logger.info("Testing integration...")
    
    # Test browser manager with resource monitoring
    await browser_manager.initialize(max_browsers=2)
    
    try:
        # Create multiple sessions to test resource management
        sessions = []
        for i in range(3):
            try:
                session_id = f"test-session-{i}"
                context = await browser_manager.create_browser_context(session_id, f"test-user-{i}")
                sessions.append(session_id)
                logger.info(f"Created browser context for session: {session_id}")
                
                # Verify context tracking
                session_info = await browser_manager.get_browser_context(session_id)
                assert session_info is not None, "Failed to get browser context"
                assert session_info["user_id"] == f"test-user-{i}", "Wrong user ID"
                
            except MCPBrowserException as e:
                if e.error_code == ErrorCode.RESOURCE_LIMIT_EXCEEDED:
                    logger.info("Resource limit correctly enforced")
                    break
                raise
        
        # Clean up sessions
        for session_id in sessions:
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
    
    finally:
        # Clean up
        await browser_manager.shutdown()
        logger.info("Integration test passed")

async def main():
    """Run all tests"""
    try:
        await test_browser_pool()
        await test_resource_limits()
        await test_error_handling()
        await test_memory_monitoring()
        await test_process_monitoring()
        await test_cleanup_on_error()
        await test_integration()
        logger.info("All tests passed successfully!")
        
    except Exception as e:
        logger.error("Test failed:", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 