#!/bin/bash
set -e

echo "Starting services..."

# Setup D-Bus Environment
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/dbus/system_bus_socket"

# Create D-Bus directory if it doesn't exist
mkdir -p /run/dbus
chown -R messagebus:messagebus /run/dbus

# Start D-Bus system daemon
echo "Starting D-Bus system daemon..."
rm -f /run/dbus/pid # Ensure clean start
dbus-daemon --system --nopidfile --nofork &
DBUS_PID=$!
echo "D-Bus system daemon started with PID $DBUS_PID"
sleep 1 # Give D-Bus a moment

# Trap signals to clean up D-Bus
cleanup() {
    echo "Caught signal, cleaning up D-Bus and Xvfb..."
    # Stop Xvfb first if it's running
    if [ -n "$XVFB_PID" ] && kill -0 $XVFB_PID 2>/dev/null; then
        echo "Stopping Xvfb (PID $XVFB_PID)..."
        kill $XVFB_PID
        wait $XVFB_PID 2>/dev/null
        echo "Xvfb stopped."
    fi
    # Stop D-Bus if it's running
    if kill -0 $DBUS_PID 2>/dev/null; then
        echo "Stopping D-Bus system daemon (PID $DBUS_PID)..."
        kill $DBUS_PID
        wait $DBUS_PID 2>/dev/null # Wait for it to stop
        echo "D-Bus stopped."
    else
        echo "D-Bus already stopped or PID not found."
    fi
    exit 0 # Exit trap handler
}
trap cleanup SIGTERM SIGINT SIGHUP

# --- Xvfb Section Start: Re-enabled ---
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
# --- Xvfb Section End: Re-enabled ---

# Determine if we're in test mode
if [ "$RUN_TESTS" = "true" ]; then
    echo "Running tests..."
    # Run connectivity checks first
    echo "\n--- Pinging example.com ---"
    ping -c 3 example.com || echo "Ping failed, continuing..."
    echo "--- End Ping ---\n"
    echo "\n--- Curling http://example.com ---"
    curl -v http://example.com || echo "Curl failed, continuing..."
    echo "--- End Curl ---\n"
    # Execute tests
    python3 -m pytest
    TEST_EXIT_CODE=$?
    # Clean up D-Bus and Xvfb
    if [ -n "$XVFB_PID" ] && ps -p $XVFB_PID > /dev/null; then 
        echo "Stopping Xvfb daemon..."
        kill $XVFB_PID
    fi 
    if [ -n "$DBUS_PID" ] && ps -p $DBUS_PID > /dev/null; then 
        echo "Stopping D-Bus daemon..."
        kill $DBUS_PID
    fi 
    exit $TEST_EXIT_CODE
else
    echo "Starting main application..."
    # Execute the main application (CMD in Dockerfile)
    exec python3 src/main.py
fi

# This part should not be reached if exec is used correctly above
echo "Script finished unexpectedly."
exit 1