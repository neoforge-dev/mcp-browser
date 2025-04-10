#!/usr/bin/env python3
"""
Rate Limiter for MCP Browser

This module provides rate limiting functionality using a sliding window algorithm.
"""

import time
import logging
import asyncio
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from collections import defaultdict
import re
from fastapi import Request, HTTPException
from error_handler import MCPBrowserException, ErrorCode
import functools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("rate-limiter")

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    requests: int
    window: int  # Window size in seconds
    exempt_with_token: bool = False

class RateLimitExceeded(MCPBrowserException):
    """Exception raised when rate limit is exceeded"""
    def __init__(self, limit: int, reset_time: int):
        super().__init__(
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message=f"Rate limit exceeded. Limit is {limit} requests. Reset in {reset_time} seconds."
        )
        self.limit = limit
        self.reset_time = reset_time

class SlidingWindowCounter:
    """Implements sliding window rate limiting algorithm"""
    
    def __init__(self, window_size: int):
        """
        Initialize sliding window counter
        
        Args:
            window_size: Window size in seconds
        """
        self.window_size = window_size
        self.requests: List[float] = []
        self._cleanup_lock = asyncio.Lock()
    
    async def add_request(self) -> bool:
        """
        Add a request to the counter
        
        Returns:
            True if request was added, False if window is full
        """
        now = time.time()
        
        async with self._cleanup_lock:
            # Clean up old requests
            cutoff = now - self.window_size
            self.requests = [ts for ts in self.requests if ts > cutoff]
            
            # Add new request
            self.requests.append(now)
        
        return True
    
    def get_count(self) -> int:
        """Get current request count in window"""
        now = time.time()
        cutoff = now - self.window_size
        return sum(1 for ts in self.requests if ts > cutoff)
    
    def time_to_reset(self) -> int:
        """Get seconds until window resets"""
        if not self.requests:
            return 0
        
        now = time.time()
        oldest = min(self.requests)
        return max(0, int(oldest + self.window_size - now))

class RateLimiter:
    """Rate limiter for FastAPI endpoints"""
    
    def __init__(self):
        """Initialize rate limiter"""
        self.limiters: Dict[str, Dict[str, SlidingWindowCounter]] = defaultdict(dict)
        self.configs: Dict[str, RateLimitConfig] = {}
        self._cleanup_task: Optional[asyncio.Task] = None  # Initialize as None
        self._cleanup_lock = asyncio.Lock()
    
    def parse_limit(self, limit: str) -> Tuple[int, int]:
        """
        Parse rate limit string (e.g., "100/minute", "10/second")
        
        Args:
            limit: Rate limit string
            
        Returns:
            Tuple of (requests, window_size_in_seconds)
        """
        match = re.match(r"(\d+)/(\w+)", limit)
        if not match:
            raise ValueError(f"Invalid rate limit format: {limit}")
        
        requests = int(match.group(1))
        unit = match.group(2).lower()
        
        if unit == "second":
            window = 1
        elif unit == "minute":
            window = 60
        elif unit == "hour":
            window = 3600
        elif unit == "day":
            window = 86400
        else:
            raise ValueError(f"Invalid time unit: {unit}")
        
        return requests, window
    
    def get_client_id(self, request: Request) -> str:
        """
        Get client identifier from request
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client identifier string
        """
        # Try X-Forwarded-For first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Fall back to client host
        return request.client.host if request.client else "unknown"
    
    def is_authenticated(self, request: Request) -> bool:
        """
        Check if request is authenticated
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if request has valid auth token
        """
        auth = request.headers.get("Authorization")
        return bool(auth and auth.startswith("Bearer "))
    
    async def is_rate_limited(
        self,
        endpoint: str,
        client_id: str,
        config: RateLimitConfig
    ) -> Tuple[bool, int, int]:
        """
        Check if request should be rate limited
        
        Args:
            endpoint: Endpoint identifier
            client_id: Client identifier
            config: Rate limit configuration
            
        Returns:
            Tuple of (is_limited, remaining, reset_time)
        """
        # Get or create limiter for this client
        if client_id not in self.limiters[endpoint]:
            self.limiters[endpoint][client_id] = SlidingWindowCounter(config.window)
        
        limiter = self.limiters[endpoint][client_id]
        
        # Check current count
        count = limiter.get_count()
        if count >= config.requests:
            return True, 0, limiter.time_to_reset()
        
        # Add request
        await limiter.add_request()
        
        return False, config.requests - count - 1, limiter.time_to_reset()
    
    async def cleanup_old_entries(self):
        """Clean up expired entries periodically"""
        try:
            while True:
                await asyncio.sleep(60)  # Run every minute
                
                async with self._cleanup_lock:
                    now = time.time()
                    logger.debug("Running rate limiter cleanup...")
                    cleaned_endpoints = 0
                    cleaned_clients = 0
                    for endpoint in list(self.limiters.keys()):
                        config = self.configs.get(endpoint)
                        if not config:
                            logger.warning(f"No config found for endpoint {endpoint} during cleanup, skipping.")
                            continue
                        
                        window_cutoff = now - config.window
                        clients_to_remove = []
                        for client_id, limiter in self.limiters[endpoint].items():
                            # Clean requests within the limiter first
                            async with limiter._cleanup_lock:
                                limiter.requests = [ts for ts in limiter.requests if ts > window_cutoff]

                            # Check if limiter is now empty and past its window
                            if not limiter.requests: 
                                # We can remove this client limiter if it's empty
                                clients_to_remove.append(client_id)
                                cleaned_clients += 1

                        for client_id in clients_to_remove:
                           del self.limiters[endpoint][client_id]
                        
                        # If endpoint dict is empty, remove it too
                        if not self.limiters[endpoint]:
                            del self.limiters[endpoint]
                            cleaned_endpoints += 1
                    
                    if cleaned_clients > 0 or cleaned_endpoints > 0:
                        logger.info(f"Rate limiter cleanup finished. Removed {cleaned_clients} client entries and {cleaned_endpoints} endpoint entries.")
                    else:
                         logger.debug("Rate limiter cleanup finished. No entries removed.")

        except asyncio.CancelledError:
            logger.info("Cleanup task cancelled")
        
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}", exc_info=True)

    async def start_cleanup_task(self):
        """Starts the background cleanup task if it's not already running."""
        if self._cleanup_task is None or self._cleanup_task.done():
            try:
                loop = asyncio.get_running_loop()
                self._cleanup_task = loop.create_task(self.cleanup_old_entries())
                logger.info("Rate limiter cleanup task started.")
            except RuntimeError:
                 logger.error("Failed to start rate limiter cleanup task: No running event loop.")
        else:
            logger.debug("Cleanup task already running.")
            
    async def stop_cleanup_task(self):
         """Stops the background cleanup task."""
         if self._cleanup_task and not self._cleanup_task.done():
             self._cleanup_task.cancel()
             try:
                 await self._cleanup_task
             except asyncio.CancelledError:
                 logger.info("Rate limiter cleanup task successfully stopped.")
             self._cleanup_task = None
         else:
             logger.debug("Cleanup task not running or already stopped.")

    def limit(self, limit: str, exempt_with_token: bool = False):
        """
        Rate limiting decorator
        
        Args:
            limit: Rate limit string (e.g., "100/minute")
            exempt_with_token: Whether to exempt authenticated requests
            
        Returns:
            Decorator function
        """
        requests, window = self.parse_limit(limit)
        
        def decorator(func):
            # Store config for this endpoint
            endpoint = f"{func.__module__}.{func.__name__}" # Use a more unique identifier
            if endpoint in self.configs:
                 logger.warning(f"Overwriting rate limit config for endpoint: {endpoint}")
            self.configs[endpoint] = RateLimitConfig(
                requests=requests,
                window=window,
                exempt_with_token=exempt_with_token
            )
            logger.debug(f"Registered rate limit for {endpoint}: {requests}/{window}s, exempt_with_token={exempt_with_token}")

            # REMOVED: Do not start cleanup task here
            # if not self._cleanup_task:
            #     self._cleanup_task = asyncio.create_task(self.cleanup_old_entries())
            
            @functools.wraps(func) # Preserve original function metadata
            async def wrapper(*args, **kwargs):
                # Find the Request object in args or kwargs
                request: Optional[Request] = None
                if 'request' in kwargs:
                    request = kwargs['request']
                else:
                    for arg in args:
                        if isinstance(arg, Request):
                            request = arg
                            break
                
                if not request:
                     logger.error(f"Rate limit decorator applied to endpoint {endpoint} without a Request argument.")
                     # Fallback: Proceed without rate limiting or raise an error
                     # Raising an error is safer during development
                     raise TypeError(f"Endpoint {endpoint} must accept 'request: Request' as an argument for rate limiting.")
                     # return await func(*args, **kwargs) 

                config = self.configs[endpoint]
                
                # Check for auth exemption
                if config.exempt_with_token and self.is_authenticated(request):
                    logger.debug(f"Authenticated request to {endpoint}, rate limit exempted.")
                    return await func(*args, **kwargs)

                client_id = self.get_client_id(request)
                
                is_limited, remaining, reset = await self.is_rate_limited(
                    endpoint, client_id, config
                )
                
                # Store headers in request state for middleware to pick up
                request.state.rate_limit_headers = {
                    "X-RateLimit-Limit": str(config.requests),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset)
                }

                if is_limited:
                    logger.warning(f"Rate limit exceeded for {client_id} on endpoint {endpoint}")
                    raise RateLimitExceeded(limit=config.requests, reset_time=reset)
                
                logger.debug(f"Request from {client_id} to {endpoint} allowed. Remaining: {remaining}")
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator