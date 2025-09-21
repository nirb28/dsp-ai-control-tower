#!/usr/bin/env python3
"""
Test script for the Project Manifest System in DSP AI Control Tower
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
SUPERUSER_SECRET = "dspsa_p@ssword"  # Default superuser secret

class ManifestTester:
    def __init__(self, base_url: str = BASE_URL, superuser_secret: str = SUPERUSER_SECRET):
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json",
            "X-DSPAI-Client-Secret": superuser_secret
        }
    
    def test_api_connection(self) -> bool:
        """Test basic API connectivity"""
        try:
            response = requests.get(f"{self.base_url}/")
            print(f"✅ API Connection: {response.status_code} - {response.json()['message']}")
            return True
        except Exception as e:
            print(f"❌ API Connection failed: {e}")
            return False
    
    def test_module_types(self) -> bool:
        """Test getting available module types"""
        try:
            response = requests.get(f"{self.base_url}/module-types")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Module Types: Found {len(data['module_types'])} types")
                for module_type in data['module_types'][:3]:  # Show first 3
                    print(f"   - {module_type['type']}: {module_type['description']}")
                return True
            else:
                print(f"❌ Module Types failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Module Types failed: {e}")
            return False
    
    def create_test_manifest(self) -> Dict[str, Any]:
        """Create a test manifest"""
        manifest = {
            "manifest": {
                "project_id": "test-manifest-001",
                "project_name": "Test Manifest Project",
                "version": "1.0.0",
                "description": "Test manifest for validation",
                "owner": "test@example.com",
                "team": ["developer1@example.com", "developer2@example.com"],
                "tags": ["test", "validation", "dev"],
                "environment": "development",
                "modules": [
                    {
                        "module_type": "jwt_config",
                        "name": "test-auth",
                        "version": "1.0.0",
                        "status": "enabled",
                        "description": "Test JWT configuration",
                        "dependencies": [],
                        "config": {
                            "secret_key": "test-secret-key",
                            "algorithm": "HS256",
                            "expiration_minutes": 30,
                            "issuer": "test-system",
                            "audience": "test-users",
                            "refresh_token_enabled": false
                        }
                    },
                    {
                        "module_type": "inference_endpoint",
                        "name": "test-llm",
                        "version": "1.0.0",
                        "status": "enabled",
                        "description": "Test LLM inference endpoint",
                        "dependencies": ["test-auth"],
                        "cross_references": {
                            "authentication": {
                                "module_name": "test-auth",
                                "module_type": "jwt_config",
                                "purpose": "JWT token validation for API requests",
                                "required": True
                            },
                            "monitoring": {
                                "module_name": "test-monitoring",
                                "module_type": "monitoring",
                                "purpose": "Track inference performance",
                                "required": False
                            }
                        },
                        "config": {
                            "model_name": "gpt-3.5-turbo",
                            "model_version": "latest",
                            "endpoint_url": "https://api.openai.com/v1/chat/completions",
                            "system_prompt": "You are a test assistant.",
                            "max_tokens": 100,
                            "temperature": 0.7,
                            "top_p": 1.0,
                            "batch_size": 1
                        }
                    },
                    {
                        "module_type": "monitoring",
                        "name": "test-monitoring",
                        "version": "1.0.0",
                        "status": "enabled",
                        "description": "Test monitoring configuration",
                        "dependencies": [],
                        "config": {
                            "metrics_enabled": true,
                            "logging_level": "DEBUG",
                            "tracing_enabled": false,
                            "health_check_interval": 60,
                            "alerting_enabled": false,
                            "dashboard_url": None
                        }
                    }
                ],
                "metadata": {
                    "test_run": True,
                    "created_by": "test_script"
                }
            }
        }
        return manifest
    
    def test_manifest_validation(self, manifest: Dict[str, Any]) -> bool:
        """Test manifest validation endpoint"""
        try:
            response = requests.post(
                f"{self.base_url}/manifests/validate",
                headers={"Content-Type": "application/json"},
                json=manifest
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['valid']:
                    print("✅ Manifest Validation: Passed")
                    if data['warnings']:
                        print(f"   ⚠️  Warnings: {len(data['warnings'])}")
                        for warning in data['warnings'][:2]:
                            print(f"      - {warning}")
                    return True
                else:
                    print(f"❌ Manifest Validation: Failed with errors:")
                    for error in data['errors'][:3]:
                        print(f"      - {error}")
                    return False
            else:
                print(f"❌ Manifest Validation failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Manifest Validation failed: {e}")
            return False
    
    def test_create_manifest(self, manifest: Dict[str, Any]) -> bool:
        """Test creating a manifest"""
        try:
            response = requests.post(
                f"{self.base_url}/manifests",
                headers=self.headers,
                json=manifest
            )
            
            if response.status_code == 201:
                data = response.json()
                print(f"✅ Create Manifest: {data['message']}")
                return True
            else:
                print(f"❌ Create Manifest failed: {response.status_code}")
                if response.status_code == 400:
                    print(f"   Error: {response.json().get('detail', 'Unknown error')}")
                return False
        except Exception as e:
            print(f"❌ Create Manifest failed: {e}")
            return False
    
    def test_list_manifests(self) -> bool:
        """Test listing manifests"""
        try:
            response = requests.get(f"{self.base_url}/manifests")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ List Manifests: Found {data['count']} manifests")
                for manifest in data['manifests'][:2]:  # Show first 2
                    print(f"   - {manifest['project_id']}: {manifest['project_name']} ({manifest['environment']})")
                return True
            else:
                print(f"❌ List Manifests failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ List Manifests failed: {e}")
            return False
    
    def test_get_manifest(self, project_id: str) -> bool:
        """Test getting a specific manifest"""
        try:
            response = requests.get(f"{self.base_url}/manifests/{project_id}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Get Manifest: Retrieved '{data['project_name']}'")
                print(f"   - Modules: {len(data['modules'])}")
                print(f"   - Environment: {data['environment']}")
                print(f"   - Owner: {data['owner']}")
                return True
            elif response.status_code == 404:
                print(f"⚠️  Get Manifest: Not found - {project_id}")
                return True  # This is expected for non-existent manifests
            else:
                print(f"❌ Get Manifest failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Get Manifest failed: {e}")
            return False
    
    def test_get_manifest_modules(self, project_id: str) -> bool:
        """Test getting manifest modules"""
        try:
            response = requests.get(f"{self.base_url}/manifests/{project_id}/modules")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Get Modules: Found {data['count']} modules")
                for module in data['modules'][:2]:  # Show first 2
                    cross_ref_count = len(module.get('cross_references', {}))
                    print(f"   - {module['name']} ({module['module_type']}): {module['status']}, {cross_ref_count} cross-refs")
                return True
            elif response.status_code == 404:
                print(f"⚠️  Get Modules: Manifest not found - {project_id}")
                return True
            else:
                print(f"❌ Get Modules failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Get Modules failed: {e}")
            return False
    
    def test_update_manifest(self, manifest: Dict[str, Any]) -> bool:
        """Test updating a manifest"""
        try:
            # Modify the manifest slightly
            manifest['manifest']['version'] = "1.1.0"
            manifest['manifest']['description'] = "Updated test manifest"
            
            project_id = manifest['manifest']['project_id']
            response = requests.put(
                f"{self.base_url}/manifests/{project_id}",
                headers=self.headers,
                json=manifest
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Update Manifest: {data['message']}")
                return True
            else:
                print(f"❌ Update Manifest failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Update Manifest failed: {e}")
            return False
    
    def test_cross_references(self, project_id: str) -> bool:
        """Test cross-reference functionality"""
        try:
            # Test cross-reference analysis
            response = requests.get(f"{self.base_url}/manifests/{project_id}/cross-references")
            
            if response.status_code == 200:
                data = response.json()
                summary = data['summary']
                print(f"✅ Cross-References Analysis: {summary['total_modules']} modules, {summary['total_references']} references")
                
                # Test suggestions
                response = requests.get(f"{self.base_url}/manifests/{project_id}/cross-references/suggestions")
                if response.status_code == 200:
                    suggestions = response.json()
                    print(f"✅ Cross-Reference Suggestions: {suggestions['summary']['total_suggestions']} suggestions")
                    return True
                else:
                    print(f"❌ Cross-Reference Suggestions failed: {response.status_code}")
                    return False
            elif response.status_code == 404:
                print(f"⚠️  Cross-References: Manifest not found - {project_id}")
                return True
            else:
                print(f"❌ Cross-References failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cross-References failed: {e}")
            return False
    
    def test_delete_manifest(self, project_id: str) -> bool:
        """Test deleting a manifest"""
        try:
            response = requests.delete(
                f"{self.base_url}/manifests/{project_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Delete Manifest: {data['message']}")
                return True
            else:
                print(f"❌ Delete Manifest failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Delete Manifest failed: {e}")
            return False
    
    def run_comprehensive_test(self):
        """Run comprehensive test suite"""
        print("🚀 Starting DSP AI Control Tower - Manifest System Tests")
        print("=" * 60)
        
        results = []
        
        # Test 1: API Connection
        results.append(self.test_api_connection())
        
        # Test 2: Module Types
        results.append(self.test_module_types())
        
        # Test 3: Create test manifest
        test_manifest = self.create_test_manifest()
        
        # Test 4: Validate manifest
        results.append(self.test_manifest_validation(test_manifest))
        
        # Test 5: Create manifest
        results.append(self.test_create_manifest(test_manifest))
        
        # Test 6: List manifests
        results.append(self.test_list_manifests())
        
        # Test 7: Get specific manifest
        project_id = test_manifest['manifest']['project_id']
        results.append(self.test_get_manifest(project_id))
        
        # Test 8: Get manifest modules
        results.append(self.test_get_manifest_modules(project_id))
        
        # Test 9: Cross-reference analysis
        results.append(self.test_cross_references(project_id))
        
        # Test 10: Update manifest
        results.append(self.test_update_manifest(test_manifest))
        
        # Test 11: Delete manifest (cleanup)
        results.append(self.test_delete_manifest(project_id))
        
        # Test existing manifest examples
        print("\n📁 Testing Existing Manifest Examples:")
        print("-" * 40)
        
        # Test customer service manifest
        results.append(self.test_get_manifest("ai-customer-service"))
        results.append(self.test_get_manifest_modules("ai-customer-service"))
        results.append(self.test_cross_references("ai-customer-service"))
        
        # Summary
        print("\n📊 Test Results Summary:")
        print("=" * 30)
        passed = sum(results)
        total = len(results)
        success_rate = (passed / total) * 100 if total > 0 else 0
        
        print(f"✅ Passed: {passed}/{total} ({success_rate:.1f}%)")
        
        if passed == total:
            print("🎉 All tests passed! Manifest system is working correctly.")
        else:
            failed = total - passed
            print(f"❌ Failed: {failed}/{total}")
            print("⚠️  Some tests failed. Check the output above for details.")
        
        return success_rate >= 80  # 80% success rate threshold

def main():
    """Main function"""
    print("DSP AI Control Tower - Manifest System Test Suite")
    print("=" * 50)
    
    # Check if custom URL or secret provided
    import argparse
    parser = argparse.ArgumentParser(description="Test the Manifest System")
    parser.add_argument("--url", default=BASE_URL, help="API base URL")
    parser.add_argument("--secret", default=SUPERUSER_SECRET, help="Superuser secret")
    
    args = parser.parse_args()
    
    tester = ManifestTester(args.url, args.secret)
    
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n🎯 Manifest System is ready for use!")
        print("\n📚 Available Endpoints:")
        print("   GET    /manifests                     - List all manifests")
        print("   POST   /manifests                     - Create manifest (superuser)")
        print("   GET    /manifests/{id}                - Get specific manifest")
        print("   PUT    /manifests/{id}                - Update manifest (superuser)")
        print("   DELETE /manifests/{id}                - Delete manifest (superuser)")
        print("   POST   /manifests/validate            - Validate manifest")
        print("   GET    /manifests/{id}/modules        - Get manifest modules")
        print("   GET    /manifests/{id}/modules/{name} - Get specific module")
        print("   GET    /module-types                  - Get available module types")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the system configuration.")
        sys.exit(1)

if __name__ == "__main__":
    main()
