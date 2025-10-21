# SAS2PY Architecture Diagrams

## 1. High-Level System Architecture

```mermaid
graph TB
    subgraph "External"
        Client[Client Application]
        Groq[Groq LLM API]
        Langfuse[Langfuse Cloud]
    end
    
    subgraph "API Gateway Layer"
        APISIX[APISIX Gateway<br/>Port 9080]
        FD[Front Door Service<br/>Dynamic Module Loader]
    end
    
    subgraph "Core Services"
        CT[Control Tower<br/>Port 8000<br/>Manifest & Policy Management]
        JWT[JWT Service<br/>Port 5000<br/>Authentication & Token Gen]
    end
    
    subgraph "Infrastructure"
        LDAP[LDAP/Active Directory<br/>User Authentication]
        VaultProd[Prod Vault<br/>AppRole Auth]
        VaultDev[Dev Vault<br/>Token Auth]
        Redis[Redis Cache]
    end
    
    subgraph "Observability"
        Prom[Prometheus<br/>Metrics]
        LF[Langfuse<br/>LLM Traces]
    end
    
    Client -->|1. Request Token| JWT
    JWT -->|2. Authenticate| LDAP
    JWT -->|3. Fetch Config| CT
    CT -->|4. Resolve Secrets| VaultProd
    CT -->|4. Resolve Secrets| VaultDev
    JWT -->|5. Return JWT/JWE| Client
    
    Client -->|6. API Request + Token| APISIX
    APISIX -->|7. Validate & Route| FD
    FD -->|8. Load Manifest| CT
    APISIX -->|9. Forward Request| Groq
    Groq -->|10. LLM Response| APISIX
    APISIX -->|11. Response| Client
    
    APISIX -->|Metrics| Prom
    APISIX -->|Traces| Langfuse
    FD -.->|Cache| Redis
    CT -.->|Cache| Redis
    
    style Client fill:#e1f5ff
    style APISIX fill:#ffe1e1
    style JWT fill:#e1ffe1
    style CT fill:#fff4e1
    style VaultProd fill:#f0e1ff
    style VaultDev fill:#f0e1ff
```

## 2. Authentication Flow - Standard JWT

```mermaid
sequenceDiagram
    participant C as Client
    participant JWT as JWT Service
    participant LDAP as LDAP Server
    participant CT as Control Tower
    participant V as Vault
    participant APISIX as APISIX Gateway
    participant Groq as Groq API
    
    Note over C,Groq: Phase 1: Token Generation
    C->>JWT: POST /token<br/>{username, password, api_key}
    JWT->>LDAP: Authenticate User
    LDAP-->>JWT: User Valid + Groups
    JWT->>CT: GET /manifests/sas2py?resolve_env=true
    CT->>V: Resolve secret references
    V-->>CT: Secrets
    CT-->>JWT: Resolved JWT Config
    JWT->>JWT: Generate JWT with claims<br/>(key, tier, rate_limit, models)
    JWT-->>C: {access_token, refresh_token}
    
    Note over C,Groq: Phase 2: API Request
    C->>APISIX: POST /sas2py/convert<br/>Authorization: Bearer JWT
    APISIX->>APISIX: jwt-auth plugin<br/>Validate signature
    APISIX->>APISIX: Extract claims<br/>(consumer key, rate_limit)
    APISIX->>APISIX: ai-prompt-template plugin<br/>Inject system prompt
    APISIX->>APISIX: proxy-rewrite plugin<br/>Transform request
    APISIX->>Groq: POST /openai/v1/chat/completions<br/>Authorization: Bearer GROQ_KEY
    Groq-->>APISIX: LLM Response (Python code)
    APISIX->>APISIX: response-rewrite plugin<br/>Clean headers
    APISIX-->>C: Converted Python Code
```

## 3. Authentication Flow - JWE Encrypted

```mermaid
sequenceDiagram
    participant C as Client
    participant JWT as JWT Service
    participant CT as Control Tower
    participant V as Vault
    participant APISIX as APISIX Gateway
    participant Groq as Groq API
    
    Note over C,Groq: Phase 1: JWE Token Generation
    C->>JWT: POST /token<br/>{username, password,<br/>api_key: "sas2py-jwe-consumer-key"}
    JWT->>CT: GET /manifests/sas2py
    CT->>V: Resolve JWE encryption key
    V-->>CT: JWE_ENCRYPTION_KEY
    CT-->>JWT: JWT Config + JWE Config
    JWT->>JWT: Generate JWT with claims<br/>+ Groq API key
    JWT->>JWT: Encrypt JWT → JWE<br/>(A256GCM, 32-byte key)
    JWT-->>C: {access_token: JWE,<br/>token_type: "JWE"}
    
    Note over C,Groq: Phase 2: JWE Request Processing
    C->>APISIX: POST /sas2py/convert-jwe<br/>Authorization: Bearer JWE
    APISIX->>APISIX: jwe-decrypt plugin<br/>Decrypt JWE → JWT
    APISIX->>APISIX: Extract JWT claims
    APISIX->>APISIX: Extract groq_api_key<br/>from decrypted payload
    APISIX->>APISIX: Forward payload in<br/>X-JWE-Payload header
    APISIX->>APISIX: serverless-pre-function<br/>Extract API key to variable
    APISIX->>APISIX: proxy-rewrite plugin<br/>Use extracted API key
    APISIX->>Groq: POST /openai/v1/chat/completions<br/>Authorization: Bearer $extracted_key
    Groq-->>APISIX: LLM Response
    APISIX-->>C: Converted Code
```

## 4. Multi-Vault Secret Resolution

```mermaid
sequenceDiagram
    participant App as Application
    participant CT as Control Tower
    participant SM as Secret Manager
    participant VM as Vault Manager
    participant PV as Prod Vault
    participant DV as Dev Vault
    participant Config as Config File
    participant Env as Environment Vars
    
    App->>CT: GET /manifests/sas2py?resolve_env=true
    CT->>CT: Load manifest JSON
    CT->>CT: Identify secret references
    
    Note over CT,Env: Reference 1: Vault Secret
    CT->>SM: Resolve "vault:prod-vault:api-keys/groq#key"
    SM->>VM: Get vault instance "prod-vault"
    VM->>PV: Authenticate (AppRole)
    PV-->>VM: Token
    VM->>PV: GET /v1/secret/data/api-keys/groq
    PV-->>VM: {key: "actual_api_key"}
    VM-->>SM: "actual_api_key"
    SM->>SM: Cache secret (TTL: 300s)
    SM-->>CT: "actual_api_key"
    
    Note over CT,Env: Reference 2: Config File
    CT->>SM: Resolve "config:api_keys.groq"
    SM->>Config: Read secrets_config.json
    Config-->>SM: {"api_keys": {"groq": "key_value"}}
    SM-->>CT: "key_value"
    
    Note over CT,Env: Reference 3: Environment Variable
    CT->>SM: Resolve "env:PROD_JWT_SECRET"
    SM->>Env: os.getenv("PROD_JWT_SECRET")
    Env-->>SM: "secret_value"
    SM-->>CT: "secret_value"
    
    CT->>CT: Substitute all resolved values
    CT-->>App: Fully resolved manifest
```

## 5. LDAP Integration Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant JWT as JWT Service
    participant LDAP as LDAP Server
    participant CT as Control Tower
    
    C->>JWT: POST /token<br/>{username: "user@example.com",<br/>password: "pass123"}
    
    Note over JWT,LDAP: LDAP Authentication
    JWT->>LDAP: Bind with admin credentials
    LDAP-->>JWT: Admin session established
    
    JWT->>LDAP: Search for user DN<br/>filter: (mail=user@example.com)
    LDAP-->>JWT: DN: cn=user,ou=users,dc=example,dc=com
    
    JWT->>LDAP: Authenticate user<br/>bind(DN, password)
    LDAP-->>JWT: Authentication successful
    
    JWT->>LDAP: Query group membership<br/>filter: (member=DN)
    LDAP-->>JWT: Groups: [engineers, data-scientists]
    
    JWT->>LDAP: Query user attributes<br/>(department, title, email)
    LDAP-->>JWT: Attributes: {dept: "AI", title: "Engineer"}
    
    Note over JWT,CT: Claim Generation
    JWT->>JWT: Map LDAP groups to roles<br/>engineers → developer<br/>data-scientists → analyst
    
    JWT->>CT: GET /manifests/sas2py<br/>Extract JWT config
    CT-->>JWT: JWT config with claim templates
    
    JWT->>JWT: Generate JWT claims:<br/>- sub: user@example.com<br/>- groups: [engineers, data-scientists]<br/>- roles: [developer, analyst]<br/>- department: AI<br/>+ API key static claims
    
    JWT-->>C: {access_token, refresh_token}
```

## 6. Multi-Environment Configuration

```mermaid
graph TB
    subgraph "Manifest Structure"
        M[Project Manifest<br/>sas2py.json]
        M --> Modules[Modules Array]
        M --> Envs[Environments Object]
    end
    
    subgraph "Environments"
        Envs --> Common[common:<br/>groq_api_key]
        Envs --> Dev[development:<br/>localhost URLs<br/>plain secrets]
        Envs --> Staging[staging:<br/>staging URLs<br/>env var secrets]
        Envs --> Prod[production:<br/>prod URLs<br/>vault secrets]
    end
    
    subgraph "Module Configuration"
        Modules --> JWT[JWT Module]
        Modules --> Inf[Inference Module]
        Modules --> GW[Gateway Module]
        Modules --> Mon[Monitoring Module]
    end
    
    subgraph "Variable Resolution"
        JWT --> V1["${environments.${environment}.urls.jwt_service_url}"]
        Inf --> V2["${environments.${environment}.urls.api_base_url}"]
        GW --> V3["${environments.${environment}.secrets.jwt_secret_key}"]
        Mon --> V4["${environments.${environment}.secrets.langfuse_public_key}"]
    end
    
    subgraph "Environment Selection"
        Req[API Request:<br/>?resolve_env=true<br/>X-Environment: production]
        Req --> Select{Select Environment}
        Select -->|development| DevRes[Resolve with dev values]
        Select -->|staging| StagingRes[Resolve with staging values]
        Select -->|production| ProdRes[Resolve with prod values]
    end
    
    DevRes --> Output[Resolved Manifest]
    StagingRes --> Output
    ProdRes --> Output
    
    style M fill:#fff4e1
    style Common fill:#e1f5ff
    style Dev fill:#e1ffe1
    style Staging fill:#ffe1e1
    style Prod fill:#f0e1ff
```

## 7. APISIX Plugin Processing Pipeline

```mermaid
graph LR
    subgraph "Request Flow"
        Client[Client Request] --> R1[Route Matching]
        R1 --> Auth{Authentication}
    end
    
    subgraph "Authentication Plugins"
        Auth -->|JWT| P1[jwt-auth plugin<br/>Validate signature<br/>Extract claims]
        Auth -->|JWE| P2[jwe-decrypt plugin<br/>Decrypt token<br/>Extract payload]
    end
    
    subgraph "Pre-Processing"
        P1 --> P3[request-id plugin<br/>Generate UUID<br/>X-Request-Id]
        P2 --> P3
        P3 --> P4[serverless-pre-function<br/>Custom Lua logic<br/>Extract variables]
    end
    
    subgraph "Transformation"
        P4 --> P5[ai-prompt-template<br/>Inject system prompt<br/>Transform user input]
        P5 --> P6[proxy-rewrite<br/>URI: /openai/v1/chat/completions<br/>Headers: Authorization]
    end
    
    subgraph "Observability"
        P6 --> P7[prometheus plugin<br/>Record metrics<br/>Latency, count]
        P7 --> P8[Langfuse integration<br/>Send trace data]
    end
    
    subgraph "Upstream"
        P8 --> U[Forward to Upstream<br/>Groq API]
        U --> Resp[LLM Response]
    end
    
    subgraph "Response Processing"
        Resp --> P9[response-rewrite<br/>Remove headers<br/>Content-Encoding]
        P9 --> P10[Add X-Request-Id<br/>to response]
        P10 --> ClientResp[Return to Client]
    end
    
    style P1 fill:#e1ffe1
    style P2 fill:#e1ffe1
    style P5 fill:#ffe1e1
    style P6 fill:#ffe1e1
    style P7 fill:#fff4e1
    style P8 fill:#fff4e1
```

## 8. Dynamic Claims Resolution

```mermaid
sequenceDiagram
    participant C as Client
    participant JWT as JWT Service
    participant CT as Control Tower
    participant Func as Claims Function
    participant API as External API
    participant DB as Database
    
    C->>JWT: POST /token<br/>{username, password, api_key_config}
    
    Note over JWT,DB: Static Claims (Immediate)
    JWT->>JWT: Extract static claims:<br/>- tier: "premium"<br/>- models: ["gpt-4"]<br/>- rate_limit: 100
    
    Note over JWT,DB: Dynamic Claims - Function Type
    JWT->>CT: Load api_key_config
    CT-->>JWT: Config with dynamic claims:<br/>{quota: {type: "function"}}
    
    JWT->>Func: Call claims.quota.get_remaining_quota<br/>args: {user_id: "user123"}
    Func->>DB: Query user quota
    DB-->>Func: {remaining: 5000, total: 10000}
    Func-->>JWT: {quota_remaining: 5000}
    
    Note over JWT,DB: Dynamic Claims - API Type
    JWT->>API: GET /api/usage-stats/user123<br/>Authorization: Bearer internal_token
    API->>DB: Query usage statistics
    DB-->>API: {requests_today: 45, cost: 2.50}
    API-->>JWT: {usage_stats: {requests: 45, cost: 2.50}}
    
    Note over JWT,DB: Merge All Claims
    JWT->>JWT: Merge claims:<br/>Static + Dynamic Function + Dynamic API
    JWT->>JWT: Generate JWT with all claims
    JWT-->>C: {access_token: "eyJ..."}
    
    Note over C,DB: Token Contains
    Note right of JWT: {<br/>  "sub": "user123",<br/>  "tier": "premium",<br/>  "models": ["gpt-4"],<br/>  "rate_limit": 100,<br/>  "quota_remaining": 5000,<br/>  "usage_stats": {...}<br/>}
```

## 9. Complete End-to-End Request Flow

```mermaid
sequenceDiagram
    participant U as User
    participant C as Client App
    participant JWT as JWT Service<br/>(Port 5000)
    participant LDAP as LDAP
    participant CT as Control Tower<br/>(Port 8000)
    participant V as Vault
    participant APISIX as APISIX<br/>(Port 9080)
    participant Groq as Groq LLM
    participant LF as Langfuse
    
    Note over U,LF: Step 1: Authentication & Token Generation
    U->>C: Login (username/password)
    C->>JWT: POST /token
    JWT->>LDAP: Authenticate user
    LDAP-->>JWT: User valid + groups
    JWT->>CT: GET /manifests/sas2py
    CT->>V: Resolve secrets
    V-->>CT: Secrets
    CT-->>JWT: JWT config
    JWT->>JWT: Generate JWT
    JWT-->>C: JWT token
    C-->>U: Login successful
    
    Note over U,LF: Step 2: SAS Code Conversion Request
    U->>C: Convert SAS code
    C->>APISIX: POST /sas2py/convert<br/>Authorization: Bearer JWT<br/>Body: {user_input: "SAS code"}
    
    Note over U,LF: Step 3: APISIX Processing
    APISIX->>APISIX: jwt-auth: Validate
    APISIX->>APISIX: request-id: Generate UUID
    APISIX->>APISIX: ai-prompt-template:<br/>Inject system prompt
    APISIX->>APISIX: proxy-rewrite:<br/>Transform to OpenAI format
    APISIX->>APISIX: prometheus: Record metrics
    
    Note over U,LF: Step 4: LLM Inference
    APISIX->>Groq: POST /openai/v1/chat/completions
    Groq->>Groq: Process with llama-3.1-70b
    Groq-->>APISIX: Python code response
    
    Note over U,LF: Step 5: Response & Observability
    APISIX->>LF: Send trace:<br/>- Request/response<br/>- Latency<br/>- Token usage
    APISIX->>APISIX: response-rewrite:<br/>Clean headers
    APISIX-->>C: Python code
    C-->>U: Display converted code
    
    Note over U,LF: Step 6: Monitoring
    LF->>LF: Store trace in project "sas2py"
    APISIX->>APISIX: Update Prometheus metrics
```

## 10. Module Dependency Graph

```mermaid
graph TD
    subgraph "Infrastructure Modules"
        VM[Vault Manager<br/>Multi-instance secrets]
        Mon[Langfuse Monitoring<br/>LLM observability]
    end
    
    subgraph "Authentication Modules"
        JWT1[Simple Auth JWT<br/>sas2py-consumer-key]
        JWT2[JWE Auth<br/>sas2py-jwe-consumer-key]
    end
    
    subgraph "Inference Modules"
        Inf1[Convert Endpoint<br/>llama-3.1-70b]
        Inf2[Test Endpoint<br/>llama-3.1-8b]
        Inf3[Convert-JWE Endpoint<br/>llama-3.1-70b]
        Inf4[OpenAI Compatible<br/>llama-3.1-70b]
    end
    
    subgraph "Gateway Modules"
        GW1[APISIX Convert Route<br/>/sas2py/convert]
        GW2[APISIX Test Route<br/>/sas2py/test]
        GW3[APISIX Convert-JWE Route<br/>/sas2py/convert-jwe]
        GW4[APISIX OpenAI Route<br/>/sas2py/v1/chat/completions]
    end
    
    VM -.->|Provides secrets| JWT1
    VM -.->|Provides secrets| JWT2
    
    JWT1 -->|Required by| Inf1
    JWT1 -->|Required by| Inf2
    JWT1 -->|Required by| Inf4
    JWT2 -->|Required by| Inf3
    
    Inf1 -->|Required by| GW1
    Inf2 -->|Required by| GW2
    Inf3 -->|Required by| GW3
    Inf4 -->|Required by| GW4
    
    JWT1 -->|Required by| GW1
    JWT1 -->|Required by| GW2
    JWT1 -->|Required by| GW4
    JWT2 -->|Required by| GW3
    
    Mon -.->|Observes| GW1
    Mon -.->|Observes| GW3
    Mon -.->|Observes| GW4
    
    style VM fill:#f0e1ff
    style Mon fill:#fff4e1
    style JWT1 fill:#e1ffe1
    style JWT2 fill:#e1ffe1
    style Inf1 fill:#e1f5ff
    style Inf2 fill:#e1f5ff
    style Inf3 fill:#e1f5ff
    style Inf4 fill:#e1f5ff
    style GW1 fill:#ffe1e1
    style GW2 fill:#ffe1e1
    style GW3 fill:#ffe1e1
    style GW4 fill:#ffe1e1
```

## 11. Secret Reference Resolution Patterns

```mermaid
graph TB
    subgraph "Secret Reference Types"
        Ref[Secret Reference in Manifest]
    end
    
    Ref --> Type{Reference Type?}
    
    Type -->|vault:instance:path#key| V1[Vault Resolution]
    Type -->|config:section.key| V2[Config File Resolution]
    Type -->|env:VAR_NAME| V3[Environment Variable]
    Type -->|encrypted:base64| V4[Decrypt Value]
    Type -->|literal:value| V5[Use As-Is]
    
    subgraph "Vault Resolution"
        V1 --> V1A[Parse: instance, path, key]
        V1A --> V1B[Select vault instance]
        V1B --> V1C{Auth Method?}
        V1C -->|AppRole| V1D[Authenticate with role_id/secret_id]
        V1C -->|Token| V1E[Use vault_token]
        V1D --> V1F[Read secret from KV]
        V1E --> V1F
        V1F --> V1G[Extract key from secret]
        V1G --> V1H[Cache result]
        V1H --> Result[Return Secret Value]
    end
    
    subgraph "Config Resolution"
        V2 --> V2A[Load secrets_config.json]
        V2A --> V2B[Navigate path: section.key]
        V2B --> V2C{Encrypted?}
        V2C -->|Yes| V2D[Decrypt value]
        V2C -->|No| V2E[Return value]
        V2D --> Result
        V2E --> Result
    end
    
    subgraph "Environment Variable"
        V3 --> V3A[os.getenv VAR_NAME]
        V3A --> V3B{Exists?}
        V3B -->|Yes| V3C[Return value]
        V3B -->|No| V3D[Raise error]
        V3C --> Result
    end
    
    subgraph "Encrypted Value"
        V4 --> V4A[Decode base64]
        V4A --> V4B[Decrypt with ENCRYPTION_KEY]
        V4B --> V4C[Return plaintext]
        V4C --> Result
    end
    
    subgraph "Literal Value"
        V5 --> V5A[Return value directly]
        V5A --> Result
    end
    
    style V1 fill:#f0e1ff
    style V2 fill:#e1f5ff
    style V3 fill:#e1ffe1
    style V4 fill:#ffe1e1
    style V5 fill:#fff4e1
```

## 12. Rate Limiting & Claims Enforcement

```mermaid
sequenceDiagram
    participant C as Client
    participant APISIX as APISIX Gateway
    participant Redis as Redis Cache
    participant Groq as Groq API
    
    Note over C,Groq: Request 1 - Within Limit
    C->>APISIX: POST /sas2py/convert<br/>Authorization: Bearer JWT
    APISIX->>APISIX: jwt-auth: Extract claims<br/>{rate_limit: 100, key: "consumer"}
    APISIX->>Redis: Check rate limit counter<br/>Key: consumer:rate_limit
    Redis-->>APISIX: Count: 45/100
    APISIX->>Redis: Increment counter
    Redis-->>APISIX: Count: 46/100
    APISIX->>Groq: Forward request
    Groq-->>APISIX: Response
    APISIX-->>C: 200 OK<br/>X-RateLimit-Remaining: 54
    
    Note over C,Groq: Request 2 - Limit Exceeded
    C->>APISIX: POST /sas2py/convert<br/>Authorization: Bearer JWT
    APISIX->>APISIX: jwt-auth: Extract claims
    APISIX->>Redis: Check rate limit counter
    Redis-->>APISIX: Count: 100/100
    APISIX->>APISIX: Rate limit exceeded
    APISIX-->>C: 429 Too Many Requests<br/>X-RateLimit-Remaining: 0<br/>Retry-After: 3600
    
    Note over C,Groq: Request 3 - Different Tier
    C->>APISIX: POST /sas2py/convert<br/>Authorization: Bearer JWT_PREMIUM
    APISIX->>APISIX: jwt-auth: Extract claims<br/>{rate_limit: 1000, tier: "premium"}
    APISIX->>Redis: Check rate limit counter<br/>Key: premium_consumer:rate_limit
    Redis-->>APISIX: Count: 250/1000
    APISIX->>Redis: Increment counter
    APISIX->>Groq: Forward request
    Groq-->>APISIX: Response
    APISIX-->>C: 200 OK<br/>X-RateLimit-Remaining: 749
```

---

## Diagram Usage Guide

### For Architecture Diagram
Use **Diagram 1** to show:
- Overall system topology
- Service interactions
- Infrastructure dependencies
- Data flow paths

### For Sequence Diagrams
- **Diagram 2**: Standard JWT authentication flow
- **Diagram 3**: JWE encrypted token flow
- **Diagram 4**: Multi-vault secret resolution
- **Diagram 5**: LDAP integration details
- **Diagram 8**: Dynamic claims resolution
- **Diagram 9**: Complete end-to-end flow

### For Configuration Diagrams
- **Diagram 6**: Multi-environment setup
- **Diagram 7**: APISIX plugin pipeline
- **Diagram 10**: Module dependencies
- **Diagram 11**: Secret resolution patterns
- **Diagram 12**: Rate limiting enforcement

### Rendering Tools
These diagrams use **Mermaid** syntax and can be rendered in:
- GitHub/GitLab markdown
- VS Code (with Mermaid extension)
- draw.io (import Mermaid)
- Online: mermaid.live
- Documentation sites (MkDocs, Docusaurus)

### Customization
To modify diagrams:
1. Copy the Mermaid code block
2. Edit in mermaid.live for live preview
3. Adjust colors using `style` directives
4. Add/remove nodes as needed
5. Update sequence steps for your flow
