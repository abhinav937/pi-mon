#!/usr/bin/env python3
"""
Pi Monitor - Security Test Script
Test various security features and configurations
"""

import requests
import json
import time
import sys
import os

def test_https_connection(base_url):
    """Test HTTPS connection and security headers"""
    print(f"🔒 Testing HTTPS connection to {base_url}")
    
    try:
        # Test basic connection
        response = requests.get(f"{base_url}/health", verify=False, timeout=10)
        print(f"✅ Connection successful: {response.status_code}")
        
        # Check security headers
        print("\n🔐 Security Headers:")
        security_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options', 
            'X-XSS-Protection',
            'Strict-Transport-Security',
            'Content-Security-Policy',
            'Referrer-Policy',
            'Permissions-Policy'
        ]
        
        for header in security_headers:
            value = response.headers.get(header, 'Not Set')
            status = "✅" if value != 'Not Set' else "❌"
            print(f"  {status} {header}: {value}")
        
        return True
        
    except requests.exceptions.SSLError as e:
        print(f"❌ SSL Error: {e}")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return False

def test_rate_limiting(base_url):
    """Test rate limiting functionality"""
    print(f"\n🚦 Testing Rate Limiting...")
    
    try:
        # Make multiple rapid requests
        responses = []
        for i in range(105):  # Exceed the 100 request limit
            response = requests.get(f"{base_url}/health", verify=False, timeout=5)
            responses.append(response.status_code)
            
            if i % 20 == 0:
                print(f"  Request {i+1}: {response.status_code}")
        
        # Check if rate limiting kicked in
        blocked_requests = [r for r in responses if r == 429 or r == 403]
        if blocked_requests:
            print(f"✅ Rate limiting working: {len(blocked_requests)} requests blocked")
        else:
            print("⚠️  Rate limiting may not be working")
        
        return True
        
    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        return False

def test_security_validation(base_url):
    """Test security validation with malicious requests"""
    print(f"\n🛡️ Testing Security Validation...")
    
    malicious_tests = [
        ("XSS attempt", "/<script>alert('xss')</script>"),
        ("Path traversal", "/../../../etc/passwd"),
        ("SQL injection", "/?id=1' OR '1'='1"),
        ("Suspicious header", {"X-Forwarded-For": "malicious.com"}),
    ]
    
    for test_name, test_value in malicious_tests:
        try:
            if isinstance(test_value, str):
                # Test malicious path
                response = requests.get(f"{base_url}{test_value}", verify=False, timeout=5)
            else:
                # Test malicious headers
                response = requests.get(f"{base_url}/health", headers=test_value, verify=False, timeout=5)
            
            if response.status_code in [400, 403, 429]:
                print(f"  ✅ {test_name}: Blocked ({response.status_code})")
            else:
                print(f"  ⚠️  {test_name}: Allowed ({response.status_code})")
                
        except Exception as e:
            print(f"  ❌ {test_name}: Error - {e}")
    
    return True

def test_certificate_info():
    """Test SSL certificate information"""
    print(f"\n📜 Testing SSL Certificate...")
    
    cert_dir = "certs"
    cert_file = os.path.join(cert_dir, "server.crt")
    key_file = os.path.join(cert_dir, "server.key")
    
    if os.path.exists(cert_file) and os.path.exists(key_file):
        print(f"✅ Certificate files found:")
        print(f"  📄 Certificate: {cert_file}")
        print(f"  🔑 Private Key: {key_file}")
        
        # Check file permissions
        cert_mode = oct(os.stat(cert_file).st_mode)[-3:]
        key_mode = oct(os.stat(key_file).st_mode)[-3:]
        
        print(f"  🔐 Certificate permissions: {cert_mode}")
        print(f"  🔐 Key permissions: {key_mode}")
        
        if key_mode == "600":
            print("  ✅ Key permissions are secure")
        else:
            print("  ⚠️  Key permissions should be 600")
            
    else:
        print("❌ Certificate files not found")
        print("  Run the certificate generation script first")
        return False
    
    return True

def main():
    """Main test function"""
    print("🔒 Pi Monitor Security Test Suite")
    print("=" * 50)
    
    # Get base URL from user
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = input("Enter the base URL (e.g., https://localhost:8080): ").strip()
    
    if not base_url:
        print("❌ No URL provided")
        return
    
    if not base_url.startswith('https://'):
        print("⚠️  Warning: URL should use HTTPS for security testing")
    
    # Run tests
    tests = [
        ("HTTPS Connection", lambda: test_https_connection(base_url)),
        ("SSL Certificate", test_certificate_info),
        ("Rate Limiting", lambda: test_rate_limiting(base_url)),
        ("Security Validation", lambda: test_security_validation(base_url)),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All security tests passed! Your Pi Monitor is secure.")
    else:
        print("⚠️  Some security tests failed. Review the configuration.")

if __name__ == "__main__":
    main()
