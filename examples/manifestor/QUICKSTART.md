# Manifest Generator Quick Start Guide

Get started with the Manifest Generator in 5 minutes!

## Installation

```bash
# Navigate to the manifestor directory
cd examples/manifestor

# Optional: Install colorama for better visuals
pip install colorama
```

## Quick Start: Create Your First Manifest

### Step 1: Launch the Tool

**Windows:**
```bash
generate_manifest.bat
```

**Linux/Mac:**
```bash
chmod +x generate_manifest.sh
./generate_manifest.sh
```

**Or directly:**
```bash
cd examples/manifestor
python manifest_generator.py
```

### Step 2: Create a New Manifest

```
Main Menu:
  1. Create new manifest
  2. Load existing manifest
  3. Add module
  4. Remove module
  5. List modules
  6. Preview manifest
  7. Save manifest
  0. Exit

Select option: 1
```

Enter project details:
```
Project ID (unique identifier): my-first-project
Project Name: My First AI Project
Owner/Team [AI Team]: My Team
Description (optional): A simple LLM application
Version [1.0.0]: 
Target Environment [development]: 
Tags (comma-separated, optional): llm, demo
```

### Step 3: Add JWT Authentication Module

```
Select option: 3

SELECT MODULE TYPE
  1. JWT Authentication & Authorization (jwt_config)
  ...

Select module type: 1
```

Configure JWT:
```
Module name [dsp_ai_jwt]: my-auth
JWT Service URL [${environments.${environment}.urls.jwt_service_url}]: 
Consumer Key [my-auth-key]: 
Rate limit (requests/min) [100]: 
Token expiration (hours) [1]: 
Enable JWE encryption? [no]: 
```

### Step 4: Add Inference Endpoint

```
Select option: 3

Select module type: 7
```

Configure inference:
```
Module name [llm_service]: my-llm
Model name [llama-3.1-70b-versatile]: 
Endpoint URL [${environments.${environment}.urls.api_base_url}]: 
System prompt [You are a helpful AI assistant.]: You are an expert assistant.
Max tokens [2000]: 
Temperature [0.7]: 

Available modules for dependencies:
  1. my-auth (jwt_config)

Dependencies (comma-separated numbers, or leave empty): 1
```

### Step 5: Add Monitoring

```
Select option: 3

Select module type: 9
```

Configure monitoring:
```
Module name [monitoring]: my-monitoring
Monitoring provider [prometheus]: langfuse
Sample rate (0.0-1.0) [1.0]: 

Dependencies: 
```

### Step 6: Preview and Save

```
Select option: 6
```

Review the generated manifest, then:

```
Select option: 7
```

Your manifest is saved as `my-first-project.json`!

## Common Scenarios

### Scenario 1: Simple Chatbot

**Modules needed:**
1. JWT Config (authentication)
2. Inference Endpoint (LLM)
3. Monitoring (observability)

**Steps:**
1. Create manifest
2. Add JWT Config → name: `chatbot-auth`
3. Add Inference Endpoint → name: `chatbot-llm`, depends on: `chatbot-auth`
4. Add Monitoring → name: `chatbot-monitoring`
5. Save

### Scenario 2: RAG Application

**Modules needed:**
1. JWT Config
2. RAG Config
3. Model Server (embeddings)
4. Inference Endpoint
5. Monitoring

**Steps:**
1. Create manifest
2. Add JWT Config → `rag-auth`
3. Add Model Server → `rag-embeddings`
4. Add RAG Config → `rag-retrieval`, depends on: `rag-embeddings`
5. Add Inference Endpoint → `rag-llm`, depends on: `rag-auth`, `rag-retrieval`
6. Add Monitoring → `rag-monitoring`
7. Save

### Scenario 3: Production API with APISIX

**Modules needed:**
1. Vault (secrets)
2. JWT Config
3. Inference Endpoint
4. APISIX Gateway
5. Monitoring

**Steps:**
1. Create manifest
2. Add Vault → `prod-vault`
3. Add JWT Config → `prod-auth`, depends on: `prod-vault`
4. Add Inference Endpoint → `prod-llm`, depends on: `prod-auth`
5. Add APISIX Gateway → `prod-gateway`, depends on: `prod-auth`, `prod-llm`
6. Add Monitoring → `prod-monitoring`
7. Save

## Editing Existing Manifests

### Load and Modify

```
Select option: 2

AVAILABLE MANIFESTS
  1. my-first-project.json
  2. sas2py.json

Select manifest number to load: 1

✓ Loaded manifest: my-first-project.json
```

### Add a New Module

```
Select option: 3
```

Follow the prompts to add a new module.

### Remove a Module

```
Select option: 4

CURRENT MODULES
  1. my-auth                     (jwt_config)
  2. my-llm                      (inference_endpoint) → depends on: my-auth
  3. my-monitoring               (monitoring)

Select module number to remove: 1

⚠ The following modules depend on 'my-auth':
  - my-llm

Remove all dependent modules as well? [no]: yes

✓ Removed dependent module: my-llm
✓ Removed module: my-auth
```

### Save Changes

```
Select option: 7

File 'my-first-project.json' already exists. Overwrite? [no]: yes

✓ Manifest saved to: D:\...\manifests\my-first-project.json
```

## Tips for Success

### 1. Plan Your Architecture First

Before starting, sketch out:
- What modules you need
- Dependencies between them
- Environment-specific settings

### 2. Use Descriptive Names

Good names:
- `customer-service-auth`
- `invoice-processor-llm`
- `document-rag-retrieval`

Bad names:
- `auth1`
- `llm`
- `module`

### 3. Add Modules in Dependency Order

Always add dependencies before dependents:
1. ✓ Add `auth` first
2. ✓ Then add `llm` that depends on `auth`

Not:
1. ✗ Add `llm` first (can't set dependency)
2. ✗ Then add `auth`

### 4. Preview Before Saving

Always use option 6 to preview before option 7 to save.

### 5. Use Environment Variables

For secrets and URLs, use:
```
${environments.${environment}.secrets.api_key}
${environments.${environment}.urls.service_url}
```

## Keyboard Shortcuts

- **Ctrl+C**: Cancel operation and return to menu
- **Enter**: Accept default value
- **0**: Return to previous menu or exit

## Next Steps

After creating your manifest:

1. **Validate it:**
   ```bash
   curl -X POST http://localhost:8000/manifests/validate \
     -H "Content-Type: application/json" \
     -d @my-first-project.json
   ```

2. **Deploy it:**
   ```bash
   curl -X POST http://localhost:8000/manifests \
     -H "Content-Type: application/json" \
     -H "X-Superuser-Secret: your-secret" \
     -d @my-first-project.json
   ```

3. **Query modules:**
   ```bash
   curl http://localhost:8000/manifests/my-first-project/modules
   ```

## Troubleshooting

### "Module already exists"
- Use a different name or remove the existing module first

### "Cannot save: project_id is required"
- Create a new manifest (option 1) or load one (option 2) first

### "Invalid selection"
- Enter a valid number from the menu options

### Colors not showing
- Install colorama: `pip install colorama`

## Example Session

Here's a complete example session:

```
==================================================================
  Control Tower Manifest Generator
==================================================================

Main Menu:
  1. Create new manifest
  ...

Select option: 1

Project ID: demo-app
Project Name: Demo Application
Owner/Team [AI Team]: 
Environment [development]: 
Tags: demo, quickstart

✓ Manifest 'demo-app' initialized!

Select option: 3

SELECT MODULE TYPE
  1. JWT Authentication & Authorization
  ...

Select module type: 1

Module name [dsp_ai_jwt]: demo-auth
JWT Service URL: http://localhost:5000
Consumer Key [demo-auth-key]: 
Rate limit [100]: 50
Token expiration [1]: 2
Enable JWE? [no]: 

✓ Module 'demo-auth' added successfully!

Select option: 7

✓ Manifest saved to: demo-app.json

Select option: 0

Goodbye!
```

## Getting Help

- Read the full documentation: `README_MANIFEST_GENERATOR.md`
- Check example manifests in the `manifests/` directory
- Review module schemas in `app.py`

Happy manifest building! 🚀
