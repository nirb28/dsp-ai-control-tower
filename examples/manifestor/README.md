# Manifest Generator CLI

Interactive command-line utility for creating and managing Control Tower project manifests.

## Features

- **Interactive Manifest Creation**: Guided prompts for creating new manifests
- **Template-Based Configuration**: Pre-built templates for all 17 module types
- **Dependency Management**: Automatic tracking and validation of module dependencies
- **Smart Module Removal**: Removes dependent modules when removing a module
- **Load & Edit**: Load existing manifests and modify them
- **Preview**: View complete manifest before saving
- **Environment Configuration**: Automatic environment setup for dev/staging/prod

## Installation

### Prerequisites

```bash
# Optional: Install colorama for colored output
pip install colorama
```

The tool works without colorama but provides better visual feedback with it.

## Usage

### Starting the Tool

```bash
cd examples/manifestor
python manifest_generator.py
```

Or use the launcher scripts:
```bash
# Windows
generate_manifest.bat

# Linux/Mac
./generate_manifest.sh
```

**Note:** Manifests are saved to and loaded from the `manifests/` directory in the project root.

### Main Menu Options

1. **Create new manifest** - Start a new manifest from scratch
2. **Load existing manifest** - Load and edit an existing manifest file
3. **Add module** - Add a new module to the current manifest
4. **Remove module** - Remove a module and its dependents
5. **List modules** - View all modules in the current manifest
6. **Preview manifest** - View the complete manifest JSON
7. **Save manifest** - Save the manifest to a file
0. **Exit** - Exit the tool

## Supported Module Types

The generator supports all 17 Control Tower module types:

| # | Module Type | Description |
|---|-------------|-------------|
| 1 | jwt_config | JWT Authentication & Authorization |
| 2 | rag_config | RAG Configuration (Document Retrieval) |
| 3 | rag_service | RAG Service Module |
| 4 | model_server | Model Server (Embeddings, Reranking) |
| 5 | api_gateway | API Gateway (Generic) |
| 6 | api_gateway_apisix | API Gateway (APISIX) |
| 7 | inference_endpoint | LLM Inference Endpoint |
| 8 | security | Security & Compliance |
| 9 | monitoring | Monitoring & Observability |
| 10 | model_registry | Model Registry (MLflow, W&B) |
| 11 | data_pipeline | Data Pipeline (ETL/ELT) |
| 12 | deployment | Deployment Configuration |
| 13 | resource_management | Resource Management |
| 14 | notifications | Notifications & Alerts |
| 15 | backup_recovery | Backup & Recovery |
| 16 | vault | HashiCorp Vault Integration |
| 17 | langgraph_workflow | LangGraph Workflow |

## Workflow Examples

### Example 1: Create a Simple LLM Project

1. Start the tool: `python manifest_generator.py`
2. Select **1** (Create new manifest)
3. Enter project details:
   - Project ID: `my-llm-app`
   - Project Name: `My LLM Application`
   - Owner: `AI Team`
   - Environment: `development`
4. Select **3** (Add module)
5. Select **1** (JWT Config) and configure authentication
6. Select **3** (Add module) again
7. Select **7** (Inference Endpoint) and configure LLM
8. Select **3** (Add module) again
9. Select **9** (Monitoring) and configure observability
10. Select **6** (Preview) to review
11. Select **7** (Save) to save the manifest

### Example 2: Add APISIX Gateway to Existing Manifest

1. Start the tool: `python manifest_generator.py`
2. Select **2** (Load existing manifest)
3. Choose your manifest from the list
4. Select **3** (Add module)
5. Select **6** (API Gateway APISIX)
6. Configure the gateway with routes and plugins
7. When asked for dependencies, select existing modules
8. Select **7** (Save) to update the manifest

### Example 3: Remove a Module with Dependencies

1. Load your manifest
2. Select **4** (Remove module)
3. Select the module number to remove
4. If other modules depend on it, you'll see a warning:
   ```
   ⚠ The following modules depend on 'auth-service':
     - llm-inference
     - api-gateway
   
   Remove all dependent modules as well? [no]: yes
   ```
5. Confirm to remove all dependent modules
6. Save the updated manifest

## Module Templates

Each module type has a pre-configured template with sensible defaults. The tool will prompt you for:

### JWT Config Template
- JWT Service URL
- Consumer Key
- Rate Limit
- Token Expiration
- JWE Encryption (optional)

### RAG Config Template
- RAG Service URL
- Configuration Name
- Vector Store Type (FAISS, Redis, Elasticsearch, Neo4j)
- Embedding Model
- Chunk Size and Overlap
- Top K Results

### APISIX Gateway Template
- Route Name and URI
- Upstream URL
- Plugins (JWT Auth, Prometheus, etc.)
- Timeout Settings

### Inference Endpoint Template
- Model Name
- Endpoint URL
- System Prompt
- Max Tokens
- Temperature

### Monitoring Template
- Provider (Prometheus, Langfuse, Datadog)
- Logging Level
- Tracing Settings
- Health Check Interval

### Vault Template
- Instance Name
- Vault URL
- Auth Method (Token, AppRole)
- KV Mount Point
- SSL Verification

## Environment Variable Substitution

The generator automatically creates environment configurations with variable substitution:

```json
{
  "environments": {
    "development": {
      "urls": {
        "jwt_service_url": "http://localhost:5000",
        "api_base_url": "http://localhost:8000"
      },
      "secrets": {
        "jwe_encryption_key": "${DEV_JWE_KEY}"
      }
    },
    "production": {
      "urls": {
        "jwt_service_url": "https://jwt.example.com",
        "api_base_url": "https://api.example.com"
      },
      "secrets": {
        "jwe_encryption_key": "${PROD_JWE_KEY}"
      }
    }
  }
}
```

## Dependency Management

The tool automatically:

1. **Tracks Dependencies**: When adding a module, you can select which existing modules it depends on
2. **Validates Dependencies**: Ensures referenced modules exist
3. **Cascading Removal**: When removing a module, finds and removes all dependent modules
4. **Circular Detection**: Prevents circular dependencies

### Dependency Example

```
Module: llm-inference
  ↓ depends on
Module: auth-service
  ↓ depends on
Module: vault-secrets
```

If you remove `auth-service`, the tool will:
1. Detect that `llm-inference` depends on it
2. Warn you about the dependency
3. Offer to remove both modules together

## Tips and Best Practices

### 1. Start with Core Modules
Add modules in this order:
1. Vault (if using secrets)
2. JWT Config (authentication)
3. Monitoring (observability)
4. Inference Endpoints or RAG Config
5. API Gateway (routing)

### 2. Use Environment Variables
For sensitive data, use environment variable substitution:
- `${VARIABLE_NAME}` - Direct environment variable
- `${environments.${environment}.secrets.key}` - Environment-specific secrets
- `config:path.to.value` - Reference to config file

### 3. Consistent Naming
Use consistent naming patterns:
- `{project}-{module-type}` (e.g., `sas2py-auth`, `sas2py-convert`)
- Lowercase with hyphens
- Descriptive and unique

### 4. Preview Before Saving
Always preview your manifest before saving to catch:
- Missing dependencies
- Configuration errors
- Duplicate module names

### 5. Version Control
Save manifests to version control:
```bash
git add manifests/my-project.json
git commit -m "Add LLM inference configuration"
```

## Troubleshooting

### Issue: Module already exists
**Solution**: Use a different module name or remove the existing module first

### Issue: Cannot save manifest
**Solution**: Ensure you've created or loaded a manifest first (option 1 or 2)

### Issue: Dependency errors
**Solution**: Add modules in dependency order (dependencies first, then dependents)

### Issue: Colors not showing
**Solution**: Install colorama: `pip install colorama`

## Advanced Usage

### Batch Module Addition
You can add multiple modules in sequence without returning to the main menu:
1. Add first module
2. Immediately select option 3 again
3. Add next module
4. Repeat as needed

### Editing Existing Configurations
To modify a module's configuration:
1. Load the manifest
2. Remove the module (option 4)
3. Add it again with new configuration (option 3)
4. Save the manifest

### Template Customization
To customize templates, edit `manifest_templates.py`:
- Modify default values
- Add new prompts
- Change configuration structure

## File Structure

```
manifests/
├── manifest_generator.py      # Main CLI application
├── manifest_templates.py      # Module configuration templates
├── README_MANIFEST_GENERATOR.md  # This file
├── *.json                     # Generated manifest files
```

## Integration with Control Tower

Generated manifests can be used directly with the Control Tower API:

```bash
# Upload manifest to Control Tower
curl -X POST http://localhost:8000/manifests \
  -H "Content-Type: application/json" \
  -H "X-Superuser-Secret: your-secret" \
  -d @manifests/my-project.json
```

## Future Enhancements

Planned features:
- [ ] Manifest validation against schema
- [ ] Import from existing deployments
- [ ] Module templates from community
- [ ] Diff between manifest versions
- [ ] Export to Kubernetes manifests
- [ ] Interactive dependency graph visualization

## Support

For issues or questions:
1. Check the Control Tower documentation
2. Review example manifests in the `manifests/` directory
3. Examine the module data models in `app.py`

## License

Part of the DSP AI Control Tower project.
