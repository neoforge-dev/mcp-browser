#!/usr/bin/env python3
"""
Example script demonstrating usage of the MCP Browser Responsive Testing API
"""
import requests
import json
import os
import time
from pprint import pprint

# API settings
API_BASE_URL = "http://localhost:7665"
TEST_URL = "https://example.com"

# Create output directory
output_dir = "responsive_results"
os.makedirs(output_dir, exist_ok=True)

def responsive_test():
    """Test a website for responsive behavior across multiple viewport sizes"""
    print(f"Testing responsive behavior for: {TEST_URL}")
    
    # Configure test parameters
    viewports = [
        {"width": 375, "height": 667},    # Mobile portrait
        {"width": 768, "height": 1024},   # Tablet portrait
        {"width": 1366, "height": 768},   # Laptop
        {"width": 1920, "height": 1080}   # Desktop
    ]
    
    selectors = [
        "h1",                # Main heading
        "p",                 # Paragraphs
        "a",                 # Links
        ".container",        # Container elements
        "#main",            # Main content area
    ]
    
    # Make API request
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/responsive/test",
            json={
                "url": TEST_URL,
                "viewports": viewports,
                "selectors": selectors,
                "include_screenshots": True,
                "compare_elements": True
            }
        )
        
        # Process response
        if response.status_code == 200:
            result = response.json()
            
            # Save full results
            timestamp = int(time.time())
            output_file = os.path.join(output_dir, f"responsive_test_{timestamp}.json")
            
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)
                
            print(f"Full results saved to: {output_file}")
            
            # Display summary
            print("\nResponsive Testing Summary:")
            print("--------------------------")
            
            print(f"URL: {result['url']}")
            print(f"Tested Viewports: {len(result['viewports'])}")
            
            # Show viewport-specific metrics
            print("\nViewport Metrics:")
            for vp_result in result['viewport_results']:
                vp_name = vp_result['viewport_name']
                print(f"\n- {vp_name}:")
                
                if 'page_metrics' in vp_result:
                    metrics = vp_result['page_metrics']
                    print(f"  Document Size: {metrics.get('documentWidth', 'N/A')}x{metrics.get('documentHeight', 'N/A')}")
                    print(f"  Horizontal Scrolling: {'Present' if metrics.get('horizontalScrollPresent', False) else 'None'}")
                    print(f"  Small Touch Targets: {metrics.get('touchTargetSizes', 'N/A')}")
                    print(f"  Media Queries: {len(metrics.get('mediaQueries', []))}")
                
                if 'screenshot_path' in vp_result:
                    print(f"  Screenshot: {vp_result['screenshot_path']}")
            
            # Show responsive issues if any
            if result.get('element_comparison'):
                print("\nResponsive Issues Detected:")
                issues_found = False
                
                for selector, comparison in result['element_comparison'].items():
                    if comparison.get('differences') or comparison.get('responsive_issues'):
                        issues_found = True
                        print(f"\n- {selector}:")
                        
                        for diff in comparison.get('differences', []):
                            print(f"  • {diff.get('description', 'Unknown issue')}")
                            if 'counts' in diff:
                                print(f"    Element counts: {diff['counts']}")
                        
                        for issue in comparison.get('responsive_issues', []):
                            print(f"  • {issue.get('description', 'Unknown issue')}")
                            if 'visibility' in issue:
                                print(f"    Visibility changes: {issue['visibility']}")
                
                if not issues_found:
                    print("No significant responsive issues detected.")
            
            return True
        else:
            print(f"Error: API returned status code {response.status_code}")
            print(response.text)
            return False
    
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    responsive_test() 