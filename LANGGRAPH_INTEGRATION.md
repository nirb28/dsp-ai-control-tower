# LangGraph Workflow Integration

Modular LangGraph-based prompt chaining system integrated with the DSP AI Front Door, Control Tower, and JWT architecture.

## Overview

This integration enables building complex multi-step AI workflows using LangGraph, with full support for:

- **Prompt Chaining**: Sequential and parallel LLM calls
- **JWT Authentication**: Secure access through DSP AI JWT service
- **APISIX Routing**: Enterprise-grade API gateway for LLM requests
- **Manifest-Driven**: Configuration managed through Control Tower manifests
- **Modular Design**: Workflows defined as reusable modules

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Control Tower (CT)                          │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────────────┐   │
│  │  JWT Config  │  │   Inference   │  │  LangGraph        │   │
│  │   Module     │  │   Endpoint    │  │  Workflow Module  │   │
│  └──────────────┘  └───────────────┘  └───────────────────┘   │
│                    Manifest: langgraph-summarizer.json          │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Front Door (FD2)                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           LangGraph Workflow Module                      │   │
│  │  ┌────────────┐  ┌──────────────┐  ┌───────────────┐  │   │
│  │  │   Split    │→ │  Summarize   │→ │   Combine     │  │   │
│  │  │  Document  │  │   Chunks     │  │  Summaries    │  │   │
│  │  └────────────┘  └──────────────┘  └───────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                       APISIX Gateway                             │
│          (JWT Auth, Rate Limiting, Monitoring)                   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LLM Provider                           │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Control Tower Module Type

Added `LANGGRAPH_WORKFLOW` module type to Control Tower with configuration schema:

```python
class LangGraphWorkflowModule(BaseModel):
    workflow_name: str
    workflow_type: str  # sequential, parallel, conditional
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    state_schema: Dict[str, Any]
    jwt_module: Optional[str]
    inference_modules: List[str]
    max_iterations: int = 10
    timeout_seconds: int = 300
    enable_checkpointing: bool = False
    retry_on_error: bool = True
    max_retries: int = 3
    tracing_enabled: bool = True
    log_intermediate_results: bool = True
```

### 2. Manifest Configuration

The manifest defines all required modules and their relationships:

- **JWT Config Module**: Authentication configuration
- **Inference Endpoint Module**: LLM endpoint configuration
- **API Gateway Module**: APISIX routing configuration
- **LangGraph Workflow Module**: Workflow definition

Example: `manifests/langgraph-summarizer.json`

### 3. Front Door Module Implementation

Located at: `src/modules/langgraph_workflow.py`

Key features:
- Dynamic workflow graph construction from manifest
- Function nodes (split, combine, transform)
- LLM nodes with prompt templates
- Parallel execution support
- JWT-authenticated APISIX calls
- Error handling and retry logic
- Comprehensive logging

### 4. Workflow Nodes

**Function Nodes**:
```json
{
  "id": "split_document",
  "type": "function",
  "function": "split_into_chunks",
  "config": {
    "chunk_size": 2000,
    "chunk_overlap": 200
  }
}
```

**LLM Nodes**:
```json
{
  "id": "summarize_chunks",
  "type": "llm",
  "inference_module": "summarize-llm",
  "prompt_template": "Summarize: {chunk}",
  "config": {
    "parallel": true,
    "max_tokens": 300
  }
}
```

## Setup

### 1. Prerequisites

```bash
# Control Tower
cd dsp-ai-control-tower
pip install -r requirements.txt

# Front Door
cd dsp-fd2
pip install -r requirements.txt  # Now includes langgraph>=0.2.0
```

### 2. Environment Variables

Create `.env` file:

```bash
# Groq API Key
GROQ_API_KEY=your_groq_api_key_here

# Control Tower
CONTROL_TOWER_URL=http://localhost:9000

# Front Door
FRONT_DOOR_URL=http://localhost:8080

# JWT Service
JWT_SERVICE_URL=http://localhost:5000
```

### 3. Start Services

```bash
# Terminal 1: Start Control Tower
cd dsp-ai-control-tower
python app.py

# Terminal 2: Start JWT Service
cd dsp_ai_jwt
python app.py

# Terminal 3: Start APISIX (if using)
cd dsp-fd2
docker-compose -f docker-compose-apisix.yml up

# Terminal 4: Start Front Door
cd dsp-fd2
python run.py
```

### 4. Deploy Manifest

```bash
# Upload manifest to Control Tower
curl -X POST http://localhost:9000/manifests \
  -H "Content-Type: application/json" \
  -d @manifests/langgraph-summarizer.json
```

## Usage

### Python Client Example

```python
import httpx

# 1. Get JWT Token
token_response = httpx.post(
    "http://localhost:8080/langgraph-summarizer/summarizer-auth/token",
    json={"username": "test_user", "password": "test_password"}
)
jwt_token = token_response.json()["access_token"]

# 2. Execute Workflow
workflow_response = httpx.post(
    "http://localhost:8080/langgraph-summarizer/workflow/doc-summarizer-workflow",
    headers={"Authorization": f"Bearer {jwt_token}"},
    json={
        "document": "Your long document text here...",
        "workflow_params": {}
    }
)

# 3. Get Results
result = workflow_response.json()
print(result["final_summary"])
```

### Running the Example

```bash
cd dsp-ai-control-tower/examples
python langgraph_summarizer_example.py
```

## Workflow State Management

LangGraph workflows maintain state throughout execution:

```python
class WorkflowState(TypedDict):
    messages: List[Dict[str, Any]]  # Message history
    document: str                    # Input document
    chunks: List[str]                # Document chunks
    summaries: List[str]             # Chunk summaries
    final_summary: str               # Final result
    error: Optional[str]             # Error tracking
    metadata: Dict[str, Any]         # Execution metadata
```

## Node Types

### 1. Function Nodes

Built-in functions:
- `split_into_chunks`: Split text by size with overlap
- `combine_results`: Merge multiple outputs

Custom functions can be added to `_get_node_function()`.

### 2. LLM Nodes

Features:
- Prompt template with variable substitution
- Parallel execution for batch processing
- Configurable model parameters
- Automatic retry on failure
- JWT-authenticated API calls through APISIX

## Parallel Execution

For chunk processing:

```json
{
  "id": "summarize_chunks",
  "type": "llm",
  "config": {
    "parallel": true,
    "batch_size": 5
  }
}
```

Processes chunks in parallel batches of 5 for faster execution.

## Error Handling

Workflow module includes:
- Node-level error catching
- Configurable retry logic
- Error state tracking
- Graceful degradation

Configuration:
```json
{
  "retry_on_error": true,
  "max_retries": 3,
  "timeout_seconds": 300
}
```

## Monitoring & Observability

### Logging

Each node logs:
- Execution start/completion
- Input/output data (if enabled)
- Errors and retries
- Performance metrics

### Tracing

Enable workflow tracing:
```json
{
  "tracing_enabled": true,
  "log_intermediate_results": true
}
```

### Metrics

Available through Front Door health check:
```bash
curl http://localhost:8080/health
```

## Advanced Workflows

### Conditional Branching

Define conditional edges:
```json
{
  "edges": [
    {
      "from": "analyze",
      "to": "route_decision",
      "condition": "check_quality"
    }
  ]
}
```

### Iterative Refinement

Use `max_iterations` for iterative workflows:
```json
{
  "max_iterations": 5,
  "edges": [
    {
      "from": "refine",
      "to": "evaluate",
      "condition": "needs_improvement"
    },
    {
      "from": "evaluate",
      "to": "refine"
    }
  ]
}
```

## Security

### JWT Authentication

All workflow requests require valid JWT tokens:
1. Client requests token from FD JWT endpoint
2. Token includes project-specific claims
3. APISIX validates token on each LLM call
4. Rate limiting applied per token

### APISIX Integration

Benefits:
- Centralized authentication
- Rate limiting per user/endpoint
- Request/response transformation
- Monitoring and metrics
- Load balancing across LLM providers

## Performance Optimization

### Chunk Size Tuning

Balance between:
- **Smaller chunks**: More API calls, better parallelization
- **Larger chunks**: Fewer calls, more context per summary

Recommended:
```json
{
  "chunk_size": 2000,
  "chunk_overlap": 200,
  "parallel": true,
  "batch_size": 5
}
```

### Caching

Implement caching in workflow nodes:
```python
async def cached_node(state: WorkflowState) -> WorkflowState:
    cache_key = hash(state["input"])
    if cached := await get_cache(cache_key):
        return cached
    result = await process(state)
    await set_cache(cache_key, result)
    return result
```

## Troubleshooting

### Common Issues

**1. JWT Token Expired**
```python
# Solution: Refresh token before workflow execution
if token_expired(jwt_token):
    jwt_token = get_new_token()
```

**2. APISIX Connection Failed**
```bash
# Check APISIX is running
curl http://localhost:9180/apisix/admin/routes
```

**3. LLM API Timeout**
```json
{
  "timeout_seconds": 600,  // Increase timeout
  "max_retries": 5
}
```

## Extension Points

### Custom Node Functions

Add new functions to `langgraph_workflow.py`:

```python
async def _custom_transform(
    self,
    state: WorkflowState,
    config: Dict[str, Any]
) -> WorkflowState:
    # Your transformation logic
    return state

# Register in _get_node_function
functions = {
    "split_into_chunks": self._split_into_chunks,
    "custom_transform": self._custom_transform,
}
```

### Custom Workflows

Create new manifest with different node configurations:
- Question answering with RAG
- Code generation with testing
- Multi-agent debates
- Iterative refinement loops

## Best Practices

1. **Modularity**: Keep workflows focused on single tasks
2. **Reusability**: Define common nodes in templates
3. **Error Handling**: Always include error states
4. **Logging**: Enable for debugging, disable in production
5. **Testing**: Test workflows with various input sizes
6. **Monitoring**: Track execution time and token usage
7. **Security**: Never log sensitive data
8. **Documentation**: Document node purposes and configs

## Example Workflows

### Document Summarization
- Split → Summarize Chunks → Combine
- File: `manifests/langgraph-summarizer.json`

### Future Examples
- **Code Translation**: Analyze → Translate → Test → Refine
- **Data Analysis**: Load → Analyze → Visualize → Report
- **Content Generation**: Research → Draft → Review → Finalize

## Resources

- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **Control Tower**: `./app.py`
- **Front Door Module**: `../dsp-fd2/src/modules/langgraph_workflow.py`
- **Example**: `./examples/langgraph_summarizer_example.py`

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review manifest validation errors
3. Test components individually
4. Consult architecture diagrams above
