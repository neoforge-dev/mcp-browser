#!/usr/bin/env python3
import pytest
import pytest_asyncio
import asyncio
import logging
from src.browser_pool import BrowserPool, BrowserInstance
from src.error_handler import MCPBrowserException, ErrorCode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test-resource-management")

# Removed the local browser_pool fixture definition
# It will now use the session-scoped fixture from conftest.py

@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_resource_limits_enforcement(browser_pool):
    """Test that the browser pool enforces resource limits."""
    logger.info("Starting resource limits test")
    
    # Get initial browser
    browser = await browser_pool.get_browser()
    assert browser is not None
    
    try:
        # Verify memory limit enforcement
        browser_pool.max_memory_percent = 1.0  # Set unrealistically low
        await asyncio.sleep(2)  # Allow monitor to check
        
        # Should trigger cleanup
        assert len(browser_pool.browsers) == 0, "Browser should be closed due to memory limit"
        
    finally:
        # Reset limits
        browser_pool.max_memory_percent = 80.0
        if browser in browser_pool.browsers.values():
            await browser_pool.close_browser(browser)

@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_idle_browser_cleanup(browser_pool):
    """Test that idle browsers are cleaned up."""
    logger.info("Starting idle cleanup test")
    
    # Create a browser and context
    browser = await browser_pool.get_browser()
    context = await browser_pool.create_context("idle-test-ctx")
    
    try:
        # Close context and wait for idle timeout
        await browser_pool.close_context(context)
        await asyncio.sleep(2)  # Wait longer than idle_timeout
        
        # Verify browser was cleaned up
        assert len(browser_pool.browsers) == 0, "Idle browser should be cleaned up"
        
    except Exception as e:
        logger.error(f"Error in idle cleanup test: {e}", exc_info=True)
        raise
    finally:
        if browser in browser_pool.browsers.values():
            await browser_pool.close_browser(browser)

@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_shared_pool_max_browser_limit(browser_pool):
    """Test that the shared browser pool enforces its max_browsers limit."""
    logger.info("Starting max browser limit test")
    
    # Get the pool's max_browsers limit
    max_browsers = browser_pool.max_browsers
    logger.info(f"Pool max_browsers limit: {max_browsers}")
    
    browsers = []
    try:
        # Create browsers up to the limit
        for i in range(max_browsers):
            logger.info(f"Creating browser {i+1}/{max_browsers}")
            browser = await browser_pool.get_browser()
            assert browser is not None, f"Failed to create browser {i+1}"
            browsers.append(browser)
            logger.info(f"Successfully created browser {i+1}")
        
        # Try to create one more browser (should fail)
        logger.info("Attempting to create browser beyond limit")
        with pytest.raises(MCPBrowserException) as exc_info:
            await browser_pool.get_browser()
        
        assert exc_info.value.error_code == ErrorCode.MAX_BROWSERS_REACHED, \
               f"Expected MAX_BROWSERS_REACHED error, got {exc_info.value.error_code}"
        logger.info("Successfully caught MAX_BROWSERS_REACHED error")
        
    finally:
        # Clean up browsers
        logger.info("Cleaning up browsers")
        for browser in browsers:
            try:
                if browser in browser_pool.browsers.values():
                    await browser_pool.close_browser(browser)
            except Exception as e:
                logger.error(f"Error closing browser: {e}", exc_info=True)
        
        logger.info("Max browser limit test completed")

@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_resource_monitoring(browser_pool):
    """Test that the browser pool monitors resource usage."""
    logger.info("Starting resource monitoring test")
    
    # Create a browser
    browser = await browser_pool.get_browser()
    assert browser is not None
    
    try:
        # Wait for monitoring cycle
        await asyncio.sleep(1)
        
        # Verify monitoring is active
        assert browser_pool.monitor_task is not None
        assert not browser_pool.monitor_task.done()
        
        # Verify resource tracking
        browser_info = browser_pool.browsers.get(browser.id)
        assert browser_info is not None
        assert hasattr(browser_info, 'last_used')
        assert hasattr(browser_info, 'memory_percent')
        assert hasattr(browser_info, 'cpu_percent')
        
    finally:
        if browser in browser_pool.browsers.values():
            await browser_pool.close_browser(browser)
        logger.info("Resource monitoring test completed") 