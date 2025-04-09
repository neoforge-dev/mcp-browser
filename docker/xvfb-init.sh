#!/bin/bash
set -e

# Log startup message
echo "Starting Xvfb and MCP Browser..."

# Kill any existing Xvfb processes
if [ -f /tmp/.X99-lock ]; then
    echo "Removing existing X11 lock file"
    rm -f /tmp/.X99-lock
fi

# Start Xvfb
Xvfb :99 -screen 0 1280x720x24 > /dev/null 2>&1 &
XVFB_PID=$!

# Give Xvfb time to start
echo "Waiting for Xvfb to initialize..."
sleep 2

# Check if Xvfb is running
if ! ps -p $XVFB_PID > /dev/null; then
    echo "Error: Xvfb failed to start"
    exit 1
fi

echo "Xvfb started with PID $XVFB_PID"

# Set up a trap to ensure clean shutdown
trap "echo 'Shutting down Xvfb and MCP Browser'; kill $XVFB_PID; exit" SIGINT SIGTERM

# Determine if we're in test mode
if [ "$RUN_TESTS" = "true" ]; then
    echo "Running tests..."
    cd /app
    pytest /app/tests -v -vv --capture=no
else
    echo "Starting MCP Browser application..."
    cd /app
    python3 src/main.py
fi

# Clean up Xvfb
kill $XVFB_PID 