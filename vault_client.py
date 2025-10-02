"""
Enhanced HashiCorp Vault Client for DSP AI Control Tower
Supports multiple Vault instances with different authentication methods
"""

import os
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json


class VaultClient:
    """Client for interacting with HashiCorp Vault"""
    
    def __init__(
        self,
        vault_url: str = None,
        vault_token: str = None,
        vault_namespace: str = None,
        role_id: str = None,
        secret_id: str = None,
        auth_method: str = "token",
        mount_point: str = "secret",
        kv_version: int = 2,
        verify_ssl: bool = True,
        timeout: int = 30,
        instance_name: str = "default"
    ):
        """
        Initialize Vault client
        
        Args:
            vault_url: Vault server URL
            vault_token: Vault authentication token (for token auth)
            vault_namespace: Vault namespace for enterprise
            role_id: AppRole Role ID (for approle auth)
            secret_id: AppRole Secret ID (for approle auth)
            auth_method: Authentication method (token, approle)
            mount_point: KV secrets engine mount point
            kv_version: KV secrets engine version (1 or 2)
            verify_ssl: Verify SSL certificates
            timeout: Request timeout in seconds
            instance_name: Unique name for this Vault instance
        """
        self.vault_url = vault_url or os.getenv("VAULT_ADDR", "http://localhost:8200")
        self.vault_namespace = vault_namespace or os.getenv("VAULT_NAMESPACE")
        self.auth_method = auth_method
        self.mount_point = mount_point
        self.kv_version = kv_version
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.instance_name = instance_name
        
        # Remove trailing slash from URL
        self.vault_url = self.vault_url.rstrip("/")
        
        # Authentication credentials
        self.vault_token = vault_token
        self.role_id = role_id
        self.secret_id = secret_id
        
        # Token metadata cache
        self._token_metadata = None
        self._token_metadata_expires = None
        
        # Authenticate if using AppRole
        if self.auth_method == "approle" and self.role_id and self.secret_id:
            self._authenticate_approle()
        
    def _authenticate_approle(self):
        """Authenticate using AppRole and obtain token"""
        try:
            api_path = "/v1/auth/approle/login"
            data = {
                "role_id": self.role_id,
                "secret_id": self.secret_id
            }
            
            response = self._make_request("POST", api_path, data=data, use_auth=False)
            self.vault_token = response.get("auth", {}).get("client_token")
            
            if not self.vault_token:
                raise VaultError(f"Failed to obtain token from AppRole authentication for instance '{self.instance_name}'")
                
        except Exception as e:
            raise VaultError(f"AppRole authentication failed for instance '{self.instance_name}': {str(e)}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for Vault requests"""
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.vault_token:
            headers["X-Vault-Token"] = self.vault_token
        
        if self.vault_namespace:
            headers["X-Vault-Namespace"] = self.vault_namespace
            
        return headers
    
    def _make_request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        use_auth: bool = True
    ) -> Dict[str, Any]:
        """Make HTTP request to Vault"""
        url = f"{self.vault_url}{path}"
        
        try:
            with httpx.Client(verify=self.verify_ssl, timeout=self.timeout) as client:
                headers = self._get_headers() if use_auth else {"Content-Type": "application/json"}
                
                response = client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    params=params
                )
                
                # Check for errors
                if response.status_code >= 400:
                    error_msg = f"Vault request failed for instance '{self.instance_name}': {response.status_code}"
                    try:
                        error_data = response.json()
                        if "errors" in error_data:
                            error_msg += f" - {', '.join(error_data['errors'])}"
                    except:
                        error_msg += f" - {response.text}"
                    raise VaultError(error_msg, response.status_code)
                
                # Return empty dict for 204 No Content
                if response.status_code == 204:
                    return {}
                    
                return response.json()
                
        except httpx.RequestError as e:
            raise VaultError(f"Vault connection error for instance '{self.instance_name}': {str(e)}")
    
    def health_check(self) -> Dict[str, Any]:
        """Check Vault server health"""
        try:
            response = self._make_request("GET", "/v1/sys/health", use_auth=False)
            return {
                "instance_name": self.instance_name,
                "healthy": True,
                "initialized": response.get("initialized", False),
                "sealed": response.get("sealed", True),
                "version": response.get("version", "unknown"),
                "vault_url": self.vault_url
            }
        except VaultError as e:
            return {
                "instance_name": self.instance_name,
                "healthy": False,
                "error": str(e),
                "vault_url": self.vault_url
            }
    
    def read_secret(
        self,
        path: str,
        version: Optional[int] = None
    ) -> Dict[str, Any]:
        """Read a secret from Vault KV store"""
        if self.kv_version == 2:
            # KV v2 uses /data/ in the path
            api_path = f"/v1/{self.mount_point}/data/{path}"
            params = {"version": version} if version else None
            response = self._make_request("GET", api_path, params=params)
            
            # KV v2 wraps data in metadata
            return response.get("data", {}).get("data", {})
        else:
            # KV v1 direct path
            api_path = f"/v1/{self.mount_point}/{path}"
            response = self._make_request("GET", api_path)
            return response.get("data", {})
    
    def write_secret(
        self,
        path: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Write a secret to Vault KV store"""
        if self.kv_version == 2:
            api_path = f"/v1/{self.mount_point}/data/{path}"
            payload = {"data": data}
        else:
            api_path = f"/v1/{self.mount_point}/{path}"
            payload = data
            
        response = self._make_request("POST", api_path, data=payload)
        return response.get("data", {})
    
    def list_secrets(self, path: str = "") -> List[str]:
        """List secrets at a given path"""
        if self.kv_version == 2:
            api_path = f"/v1/{self.mount_point}/metadata/{path}"
        else:
            api_path = f"/v1/{self.mount_point}/{path}"
            
        response = self._make_request("LIST", api_path)
        return response.get("data", {}).get("keys", [])
    
    def resolve_secret_reference(
        self,
        reference: str
    ) -> Any:
        """
        Resolve a Vault secret reference to its value
        
        Supports formats:
        - secret/path#key
        - secret/path (returns entire secret)
        - secret/path#key@version (specific version)
        
        Args:
            reference: Vault reference string
            
        Returns:
            Secret value
        """
        # Parse version if specified
        version = None
        if "@" in reference:
            reference, version_str = reference.rsplit("@", 1)
            version = int(version_str)
        
        # Parse key if specified
        key = None
        if "#" in reference:
            path, key = reference.rsplit("#", 1)
        else:
            path = reference
        
        # Read the secret
        secret_data = self.read_secret(path, version=version)
        
        # Return specific key or entire secret
        if key:
            if key not in secret_data:
                raise VaultError(f"Key '{key}' not found in secret at path '{path}' in instance '{self.instance_name}'")
            return secret_data[key]
        else:
            return secret_data


class VaultError(Exception):
    """Exception raised for Vault-related errors"""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class MultiVaultManager:
    """Manager for multiple Vault instances"""
    
    def __init__(self):
        self.vault_instances: Dict[str, VaultClient] = {}
    
    def add_vault_instance(
        self,
        instance_name: str,
        vault_url: str,
        auth_method: str = "token",
        vault_token: str = None,
        role_id: str = None,
        secret_id: str = None,
        vault_namespace: str = None,
        mount_point: str = "secret",
        kv_version: int = 2,
        verify_ssl: bool = True
    ) -> VaultClient:
        """Add a new Vault instance to the manager"""
        client = VaultClient(
            vault_url=vault_url,
            vault_token=vault_token,
            vault_namespace=vault_namespace,
            role_id=role_id,
            secret_id=secret_id,
            auth_method=auth_method,
            mount_point=mount_point,
            kv_version=kv_version,
            verify_ssl=verify_ssl,
            instance_name=instance_name
        )
        
        self.vault_instances[instance_name] = client
        return client
    
    def get_vault_instance(self, instance_name: str) -> Optional[VaultClient]:
        """Get a Vault instance by name"""
        return self.vault_instances.get(instance_name)
    
    def read_secret(
        self,
        instance_name: str,
        path: str,
        key: Optional[str] = None,
        version: Optional[int] = None
    ) -> Any:
        """Read a secret from a specific Vault instance"""
        vault_client = self.get_vault_instance(instance_name)
        if not vault_client:
            raise VaultError(f"Vault instance '{instance_name}' not found")
        
        reference = path
        if key:
            reference += f"#{key}"
        if version:
            reference += f"@{version}"
        
        return vault_client.resolve_secret_reference(reference)
    
    def health_check_all(self) -> Dict[str, Any]:
        """Check health of all Vault instances"""
        results = {}
        for name, client in self.vault_instances.items():
            results[name] = client.health_check()
        return results
    
    def list_instances(self) -> List[str]:
        """List all registered Vault instances"""
        return list(self.vault_instances.keys())
