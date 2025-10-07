#!/usr/bin/env python3
"""
Test script to validate Vercel deployment
Run this after deploying to verify all endpoints work correctly
"""

import requests
import json
import sys

def test_endpoint(url, method='GET', data=None, expected_status=200):
    """Test a single endpoint"""
    try:
        if method == 'GET':
            response = requests.get(url, timeout=30)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=30)
        else:
            print(f"❌ Unsupported method: {method}")
            return False
        
        if response.status_code == expected_status:
            print(f"✅ {method} {url} - Status: {response.status_code}")
            return True
        else:
            print(f"❌ {method} {url} - Expected: {expected_status}, Got: {response.status_code}")
            if response.text:
                print(f"   Response: {response.text[:200]}...")
            return False
    except Exception as e:
        print(f"❌ {method} {url} - Error: {e}")
        return False

def main():
    # Get base URL from command line or use default
    if len(sys.argv) < 2:
        print("❌ Please provide your Vercel deployment URL")
        print("Usage: python test_deployment.py <your-vercel-url>")
        print("Example: python test_deployment.py https://psu-menu-analyzer.vercel.app")
        sys.exit(1)
    
    base_url = sys.argv[1].rstrip('/')
    
    print(f"Testing PSU Menu Analyzer deployment at: {base_url}")
    print("=" * 60)
    
    tests = [
        # Test health endpoint
        (f"{base_url}/api/health", 'GET', None, 200),
        
        # Test main page
        (f"{base_url}/", 'GET', None, 200),
        
        # Test analyze endpoint with sample data
        (f"{base_url}/api/analyze", 'POST', {
            "campus": "altoona-port-sky",
            "vegetarian": False,
            "vegan": False,
            "exclude_beef": False,
            "exclude_pork": False,
            "prioritize_protein": False
        }, 200),
    ]
    
    passed = 0
    total = len(tests)
    
    for url, method, data, expected_status in tests:
        if test_endpoint(url, method, data, expected_status):
            passed += 1
        print()
    
    print("=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your deployment is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
