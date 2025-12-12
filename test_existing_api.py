#!/usr/bin/env python3
"""
Test your existing API to make sure it's working properly.
"""

import requests
import json

# Your existing API URL
API_BASE_URL = "https://t0phcz2vp8.execute-api.us-east-1.amazonaws.com/prod"

def test_health():
    """Test the health endpoint."""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            print("Health check passed")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"Health check failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Health check error: {e}")
        return False

def test_upload_url():
    """Test upload URL generation."""
    print("\n Testing upload URL generation...")
    try:
        params = {
            "filename": "test-contract.pdf",
            "contentType": "application/pdf", 
            "size": 1024000
        }
        response = requests.get(f"{API_BASE_URL}/upload-url", params=params, timeout=10)
        if response.status_code == 200:
            print("Upload URL generation passed")
            data = response.json()
            print(f"Bucket: {data['bucket']}")
            print(f"Method: {data['upload_method']}")
            print(f"Expires in: {data['expires_in']} seconds")
            return True
        else:
            print(f"Upload URL generation failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Upload URL generation error: {e}")
        return False

def test_analysis_endpoint():
    """Test analysis endpoint (should return proper error for invalid URI)."""
    print("\n Testing analysis endpoint...")
    try:
        payload = {
            "contract_id": "test-123",
            "contract_uri": "https://invalid-uri.com/test.pdf",
            "llm_enabled": False
        }
        response = requests.post(f"{API_BASE_URL}/analysis", json=payload, timeout=30)
        
        # We expect this to fail with a proper error message
        if response.status_code in [400, 500]:
            print("Analysis endpoint responding correctly")
            try:
                error_data = response.json()
                if isinstance(error_data.get('detail'), dict):
                    print(f"Error category: {error_data['detail'].get('category', 'Unknown')}")
                    print(f"Error message: {error_data['detail'].get('message', 'Unknown')}")
                else:
                    print(f"Error: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"Raw response: {response.text}")
            return True
        else:
            print(f"Unexpected response: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Analysis endpoint error: {e}")
        return False

def main():
    """Run all tests."""
    print(f"Testing API at: {API_BASE_URL}")
    print("=" * 50)
    
    tests = [
        test_health,
        test_upload_url, 
        test_analysis_endpoint
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("All tests passed! Your API is working correctly.")
    else:
        print("Some tests failed. Check the output above for details.")
    
    return passed == len(tests)

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)