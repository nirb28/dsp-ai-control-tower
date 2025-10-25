### 2. Set Environment Variables

Create `.env` file in both directories:

```bash
# Optional (defaults shown)
CONTROL_TOWER_URL=http://localhost:9000
FRONT_DOOR_URL=http://localhost:8080
JWT_SERVICE_URL=http://localhost:5000
```

### 3. Start Services

```bash
# Terminal 1: Control Tower
cd dsp-ai-control-tower
python app.py
# Runs on http://localhost:9000

# Terminal 2: JWT Service
cd dsp_ai_jwt
python app.py
# Runs on http://localhost:5000

# Terminal 3: APISIX (optional but recommended)
cd dsp-fd2
docker-compose -f docker-compose-apisix.yml up

# Terminal 4: Front Door
cd dsp-fd2
python run.py
# Runs on http://localhost:8080
```

### 4. Upload Manifest

```bash
cd dsp-ai-control-tower

# Upload the summarizer manifest
curl -X POST http://localhost:9000/manifests \
  -H "Content-Type: application/json" \
  -d @manifests/langgraph-summarizer.json
```

### 5. Run Example

```bash
cd dsp-ai-control-tower/examples
python langgraph_summarizer_example.py
```

Expected output:
```

## How It Works

### 1. JWT Authentication

```python
# Get token
response = httpx.post(
    f"{FRONT_DOOR_URL}/langgraph-summarizer/summarizer-auth/token",
    json={"username": "test_user", "password": "test_password"}
)
jwt_token = response.json()["access_token"]
```

### 2. Workflow Execution

```python
# Execute workflow
response = httpx.post(
    f"{FRONT_DOOR_URL}/langgraph-summarizer/workflow/doc-summarizer-workflow",
    headers={"Authorization": f"Bearer {jwt_token}"},
    json={"document": "Your text here..."}
)
result = response.json()
```

### 3. Get Results

```python
print(result["final_summary"])
print(result["metadata"])
```

## Customizing the Workflow

### Change Chunk Size

In manifest:
```json
{
  "id": "split_document",
  "config": {
    "chunk_size": 3000,  // Increase for larger chunks
    "chunk_overlap": 300
  }
}
```

### Change LLM Model

In manifest:
```json
{
  "module_type": "inference_endpoint",
  "config": {
    "model_name": "llama-3.1-8b-instant",  // Faster, cheaper
    "max_tokens": 500
  }
}
```

### Add Custom Processing

Create a new node:
```json
{
  "id": "custom_step",
  "type": "function",
  "function": "your_custom_function",
  "config": { "param": "value" }
}
```

Then implement in `src/modules/langgraph_workflow.py`:
```python
async def _your_custom_function(
    self,
    state: WorkflowState,
    config: Dict[str, Any]
) -> WorkflowState:
    # Your logic here
    return state
```
