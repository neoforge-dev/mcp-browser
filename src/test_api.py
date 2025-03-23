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

# Output directories
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
SCREENSHOTS_DIR = os.path.join(OUTPUT_DIR, "screenshots")
DOM_DIR = os.path.join(OUTPUT_DIR, "dom")
CSS_DIR = os.path.join(OUTPUT_DIR, "css")

# Create output directories if they don't exist
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(DOM_DIR, exist_ok=True)
os.makedirs(CSS_DIR, exist_ok=True)

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
                    filepath = os.path.join(SCREENSHOTS_DIR, filename)
                    
                    with open(filepath, "wb") as f:
                        f.write(img_data)
                    
                    log_message(f"Screenshot saved to {filepath}")
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
                    filepath = os.path.join(DOM_DIR, filename)
                    
                    with open(filepath, "w") as f:
                        json.dump(result["dom"], f, indent=2)
                    
                    log_message(f"DOM extraction saved to {filepath}")
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
    url = "https://example.com"
    selector = "p"
    check_accessibility = True
    
    try:
        # Make the API call
        response = requests.post(
            f"{API_BASE_URL}/api/css/analyze",
            params={"url": url, "selector": selector, "check_accessibility": check_accessibility}
        )
        
        # Check response
        if response.status_code == 200:
            css_data = response.json()
            log_message(f"CSS analysis successful")
            
            # Save the response to file
            timestamp = int(time.time())
            output_file = os.path.join(CSS_DIR, f"css_analysis_{timestamp}.json")
            
            with open(output_file, "w") as f:
                json.dump(css_data, f, indent=2)
                
            log_message(f"CSS analysis data saved to {output_file}")
            return True
        else:
            log_message(f"CSS analysis failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        log_message(f"Error testing CSS analysis API: {e}")
        return False

def test_accessibility():
    """Test the accessibility testing API"""
    log_message("Testing accessibility testing API...")
    
    # Test parameters
    url = "https://example.com"
    standard = "wcag2aa"
    include_html = True
    include_warnings = True
    
    try:
        # Make the API call
        response = requests.post(
            f"{API_BASE_URL}/api/accessibility/test",
            params={
                "url": url, 
                "standard": standard, 
                "include_html": include_html,
                "include_warnings": include_warnings
            }
        )
        
        # Check response
        if response.status_code == 200:
            accessibility_data = response.json()
            log_message(f"Accessibility testing successful")
            
            # Save the response to file
            timestamp = int(time.time())
            output_dir = os.path.join(OUTPUT_DIR, "accessibility")
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"accessibility_test_{timestamp}.json")
            
            with open(output_file, "w") as f:
                json.dump(accessibility_data, f, indent=2)
                
            log_message(f"Accessibility test data saved to {output_file}")
            return True
        else:
            log_message(f"Accessibility testing failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        log_message(f"Error testing accessibility API: {e}")
        return False

def test_responsive():
    """Test the responsive design testing API"""
    log_message("Testing responsive design testing API...")
    
    # Test parameters
    url = "https://example.com"
    viewports = [
        {"width": 375, "height": 667},  # Mobile
        {"width": 1366, "height": 768}  # Laptop
    ]
    selectors = ["h1", "p"]
    
    try:
        # Make the API call
        response = requests.post(
            f"{API_BASE_URL}/api/responsive/test",
            params={
                "url": url,
                "include_screenshots": True,
                "compare_elements": True
            },
            json={
                "viewports": viewports,
                "selectors": selectors
            }
        )
        
        # Check response
        if response.status_code == 200:
            responsive_data = response.json()
            log_message(f"Responsive design testing successful")
            
            # Save the response to file
            timestamp = int(time.time())
            output_dir = os.path.join(OUTPUT_DIR, "responsive")
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"responsive_test_summary_{timestamp}.json")
            
            with open(output_file, "w") as f:
                json.dump(responsive_data, f, indent=2)
                
            log_message(f"Responsive test data saved to {output_file}")
            return True
        else:
            log_message(f"Responsive design testing failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        log_message(f"Error testing responsive design API: {e}")
        return False

def run_tests():
    """Run all the API tests"""
    # Check if the API is running
    if not check_api_status():
        log_message("API is not running. Exiting.")
        sys.exit(1)
    
    # Keep track of test results
    test_results = {
        "screenshot_capture": None,
        "dom_extraction": None,
        "css_analysis": None,
        "accessibility_testing": None,
        "responsive_testing": None
    }
    
    # Run tests
    test_results["screenshot_capture"] = test_screenshot_capture()
    test_results["dom_extraction"] = test_dom_extraction()
    test_results["css_analysis"] = test_css_analysis()
    test_results["accessibility_testing"] = test_accessibility()
    test_results["responsive_testing"] = test_responsive()
    
    # Report results
    log_message("\n--- Test Results ---")
    all_passed = True
    
    for test_name, result in test_results.items():
        status = "PASSED" if result else "FAILED"
        log_message(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    # Exit with appropriate status code
    if all_passed:
        log_message("All tests passed!")
        sys.exit(0)
    else:
        log_message("Some tests failed. Check the logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 