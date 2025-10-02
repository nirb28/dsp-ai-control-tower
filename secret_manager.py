"""
Unified Secret Manager for DSP AI Control Tower
Resolves secrets from multiple sources: Vault instances, config files, OS environment, encrypted storage
"""

import os
import json
from typing import Any, Dict, Optional
from pathlib import Path
from vault_client import MultiVaultManager, VaultError
from encryption_utils import get_encryption_manager, EncryptionManager


class SecretSource:
    """Enumeration of secret sources"""
    VAULT = "vault"
    CONFIG_FILE = "config"
    ENVIRONMENT = "env"
    ENCRYPTED = "encrypted"
    LITERAL = "literal"


class SecretManager:
    """Unified manager for resolving secrets from multiple sources"""
    
    def __init__(
        self,
        vault_manager: Optional[MultiVaultManager] = None,
        config_file_path: Optional[str] = None,
        encryption_key: Optional[str] = None
    ):
        """
        Initialize Secret Manager
        
        Args:
            vault_manager: Multi-vault manager instance
            config_file_path: Path to secrets configuration file
            encryption_key: Encryption key for encrypted secrets
        """
        self.vault_manager = vault_manager or MultiVaultManager()
        self.config_file_path = config_file_path
        self.config_data = {}
        self.encryption_manager: Optional[EncryptionManager] = None
        
        # Load config file if provided
        if config_file_path and os.path.exists(config_file_path):
            self._load_config_file()
        
        # Initialize encryption manager if key provided
        if encryption_key or os.getenv("ENCRYPTION_KEY"):
            try:
                self.encryption_manager = get_encryption_manager(encryption_key)
            except ValueError:
                # Encryption key not available, continue without encryption support
                pass
    
    def _load_config_file(self):
        """Load secrets from configuration file"""
        try:
            with open(self.config_file_path, 'r') as f:
                self.config_data = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load config file '{self.config_file_path}': {str(e)}")
    
    def resolve_secret(self, reference: str) -> Any:
        """
        Resolve a secret reference from any supported source
        
        Supported formats:
        - vault:instance_name:secret/path#key[@version]
        - config:section.subsection.key
        - env:ENVIRONMENT_VARIABLE_NAME
        - encrypted:base64_encrypted_value
        - literal:plain_text_value (or just plain_text_value)
        
        Args:
            reference: Secret reference string
            
        Returns:
            Resolved secret value
        """
        if not isinstance(reference, str):
            return reference
        
        # Determine source and resolve
        if reference.startswith("vault:"):
            return self._resolve_vault_secret(reference[6:])
        elif reference.startswith("config:"):
            return self._resolve_config_secret(reference[7:])
        elif reference.startswith("env:"):
            return self._resolve_env_secret(reference[4:])
        elif reference.startswith("encrypted:"):
            return self._resolve_encrypted_secret(reference)
        elif reference.startswith("literal:"):
            return reference[8:]  # Return literal value without prefix
        else:
            # Try to detect if it's an encrypted value without prefix
            if self.encryption_manager and self.encryption_manager.is_encrypted(reference):
                return self._resolve_encrypted_secret(reference)
            # Otherwise return as literal
            return reference
    
    def _resolve_vault_secret(self, reference: str) -> Any:
        """
        Resolve secret from Vault
        
        Format: instance_name:secret/path#key[@version]
        """
        # Parse instance name
        if ":" not in reference:
            raise ValueError(f"Invalid Vault reference format. Expected 'instance_name:path', got '{reference}'")
        
        instance_name, secret_ref = reference.split(":", 1)
        
        # Parse version if specified
        version = None
        if "@" in secret_ref:
            secret_ref, version_str = secret_ref.rsplit("@", 1)
            version = int(version_str)
        
        # Parse key if specified
        key = None
        if "#" in secret_ref:
            path, key = secret_ref.rsplit("#", 1)
        else:
            path = secret_ref
        
        # Read from Vault
        try:
            return self.vault_manager.read_secret(
                instance_name=instance_name,
                path=path,
                key=key,
                version=version
            )
        except VaultError as e:
            raise ValueError(f"Failed to resolve Vault secret '{reference}': {str(e)}")
    
    def _resolve_config_secret(self, reference: str) -> Any:
        """
        Resolve secret from configuration file
        
        Format: section.subsection.key (dot-separated path)
        """
        keys = reference.split(".")
        value = self.config_data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                raise ValueError(f"Config key '{reference}' not found in configuration file")
        
        # If value is encrypted, decrypt it
        if self.encryption_manager and isinstance(value, str) and self.encryption_manager.is_encrypted(value):
            return self.encryption_manager.decrypt(value)
        
        return value
    
    def _resolve_env_secret(self, reference: str) -> str:
        """
        Resolve secret from OS environment variable
        
        Format: VARIABLE_NAME
        """
        value = os.getenv(reference)
        
        if value is None:
            raise ValueError(f"Environment variable '{reference}' not found")
        
        # If value is encrypted, decrypt it
        if self.encryption_manager and self.encryption_manager.is_encrypted(value):
            return self.encryption_manager.decrypt(value)
        
        return value
    
    def _resolve_encrypted_secret(self, reference: str) -> str:
        """
        Resolve encrypted secret
        
        Format: encrypted:base64_encrypted_value
        """
        if not self.encryption_manager:
            raise ValueError("Encryption manager not initialized. Set ENCRYPTION_KEY environment variable")
        
        return self.encryption_manager.decrypt(reference)
    
    def resolve_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively resolve all secret references in a dictionary
        
        Args:
            data: Dictionary containing secret references
            
        Returns:
            Dictionary with resolved secrets
        """
        resolved = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                resolved[key] = self.resolve_secret(value)
            elif isinstance(value, dict):
                resolved[key] = self.resolve_dict(value)
            elif isinstance(value, list):
                resolved[key] = [
                    self.resolve_dict(item) if isinstance(item, dict)
                    else self.resolve_secret(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                resolved[key] = value
        
        return resolved
    
    def add_vault_instance_from_config(self, config: Dict[str, Any]) -> str:
        """
        Add a Vault instance from configuration dictionary
        
        Args:
            config: Vault configuration dictionary
            
        Returns:
            Instance name
        """
        instance_name = config.get("instance_name", "default")
        
        # Resolve credentials from their sources
        vault_token = None
        role_id = None
        secret_id = None
        
        if "vault_token" in config:
            vault_token = self.resolve_secret(config["vault_token"])
        
        if "role_id" in config:
            role_id = self.resolve_secret(config["role_id"])
        
        if "secret_id" in config:
            secret_id = self.resolve_secret(config["secret_id"])
        
        self.vault_manager.add_vault_instance(
            instance_name=instance_name,
            vault_url=config.get("vault_url"),
            auth_method=config.get("auth_method", "token"),
            vault_token=vault_token,
            role_id=role_id,
            secret_id=secret_id,
            vault_namespace=config.get("vault_namespace"),
            mount_point=config.get("kv_mount_point", "secret"),
            kv_version=config.get("kv_version", 2),
            verify_ssl=config.get("verify_ssl", True)
        )
        
        return instance_name


# Singleton instance
_secret_manager: Optional[SecretManager] = None


def get_secret_manager(
    vault_manager: Optional[MultiVaultManager] = None,
    config_file_path: Optional[str] = None,
    encryption_key: Optional[str] = None,
    force_new: bool = False
) -> SecretManager:
    """Get or create secret manager instance"""
    global _secret_manager
    
    if force_new or _secret_manager is None:
        _secret_manager = SecretManager(
            vault_manager=vault_manager,
            config_file_path=config_file_path,
            encryption_key=encryption_key
        )
    
    return _secret_manager
