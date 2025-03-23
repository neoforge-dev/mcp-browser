#!/usr/bin/env python3
"""
Simple test script for MCP Browser API endpoints
"""
import os
import sys
import requests
import json
from datetime import datetime

# API Base URL
API_BASE_URL = "http://localhost:7665"

def log_message(msg):
    """Log a message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")

def check_api_status():
    """Check if the API is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/status")
        if response.status_code == 200:
            log_message(f"API Status: {response.json()}")
            return True
        else:
            log_message(f"API Status check failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        log_message(f"Error checking API status: {e}")
        return False

def test_api():
    """Run basic API test"""
    log_message("Starting API test...")
    
    # Check if API is running
    if not check_api_status():
        log_message("API is not running or not responding. Aborting test.")
        return False
    
    log_message("API is running. Basic test passed!")
    return True

if __name__ == "__main__":
    success = test_api()
    sys.exit(0 if success else 1) 