#!/bin/bash

# Test script for MCP Browser Protocol Extensions
# This script tests the browser navigation, DOM manipulation, and visual analysis tools

set -e

# Set API base URL
API_URL=${API_URL:-"http://localhost:7665"}
TEST_URL="https://example.com"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to make API calls with query parameters
call_api() {
    local endpoint=$1
    local query_params=$2
    
    echo -e "${YELLOW}Testing: ${endpoint}${NC}"
    
    # Prepare query string if params provided
    local query_string=""
    if [ -n "$query_params" ]; then
        query_string="?$query_params"
    fi
    
    response=$(curl -s -X POST "${API_URL}${endpoint}${query_string}")
    
    if echo "$response" | grep -q "success\":true"; then
        echo -e "${GREEN}✅ Success: $endpoint${NC}"
    else
        echo -e "${RED}❌ Failed: $endpoint${NC}"
        echo "$response"
    fi
    
    # Create a safe filename by replacing slashes and other special chars
    safe_filename=$(echo "${endpoint}${query_string}" | sed 's/[\/\?=&]/_/g')
    echo "$response" > "output/mcp_test${safe_filename}.json"
    echo ""
    
    # Return the response for further processing
    echo "$response"
}

# Create output directory if it doesn't exist
mkdir -p output

echo -e "${YELLOW}Starting MCP Browser Protocol Extensions Test...${NC}"
echo -e "${YELLOW}API URL: ${API_URL}${NC}"
echo -e "${YELLOW}Test URL: ${TEST_URL}${NC}"
echo ""

# Check API status
echo -e "${YELLOW}Checking API status...${NC}"
status=$(curl -s "${API_URL}/api/status")
echo "$status"
echo ""

# First create a new page by navigating to a URL
echo -e "${YELLOW}Creating initial browser page...${NC}"
call_api "/api/browser/navigate" "url=${TEST_URL}&wait_until=networkidle"

# Test Browser Navigation Tools
echo -e "${YELLOW}Testing Browser Navigation Tools...${NC}"

# Get current URL
call_api "/api/browser/get_url" ""

# Get page title
call_api "/api/browser/get_title" ""

# Navigate to another page
call_api "/api/browser/navigate" "url=https://example.org&wait_until=networkidle"

# Go back
call_api "/api/browser/back" "wait_until=networkidle"

# Go forward
call_api "/api/browser/forward" "wait_until=networkidle"

# Refresh page
call_api "/api/browser/refresh" "wait_until=networkidle"

# Test DOM Manipulation Tools
echo -e "${YELLOW}Testing DOM Manipulation Tools...${NC}"

# Navigate to test URL again
call_api "/api/browser/navigate" "url=${TEST_URL}&wait_until=networkidle"

# Click on a link
call_api "/api/browser/click" "selector=a&wait_for_navigation=true"

# Go back
call_api "/api/browser/back" "wait_until=networkidle"

# Check visibility
call_api "/api/browser/check_visibility" "selector=h1"

# Wait for selector
call_api "/api/browser/wait_for_selector" "selector=h1&state=visible"

# Extract text
call_api "/api/browser/extract_text" "selector=h1"

# Test Visual Analysis Tools
echo -e "${YELLOW}Testing Visual Analysis Tools...${NC}"

# Take a screenshot of full page
call_api "/api/browser/screenshot" "full_page=true&format=png"

# Take a screenshot of specific element
call_api "/api/browser/screenshot" "selector=h1&format=png"

# Evaluate JavaScript
call_api "/api/browser/evaluate" "expression=document.title"

echo -e "${GREEN}MCP Browser Protocol Extensions Test Complete!${NC}"
echo -e "${GREEN}Test results saved to the output directory.${NC}" 