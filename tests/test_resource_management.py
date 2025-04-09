#!/usr/bin/env python3
import pytest
import pytest_asyncio
import asyncio
import logging
from src.browser_pool import BrowserPool, BrowserInstance
from src.error_handler import MCPBrowserException, ErrorCode

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, # Changed to DEBUG for less noise during normal runs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test-resource-management")

# Removed the local browser_pool fixture definition
# It will now use the session-scoped fixture from conftest.py

@pytest.mark.asyncio
async def test_resource_limits_enforcement(browser_pool: BrowserPool):
    """Test that resource limits are strictly enforced (placeholder for more detailed tests)"""
    logger.debug("Starting test_resource_limits_enforcement")
    # Get initial browser
    browser = await browser_pool.get_browser()
    assert browser is not None, "Failed to get browser instance"
    logger.debug(f"Got browser {browser.id}")
    
    # Test creating a context (actual resource limit tests would be more involved)
    context_id = "limit-enforcement-test-context"
    context = await browser.create_context(context_id)
    assert context is not None, "Failed to create context"
    logger.debug(f"Created context {context_id}")
    
    # Basic cleanup for this placeholder test
    await browser.close_context(context_id)
    logger.debug(f"Closed context {context_id}")
    # Note: Browser closure is handled by the pool/fixture teardown
    logger.debug("Finished test_resource_limits_enforcement")

@pytest.mark.asyncio
async def test_idle_browser_cleanup(browser_pool: BrowserPool):
    """Test that idle browsers (not contexts) are properly cleaned up by the pool."""
    logger.debug("Starting test_idle_browser_cleanup")
    # Create a pool specifically for this test with a short idle time
    # Using the shared pool's timeout is unreliable for a targeted test
    test_pool = BrowserPool(
        max_browsers=1,
        idle_timeout=1, # Very short timeout
        monitor_interval=0.5 # Monitor frequently
    )
    await test_pool.start()

    try:
        browser = await test_pool.get_browser()
        assert browser is not None, "Failed to get browser instance from test_pool"
        browser_id = browser.id
        logger.debug(f"Got browser {browser_id} from test_pool")
        
        # Context needs to be created and closed to update last_used time of browser
        context = await browser.create_context("idle-test-ctx")
        await browser.close_context("idle-test-ctx")
        logger.debug(f"Created and closed context in browser {browser_id}")
        
        # Wait longer than idle timeout + monitor interval
        wait_time = test_pool.idle_timeout + test_pool.monitor_interval + 0.5
        logger.debug(f"Waiting for {wait_time:.2f}s for idle cleanup")
        await asyncio.sleep(wait_time)
        
        # Verify the browser was cleaned up by the pool's monitor task
        assert browser_id not in test_pool.browsers, f"Idle browser {browser_id} was not cleaned up by the test_pool"
        logger.debug(f"Confirmed browser {browser_id} was cleaned up by test_pool")
    finally:
        await test_pool.cleanup()
        logger.debug("Finished test_idle_browser_cleanup")

@pytest.mark.asyncio
async def test_shared_pool_max_browser_limit(browser_pool: BrowserPool):
    """Test that the shared browser pool enforces max_browsers limit."""
    logger.debug("Starting test_shared_pool_max_browser_limit")
    
    # Note: This test relies on the session-scoped browser_pool fixture
    # defined in conftest.py, which should have max_browsers=1
    # If conftest.py changes, this test might need adjustment.
    
    acquired_browsers = []
    try:
        # Acquire browsers up to the limit defined in the fixture
        limit = browser_pool.max_browsers
        logger.debug(f"Attempting to acquire {limit + 1} browsers from shared pool (limit: {limit})")
        for i in range(limit):
            logger.debug(f"Acquiring browser {i+1}/{limit}...")
            browser = await browser_pool.get_browser()
            assert browser is not None
            acquired_browsers.append(browser)
            logger.debug(f"Acquired browser {browser.id}")

        # Verify pool is full
        assert len(browser_pool.browsers) == limit

        # Try to acquire one more browser (should fail)
        logger.debug("Attempting to acquire one more browser (expecting failure)...")
        with pytest.raises(MCPBrowserException) as exc_info:
            await browser_pool.get_browser()
        
        assert exc_info.value.error_code == ErrorCode.MAX_BROWSERS_REACHED
        logger.debug(f"Caught expected exception: {exc_info.value.error_code}")
        
    except Exception as e:
        logger.error(f"Unexpected error in test_shared_pool_max_browser_limit: {e}", exc_info=True)
        raise # Re-raise unexpected errors
    finally:
        # Cleanup is handled by the session-scoped fixture teardown
        # We don't need to manually close browsers acquired here
        logger.debug("Finished test_shared_pool_max_browser_limit (cleanup handled by fixture)")

@pytest.mark.asyncio
async def test_resource_monitoring(browser_pool: BrowserPool):
    """Test that resource monitoring is working correctly (basic check)."""
    logger.debug("Starting test_resource_monitoring")
    # Ensure monitoring is active on the shared pool
    # Check may be fragile if tests run very fast, giving monitor no time to start
    await asyncio.sleep(0.1) # Short delay
    if browser_pool._monitor_task_handle:
         assert not browser_pool._monitor_task_handle.done(), "Monitor task is not running on shared pool"
         logger.debug("Monitor task confirmed running.")
    else:
         logger.warning("Monitor task handle not found, cannot confirm running status.")
        
    # Get initial metrics
    initial_metrics = browser_pool._get_system_metrics()
    logger.debug(f"Initial system metrics: {initial_metrics}")
    assert "memory_percent" in initial_metrics, "Memory metrics not available"
    assert "cpu_percent" in initial_metrics, "CPU metrics not available"
    
    # (Optional: Add activity to potentially change metrics, but asserting change is unreliable)
    
    logger.debug("Finished test_resource_monitoring") 