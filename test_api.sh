#!/bin/bash
# Test the MCP Browser API endpoints

set -e

# Determine the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create output directories if they don't exist
mkdir -p "$SCRIPT_DIR/output/screenshots"
mkdir -p "$SCRIPT_DIR/output/dom"
mkdir -p "$SCRIPT_DIR/output/css"

# Check if the server is running
if ! curl -s "http://localhost:7665/api/status" > /dev/null; then
    echo "Error: MCP Browser server is not running on port 7665."
    echo "Please start the server first with ./run.sh"
    exit 1
fi

# Navigate to the script directory
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Install test dependencies if not already installed
if ! python -c "import requests" 2>/dev/null; then
    echo "Installing test dependencies..."
    python -m pip install requests
fi

# Run the API tests
echo "Running API tests..."
python src/test_api.py

# Get the exit code
EXIT_CODE=$?

# Output based on success or failure
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All tests passed successfully!"
else
    echo "❌ Some tests failed. Check the output above for details."
fi

exit $EXIT_CODE 