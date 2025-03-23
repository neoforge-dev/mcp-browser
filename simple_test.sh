#!/bin/bash
set -e

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

# Set MCP_SECRET if not already set
if [ -z "$MCP_SECRET" ]; then
    export MCP_SECRET="test_secret_key"
    echo "Set MCP_SECRET to a test value. In production, use a proper secret."
fi

# Set headless mode for Playwright (no display needed)
export PLAYWRIGHT_BROWSERS_PATH=0
export PLAYWRIGHT_DRIVER_URL=""
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

# Start the MCP browser in headless-only mode
echo "Starting MCP Browser on http://localhost:7665 in headless mode"
cd src
python main.py 