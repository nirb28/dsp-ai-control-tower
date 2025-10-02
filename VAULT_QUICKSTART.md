# Vault Integration Quick Start Guide

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Setup Steps

### 1. Generate Encryption Key

```bash
# Start the server
python app.py

# In another terminal, generate key
curl -X POST "http://localhost:8000/encryption/generate-key" \
  -H "X-DSPAI-Client-Secret: your-superuser-secret"
```

**Save the returned key:**
```bash
# Windows PowerShell
$env:ENCRYPTION_KEY="your-generated-key-here"

# Windows CMD
set ENCRYPTION_KEY=your-generated-key-here

# Linux/Mac
export ENCRYPTION_KEY="your-generated-key-here"
```

### 2. Encrypt Your Secrets

```bash
# Encrypt a secret
curl -X POST "http://localhost:8000/encryption/encrypt" \
  -H "X-DSPAI-Client-Secret: your-superuser-secret" \
  -H "Content-Type: application/json" \
  -d "{\"plaintext\": \"my-secret-password\"}"

# Response:
# {
#   "plaintext": "my-secret-password",
#   "encrypted": "encrypted:gAAAAABh..."
# }
```

### 3. Configure Your Vault Instances

Edit `vault_config.json`:
```json
{
  "vault_instances": [
    {
      "instance_name": "prod-vault",
      "vault_url": "https://your-vault-url:8200",
      "auth_method": "approle",
      "role_id": "env:PROD_VAULT_ROLE_ID",
      "secret_id": "env:PROD_VAULT_SECRET_ID",
      "kv_mount_point": "secret",
      "kv_version": 2
    }
  ]
}
```

### 4. Add Secrets to Config File

Edit `secrets_config.json`:
```json
{
  "database": {
    "prod": {
      "password": "encrypted:gAAAAABh..."
    }
  },
  "api_keys": {
    "groq": "encrypted:gAAAAABh..."
  }
}
```

### 5. Create Manifest with Vault Module

```json
{
  "project_id": "my-project",
  "modules": [
    {
      "module_type": "vault",
      "name": "vault-manager",
      "config": {
        "vault_instances": [],
        "vault_config_file": "vault_config.json",
        "secrets_config_file": "secrets_config.json"
      }
    },
    {
      "module_type": "jwt_config",
      "name": "auth",
      "config": {
        "secret_key": "vault:prod-vault:myapp/jwt#secret_key"
      }
    }
  ]
}
```

## Secret Reference Examples

```json
{
  "password": "vault:prod-vault:myapp/database#password",
  "api_key": "config:api_keys.groq",
  "token": "env:MY_TOKEN",
  "encrypted_value": "encrypted:gAAAAABh...",
  "plain_value": "literal:some-value"
}
```

## Testing

```bash
# Initialize Vault system
curl -X POST "http://localhost:8000/vault/initialize?project_id=my-project" \
  -H "X-DSPAI-Client-Secret: your-superuser-secret"

# Check health
curl -X GET "http://localhost:8000/vault/health?project_id=my-project" \
  -H "X-DSPAI-Client-Secret: your-superuser-secret"

# Get resolved manifest (all secrets decrypted)
curl -X GET "http://localhost:8000/manifests/my-project?resolve_env=true"
```

## Environment Variables Needed

```bash
# Required
ENCRYPTION_KEY=your-encryption-key

# For Vault instances using token auth
DEV_VAULT_TOKEN=your-dev-token

# For Vault instances using AppRole auth
PROD_VAULT_ROLE_ID=your-role-id
PROD_VAULT_SECRET_ID=your-secret-id
```

## Common Patterns

### Multiple Vault Instances
```json
{
  "vault_instances": [
    {
      "instance_name": "prod-vault",
      "vault_url": "https://vault-prod.example.com:8200",
      "auth_method": "approle",
      "role_id": "env:PROD_VAULT_ROLE_ID",
      "secret_id": "env:PROD_VAULT_SECRET_ID"
    },
    {
      "instance_name": "dev-vault",
      "vault_url": "https://vault-dev.example.com:8200",
      "auth_method": "token",
      "vault_token": "env:DEV_VAULT_TOKEN"
    }
  ]
}
```

### Environment-Specific Secrets
```json
{
  "environments": {
    "production": {
      "secrets": {
        "db_password": "vault:prod-vault:myapp/prod/db#password"
      }
    },
    "development": {
      "secrets": {
        "db_password": "config:database.dev.password"
      }
    }
  }
}
```

## Troubleshooting

### "Encryption key not provided"
Set the `ENCRYPTION_KEY` environment variable.

### "Vault instance not found"
Check that the instance name in your reference matches the `instance_name` in your config.

### "Failed to resolve Vault secret"
- Verify Vault URL is accessible
- Check authentication credentials (role_id, secret_id, or token)
- Ensure secret path exists in Vault
- Verify KV version matches your Vault configuration

### "Config key not found"
Check that the path in `secrets_config.json` matches your reference.

## Security Checklist

- [ ] `ENCRYPTION_KEY` set as environment variable
- [ ] `vault_config.json` added to `.gitignore`
- [ ] `secrets_config.json` added to `.gitignore`
- [ ] All sensitive values encrypted
- [ ] Vault credentials stored as environment variables
- [ ] SSL verification enabled for production Vault instances
- [ ] AppRole used for production (not token auth)

## Next Steps

1. See `VAULT_INTEGRATION.md` for complete documentation
2. Review `manifests/multi-vault-example.json` for full example
3. Check API documentation at `http://localhost:8000/docs`
