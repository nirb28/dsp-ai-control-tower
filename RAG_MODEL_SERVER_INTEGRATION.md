# RAG and Model Server Integration with APISIX Gateway

This document describes the integration of RAG (Retrieval Augmented Generation) services and Model Server endpoints with the DSP AI Control Tower and Front Door through APISIX API Gateway.

## Overview

The integration enables:
- **RAG Service Integration**: Route query and retrieve requests through APISIX gateway
- **Model Server Integration**: Route embeddings, reranking, and classification requests through APISIX
- **Automatic Route Configuration**: Front Door auto-generates APISIX routes from Control Tower manifests
- **Security**: JWT authentication and API key support for all endpoints
- **Monitoring**: Prometheus metrics, request tracing, and logging

## Architecture

```
Client Request
    ↓
Front Door (FD2)
    ↓
APISIX Gateway
    ├→ RAG Service (/query, /retrieve)
    └→ Model Server (/embeddings, /rerank, /classify)
```

### Request Flow

1. **Manifest Definition**: Define RAG service and model server modules in Control Tower manifest
2. **Auto-Configuration**: Front Door reads manifest and auto-generates APISIX routes
3. **Request Routing**: Client requests are routed through APISIX with plugins (auth, rate limiting, etc.)
4. **Service Invocation**: APISIX forwards requests to backend RAG/model services
5. **Response**: Response flows back through APISIX to client

## Module Types

### 1. RAG Service Module (`rag_service`)

Integrates with RAG service endpoints for document retrieval and query answering.

#### Configuration

```json
{
  "module_type": "rag_service",
  "name": "knowledge-base",
  "config": {
    "service_url": "http://rag-service:8080",
    "configuration_name": "production-kb",
    "query_endpoint": "/query",
    "retrieve_endpoint": "/retrieve",
    "default_k": 10,
    "default_similarity_threshold": 0.7,
    "use_reranking": true,
    "filter_after_reranking": true,
    "query_expansion_enabled": true,
    "query_expansion_strategy": "multi_query",
    "query_expansion_llm_config": "llama3-8b",
    "query_expansion_num_queries": 3,
    "jwt_auth_enabled": true,
    "jwt_module_reference": "auth-service",
    "request_timeout": 120,
    "max_retries": 3,
    "default_metadata_filter": {
      "status": "published"
    }
  }
}
```

#### Generated Routes

The Front Door automatically generates APISIX routes for RAG service modules:

- **Query Endpoint**: `/{project_id}/rag/{module_name}/query`
  - Methods: GET, POST
  - Forwards to: `{service_url}/query`
  
- **Retrieve Endpoint**: `/{project_id}/rag/{module_name}/retrieve`
  - Methods: GET, POST
  - Forwards to: `{service_url}/retrieve`

#### Configuration Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `service_url` | string | required | RAG service base URL |
| `configuration_name` | string | required | RAG configuration to use |
| `query_endpoint` | string | `/query` | Query endpoint path |
| `retrieve_endpoint` | string | `/retrieve` | Retrieve endpoint path |
| `default_k` | int | 5 | Default number of documents to retrieve |
| `default_similarity_threshold` | float | 0.0 | Default similarity threshold |
| `use_reranking` | bool | false | Enable reranking by default |
| `filter_after_reranking` | bool | true | Filter results after reranking |
| `query_expansion_enabled` | bool | false | Enable query expansion |
| `query_expansion_strategy` | string | null | Strategy: `fusion` or `multi_query` |
| `query_expansion_llm_config` | string | null | LLM config name for expansion |
| `query_expansion_num_queries` | int | 3 | Number of expanded queries |
| `jwt_auth_enabled` | bool | false | Enable JWT authentication |
| `jwt_module_reference` | string | null | Reference to JWT config module |
| `request_timeout` | int | 60 | Request timeout in seconds |
| `max_retries` | int | 2 | Maximum number of retries |
| `default_metadata_filter` | object | null | Default metadata filter |

### 2. Model Server Module (`model_server`)

Integrates with model server endpoints for embeddings, reranking, and classification.

#### Configuration

```json
{
  "module_type": "model_server",
  "name": "embedding-reranker",
  "config": {
    "service_url": "http://model-server:8000",
    "embeddings_endpoint": "/embeddings",
    "rerank_endpoint": "/rerank",
    "classify_endpoint": "/classify",
    "health_endpoint": "/health",
    "default_embedding_model": "BAAI/bge-large-en-v1.5",
    "default_reranker_model": "BAAI/bge-reranker-large",
    "default_classifier_model": "cross-encoder/ms-marco-MiniLM-L-12-v2",
    "available_embedding_models": [
      "BAAI/bge-large-en-v1.5",
      "sentence-transformers/all-mpnet-base-v2"
    ],
    "available_reranker_models": [
      "BAAI/bge-reranker-large"
    ],
    "available_classifier_models": [
      "cross-encoder/ms-marco-MiniLM-L-12-v2"
    ],
    "batch_size": 32,
    "request_timeout": 60,
    "max_retries": 2,
    "api_key_enabled": false,
    "jwt_auth_enabled": true,
    "jwt_module_reference": "auth-service"
  }
}
```

#### Generated Routes

The Front Door automatically generates APISIX routes for model server modules:

- **Embeddings**: `/{project_id}/models/{module_name}/embeddings`
- **Reranking**: `/{project_id}/models/{module_name}/rerank`
- **Classification**: `/{project_id}/models/{module_name}/classify`
- **Health Check**: `/{project_id}/models/{module_name}/health`

All routes:
- Methods: GET, POST
- Forward to corresponding backend endpoints
- Support JWT authentication and API key authentication

#### Configuration Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `service_url` | string | required | Model server base URL |
| `embeddings_endpoint` | string | `/embeddings` | Embeddings endpoint path |
| `rerank_endpoint` | string | `/rerank` | Reranking endpoint path |
| `classify_endpoint` | string | `/classify` | Classification endpoint path |
| `health_endpoint` | string | `/health` | Health check endpoint path |
| `default_embedding_model` | string | null | Default embedding model |
| `default_reranker_model` | string | null | Default reranker model |
| `default_classifier_model` | string | null | Default classifier model |
| `available_embedding_models` | array | [] | List of available embedding models |
| `available_reranker_models` | array | [] | List of available reranker models |
| `available_classifier_models` | array | [] | List of available classifier models |
| `batch_size` | int | 32 | Batch size for processing |
| `request_timeout` | int | 30 | Request timeout in seconds |
| `max_retries` | int | 2 | Maximum number of retries |
| `api_key_enabled` | bool | false | Enable API key authentication |
| `api_key` | string | null | API key for authentication |
| `jwt_auth_enabled` | bool | false | Enable JWT authentication |
| `jwt_module_reference` | string | null | Reference to JWT config module |

## Usage Examples

### 1. Create Manifest with RAG and Model Server

```json
{
  "project_id": "ai-platform",
  "project_name": "AI Platform",
  "modules": [
    {
      "module_type": "jwt_config",
      "name": "auth-service",
      "config": {
        "secret_key": "${JWT_SECRET_KEY}",
        "algorithm": "HS256",
        "expiration_minutes": 60
      }
    },
    {
      "module_type": "rag_service",
      "name": "knowledge-base",
      "config": {
        "service_url": "http://rag-service:8080",
        "configuration_name": "default",
        "jwt_auth_enabled": true,
        "jwt_module_reference": "auth-service"
      }
    },
    {
      "module_type": "model_server",
      "name": "embeddings",
      "config": {
        "service_url": "http://model-server:8000",
        "jwt_auth_enabled": true,
        "jwt_module_reference": "auth-service"
      }
    },
    {
      "module_type": "api_gateway",
      "name": "apisix-gateway",
      "config": {
        "gateway_type": "apisix",
        "admin_api_url": "http://apisix-admin:9180",
        "admin_key": "${APISIX_ADMIN_KEY}"
      }
    }
  ]
}
```

### 2. Upload Manifest to Control Tower

```bash
curl -X POST http://localhost:8001/manifests \
  -H "Content-Type: application/json" \
  -H "X-Superuser-Secret: your-secret-key" \
  -d @manifest.json
```

### 3. Trigger Front Door Sync

```bash
curl -X POST http://localhost:8002/admin/sync-manifests
```

### 4. Query RAG Service through APISIX

```bash
# Get JWT token first
TOKEN=$(curl -X POST http://jwt-service:8000/token \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}' | jq -r '.access_token')

# Query RAG service
curl -X POST http://localhost:9080/ai-platform/rag/knowledge-base/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?",
    "k": 5,
    "use_reranking": true
  }'
```

### 5. Call Model Server through APISIX

```bash
# Generate embeddings
curl -X POST http://localhost:9080/ai-platform/models/embeddings/embeddings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["Hello world", "Machine learning"],
    "model_name": "BAAI/bge-large-en-v1.5"
  }'

# Rerank documents
curl -X POST http://localhost:9080/ai-platform/models/embeddings/rerank \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is AI?",
    "texts": ["AI is artificial intelligence", "ML is machine learning"],
    "model_name": "BAAI/bge-reranker-large"
  }'
```

## APISIX Plugin Configuration

### Automatic Plugin Application

The Front Door automatically applies plugins based on module configuration:

#### JWT Authentication
- Applied when `jwt_auth_enabled: true`
- Uses JWT module reference for configuration
- Plugin: `jwt-auth`

#### API Key Authentication
- Applied when `api_key_enabled: true` (model server only)
- Plugin: `key-auth`

#### Proxy Rewrite
- Automatically applied to all routes
- Rewrites request URI to match backend service paths
- Example: `/{project_id}/rag/{module}/query` → `/query`

### Custom Plugins

You can add custom plugins in the APISIX gateway module:

```json
{
  "module_type": "api_gateway",
  "name": "apisix-gateway",
  "config": {
    "global_plugins": [
      {
        "name": "limit-req",
        "enabled": true,
        "config": {
          "rate": 100,
          "burst": 50,
          "key": "remote_addr"
        }
      },
      {
        "name": "prometheus",
        "enabled": true,
        "config": {
          "prefer_name": true
        }
      }
    ]
  }
}
```

## Monitoring and Observability

### Prometheus Metrics

APISIX automatically exposes metrics when Prometheus plugin is enabled:

- Request count
- Request latency
- Error rates
- Upstream status

Access metrics at: `http://apisix:9091/apisix/prometheus/metrics`

### Request Tracing

Enable request ID tracking:

```json
{
  "name": "request-id",
  "enabled": true,
  "config": {
    "header_name": "X-Request-ID",
    "include_in_response": true
  }
}
```

### Logging

Configure HTTP logging plugin:

```json
{
  "name": "http-logger",
  "enabled": true,
  "config": {
    "uri": "http://log-collector:8080/logs",
    "batch_max_size": 1000,
    "max_retry_count": 3
  }
}
```

## Testing

Run the comprehensive test suite:

```bash
cd dsp-ai-control-tower
python test_rag_model_server_integration.py
```

The test script validates:
1. Manifest upload to Control Tower
2. Module retrieval and validation
3. Front Door manifest sync
4. APISIX route generation
5. Route URI patterns
6. Expected request/response formats

## Troubleshooting

### Routes Not Created

**Problem**: APISIX routes not created after manifest upload

**Solutions**:
1. Check Front Door logs: `docker logs front-door`
2. Verify APISIX admin API is accessible
3. Trigger manual sync: `POST /admin/sync-manifests`
4. Check APISIX admin key is correct

### Authentication Failures

**Problem**: JWT authentication failing

**Solutions**:
1. Verify JWT module is configured in manifest
2. Check JWT secret key is set correctly
3. Ensure JWT token is valid and not expired
4. Verify `jwt_module_reference` points to correct module

### Service Unreachable

**Problem**: Backend service unreachable through APISIX

**Solutions**:
1. Verify service URL is correct in module config
2. Check service is running: `curl http://service-url/health`
3. Verify APISIX upstream configuration
4. Check network connectivity between APISIX and service

### Route Conflicts

**Problem**: Multiple routes with same URI pattern

**Solutions**:
1. Use unique module names
2. Check for duplicate modules in manifest
3. Review APISIX route priorities
4. Clean up old routes: `DELETE /admin/apisix/projects/{id}/resources`

## Best Practices

### 1. Module Naming

- Use descriptive, unique names for modules
- Follow naming convention: `{service-type}-{purpose}`
- Examples: `knowledge-base`, `embedding-reranker`, `auth-service`

### 2. Security

- Always enable JWT authentication for production
- Use environment variables for secrets
- Rotate JWT keys regularly
- Enable rate limiting to prevent abuse

### 3. Timeouts

- Set appropriate timeouts based on service characteristics
- RAG queries: 60-120 seconds (due to LLM processing)
- Model server: 30-60 seconds (depends on model size)
- Adjust retries based on service reliability

### 4. Monitoring

- Enable Prometheus metrics
- Set up Grafana dashboards
- Configure alerting for errors and latency
- Monitor upstream health

### 5. Environment Management

- Use environment-specific configurations
- Leverage environment variable substitution
- Test in staging before production deployment
- Document environment differences

## API Reference

### Control Tower Endpoints

- `POST /manifests` - Upload manifest
- `GET /manifests/{project_id}` - Get manifest
- `GET /manifests/{project_id}/modules` - Get modules
- `GET /manifests/{project_id}/modules/{name}` - Get specific module

### Front Door Endpoints

- `POST /admin/sync-manifests` - Sync all manifests
- `GET /admin/projects/{id}/routing` - Get routing mode
- `GET /admin/apisix/projects/{id}/resources` - Get APISIX resources
- `DELETE /admin/apisix/projects/{id}/resources` - Cleanup resources

### Generated APISIX Routes

#### RAG Service
- `POST /{project_id}/rag/{module_name}/query` - Query documents
- `POST /{project_id}/rag/{module_name}/retrieve` - Retrieve documents

#### Model Server
- `POST /{project_id}/models/{module_name}/embeddings` - Generate embeddings
- `POST /{project_id}/models/{module_name}/rerank` - Rerank documents
- `POST /{project_id}/models/{module_name}/classify` - Classify text
- `GET /{project_id}/models/{module_name}/health` - Health check

## Examples

See the following files for complete examples:
- `manifests/rag-model-server-integration.json` - Complete manifest example
- `test_rag_model_server_integration.py` - Test script with usage examples

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review APISIX logs: `docker logs apisix`
3. Review Front Door logs: `docker logs front-door`
4. Check Control Tower logs: `docker logs control-tower`
