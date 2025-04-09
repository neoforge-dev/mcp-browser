import pytest
import pytest_asyncio
import asyncio
import logging
from contextlib import asynccontextmanager
from src.browser_pool import BrowserPool
from typing import Generator
import uuid
import docker
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test-fixtures")

# --- Docker Fixtures ---

@pytest.fixture(scope="session")
def docker_client():
    """Session-scoped fixture providing a Docker client."""
    logger.info("Creating Docker client...")
    try:
        client = docker.from_env()
        client.ping() # Simple check to verify connection
        logger.info("Docker client created successfully.")
        return client
    except Exception as e:
        logger.error(f"Failed to create Docker client: {e}", exc_info=True)
        pytest.fail(f"Docker client creation failed: {e}")

@pytest.fixture(scope="session")
def mcp_browser_container(docker_client):
    """Session-scoped fixture providing the running MCP Browser container object."""
    container_name = "mcp-browser"
    logger.info(f"Searching for container '{container_name}'...")
    try:
        # Wait up to 10 seconds for the container
        for _ in range(10):
            containers = docker_client.containers.list(filters={"name": container_name})
            if containers:
                container = containers[0]
                if container.status == 'running':
                     logger.info(f"Found running container '{container_name}' ({container.id})")
                     return container
                else:
                     logger.info(f"Found container '{container_name}' but status is {container.status}. Waiting...")
            time.sleep(1)
        pytest.fail(f"Container '{container_name}' not found or not running after 10s.")
    except Exception as e:
        logger.error(f"Error finding container '{container_name}': {e}", exc_info=True)
        pytest.fail(f"Error finding container '{container_name}': {e}")

# --- Event Loop Fixture ---

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
        idle_timeout=5,
        max_memory_percent=80.0,
        max_cpu_percent=80.0,
        monitor_interval=1.0,
        network_isolation=True,  # Restore network isolation
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

# Reverted scope to session
@pytest_asyncio.fixture(scope="session") 
async def browser_context(browser_pool):
    """Fixture providing a session-scoped browser context for tests."""
    # This assumes the pool manages only ONE browser for the entire session
    # and contexts share that single browser instance. 
    # Simpler version, relies on pool fixture correctness.
    browser_instance = None
    context = None
    context_id = f"shared-test-ctx-{uuid.uuid4()}"
    
    logger.debug(f"Setting up session-scoped browser_context fixture (context_id: {context_id})")
    try:
        # Get the single browser instance managed by the session pool
        # Assumes pool already has or will create the instance
        # This might need refinement if pool doesn't guarantee instance exists
        instances = list(browser_pool.browsers.values())
        if not instances:
             logger.debug(f"[{context_id}] No browser instance in pool yet, getting one...")
             browser_instance = await browser_pool.get_browser()
        else:
             browser_instance = instances[0]
             logger.debug(f"[{context_id}] Using existing browser instance from pool: {browser_instance.id}")
             
        assert browser_instance is not None, f"[{context_id}] Failed to get browser instance from pool"

        # Create context within the instance
        logger.debug(f"[{context_id}] Creating context in browser {browser_instance.id}...")
        context = await browser_instance.create_context(context_id)
        assert context is not None, f"[{context_id}] Failed to create context"
        logger.debug(f"[{context_id}] Context created successfully, yielding to tests.")
        
        yield context # Yield the created context
        
    except Exception as e:
         logger.error(f"[{context_id}] Error setting up session browser_context fixture: {e}", exc_info=True)
         raise
         
    finally:
        # Teardown for the session context
        logger.debug(f"[{context_id}] Tearing down session-scoped browser_context fixture...")
        if context and browser_instance:
            logger.debug(f"[{context_id}] Closing context in browser {browser_instance.id}...")
            try:
                await browser_instance.close_context(context_id)
                logger.debug(f"[{context_id}] Context closed successfully.")
            except Exception as e:
                logger.error(f"[{context_id}] Error closing context during session fixture teardown: {e}")
        # Do NOT close the browser instance here, it's managed by the browser_pool session fixture 