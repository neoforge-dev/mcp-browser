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
from error_handler import MCPBrowserException, ErrorCode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("browser-pool")

class BrowserInstance:
    """Represents a browser instance in the pool"""
    
    def __init__(self, instance_id: str):
        """
        Initialize a browser instance
        
        Args:
            instance_id: Unique identifier for this browser instance
        """
        self.id = instance_id
        self.contexts: Dict[str, BrowserContext] = {}
        self.last_used = time.time()
        self.browser: Optional[Browser] = None
        self.is_closing = False
        self.process: Optional[psutil.Process] = None
        self._playwright = None
        
        logger.info(f"Created browser instance {self.id}")
    
    async def initialize(self):
        """Initialize the browser instance with Playwright"""
        try:
            logger.info(f"Initializing browser instance {self.id}")
            self._playwright = await async_playwright().start()
            
            # Launch browser with resource constraints
            self.browser = await self._playwright.chromium.launch(
                args=[
                    '--disable-dev-shm-usage',  # Avoid /dev/shm issues in Docker
                    '--no-sandbox',  # Required for Docker
                    '--disable-gpu',  # Reduce resource usage
                    '--disable-software-rasterizer',  # Reduce memory usage
                    '--disable-extensions',  # Disable extensions
                    f'--js-flags=--max-old-space-size={256}',  # Limit JS heap
                ],
                handle_sigint=True,
                handle_sigterm=True,
                handle_sighup=True
            )
            
            # Get browser process for monitoring
            self.process = psutil.Process(self.browser.process.pid)
            
            logger.info(f"Browser instance {self.id} initialized with PID {self.process.pid}")
            return self.browser
            
        except Exception as e:
            logger.error(f"Failed to initialize browser instance {self.id}: {str(e)}")
            raise MCPBrowserException(
                error_code=ErrorCode.BROWSER_INITIALIZATION_FAILED,
                message=f"Failed to initialize browser: {str(e)}",
                original_exception=e
            )
    
    async def create_context(self, context_id: str, **kwargs) -> BrowserContext:
        """
        Create a new browser context with resource limits
        
        Args:
            context_id: Unique identifier for this context
            **kwargs: Additional context options
            
        Returns:
            Browser context object
        """
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
            
            # Create the context with resource limits
            context = await self.browser.new_context(**context_params)
            
            # Set default timeout
            context.set_default_timeout(30000)
            
            # Store the context
            self.contexts[context_id] = context
            self.last_used = time.time()
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to create context {context_id}: {str(e)}")
            raise MCPBrowserException(
                error_code=ErrorCode.CONTEXT_CREATION_FAILED,
                message=f"Failed to create browser context: {str(e)}",
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
            return
            
        self.is_closing = True
        logger.info(f"Closing browser instance {self.id}")
        
        try:
            # Close all contexts
            for context_id in list(self.contexts.keys()):
                await self.close_context(context_id)
            
            # Close browser
            if self.browser:
                await self.browser.close()
                self.browser = None
            
            # Stop playwright
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
            
            # Ensure process is terminated
            if self.process and self.process.is_running():
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except psutil.TimeoutExpired:
                    self.process.kill()
            
            logger.info(f"Browser instance {self.id} closed and resources cleaned up")
            
        except Exception as e:
            logger.error(f"Error closing browser instance {self.id}: {str(e)}")
            raise MCPBrowserException(
                error_code=ErrorCode.BROWSER_CLEANUP_FAILED,
                message=f"Failed to clean up browser resources: {str(e)}",
                original_exception=e
            )

class BrowserPool:
    """Manages a pool of browser instances"""
    
    def __init__(self, max_browsers: int = 10, idle_timeout: int = 300):
        """
        Initialize the browser pool
        
        Args:
            max_browsers: Maximum number of concurrent browser instances
            idle_timeout: Time in seconds after which idle browsers are closed
        """
        self.max_browsers = max_browsers
        self.idle_timeout = idle_timeout
        self.browsers: Dict[str, BrowserInstance] = {}
        self.cleanup_task = None
        self.monitor_task = None
        self.lock = asyncio.Lock()
        
        # Resource limits
        self.max_memory_percent = float(os.environ.get("MAX_MEMORY_PERCENT", 80))
        self.max_cpu_percent = float(os.environ.get("MAX_CPU_PERCENT", 80))
        self.memory_threshold = float(os.environ.get("MEMORY_THRESHOLD", 90))
        
        # Resource monitoring intervals
        self.monitor_interval = int(os.environ.get("MONITOR_INTERVAL", 5))
        self.cleanup_interval = int(os.environ.get("CLEANUP_INTERVAL", 60))
        
        # Recovery settings
        self.max_recovery_attempts = int(os.environ.get("MAX_RECOVERY_ATTEMPTS", 3))
        self.recovery_delay = float(os.environ.get("RECOVERY_DELAY", 1.0))
        
        logger.info(
            f"Browser pool initialized with max_browsers={max_browsers}, "
            f"idle_timeout={idle_timeout}s, "
            f"max_memory={self.max_memory_percent}%, "
            f"max_cpu={self.max_cpu_percent}%, "
            f"monitor_interval={self.monitor_interval}s"
        )
    
    async def start(self):
        """Start the browser pool and monitoring tasks"""
        logger.info("Starting browser pool")
        self.cleanup_task = asyncio.create_task(self._cleanup_task())
        self.monitor_task = asyncio.create_task(self._monitor_task())
    
    async def stop(self):
        """Stop the browser pool and clean up all resources"""
        logger.info("Stopping browser pool")
        
        # Cancel monitoring tasks
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
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
    
    def _get_browser_metrics(self, browser: BrowserInstance) -> Dict[str, float]:
        """Get resource usage for a browser instance"""
        metrics = {"memory_percent": 0.0, "cpu_percent": 0.0}
        
        if browser.process and browser.process.is_running():
            try:
                metrics["memory_percent"] = browser.process.memory_percent()
                metrics["cpu_percent"] = browser.process.cpu_percent(interval=1)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return metrics
    
    async def _monitor_task(self):
        """Monitor system and browser resource usage"""
        try:
            while True:
                await asyncio.sleep(self.monitor_interval)
                
                system_metrics = self._get_system_metrics()
                total_browser_cpu = 0.0
                total_browser_memory = 0.0
                browsers_to_restart = []
                
                # Check each browser's resource usage
                async with self.lock:
                    for browser_id, browser in self.browsers.items():
                        try:
                            metrics = self._get_browser_metrics(browser)
                            total_browser_cpu += metrics["cpu_percent"]
                            total_browser_memory += metrics["memory_percent"]
                            
                            # Check if browser needs restart
                            if (metrics["cpu_percent"] > self.max_cpu_percent or 
                                metrics["memory_percent"] > self.max_memory_percent):
                                logger.warning(
                                    f"Browser {browser_id} using high resources: "
                                    f"CPU={metrics['cpu_percent']:.1f}%, "
                                    f"Memory={metrics['memory_percent']:.1f}%"
                                )
                                browsers_to_restart.append(browser_id)
                                
                        except Exception as e:
                            logger.error(f"Error monitoring browser {browser_id}: {str(e)}")
                            browsers_to_restart.append(browser_id)
                
                # Attempt recovery for problematic browsers
                for browser_id in browsers_to_restart:
                    await self._recover_browser(browser_id)
                
                # Check system resource usage
                if system_metrics["memory_percent"] > self.memory_threshold:
                    logger.warning(
                        f"System memory usage high ({system_metrics['memory_percent']:.1f}%), "
                        "cleaning up idle browsers"
                    )
                    await self._cleanup_idle_browsers()
                
                # Log overall usage
                logger.info(
                    f"Resource usage - System: Memory={system_metrics['memory_percent']:.1f}%, "
                    f"CPU={system_metrics['cpu_percent']:.1f}%, "
                    f"Browsers: Memory={total_browser_memory:.1f}%, "
                    f"CPU={total_browser_cpu:.1f}%"
                )
        
        except asyncio.CancelledError:
            logger.info("Monitor task cancelled")
            raise
        
        except Exception as e:
            logger.error(f"Error in monitor task: {str(e)}", exc_info=True)
    
    async def _recover_browser(self, browser_id: str):
        """
        Attempt to recover a problematic browser instance
        
        Args:
            browser_id: ID of the browser to recover
        """
        if browser_id not in self.browsers:
            return
            
        browser = self.browsers[browser_id]
        
        for attempt in range(self.max_recovery_attempts):
            try:
                logger.info(f"Recovery attempt {attempt + 1} for browser {browser_id}")
                
                # Try graceful cleanup first
                await self.close_browser(browser_id)
                
                # Create a new browser instance
                new_browser = BrowserInstance(browser_id)
                await new_browser.initialize()
                
                # Restore contexts if possible
                for context_id in browser.contexts.keys():
                    try:
                        await new_browser.create_context(context_id)
                        logger.info(f"Restored context {context_id} in browser {browser_id}")
                    except Exception as e:
                        logger.error(f"Failed to restore context {context_id}: {str(e)}")
                
                self.browsers[browser_id] = new_browser
                logger.info(f"Successfully recovered browser {browser_id}")
                return
                
            except Exception as e:
                logger.error(f"Recovery attempt {attempt + 1} failed: {str(e)}")
                await asyncio.sleep(self.recovery_delay * (attempt + 1))
        
        logger.error(f"Failed to recover browser {browser_id} after {self.max_recovery_attempts} attempts")
        # Remove the browser from the pool
        if browser_id in self.browsers:
            del self.browsers[browser_id]
    
    async def _cleanup_idle_browsers(self):
        """Clean up idle browser instances"""
        now = time.time()
        to_close = []
        
        async with self.lock:
            # Sort browsers by last used time
            sorted_browsers = sorted(
                self.browsers.items(),
                key=lambda x: x[1].last_used
            )
            
            # Keep at least one browser instance
            for browser_id, browser in sorted_browsers[1:]:
                if now - browser.last_used > self.idle_timeout:
                    to_close.append(browser_id)
        
        if to_close:
            logger.info(f"Cleaning up {len(to_close)} idle browsers")
            for browser_id in to_close:
                await self.close_browser(browser_id)
    
    async def _cleanup_task(self):
        """Background task to clean up idle browsers"""
        try:
            while True:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_idle_browsers()
        
        except asyncio.CancelledError:
            logger.info("Cleanup task cancelled")
            raise
        
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}", exc_info=True)
    
    async def get_browser(self) -> BrowserInstance:
        """
        Get a browser instance from the pool
        
        Returns:
            A browser instance
            
        Raises:
            MCPBrowserException if resource limits are exceeded
        """
        async with self.lock:
            # Check system resources
            metrics = self._get_system_metrics()
            if metrics["memory_percent"] > self.memory_threshold:
                # Try to free up resources
                await self._cleanup_idle_browsers()
                
                # Check again
                metrics = self._get_system_metrics()
                if metrics["memory_percent"] > self.memory_threshold:
                    raise MCPBrowserException(
                        error_code=ErrorCode.RESOURCE_LIMIT_EXCEEDED,
                        message="System memory usage too high to create new browser"
                    )
            
            # Check if we can create a new browser
            if len(self.browsers) >= self.max_browsers:
                # Find the least recently used browser
                browser_id = min(self.browsers.items(), key=lambda x: x[1].last_used)[0]
                logger.info(f"Reusing existing browser {browser_id}")
                browser = self.browsers[browser_id]
            else:
                # Create a new browser
                browser_id = str(uuid.uuid4())
                browser = BrowserInstance(browser_id)
                self.browsers[browser_id] = browser
                
                # Initialize the browser
                try:
                    await browser.initialize()
                except Exception as e:
                    del self.browsers[browser_id]
                    raise MCPBrowserException(
                        error_code=ErrorCode.BROWSER_INITIALIZATION_FAILED,
                        message=f"Failed to initialize browser: {str(e)}",
                        original_exception=e
                    )
            
            browser.last_used = time.time()
            return browser
    
    async def close_browser(self, browser_id: str):
        """
        Close a browser instance and clean up its resources
        
        Args:
            browser_id: ID of the browser to close
        """
        if browser_id not in self.browsers:
            logger.warning(f"Browser {browser_id} not found in pool")
            return
            
        browser = self.browsers[browser_id]
        try:
            await browser.close()
        finally:
            # Always remove from pool, even if close fails
            del self.browsers[browser_id]
            
        logger.info(f"Removed browser {browser_id} from pool, {len(self.browsers)} browsers remaining")

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