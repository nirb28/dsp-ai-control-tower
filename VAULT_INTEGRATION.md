# Multi-Vault Secret Management System

## Overview

The DSP AI Control Tower now supports comprehensive secret management from multiple sources:
- **Multiple HashiCorp Vault instances** with different authentication methods
- **Configuration files** with encrypted secrets
- **OS environment variables**
- **Encrypted storage** for sensitive values

## Secret Reference Formats

### 1. Vault Secrets
```
vault:instance_name:secret/path#key[@version]
```

Examples:
- `vault:prod-vault:myapp/database#password`
- `vault:dev-vault:api-keys/groq#api_key`
- `vault:prod-vault:jwt#secret@5`

### 2. Configuration File Secrets
```
config:section.subsection.key
```

Examples:
- `config:database.prod.password`
- `config:api_keys.groq`

### 3. Environment Variables
```
env:VARIABLE_NAME
```

Examples:
- `env:PROD_VAULT_TOKEN`
- `env:DATABASE_PASSWORD`

### 4. Encrypted Values
```
encrypted:base64_encrypted_string
```

### 5. Literal Values
```
literal:plain_text_value
```

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Generate Encryption Key
```bash
curl -X POST "http://localhost:8000/encryption/generate-key" \
  -H "X-DSPAI-Client-Secret: your-superuser-secret"
```

Set as environment variable:
```bash
export ENCRYPTION_KEY="your-generated-key"
```

### 3. Encrypt Sensitive Values
```bash
curl -X POST "http://localhost:8000/encryption/encrypt" \
  -H "X-DSPAI-Client-Secret: your-superuser-secret" \
  -H "Content-Type: application/json" \
  -d '{"plaintext": "my-secret-value"}'
```

### 4. Configure Vault Module in Manifest

```json
{
  "module_type": "vault",
  "name": "vault-manager",
  "config": {
    "vault_instances": [
      {
        "instance_name": "prod-vault",
        "vault_url": "https://vault-prod.example.com:8200",
        "auth_method": "approle",
        "role_id": "env:PROD_VAULT_ROLE_ID",
        "secret_id": "env:PROD_VAULT_SECRET_ID",
        "kv_mount_point": "secret",
        "kv_version": 2
      }
    ],
    "vault_config_file": "vault_config.json",
    "secrets_config_file": "secrets_config.json"
  }
}
```

## API Endpoints

### Initialize Vault System
```bash
POST /vault/initialize?project_id=my-project
```

### Check Vault Health
```bash
GET /vault/health?project_id=my-project
```

### Read Secret from Vault
```bash
POST /vault/read-secret
{
  "project_id": "my-project",
  "instance_name": "prod-vault",
  "secret_path": "myapp/database",
  "key": "password"
}
```

### Get Resolved Manifest
```bash
GET /manifests/my-project?resolve_env=true
```

## Security Best Practices

1. **Never commit secrets** - Use .gitignore
2. **Encrypt all sensitive values**
3. **Use environment variables** for Vault credentials
4. **Rotate secrets regularly**
5. **Use AppRole for production**
6. **Enable SSL verification**
7. **Limit token TTL**
8. **Audit secret access**

## Files Created

- `vault_client.py` - Multi-instance Vault client
- `encryption_utils.py` - Encryption/decryption utilities
- `secret_manager.py` - Unified secret resolution
- `vault_config.json` - External Vault configuration
- `secrets_config.json` - Fallback secrets configuration
- `manifests/multi-vault-example.json` - Example manifest

## Example Usage

See `manifests/multi-vault-example.json` for a complete example with:
- Multiple Vault instances
- Different authentication methods per instance
- Mixed secret sources (vault, config, env)
- Environment-specific configurations

For detailed troubleshooting and migration guides, see the inline documentation in the source files.
