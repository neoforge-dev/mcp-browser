#!/bin/bash
set -e

# Log startup message
echo "Starting Xvfb and MCP Browser..."

# Start Xvfb
Xvfb :99 -screen 0 1280x1024x24 -ac +extension GLX +render -noreset &
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

# Start the MCP browser application
echo "Starting MCP Browser application..."
cd /app
python src/main.py

# If the application exits, also kill Xvfb
kill $XVFB_PID 