#!/bin/bash
set -e

# Check if .env file exists and source it
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
elif [ -f .env.example ]; then
    echo "No .env file found. Using .env.example as a template..."
    cp .env.example .env
    echo "Please update the .env file with your actual secrets and configuration."
    echo "Press Enter to continue with example values or Ctrl+C to abort."
    read -r
    export $(grep -v '^#' .env | xargs)
fi

# Check if MCP_SECRET is set
if [ -z "$MCP_SECRET" ]; then
    echo "WARNING: MCP_SECRET environment variable is not set."
    echo "Some functionality may be limited."
    echo "You can set it in your .env file or using: export MCP_SECRET=your_secret_key"
    
    # Generate a random secret if needed
    MCP_SECRET=$(openssl rand -hex 16)
    echo "Generated a random MCP_SECRET for this session: $MCP_SECRET"
    export MCP_SECRET
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "docker-compose is not installed. Please install it first."
    exit 1
fi

# Build and start the MCP browser container
echo "Building and starting MCP browser..."
echo "The server will be available at http://localhost:7665"

# Use cat to prevent interactive output issues
docker-compose up --build "$@" | cat

# Handle exit
echo "MCP browser stopped." 