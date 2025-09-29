"""
Test script for environment variable resolution in Control Tower
"""

import requests
import json
import os

# Configuration
CONTROL_TOWER_URL = "http://localhost:8000"
CONTROL_TOWER_SECRET = "dspsa_p@ssword"

def test_environment_resolution():
    """Test environment variable resolution functionality"""
    print("Testing Control Tower Environment Variable Resolution")
    print("=" * 60)
    
    # Set test environment variables
    os.environ["DEV_JWT_SECRET"] = "dev-secret-12345"
    os.environ["DEV_OPENAI_API_KEY"] = "sk-dev-test-key"
    
    headers = {"accept": "application/json"}
    
    # Test 1: Get manifest without resolution
    print("\n1. Testing manifest without environment resolution...")
    try:
        response = requests.get(
            f"{CONTROL_TOWER_URL}/manifests/basic-llm-project",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            jwt_config = None
            for module in data.get("modules", []):
                if module.get("name") == "simple-auth":
                    jwt_config = module
                    break
            
            if jwt_config:
                secret_key = jwt_config["config"]["secret_key"]
                print(f"✓ Raw secret_key: {secret_key}")
                if "${environments.${environment}.secrets.jwt_secret_key}" in secret_key:
                    print("✓ Contains unresolved placeholder as expected")
                else:
                    print("✗ Expected unresolved placeholder")
            else:
                print("✗ JWT config module not found")
        else:
            print(f"✗ Failed to get manifest: {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 2: Get manifest with resolution
    print("\n2. Testing manifest with environment resolution...")
    try:
        response = requests.get(
            f"{CONTROL_TOWER_URL}/manifests/basic-llm-project?resolve_env=true",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            jwt_config = None
            for module in data.get("modules", []):
                if module.get("name") == "simple-auth":
                    jwt_config = module
                    break
            
            if jwt_config:
                secret_key = jwt_config["config"]["secret_key"]
                print(f"✓ Resolved secret_key: {secret_key}")
                if secret_key == "${DEV_JWT_SECRET}":
                    print("✓ Environment variable resolved correctly")
                else:
                    print(f"✗ Expected ${{DEV_JWT_SECRET}}, got: {secret_key}")
                
                # Check environment overrides applied
                expiration = jwt_config["config"].get("expiration_minutes", 30)
                print(f"✓ Expiration minutes: {expiration}")
                if expiration == 30:  # development default
                    print("✓ Development environment settings applied")
                else:
                    print(f"✗ Expected 30 minutes for development, got: {expiration}")
            else:
                print("✗ JWT config module not found")
        else:
            print(f"✗ Failed to get manifest with resolution: {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 3: Get specific module without resolution
    print("\n3. Testing specific module without environment resolution...")
    try:
        response = requests.get(
            f"{CONTROL_TOWER_URL}/manifests/basic-llm-project/modules/simple-auth",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            secret_key = data["config"]["secret_key"]
            print(f"✓ Raw module secret_key: {secret_key}")
            if "${environments.${environment}.secrets.jwt_secret_key}" in secret_key:
                print("✓ Contains unresolved placeholder as expected")
            else:
                print("✗ Expected unresolved placeholder")
        else:
            print(f"✗ Failed to get module: {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 4: Get specific module with resolution
    print("\n4. Testing specific module with environment resolution...")
    try:
        response = requests.get(
            f"{CONTROL_TOWER_URL}/manifests/basic-llm-project/modules/simple-auth?resolve_env=true",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            secret_key = data["config"]["secret_key"]
            print(f"✓ Resolved module secret_key: {secret_key}")
            if secret_key == "${DEV_JWT_SECRET}":
                print("✓ Environment variable resolved correctly")
            else:
                print(f"✗ Expected ${{DEV_JWT_SECRET}}, got: {secret_key}")
            
            # Check environment overrides applied
            expiration = data["config"].get("expiration_minutes", 30)
            print(f"✓ Module expiration minutes: {expiration}")
        else:
            print(f"✗ Failed to get module with resolution: {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 5: Test inference endpoint with environment resolution
    print("\n5. Testing inference endpoint with environment resolution...")
    try:
        response = requests.get(
            f"{CONTROL_TOWER_URL}/manifests/basic-llm-project/modules/llm-chat?resolve_env=true",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            endpoint_url = data["config"]["endpoint_url"]
            api_key = data["config"]["api_key"]
            print(f"✓ Resolved endpoint_url: {endpoint_url}")
            print(f"✓ Resolved api_key: {api_key}")
            
            if "https://dev-api.company.com" in endpoint_url:
                print("✓ Environment URL resolved correctly")
            else:
                print(f"✗ Expected dev URL in endpoint, got: {endpoint_url}")
                
            if api_key == "${DEV_OPENAI_API_KEY}":
                print("✓ API key environment variable resolved correctly")
            else:
                print(f"✗ Expected ${{DEV_OPENAI_API_KEY}}, got: {api_key}")
        else:
            print(f"✗ Failed to get inference module with resolution: {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "=" * 60)
    print("Environment Resolution Test Complete")

if __name__ == "__main__":
    test_environment_resolution()
