#!/usr/bin/env python3
"""
Simple WebSocket server for testing event subscriptions.
This demonstrates the WebSocket event subscriptions feature with a minimal implementation.
"""

import asyncio
import json
import logging
import uuid
import time
from datetime import datetime
from typing import Dict, List, Set, Any, Optional, AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from enum import Enum
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Define event types and models
class EventType(str, Enum):
    """Types of browser events"""
    PAGE = "PAGE"
    DOM = "DOM"
    CONSOLE = "CONSOLE"
    NETWORK = "NETWORK"

# Global variables
active_connections: Set[WebSocket] = set()
event_connections: Dict[str, WebSocket] = {}
active_subscriptions: Dict[str, Dict[str, Any]] = {}
subscription_handlers: Dict[str, List[str]] = {
    "PAGE": [],
    "DOM": [],
    "CONSOLE": [],
    "NETWORK": [],
}

# Forward declare the event generator function signature
async def event_generator():
    """Generate simulated events for testing"""
    pass  # Actual implementation below

# Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown events"""
    # Startup: Create task for event generator
    event_task = asyncio.create_task(event_generator())
    logger.info("WebSocket Event Test Server started")
    
    yield  # Run the application
    
    # Shutdown: Cancel the event generator task
    event_task.cancel()
    try:
        await event_task
    except asyncio.CancelledError:
        logger.info("Event generator task cancelled")

# Create FastAPI app with lifespan
app = FastAPI(
    title="WebSocket Event Test",
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

# Event handler functions
async def broadcast_event(event_type: str, event_name: str, data: Dict[str, Any]):
    """Broadcast an event to all subscribed clients"""
    event = {
        "type": event_type,
        "event": event_name,
        "timestamp": time.time(),
        "data": data
    }
    
    # Convert event to JSON string
    event_json = json.dumps(event)
    
    # Find subscriptions for this event type
    for subscription_id in subscription_handlers.get(event_type, []):
        if subscription_id in active_subscriptions:
            client_id = active_subscriptions[subscription_id]["client_id"]
            
            # Check if client is still connected
            if client_id in event_connections:
                try:
                    await event_connections[client_id].send_text(event_json)
                    logger.info(f"Event {event_name} sent to client {client_id}")
                except Exception as e:
                    logger.error(f"Error sending event to client {client_id}: {e}")

async def add_subscription(client_id: str, subscription_id: str, event_types: List[str], filters: Optional[Dict[str, Any]] = None):
    """Add a new subscription for a client"""
    # Store subscription details
    active_subscriptions[subscription_id] = {
        "client_id": client_id,
        "event_types": event_types,
        "filters": filters,
        "created_at": time.time()
    }
    
    # Register subscription for each event type
    for event_type in event_types:
        if event_type in subscription_handlers:
            subscription_handlers[event_type].append(subscription_id)
    
    logger.info(f"Added subscription {subscription_id} for client {client_id}, event types: {event_types}")

async def remove_subscription(subscription_id: str):
    """Remove a subscription"""
    if subscription_id in active_subscriptions:
        # Get event types for this subscription
        event_types = active_subscriptions[subscription_id].get("event_types", [])
        
        # Remove from subscription handlers
        for event_type in event_types:
            if event_type in subscription_handlers and subscription_id in subscription_handlers[event_type]:
                subscription_handlers[event_type].remove(subscription_id)
        
        # Remove from active subscriptions
        del active_subscriptions[subscription_id]
        logger.info(f"Removed subscription {subscription_id}")
        return True
    
    return False

# Actual implementation of event generator task
async def event_generator():
    """Generate simulated events for testing"""
    event_types = ["PAGE", "DOM", "CONSOLE", "NETWORK"]
    event_names = {
        "PAGE": ["page.load", "page.navigate", "page.error"],
        "DOM": ["dom.mutation", "dom.attribute", "dom.child"],
        "CONSOLE": ["console.log", "console.error", "console.warning"],
        "NETWORK": ["network.request", "network.response", "network.error"]
    }
    
    while True:
        # Only generate events if there are active subscriptions
        if active_subscriptions:
            # Select random event type
            event_type = event_types[int(time.time() * 10) % len(event_types)]
            
            # Check if there are any subscribers for this event type
            if subscription_handlers.get(event_type, []):
                # Select random event name
                names = event_names.get(event_type, ["test.event"])
                event_name = names[int(time.time() * 100) % len(names)]
                
                # Generate event data
                data = {
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "message": f"Simulated {event_type}.{event_name} event",
                    "value": round(time.time() % 100, 2),
                    "details": {
                        "random": uuid.uuid4().hex[:8],
                        "counter": int(time.time()) % 1000
                    }
                }
                
                # Broadcast event
                await broadcast_event(event_type, event_name, data)
                logger.debug(f"Generated event: {event_type}.{event_name}")
        
        # Wait before generating next event
        await asyncio.sleep(2)

# API endpoints
@app.get("/api/status")
async def get_status():
    """Get server status"""
    return {
        "status": "ok",
        "version": "0.1.0",
        "timestamp": time.time(),
        "connections": len(active_connections),
        "subscriptions": len(active_subscriptions)
    }

# WebSocket endpoint for browser events
@app.websocket("/ws/events")
async def websocket_browser_events(websocket: WebSocket):
    """WebSocket endpoint for browser events"""
    await websocket.accept()
    
    # Generate a unique client ID
    client_id = f"client_{str(uuid.uuid4())}"
    
    # Add to active connections
    active_connections.add(websocket)
    event_connections[client_id] = websocket
    
    # Send welcome message
    await websocket.send_text(json.dumps({
        "type": "connection",
        "client_id": client_id,
        "message": "Connected to WebSocket Event Test Server",
        "timestamp": time.time()
    }))
    
    logger.info(f"Client {client_id} connected")
    
    try:
        # Process incoming messages
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                # Parse JSON message
                message = json.loads(data)
                action = message.get("action", "")
                
                # Process action
                if action == "subscribe":
                    # Subscribe to events
                    event_types = message.get("event_types", [])
                    filters = message.get("filters")
                    
                    # Generate subscription ID
                    subscription_id = f"sub_{str(uuid.uuid4())}"
                    
                    # Add subscription
                    await add_subscription(client_id, subscription_id, event_types, filters)
                    
                    # Send confirmation
                    await websocket.send_text(json.dumps({
                        "type": "subscription",
                        "subscription_id": subscription_id,
                        "event_types": event_types,
                        "filters": filters,
                        "timestamp": time.time()
                    }))
                    
                elif action == "unsubscribe":
                    # Unsubscribe from events
                    subscription_id = message.get("subscription_id", "")
                    
                    # Remove subscription
                    success = await remove_subscription(subscription_id)
                    
                    # Send confirmation
                    await websocket.send_text(json.dumps({
                        "type": "unsubscription",
                        "subscription_id": subscription_id,
                        "success": success,
                        "timestamp": time.time()
                    }))
                    
                elif action == "list":
                    # List active subscriptions for this client
                    client_subscriptions = {
                        sub_id: sub_data
                        for sub_id, sub_data in active_subscriptions.items()
                        if sub_data.get("client_id") == client_id
                    }
                    
                    # Send subscription list
                    await websocket.send_text(json.dumps({
                        "type": "subscription_list",
                        "subscriptions": client_subscriptions,
                        "timestamp": time.time()
                    }))
                    
                elif action == "test_event":
                    # Generate a test event for debugging
                    event_type = message.get("event_type", "PAGE")
                    event_name = message.get("event_name", "test.event")
                    event_data = message.get("data", {"message": "Test event"})
                    
                    # Broadcast event
                    await broadcast_event(event_type, event_name, event_data)
                    
                    # Send confirmation
                    await websocket.send_text(json.dumps({
                        "type": "event_generated",
                        "event_type": event_type,
                        "event_name": event_name,
                        "timestamp": time.time()
                    }))
                    
                else:
                    # Unknown action
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": f"Unknown action: {action}",
                        "timestamp": time.time()
                    }))
                    
            except json.JSONDecodeError:
                # Invalid JSON
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": "Invalid JSON message",
                    "timestamp": time.time()
                }))
                
    except WebSocketDisconnect:
        # Client disconnected
        logger.info(f"Client {client_id} disconnected")
        
        # Remove from active connections
        active_connections.discard(websocket)
        
        if client_id in event_connections:
            del event_connections[client_id]
        
        # Remove client subscriptions
        client_subscriptions = [
            sub_id for sub_id, sub_data in active_subscriptions.items()
            if sub_data.get("client_id") == client_id
        ]
        
        for subscription_id in client_subscriptions:
            await remove_subscription(subscription_id)

# New endpoint for browser events at the expected path
@app.websocket("/ws/browser/events")
async def websocket_browser_events_alias(websocket: WebSocket):
    """WebSocket endpoint for browser events (alias for compatibility)"""
    await websocket.accept()
    
    # Generate a unique client ID
    client_id = f"client_{str(uuid.uuid4())}"
    
    # Add to active connections
    active_connections.add(websocket)
    event_connections[client_id] = websocket
    
    # Send welcome message
    await websocket.send_text(json.dumps({
        "type": "connection",
        "client_id": client_id,
        "message": "Connected to MCP Browser Event Subscription Service",
        "timestamp": time.time()
    }))
    
    logger.info(f"Client {client_id} connected to browser events endpoint")
    
    try:
        # Process incoming messages
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                # Parse JSON message
                message = json.loads(data)
                action = message.get("action", "")
                
                # Process action
                if action == "subscribe":
                    # Subscribe to events
                    event_types = message.get("event_types", [])
                    filters = message.get("filters")
                    
                    # Generate subscription ID
                    subscription_id = f"sub_{str(uuid.uuid4())}"
                    
                    # Add subscription
                    await add_subscription(client_id, subscription_id, event_types, filters)
                    
                    # Send confirmation
                    await websocket.send_text(json.dumps({
                        "type": "subscription",
                        "subscription_id": subscription_id,
                        "event_types": event_types,
                        "filters": filters,
                        "timestamp": time.time()
                    }))
                    
                elif action == "unsubscribe":
                    # Unsubscribe from events
                    subscription_id = message.get("subscription_id", "")
                    
                    # Remove subscription
                    success = await remove_subscription(subscription_id)
                    
                    # Send confirmation
                    await websocket.send_text(json.dumps({
                        "type": "unsubscription",
                        "subscription_id": subscription_id,
                        "success": success,
                        "timestamp": time.time()
                    }))
                    
                elif action == "list":
                    # List active subscriptions for this client
                    client_subscriptions = {
                        sub_id: sub_data
                        for sub_id, sub_data in active_subscriptions.items()
                        if sub_data.get("client_id") == client_id
                    }
                    
                    # Send subscription list
                    await websocket.send_text(json.dumps({
                        "type": "subscription_list",
                        "subscriptions": client_subscriptions,
                        "timestamp": time.time()
                    }))
                
                elif action == "execute":
                    # Handle execute command (for navigation, etc.)
                    command = message.get("command", "")
                    params = message.get("params", {})
                    
                    # Log the command (in a real implementation, this would actually execute it)
                    logger.info(f"Received execute command: {command} with params: {params}")
                    
                    # Send confirmation
                    await websocket.send_text(json.dumps({
                        "type": "command_executed",
                        "command": command,
                        "success": True,
                        "message": f"Command {command} acknowledged (simulation)",
                        "timestamp": time.time()
                    }))
                    
                    # If this is a navigation command, generate a simulated PAGE event
                    if command == "navigate" and "url" in params:
                        # Simulate a page load event
                        await asyncio.sleep(0.5)  # Simulate loading time
                        
                        page_event_data = {
                            "url": params["url"],
                            "title": f"Page Title for {params['url']}",
                            "status": 200,
                            "timestamp": time.time()
                        }
                        
                        # Broadcast a PAGE event
                        await broadcast_event("PAGE", "page.load", page_event_data)
                
                elif action == "test_event":
                    # Generate a test event for debugging
                    event_type = message.get("event_type", "PAGE")
                    event_name = message.get("event_name", "test.event")
                    event_data = message.get("data", {"message": "Test event"})
                    
                    # Broadcast event
                    await broadcast_event(event_type, event_name, event_data)
                    
                    # Send confirmation
                    await websocket.send_text(json.dumps({
                        "type": "event_generated",
                        "event_type": event_type,
                        "event_name": event_name,
                        "timestamp": time.time()
                    }))
                    
                else:
                    # Unknown action
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": f"Unknown action: {action}",
                        "timestamp": time.time()
                    }))
                    
            except json.JSONDecodeError:
                # Invalid JSON
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": "Invalid JSON message",
                    "timestamp": time.time()
                }))
                
    except WebSocketDisconnect:
        # Client disconnected
        logger.info(f"Client {client_id} disconnected")
        
        # Remove from active connections
        active_connections.discard(websocket)
        
        if client_id in event_connections:
            del event_connections[client_id]
        
        # Remove client subscriptions
        client_subscriptions = [
            sub_id for sub_id, sub_data in active_subscriptions.items()
            if sub_data.get("client_id") == client_id
        ]
        
        for subscription_id in client_subscriptions:
            await remove_subscription(subscription_id)

# Main entry point
if __name__ == "__main__":
    # Use reload=False to prevent frequent reloads during development
    uvicorn.run("test_websocket:app", host="0.0.0.0", port=8765, reload=False) 