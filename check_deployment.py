#!/usr/bin/env python3
"""
Quick deployment checker for PSU Menu Analyzer
This script helps you test your actual Vercel deployment
"""

import requests
import json
import sys

def check_deployment(base_url):
    """Check if deployment is working"""
    print(f"🔍 Checking deployment at: {base_url}")
    print("=" * 50)
    
    # Test 1: Health endpoint
    try:
        response = requests.get(f"{base_url}/api/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health endpoint working")
            health_data = response.json()
            print(f"   Status: {health_data.get('status', 'unknown')}")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
        return False
    
    # Test 2: Main page
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            print("✅ Main page loading")
        else:
            print(f"❌ Main page failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Main page error: {e}")
        return False
    
    # Test 3: Analyze endpoint (without API key - should fail gracefully)
    try:
        test_data = {
            "campus": "altoona-port-sky",
            "vegetarian": False,
            "vegan": False,
            "exclude_beef": False,
            "exclude_pork": False,
            "prioritize_protein": False
        }
        response = requests.post(f"{base_url}/api/analyze", json=test_data, timeout=30)
        
        if response.status_code == 200:
            print("✅ Analyze endpoint working (with API key)")
            return True
        elif response.status_code == 500:
            # This might be expected if no API key is set
            error_data = response.json()
            if "Gemini API" in error_data.get('error', ''):
                print("⚠️  Analyze endpoint responding but needs API key")
                print("   This is expected if GEMINI_API_KEY is not set")
                return True
            else:
                print(f"❌ Analyze endpoint server error: {error_data.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ Analyze endpoint failed: {response.status_code}")
            if response.text:
                print(f"   Response: {response.text[:200]}...")
            return False
    except Exception as e:
        print(f"❌ Analyze endpoint error: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python check_deployment.py <your-vercel-url>")
        print("Example: python check_deployment.py https://psu-menu-analyzer.vercel.app")
        sys.exit(1)
    
    base_url = sys.argv[1].rstrip('/')
    
    if check_deployment(base_url):
        print("\n🎉 Deployment check passed!")
        print("Your PSU Menu Analyzer is working correctly on Vercel.")
        print("\nNext steps:")
        print("1. Set your GEMINI_API_KEY in Vercel environment variables")
        print("2. Test the full functionality with the web interface")
    else:
        print("\n❌ Deployment check failed!")
        print("Please check:")
        print("1. Your Vercel URL is correct")
        print("2. The deployment completed successfully")
        print("3. Environment variables are set correctly")

if __name__ == "__main__":
    main()
