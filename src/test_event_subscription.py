#!/usr/bin/env python3
"""
Test script for MCP Browser WebSocket event subscriptions
This script connects to the MCP Browser server's WebSocket event endpoint,
subscribes to browser events, and displays them in real-time.
"""

import asyncio
import json
import sys
import argparse
import logging
import websockets
from datetime import datetime

# Try to import colorama for colored output
try:
    from colorama import Fore, Style, init
    # Initialize colorama
    init()
    HAS_COLORAMA = True
except ImportError:
    # Fallback if colorama is not available
    print("Warning: colorama not found. Using plain text output.")
    HAS_COLORAMA = False
    
    # Create dummy color objects
    class DummyColors:
        def __getattr__(self, name):
            return ""
    
    Fore = DummyColors()
    Style = DummyColors()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Event type colors
EVENT_COLORS = {
    "PAGE": Fore.BLUE,
    "NETWORK": Fore.CYAN,
    "CONSOLE": Fore.GREEN,
    "DOM": Fore.MAGENTA,
    "ERROR": Fore.RED,
    "DEFAULT": Fore.WHITE,
}

# Parse command line arguments
parser = argparse.ArgumentParser(description="MCP Browser Event Subscription Test")
parser.add_argument(
    "--url", 
    default="ws://localhost:7665/ws/browser/events", 
    help="WebSocket URL for the browser events endpoint"
)
parser.add_argument(
    "--types", 
    default="PAGE,NETWORK,CONSOLE,DOM", 
    help="Comma-separated list of event types to subscribe to"
)
parser.add_argument(
    "--filter-url", 
    default="", 
    help="Filter events by URL pattern"
)
parser.add_argument(
    "--target-url", 
    default="", 
    help="URL to navigate to after connecting"
)
parser.add_argument(
    "--timeout", 
    type=int, 
    default=0, 
    help="Exit after this many seconds (0 means run indefinitely)"
)

args = parser.parse_args()

async def subscribe_to_events(ws, event_types, url_pattern=None):
    """Subscribe to browser events"""
    subscription_data = {
        "action": "subscribe",
        "event_types": event_types.split(","),
    }
    
    if url_pattern:
        subscription_data["filters"] = {"url_pattern": url_pattern}
    
    await ws.send(json.dumps(subscription_data))
    response = await ws.recv()
    
    logger.info(f"Subscription response: {response}")
    return json.loads(response)

async def print_event(event_data):
    """Format and print an event"""
    try:
        event_json = json.loads(event_data)
        timestamp = datetime.fromtimestamp(event_json.get("timestamp", 0)).strftime("%H:%M:%S")
        event_type = event_json.get("type", "DEFAULT")
        event_name = event_json.get("event", "unknown")
        page_id = event_json.get("page_id", "unknown")
        data = event_json.get("data", {})
        
        # Get the appropriate color
        color = EVENT_COLORS.get(event_type, EVENT_COLORS["DEFAULT"])
        
        # Print the event
        print(f"{color}[{timestamp}] {event_type}.{event_name} {Style.RESET_ALL}")
        
        # Format the data nicely
        if isinstance(data, dict):
            for key, value in data.items():
                # Handle nested data for better display
                if isinstance(value, dict) and len(value) > 0:
                    print(f"  {key}:")
                    for subkey, subvalue in value.items():
                        if isinstance(subvalue, str) and len(subvalue) > 100:
                            subvalue = subvalue[:100] + "..."
                        print(f"    {subkey}: {subvalue}")
                else:
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + "..."
                    print(f"  {key}: {value}")
        else:
            print(f"  {data}")
        
        print("-" * 80)
    except Exception as e:
        logger.error(f"Error processing event: {e}")
        logger.error(f"Raw event data: {event_data}")

async def timeout_handler():
    """Handle timeout and exit gracefully"""
    if args.timeout > 0:
        logger.info(f"Will exit after {args.timeout} seconds")
        await asyncio.sleep(args.timeout)
        logger.info("Timeout reached, exiting")
        print(f"\n{Fore.YELLOW}Test completed after {args.timeout} seconds{Style.RESET_ALL}")
        sys.exit(0)

async def main():
    """Main function"""
    try:
        logger.info(f"Connecting to WebSocket at {args.url}")
        
        # Start timeout handler if specified
        if args.timeout > 0:
            asyncio.create_task(timeout_handler())
            
        async with websockets.connect(args.url) as ws:
            logger.info("Connected to WebSocket server")
            
            # Subscribe to events
            subscription = await subscribe_to_events(ws, args.types, args.filter_url)
            subscription_id = subscription.get("subscription_id", "unknown")
            logger.info(f"Subscribed to events with ID: {subscription_id}")
            
            # Navigate to target URL if provided
            if args.target_url:
                navigate_msg = {
                    "action": "execute",
                    "command": "navigate",
                    "params": {"url": args.target_url}
                }
                await ws.send(json.dumps(navigate_msg))
                logger.info(f"Navigating to {args.target_url}")
            
            # Print initial message
            print("\n" + "=" * 80)
            print(f"{Fore.YELLOW}MCP Browser Event Subscription Test{Style.RESET_ALL}")
            print(f"Listening for events of types: {args.types}")
            if args.filter_url:
                print(f"Filtering by URL pattern: {args.filter_url}")
            if args.timeout > 0:
                print(f"Will exit after {args.timeout} seconds")
            print("=" * 80 + "\n")
            
            # Receive events
            while True:
                message = await ws.recv()
                await print_event(message)
                
    except websockets.exceptions.ConnectionClosed:
        logger.error("WebSocket connection closed")
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScript terminated by user")
        sys.exit(0) 