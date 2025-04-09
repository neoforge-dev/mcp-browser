#!/bin/bash
set -e

# Log startup message
echo "Starting services..."

# Ensure necessary directories exist and have correct permissions
mkdir -p /run/dbus
chown -R messagebus:messagebus /run/dbus

# Start D-Bus system service
echo "Starting D-Bus system daemon..."
dbus-daemon --system --fork
DBUS_PID=$(pidof dbus-daemon)
echo "D-Bus system daemon started with PID $DBUS_PID"
sleep 1 # Give D-Bus a moment

# Kill any existing Xvfb processes
if [ -f /tmp/.X99-lock ]; then
    echo "Removing existing X11 lock file"
    rm -f /tmp/.X99-lock
fi

# Start Xvfb
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1280x720x24 > /dev/null 2>&1 &
XVFB_PID=$!

# Give Xvfb time to start
echo "Waiting for Xvfb to initialize..."
sleep 2

# Check if Xvfb is running
if ! ps -p $XVFB_PID > /dev/null; then
    echo "Error: Xvfb failed to start"
    if [ -n "$DBUS_PID" ] && ps -p $DBUS_PID > /dev/null; then kill $DBUS_PID; fi
    exit 1
fi

echo "Xvfb started with PID $XVFB_PID"

# Set up a trap to ensure clean shutdown of all services
trap "echo 'Shutting down...'; kill $XVFB_PID; if [ -n \"$DBUS_PID\" ] && ps -p $DBUS_PID > /dev/null; then kill $DBUS_PID; fi; exit" SIGINT SIGTERM

# Determine if we're in test mode
if [ "$RUN_TESTS" = "true" ]; then
    echo "Running tests..."
    cd /app
    
    # Add connectivity checks
    echo "\n--- Pinging example.com ---"
    ping -c 3 example.com || echo "Ping failed!"
    echo "--- End Ping ---\n"
    
    echo "\n--- Curling http://example.com ---"
    curl -v http://example.com || echo "Curl failed!"
    echo "--- End Curl ---\n"
    
    pytest /app/tests -v -vv --capture=no
else
    echo "Starting MCP Browser application..."
    cd /app
    python3 src/main.py
fi

# Clean up Xvfb
kill $XVFB_PID 