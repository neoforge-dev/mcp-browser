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
            
            # --- DEBUG: Minimize launch args --- 
            # launch_args = [
            #     '--disable-dev-shm-usage',  # Avoid /dev/shm issues in Docker
            #     '--no-sandbox',  # Required for Docker
            #     '--disable-gpu',  # Reduce resource usage
            #     '--disable-software-rasterizer',  # Reduce memory usage
            #     '--disable-extensions',  # Disable extensions
            #     f'--js-flags=--max-old-space-size={256}',  # Limit JS heap
            # ]
            # if self.network_isolation:
            #      # Experimental flags, might change based on Chromium version
            #      launch_args.extend([
            #          '--disable-features=NetworkService,NetworkServiceInProcess',
            #          '--disable-background-networking',
            #          '--disable-sync',
            #          '--disable-default-apps',
            #          '--disable-breakpad', # Disable crash reporting
            #          '--disable-component-extensions-with-background-pages',
            #          '--disable-component-update',
            #          '--disable-domain-reliability',
            #          '--disable-client-side-phishing-detection',
            #          '--disable-sync-preferences',
            #          '--enable-strict-mixed-content-checking',
            #          '--use-mock-keychain', # Prevent keychain access
            #      ])
            launch_args = ['--no-sandbox'] # Minimal args for debugging
            logger.warning(f"[DEBUG] Using minimal launch_args: {launch_args}")
            # --- END DEBUG --- 

            self.browser = await self._playwright.chromium.launch(
                args=launch_args,
                handle_sigint=True,
                handle_sigterm=True,
                handle_sighup=True
            )
            
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
        
        close_error = None
        try:
            # Close all contexts first
            context_ids = list(self.contexts.keys())
            if context_ids:
                logger.debug(f"[Browser {self.id}] Closing {len(context_ids)} contexts: {context_ids}")
                for context_id in context_ids:
                    try:
                        await self.close_context(context_id)
                    except Exception as e:
                        logger.error(f"[Browser {self.id}] Error closing context {context_id}: {e}", exc_info=True)
                        if not close_error: close_error = e # Keep first error
            
            # Close browser with timeout
            if self.browser:
                logger.debug(f"[Browser {self.id}] Closing browser process")
                try:
                    await asyncio.wait_for(self.browser.close(), timeout=5.0) # Added timeout
                    logger.debug(f"[Browser {self.id}] Successfully closed browser process")
                except asyncio.TimeoutError:
                    logger.error(f"[Browser {self.id}] Timeout closing browser process")
                    if not close_error: close_error = asyncio.TimeoutError("Browser close timeout")
                except Exception as e:
                    logger.error(f"[Browser {self.id}] Error closing browser process: {e}", exc_info=True)
                    if not close_error: close_error = e
                finally:
                    self.browser = None
            
            # Stop playwright with timeout
            if self._playwright:
                logger.debug(f"[Browser {self.id}] Stopping playwright")
                try:
                    await asyncio.wait_for(self._playwright.stop(), timeout=5.0) # Added timeout
                    logger.debug(f"[Browser {self.id}] Successfully stopped playwright")
                except asyncio.TimeoutError:
                    logger.error(f"[Browser {self.id}] Timeout stopping playwright")
                    if not close_error: close_error = asyncio.TimeoutError("Playwright stop timeout")
                except Exception as e:
                    logger.error(f"[Browser {self.id}] Error stopping playwright: {e}", exc_info=True)
                    if not close_error: close_error = e
                finally:
                    self._playwright = None
            
            if close_error:
                logger.warning(f"[Browser {self.id}] Close process completed with errors.")
                # Raise the first encountered error after attempting all cleanup steps
                raise MCPBrowserException(
                    error_code=ErrorCode.BROWSER_CLEANUP_FAILED,
                    message=f"Failed to clean up browser resources fully: {str(close_error)}",
                    original_exception=close_error
                )
            else:
                 logger.info(f"[Browser {self.id}] Close process completed successfully")
            
        except Exception as e:
            # Catch any unexpected error during the close process itself
            logger.error(f"[Browser {self.id}] Unexpected error during close process: {e}", exc_info=True)
            if not isinstance(e, MCPBrowserException):
                 raise MCPBrowserException(
                    error_code=ErrorCode.BROWSER_CLEANUP_FAILED,
                    message=f"Unexpected failure during browser cleanup: {str(e)}",
                    original_exception=e
                )
            else:
                raise e # Re-raise if it's already an MCPBrowserException

    async def _handle_route(self, route):
        """Intercept and handle network requests based on isolation rules."""
        request = route.request
        url = request.url
        log_prefix = f"[Browser {self.id}][Route Handler]"
        logger.debug(f"{log_prefix} Intercepted request to: {url}")
        
        try:
            domain = url.split('/')[2].split(':')[0] # Extract domain name
            logger.debug(f"{log_prefix} Extracted domain: {domain}")
        except IndexError:
            logger.warning(f"{log_prefix} Could not extract domain from URL: {url}. Allowing by default.")
            try:
                await route.continue_()
                logger.debug(f"{log_prefix} Allowed request (no domain) to {url}")
            except Exception as e:
                 logger.error(f"{log_prefix} Error continuing request (no domain) to {url}: {e}")
                 try: await route.abort() # Attempt to abort if continue fails
                 except: pass
            return

        if domain in self.blocked_domains:
            logger.warning(f"{log_prefix} Blocking request to {domain} (explicitly blocked) for URL: {url}")
            try:
                await route.abort("blockedbyclient")
            except Exception as e:
                 logger.error(f"{log_prefix} Error aborting blocked request to {url}: {e}")
            return
        
        # If allowed_domains is defined, only allow those domains
        if self.allowed_domains and domain not in self.allowed_domains:
            logger.warning(f"{log_prefix} Blocking request to {domain} (not in allowed list) for URL: {url}")
            try:
                await route.abort("addressunreachable") # Use a different error code
            except Exception as e:
                 logger.error(f"{log_prefix} Error aborting unallowed request to {url}: {e}")
            return

        # Allow the request if it passes all checks
        logger.debug(f"{log_prefix} Allowing request to {url} (Domain: {domain})")
        try:
            await route.continue_()
            logger.debug(f"{log_prefix} Successfully continued request to {url}")
        except Exception as e:
             logger.error(f"{log_prefix} Error continuing allowed request to {url}: {e}")
             # Attempt to abort if continue fails, otherwise it might hang
             try: await route.abort() 
             except: pass

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
        """Check if system resource usage is within limits. Closes LRU browser if exceeded."""
        metrics = self._get_system_metrics()
        memory_usage = metrics["memory_percent"]
        cpu_usage = metrics["cpu_percent"]
        limit_exceeded = False
        lru_browser_id = None

        if memory_usage > self.max_memory_percent:
            logger.warning(f"Memory usage high: {memory_usage:.2f}% (Limit: {self.max_memory_percent}%)")
            limit_exceeded = True
        
        if cpu_usage > self.max_cpu_percent:
            logger.warning(f"CPU usage high: {cpu_usage:.2f}% (Limit: {self.max_cpu_percent}%)")
            limit_exceeded = True

        if limit_exceeded:
            async with self.lock: # Acquire lock to safely access browsers list
                if not self.browsers:
                    logger.warning("Resource limit exceeded but no browsers to close.")
                    return False # Cannot recover if no browsers exist

                # Find the least recently used browser
                lru_browser_id = min(self.browsers.keys(), key=lambda bid: self.browsers[bid].last_used)
                logger.warning(f"Resource limit exceeded. Closing least recently used browser: {lru_browser_id}")
            
            # Close the identified browser (outside the main lock to avoid deadlock)
            try:
                await self.close_browser(lru_browser_id)
                # Recheck limits after closing one browser
                metrics = self._get_system_metrics()
                memory_usage = metrics["memory_percent"]
                cpu_usage = metrics["cpu_percent"]
                if memory_usage > self.max_memory_percent or cpu_usage > self.max_cpu_percent:
                     logger.error(f"Resource usage still high after closing LRU browser {lru_browser_id}. Mem: {memory_usage:.2f}%, CPU: {cpu_usage:.2f}%")
                     return False # Still exceeding limits
                else:
                     logger.info(f"Resource usage back within limits after closing {lru_browser_id}.")
                     return True
            except Exception as e:
                 logger.error(f"Failed to close LRU browser {lru_browser_id} during resource limit check: {e}", exc_info=True)
                 return False # Failed to recover

        return True # Limits were not exceeded
    
    async def _close_idle_browsers(self, force_check=False):
        """Closes browser instances that have been idle for too long."""
        async with self.lock:
            current_time = time.time()
            browsers_to_close = []

            for instance_id, browser in self.browsers.items():
                if not browser.is_closing and not browser.contexts:
                    idle_time = current_time - browser.last_used
                    if idle_time > self.idle_timeout:
                        logger.info(f"Browser {instance_id} idle for {idle_time:.2f}s, scheduling for close")
                        browsers_to_close.append(instance_id)

            if browsers_to_close:
                logger.info(f"Closing {len(browsers_to_close)} idle browsers sequentially")
                # Close sequentially for easier debugging
                for browser_id in browsers_to_close:
                    logger.debug(f"Closing idle browser {browser_id}...")
                    try:
                        await self.close_browser(browser_id)
                        logger.debug(f"Successfully closed idle browser {browser_id}")
                    except Exception as e:
                        logger.error(f"Error closing idle browser {browser_id}: {e}", exc_info=True)
    
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
        browser_closed_successfully = False
        try:
            async with self.lock:
                if browser_id in self.browsers:
                    browser = self.browsers[browser_id]
                    logger.info(f"[Pool] Found browser {browser_id}. Initiating close...")
                    
                    # Apply timeout specifically to the instance close operation
                    try:
                        await asyncio.wait_for(browser.close(), timeout=10.0) # Added timeout
                        logger.debug(f"[Pool] Successfully awaited browser.close() for {browser_id}")
                        browser_closed_successfully = True
                    except asyncio.TimeoutError:
                         logger.error(f"[Pool] Timeout during browser.close() for {browser_id}")
                         # Attempt to force cleanup if possible (may still hang)
                    except Exception as e:
                        logger.error(f"[Pool] Error during browser.close() for {browser_id}: {e}", exc_info=True)
                        # Consider the browser potentially problematic, but proceed with removal
                    
                    # Always remove from tracking, even if close failed/timed out
                    del self.browsers[browser_id]
                    logger.debug(f"[Pool] Removed browser {browser_id} from pool tracking.")
                else:
                    logger.warning(f"[Pool] Attempted to close non-existent browser {browser_id}")
        except Exception as e:
            logger.error(f"[Pool] Error in close_browser lock/lookup for {browser_id}: {e}", exc_info=True)
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
        self._shutting_down = True # Signal monitor to stop
        
        try:
            # Stop monitoring first
            if self._monitor_task_handle and not self._monitor_task_handle.done():
                logger.info("[Pool] Cancelling monitor task...")
                self._monitor_task_handle.cancel()
                try:
                    await asyncio.wait_for(self._monitor_task_handle, timeout=5.0)
                    logger.info("[Pool] Monitor task cancelled successfully.")
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    logger.warning("[Pool] Monitor task cancellation timed out or already cancelled.")
                except Exception as e:
                    logger.error(f"[Pool] Error waiting for monitor task cancellation: {e}")
            
            # Now acquire lock and close browsers
            async with self.lock:
                browsers_to_close = list(self.browsers.keys())
                logger.info(f"[Pool] Closing {len(browsers_to_close)} remaining browsers: {browsers_to_close}")
                
                for browser_id in browsers_to_close:
                    browser = self.browsers.get(browser_id) # Use .get() for safety
                    if browser:
                        logger.debug(f"[Pool] Cleaning up browser {browser_id}")
                        try:
                            # Using close_browser which now has internal timeouts
                            await asyncio.wait_for(self.close_browser(browser_id), timeout=15.0) # Overall timeout for close_browser
                        except asyncio.TimeoutError:
                            logger.error(f"[Pool] Overall timeout cleaning up browser {browser_id}. Might be stuck.")
                        except Exception as e:
                            logger.error(f"[Pool] Error during cleanup for browser {browser_id}: {e}")
                    else:
                         logger.warning(f"[Pool] Browser {browser_id} not found during final cleanup loop, already removed?)")
                
                # Clear browser tracking dictionary
                self.browsers.clear()
                
                logger.info("[Pool] Cleanup completed")
                
        except asyncio.CancelledError:
            logger.warning("[Pool] Cleanup was cancelled")
        except Exception as e:
            logger.error(f"[Pool] Unexpected error during cleanup: {e}", exc_info=True)
        finally:
            # Ensure we don't try to use the event loop after it's closed
            # And release lock if held
            try:
                if self.lock.locked():
                    self.lock.release()
                    logger.debug("[Pool] Released lock in cleanup finally block.")
            except Exception as lock_e:
                 logger.warning(f"[Pool] Exception releasing lock in cleanup: {lock_e}")

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