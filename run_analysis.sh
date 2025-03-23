#!/bin/bash
# Run the MCP Browser with all frontend analysis APIs enabled

# Default port
PORT=7665

# Banner function
function print_banner() {
    echo "==============================================="
    echo "  MCP Browser - Frontend Analysis Platform"
    echo "  Version 0.2.0"
    echo "==============================================="
    echo ""
}

# Help function
function print_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -p, --port PORT    Specify the port to run on (default: 7665)"
    echo "  -h, --help         Show this help message"
    echo ""
    echo "Available API Endpoints:"
    echo "  - /api/screenshots/capture   Capture screenshots with various options"
    echo "  - /api/dom/extract           Extract and analyze DOM structure"
    echo "  - /api/css/analyze           Analyze CSS properties of elements"
    echo "  - /api/accessibility/test    Test for accessibility issues"
    echo "  - /api/responsive/test       Test responsive behavior across viewports"
    echo ""
    echo "Example: $0 --port 8080"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--port)
            PORT="$2"
            shift
            shift
            ;;
        -h|--help)
            print_banner
            print_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            print_help
            exit 1
            ;;
    esac
done

# Create required directories
mkdir -p output/screenshots
mkdir -p output/dom
mkdir -p output/css
mkdir -p output/accessibility
mkdir -p output/responsive

# Print banner
print_banner

# Check for Python and uv
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found"
    exit 1
fi

if ! command -v uv &> /dev/null; then
    echo "Error: The uv package manager is required but not found"
    echo "Install with: pip install uv"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Set environment variables
export SERVER_PORT=$PORT

# Run the server
echo "Starting MCP Browser on port $PORT..."
echo "Press Ctrl+C to stop the server"
echo ""

uv run src/main.py

# Capture Ctrl+C and clean up
trap 'echo "Shutting down MCP Browser..."; exit 0' INT 