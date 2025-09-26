"""
Test script for APISIX integration with Control Tower and Front Door
"""

import asyncio
import json
import sys
from typing import Dict, Any
import jwt as pyjwt
from datetime import datetime, timedelta, timezone

import httpx

# Configuration
CONTROL_TOWER_URL = "http://localhost:8000"
FRONT_DOOR_URL = "http://localhost:8080"
APISIX_ADMIN_URL = "http://localhost:9180"
APISIX_GATEWAY_URL = "http://localhost:9080"
APISIX_ADMIN_KEY = "edd1c9f034335f136f87ad84b625c8f1"
JWT_SECRET = "your-secret-key"
SUPERUSER_USERNAME = "admin"
SUPERUSER_PASSWORD = "admin123"
from test_manifest_system import SUPERUSER_SECRET

def generate_jwt_token(secret: str = JWT_SECRET, exp_minutes: int = 30) -> str:
    """Generate a test JWT token"""
    now = datetime.now(timezone.utc)
    payload = {
        "key": "test-apisix-project-key",  # This must match the consumer's JWT key
        "sub": "test-user",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=exp_minutes)).timestamp()),
        "iss": "frontdoor-ai-gateway",
        "aud": "ai-services",
        "metadata_filter": {
            "access_level": "standard",
            "department": "engineering"
        }
    }
    
    # Use PyJWT to encode the token
    token = pyjwt.encode(payload, secret, algorithm="HS256")
    return token


async def test_control_tower_connection():
    """Test connection to Control Tower"""
    print("\n1. Testing Control Tower Connection...")
    
    async with httpx.AsyncClient() as client:
        try:
            # Use an existing Control Tower endpoint since /health is not available
            # /manifests returns 200 with the list of manifests
            response = await client.get(f"{CONTROL_TOWER_URL}/manifests")
            if response.status_code == 200:
                print("✓ Control Tower reachable (manifests endpoint)")
                return True
            else:
                print(f"✗ Control Tower returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Failed to connect to Control Tower: {e}")
            return False


async def test_apisix_admin_api():
    """Test APISIX Admin API"""
    print("\n2. Testing APISIX Admin API...")
    
    headers = {"X-API-KEY": APISIX_ADMIN_KEY}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{APISIX_ADMIN_URL}/apisix/admin/routes",
                headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                route_count = len(data.get("list", []))
                print(f"✓ APISIX Admin API is accessible (Found {route_count} routes)")
                return True
            else:
                print(f"✗ APISIX Admin API returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Failed to connect to APISIX Admin API: {e}")
            return False


async def create_test_manifest():
    """Create a test manifest in Control Tower"""
    print("\n3. Creating Test Manifest in Control Tower...")
    
    manifest = {
        "manifest": {
            "project_id": "test-apisix-project",
            "project_name": "Test APISIX Integration",
            "version": "1.0.0",
            "description": "Test project for APISIX integration",
            "owner": "test-team",
            "team": ["test@example.com"],
            "tags": ["test", "apisix"],
            "environment": "test",
            "modules": [
                {
                    "module_type": "jwt_config",
                    "name": "test-jwt-auth",
                    "version": "1.0.0",
                    "status": "enabled",
                    "description": "Test JWT authentication",
                    "dependencies": [],
                    "cross_references": {},
                    "config": {
                        "secret_key": JWT_SECRET,
                        "algorithm": "HS256",
                        "expiration_minutes": 30,
                        "issuer": "frontdoor-ai-gateway",
                        "audience": "ai-services",
                        "refresh_token_enabled": False
                    }
                },
                {
                    "module_type": "api_gateway",
                    "name": "test-apisix-gateway",
                    "version": "1.0.0",
                    "status": "enabled",
                    "description": "Test APISIX Gateway",
                    "dependencies": ["test-jwt-auth"],
                    "cross_references": {
                        "auth": {
                            "module_name": "test-jwt-auth",
                            "module_type": "jwt_config",
                            "purpose": "JWT validation",
                            "required": True
                        }
                    },
                    "config": {
                        "admin_api_url": APISIX_ADMIN_URL,
                        "admin_key": APISIX_ADMIN_KEY,
                        "gateway_url": APISIX_GATEWAY_URL,
                        "routes": [
                            {
                                "name": "echo-route",
                                "uri": "/test/echo",
                                "methods": ["GET", "POST"],
                                "plugins": [
                                    {
                                        "name": "jwt-auth",
                                        "enabled": True,
                                        "config": {
                                            "key": "test-key",
                                            "secret": JWT_SECRET,
                                            "algorithm": "HS256"
                                        }
                                    },
                                    {
                                        "name": "limit-req",
                                        "enabled": True,
                                        "config": {
                                            "rate": 10,
                                            "burst": 5,
                                            "key_type": "var",
                                            "key": "remote_addr"
                                        }
                                    },
                                    {
                                        "name": "serverless-pre-function",
                                        "enabled": True,
                                        "config": {
                                            "phase": "access",
                                            "functions": [
                                                """
                                                return function(conf, ctx)
                                                    ngx.say('{"message":"Hello from APISIX","timestamp":"' .. os.date() .. '"}')
                                                    ngx.exit(200)
                                                end
                                                """
                                            ]
                                        }
                                    }
                                ]
                            }
                        ],
                        "jwt_auth_enabled": True,
                        "rate_limiting_enabled": True,
                        "logging_enabled": True,
                        "prometheus_enabled": True
                    }
                }
            ],
            "metadata": {
                "test": True,
                "created_by": "test_script"
            }
        }
    }
    
    # Use X-DSPAI-Client-Secret header for superuser authentication
    headers = {"X-DSPAI-Client-Secret": SUPERUSER_SECRET}
    
    async with httpx.AsyncClient() as client:
        try:
            # First, try to delete existing test manifest
            await client.delete(
                f"{CONTROL_TOWER_URL}/manifests/test-apisix-project",
                headers=headers
            )
        except:
            pass
        
        # Create new manifest
        response = await client.post(
            f"{CONTROL_TOWER_URL}/manifests",
            json=manifest,
            headers=headers
        )
        
        if response.status_code == 201:
            print("✓ Test manifest created successfully")
            return True
        else:
            print(f"✗ Failed to create manifest: {response.status_code} - {response.text}")
            return False


async def test_front_door_sync():
    """Test Front Door syncing manifests to APISIX"""
    print("\n4. Testing Front Door APISIX Sync...")
    
    async with httpx.AsyncClient() as client:
        try:
            # Trigger sync
            response = await client.post(f"{FRONT_DOOR_URL}/admin/sync")
            
            if response.status_code == 200:
                data = response.json()
                projects = data.get("projects", {})
                apisix_projects = projects.get("apisix", [])
                print(f"✓ Sync completed. APISIX projects: {apisix_projects}")
                return True
            else:
                print(f"✗ Sync failed with status {response.status_code}")
                print(f"  Response: {response.text}")
                return False
        except Exception as e:
            print(f"✗ Failed to sync: {e}")
            return False


async def test_apisix_route_created():
    """Verify route was created in APISIX"""
    print("\n5. Verifying APISIX Route Creation...")
    
    headers = {"X-API-KEY": APISIX_ADMIN_KEY}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{APISIX_ADMIN_URL}/apisix/admin/routes",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                routes = data.get("list", [])
                
                test_route_found = False
                for route in routes:
                    route_value = route.get("value", {})
                    # Check for the project-prefixed route name
                    if route_value.get("name") == "test-apisix-project-echo-route":
                        test_route_found = True
                        print(f"✓ Test route found: {route_value.get('uri')}")
                        break
                
                if not test_route_found:
                    print("✗ Test route not found in APISIX")
                
                return test_route_found
            else:
                print(f"✗ Failed to list routes: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Failed to verify route: {e}")
            return False


async def test_request_with_jwt():
    """Test making a request through APISIX with JWT"""
    print("\n6. Testing Request through APISIX with JWT...")
    
    token = generate_jwt_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        try:
            # Request through APISIX gateway with project-prefixed URI
            response = await client.get(
                f"{APISIX_GATEWAY_URL}/test-apisix-project/test/echo",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Request successful: {data}")
                return True
            else:
                print(f"✗ Request failed with status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            print(f"✗ Request failed: {e}")
            return False


async def test_request_without_jwt():
    """Test making a request without JWT (should fail)"""
    print("\n7. Testing Request without JWT (should fail)...")
    
    async with httpx.AsyncClient() as client:
        try:
            # Try to access with project-prefixed URI without JWT
            response = await client.get(f"{APISIX_GATEWAY_URL}/test-apisix-project/test/echo")
            
            if response.status_code == 401:
                print("✓ Request correctly rejected without JWT")
                return True
            else:
                print(f"✗ Expected 401 but got {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            return False


async def test_rate_limiting():
    """Test rate limiting"""
    print("\n8. Testing Rate Limiting...")
    
    token = generate_jwt_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        success_count = 0
        rate_limited = False
        
        # Make 15 rapid requests (rate limit is 10 with burst of 5)
        for i in range(15):
            try:
                response = await client.get(
                    f"{APISIX_GATEWAY_URL}/test-apisix-project/test/echo",
                    headers=headers
                )
                
                if response.status_code == 200:
                    success_count += 1
                elif response.status_code == 429:
                    rate_limited = True
                    print(f"✓ Rate limited at request {i+1}")
                    break
            except:
                pass
        
        if rate_limited:
            print(f"✓ Rate limiting is working (allowed {success_count} requests)")
            return True
        else:
            print(f"✗ Rate limiting not triggered after {success_count} requests")
            return False


async def main():
    """Run all tests"""
    print("=" * 60)
    print("APISIX Integration Test Suite")
    print("=" * 60)
    
    tests = [
        ("Control Tower Connection", test_control_tower_connection),
        ("APISIX Admin API", test_apisix_admin_api),
        ("Create Test Manifest", create_test_manifest),
        ("Front Door Sync", test_front_door_sync),
        ("APISIX Route Creation", test_apisix_route_created),
        ("Request with JWT", test_request_with_jwt),
        ("Request without JWT", test_request_without_jwt),
        ("Rate Limiting", test_rate_limiting),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))
        
        await asyncio.sleep(1)  # Small delay between tests
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! APISIX integration is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check the configuration.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
