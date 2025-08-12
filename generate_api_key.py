#!/usr/bin/env python3
"""
Generate a secure API key for Pi Monitor
"""

import secrets
import string

def generate_api_key(length=32):
    """Generate a secure API key"""
    # Use URL-safe characters
    alphabet = string.ascii_letters + string.digits + '-_'
    api_key = ''.join(secrets.choice(alphabet) for _ in range(length))
    return api_key

def generate_secure_api_key(length=64):
    """Generate a more secure API key with mixed characters"""
    # Generate a random hex string and convert to base64-like format
    random_bytes = secrets.token_bytes(length // 2)
    api_key = secrets.token_urlsafe(length)
    return api_key

if __name__ == "__main__":
    print("Pi Monitor API Key Generator")
    print("=" * 40)
    
    # Generate different types of keys
    simple_key = generate_api_key(32)
    secure_key = generate_secure_api_key(64)
    
    print(f"\nSimple API Key (32 chars):")
    print(f"{simple_key}")
    
    print(f"\nSecure API Key (64 chars):")
    print(f"{secure_key}")
    
    print(f"\nTo use these keys:")
    print(f"1. Copy one of the keys above")
    print(f"2. Set it as an environment variable:")
    print(f"   export PI_MONITOR_API_KEY='{secure_key}'")
    print(f"3. Or add it to your .env file:")
    print(f"   PI_MONITOR_API_KEY={secure_key}")
    
    print(f"\n⚠️  Keep your API key secret and secure!")
    print(f"⚠️  Never commit API keys to version control!")
