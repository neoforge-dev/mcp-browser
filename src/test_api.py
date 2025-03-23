#!/usr/bin/env python3
"""
Test script for MCP Browser API endpoints
"""
import os
import sys
import requests
import json
import base64
import time
from datetime import datetime

# API Base URL - can be overridden by environment variable
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:7665")

def log_message(msg):
    """Log a message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")

def check_api_status():
    """Check if the API is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/status")
        if response.status_code == 200:
            status_data = response.json()
            log_message(f"API Status: {status_data}")
            return True
        else:
            log_message(f"API Status check failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        log_message(f"Error checking API status: {e}")
        return False

def test_screenshot_capture():
    """Test the screenshot capture API"""
    log_message("Testing screenshot capture API...")
    
    # Test parameters
    test_url = "https://example.com"
    viewport = {"width": 1280, "height": 800}
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/screenshots/capture",
            params={
                "url": test_url,
                "full_page": True,
                "format": "png"
            },
            json={
                "viewport": viewport
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                # Save the screenshot to a file for verification
                if "screenshot" in result:
                    img_data = base64.b64decode(result["screenshot"])
                    timestamp = int(time.time())
                    filename = f"screenshot_{timestamp}.png"
                    
                    with open(filename, "wb") as f:
                        f.write(img_data)
                    
                    log_message(f"Screenshot saved to {filename}")
                    return True
                else:
                    log_message("Screenshot data missing from response")
                    return False
            else:
                log_message(f"Screenshot capture failed: {result.get('error', 'Unknown error')}")
                return False
        else:
            log_message(f"API request failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        log_message(f"Error testing screenshot capture: {e}")
        return False

def test_dom_extraction():
    """Test the DOM extraction API"""
    log_message("Testing DOM extraction API...")
    
    # Test parameters
    test_url = "https://example.com"
    selector = "h1"  # Example.com has an h1 element
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/dom/extract",
            params={
                "url": test_url,
                "selector": selector,
                "include_styles": True,
                "include_attributes": True
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                # Save the DOM info to a file for verification
                if "dom" in result:
                    timestamp = int(time.time())
                    filename = f"dom_extraction_{timestamp}.json"
                    
                    with open(filename, "w") as f:
                        json.dump(result["dom"], f, indent=2)
                    
                    log_message(f"DOM extraction saved to {filename}")
                    return True
                else:
                    log_message("DOM data missing from response")
                    return False
            else:
                log_message(f"DOM extraction failed: {result.get('error', 'Unknown error')}")
                return False
        else:
            log_message(f"API request failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        log_message(f"Error testing DOM extraction: {e}")
        return False

def test_css_analysis():
    """Test the CSS analysis API"""
    log_message("Testing CSS analysis API...")
    
    # Test parameters
    test_url = "https://example.com"
    selector = "p"  # Example.com has paragraphs
    properties = ["color", "font-size", "margin", "padding"]
    check_accessibility = True
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/css/analyze",
            params={
                "url": test_url,
                "selector": selector,
                "check_accessibility": check_accessibility
            },
            json={
                "properties": properties
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                # Save the CSS analysis to a file for verification
                if "elements" in result:
                    timestamp = int(time.time())
                    filename = f"css_analysis_{timestamp}.json"
                    
                    with open(filename, "w") as f:
                        json.dump(result, f, indent=2)
                    
                    log_message(f"CSS analysis saved to {filename}")
                    return True
                else:
                    log_message("CSS data missing from response")
                    return False
            else:
                log_message(f"CSS analysis failed: {result.get('error', 'Unknown error')}")
                return False
        else:
            log_message(f"API request failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        log_message(f"Error testing CSS analysis: {e}")
        return False

def run_tests():
    """Run all tests"""
    log_message("Starting API tests...")
    
    # Check if API is running
    if not check_api_status():
        log_message("API is not running or not responding. Aborting tests.")
        return False
    
    # Run tests
    screenshot_result = test_screenshot_capture()
    dom_result = test_dom_extraction()
    css_result = test_css_analysis()
    
    # Report results
    log_message("\nTest Results:")
    log_message(f"- Screenshot Capture: {'PASS' if screenshot_result else 'FAIL'}")
    log_message(f"- DOM Extraction: {'PASS' if dom_result else 'FAIL'}")
    log_message(f"- CSS Analysis: {'PASS' if css_result else 'FAIL'}")
    
    return screenshot_result and dom_result and css_result

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 