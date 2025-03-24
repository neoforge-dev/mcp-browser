#!/bin/bash
# Simple test for the MCP Browser API endpoints

set -e

# Determine the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if the server is running
if ! curl -s "http://localhost:7665/api/status" > /dev/null; then
    echo "Error: MCP Browser server is not running on port 7665."
    echo "Please start the server first with ./run.sh or 'uv run src/main.py'"
    exit 1
fi

# Navigate to the script directory
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Run the simple test with pipe to cat to avoid interactive issues
echo "Running simple API test..."
python src/simple_test.py | cat

# Get the exit code (use PIPESTATUS to get the exit code of the python command, not cat)
EXIT_CODE=${PIPESTATUS[0]}

# Output based on success or failure
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Basic test passed successfully!"
else
    echo "❌ Basic test failed. Check the output above for details."
fi

exit $EXIT_CODE 