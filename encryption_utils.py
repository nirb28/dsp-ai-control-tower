"""
Encryption utilities for securing stored secrets
Uses Fernet symmetric encryption (AES-128 in CBC mode)
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from typing import Optional


class EncryptionManager:
    """Manager for encrypting and decrypting sensitive data"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption manager
        
        Args:
            encryption_key: Base64-encoded encryption key or passphrase
                          If None, uses ENCRYPTION_KEY environment variable
        """
        key = encryption_key or os.getenv("ENCRYPTION_KEY")
        
        if not key:
            raise ValueError("Encryption key not provided. Set ENCRYPTION_KEY environment variable or pass encryption_key parameter")
        
        # If key looks like a passphrase (not base64), derive a key from it
        if not self._is_base64_key(key):
            self.fernet = Fernet(self._derive_key_from_passphrase(key))
        else:
            self.fernet = Fernet(key.encode() if isinstance(key, str) else key)
    
    @staticmethod
    def _is_base64_key(key: str) -> bool:
        """Check if key is a valid base64-encoded Fernet key"""
        try:
            decoded = base64.urlsafe_b64decode(key)
            return len(decoded) == 32  # Fernet keys are 32 bytes
        except:
            return False
    
    @staticmethod
    def _derive_key_from_passphrase(passphrase: str, salt: Optional[bytes] = None) -> bytes:
        """Derive a Fernet key from a passphrase using PBKDF2"""
        if salt is None:
            # Use a fixed salt for deterministic key derivation
            # In production, you might want to store this salt securely
            salt = b'dsp-ai-control-tower-salt-v1'
        
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
        return key
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet encryption key"""
        return Fernet.generate_key().decode()
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64-encoded encrypted string with 'encrypted:' prefix
        """
        if not plaintext:
            return plaintext
        
        encrypted_bytes = self.fernet.encrypt(plaintext.encode())
        encrypted_str = encrypted_bytes.decode()
        
        # Add prefix to identify encrypted values
        return f"encrypted:{encrypted_str}"
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string
        
        Args:
            ciphertext: Encrypted string (with or without 'encrypted:' prefix)
            
        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return ciphertext
        
        # Remove prefix if present
        if ciphertext.startswith("encrypted:"):
            ciphertext = ciphertext[10:]  # Remove 'encrypted:' prefix
        
        try:
            decrypted_bytes = self.fernet.decrypt(ciphertext.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt value: {str(e)}")
    
    def is_encrypted(self, value: str) -> bool:
        """Check if a value is encrypted"""
        return isinstance(value, str) and value.startswith("encrypted:")
    
    def encrypt_dict(self, data: dict, keys_to_encrypt: list = None) -> dict:
        """
        Encrypt specific keys in a dictionary
        
        Args:
            data: Dictionary to encrypt
            keys_to_encrypt: List of keys to encrypt (if None, encrypts all string values)
            
        Returns:
            Dictionary with encrypted values
        """
        encrypted_data = {}
        
        for key, value in data.items():
            if keys_to_encrypt is None or key in keys_to_encrypt:
                if isinstance(value, str):
                    encrypted_data[key] = self.encrypt(value)
                elif isinstance(value, dict):
                    encrypted_data[key] = self.encrypt_dict(value, keys_to_encrypt)
                else:
                    encrypted_data[key] = value
            else:
                encrypted_data[key] = value
        
        return encrypted_data
    
    def decrypt_dict(self, data: dict, keys_to_decrypt: list = None) -> dict:
        """
        Decrypt specific keys in a dictionary
        
        Args:
            data: Dictionary to decrypt
            keys_to_decrypt: List of keys to decrypt (if None, decrypts all encrypted values)
            
        Returns:
            Dictionary with decrypted values
        """
        decrypted_data = {}
        
        for key, value in data.items():
            if isinstance(value, str) and self.is_encrypted(value):
                if keys_to_decrypt is None or key in keys_to_decrypt:
                    decrypted_data[key] = self.decrypt(value)
                else:
                    decrypted_data[key] = value
            elif isinstance(value, dict):
                decrypted_data[key] = self.decrypt_dict(value, keys_to_decrypt)
            else:
                decrypted_data[key] = value
        
        return decrypted_data


# Singleton instance
_encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager(encryption_key: Optional[str] = None) -> EncryptionManager:
    """Get or create encryption manager instance"""
    global _encryption_manager
    
    if _encryption_manager is None or encryption_key is not None:
        _encryption_manager = EncryptionManager(encryption_key)
    
    return _encryption_manager
