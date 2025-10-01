import os
import json
import subprocess
import hashlib
import secrets
from fastapi import FastAPI, HTTPException, Body, Depends, Header, Query
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum
import uvicorn
import re
from config import SUPERUSER_SECRET_HASH, SUPERUSER_SALT
import asyncio

app = FastAPI(title="DSPAI - Control Tower", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/docs", include_in_schema=False)
async def swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="DSPAI - Control Tower",
        swagger_favicon_url="/static/control-tower.ico"
    )

class PolicyEvaluationRequest(BaseModel):
    input_data: Dict[str, Any] = Field(..., description="Input data to evaluate against the policy")

class PolicyEvaluationResponse(BaseModel):
    result: Dict[str, Any]
    allow: bool
    policy_path: str

class ClientSecretRequest(BaseModel):
    client_id: str = Field(..., description="Client ID for which to generate a secret")
    plain_secret: str = Field(..., description="Plain text secret to hash")

class ClientSecretResponse(BaseModel):
    client_id: str
    hashed_secret: str
    salt: str

class UserPoliciesRequest(BaseModel):
    user_id: str = Field(..., description="User ID to find applicable policies for")
    group_ids: List[str] = Field(default=[], description="Optional list of group IDs the user belongs to")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_id": "nbkABCD",
                    "group_ids": ["unix_grp1", "unix_grp2"]
                }
            ]
        }
    }

class JupyterLabRequest(BaseModel):
    aihpc_lane: str = Field(..., description="Environment type to deploy to (e.g., 'training_dev', 'training_prod')")
    username: str = Field(..., description="Username for the Jupyter Lab")
    conda_env: str = Field(..., description="Conda environment to use")
    port: int = Field(8888, description="Port to run Jupyter Lab on")
    aihpc_env: str = Field("dev", description="AIHPC environment to use (e.g., 'dev', 'prod')")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "aihpc_lane": "training_dev",
                    "username": "user123",
                    "conda_env": "pytorch",
                    "port": 8888,
                    "aihpc_env": "dev"
                }
            ]
        }
    }

class ModelDeploymentRequest(BaseModel):
    aihpc_lane: str = Field(..., description="Environment type to deploy to (e.g., 'inference_dev', 'inference_prod')")
    username: str = Field(..., description="Username for the model deployment")
    model_name: str = Field(..., description="Name of the model to deploy")
    conda_env: str = Field(..., description="Conda environment to use")
    script_path: str = Field(..., description="Path to the deployment script")
    model_dir: str = Field(..., description="Directory containing the model files")
    port: int = Field(8000, description="Port to run the model server on")
    workers: int = Field(2, description="Number of workers for the model server")
    aihpc_env: str = Field("dev", description="AIHPC environment to use (e.g., 'dev', 'prod')")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "aihpc_lane": "inference_dev",
                    "username": "user123",
                    "model_name": "sentiment_analysis",
                    "conda_env": "pytorch",
                    "script_path": "app.server",
                    "model_dir": "/models/sentiment",
                    "port": 8000,
                    "workers": 2,
                    "aihpc_env": "dev"
                }
            ]
        }
    }

class HpcTemplateResponse(BaseModel):
    template: Dict[str, Any]
    message: str

class PolicyRequest(BaseModel):
    client_id: str = Field(..., description="Client ID (policy file name without .rego extension)")
    policy_content: str = Field(..., description="Full content of the Rego policy file")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "client_id": "example_client",
                    "policy_content": "package dspai.policy\nimport rego.v1\n\n# Client authentication\nclient_secret := \"hashed_secret\"\nclient_salt := \"random_salt\"\n\n# Default deny\ndefault allow := false\n\nallow := true {\n    input.action == \"read\"\n}"
                }
            ]
        }
    }

class PolicyStatusRequest(BaseModel):
    enabled: bool = Field(..., description="Whether the policy should be enabled or disabled")

# ==================== PROJECT MANIFEST MODELS ====================

class ModuleType(str, Enum):
    JWT_CONFIG = "jwt_config"
    RAG_CONFIG = "rag_config"
    API_GATEWAY = "api_gateway"
    INFERENCE_ENDPOINT = "inference_endpoint"
    SECURITY = "security"
    MONITORING = "monitoring"
    MODEL_REGISTRY = "model_registry"
    DATA_PIPELINE = "data_pipeline"
    DEPLOYMENT = "deployment"
    RESOURCE_MANAGEMENT = "resource_management"
    NOTIFICATIONS = "notifications"
    BACKUP_RECOVERY = "backup_recovery"

class ModuleStatus(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"
    DEVELOPMENT = "development"

class JWTConfigModule(BaseModel):
    secret_key: str = Field(..., description="JWT secret key")
    algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    expiration_minutes: int = Field(default=30, description="Token expiration time in minutes")
    issuer: Optional[str] = Field(None, description="JWT issuer")
    audience: Optional[str] = Field(None, description="JWT audience")
    refresh_token_enabled: bool = Field(default=True, description="Enable refresh tokens")
    
class RAGConfigModule(BaseModel):
    vector_store_type: str = Field(..., description="Type of vector store (faiss, pinecone, etc.)")
    embedding_model: str = Field(..., description="Embedding model name")
    chunk_size: int = Field(default=512, description="Document chunk size")
    chunk_overlap: int = Field(default=50, description="Chunk overlap size")
    retrieval_k: int = Field(default=5, description="Number of documents to retrieve")
    reranker_enabled: bool = Field(default=False, description="Enable reranking")
    query_expansion_enabled: bool = Field(default=False, description="Enable query expansion")
    
class APIGatewayModule(BaseModel):
    gateway_type: str = Field(default="generic", description="Gateway type")
    rate_limiting: Dict[str, int] = Field(default_factory=dict, description="Rate limiting rules")
    cors_origins: List[str] = Field(default_factory=list, description="CORS allowed origins")
    authentication_required: bool = Field(default=True, description="Require authentication")
    api_versioning: str = Field(default="v1", description="API version")
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    load_balancing_strategy: str = Field(default="round_robin", description="Load balancing strategy")
    
    @model_validator(mode='before')
    @classmethod
    def reject_apisix(cls, data: Any) -> Any:
        """Reject if gateway_type is apisix - should use APISIXGatewayModule instead"""
        if isinstance(data, dict) and data.get('gateway_type') == 'apisix':
            raise ValueError("Use APISIXGatewayModule for gateway_type='apisix'")
        return data
    
class APISIXPlugin(BaseModel):
    """APISIX plugin configuration"""
    name: str = Field(..., description="Plugin name (e.g., jwt-auth, limit-req, prometheus)")
    enabled: bool = Field(default=True, description="Whether the plugin is enabled")
    config: Dict[str, Any] = Field(default_factory=dict, description="Plugin-specific configuration")
    priority: Optional[int] = Field(None, description="Plugin execution priority (higher runs first)")
    
class APISIXRoute(BaseModel):
    """APISIX route configuration"""
    name: str = Field(..., description="Route name")
    uri: str = Field(..., description="URI pattern for matching requests")
    methods: List[str] = Field(default_factory=lambda: ["GET", "POST"], description="HTTP methods")
    upstream_id: Optional[str] = Field(None, description="Reference to upstream service")
    upstream: Optional[Dict[str, Any]] = Field(None, description="Inline upstream configuration")
    service_id: Optional[str] = Field(None, description="Reference to service configuration")
    plugins: Union[List[APISIXPlugin], Dict[str, Any]] = Field(default_factory=dict, description="Plugins (list or dict format)")
    host: Optional[str] = Field(None, description="Host header for routing")
    priority: int = Field(default=0, description="Route priority (higher matches first)")
    vars: Optional[List[List[str]]] = Field(None, description="Advanced routing conditions")
    
class APISIXUpstream(BaseModel):
    """APISIX upstream configuration for load balancing"""
    name: str = Field(..., description="Upstream name")
    type: str = Field(default="roundrobin", description="Load balancing type (roundrobin, chash, least_conn)")
    nodes: Dict[str, int] = Field(..., description="Backend nodes {host:port: weight}")
    timeout: Dict[str, int] = Field(
        default_factory=lambda: {"connect": 30, "send": 30, "read": 30},
        description="Timeout settings in seconds"
    )
    retries: int = Field(default=1, description="Number of retries")
    health_check: Optional[Dict[str, Any]] = Field(None, description="Health check configuration")
    
class APISIXGatewayModule(BaseModel):
    """APISIX API Gateway configuration for AI services"""
    gateway_type: str = Field(default="apisix", description="Gateway type - must be 'apisix'")
    admin_api_url: str = Field(default="http://localhost:9080", description="APISIX Admin API URL")
    admin_key: str = Field(default="${APISIX_ADMIN_KEY}", description="Admin API key")
    gateway_url: str = Field(default="http://localhost:9080", description="Gateway URL for clients")
    dashboard_url: Optional[str] = Field(default="http://localhost:9000", description="APISIX Dashboard URL")
    
    # Core configurations
    routes: List[APISIXRoute] = Field(default_factory=list, description="Route configurations")
    upstreams: List[APISIXUpstream] = Field(default_factory=list, description="Upstream service configurations")
    
    # Global plugins that apply to all routes
    global_plugins: List[APISIXPlugin] = Field(default_factory=list, description="Global plugins")
    
    # Default plugin configurations
    jwt_auth_enabled: bool = Field(default=True, description="Enable JWT authentication globally")
    rate_limiting_enabled: bool = Field(default=True, description="Enable rate limiting globally")
    logging_enabled: bool = Field(default=True, description="Enable logging globally")
    prometheus_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    
    # Security configurations
    ssl_enabled: bool = Field(default=False, description="Enable SSL/TLS")
    ssl_cert: Optional[str] = Field(None, description="SSL certificate path")
    ssl_key: Optional[str] = Field(None, description="SSL private key path")
    
    # CORS configuration
    cors_enabled: bool = Field(default=True, description="Enable CORS")
    cors_origins: List[str] = Field(default_factory=lambda: ["*"], description="Allowed CORS origins")
    cors_methods: List[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed CORS methods"
    )
    
    # Default timeout and retry settings
    default_timeout: int = Field(default=60, description="Default request timeout in seconds")
    default_retries: int = Field(default=2, description="Default number of retries")
    
    # AI-specific configurations
    streaming_enabled: bool = Field(default=True, description="Enable streaming for LLM responses")
    response_buffering: bool = Field(default=False, description="Buffer responses before sending")
    request_buffering: bool = Field(default=True, description="Buffer requests before forwarding")
    
class InferenceEndpointModule(BaseModel):
    # APISIX route reference (if using APISIX gateway)
    apisix_route: Optional[str] = Field(None, description="APISIX route name to use for this endpoint")
    apisix_gateway_module: Optional[str] = Field(None, description="Name of the APISIX gateway module providing the route")
    
    # Direct endpoint configuration (optional if using APISIX route)
    model_name: Optional[str] = Field(None, description="Model name for inference")
    model_version: Optional[str] = Field(default="latest", description="Model version")
    endpoint_url: Optional[str] = Field(None, description="Inference endpoint URL")
    system_prompt: Optional[str] = Field(None, description="System prompt for LLM")
    max_tokens: Optional[int] = Field(default=1024, description="Maximum tokens per response")
    temperature: Optional[float] = Field(default=0.7, description="Sampling temperature")
    top_p: Optional[float] = Field(default=0.9, description="Top-p sampling parameter")
    batch_size: Optional[int] = Field(default=1, description="Batch size for inference")
    
class SecurityModule(BaseModel):
    encryption_at_rest: bool = Field(default=True, description="Enable encryption at rest")
    encryption_in_transit: bool = Field(default=True, description="Enable encryption in transit")
    vulnerability_scanning: bool = Field(default=True, description="Enable vulnerability scanning")
    access_control_type: str = Field(default="rbac", description="Access control type (rbac, abac)")
    audit_logging: bool = Field(default=True, description="Enable audit logging")
    compliance_standards: List[str] = Field(default_factory=list, description="Compliance standards")
    
class MonitoringModule(BaseModel):
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")
    logging_level: str = Field(default="INFO", description="Logging level")
    tracing_enabled: bool = Field(default=True, description="Enable distributed tracing")
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    alerting_enabled: bool = Field(default=True, description="Enable alerting")
    dashboard_url: Optional[str] = Field(None, description="Monitoring dashboard URL")
    
class ModelRegistryModule(BaseModel):
    registry_type: str = Field(..., description="Model registry type (mlflow, wandb, etc.)")
    registry_url: str = Field(..., description="Model registry URL")
    auto_versioning: bool = Field(default=True, description="Enable automatic versioning")
    model_validation: bool = Field(default=True, description="Enable model validation")
    metadata_tracking: bool = Field(default=True, description="Enable metadata tracking")
    experiment_tracking: bool = Field(default=True, description="Enable experiment tracking")
    
class DataPipelineModule(BaseModel):
    pipeline_type: str = Field(..., description="Pipeline type (batch, streaming, hybrid)")
    data_sources: List[str] = Field(..., description="List of data sources")
    data_sinks: List[str] = Field(..., description="List of data sinks")
    processing_engine: str = Field(..., description="Processing engine (spark, airflow, etc.)")
    schedule: Optional[str] = Field(None, description="Pipeline schedule (cron format)")
    data_quality_checks: bool = Field(default=True, description="Enable data quality checks")
    
class DeploymentModule(BaseModel):
    deployment_strategy: str = Field(default="blue_green", description="Deployment strategy")
    container_registry: str = Field(..., description="Container registry URL")
    orchestration_platform: str = Field(..., description="Orchestration platform (k8s, docker-compose)")
    auto_scaling: bool = Field(default=True, description="Enable auto-scaling")
    rollback_enabled: bool = Field(default=True, description="Enable rollback")
    environment_configs: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Environment-specific configs")
    
class ResourceManagementModule(BaseModel):
    compute_resources: Dict[str, Any] = Field(default_factory=dict, description="Compute resource allocations")
    storage_resources: Dict[str, Any] = Field(default_factory=dict, description="Storage resource allocations")
    network_resources: Dict[str, Any] = Field(default_factory=dict, description="Network resource allocations")
    auto_scaling_policies: Dict[str, Any] = Field(default_factory=dict, description="Auto-scaling policies")
    cost_optimization: bool = Field(default=True, description="Enable cost optimization")
    resource_quotas: Dict[str, Any] = Field(default_factory=dict, description="Resource quotas")
    
class NotificationModule(BaseModel):
    email_enabled: bool = Field(default=True, description="Enable email notifications")
    slack_enabled: bool = Field(default=False, description="Enable Slack notifications")
    webhook_enabled: bool = Field(default=False, description="Enable webhook notifications")
    notification_channels: Dict[str, Any] = Field(default_factory=dict, description="Notification channel configs")
    alert_rules: List[Dict[str, Any]] = Field(default_factory=list, description="Alert rules")
    escalation_policies: List[Dict[str, Any]] = Field(default_factory=list, description="Escalation policies")
    
class BackupRecoveryModule(BaseModel):
    backup_enabled: bool = Field(default=True, description="Enable automated backups")
    backup_frequency: str = Field(default="daily", description="Backup frequency")
    retention_policy: str = Field(default="30d", description="Backup retention policy")
    disaster_recovery_enabled: bool = Field(default=True, description="Enable disaster recovery")
    backup_storage_type: str = Field(default="cloud", description="Backup storage type")
    restore_testing: bool = Field(default=True, description="Enable restore testing")

class ModuleCrossReference(BaseModel):
    """Cross-reference to another module for specific functionality"""
    module_name: str = Field(..., description="Name of the referenced module")
    module_type: Optional[str] = Field(None, description="Expected type of the referenced module")
    purpose: str = Field(..., description="Purpose of this cross-reference")
    required: bool = Field(default=True, description="Whether this reference is required")
    fallback: Optional[str] = Field(None, description="Fallback module if primary is not available")

class ModuleConfig(BaseModel):
    module_type: ModuleType = Field(..., description="Type of the module")
    name: str = Field(..., description="Module name")
    version: Optional[str] = Field(default="1.0.0", description="Module version")
    status: Optional[ModuleStatus] = Field(default=ModuleStatus.ENABLED, description="Module status")
    description: Optional[str] = Field(None, description="Module description")
    config: Union[
        JWTConfigModule,
        RAGConfigModule,
        APISIXGatewayModule,
        APIGatewayModule,
        InferenceEndpointModule,
        SecurityModule,
        MonitoringModule,
        ModelRegistryModule,
        DataPipelineModule,
        DeploymentModule,
        ResourceManagementModule,
        NotificationModule,
        BackupRecoveryModule,
        Dict[str, Any]
    ] = Field(..., description="Module-specific configuration")
    
    @model_validator(mode='before')
    @classmethod
    def validate_config(cls, data: Any) -> Any:
        """Custom validator to handle api_gateway discrimination"""
        # Just return data as-is, let Pydantic's Union matching handle it
        # The order in the Union (APISIXGatewayModule before APIGatewayModule) matters
        return data
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "module_type": "inference_endpoint",
                    "name": "my-llm",
                    "config": {
                        "model_name": "gpt-4",
                        "endpoint_url": "https://api.openai.com/v1/chat/completions"
                    }
                }
            ]
        }
    }
    
class ProjectManifest(BaseModel):
    project_id: str = Field(..., description="Unique project identifier")
    project_name: str = Field(..., description="Human-readable project name")
    version: Optional[str] = Field(default="1.0.0", description="Manifest version")
    description: Optional[str] = Field(None, description="Project description")
    owner: str = Field(..., description="Project owner")
    tags: Optional[List[str]] = Field(default_factory=list, description="Project tags")
    environment: Optional[str] = Field(default="development", description="Target environment")
    environments: Optional[Dict[str, Dict[str, Any]]] = Field(default_factory=dict, description="Environment-specific configurations")
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default_factory=datetime.now, description="Last update timestamp")
    modules: List[ModuleConfig] = Field(..., description="List of module configurations")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
class ManifestRequest(BaseModel):
    manifest: ProjectManifest = Field(..., description="Project manifest")
    
class ManifestResponse(BaseModel):
    message: str
    manifest_id: str
    manifest_path: str
    
class ManifestListResponse(BaseModel):
    manifests: List[Dict[str, Any]]
    count: int
    
class ManifestValidationRequest(BaseModel):
    manifest: ProjectManifest = Field(..., description="Manifest to validate")
    
class ManifestValidationResponse(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

# ==================== MANIFEST UTILITY FUNCTIONS ====================

def validate_manifest_dependencies(modules: List[ModuleConfig]) -> List[str]:
    """Validate manifest modules"""
    errors = []
    # Basic validation - check for duplicate module names
    module_names = [module.name for module in modules]
    duplicates = [name for name in set(module_names) if module_names.count(name) > 1]
    if duplicates:
        errors.append(f"Duplicate module names found: {', '.join(duplicates)}")
    
    return errors

def get_manifest_path(project_id: str) -> str:
    """Get the file path for a manifest"""
    return f"manifests/{project_id}.json"

def load_manifest(project_id: str) -> Optional[ProjectManifest]:
    """Load a manifest from file"""
    manifest_path = get_manifest_path(project_id)
    
    if not os.path.exists(manifest_path):
        return None
    
    try:
        with open(manifest_path, 'r') as f:
            manifest_data = json.load(f)
        return ProjectManifest.model_validate(manifest_data)
    except Exception:
        return None

def save_manifest(manifest: ProjectManifest) -> str:
    """Save a manifest to file"""
    manifest_path = get_manifest_path(manifest.project_id)
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    
    # Update timestamp
    manifest.updated_at = datetime.now()
    
    # Save manifest
    with open(manifest_path, 'w') as f:
        json.dump(manifest.model_dump(), f, indent=2, default=str)
    
    return manifest_path

def resolve_environment_variables(data: Any, manifest: ProjectManifest) -> Any:
    """Recursively resolve environment variable placeholders in manifest data"""
    if isinstance(data, dict):
        resolved = {}
        for key, value in data.items():
            # Resolve both keys and values (important for upstream nodes)
            resolved_key = resolve_environment_variables(key, manifest) if isinstance(key, str) else key
            resolved_value = resolve_environment_variables(value, manifest)
            resolved[resolved_key] = resolved_value
        return resolved
    elif isinstance(data, list):
        return [resolve_environment_variables(item, manifest) for item in data]
    elif isinstance(data, str):
        # Handle environment variable substitution
        if "${" in data:
            resolved_value = data
            
            # Handle ${environments.${environment}.key} pattern
            env_pattern = r'\$\{environments\.\$\{environment\}\.([^}]+)\}'
            matches = re.findall(env_pattern, resolved_value)
            for match in matches:
                placeholder = f"${{environments.${{environment}}.{match}}}"
                
                # Navigate to the environment value
                try:
                    current_env = manifest.environment
                    if hasattr(manifest, 'environments') and manifest.environments:
                        env_data = manifest.environments.get(current_env, {})
                        
                        # Split the key path (e.g., "secrets.jwt_secret_key")
                        key_parts = match.split('.')
                        value = env_data
                        for part in key_parts:
                            if isinstance(value, dict) and part in value:
                                value = value[part]
                            else:
                                value = None
                                break
                        
                        if value is not None:
                            resolved_value = resolved_value.replace(placeholder, str(value))
                except (AttributeError, KeyError):
                    # Keep original placeholder if resolution fails
                    pass
            
            # Handle ${environment} pattern
            env_var_pattern = r'\$\{environment\}'
            resolved_value = re.sub(env_var_pattern, manifest.environment, resolved_value)
            
            # Handle other ${VARIABLE} patterns (environment variables)
            var_pattern = r'\$\{([A-Z_][A-Z0-9_]*)\}'
            matches = re.findall(var_pattern, resolved_value)
            for match in matches:
                placeholder = f"${{{match}}}"
                env_value = os.getenv(match)
                if env_value is not None:
                    resolved_value = resolved_value.replace(placeholder, env_value)
            
            return resolved_value
        return data
    else:
        return data

def apply_environment_overrides(module: ModuleConfig, manifest: ProjectManifest) -> ModuleConfig:
    """Apply environment-specific overrides to a module configuration (deprecated - kept for compatibility)"""
    # No-op function since environment_overrides field has been removed
    return module

def get_resolved_manifest(project_id: str, resolve_env: bool = False) -> Optional[ProjectManifest]:
    """Load a manifest and optionally resolve environment variables"""
    manifest = load_manifest(project_id)
    if not manifest or not resolve_env:
        return manifest
    
    # Convert to dict, resolve variables, and convert back
    manifest_dict = manifest.model_dump()
    resolved_dict = resolve_environment_variables(manifest_dict, manifest)
    
    # Apply environment overrides to modules
    if 'modules' in resolved_dict:
        for i, module_data in enumerate(resolved_dict['modules']):
            module = ModuleConfig.model_validate(module_data)
            module_with_overrides = apply_environment_overrides(module, manifest)
            resolved_dict['modules'][i] = module_with_overrides.model_dump()
    
    return ProjectManifest.model_validate(resolved_dict)

def get_resolved_module(project_id: str, module_name: str, resolve_env: bool = False) -> Optional[ModuleConfig]:
    """Get a specific module with optional environment resolution"""
    manifest = load_manifest(project_id)
    if not manifest:
        return None
    
    # Find the module
    target_module = None
    for module in manifest.modules:
        if module.name == module_name:
            target_module = module
            break
    
    if not target_module:
        return None
    
    if not resolve_env:
        return target_module
    
    # Apply environment overrides
    module_with_overrides = apply_environment_overrides(target_module, manifest)
    
    # Resolve environment variables
    module_dict = module_with_overrides.model_dump()
    resolved_dict = resolve_environment_variables(module_dict, manifest)
    
    return ModuleConfig.model_validate(resolved_dict)

def analyze_cross_references(modules: List[ModuleConfig]) -> Dict[str, Any]:
    """Analyze module capabilities (deprecated - cross_references removed)"""
    module_graph = {}
    
    # Build module capability map based on type
    for module in modules:
        services = []
        if module.module_type == "jwt_config":
            services.extend(["authentication", "authorization", "token_validation"])
        elif module.module_type == "monitoring":
            services.extend(["logging", "metrics", "tracing", "health_checks"])
        elif module.module_type == "security":
            services.extend(["encryption", "access_control", "audit_logging"])
        elif module.module_type == "notifications":
            services.extend(["alerting", "notifications", "escalation"])
        elif module.module_type == "backup_recovery":
            services.extend(["backup", "disaster_recovery", "data_protection"])
        elif module.module_type == "resource_management":
            services.extend(["scaling", "resource_allocation", "cost_optimization"])
        elif module.module_type == "model_registry":
            services.extend(["model_versioning", "experiment_tracking", "model_validation"])
        elif module.module_type == "api_gateway":
            services.extend(["routing", "rate_limiting", "cors", "load_balancing"])
        elif module.module_type == "rag_config":
            services.extend(["knowledge_retrieval", "document_search", "semantic_search"])
        elif module.module_type == "inference_endpoint":
            services.extend(["llm_inference", "text_generation", "model_serving"])
        elif module.module_type == "data_pipeline":
            services.extend(["data_processing", "etl", "data_quality"])
        elif module.module_type == "deployment":
            services.extend(["container_deployment", "orchestration", "scaling"])
            
        module_graph[module.name] = {
            "provides": services,
            "module_type": module.module_type
        }
    
    return module_graph

def get_cross_reference_suggestions(modules: List[ModuleConfig]) -> Dict[str, List[str]]:
    """Get suggestions for module relationships (deprecated - cross_references removed)"""
    # Return empty suggestions since cross_references field has been removed
    return {}

def list_manifests() -> List[Dict[str, Any]]:
    """List all available manifests"""
    manifests = []
    manifest_dir = "manifests"
    
    if not os.path.exists(manifest_dir):
        return manifests
    
    for file in os.listdir(manifest_dir):
        if file.endswith(".json"):
            project_id = file.replace(".json", "")
            manifest = load_manifest(project_id)
            if manifest:
                manifests.append({
                    "project_id": manifest.project_id,
                    "project_name": manifest.project_name,
                    "version": manifest.version,
                    "environment": manifest.environment,
                    "owner": manifest.owner,
                    "module_count": len(manifest.modules),
                    "created_at": manifest.created_at,
                    "updated_at": manifest.updated_at
                })
    
    return manifests

def extract_aihpc_config(policy_content: str, aihpc_env: str, aihpc_lane: str) -> Dict[str, str]:
    """Extract AIHPC configuration from policy content for a specific environment and lane"""
    # Extract aihpc configuration for the specified environment
    aihpc_match = re.search(r'aihpc\.' + aihpc_env + r'\s*:=\s*({.*?})\s*$', policy_content, re.DOTALL | re.MULTILINE)
    if not aihpc_match:
        raise HTTPException(status_code=400, detail=f"AIHPC configuration not defined for environment: {aihpc_env}")
    
    # Extract the specific environment configuration
    # Modified regex to properly handle nested braces and find the specific lane
    env_config_str = aihpc_match.group(1)
    lane_pattern = rf'"{aihpc_lane}"\s*:\s*({{\s*"[^"]+"\s*:\s*"[^"]+"\s*,\s*"[^"]+"\s*:\s*"[^"]+"\s*,\s*"[^"]+"\s*:\s*\d+\s*,\s*.*?}})'
    env_match = re.search(lane_pattern, env_config_str, re.DOTALL)
    
    if not env_match:
        raise HTTPException(status_code=400, detail=f"Environment type not defined: {aihpc_lane}")
    
    env_config = env_match.group(1)
    
    # Define the configuration fields to extract with their default values
    config_fields = {
        "account": None,
        "partition": None,
        "num_gpu": "1"  # Default value
    }
    
    # Extract each field from the environment configuration
    for field, default in config_fields.items():
        if field == "num_gpu":
            # Special case for num_gpu which is a number
            match = re.search(rf'"{field}"\s*:\s*(\d+)', env_config)
            if match:
                config_fields[field] = match.group(1)
        else:
            # For string fields
            match = re.search(rf'"{field}"\s*:\s*"([^"]+)"', env_config)
            if match:
                config_fields[field] = match.group(1)
            elif default is None:
                # Required field is missing
                raise HTTPException(status_code=400, detail=f"{field.capitalize()} not defined for environment: {aihpc_lane}")
    
    return config_fields

def hash_secret(secret: str, salt: str = None):
    """Hash a secret with a salt using SHA-256"""
    if salt is None:
        # Generate a random salt if none is provided
        salt = secrets.token_hex(16)
    
    # Combine the secret and salt and hash
    combined = secret + salt
    hashed = hashlib.sha256(combined.encode()).hexdigest()
    
    return hashed, salt

async def authenticate_superuser(
    x_dspai_client_secret: str = Header(..., description="Superuser secret for authentication", alias="X-DSPAI-Client-Secret")
):
    """Authenticate superuser using the superuser secret"""
    # Check if superuser secret is provided
    superuser_hashed_secret, _ = hash_secret(x_dspai_client_secret, SUPERUSER_SALT)
    if superuser_hashed_secret != SUPERUSER_SECRET_HASH:
        # Add a delay to prevent timing attacks
        await asyncio.sleep(1)
        raise HTTPException(status_code=401, detail="Invalid superuser credentials")
    
    return True

async def authenticate_client(
    x_dspai_client_id: str = Header(..., description="Client ID (policy file name)", alias="X-DSPAI-Client-ID"),
    x_dspai_client_secret: str = Header(..., description="Client secret for authentication", alias="X-DSPAI-Client-Secret")
):
    """Authenticate client using client_id and client_secret from headers"""
    # Check if superuser secret is provided
    superuser_hashed_secret, _ = hash_secret(x_dspai_client_secret, SUPERUSER_SALT)
    if superuser_hashed_secret == SUPERUSER_SECRET_HASH:
        # Superuser authentication successful, construct policy path
        policy_path = f"policies/clients/{x_dspai_client_id}.rego"
        
        # Check if policy file exists
        if not os.path.exists(policy_path):
            raise HTTPException(status_code=404, detail=f"Client ID not found: {x_dspai_client_id}")
        
        return policy_path
    
    # Construct the policy path
    policy_path = f"policies/clients/{x_dspai_client_id}.rego"
    
    # Check if policy file exists
    if not os.path.exists(policy_path):
        raise HTTPException(status_code=404, detail=f"Client ID not found: {x_dspai_client_id}")
    
    # Read the policy file to extract the client secret
    with open(policy_path, 'r') as f:
        policy_content = f.read()
    
    # Look for client_secret and salt in the policy file
    import re
    hashed_secret_match = re.search(r'client_secret\s*:=\s*"([^"]+)"', policy_content)
    salt_match = re.search(r'client_salt\s*:=\s*"([^"]+)"', policy_content)
    
    if not hashed_secret_match or not salt_match:
        raise HTTPException(status_code=401, detail="Client secret or salt not defined in policy")
    
    stored_hashed_secret = hashed_secret_match.group(1)
    stored_salt = salt_match.group(1)
    
    # Hash the provided secret with the stored salt
    provided_hashed_secret, _ = hash_secret(x_dspai_client_secret, stored_salt)
    
    # Verify the client secret
    if provided_hashed_secret != stored_hashed_secret:
        raise HTTPException(status_code=401, detail="Invalid client secret")
    
    return policy_path

@app.get("/")
async def root():
    return {"message": "DSP AI Control Tower - OPA Policy Evaluator API. Swagger: /docs"}

@app.get("/policies")
async def list_policies():
    """List all available Rego policies"""
    policies = []
    client_dir = "policies/clients"
    
    if os.path.exists(client_dir):
        for file in os.listdir(client_dir):
            if file.endswith(".rego") and not file.endswith("_test.rego"):
                policy_path = os.path.join(client_dir, file)
                # Convert Windows path to Unix-style for consistency
                policy_path = policy_path.replace("\\", "/")
                
                # Read the policy file to check if it's enabled
                with open(policy_path, 'r') as f:
                    policy_content = f.read()
                
                # Check if policy is enabled (if enabled flag exists)
                enabled_match = re.search(r'policy_enabled\s*:=\s*(true|false)', policy_content)
                
                policy_info = {
                    "policy_path": policy_path,
                    "policy_name": os.path.basename(policy_path)
                }
                
                # Add enabled status if it exists
                if enabled_match:
                    policy_info["enabled"] = enabled_match.group(1) == "true"
                else:
                    policy_info["enabled"] = True  # Default to enabled if flag doesn't exist
                
                policies.append(policy_info)
    
    return {"policies": policies}

@app.post("/generate-client-secret", response_model=ClientSecretResponse)
async def generate_client_secret(request: ClientSecretRequest):
    """Generate a hashed client secret with salt"""
    hashed_secret, salt = hash_secret(request.plain_secret)
    
    return {
        "client_id": request.client_id,
        "hashed_secret": hashed_secret,
        "salt": salt
    }

@app.post("/evaluate", response_model=PolicyEvaluationResponse)
async def evaluate_policy(
    request: PolicyEvaluationRequest,
    policy_path: str = Depends(authenticate_client)
):
    """Evaluate input data against a specified Rego policy with client authentication via headers"""
    # Create temporary input file
    input_file = "temp_input.json"
    with open(input_file, "w") as f:
        json.dump(request.input_data, f)
    
    try:
        # Run OPA evaluation using the opa.exe executable
        cmd = [
            "opa", "eval", 
            "--data", policy_path, 
            "--input", input_file, 
            "--format", "json",
            "data.dspai.policy"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500, 
                detail=f"OPA evaluation failed: {result.stderr}"
            )
        
        # Parse the OPA result
        opa_result = json.loads(result.stdout)
        
        # Extract the allow decision
        allow = False
        if "result" in opa_result and len(opa_result["result"]) > 0:
            if "allow" in opa_result["result"][0]["expressions"][0]["value"]:
                allow = opa_result["result"][0]["expressions"][0]["value"]["allow"]
        
        return {
            "result": opa_result,
            "allow": allow,
            "policy_path": policy_path
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating policy: {str(e)}")
    
    finally:
        # Clean up temporary file
        if os.path.exists(input_file):
            os.remove(input_file)

@app.post("/batch-evaluate")
async def batch_evaluate_policies(
    input_data: Dict[str, Any] = Body(..., description="Input data to evaluate against the policy"),
    policy_path: str = Depends(authenticate_client)
):
    """Evaluate input data against policy with client authentication via headers"""
    results = []
    
    # Create temporary input file
    input_file = "temp_input.json"
    with open(input_file, "w") as f:
        json.dump(input_data, f)
    
    try:
        # Run OPA evaluation
        cmd = [
            "opa.exe", "eval", 
            "--data", policy_path, 
            "--input", input_file, 
            "--format", "json",
            "data.dspai.policy"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            results.append({
                "policy_path": policy_path,
                "error": f"OPA evaluation failed: {result.stderr}",
                "allow": False
            })
        else:
            # Parse the OPA result
            opa_result = json.loads(result.stdout)
            
            # Extract the allow decision
            allow = False
            if "result" in opa_result and len(opa_result["result"]) > 0:
                if "allow" in opa_result["result"][0]["expressions"][0]["value"]:
                    allow = opa_result["result"][0]["expressions"][0]["value"]["allow"]
            
            results.append({
                "policy_path": policy_path,
                "result": opa_result,
                "allow": allow
            })
    
    except Exception as e:
        results.append({
            "policy_path": policy_path,
            "error": f"Error evaluating policy: {str(e)}",
            "allow": False
        })
    
    finally:
        # Clean up temporary file
        if os.path.exists(input_file):
            os.remove(input_file)
    
    return {"results": results}

@app.post("/user-policies")
async def list_user_policies(request: UserPoliciesRequest):
    """List all policies applicable to a specific user and their groups"""
    applicable_policies = []
    client_dir = "policies/clients"
    
    if not os.path.exists(client_dir):
        return {"policies": []}
    
    for file in os.listdir(client_dir):
        if file.endswith(".rego") and not file.endswith("_test.rego"):
            policy_path = os.path.join(client_dir, file)
            # Convert Windows path to Unix-style for consistency
            policy_path = policy_path.replace("\\", "/")
            
            # Read the policy file to extract user and group roles
            with open(policy_path, 'r') as f:
                policy_content = f.read()
            
            # Check if policy is enabled (if enabled flag exists)
            enabled_match = re.search(r'policy_enabled\s*:=\s*(true|false)', policy_content)
            # If enabled flag exists and is set to false, skip this policy
            if enabled_match and enabled_match.group(1) == "false":
                continue
            
            # Check if user is directly mentioned in user_roles
            user_match = re.search(rf'"{request.user_id}":\s*"([^"]+)"', policy_content)
            
            # Check if any of the user's groups are mentioned in group_roles
            group_matches = []
            for group_id in request.group_ids:
                group_match = re.search(rf'"{group_id}":\s*"([^"]+)"', policy_content)
                if group_match:
                    group_matches.append({
                        "group_id": group_id,
                        "role": group_match.group(1)
                    })
            
            # If either user or any group is found, add to applicable policies
            if user_match or group_matches:
                policy_info = {
                    "policy_path": policy_path,
                    "policy_name": os.path.basename(policy_path),
                }
                
                # Add enabled status if it exists
                if enabled_match:
                    policy_info["enabled"] = enabled_match.group(1) == "true"
                else:
                    policy_info["enabled"] = True  # Default to enabled if flag doesn't exist
                
                if user_match:
                    policy_info["user_role"] = user_match.group(1)
                
                if group_matches:
                    policy_info["group_roles"] = group_matches
                
                # Extract allowed actions based on roles
                roles_match = re.search(r'roles\s*:=\s*{([^}]+)}', policy_content, re.DOTALL)
                if roles_match:
                    roles_content = roles_match.group(1)
                    policy_info["available_actions"] = {}
                    
                    # Extract user's direct role actions if available
                    if user_match:
                        user_role = user_match.group(1)
                        role_actions_match = re.search(rf'"{user_role}":\s*\[(.*?)\]', roles_content)
                        if role_actions_match:
                            actions = re.findall(r'"([^"]+)"', role_actions_match.group(1))
                            policy_info["available_actions"]["user"] = actions
                    
                    # Extract group role actions
                    for group_match in group_matches:
                        group_role = group_match["role"]
                        role_actions_match = re.search(rf'"{group_role}":\s*\[(.*?)\]', roles_content)
                        if role_actions_match:
                            actions = re.findall(r'"([^"]+)"', role_actions_match.group(1))
                            if "groups" not in policy_info["available_actions"]:
                                policy_info["available_actions"]["groups"] = {}
                            policy_info["available_actions"]["groups"][group_match["group_id"]] = actions
                
                applicable_policies.append(policy_info)
    
    return {"policies": applicable_policies}

def load_template(template_name: str) -> Dict[str, Any]:
    """Load a template from the templates directory"""
    template_path = os.path.join("templates", f"{template_name}.json")
    
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail=f"Template not found: {template_name}")
    
    try:
        with open(template_path, 'r') as f:
            template = json.load(f)
        return template
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading template: {str(e)}")

@app.post("/templates/jupyter-lab", response_model=HpcTemplateResponse)
async def generate_jupyter_lab_template(
    request: JupyterLabRequest,
    policy_path: str = Depends(authenticate_client)
):
    """Generate a Jupyter Lab job template for HPC Slurm cluster"""
    # Load the template
    template = load_template("jupyter_lab")
    
    # Extract policy information
    with open(policy_path, 'r') as f:
        policy_content = f.read()
    
    # Extract project name from policy
    project_match = re.search(r'project\s*:=\s*"([^"]+)"', policy_content)
    if project_match:
        project = project_match.group(1)
    else:
        # Use policy filename as project if not explicitly defined
        project = os.path.basename(policy_path).replace(".rego", "")
    
    # Extract allowed models if available
    allowed_models = []
    allowed_models_match = re.search(r'allowed_models\s*:=\s*\[(.*?)\]', policy_content, re.DOTALL)
    if allowed_models_match:
        models_str = allowed_models_match.group(1)
        allowed_models = [m.strip('"') for m in re.findall(r'"([^"]+)"', models_str)]
    
    # Extract AIHPC configuration
    aihpc_config = extract_aihpc_config(policy_content, request.aihpc_env, request.aihpc_lane)
    
    # Replace placeholders in the template
    template_str = json.dumps(template)
    template_str = template_str.replace("{project}", project)
    template_str = template_str.replace("{aihpc.account}", aihpc_config["account"])
    template_str = template_str.replace("{aihpc.partition}", aihpc_config["partition"])
    template_str = template_str.replace("{aihpc.num_gpu}", aihpc_config["num_gpu"])
    
    # Replace allowed_models if available
    if allowed_models:
        template_str = template_str.replace("{allowed_models}", ", ".join(allowed_models))
    else:
        template_str = template_str.replace("{allowed_models}", "")
    
    # Replace user-specific values
    template_str = template_str.replace("{username}", request.username)
    template_str = template_str.replace("{conda_env}", request.conda_env)
    template_str = template_str.replace("{port}", str(request.port))
    
    # Convert back to dictionary
    filled_template = json.loads(template_str)
    
    return {
        "template": filled_template,
        "message": "Jupyter Lab template generated successfully"
    }

@app.post("/templates/model-deployment", response_model=HpcTemplateResponse)
async def generate_model_deployment_template(
    request: ModelDeploymentRequest,
    policy_path: str = Depends(authenticate_client)
):
    """Generate a Model Deployment job template for HPC Slurm cluster"""
    # Load the template
    template = load_template("model_deployment")
    
    # Extract policy information
    with open(policy_path, 'r') as f:
        policy_content = f.read()
    
    # Extract project name from policy
    project_match = re.search(r'project\s*:=\s*"([^"]+)"', policy_content)
    if project_match:
        project = project_match.group(1)
    else:
        # Use policy filename as project if not explicitly defined
        project = os.path.basename(policy_path).replace(".rego", "")
    
    # Extract AIHPC configuration
    aihpc_config = extract_aihpc_config(policy_content, request.aihpc_env, request.aihpc_lane)
    
    # Replace placeholders in the template
    template_str = json.dumps(template)
    template_str = template_str.replace("{project}", project)
    template_str = template_str.replace("{aihpc.account}", aihpc_config["account"])
    template_str = template_str.replace("{aihpc.partition}", aihpc_config["partition"])
    template_str = template_str.replace("{aihpc.num_gpu}", aihpc_config["num_gpu"])
    
    # Replace user-specific values
    template_str = template_str.replace("model_name", request.model_name)
    template_str = template_str.replace("/home", f"/home/{request.username}/models/{request.model_name}")
    template_str = template_str.replace("/home/models/", f"/home/{request.username}/models/{request.model_name}")
    template_str = template_str.replace("/home/models/logs", f"/home/{request.username}/models/{request.model_name}/logs")
    template_str = template_str.replace("source activate", f"source activate {request.conda_env}; python -m {request.script_path} --model-dir={request.model_dir} --port={request.port} --workers={request.workers}")
    
    # Convert back to dictionary
    filled_template = json.loads(template_str)
    
    return {
        "template": filled_template,
        "message": "Model Deployment template generated successfully"
    }

@app.post("/policies/add", status_code=201)
async def add_policy(
    request: PolicyRequest,
    is_superuser: bool = Depends(authenticate_superuser)
):
    """Add a new Rego policy (superuser only)"""
    # Ensure the client_id is valid
    if not re.match(r'^[a-zA-Z0-9_]+$', request.client_id):
        raise HTTPException(status_code=400, detail="Invalid client_id format. Use only alphanumeric characters and underscores.")
    
    # Construct the policy path
    policy_path = f"policies/clients/{request.client_id}.rego"
    
    # Check if policy already exists
    if os.path.exists(policy_path):
        raise HTTPException(status_code=409, detail=f"Policy already exists: {request.client_id}")
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(policy_path), exist_ok=True)
    
    # Add enabled flag if not already present in the policy content
    if "policy_enabled" not in request.policy_content:
        # Find the first line after package declaration to insert the enabled flag
        lines = request.policy_content.split('\n')
        package_index = -1
        for i, line in enumerate(lines):
            if line.startswith('package '):
                package_index = i
                break
        
        if package_index >= 0:
            # Insert after package and import statements
            insert_index = package_index + 1
            while insert_index < len(lines) and lines[insert_index].startswith('import '):
                insert_index += 1
            
            lines.insert(insert_index, "\n# Policy status - controls whether this policy is active")
            lines.insert(insert_index + 1, "policy_enabled := true")
            
            # Reassemble the policy content
            request.policy_content = '\n'.join(lines)
    
    # Write the policy file
    try:
        with open(policy_path, 'w') as f:
            f.write(request.policy_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write policy file: {str(e)}")
    
    return {"message": f"Policy added successfully: {request.client_id}", "policy_path": policy_path}

@app.put("/policies/update/{client_id}")
async def update_policy(
    client_id: str,
    request: PolicyRequest,
    is_superuser: bool = Depends(authenticate_superuser)
):
    """Update an existing Rego policy (superuser only)"""
    # Ensure the client_id in path matches the one in request
    if client_id != request.client_id:
        raise HTTPException(status_code=400, detail="client_id in path must match client_id in request body")
    
    # Ensure the client_id is valid
    if not re.match(r'^[a-zA-Z0-9_]+$', request.client_id):
        raise HTTPException(status_code=400, detail="Invalid client_id format. Use only alphanumeric characters and underscores.")
    
    # Construct the policy path
    policy_path = f"policies/clients/{request.client_id}.rego"
    
    # Check if policy exists
    if not os.path.exists(policy_path):
        raise HTTPException(status_code=404, detail=f"Policy not found: {request.client_id}")
    
    # Write the updated policy file
    try:
        with open(policy_path, 'w') as f:
            f.write(request.policy_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update policy file: {str(e)}")
    
    return {"message": f"Policy updated successfully: {request.client_id}", "policy_path": policy_path}

@app.delete("/policies/delete/{client_id}")
async def delete_policy(
    client_id: str,
    is_superuser: bool = Depends(authenticate_superuser)
):
    """Delete an existing Rego policy (superuser only)"""
    # Ensure the client_id is valid
    if not re.match(r'^[a-zA-Z0-9_]+$', client_id):
        raise HTTPException(status_code=400, detail="Invalid client_id format. Use only alphanumeric characters and underscores.")
    
    # Construct the policy path
    policy_path = f"policies/clients/{client_id}.rego"
    
    # Check if policy exists
    if not os.path.exists(policy_path):
        raise HTTPException(status_code=404, detail=f"Policy not found: {client_id}")
    
    # Delete the policy file
    try:
        os.remove(policy_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete policy file: {str(e)}")
    
    return {"message": f"Policy deleted successfully: {client_id}"}

@app.get("/policies/{client_id}")
async def get_policy(
    client_id: str,
    is_superuser: bool = Depends(authenticate_superuser)
):
    """Get the content of a specific Rego policy (superuser only)"""
    # Ensure the client_id is valid
    if not re.match(r'^[a-zA-Z0-9_]+$', client_id):
        raise HTTPException(status_code=400, detail="Invalid client_id format. Use only alphanumeric characters and underscores.")
    
    # Construct the policy path
    policy_path = f"policies/clients/{client_id}.rego"
    
    # Check if policy exists
    if not os.path.exists(policy_path):
        raise HTTPException(status_code=404, detail=f"Policy not found: {client_id}")
    
    # Read the policy file
    try:
        with open(policy_path, 'r') as f:
            policy_content = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read policy file: {str(e)}")
    
    return {"client_id": client_id, "policy_content": policy_content, "policy_path": policy_path}

@app.patch("/policies/{client_id}/status")
async def update_policy_status(
    client_id: str,
    request: PolicyStatusRequest,
    is_superuser: bool = Depends(authenticate_superuser)
):
    """Enable or disable a policy (superuser only)"""
    # Ensure the client_id is valid
    if not re.match(r'^[a-zA-Z0-9_]+$', client_id):
        raise HTTPException(status_code=400, detail="Invalid client_id format. Use only alphanumeric characters and underscores.")
    
    # Construct the policy path
    policy_path = f"policies/clients/{client_id}.rego"
    
    # Check if policy exists
    if not os.path.exists(policy_path):
        raise HTTPException(status_code=404, detail=f"Policy not found: {client_id}")
    
    # Read the policy file
    try:
        with open(policy_path, 'r') as f:
            policy_content = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read policy file: {str(e)}")
    
    # Check if policy_enabled flag exists
    enabled_match = re.search(r'policy_enabled\s*:=\s*(true|false)', policy_content)
    
    if enabled_match:
        # Update the existing flag
        new_status = "true" if request.enabled else "false"
        updated_content = re.sub(
            r'policy_enabled\s*:=\s*(true|false)',
            f'policy_enabled := {new_status}',
            policy_content
        )
    else:
        # Add the flag if it doesn't exist
        # Find the first line after package declaration to insert the enabled flag
        lines = policy_content.split('\n')
        package_index = -1
        for i, line in enumerate(lines):
            if line.startswith('package '):
                package_index = i
                break
        
        if package_index >= 0:
            # Insert after package and import statements
            insert_index = package_index + 1
            while insert_index < len(lines) and lines[insert_index].startswith('import '):
                insert_index += 1
            
            new_status = "true" if request.enabled else "false"
            lines.insert(insert_index, "\n# Policy status - controls whether this policy is active")
            lines.insert(insert_index + 1, f"policy_enabled := {new_status}")
            
            # Reassemble the policy content
            updated_content = '\n'.join(lines)
        else:
            # If package declaration not found, just prepend the flag
            new_status = "true" if request.enabled else "false"
            updated_content = f"# Policy status - controls whether this policy is active\npolicy_enabled := {new_status}\n\n{policy_content}"
    
    # Write the updated policy file
    try:
        with open(policy_path, 'w') as f:
            f.write(updated_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update policy file: {str(e)}")
    
    status_text = "enabled" if request.enabled else "disabled"
    return {"message": f"Policy {status_text} successfully: {client_id}", "policy_path": policy_path, "enabled": request.enabled}

# ==================== MANIFEST API ENDPOINTS ====================

@app.get("/manifests", response_model=ManifestListResponse)
async def list_project_manifests():
    """List all project manifests"""
    manifests = list_manifests()
    return {"manifests": manifests, "count": len(manifests)}

@app.post("/manifests", response_model=ManifestResponse, status_code=201)
async def create_project_manifest(
    request: ManifestRequest,
    is_superuser: bool = Depends(authenticate_superuser)
):
    """Create a new project manifest (superuser only)"""
    # Validate project_id format
    if not re.match(r'^[a-zA-Z0-9_-]+$', request.manifest.project_id):
        raise HTTPException(
            status_code=400, 
            detail="Invalid project_id format. Use only alphanumeric characters, underscores, and hyphens."
        )
    
    # Check if manifest already exists
    if load_manifest(request.manifest.project_id):
        raise HTTPException(
            status_code=409, 
            detail=f"Manifest already exists: {request.manifest.project_id}"
        )
    
    # Validate module dependencies
    dependency_errors = validate_manifest_dependencies(request.manifest.modules)
    if dependency_errors:
        raise HTTPException(status_code=400, detail="Dependency validation failed: " + "; ".join(dependency_errors))
    
    try:
        manifest_path = save_manifest(request.manifest)
        return {
            "message": f"Manifest created successfully: {request.manifest.project_id}",
            "manifest_id": request.manifest.project_id,
            "manifest_path": manifest_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create manifest: {str(e)}")

@app.get("/manifests/{project_id}")
async def get_project_manifest(
    project_id: str,
    resolve_env: bool = Query(False, description="Resolve environment variables and apply overrides")
):
    """Get a specific project manifest with optional environment variable resolution"""
    if not re.match(r'^[a-zA-Z0-9_-]+$', project_id):
        raise HTTPException(
            status_code=400, 
            detail="Invalid project_id format. Use only alphanumeric characters, underscores, and hyphens."
        )
    
    manifest = get_resolved_manifest(project_id, resolve_env)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Manifest not found: {project_id}")
    
    return manifest

@app.put("/manifests/{project_id}", response_model=ManifestResponse)
async def update_project_manifest(
    project_id: str,
    request: ManifestRequest,
    is_superuser: bool = Depends(authenticate_superuser)
):
    """Update an existing project manifest (superuser only)"""
    if project_id != request.manifest.project_id:
        raise HTTPException(
            status_code=400, 
            detail="project_id in path must match project_id in manifest"
        )
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', project_id):
        raise HTTPException(
            status_code=400, 
            detail="Invalid project_id format. Use only alphanumeric characters, underscores, and hyphens."
        )
    
    # Check if manifest exists
    existing_manifest = load_manifest(project_id)
    if not existing_manifest:
        raise HTTPException(status_code=404, detail=f"Manifest not found: {project_id}")
    
    # Validate module dependencies
    dependency_errors = validate_manifest_dependencies(request.manifest.modules)
    if dependency_errors:
        raise HTTPException(status_code=400, detail="Dependency validation failed: " + "; ".join(dependency_errors))
    
    # Preserve creation timestamp
    request.manifest.created_at = existing_manifest.created_at
    
    try:
        manifest_path = save_manifest(request.manifest)
        return {
            "message": f"Manifest updated successfully: {project_id}",
            "manifest_id": project_id,
            "manifest_path": manifest_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update manifest: {str(e)}")

@app.delete("/manifests/{project_id}")
async def delete_project_manifest(
    project_id: str,
    is_superuser: bool = Depends(authenticate_superuser)
):
    """Delete a project manifest (superuser only)"""
    if not re.match(r'^[a-zA-Z0-9_-]+$', project_id):
        raise HTTPException(
            status_code=400, 
            detail="Invalid project_id format. Use only alphanumeric characters, underscores, and hyphens."
        )
    
    manifest_path = get_manifest_path(project_id)
    
    if not os.path.exists(manifest_path):
        raise HTTPException(status_code=404, detail=f"Manifest not found: {project_id}")
    
    try:
        os.remove(manifest_path)
        return {"message": f"Manifest deleted successfully: {project_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete manifest: {str(e)}")

@app.post("/manifests/validate", response_model=ManifestValidationResponse)
async def validate_project_manifest(request: ManifestValidationRequest):
    """Validate a project manifest without saving it"""
    errors = []
    warnings = []
    
    # Validate project_id format
    if not re.match(r'^[a-zA-Z0-9_-]+$', request.manifest.project_id):
        errors.append("Invalid project_id format. Use only alphanumeric characters, underscores, and hyphens.")
    
    # Validate module dependencies
    dependency_errors = validate_manifest_dependencies(request.manifest.modules)
    errors.extend(dependency_errors)
    
    # Check for duplicate module names
    module_names = [module.name for module in request.manifest.modules]
    duplicate_names = [name for name in set(module_names) if module_names.count(name) > 1]
    if duplicate_names:
        errors.append(f"Duplicate module names found: {', '.join(duplicate_names)}")
    
    # Warning for disabled modules
    disabled_modules = [module.name for module in request.manifest.modules if module.status == ModuleStatus.DISABLED]
    if disabled_modules:
        warnings.append(f"Disabled modules found: {', '.join(disabled_modules)}")
    
    # Warning for deprecated modules
    deprecated_modules = [module.name for module in request.manifest.modules if module.status == ModuleStatus.DEPRECATED]
    if deprecated_modules:
        warnings.append(f"Deprecated modules found: {', '.join(deprecated_modules)}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }

@app.get("/manifests/{project_id}/modules")
async def get_project_modules(
    project_id: str,
    resolve_env: bool = Query(False, description="Resolve environment variables and apply overrides")
):
    """Get all modules for a specific project with optional environment variable resolution"""
    if not re.match(r'^[a-zA-Z0-9_-]+$', project_id):
        raise HTTPException(
            status_code=400, 
            detail="Invalid project_id format. Use only alphanumeric characters, underscores, and hyphens."
        )
    
    manifest = get_resolved_manifest(project_id, resolve_env)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Manifest not found: {project_id}")
    
    return {"modules": manifest.modules, "count": len(manifest.modules)}

@app.get("/manifests/{project_id}/modules/{module_name}")
async def get_project_module(
    project_id: str, 
    module_name: str,
    resolve_env: bool = Query(False, description="Resolve environment variables and apply overrides")
):
    """Get a specific module configuration from a project with optional environment variable resolution"""
    if not re.match(r'^[a-zA-Z0-9_-]+$', project_id):
        raise HTTPException(
            status_code=400, 
            detail="Invalid project_id format. Use only alphanumeric characters, underscores, and hyphens."
        )
    
    module = get_resolved_module(project_id, module_name, resolve_env)
    if not module:
        # Check if project exists first
        manifest = load_manifest(project_id)
        if not manifest:
            raise HTTPException(status_code=404, detail=f"Manifest not found: {project_id}")
        else:
            raise HTTPException(status_code=404, detail=f"Module not found: {module_name}")
    
    return module

@app.get("/manifests/{project_id}/cross-references")
async def get_project_cross_references(project_id: str):
    """Get cross-reference analysis for a project manifest"""
    if not re.match(r'^[a-zA-Z0-9_-]+$', project_id):
        raise HTTPException(
            status_code=400, 
            detail="Invalid project_id format. Use only alphanumeric characters, underscores, and hyphens."
        )
    
    manifest = load_manifest(project_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Manifest not found: {project_id}")
    
    cross_ref_analysis = analyze_cross_references(manifest.modules)
    suggestions = get_cross_reference_suggestions(manifest.modules)
    
    return {
        "project_id": project_id,
        "module_capabilities": cross_ref_analysis,
        "summary": {
            "total_modules": len(manifest.modules)
        }
    }

@app.get("/manifests/{project_id}/cross-references/suggestions")
async def get_cross_reference_suggestions_for_project(project_id: str):
    """Get cross-reference suggestions for a project"""
    if not re.match(r'^[a-zA-Z0-9_-]+$', project_id):
        raise HTTPException(
            status_code=400, 
            detail="Invalid project_id format. Use only alphanumeric characters, underscores, and hyphens."
        )
    
    manifest = load_manifest(project_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Manifest not found: {project_id}")
    
    suggestions = get_cross_reference_suggestions(manifest.modules)
    
    return {
        "project_id": project_id,
        "suggestions": suggestions,
        "summary": {
            "modules_with_suggestions": len(suggestions),
            "total_suggestions": sum(len(s) for s in suggestions.values())
        }
    }

@app.get("/manifests/{project_id}/modules/{module_name}/references")
async def get_module_references(
    project_id: str, 
    module_name: str
):
    """Get all cross-references for a specific module"""
    if not re.match(r'^[a-zA-Z0-9_-]+$', project_id):
        raise HTTPException(
            status_code=400, 
            detail="Invalid project_id format. Use only alphanumeric characters, underscores, and hyphens."
        )
    
    manifest = load_manifest(project_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Manifest not found: {project_id}")
    
    target_module = None
    for module in manifest.modules:
        if module.name == module_name:
            target_module = module
            break
    
    if not target_module:
        raise HTTPException(status_code=404, detail=f"Module not found: {module_name}")
    
    cross_ref_analysis = analyze_cross_references(manifest.modules)
    module_analysis = cross_ref_analysis.get(module_name, {})
    
    return {
        "project_id": project_id,
        "module_name": module_name,
        "module_type": target_module.module_type,
        "provides_services": module_analysis.get("provides", []),
        "references": module_analysis.get("references", {}),
        "referenced_by": module_analysis.get("referenced_by", []),
        "cross_references_raw": target_module.cross_references
    }

@app.get("/module-types")
async def get_available_module_types():
    """Get all available module types and their descriptions"""
    return {
        "module_types": [
            {"type": ModuleType.JWT_CONFIG, "description": "JWT authentication and authorization configuration"},
            {"type": ModuleType.RAG_CONFIG, "description": "Retrieval Augmented Generation system configuration"},
            {"type": ModuleType.API_GATEWAY, "description": "API gateway and routing configuration"},
            {"type": ModuleType.INFERENCE_ENDPOINT, "description": "LLM inference endpoint configuration with prompts"},
            {"type": ModuleType.SECURITY, "description": "Security policies and compliance configuration"},
            {"type": ModuleType.MONITORING, "description": "Monitoring, logging, and observability configuration"},
            {"type": ModuleType.MODEL_REGISTRY, "description": "Model registry and versioning configuration"},
            {"type": ModuleType.DATA_PIPELINE, "description": "Data processing pipeline configuration"},
            {"type": ModuleType.DEPLOYMENT, "description": "Deployment strategy and environment configuration"},
            {"type": ModuleType.RESOURCE_MANAGEMENT, "description": "Resource allocation and scaling configuration"},
            {"type": ModuleType.NOTIFICATIONS, "description": "Notification and alerting configuration"},
            {"type": ModuleType.BACKUP_RECOVERY, "description": "Backup and disaster recovery configuration"}
        ]
    }

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
