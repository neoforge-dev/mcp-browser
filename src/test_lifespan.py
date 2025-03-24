#!/usr/bin/env python3
"""
Test file to verify lifespan events are working correctly.
This is a simplified version of the main application with lifespan events.
"""

import asyncio
import logging
from typing import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test-lifespan")

# App state
app_state = {}

# Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown events"""
    global app_state
    
    # Startup: Initialize services
    app_state["initialized"] = True
    app_state["start_time"] = asyncio.get_event_loop().time()
    
    logger.info("Test server started with lifespan event")
    
    yield  # Run the application
    
    # Shutdown: Cleanup resources
    app_state["shutdown_time"] = asyncio.get_event_loop().time()
    app_state["uptime"] = app_state["shutdown_time"] - app_state["start_time"]
    
    logger.info(f"Test server shut down. Uptime: {app_state['uptime']:.2f} seconds")

# Create FastAPI app with lifespan
app = FastAPI(
    title="Lifespan Test",
    description="Test server for lifespan events",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Lifespan Test Server",
        "initialized": app_state.get("initialized", False),
        "uptime": asyncio.get_event_loop().time() - app_state.get("start_time", 0)
    }

@app.get("/state")
async def state():
    """Get app state"""
    return app_state

# Main entry point
if __name__ == "__main__":
    uvicorn.run("test_lifespan:app", host="0.0.0.0", port=8766, reload=False) 