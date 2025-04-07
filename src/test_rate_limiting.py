#!/usr/bin/env python3
"""
Test Rate Limiting for MCP Browser

This module tests the rate limiting functionality for API endpoints.
"""

import asyncio
import logging
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from typing import Dict, List, Optional, Any

from rate_limiter import RateLimiter, RateLimitConfig, RateLimitExceeded
from error_handler import MCPBrowserException, ErrorCode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test-rate-limiting")

# Test app
app = FastAPI()
rate_limiter = RateLimiter()

@app.get("/test")
@rate_limiter.limit("10/minute")
async def test_endpoint():
    return {"status": "ok"}

@app.get("/auth-test")
@rate_limiter.limit("5/minute", exempt_with_token=True)
async def auth_test_endpoint(request: Request):
    return {"status": "ok"}

def test_basic_rate_limiting():
    """Test basic rate limiting functionality"""
    logger.info("Testing basic rate limiting...")
    
    client = TestClient(app)
    
    # Make requests up to the limit
    for i in range(10):
        response = client.get("/test")
        assert response.status_code == 200, f"Request {i+1} failed"
        
        # Check rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        
        remaining = int(response.headers["X-RateLimit-Remaining"])
        assert remaining == 9 - i, f"Wrong remaining count: {remaining}"
    
    # Next request should fail
    response = client.get("/test")
    assert response.status_code == 429
    assert response.json()["error_code"] == ErrorCode.RATE_LIMIT_EXCEEDED.value

def test_authenticated_rate_limiting():
    """Test rate limiting with authentication exemption"""
    logger.info("Testing authenticated rate limiting...")
    
    client = TestClient(app)
    
    # Test without auth token (should be limited)
    for i in range(5):
        response = client.get("/auth-test")
        assert response.status_code == 200, f"Request {i+1} failed"
    
    response = client.get("/auth-test")
    assert response.status_code == 429
    
    # Test with auth token (should bypass limit)
    headers = {"Authorization": "Bearer test-token"}
    for _ in range(10):  # Try more requests than normal limit
        response = client.get("/auth-test", headers=headers)
        assert response.status_code == 200, "Authenticated request failed"

def test_burst_protection():
    """Test protection against burst requests"""
    logger.info("Testing burst protection...")
    
    client = TestClient(app)
    
    # Send burst of concurrent requests
    async def make_requests():
        tasks = []
        for _ in range(20):  # Try double the limit
            tasks.append(client.get("/test"))
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    responses = asyncio.run(make_requests())
    
    # Count successful and failed requests
    success_count = sum(1 for r in responses if getattr(r, "status_code", 0) == 200)
    fail_count = sum(1 for r in responses if getattr(r, "status_code", 0) == 429)
    
    assert success_count == 10, f"Expected 10 successful requests, got {success_count}"
    assert fail_count == 10, f"Expected 10 failed requests, got {fail_count}"

def test_sliding_window():
    """Test sliding window rate limiting"""
    logger.info("Testing sliding window rate limiting...")
    
    client = TestClient(app)
    
    # Make requests up to limit
    for _ in range(10):
        response = client.get("/test")
        assert response.status_code == 200
    
    # Wait for half the window
    asyncio.run(asyncio.sleep(30))
    
    # Should allow half the requests
    for i in range(5):
        response = client.get("/test")
        assert response.status_code == 200, f"Request {i+1} should be allowed"
    
    # Next request should fail
    response = client.get("/test")
    assert response.status_code == 429

def test_custom_limits():
    """Test custom rate limit configurations"""
    logger.info("Testing custom rate limits...")
    
    # Create test endpoint with custom limits
    @app.get("/custom")
    @rate_limiter.limit("2/second")
    async def custom_endpoint():
        return {"status": "ok"}
    
    client = TestClient(app)
    
    # Test second-based limit
    response = client.get("/custom")
    assert response.status_code == 200
    
    response = client.get("/custom")
    assert response.status_code == 200
    
    response = client.get("/custom")
    assert response.status_code == 429
    
    # Wait a second
    asyncio.run(asyncio.sleep(1))
    
    # Should be allowed again
    response = client.get("/custom")
    assert response.status_code == 200

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 