import pytest
import pytest_asyncio
import asyncio
import logging
from contextlib import asynccontextmanager
from src.browser_pool import BrowserPool
from typing import Generator
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test-fixtures")

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    
    # Clean up pending tasks
    pending = asyncio.all_tasks(loop)
    if pending:
        logger.info(f"Cleaning up {len(pending)} pending tasks")
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def browser_pool(event_loop):
    """Session-scoped fixture providing a shared browser pool for tests."""
    logger.info("Creating session-scoped browser pool")
    pool = BrowserPool(
        max_browsers=1,
        idle_timeout=1,
        max_memory_percent=80.0,
        max_cpu_percent=80.0,
        monitor_interval=0.5,
        network_isolation=True,  # Re-enabled
        allowed_domains=["example.com"], 
        blocked_domains=["blocked.com"]
    )
    
    try:
        await pool.start()
        logger.info("Browser pool started successfully")
        yield pool
    except Exception as e:
        logger.error(f"Error in browser_pool fixture: {e}", exc_info=True)
        raise
    finally:
        logger.info("Cleaning up session-scoped browser pool")
        try:
            # Use pool's cleanup method directly
            await pool.cleanup()
            logger.info("Session-scoped browser pool cleanup completed via pool.cleanup()")
        except Exception as e:
            logger.error(f"Error during browser pool cleanup call: {e}", exc_info=True)
            # Avoid re-raising here to allow event loop cleanup to proceed

@pytest.fixture(autouse=True)
def setup_async_environment(event_loop: asyncio.AbstractEventLoop) -> None:
    """Set up the async environment for each test."""
    asyncio.set_event_loop(event_loop)

@pytest_asyncio.fixture(scope="function") 
async def browser_context(browser_pool):
    """Fixture providing a function-scoped browser context for tests."""
    browser_instance = None
    context = None
    context_id = f"test-ctx-{uuid.uuid4()}" # Unique ID per test function
    
    logger.debug(f"Setting up browser_context fixture for test function (context_id: {context_id})")
    
    try:
        # Get a browser instance from the pool for this test function
        logger.debug(f"[{context_id}] Requesting browser instance from pool...")
        browser_instance = await browser_pool.get_browser()
        assert browser_instance is not None, f"[{context_id}] Failed to get browser instance from pool"
        logger.debug(f"[{context_id}] Got browser instance: {browser_instance.id}")
        
        # Create context within the instance
        logger.debug(f"[{context_id}] Creating context in browser {browser_instance.id}...")
        context = await browser_instance.create_context(context_id)
        assert context is not None, f"[{context_id}] Failed to create context"
        logger.debug(f"[{context_id}] Context created successfully, yielding to test.")
        
        yield context # Yield the created context to the test function
        
    except Exception as e:
         logger.error(f"[{context_id}] Error setting up browser_context fixture: {e}", exc_info=True)
         raise # Re-raise the setup error
         
    finally:
        # Teardown: Ensure cleanup happens even if test fails or setup partially completes
        logger.debug(f"[{context_id}] Tearing down browser_context fixture...")
        if context and browser_instance:
            logger.debug(f"[{context_id}] Closing context in browser {browser_instance.id}...")
            try:
                await browser_instance.close_context(context_id)
                logger.debug(f"[{context_id}] Context closed successfully.")
            except Exception as e:
                logger.error(f"[{context_id}] Error closing context during fixture teardown: {e}")
        else:
             logger.debug(f"[{context_id}] No context object to close.")

        # Crucially, close the browser instance via the pool to release it
        if browser_instance:
             logger.debug(f"[{context_id}] Closing browser instance {browser_instance.id} via pool...")
             try:
                 await browser_pool.close_browser(browser_instance.id)
                 logger.debug(f"[{context_id}] Browser instance {browser_instance.id} closed via pool.")
             except Exception as e:
                 logger.error(f"[{context_id}] Error closing browser instance {browser_instance.id} via pool: {e}")
        else:
            logger.debug(f"[{context_id}] No browser instance object to close via pool.")
            
        logger.debug(f"[{context_id}] Teardown of browser_context fixture complete.") 