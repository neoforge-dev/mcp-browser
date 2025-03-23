#!/bin/bash
set -e

# Check for Xvfb
if ! command -v Xvfb &> /dev/null; then
    echo "Xvfb not found. You may need to install it."
    echo "On macOS: brew install xquartz"
    echo "On Linux: sudo apt-get install xvfb"
    
    read -p "Continue without Xvfb? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    echo "Continuing without Xvfb. Some features may not work properly."
    export DISPLAY=:0
else
    # Start Xvfb if not already running
    if ! ps aux | grep -v grep | grep -q "Xvfb :99"; then
        echo "Starting Xvfb..."
        Xvfb :99 -screen 0 1280x1024x24 -ac +extension GLX +render -noreset &
        XVFB_PID=$!
        export DISPLAY=:99
        
        # Give Xvfb time to start
        sleep 2
        
        # Check if Xvfb is running
        if ! ps -p $XVFB_PID > /dev/null; then
            echo "Error: Xvfb failed to start"
            exit 1
        fi
        
        echo "Xvfb started with PID $XVFB_PID"
        
        # Set up a trap to ensure clean shutdown
        trap "echo 'Shutting down Xvfb'; kill $XVFB_PID; exit" SIGINT SIGTERM EXIT
    else
        echo "Xvfb is already running"
        export DISPLAY=:99
    fi
fi

# Check for virtual environment and create if needed
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
uv pip install -e .

# Install Playwright browsers if needed
if [ ! -d "$HOME/.cache/ms-playwright" ]; then
    echo "Installing Playwright browsers..."
    python -m playwright install
fi

# Set MCP_SECRET if not already set
if [ -z "$MCP_SECRET" ]; then
    export MCP_SECRET="test_secret_key"
    echo "Set MCP_SECRET to a test value. In production, use a proper secret."
fi

# Start the MCP browser
echo "Starting MCP Browser on http://localhost:7665"
cd src
python main.py 