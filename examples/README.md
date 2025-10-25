# LangGraph Examples

This directory contains working examples demonstrating LangGraph workflow usage.

## Available Examples

### 1. Document Summarizer (`langgraph_summarizer_example.py`)

**Purpose**: Demonstrates multi-step document summarization workflow with parallel processing.

**What it does**:
- Splits long documents into manageable chunks
- Summarizes each chunk in parallel using LLM
- Combines chunk summaries into final comprehensive summary

**Usage**:
```bash
# Make sure all services are running:
# - Control Tower (port 9000)
# - JWT Service (port 5000)
# - Front Door (port 8080)

# Then run:
python langgraph_summarizer_example.py
```

**Expected Output**:
```
================================================================================
🚀 LangGraph Document Summarizer Example
================================================================================

📝 Getting JWT token...
✅ JWT token obtained successfully

📄 Submitting document for summarization...
🔄 Executing workflow...
✅ Workflow completed successfully

📊 SUMMARIZATION RESULTS
...
```

## Prerequisites

### 1. Services Running

```bash
# Terminal 1: Control Tower
cd dsp-ai-control-tower
python app.py

# Terminal 2: JWT Service
cd dsp_ai_jwt
python app.py

# Terminal 3: Front Door
cd dsp-fd2
python run.py
```

### 2. Manifest Deployed

```bash
curl -X POST http://localhost:9000/manifests \
  -H "Content-Type: application/json" \
  -d @manifests/langgraph-summarizer.json
```

### 3. Environment Variables

Create `.env` file:
```bash
GROQ_API_KEY=your_groq_api_key_here
```

## Customizing Examples

### Change the Document

Edit the `SAMPLE_DOCUMENT` variable in the example file:

```python
SAMPLE_DOCUMENT = """
Your custom document text here...
"""
```

### Modify Configuration

Edit the manifest at `manifests/langgraph-summarizer.json`:

```json
{
  "chunk_size": 3000,     // Larger chunks
  "max_tokens": 1000,     // Longer summaries
  "temperature": 0.5      // More creative
}
```

### Use Different Model

In the manifest, change the model:

```json
{
  "model_name": "llama-3.1-8b-instant"  // Faster, cheaper
}
```

## Creating Your Own Examples

### Template Structure

```python
import httpx
import os

CONTROL_TOWER_URL = os.getenv("CONTROL_TOWER_URL", "http://localhost:9000")
FRONT_DOOR_URL = os.getenv("FRONT_DOOR_URL", "http://localhost:8080")
PROJECT_ID = "your-project-id"
JWT_MODULE = "your-jwt-module"
WORKFLOW_MODULE = "your-workflow-module"

class YourClient:
    def get_jwt_token(self):
        # Get JWT token from Front Door
        pass
    
    def execute_workflow(self, input_data):
        # Execute your workflow
        pass
    
    def display_results(self, result):
        # Display results
        pass

def main():
    client = YourClient()
    client.get_jwt_token()
    result = client.execute_workflow(input_data)
    client.display_results(result)

if __name__ == "__main__":
    main()
```
### "Workflow not found" Error

**Problem**: Manifest not deployed

**Solution**: Deploy the manifest
```bash
curl -X POST http://localhost:9000/manifests \
  -d @manifests/langgraph-summarizer.json
```
