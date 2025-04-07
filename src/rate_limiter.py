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
        self._cleanup_task = None
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
                    for endpoint in list(self.limiters.keys()):
                        config = self.configs.get(endpoint)
                        if not config:
                            continue
                        
                        for client_id in list(self.limiters[endpoint].keys()):
                            limiter = self.limiters[endpoint][client_id]
                            if not limiter.requests or max(limiter.requests) < now - config.window:
                                del self.limiters[endpoint][client_id]
                        
                        if not self.limiters[endpoint]:
                            del self.limiters[endpoint]
        
        except asyncio.CancelledError:
            logger.info("Cleanup task cancelled")
        
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}", exc_info=True)
    
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
            endpoint = func.__name__
            self.configs[endpoint] = RateLimitConfig(
                requests=requests,
                window=window,
                exempt_with_token=exempt_with_token
            )
            
            # Start cleanup task if not running
            if not self._cleanup_task:
                self._cleanup_task = asyncio.create_task(self.cleanup_old_entries())
            
            async def wrapper(request: Request, *args, **kwargs):
                config = self.configs[endpoint]
                
                # Check for auth exemption
                if config.exempt_with_token and self.is_authenticated(request):
                    return await func(request, *args, **kwargs)
                
                # Get client ID and check rate limit
                client_id = self.get_client_id(request)
                is_limited, remaining, reset_time = await self.is_rate_limited(
                    endpoint, client_id, config
                )
                
                # Set rate limit headers
                request.state.rate_limit_headers = {
                    "X-RateLimit-Limit": str(config.requests),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_time)
                }
                
                if is_limited:
                    raise RateLimitExceeded(config.requests, reset_time)
                
                return await func(request, *args, **kwargs)
            
            return wrapper
        
        return decorator 