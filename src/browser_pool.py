#!/usr/bin/env python3
"""
Browser Pool for MCP Browser

This module provides a pool of browser instances for efficient resource management.
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
import time
import uuid
import psutil
from playwright.async_api import async_playwright, Browser, BrowserContext
from src.error_handler import MCPBrowserException, ErrorCode

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("browser-pool")

class BrowserInstance:
    """Represents a browser instance in the pool"""
    
    def __init__(self, instance_id: str, allowed_domains: Set[str] = None, blocked_domains: Set[str] = None, network_isolation: bool = True):
        """
        Initialize a browser instance
        
        Args:
            instance_id: Unique identifier for this browser instance
            allowed_domains: Set of domains allowed for network access
            blocked_domains: Set of domains explicitly blocked
            network_isolation: Whether network isolation is enabled
        """
        self.id = instance_id
        self.contexts: Dict[str, BrowserContext] = {}
        self.last_used = time.time()
        self.browser: Optional[Browser] = None
        self.is_closing = False
        self._playwright = None
        self.network_isolation = network_isolation
        self.allowed_domains = allowed_domains or set()
        self.blocked_domains = blocked_domains or set()
        
        logger.info(f"Created browser instance {self.id} with network isolation: {self.network_isolation}")
        if self.network_isolation:
            logger.info(f"Allowed domains: {self.allowed_domains}")
            logger.info(f"Blocked domains: {self.blocked_domains}")
    
    async def initialize(self):
        """Initialize the browser instance with Playwright"""
        try:
            logger.info(f"Initializing browser instance {self.id}")
            self._playwright = await async_playwright().start()
            
            # Launch browser with resource constraints and isolation args
            launch_args = [
                '--disable-dev-shm-usage',  # Avoid /dev/shm issues in Docker
                '--no-sandbox',  # Required for Docker
                '--disable-gpu',  # Reduce resource usage
                '--disable-software-rasterizer',  # Reduce memory usage
                '--disable-extensions',  # Disable extensions
                f'--js-flags=--max-old-space-size={256}',  # Limit JS heap
            ]
            if self.network_isolation:
                 # Experimental flags, might change based on Chromium version
                 launch_args.extend([
                     '--disable-features=NetworkService,NetworkServiceInProcess',
                     '--disable-background-networking',
                     '--disable-sync',
                     '--disable-default-apps',
                     '--disable-breakpad', # Disable crash reporting
                     '--disable-component-extensions-with-background-pages',
                     '--disable-component-update',
                     '--disable-domain-reliability',
                     '--disable-client-side-phishing-detection',
                     '--disable-sync-preferences',
                     '--enable-strict-mixed-content-checking',
                     '--use-mock-keychain', # Prevent keychain access
                 ])

            self.browser = await self._playwright.chromium.launch(
                args=launch_args,
                handle_sigint=True,
                handle_sigterm=True,
                handle_sighup=True
            )
            
            # Get browser process for monitoring - Removed as browser.process is not available/reliable
            # if self.browser and hasattr(self.browser, 'process') and self.browser.process:
            #      try:
            #           self.process = psutil.Process(self.browser.process.pid)
            #           logger.info(f"Browser instance {self.id} initialized with PID {self.process.pid}")
            #      except (psutil.NoSuchProcess, AttributeError) as e:
            #            logger.warning(f"Could not get process info for browser {self.id}: {e}")
            #            self.process = None
            # else:
            #      logger.warning(f"Browser instance {self.id} started but process info unavailable.")
            logger.info(f"Browser instance {self.id} initialized successfully.")

            return self.browser
            
        except Exception as e:
            logger.error(f"Failed to initialize browser instance {self.id}: {str(e)}")
            await self.close() # Attempt cleanup on failure
            raise MCPBrowserException(
                error_code=ErrorCode.BROWSER_INITIALIZATION_FAILED,
                message=f"Failed to initialize browser: {str(e)}",
                original_exception=e
            )
    
    async def create_context(self, context_id: str, **kwargs) -> BrowserContext:
        """
        Create a new browser context with resource limits and network isolation
        
        Args:
            context_id: Unique identifier for this context
            **kwargs: Additional context options
            
        Returns:
            Browser context object
        """
        if not self.browser:
             raise MCPBrowserException(ErrorCode.BROWSER_NOT_INITIALIZED, f"Browser {self.id} is not initialized.")

        try:
            logger.info(f"Creating context {context_id} in browser {self.id}")
            
            # Set default viewport and device scale factor
            context_params = {
                "viewport": {"width": 1280, "height": 720},
                "device_scale_factor": 1,
                "bypass_csp": True,  # Allow running scripts
                "java_script_enabled": True,
                **kwargs
            }
            
            # Apply network isolation settings
            if self.network_isolation:
                context_params.update({
                    "ignore_https_errors": False,  # Enforce HTTPS
                    "extra_http_headers": {
                        "X-Isolated-Context": "true"  # Mark as isolated
                    }
                })
            
            # Create the context with resource limits
            context = await self.browser.new_context(**context_params)
            
            # Set up network request interception if isolation is enabled
            if self.network_isolation:
                 logger.info(f"Enabling network request interception for context {context_id} in browser {self.id}")
                 await context.route("**/*", self._handle_route)

            # Set default timeout
            context.set_default_timeout(30000)
            
            # Store the context
            self.contexts[context_id] = context
            self.last_used = time.time()
            
            logger.info(f"Context {context_id} created successfully in browser {self.id}")
            return context
            
        except Exception as e:
            logger.error(f"Failed to create context {context_id} in browser {self.id}: {str(e)}")
            # Attempt to close context if creation failed mid-way
            if 'context' in locals() and context:
                try:
                    await context.close()
                except Exception as close_exc:
                     logger.error(f"Error closing partially created context {context_id}: {close_exc}")
            raise MCPBrowserException(
                error_code=ErrorCode.CONTEXT_CREATION_FAILED,
                message=f"Failed to create browser context {context_id}: {str(e)}",
                original_exception=e
            )
    
    async def close_context(self, context_id: str):
        """
        Close a browser context and clean up resources
        
        Args:
            context_id: ID of the context to close
        """
        if context_id not in self.contexts:
            logger.warning(f"Context {context_id} not found in browser {self.id}")
            return
            
        try:
            logger.info(f"Closing context {context_id} in browser {self.id}")
            context = self.contexts[context_id]
            
            # Close all pages in the context
            for page in context.pages:
                try:
                    await page.close()
                except Exception as e:
                    logger.warning(f"Error closing page in context {context_id}: {str(e)}")
            
            # Close the context
            await context.close()
            
            del self.contexts[context_id]
            self.last_used = time.time()
            
        except Exception as e:
            logger.error(f"Error closing context {context_id}: {str(e)}")
            # Still remove from tracking
            if context_id in self.contexts:
                del self.contexts[context_id]
    
    async def close(self):
        """Close the browser instance and clean up all resources"""
        if self.is_closing:
            logger.debug(f"[Browser {self.id}] Already closing, skipping")
            return
            
        self.is_closing = True
        logger.info(f"[Browser {self.id}] Starting close process")
        
        try:
            # Close all contexts
            context_ids = list(self.contexts.keys())
            if context_ids:
                logger.debug(f"[Browser {self.id}] Closing {len(context_ids)} contexts: {context_ids}")
                for context_id in context_ids:
                    try:
                        logger.debug(f"[Browser {self.id}] Closing context {context_id}")
                        await self.close_context(context_id)
                        logger.debug(f"[Browser {self.id}] Successfully closed context {context_id}")
                    except Exception as e:
                        logger.error(f"[Browser {self.id}] Error closing context {context_id}: {e}", exc_info=True)
            else:
                logger.debug(f"[Browser {self.id}] No contexts to close")
            
            # Close browser
            if self.browser:
                logger.debug(f"[Browser {self.id}] Closing browser process")
                try:
                    await self.browser.close()
                    logger.debug(f"[Browser {self.id}] Successfully closed browser process")
                except Exception as e:
                    logger.error(f"[Browser {self.id}] Error closing browser process: {e}", exc_info=True)
                finally:
                    self.browser = None
            
            # Stop playwright
            if self._playwright:
                logger.debug(f"[Browser {self.id}] Stopping playwright")
                try:
                    await self._playwright.stop()
                    logger.debug(f"[Browser {self.id}] Successfully stopped playwright")
                except Exception as e:
                    logger.error(f"[Browser {self.id}] Error stopping playwright: {e}", exc_info=True)
                finally:
                    self._playwright = None
            
            logger.info(f"[Browser {self.id}] Close process completed successfully")
            
        except Exception as e:
            logger.error(f"[Browser {self.id}] Error during close process: {e}", exc_info=True)
            raise MCPBrowserException(
                error_code=ErrorCode.BROWSER_CLEANUP_FAILED,
                message=f"Failed to clean up browser resources: {str(e)}",
                original_exception=e
            )

    async def _handle_route(self, route):
        """Intercept and handle network requests based on isolation rules."""
        request = route.request
        url = request.url
        domain = url.split('/')[2].split(':')[0] # Extract domain name

        if domain in self.blocked_domains:
            logger.warning(f"Blocked request to {domain} (explicitly blocked) in browser {self.id}")
            await route.abort("blockedbyclient")
            return
        
        # If allowed_domains is defined, only allow those domains
        if self.allowed_domains and domain not in self.allowed_domains:
            logger.warning(f"Blocked request to {domain} (not in allowed list) in browser {self.id}")
            await route.abort("blockedbyclient")
            return

        # Allow the request if it's not blocked and either allowed_domains is empty or the domain is in the list
        logger.debug(f"Allowed request to {url} in browser {self.id}")
        await route.continue_()

class BrowserPool:
    """Manages a pool of browser instances"""
    
    def __init__(self, 
                 max_browsers: int = 5, 
                 idle_timeout: int = 300, 
                 max_memory_percent: float = 80.0, 
                 max_cpu_percent: float = 80.0, 
                 monitor_interval: int = 60,
                 network_isolation: bool = True,
                 allowed_domains: Optional[List[str]] = None,
                 blocked_domains: Optional[List[str]] = None):
        """
        Initialize the browser pool
        
        Args:
            max_browsers: Maximum number of concurrent browser instances
            idle_timeout: Time in seconds before an idle browser is closed
            max_memory_percent: Maximum system memory usage percentage allowed
            max_cpu_percent: Maximum system CPU usage percentage allowed
            monitor_interval: Interval in seconds for resource monitoring task
            network_isolation: Enable network isolation features
            allowed_domains: List of domains allowed for network access
            blocked_domains: List of domains explicitly blocked
        """
        logger.info("[Pool] Initializing browser pool")
        self.max_browsers = max_browsers
        self.idle_timeout = idle_timeout
        self.max_memory_percent = max_memory_percent
        self.max_cpu_percent = max_cpu_percent
        self.monitor_interval = monitor_interval
        
        self.browsers: Dict[str, BrowserInstance] = {}
        self.lock = asyncio.Lock()
        self._monitor_task_handle: Optional[asyncio.Task] = None
        self._shutting_down = False

        # Network Isolation Settings
        self.network_isolation = network_isolation
        self.allowed_domains: Set[str] = set(allowed_domains) if allowed_domains else set()
        self.blocked_domains: Set[str] = set(blocked_domains) if blocked_domains else set()

        logger.info(f"[Pool] Browser Pool initialized with:")
        logger.info(f"[Pool]   Max Browsers: {self.max_browsers}")
        logger.info(f"[Pool]   Idle Timeout: {self.idle_timeout}s")
        logger.info(f"[Pool]   Max Memory: {self.max_memory_percent}%")
        logger.info(f"[Pool]   Max CPU: {self.max_cpu_percent}%")
        logger.info(f"[Pool]   Monitor Interval: {self.monitor_interval}s")
        logger.info(f"[Pool]   Network Isolation: {self.network_isolation}")
        if self.network_isolation:
            logger.info(f"[Pool]   Allowed Domains: {self.allowed_domains if self.allowed_domains else 'Any (if not blocked)'}")
            logger.info(f"[Pool]   Blocked Domains: {self.blocked_domains if self.blocked_domains else 'None'}")
        logger.info("[Pool] Initialization complete")
    
    async def start(self):
        """Start the browser pool and monitoring tasks"""
        logger.info("Starting browser pool")
        self.start_monitoring()
    
    async def stop(self):
        """Stop the browser pool and clean up all resources"""
        logger.info("Stopping browser pool")
        
        # Cancel monitoring tasks
        if self._monitor_task_handle and not self._monitor_task_handle.done():
            self._monitor_task_handle.cancel()
            try:
                await self._monitor_task_handle
            except asyncio.CancelledError:
                logger.info("Monitoring task successfully cancelled.")
            except Exception as e:
                logger.error(f"Error during monitor task cancellation: {e}")
        
        # Close all browsers
        async with self.lock:
            for browser_id in list(self.browsers.keys()):
                await self.close_browser(browser_id)
        
        logger.info("Browser pool stopped")
    
    def _get_system_metrics(self) -> Dict[str, float]:
        """Get current system resource usage"""
        return {
            "memory_percent": psutil.virtual_memory().percent,
            "cpu_percent": psutil.cpu_percent(interval=1)
        }
    
    async def _check_resource_limits(self) -> bool:
        """Check if system resource usage is within limits."""
        metrics = self._get_system_metrics()
        memory_usage = metrics["memory_percent"]
        cpu_usage = metrics["cpu_percent"]

        if memory_usage > self.max_memory_percent:
            logger.warning(f"Memory usage high: {memory_usage:.2f}% (Limit: {self.max_memory_percent}%)")
            await self._close_idle_browsers(force_check=True)
            # Recheck after cleanup
            memory_usage = self._get_system_metrics()["memory_percent"]
            if memory_usage > self.max_memory_percent:
                logger.error(f"Memory usage still high after cleanup: {memory_usage:.2f}%")
                return False
        
        if cpu_usage > self.max_cpu_percent:
            logger.warning(f"CPU usage high: {cpu_usage:.2f}% (Limit: {self.max_cpu_percent}%)")
            await self._close_idle_browsers(force_check=True)
            # Recheck after cleanup
            cpu_usage = self._get_system_metrics()["cpu_percent"]
            if cpu_usage > self.max_cpu_percent:
                logger.error(f"CPU usage still high after cleanup: {cpu_usage:.2f}%")
                return False

        return True
    
    async def _close_idle_browsers(self, force_check=False):
        """Closes browser instances that have been idle for too long."""
        async with self.lock:
            current_time = time.time()
            browsers_to_close = []

            for instance_id, browser in self.browsers.items():
                if not browser.is_closing and not browser.contexts:
                    idle_time = current_time - browser.last_used
                    if idle_time > self.idle_timeout:
                        logger.info(f"Browser {instance_id} idle for {idle_time:.2f}s, closing")
                        browsers_to_close.append(instance_id)

            if browsers_to_close:
                logger.info(f"Closing {len(browsers_to_close)} idle browsers")
                await asyncio.gather(
                    *(self.close_browser(browser_id) for browser_id in browsers_to_close),
                    return_exceptions=True
                )
    
    async def _monitor_task(self):
        """Background task to monitor resources and close idle browsers."""
        logger.info("Starting browser pool monitor task")
        while not self._shutting_down:
            try:
                await asyncio.sleep(self.monitor_interval)
                if self._shutting_down:
                    break

                await self._check_resource_limits()
                await self._close_idle_browsers()

            except asyncio.CancelledError:
                logger.info("Monitor task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in monitor task: {e}", exc_info=True)
                await asyncio.sleep(self.monitor_interval)

        logger.info("Browser pool monitor task stopped")

    async def get_browser(self) -> BrowserInstance:
        """
        Get an available browser instance from the pool, creating one if necessary.
        
        Returns:
            An available BrowserInstance
            
        Raises:
            MCPBrowserException: If resource limits are exceeded or browser creation fails.
        """
        async with self.lock:
            if self._shutting_down:
                raise MCPBrowserException(ErrorCode.POOL_SHUTTING_DOWN, "Browser pool is shutting down")

            # Check resource limits before creating a new browser
            if not await self._check_resource_limits():
                raise MCPBrowserException(
                    ErrorCode.RESOURCE_LIMIT_EXCEEDED,
                    "System resource limits exceeded. Cannot create new browser"
                )

            # Check if we've reached the maximum number of browsers
            if len(self.browsers) >= self.max_browsers:
                raise MCPBrowserException(
                    ErrorCode.MAX_BROWSERS_REACHED,
                    f"Maximum number of browsers ({self.max_browsers}) reached"
                )

            # Create a new browser instance
            instance_id = str(uuid.uuid4())
            browser_instance = BrowserInstance(
                instance_id,
                allowed_domains=self.allowed_domains,
                blocked_domains=self.blocked_domains,
                network_isolation=self.network_isolation
            )

            try:
                await browser_instance.initialize()
                self.browsers[instance_id] = browser_instance
                logger.info(f"Created new browser instance {instance_id}")
                return browser_instance
            except Exception as e:
                logger.error(f"Failed to initialize browser {instance_id}: {e}")
                await browser_instance.close()
                raise MCPBrowserException(
                    ErrorCode.BROWSER_INITIALIZATION_FAILED,
                    f"Failed to initialize browser: {str(e)}",
                    original_exception=e
                )

    async def close_browser(self, browser_id: str):
        """Close a specific browser instance and remove it from the pool."""
        logger.debug(f"[Pool] close_browser called for {browser_id}")
        try:
            async with self.lock:
                if browser_id in self.browsers:
                    browser = self.browsers[browser_id]
                    logger.info(f"[Pool] Found browser {browser_id}. Initiating close...")
                    
                    # Remove timeout from browser.close()
                    try:
                        await browser.close()
                        logger.debug(f"[Pool] Successfully awaited browser.close() for {browser_id}")
                    # Removed asyncio.TimeoutError specific handling, rely on generic Exception
                    except Exception as e:
                        logger.error(f"[Pool] Error during browser.close() for {browser_id}: {e}", exc_info=True)
                        raise # Re-raise to signal cleanup issue for this browser
                    
                    del self.browsers[browser_id]
                    logger.debug(f"[Pool] Removed browser {browser_id} from pool.")
                else:
                    logger.warning(f"[Pool] Attempted to close non-existent browser {browser_id}")
        except Exception as e:
            logger.error(f"[Pool] Error in close_browser for {browser_id}: {e}", exc_info=True)
            # Do not re-raise here, allow cleanup loop to continue

    def start_monitoring(self):
        """Start the background monitoring task."""
        if self._monitor_task_handle is None or self._monitor_task_handle.done():
            self._shutting_down = False
            self._monitor_task_handle = asyncio.create_task(self._monitor_task())
            logger.info("Started browser pool monitoring")

    async def cleanup(self):
        """Clean up all browser instances and resources."""
        logger.info("[Pool] Starting cleanup")
        
        try:
            async with self.lock:
                # Get list of browsers to close
                browsers_to_close = list(self.browsers.keys())
                logger.info(f"[Pool] Closing {len(browsers_to_close)} remaining browsers: {browsers_to_close}")
                
                # Close each browser with a timeout
                for browser_id in browsers_to_close:
                    browser = self.browsers[browser_id]
                    if browser:
                        try:
                            await asyncio.wait_for(self.close_browser(browser), timeout=5.0)
                        except asyncio.TimeoutError:
                            logger.warning(f"[Pool] Timeout closing browser {browser_id}")
                        except Exception as e:
                            logger.error(f"[Pool] Error closing browser {browser_id}: {e}")
                
                # Clear browser tracking
                self.browsers.clear()
                self.last_used.clear()
                
                # Stop monitoring if active
                if self._monitor_task_handle and not self._monitor_task_handle.done():
                    self._monitor_task_handle.cancel()
                    try:
                        await asyncio.wait_for(self._monitor_task_handle, timeout=5.0)
                    except (asyncio.TimeoutError, asyncio.CancelledError):
                        pass
                    except Exception as e:
                        logger.error(f"[Pool] Error cancelling monitor task: {e}")
                
                logger.info("[Pool] Cleanup completed")
                
        except asyncio.CancelledError:
            logger.warning("[Pool] Cleanup was cancelled")
        except Exception as e:
            logger.error(f"[Pool] Unexpected error during cleanup: {e}", exc_info=True)
        finally:
            # Ensure we don't try to use the event loop after it's closed
            try:
                if self.lock.locked():
                    self.lock.release()
            except Exception:
                pass

# Global instance
browser_pool = None

async def initialize_browser_pool(max_browsers: int = 10, idle_timeout: int = 300):
    """
    Initialize the global browser pool
    
    Args:
        max_browsers: Maximum number of concurrent browser instances
        idle_timeout: Time in seconds after which idle browsers are closed
    """
    global browser_pool
    
    if browser_pool is None:
        browser_pool = BrowserPool(max_browsers, idle_timeout)
        await browser_pool.start()
    
    return browser_pool

async def close_browser_pool():
    """Close the global browser pool"""
    global browser_pool
    
    if browser_pool is not None:
        await browser_pool.stop()
        browser_pool = None 