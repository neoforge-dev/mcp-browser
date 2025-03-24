#!/bin/bash
# Test script for MCP Browser Event Subscriptions

# Set variables
API_URL="http://localhost:7665"
TEST_URL="file://$(pwd)/src/test_events.html"
WS_URL="ws://localhost:7665/ws/browser/events"
OUTPUT_DIR="./test_output"
EVENT_TYPES="PAGE,NETWORK,CONSOLE,DOM"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create output directory if it doesn't exist
mkdir -p $OUTPUT_DIR

echo -e "${YELLOW}========================================================${NC}"
echo -e "${YELLOW}MCP Browser Event Subscriptions Test${NC}"
echo -e "${YELLOW}========================================================${NC}"
echo "API URL: $API_URL"
echo "Test URL: $TEST_URL"
echo "WebSocket URL: $WS_URL"
echo -e "${YELLOW}========================================================${NC}"

# Check if API is running
echo -e "${BLUE}Checking API status...${NC}"
STATUS=$(curl -s $API_URL/api/status)
echo "API Status: $STATUS"

if [[ $STATUS != *"\"status\":\"ok\""* ]]; then
    echo -e "${RED}Error: API is not running or not responding correctly.${NC}"
    exit 1
fi

# Install required dependencies if not already installed
echo -e "${BLUE}Checking dependencies...${NC}"

if ! pip show websockets >/dev/null 2>&1; then
    echo "Installing websockets..."
    pip install websockets
fi

if ! pip show colorama >/dev/null 2>&1; then
    echo "Installing colorama..."
    pip install colorama
fi

echo -e "${GREEN}Dependencies checked.${NC}"

# Function to test WebSocket event subscriptions
test_websocket_events() {
    echo -e "${BLUE}Testing WebSocket event subscriptions...${NC}"
    echo "Launching event subscription client..."
    echo "Target URL: $TEST_URL"
    
    # Start the event subscription client with the given parameters
    python3 src/test_event_subscription.py --url $WS_URL --types $EVENT_TYPES --target-url $TEST_URL
}

# Check if we should run in test mode or interactive mode
if [ "$1" == "--test" ]; then
    # Test mode: navigate to test URL, collect events for 10 seconds, then exit
    echo -e "${BLUE}Running in test mode (automatic)...${NC}"
    echo "Will navigate to test page and collect events for 10 seconds"
    python3 src/test_event_subscription.py --url $WS_URL --types $EVENT_TYPES --target-url $TEST_URL --timeout 10
else
    # Interactive mode: user can see events in real-time and interact with the test page
    echo -e "${BLUE}Running in interactive mode...${NC}"
    echo "Press Ctrl+C to exit"
    test_websocket_events
fi

echo -e "${GREEN}Test completed.${NC}"
exit 0 