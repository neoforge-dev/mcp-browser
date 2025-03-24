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
        self.contexts: Dict[str, Any] = {}
        self.last_used = time.time()
        self.browser = None
        self.is_closing = False
        
        logger.info(f"Created browser instance {self.id}")
    
    async def initialize(self):
        """Initialize the browser instance"""
        # In a real implementation, this would launch Playwright browser
        logger.info(f"Initializing browser instance {self.id}")
        self.browser = {"id": self.id, "status": "ready"}
        return self.browser
    
    async def create_context(self, context_id: str, **kwargs) -> Dict[str, Any]:
        """
        Create a new browser context
        
        Args:
            context_id: Unique identifier for this context
            **kwargs: Additional context options
            
        Returns:
            Browser context object
        """
        logger.info(f"Creating context {context_id} in browser {self.id}")
        
        # In a real implementation, this would create a Playwright context
        context = {
            "id": context_id,
            "browser_id": self.id,
            "created_at": time.time(),
            "options": kwargs,
            "pages": []
        }
        
        self.contexts[context_id] = context
        self.last_used = time.time()
        
        return context
    
    async def close_context(self, context_id: str):
        """
        Close a browser context
        
        Args:
            context_id: ID of the context to close
        """
        if context_id not in self.contexts:
            logger.warning(f"Context {context_id} not found in browser {self.id}")
            return
            
        logger.info(f"Closing context {context_id} in browser {self.id}")
        # In a real implementation, this would close the Playwright context
        
        del self.contexts[context_id]
        self.last_used = time.time()
    
    async def close(self):
        """Close the browser instance and all its contexts"""
        if self.is_closing:
            return
            
        self.is_closing = True
        logger.info(f"Closing browser instance {self.id}")
        
        # Close all contexts
        for context_id in list(self.contexts.keys()):
            await self.close_context(context_id)
        
        # In a real implementation, this would close the Playwright browser
        self.browser = None
        
        logger.info(f"Browser instance {self.id} closed")

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
        self.lock = asyncio.Lock()
        
        logger.info(f"Browser pool initialized with max_browsers={max_browsers}, idle_timeout={idle_timeout}s")
    
    async def start(self):
        """Start the browser pool and cleanup task"""
        logger.info("Starting browser pool")
        self.cleanup_task = asyncio.create_task(self._cleanup_task())
    
    async def stop(self):
        """Stop the browser pool and close all browsers"""
        logger.info("Stopping browser pool")
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all browsers
        async with self.lock:
            for browser_id in list(self.browsers.keys()):
                await self.close_browser(browser_id)
        
        logger.info("Browser pool stopped")
    
    async def get_browser(self) -> BrowserInstance:
        """
        Get a browser instance from the pool
        
        Returns:
            A browser instance
        """
        async with self.lock:
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
                await browser.initialize()
            
            browser.last_used = time.time()
            return browser
    
    async def close_browser(self, browser_id: str):
        """
        Close a browser instance
        
        Args:
            browser_id: ID of the browser to close
        """
        if browser_id not in self.browsers:
            logger.warning(f"Browser {browser_id} not found in pool")
            return
            
        browser = self.browsers[browser_id]
        await browser.close()
        
        del self.browsers[browser_id]
        
        logger.info(f"Removed browser {browser_id} from pool, {len(self.browsers)} browsers remaining")
    
    async def _cleanup_task(self):
        """Background task to clean up idle browsers"""
        try:
            while True:
                await asyncio.sleep(60)  # Check every minute
                
                now = time.time()
                to_close = []
                
                async with self.lock:
                    for browser_id, browser in self.browsers.items():
                        if now - browser.last_used > self.idle_timeout:
                            to_close.append(browser_id)
                
                if to_close:
                    logger.info(f"Closing {len(to_close)} idle browsers")
                    
                    for browser_id in to_close:
                        await self.close_browser(browser_id)
        
        except asyncio.CancelledError:
            logger.info("Cleanup task cancelled")
            raise
        
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}", exc_info=True)

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