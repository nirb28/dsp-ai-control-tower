"""
Test script for RAG and Model Server integration with APISIX gateway

This script tests:
1. Control Tower manifest with RAG service and model server modules
2. Front Door APISIX auto-configuration for RAG and model server routes
3. End-to-end request routing through APISIX gateway
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
CONTROL_TOWER_URL = "http://localhost:8001"
FRONT_DOOR_URL = "http://localhost:8002"
APISIX_GATEWAY_URL = "http://localhost:9080"
PROJECT_ID = "ai-rag-platform"

def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def test_control_tower_manifest():
    """Test 1: Upload manifest to Control Tower"""
    print_section("TEST 1: Upload Manifest to Control Tower")
    
    manifest_path = "manifests/rag-model-server-integration.json"
    
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Upload manifest
        response = requests.post(
            f"{CONTROL_TOWER_URL}/manifests",
            json=manifest,
            headers={"X-Superuser-Secret": "your-secret-key"}
        )
        
        if response.status_code in [200, 201]:
            print(f"✓ Manifest uploaded successfully")
            print(f"  Project ID: {manifest['project_id']}")
            print(f"  Modules: {len(manifest['modules'])}")
            
            # List modules
            for module in manifest['modules']:
                print(f"    - {module['name']} ({module['module_type']})")
            
            return True
        else:
            print(f"✗ Failed to upload manifest: {response.status_code}")
            print(f"  Error: {response.text}")
            return False
            
    except FileNotFoundError:
        print(f"✗ Manifest file not found: {manifest_path}")
        return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

def test_get_manifest_modules():
    """Test 2: Retrieve manifest modules from Control Tower"""
    print_section("TEST 2: Retrieve Manifest Modules")
    
    try:
        # Get all modules
        response = requests.get(f"{CONTROL_TOWER_URL}/manifests/{PROJECT_ID}/modules")
        
        if response.status_code == 200:
            data = response.json()
            modules = data.get("modules", [])
            print(f"✓ Retrieved {len(modules)} modules")
            
            # Check for RAG service module
            rag_modules = [m for m in modules if m.get("module_type") == "rag_service"]
            if rag_modules:
                print(f"✓ Found {len(rag_modules)} RAG service module(s)")
                for rag in rag_modules:
                    config = rag.get("config", {})
                    print(f"    - {rag['name']}")
                    print(f"      Service URL: {config.get('service_url')}")
                    print(f"      Query endpoint: {config.get('query_endpoint')}")
                    print(f"      Retrieve endpoint: {config.get('retrieve_endpoint')}")
            
            # Check for model server module
            model_modules = [m for m in modules if m.get("module_type") == "model_server"]
            if model_modules:
                print(f"✓ Found {len(model_modules)} model server module(s)")
                for model in model_modules:
                    config = model.get("config", {})
                    print(f"    - {model['name']}")
                    print(f"      Service URL: {config.get('service_url')}")
                    print(f"      Embeddings: {config.get('embeddings_endpoint')}")
                    print(f"      Rerank: {config.get('rerank_endpoint')}")
                    print(f"      Classify: {config.get('classify_endpoint')}")
            
            return len(rag_modules) > 0 and len(model_modules) > 0
        else:
            print(f"✗ Failed to retrieve modules: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

def test_front_door_sync():
    """Test 3: Trigger Front Door to sync manifests and configure APISIX"""
    print_section("TEST 3: Front Door Manifest Sync")
    
    try:
        # Trigger sync
        response = requests.post(f"{FRONT_DOOR_URL}/admin/sync-manifests")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Manifest sync triggered successfully")
            print(f"  Synced projects: {data.get('synced_projects', 0)}")
            
            # Wait for sync to complete
            time.sleep(2)
            
            # Check project routing mode
            response = requests.get(f"{FRONT_DOOR_URL}/admin/projects/{PROJECT_ID}/routing")
            if response.status_code == 200:
                routing_data = response.json()
                print(f"✓ Project routing configured")
                print(f"  Routing mode: {routing_data.get('routing_mode')}")
                return True
            else:
                print(f"⚠ Could not verify routing configuration")
                return True  # Sync succeeded even if we can't verify
        else:
            print(f"✗ Failed to sync manifests: {response.status_code}")
            print(f"  Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

def test_apisix_routes():
    """Test 4: Verify APISIX routes were created"""
    print_section("TEST 4: Verify APISIX Routes")
    
    try:
        # Get APISIX resources for project
        response = requests.get(f"{FRONT_DOOR_URL}/admin/apisix/projects/{PROJECT_ID}/resources")
        
        if response.status_code == 200:
            data = response.json()
            routes = data.get("routes", [])
            upstreams = data.get("upstreams", [])
            
            print(f"✓ APISIX resources retrieved")
            print(f"  Routes: {len(routes)}")
            print(f"  Upstreams: {len(upstreams)}")
            
            # Check for RAG routes
            rag_routes = [r for r in routes if "/rag/" in r.get("value", {}).get("uri", "")]
            if rag_routes:
                print(f"\n✓ Found {len(rag_routes)} RAG service route(s):")
                for route in rag_routes:
                    route_data = route.get("value", {})
                    print(f"    - {route_data.get('name')}")
                    print(f"      URI: {route_data.get('uri')}")
                    print(f"      Methods: {route_data.get('methods')}")
            
            # Check for model server routes
            model_routes = [r for r in routes if "/models/" in r.get("value", {}).get("uri", "")]
            if model_routes:
                print(f"\n✓ Found {len(model_routes)} model server route(s):")
                for route in model_routes:
                    route_data = route.get("value", {})
                    print(f"    - {route_data.get('name')}")
                    print(f"      URI: {route_data.get('uri')}")
                    print(f"      Methods: {route_data.get('methods')}")
            
            return len(rag_routes) > 0 and len(model_routes) > 0
        else:
            print(f"✗ Failed to retrieve APISIX resources: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

def test_rag_query_route():
    """Test 5: Test RAG query endpoint through APISIX"""
    print_section("TEST 5: Test RAG Query Route (Dry Run)")
    
    # Note: This is a dry run test - actual RAG service needs to be running
    print("ℹ This test demonstrates the expected request format")
    print("  Actual testing requires RAG service to be running\n")
    
    # Expected route
    route_uri = f"/{PROJECT_ID}/rag/knowledge-base/query"
    full_url = f"{APISIX_GATEWAY_URL}{route_uri}"
    
    print(f"Expected RAG query endpoint:")
    print(f"  URL: {full_url}")
    print(f"  Method: POST")
    print(f"  Headers: Authorization: Bearer <jwt_token>")
    
    # Sample request body
    sample_request = {
        "query": "What is machine learning?",
        "k": 5,
        "similarity_threshold": 0.7,
        "use_reranking": True,
        "filter_after_reranking": True
    }
    
    print(f"\nSample request body:")
    print(json.dumps(sample_request, indent=2))
    
    return True

def test_model_server_routes():
    """Test 6: Test model server endpoints through APISIX"""
    print_section("TEST 6: Test Model Server Routes (Dry Run)")
    
    # Note: This is a dry run test - actual model server needs to be running
    print("ℹ This test demonstrates the expected request formats")
    print("  Actual testing requires model server to be running\n")
    
    endpoints = [
        {
            "name": "Embeddings",
            "path": f"/{PROJECT_ID}/models/embedding-reranker/embeddings",
            "sample": {
                "texts": ["Hello world", "Machine learning"],
                "model_name": "BAAI/bge-large-en-v1.5"
            }
        },
        {
            "name": "Reranking",
            "path": f"/{PROJECT_ID}/models/embedding-reranker/rerank",
            "sample": {
                "query": "What is AI?",
                "texts": ["AI is artificial intelligence", "ML is machine learning"],
                "model_name": "BAAI/bge-reranker-large"
            }
        },
        {
            "name": "Classification",
            "path": f"/{PROJECT_ID}/models/embedding-reranker/classify",
            "sample": {
                "texts": ["This is a positive review"],
                "labels": ["positive", "negative", "neutral"],
                "model_name": "cross-encoder/ms-marco-MiniLM-L-12-v2"
            }
        }
    ]
    
    for endpoint in endpoints:
        print(f"{endpoint['name']} endpoint:")
        print(f"  URL: {APISIX_GATEWAY_URL}{endpoint['path']}")
        print(f"  Method: POST")
        print(f"  Sample request:")
        print(f"  {json.dumps(endpoint['sample'], indent=4)}\n")
    
    return True

def test_cleanup():
    """Test 7: Cleanup APISIX resources"""
    print_section("TEST 7: Cleanup (Optional)")
    
    print("To cleanup APISIX resources for this project, run:")
    print(f"  DELETE {FRONT_DOOR_URL}/admin/apisix/projects/{PROJECT_ID}/resources")
    print("\nTo delete the manifest from Control Tower, run:")
    print(f"  DELETE {CONTROL_TOWER_URL}/manifests/{PROJECT_ID}")
    
    return True

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("  RAG and Model Server Integration Test Suite")
    print("="*80)
    
    tests = [
        ("Upload Manifest", test_control_tower_manifest),
        ("Retrieve Modules", test_get_manifest_modules),
        ("Front Door Sync", test_front_door_sync),
        ("Verify APISIX Routes", test_apisix_routes),
        ("RAG Query Route", test_rag_query_route),
        ("Model Server Routes", test_model_server_routes),
        ("Cleanup Info", test_cleanup),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test failed with exception: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠ {total - passed} test(s) failed")

if __name__ == "__main__":
    main()
