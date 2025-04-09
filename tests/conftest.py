import pytest
import pytest_asyncio
import asyncio
import logging
from src.browser_pool import BrowserPool
from typing import Generator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
def setup_async_environment(event_loop: asyncio.AbstractEventLoop) -> None:
    """Set up the async environment for each test."""
    asyncio.set_event_loop(event_loop)

@pytest_asyncio.fixture(scope="session")
async def browser_pool(event_loop):
    """Create a browser pool for testing."""
    pool = BrowserPool(
        max_browsers=2,
        idle_timeout=5,  # Short timeout for testing
        max_memory_percent=30.0,  # Strict memory limit
        max_cpu_percent=30.0,  # Strict CPU limit
        monitor_interval=1  # Frequent monitoring
    )
    
    try:
        await pool.start()
        logger.info("Browser pool started successfully")
        yield pool
    except Exception as e:
        logger.error(f"Error starting browser pool: {e}")
        raise
    finally:
        logger.info("Cleaning up browser pool")
        await pool.cleanup()

@pytest.fixture
async def browser_context(browser_pool):
    """Create a browser context for testing."""
    logger.debug("browser_context fixture: Getting browser...")
    browser = await browser_pool.get_browser()
    logger.debug(f"browser_context fixture: Got browser {browser.pid if hasattr(browser, 'pid') else 'N/A'}, creating context...")
    context = await browser.create_context()
    logger.debug(f"browser_context fixture: Created context, yielding.")
    yield context
    # --- Teardown starts here ---
    logger.info(f"browser_context fixture: Starting teardown for context...")
    try:
        logger.debug(f"browser_context fixture: Closing context...")
        await context.close()
        logger.debug(f"browser_context fixture: Context closed.")
    except Exception as e:
        logger.error(f"browser_context fixture: Error closing context: {e}", exc_info=True)
    
    try:
        browser_id = browser.id if hasattr(browser, 'id') else 'N/A'
        logger.debug(f"browser_context fixture: Closing browser {browser_id} via pool...")
        await browser_pool.close_browser(browser)
        logger.debug(f"browser_context fixture: Browser {browser_id} closed via pool.")
    except Exception as e:
        logger.error(f"browser_context fixture: Error closing browser via pool: {e}", exc_info=True)
    logger.info(f"browser_context fixture: Teardown complete.") 