"""
Test script for analytics endpoints
Run this to verify analytics implementation
"""
import requests
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:8000"  # Change to your server URL
# BASE_URL = "https://dely-backend.onrender.com"

# Get admin token first by logging in
def get_admin_token():
    """Login as admin and get JWT token"""
    login_url = f"{BASE_URL}/admin/auth/login"
    
    # Replace with your admin credentials
    credentials = {
        "email": "admin@example.com",  # Replace with actual admin email
        "password": "admin123"  # Replace with actual admin password
    }
    
    response = requests.post(login_url, json=credentials)
    
    if response.status_code == 200:
        data = response.json()
        return data["data"]["token"]
    else:
        print(f"Failed to login: {response.status_code}")
        print(response.text)
        return None


def test_endpoint(endpoint, token, params=None):
    """Test an analytics endpoint"""
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    url = f"{BASE_URL}/admin/analytics/{endpoint}"
    
    print(f"\n{'=' * 80}")
    print(f"Testing: {endpoint}")
    print(f"URL: {url}")
    if params:
        print(f"Params: {params}")
    print(f"{'=' * 80}")
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data['success']}")
            print(f"Message: {data['message']}")
            print(f"\nData Preview:")
            print(json.dumps(data['data'], indent=2)[:500] + "...")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Exception: {str(e)}")
        return False


def main():
    """Run all analytics tests"""
    print("=" * 80)
    print("ANALYTICS ENDPOINTS TEST SUITE")
    print("=" * 80)
    
    # Get admin token
    print("\n1. Authenticating as admin...")
    token = get_admin_token()
    
    if not token:
        print("❌ Failed to get admin token. Please check credentials.")
        return
    
    print("✅ Successfully authenticated!")
    
    # Test all endpoints
    tests = [
        ("dashboard", {"period": "month"}),
        ("revenue", {"period": "week"}),
        ("products", {"period": "month", "limit": 5}),
        ("categories", {"period": "month"}),
        ("companies", {"period": "month"}),
        ("users", {"period": "month"}),
        ("orders", {"period": "month"}),
    ]
    
    results = []
    
    for endpoint, params in tests:
        success = test_endpoint(endpoint, token, params)
        results.append((endpoint, success))
    
    # Test export (don't download, just check response)
    print(f"\n{'=' * 80}")
    print("Testing: export (CSV)")
    print(f"{'=' * 80}")
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE_URL}/admin/analytics/export"
    params = {"period": "month", "format": "csv"}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            print(f"Status Code: {response.status_code}")
            print(f"Content-Type: {response.headers.get('Content-Type')}")
            print(f"Content-Length: {len(response.content)} bytes")
            print("✅ Export endpoint working!")
            results.append(("export", True))
        else:
            print(f"❌ Export failed: {response.status_code}")
            results.append(("export", False))
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        results.append(("export", False))
    
    # Summary
    print(f"\n{'=' * 80}")
    print("TEST SUMMARY")
    print(f"{'=' * 80}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for endpoint, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {endpoint}")
    
    print(f"\n{passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All analytics endpoints are working correctly!")
    else:
        print("\n⚠️ Some tests failed. Please check the output above.")


if __name__ == "__main__":
    main()
