# MCP Browser WebSocket Event Subscriptions

This document describes the WebSocket event subscription feature in MCP Browser, which allows real-time monitoring of browser events.

## Overview

The WebSocket event subscription system enables clients to:

1. Connect to the MCP Browser server via WebSockets
2. Subscribe to specific types of browser events
3. Receive real-time notifications when these events occur
4. Filter events based on various criteria

This creates a powerful foundation for building real-time monitoring, debugging, and automation tools that can react to browser activity.

## Event Types

The system supports the following event types:

| Event Type | Description                             | Examples                                      |
|------------|-----------------------------------------|-----------------------------------------------|
| PAGE       | Page lifecycle events                   | Navigation, loads, errors                     |
| DOM        | DOM mutations and changes               | Element additions/removals, attribute changes |
| CONSOLE    | Browser console messages                | Logs, warnings, errors                        |
| NETWORK    | Network requests, responses, and errors | XHR, fetch, resource loading                  |

## WebSocket Endpoints

### Browser Events Endpoint

- URL: `/ws/browser/events`
- Description: Main WebSocket endpoint for subscribing to browser events

## Subscribing to Events

To subscribe to events, send a JSON message to the WebSocket with:

```json
{
  "action": "subscribe",
  "event_types": ["PAGE", "NETWORK", "CONSOLE", "DOM"],
  "filters": {
    "url_pattern": "example\\.com"  // Optional URL pattern filter
  }
}
```

You'll receive a confirmation with a subscription ID:

```json
{
  "type": "subscription",
  "subscription_id": "sub_ce12596c-d74e-4cf6-a911-2534dfbcb773",
  "event_types": ["PAGE", "NETWORK", "CONSOLE", "DOM"],
  "filters": { "url_pattern": "example\\.com" },
  "timestamp": 1742765514.711262
}
```

## Receiving Events

Events are pushed to the client as JSON messages with this structure:

```json
{
  "type": "PAGE",
  "event": "page.load",
  "timestamp": 1742765514.711472,
  "page_id": "page_123456",
  "data": {
    "url": "https://example.com",
    "lifecycle": "load",
    "timestamp": 1742765514.711472
  }
}
```

## Event Filtering

Events can be filtered using:

- `url_pattern`: Regular expression to match the page URL
- `page_id`: Specific page ID to monitor

## Unsubscribing

To unsubscribe, send:

```json
{
  "action": "unsubscribe",
  "subscription_id": "sub_ce12596c-d74e-4cf6-a911-2534dfbcb773"
}
```

## Listing Active Subscriptions

To list your active subscriptions, send:

```json
{
  "action": "list"
}
```

## Example Usage Scenarios

1. **Real-time debugging**: Monitor console errors, network failures, and DOM changes
2. **Performance monitoring**: Track page load times, resource loading, and rendering performance
3. **Automation**: Trigger actions based on specific page events
4. **Testing**: Verify expected events occur in the correct sequence
5. **Analytics**: Collect detailed browsing behavior and performance data

## Testing

The repository includes test scripts to demonstrate this functionality:

1. `src/test_websocket.py`: A minimal WebSocket server that simulates browser events
2. `src/test_websocket_client.py`: A client that connects to the WebSocket server and displays events

To run the tests:

```bash
# Terminal 1: Start the WebSocket server
python src/test_websocket.py

# Terminal 2: Run the WebSocket client
python src/test_websocket_client.py --test-events
```

## Integration with MCP Browser

The WebSocket event subscription system is integrated with the MCP Browser's core functionality:

1. Real browser events are captured and transmitted through the WebSocket
2. Event handlers are automatically set up when pages are created
3. The system handles disconnections and subscription management gracefully
4. Events can be used by agent tools to enhance browser automation 