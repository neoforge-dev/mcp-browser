#!/usr/bin/env python3
"""
WebSocket client for testing the WebSocket event subscription feature.
This connects to the test WebSocket server, subscribes to events, and displays them.
"""

import asyncio
import json
import logging
import sys
import argparse
import websockets
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Parse command line arguments
parser = argparse.ArgumentParser(description="WebSocket Event Subscription Test Client")
parser.add_argument(
    "--url", 
    default="ws://localhost:8765/ws/events", 
    help="WebSocket URL for the event endpoint"
)
parser.add_argument(
    "--types", 
    default="PAGE,NETWORK,CONSOLE,DOM", 
    help="Comma-separated list of event types to subscribe to"
)
parser.add_argument(
    "--test-events", 
    action="store_true", 
    help="Generate test events periodically"
)
parser.add_argument(
    "--timeout", 
    type=int, 
    default=0, 
    help="Exit after this many seconds (0 means run indefinitely)"
)

args = parser.parse_args()

async def subscribe_to_events(ws, event_types):
    """Subscribe to events"""
    subscription_data = {
        "action": "subscribe",
        "event_types": event_types.split(","),
    }
    
    await ws.send(json.dumps(subscription_data))
    response = await ws.recv()
    
    logger.info(f"Subscription response: {response}")
    return json.loads(response)

async def generate_test_event(ws, event_type="PAGE", event_name="test.event"):
    """Generate a test event"""
    test_event_data = {
        "action": "test_event",
        "event_type": event_type,
        "event_name": event_name,
        "data": {
            "message": f"Test event: {event_type}.{event_name}",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "details": {
                "test": True,
                "generated_at": str(datetime.now())
            }
        }
    }
    
    await ws.send(json.dumps(test_event_data))
    response = await ws.recv()
    
    logger.info(f"Test event response: {response}")

async def print_event(event_data):
    """Format and print an event"""
    try:
        event_json = json.loads(event_data)
        event_type = event_json.get("type", "DEFAULT")
        event_name = event_json.get("event", "unknown")
        timestamp = datetime.fromtimestamp(event_json.get("timestamp", 0)).strftime("%H:%M:%S")
        data = event_json.get("data", {})
        
        # Print the event
        print(f"[{timestamp}] {event_type}.{event_name}")
        
        # Format the data nicely
        if isinstance(data, dict):
            for key, value in data.items():
                # Handle nested data
                if isinstance(value, dict) and len(value) > 0:
                    print(f"  {key}:")
                    for subkey, subvalue in value.items():
                        print(f"    {subkey}: {subvalue}")
                else:
                    print(f"  {key}: {value}")
        else:
            print(f"  {data}")
        
        print("-" * 80)
    except Exception as e:
        logger.error(f"Error processing event: {e}")
        logger.error(f"Raw event data: {event_data}")

async def test_event_generator(ws):
    """Generate test events periodically"""
    if not args.test_events:
        return
        
    event_types = ["PAGE", "DOM", "CONSOLE", "NETWORK"]
    event_names = {
        "PAGE": ["page.load", "page.navigate", "page.error"],
        "DOM": ["dom.mutation", "dom.attribute", "dom.child"],
        "CONSOLE": ["console.log", "console.error", "console.warning"],
        "NETWORK": ["network.request", "network.response", "network.error"]
    }
    
    logger.info("Starting test event generator")
    
    while True:
        # Cycle through event types
        for event_type in event_types:
            # Cycle through event names for this type
            for event_name in event_names.get(event_type, ["test.event"]):
                try:
                    await generate_test_event(ws, event_type, event_name)
                    await asyncio.sleep(2)  # Wait between events
                except Exception as e:
                    logger.error(f"Error generating test event: {e}")
                    return

async def timeout_handler():
    """Handle timeout and exit gracefully"""
    if args.timeout > 0:
        logger.info(f"Will exit after {args.timeout} seconds")
        await asyncio.sleep(args.timeout)
        logger.info("Timeout reached, exiting")
        print(f"\nTest completed after {args.timeout} seconds")
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
            
            # Receive welcome message
            welcome = await ws.recv()
            logger.info(f"Welcome message: {welcome}")
            
            # Subscribe to events
            subscription = await subscribe_to_events(ws, args.types)
            subscription_id = subscription.get("subscription_id", "unknown")
            logger.info(f"Subscribed to events with ID: {subscription_id}")
            
            # Start test event generator if requested
            if args.test_events:
                asyncio.create_task(test_event_generator(ws))
            
            # Print initial message
            print("\n" + "=" * 80)
            print("WebSocket Event Subscription Test Client")
            print(f"Connected to: {args.url}")
            print(f"Subscribed to event types: {args.types}")
            if args.test_events:
                print("Test event generation: Enabled")
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