#!/bin/bash
# Test script for MCP WebSocket event subscription

set -e

# Configuration
HOST=${HOST:-"localhost"}
PORT=${PORT:-8765}
ENDPOINT="ws://$HOST:$PORT/ws/browser/events"

# Check if colorama is available for colored output
if python3 -c "import colorama" &>/dev/null; then
    HAS_COLORAMA=1
else
    HAS_COLORAMA=0
    echo "Notice: colorama not installed. Running without color."
fi

# Color output function
color_echo() {
    local COLOR=$1
    local TEXT=$2
    
    if [ "$HAS_COLORAMA" -eq 1 ]; then
        python3 -c "import colorama; colorama.init(); print($COLOR + '$TEXT' + colorama.Style.RESET_ALL)" | cat
    else
        echo "$TEXT"
    fi
}

# Start the WebSocket server if it's not already running
if ! nc -z localhost $PORT 2>/dev/null; then
    color_echo "colorama.Fore.YELLOW" "Starting WebSocket server..."
    python3 src/test_websocket.py & 
    WEBSOCKET_PID=$!
    
    # Wait for server to start
    sleep 2
    
    color_echo "colorama.Fore.GREEN" "WebSocket server started with PID $WEBSOCKET_PID"
    
    # Register cleanup handler
    cleanup() {
        color_echo "colorama.Fore.YELLOW" "Stopping WebSocket server..."
        kill $WEBSOCKET_PID 2>/dev/null || true
        color_echo "colorama.Fore.GREEN" "WebSocket server stopped"
        exit 0
    }
    
    trap cleanup INT TERM EXIT
fi

# Check if server is running
if ! nc -z localhost $PORT 2>/dev/null; then
    color_echo "colorama.Fore.RED" "WebSocket server is not running!"
    exit 1
fi

# Run client test with websocket-client and colorama
color_echo "colorama.Fore.BLUE" "Testing WebSocket event subscription..."

# Run the client and pipe to cat to prevent interactive issues
python3 src/test_event_subscription.py -s $ENDPOINT -t "PAGE,DOM" -f "*example.com*" | cat

# If we started the server, we'll clean it up on exit via the trap
if [ -n "$WEBSOCKET_PID" ]; then
    color_echo "colorama.Fore.GREEN" "Test completed successfully. Press Ctrl+C to exit."
    # Keep the script running so the server stays alive for manual testing
    while true; do
        sleep 1
    done
else
    color_echo "colorama.Fore.GREEN" "Test completed successfully."
fi 