#!/usr/bin/env python3

"""
MCP Browser WebSocket Event Subscription Example

This example demonstrates how to:
1. Connect to the MCP Browser WebSocket event endpoint
2. Subscribe to specific browser events
3. Process and handle the events in real-time
4. Unsubscribe when no longer needed

Requirements:
- websockets
- asyncio
- json

Usage:
python event_subscription_example.py
"""

import asyncio
import json
import signal
import sys
import time
import argparse
from uuid import uuid4
import websockets

# Default configuration
DEFAULT_WS_URL = "ws://localhost:7665/ws/browser/events"
DEFAULT_API_URL = "http://localhost:7665"
DEFAULT_TEST_URL = "https://example.com"
DEFAULT_TIMEOUT = 60  # seconds

# Event colors for terminal output
COLORS = {
    "PAGE": "\033[94m",    # Blue
    "DOM": "\033[92m",     # Green
    "CONSOLE": "\033[93m", # Yellow
    "NETWORK": "\033[91m", # Red
    "DEFAULT": "\033[0m",  # Reset
}

class EventSubscriptionClient:
    def __init__(self, ws_url, timeout=60):
        self.ws_url = ws_url
        self.timeout = timeout
        self.subscriptions = {}
        self.running = False
        self.websocket = None
        self.client_id = None
        
    async def connect(self):
        """Connect to the WebSocket server"""
        try:
            self.websocket = await websockets.connect(self.ws_url)
            print(f"Connected to {self.ws_url}")
            # Wait for the welcome message
            welcome = await self.websocket.recv()
            welcome_data = json.loads(welcome)
            if welcome_data.get("type") == "connection":
                self.client_id = welcome_data.get("client_id")
                print(f"Received welcome message: {welcome_data.get('message')}")
                print(f"Client ID: {self.client_id}")
            
            # Set a timeout handler
            if self.timeout > 0:
                asyncio.create_task(self._timeout_handler())
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    async def subscribe(self, event_types, filters=None):
        """Subscribe to specific event types with optional filters"""
        if not self.websocket:
            print("Not connected. Call connect() first.")
            return None
        
        subscription_request = {
            "action": "subscribe",
            "event_types": event_types
        }
        
        if filters:
            subscription_request["filters"] = filters
            
        await self.websocket.send(json.dumps(subscription_request))
        response = await self.websocket.recv()
        response_data = json.loads(response)
        
        if "subscription_id" in response_data:
            subscription_id = response_data["subscription_id"]
            self.subscriptions[subscription_id] = {
                "event_types": event_types,
                "filters": filters
            }
            print(f"Subscribed to {', '.join(event_types)} with ID: {subscription_id}")
            return subscription_id
        else:
            print(f"Subscription failed: {response_data}")
            return None
    
    async def unsubscribe(self, subscription_id):
        """Unsubscribe from a specific subscription"""
        if not self.websocket:
            print("Not connected. Call connect() first.")
            return False
            
        if subscription_id not in self.subscriptions:
            print(f"Subscription ID {subscription_id} not found.")
            return False
            
        unsubscribe_request = {
            "action": "unsubscribe",
            "subscription_id": subscription_id
        }
        
        await self.websocket.send(json.dumps(unsubscribe_request))
        response = await self.websocket.recv()
        response_data = json.loads(response)
        
        if response_data.get("success", False):
            del self.subscriptions[subscription_id]
            print(f"Unsubscribed from {subscription_id}")
            return True
        else:
            print(f"Unsubscribe failed: {response_data}")
            return False
    
    async def list_subscriptions(self):
        """List all active subscriptions"""
        if not self.websocket:
            print("Not connected. Call connect() first.")
            return []
            
        list_request = {
            "action": "list"
        }
        
        await self.websocket.send(json.dumps(list_request))
        response = await self.websocket.recv()
        response_data = json.loads(response)
        
        if "subscriptions" in response_data:
            return response_data["subscriptions"]
        else:
            print(f"List subscriptions failed: {response_data}")
            return []
    
    async def listen(self):
        """Listen for events and process them"""
        if not self.websocket:
            print("Not connected. Call connect() first.")
            return
            
        self.running = True
        try:
            while self.running:
                message = await self.websocket.recv()
                event = json.loads(message)
                # Only process events with a proper type
                if "type" in event and event["type"] not in ["connection", "subscription"]:
                    self._process_event(event)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")
        except Exception as e:
            print(f"Error in listen loop: {e}")
        finally:
            self.running = False
    
    def _process_event(self, event):
        """Process a received event"""
        event_type = event.get("type", "UNKNOWN")
        event_name = event.get("event", "unknown")
        timestamp = event.get("timestamp", time.time())
        
        # Format timestamp
        time_str = time.strftime("%H:%M:%S", time.localtime(timestamp))
        
        # Get color for event type
        color = COLORS.get(event_type, COLORS["DEFAULT"])
        reset = COLORS["DEFAULT"]
        
        # Print event information
        print(f"{color}[{time_str}] {event_type}.{event_name}{reset}")
        
        # Print event data
        if "data" in event:
            data_str = json.dumps(event["data"], indent=2)
            print(f"  Data: {data_str}")
        
        # Print page ID if available
        if "page_id" in event:
            print(f"  Page: {event['page_id']}")
        
        print("-" * 40)
    
    async def close(self):
        """Close the WebSocket connection"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            print("Connection closed")
    
    async def _timeout_handler(self):
        """Handle timeout to automatically close the connection"""
        await asyncio.sleep(self.timeout)
        if self.running:
            print(f"Timeout after {self.timeout} seconds")
            await self.close()
            
async def navigate_to_page(api_url, url):
    """Navigate the browser to a specific URL using the API"""
    import aiohttp
    
    navigate_url = f"{api_url}/api/browser/navigate?url={url}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(navigate_url) as response:
                result = await response.json()
                if result.get("success", False):
                    print(f"Successfully navigated to: {url}")
                else:
                    print(f"Navigation failed: {result}")
    except Exception as e:
        print(f"Navigation error: {e}")
        print("Continuing without navigation...")


async def main():
    parser = argparse.ArgumentParser(description="MCP Browser WebSocket Event Subscription Example")
    parser.add_argument("--ws-url", default=DEFAULT_WS_URL, help="WebSocket URL")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="API URL")
    parser.add_argument("--test-url", default=DEFAULT_TEST_URL, help="URL to navigate to")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Timeout in seconds")
    args = parser.parse_args()
    
    # Extract the base URL from the WebSocket URL to use for API calls if not specified
    if args.ws_url and args.ws_url.startswith("ws://") and "--api-url" not in sys.argv:
        ws_parts = args.ws_url.split("/")
        if len(ws_parts) >= 3:
            args.api_url = f"http://{ws_parts[2]}"
            print(f"Using API URL derived from WebSocket URL: {args.api_url}")
    
    # Setup signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(client)))
    
    # Create client
    client = EventSubscriptionClient(args.ws_url, args.timeout)
    
    # Connect to WebSocket server
    if not await client.connect():
        return 1
    
    # Subscribe to events
    subscription_id = await client.subscribe([
        "PAGE", "NETWORK", "CONSOLE", "DOM"
    ])
    
    if not subscription_id:
        await client.close()
        return 1
    
    # Navigate to test URL to generate events
    print(f"Navigating to {args.test_url}...")
    await navigate_to_page(args.api_url, args.test_url)
    
    # Listen for events
    print("Listening for events. Press Ctrl+C to exit.")
    await client.listen()
    
    # Cleanup
    await client.close()
    return 0

async def shutdown(client):
    """Shutdown gracefully"""
    print("Shutting down...")
    await client.close()
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    await asyncio.gather(*tasks, return_exceptions=True)
    asyncio.get_event_loop().stop()

if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 