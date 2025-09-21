# DSP AI Control Tower - Module Cross-References

## Overview

The Module Cross-Reference system enables precise dependency specification between modules in project manifests. Instead of just listing dependencies by name, modules can now specify exactly which other modules they want to use for specific purposes, with type validation and fallback support.

### Core Capabilities
- **Typed References**: Cross-references can specify expected module types for validation
- **Purpose Documentation**: Each reference includes a clear description of its purpose
- **Optional vs Required**: References can be marked as optional or required
- **Fallback Support**: Specify fallback modules if the primary reference is unavailable
- **Validation**: Automatic validation of cross-reference integrity
- **Analysis Tools**: Built-in analysis and suggestion system
- **Service Discovery**: Automatic detection of services provided by each module type

## Cross-Reference Structure

### ModuleCrossReference Model
```json
{
  "module_name": "target-module-name",
  "module_type": "expected_module_type",
  "purpose": "Description of why this reference is needed",
  "required": true,
  "fallback": "backup-module-name"
}
```

## 📋 Module Configuration with Cross-References

### Enhanced Module Structure
```json
{
  "module_type": "inference_endpoint",
  "name": "llm-inference",
  "version": "1.0.0",
  "status": "enabled",
  "description": "LLM inference endpoint",
  "dependencies": ["knowledge-base"],
  "cross_references": {
    "authentication": {
      "module_name": "auth-service",
      "module_type": "jwt_config",
      "purpose": "JWT token validation for API requests",
      "required": true
    },
    "knowledge_base": {
      "module_name": "knowledge-base",
      "module_type": "rag_config", 
      "purpose": "Retrieve relevant context for queries",
      "required": true
    },
    "monitoring": {
      "module_name": "observability",
      "module_type": "monitoring",
      "purpose": "Track inference performance metrics",
      "required": false
    },
    "security": {
      "module_name": "security-policies",
      "module_type": "security",
      "purpose": "Apply security policies for data handling",
      "required": true,
      "fallback": "basic-security"
    }
  },
  "environment_overrides": {
    "production": {
      "max_tokens": 1000,
      "temperature": 0.5
    }
  },
  "config": {
    "model_name": "gpt-4",
    "endpoint_url": "https://api.openai.com/v1/chat/completions",
    "system_prompt": "You are an AI assistant...",
    "max_tokens": 500,
    "temperature": 0.7
  }
}
```

## API Endpoints

### Cross-Reference Analysis

#### Get Project Cross-References
```bash
GET /manifests/{project_id}/cross-references
```

**Response:**
```json
{
  "project_id": "ai-customer-service",
  "cross_reference_graph": {
    "llm-inference": {
      "provides": ["llm_inference", "text_generation", "model_serving"],
      "consumes": ["authentication", "knowledge_base", "monitoring"],
      "references": {
        "authentication": {
          "target": "auth-service",
          "purpose": "JWT token validation",
          "required": true,
          "fallback": null
        }
      },
      "referenced_by": [
        {
          "source": "gateway",
          "reference_key": "inference",
          "purpose": "Route inference requests"
        }
      ]
    }
  },
  "suggestions": {
    "llm-inference": [
      "Consider adding monitoring reference to 'observability' for performance tracking"
    ]
  },
  "summary": {
    "total_modules": 5,
    "modules_with_references": 3,
    "total_references": 8,
    "modules_referenced": 4
  }
}
```

#### Get Cross-Reference Suggestions
```bash
GET /manifests/{project_id}/cross-references/suggestions
```

#### Get Module References
```bash
GET /manifests/{project_id}/modules/{module_name}/references
```

## 🔧 Common Cross-Reference Patterns

### 1. Inference Endpoint References
```json
{
  "cross_references": {
    "authentication": {
      "module_name": "jwt-auth",
      "module_type": "jwt_config",
      "purpose": "API request authentication",
      "required": true
    },
    "knowledge_base": {
      "module_name": "enterprise-rag",
      "module_type": "rag_config",
      "purpose": "Context retrieval for responses",
      "required": true
    },
    "monitoring": {
      "module_name": "observability",
      "module_type": "monitoring", 
      "purpose": "Performance and usage tracking",
      "required": false
    },
    "security": {
      "module_name": "security-policies",
      "module_type": "security",
      "purpose": "Data handling compliance",
      "required": true
    }
  }
}
```

### 2. API Gateway References
```json
{
  "cross_references": {
    "authentication": {
      "module_name": "sso-auth",
      "module_type": "jwt_config",
      "purpose": "Request authentication and authorization",
      "required": true
    },
    "monitoring": {
      "module_name": "gateway-metrics",
      "module_type": "monitoring",
      "purpose": "API gateway performance monitoring",
      "required": true
    },
    "security": {
      "module_name": "api-security",
      "module_type": "security",
      "purpose": "API security policies and rate limiting",
      "required": true
    }
  }
}
```

### 3. RAG Configuration References
```json
{
  "cross_references": {
    "authentication": {
      "module_name": "user-auth",
      "module_type": "jwt_config",
      "purpose": "User context for personalized retrieval",
      "required": false
    },
    "security": {
      "module_name": "data-security",
      "module_type": "security",
      "purpose": "Document access control and encryption",
      "required": true
    },
    "monitoring": {
      "module_name": "rag-observability",
      "module_type": "monitoring",
      "purpose": "Query performance and relevance tracking",
      "required": false
    },
    "backup": {
      "module_name": "vector-backup",
      "module_type": "backup_recovery",
      "purpose": "Vector store backup and recovery",
      "required": true
    }
  }
}
```

## Validation Rules

### Cross-Reference Validation
1. **Module Existence**: Referenced modules must exist in the manifest
2. **Type Matching**: If module_type is specified, it must match the actual module type
3. **Required References**: Required references must be satisfied or have valid fallbacks
4. **Circular Dependencies**: System detects and warns about circular references
5. **Fallback Validation**: Fallback modules must also exist and be of compatible type

### Validation Errors
```json
{
  "valid": false,
  "errors": [
    "Module 'llm-inference' has required cross-reference 'authentication' to 'auth-service' which is not present in manifest",
    "Module 'gateway' cross-reference 'monitoring' expects module 'metrics' to be of type 'monitoring' but it is of type 'notifications'"
  ],
  "warnings": [
    "Module 'rag-system' has optional cross-reference 'backup' to missing module 'backup-service'"
  ]
}
```

## Analysis and Suggestions

### Cross-Reference Graph Analysis
```json
{
  "cross_reference_graph": {
    "module-name": {
      "provides": ["service1", "service2"],
      "consumes": ["reference1", "reference2"],
      "references": {
        "reference1": {
          "target": "target-module",
          "purpose": "Service purpose",
          "required": true,
          "fallback": "fallback-module"
        }
      },
      "referenced_by": [
        {
          "source": "source-module",
          "reference_key": "reference-key",
          "purpose": "Why this module is referenced"
        }
      ]
    }
  }
}
```

## 🛠️ Best Practices

### 1. Reference Naming
- Use descriptive reference keys: `authentication`, `knowledge_base`, `monitoring`
- Be consistent across similar modules
- Use singular nouns for clarity

### 2. Purpose Documentation
- Clearly explain why the reference is needed
- Include what functionality it provides
- Mention any specific requirements

### 3. Required vs Optional
- Mark authentication and security references as required
- Monitoring and logging can often be optional
- Consider fallbacks for critical but potentially missing modules

### 4. Fallback Strategy
```json
{
  "primary_auth": {
    "module_name": "enterprise-sso",
    "module_type": "jwt_config",
    "purpose": "Enterprise SSO authentication",
    "required": true,
    "fallback": "basic-auth"
  }
}
```

### 5. Environment Overrides
Use environment overrides to adjust cross-references per environment:
```json
{
  "environment_overrides": {
    "development": {
      "cross_references": {
        "monitoring": {
          "required": false
        }
      }
    },
    "production": {
      "cross_references": {
        "monitoring": {
          "required": true
        },
        "backup": {
          "required": true
        }
      }
    }
  }
}
```

## Testing Cross-References

### Test Script Usage
```bash
# Run comprehensive tests including cross-references
python test_manifest_system.py

# Test specific project cross-references
curl http://localhost:8000/manifests/ai-customer-service/cross-references

# Get suggestions for a project
curl http://localhost:8000/manifests/ai-customer-service/cross-references/suggestions
```

### Validation Testing
```bash
# Validate manifest with cross-references
curl -X POST http://localhost:8000/manifests/validate \
  -H "Content-Type: application/json" \
  -d @manifest-with-cross-refs.json
```

##  Advanced Use Cases

### 1. Multi-Environment References
Different environments may need different module references:
```json
{
  "cross_references": {
    "authentication": {
      "module_name": "${environment}-auth",
      "module_type": "jwt_config",
      "purpose": "Environment-specific authentication",
      "required": true
    }
  }
}
```

### 2. Conditional References
References that depend on other configuration:
```json
{
  "cross_references": {
    "cache": {
      "module_name": "redis-cache",
      "module_type": "resource_management",
      "purpose": "Response caching for performance",
      "required": false,
      "fallback": "memory-cache"
    }
  }
}
```

### 3. Service Mesh Integration
References for service mesh architectures:
```json
{
  "cross_references": {
    "service_mesh": {
      "module_name": "istio-gateway",
      "module_type": "api_gateway",
      "purpose": "Service mesh traffic management",
      "required": true
    },
    "observability": {
      "module_name": "jaeger-tracing",
      "module_type": "monitoring",
      "purpose": "Distributed tracing in service mesh",
      "required": true
    }
  }
}
```

## Support and Troubleshooting

### Debug Mode
Enable detailed cross-reference analysis:
```bash
curl "http://localhost:8000/manifests/my-project/cross-references?debug=true"
```

---

*DSP AI Control Tower - Module Cross-References v1.0*
