# APISIX AI Gateway Integration

## Overview

This document describes the integration of Apache APISIX as an AI Gateway in the DSP AI Control Tower and Front Door architecture. APISIX provides enterprise-grade API gateway capabilities including JWT authentication, rate limiting, load balancing, and observability for AI/LLM services.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│   Client    │────▶│  Front Door  │────▶│   APISIX    │────▶│ LLM Services │
│             │     │   (FD2)      │     │   Gateway   │     │              │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
                            │                     │
                            ▼                     ▼
                    ┌──────────────┐     ┌──────────────┐
                    │Control Tower │     │     etcd     │
                    │  Manifests   │     │ Config Store │
                    └──────────────┘     └──────────────┘
```

## Key Components

### 1. Control Tower Manifest System

The Control Tower now supports APISIX gateway configuration through the `APISIXGatewayModule`:

```json
{
  "module_type": "api_gateway",
  "name": "apisix-gateway",
  "config": {
    "admin_api_url": "http://apisix:9180",
    "admin_key": "${APISIX_ADMIN_KEY}",
    "routes": [...],
    "upstreams": [...],
    "global_plugins": [...]
  }
}
```

### 2. APISIX Gateway Features

#### Supported Plugins

- **Authentication**
  - JWT Authentication (`jwt-auth`)
  - API Key (`key-auth`)
  - Basic Auth (`basic-auth`)
  - OAuth 2.0 (`openid-connect`)

- **Traffic Control**
  - Rate Limiting (`limit-req`, `limit-count`, `limit-conn`)
  - Circuit Breaker (`api-breaker`)
  - Request/Response Transformation (`proxy-rewrite`, `response-rewrite`)
  - CORS (`cors`)

- **Observability**
  - Prometheus Metrics (`prometheus`)
  - Request ID Tracking (`request-id`)
  - Distributed Tracing (`zipkin`, `skywalking`, `opentelemetry`)
  - Logging (`http-logger`, `tcp-logger`, `kafka-logger`)

- **Security**
  - IP Restriction (`ip-restriction`)
  - CSRF Protection (`csrf`)
  - Request Validation (`request-validation`)

### 3. Front Door Integration

The Front Door service (`dsp-fd2`) integrates with APISIX through:

1. **Automatic Route Configuration**: Reads manifests from Control Tower and configures APISIX routes
2. **Request Forwarding**: Routes all requests through APISIX gateway
3. **Health Monitoring**: Monitors APISIX health and route status

## Configuration

### APISIX Gateway Module Configuration

```python
class APISIXGatewayModule(BaseModel):
    admin_api_url: str  # APISIX Admin API URL
    admin_key: str      # Admin API authentication key
    gateway_url: str    # Gateway URL for client requests
    
    routes: List[APISIXRoute]        # Route configurations
    upstreams: List[APISIXUpstream]  # Upstream service definitions
    global_plugins: List[APISIXPlugin]  # Global plugin configurations
    
    # Feature flags
    jwt_auth_enabled: bool
    rate_limiting_enabled: bool
    logging_enabled: bool
    prometheus_enabled: bool
    cors_enabled: bool
    streaming_enabled: bool  # For LLM streaming responses
```

### Route Configuration

```python
class APISIXRoute(BaseModel):
    name: str           # Route identifier
    uri: str            # URI pattern for matching
    methods: List[str]  # HTTP methods
    upstream_id: str    # Reference to upstream
    plugins: List[APISIXPlugin]  # Route-specific plugins
    priority: int       # Route matching priority
```

### Plugin Configuration

```python
class APISIXPlugin(BaseModel):
    name: str           # Plugin name
    enabled: bool       # Enable/disable flag
    config: Dict[str, Any]  # Plugin-specific configuration
    priority: int       # Execution priority
```

## Usage Examples

### 1. Create a Manifest with APISIX Configuration

```json
{
  "project_id": "my-ai-service",
  "modules": [
    {
      "module_type": "api_gateway",
      "name": "apisix-gateway",
      "config": {
        "routes": [
          {
            "name": "llm-inference",
            "uri": "/v1/inference/*",
            "methods": ["POST"],
            "upstream_id": "llm-cluster",
            "plugins": [
              {
                "name": "jwt-auth",
                "enabled": true,
                "config": {
                  "key": "user-key",
                  "secret": "${JWT_SECRET}"
                }
              },
              {
                "name": "limit-req",
                "enabled": true,
                "config": {
                  "rate": 100,
                  "burst": 50
                }
              }
            ]
          }
        ],
        "upstreams": [
          {
            "name": "llm-cluster",
            "type": "roundrobin",
            "nodes": {
              "llm-service-1:8080": 100,
              "llm-service-2:8080": 100
            }
          }
        ]
      }
    }
  ]
}
```

### 2. Deploy with Docker Compose

```bash
# Start all services
docker-compose -f docker-compose-apisix.yml up -d

# Check service health
curl http://localhost:8080/health

# Sync manifests to APISIX
curl -X POST http://localhost:8080/admin/apisix/sync

# View configured routes
curl http://localhost:8080/admin/apisix/routes
```

### 3. Make Authenticated Requests

```python
import jwt
import httpx
from datetime import datetime, timedelta

# Generate JWT token
token = jwt.encode({
    "sub": "user123",
    "exp": datetime.utcnow() + timedelta(hours=1),
    "iss": "frontdoor-ai-gateway"
}, "your-secret-key", algorithm="HS256")

# Make request through APISIX
response = httpx.post(
    "http://localhost:9080/v1/inference/complete",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "prompt": "What is machine learning?",
        "max_tokens": 100
    }
)
```

## Plugin Configuration Examples

### JWT Authentication

```json
{
  "name": "jwt-auth",
  "config": {
    "key": "user-key",
    "secret": "${JWT_SECRET}",
    "algorithm": "HS256",
    "exp": 3600,
    "header": "Authorization",
    "cookie": "jwt_token"
  }
}
```

### Rate Limiting

```json
{
  "name": "limit-req",
  "config": {
    "rate": 100,
    "burst": 50,
    "key_type": "var",
    "key": "consumer_name",
    "rejected_code": 429,
    "rejected_msg": "Rate limit exceeded"
  }
}
```

### Request Logging

```json
{
  "name": "http-logger",
  "config": {
    "uri": "http://logging-service:8080/logs",
    "batch_max_size": 1000,
    "include_req_body": true,
    "include_resp_body": false
  }
}
```

### CORS Configuration

```json
{
  "name": "cors",
  "config": {
    "allow_origins": "*",
    "allow_methods": "GET, POST, PUT, DELETE, OPTIONS",
    "allow_headers": "*",
    "expose_headers": "X-Request-Id",
    "max_age": 3600
  }
}
```

## API Endpoints

### Front Door Admin Endpoints

- `GET /admin/apisix/status` - Get APISIX gateway status
- `POST /admin/apisix/sync` - Sync manifests from Control Tower
- `POST /admin/apisix/configure/{project_id}` - Configure specific project
- `GET /admin/apisix/routes` - List all configured routes
- `GET /admin/apisix/upstreams` - List all configured upstreams

### APISIX Admin API

- `GET /apisix/admin/routes` - List routes
- `PUT /apisix/admin/routes/{id}` - Create/update route
- `DELETE /apisix/admin/routes/{id}` - Delete route
- `GET /apisix/admin/upstreams` - List upstreams
- `PUT /apisix/admin/upstreams/{id}` - Create/update upstream

## Monitoring and Observability

### Prometheus Metrics

APISIX exposes metrics at `http://localhost:9091/metrics`:

- Request count by route
- Request latency distribution
- Upstream health status
- Error rates
- Active connections

### Grafana Dashboard

Import the provided dashboard for visualizing:

- Request rate and latency
- Error rates by route
- Upstream health
- Rate limiting statistics
- JWT authentication metrics

### Distributed Tracing

Configure OpenTelemetry or Zipkin for end-to-end request tracing:

```json
{
  "name": "opentelemetry",
  "config": {
    "trace_id_source": "x-request-id",
    "resource": {
      "service.name": "apisix-gateway"
    },
    "collector": {
      "address": "otel-collector:4317"
    }
  }
}
```

## Testing

Run the integration test suite:

```bash
# Install test dependencies
pip install httpx pyjwt

# Run tests
python test_apisix_integration.py
```

Test coverage includes:
- Control Tower connectivity
- APISIX Admin API access
- Manifest creation and sync
- Route configuration
- JWT authentication
- Rate limiting
- Error handling

## Troubleshooting

### Common Issues

1. **Routes not being created**
   - Check APISIX Admin API connectivity
   - Verify admin key is correct
   - Check etcd connectivity

2. **JWT authentication failing**
   - Verify secret key matches between services
   - Check token expiration
   - Validate algorithm (HS256, RS256)

3. **Rate limiting not working**
   - Verify plugin is enabled
   - Check key configuration (var, consumer_name)
   - Review rate and burst settings

4. **Upstream connection failures**
   - Check service health
   - Verify network connectivity
   - Review timeout settings

### Debug Commands

```bash
# Check APISIX logs
docker logs apisix

# View etcd configuration
docker exec etcd etcdctl get /apisix --prefix

# Test Admin API
curl -H "X-API-KEY: ${APISIX_ADMIN_KEY}" http://localhost:9180/apisix/admin/routes

# Check route configuration
curl -H "X-API-KEY: ${APISIX_ADMIN_KEY}" http://localhost:9180/apisix/admin/routes/{route_id}
```

## Security Considerations

1. **Admin API Security**
   - Use strong admin keys
   - Restrict admin API access by IP
   - Enable TLS for admin API

2. **JWT Security**
   - Use strong secrets (minimum 256 bits)
   - Implement token rotation
   - Set appropriate expiration times

3. **Network Security**
   - Use TLS between APISIX and upstreams
   - Implement mutual TLS where possible
   - Enable CORS appropriately

4. **Rate Limiting**
   - Set appropriate limits per consumer
   - Implement different tiers for users
   - Monitor for abuse patterns

## Performance Optimization

1. **Connection Pooling**
   ```yaml
   upstream:
     keepalive: 320
     keepalive_requests: 1000
     keepalive_timeout: 60s
   ```

2. **Buffer Settings for LLM**
   ```yaml
   proxy_buffer_size: 16k
   proxy_buffers: 8 32k
   client_max_body_size: 100m
   ```

3. **Streaming Responses**
   ```yaml
   proxy_buffering: "off"  # For SSE/streaming
   proxy_request_buffering: "on"
   ```

## Migration Guide

### From Direct LLM Access to APISIX

1. Update manifest with APISIX gateway configuration
2. Deploy APISIX infrastructure
3. Sync manifests to configure routes
4. Update client endpoints to use APISIX gateway
5. Monitor and tune performance

### From Other API Gateways

1. Export existing route configurations
2. Convert to APISIX route format
3. Map plugins to APISIX equivalents
4. Test with shadow traffic
5. Gradual traffic migration

## Future Enhancements

- [ ] GraphQL support for AI services
- [ ] WebSocket support for real-time AI interactions
- [ ] Custom plugin development for AI-specific features
- [ ] A/B testing for model versions
- [ ] Cost tracking per API call
- [ ] Semantic caching for LLM responses
- [ ] Request/response transformation for model compatibility

## References

- [APISIX Documentation](https://apisix.apache.org/docs/)
- [APISIX Plugin Hub](https://apisix.apache.org/docs/apisix/plugins/)
- [Control Tower Manifest System](./MANIFEST_SYSTEM.md)
- [Front Door Documentation](../dsp-fd2/README.md)
