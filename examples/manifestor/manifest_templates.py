"""
Module configuration templates for the Manifest Generator
"""

from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from manifest_generator import ManifestGenerator


class ModuleTemplates:
    """Collection of configuration templates for different module types"""
    
    def __init__(self, generator: 'ManifestGenerator'):
        self.gen = generator
    
    def get_config(self, module_type: str, module_name: str, is_apisix: bool = False) -> Dict[str, Any]:
        """Get module configuration based on type"""
        
        templates = {
            "jwt_config": self.jwt_config,
            "rag_config": self.rag_config,
            "rag_service": self.rag_service,
            "model_server": self.model_server,
            "api_gateway": self.apisix_gateway if is_apisix else self.api_gateway,
            "inference_endpoint": self.inference_endpoint,
            "security": self.security,
            "monitoring": self.monitoring,
            "model_registry": self.model_registry,
            "data_pipeline": self.data_pipeline,
            "deployment": self.deployment,
            "resource_management": self.resource_management,
            "notifications": self.notifications,
            "backup_recovery": self.backup_recovery,
            "vault": self.vault,
            "langgraph_workflow": self.langgraph_workflow,
        }
        
        template_func = templates.get(module_type, self.generic)
        return template_func(module_name)
    
    def jwt_config(self, module_name: str) -> Dict[str, Any]:
        """JWT configuration template"""
        print(f"\n{self.gen.Fore.CYAN if hasattr(self.gen, 'Fore') else ''}JWT Configuration Template")
        
        service_url = self.gen.get_input("JWT Service URL", "${environments.${environment}.urls.jwt_service_url}")
        consumer_key = self.gen.get_input("Consumer Key", f"{module_name}-key")
        use_jwe = self.gen.get_choice("Enable JWE encryption?", ["yes", "no"], "no") == "yes"
        
        config = {
            "id": f"{module_name}-config",
            "owner": self.gen.manifest.get("owner", "AI Team"),
            "service_url": service_url,
            "claims": {
                "static": {
                    "key": consumer_key,
                    "rate_limit": int(self.gen.get_input("Rate limit (requests/min)", "100")),
                    "project": self.gen.manifest.get("project_id", "project"),
                    "environment": "${environment}",
                    "exp_hours": int(self.gen.get_input("Token expiration (hours)", "1"))
                }
            }
        }
        
        if use_jwe:
            config["jwe_config"] = {
                "enabled": True,
                "encryption_key": "${environments.${environment}.secrets.jwe_encryption_key}",
                "algorithm": "dir",
                "encryption": "A256GCM",
                "compression": None
            }
            
            for env in ["development", "staging", "production"]:
                if env not in self.gen.environments:
                    self.gen.environments[env] = {"secrets": {}, "urls": {}}
                self.gen.environments[env]["secrets"]["jwe_encryption_key"] = f"${{{env.upper()}_JWE_KEY}}"
        
        for env in ["development", "staging", "production"]:
            if env not in self.gen.environments:
                self.gen.environments[env] = {"secrets": {}, "urls": {}}
            self.gen.environments[env]["urls"]["jwt_service_url"] = "http://localhost:5000" if env == "development" else "https://jwt.example.com"
        
        return config
    
    def rag_config(self, module_name: str) -> Dict[str, Any]:
        """RAG configuration template"""
        print(f"\n{self.gen.Fore.CYAN if hasattr(self.gen, 'Fore') else ''}RAG Configuration Template")
        
        service_url = self.gen.get_input("RAG Service URL", "${environments.${environment}.urls.rag_service_url}")
        config_name = self.gen.get_input("Configuration name", "default")
        vector_store_type = self.gen.get_choice(
            "Vector store type",
            ["faiss", "redis", "elasticsearch", "neo4j_knowledge_graph"],
            "faiss"
        )
        
        config = {
            "service_url": service_url,
            "configuration_name": config_name,
            "vector_store_type": vector_store_type,
            "embedding_model": self.gen.get_input("Embedding model", "BAAI/bge-small-en-v1.5"),
            "chunk_size": int(self.gen.get_input("Chunk size", "500")),
            "chunk_overlap": int(self.gen.get_input("Chunk overlap", "50")),
            "top_k": int(self.gen.get_input("Top K results", "5"))
        }
        
        for env in ["development", "staging", "production"]:
            if env not in self.gen.environments:
                self.gen.environments[env] = {"secrets": {}, "urls": {}}
            self.gen.environments[env]["urls"]["rag_service_url"] = "http://localhost:8080" if env == "development" else "https://rag.example.com"
        
        return config
    
    def rag_service(self, module_name: str) -> Dict[str, Any]:
        """RAG service module template"""
        print(f"\n{self.gen.Fore.CYAN if hasattr(self.gen, 'Fore') else ''}RAG Service Module Template")
        
        service_url = self.gen.get_input("Service URL", "${environments.${environment}.urls.rag_service_url}")
        
        return {
            "service_url": service_url,
            "default_top_k": int(self.gen.get_input("Default top K", "5")),
            "default_similarity_threshold": float(self.gen.get_input("Similarity threshold", "0.7")),
            "use_reranking": self.gen.get_choice("Enable reranking?", ["yes", "no"], "yes") == "yes",
            "query_expansion_enabled": self.gen.get_choice("Enable query expansion?", ["yes", "no"], "no") == "yes"
        }
    
    def model_server(self, module_name: str) -> Dict[str, Any]:
        """Model server template"""
        print(f"\n{self.gen.Fore.CYAN if hasattr(self.gen, 'Fore') else ''}Model Server Template")
        
        service_url = self.gen.get_input("Model Server URL", "http://localhost:8000")
        
        return {
            "service_url": service_url,
            "embeddings_endpoint": "/embeddings",
            "rerank_endpoint": "/rerank",
            "classify_endpoint": "/classify",
            "health_endpoint": "/health",
            "default_embedding_model": self.gen.get_input("Default embedding model", "BAAI/bge-small-en-v1.5"),
            "batch_size": int(self.gen.get_input("Batch size", "32")),
            "request_timeout": int(self.gen.get_input("Request timeout (seconds)", "30"))
        }
    
    def api_gateway(self, module_name: str) -> Dict[str, Any]:
        """Generic API gateway template"""
        print(f"\n{self.gen.Fore.CYAN if hasattr(self.gen, 'Fore') else ''}API Gateway Template")
        
        return {
            "gateway_type": "generic",
            "rate_limiting": {
                "requests_per_minute": int(self.gen.get_input("Rate limit (req/min)", "100"))
            },
            "cors_origins": ["*"],
            "authentication_required": self.gen.get_choice("Require authentication?", ["yes", "no"], "yes") == "yes",
            "api_versioning": self.gen.get_input("API version", "v1"),
            "request_timeout": int(self.gen.get_input("Request timeout (seconds)", "30"))
        }
    
    def apisix_gateway(self, module_name: str) -> Dict[str, Any]:
        """APISIX gateway template"""
        print(f"\n{self.gen.Fore.CYAN if hasattr(self.gen, 'Fore') else ''}APISIX Gateway Template")
        
        route_name = self.gen.get_input("Route name", "default-route")
        route_uri = self.gen.get_input("Route URI", f"/{self.gen.manifest.get('project_id', 'api')}/v1")
        upstream_url = self.gen.get_input("Upstream URL", "${environments.${environment}.urls.upstream_url}")
        
        return {
            "gateway_type": "apisix",
            "admin_api_url": "http://localhost:9180",
            "admin_key": "${APISIX_ADMIN_KEY}",
            "gateway_url": "http://localhost:9080",
            "routes": [
                {
                    "name": route_name,
                    "uri": route_uri,
                    "methods": ["GET", "POST"],
                    "upstream": {
                        "type": "roundrobin",
                        "nodes": {upstream_url: 1},
                        "timeout": {"connect": 60, "send": 60, "read": 60}
                    },
                    "plugins": {
                        "jwt-auth": {},
                        "prometheus": {"prefer_name": True}
                    }
                }
            ],
            "jwt_auth_enabled": True,
            "rate_limiting_enabled": True,
            "prometheus_enabled": True
        }
    
    def inference_endpoint(self, module_name: str) -> Dict[str, Any]:
        """Inference endpoint template"""
        print(f"\n{self.gen.Fore.CYAN if hasattr(self.gen, 'Fore') else ''}Inference Endpoint Template")
        
        model_name = self.gen.get_input("Model name", "llama-3.1-70b-versatile")
        endpoint_url = self.gen.get_input("Endpoint URL", "${environments.${environment}.urls.api_base_url}")
        system_prompt = self.gen.get_input("System prompt", "You are a helpful AI assistant.")
        
        return {
            "model_name": model_name,
            "endpoint_url": endpoint_url,
            "system_prompt": system_prompt,
            "max_tokens": int(self.gen.get_input("Max tokens", "2000")),
            "temperature": float(self.gen.get_input("Temperature", "0.7"))
        }
    
    def security(self, module_name: str) -> Dict[str, Any]:
        """Security module template"""
        print(f"\n{self.gen.Fore.CYAN if hasattr(self.gen, 'Fore') else ''}Security Module Template")
        
        return {
            "encryption_at_rest": True,
            "encryption_in_transit": True,
            "vulnerability_scanning": True,
            "access_control_type": self.gen.get_choice("Access control type", ["rbac", "abac"], "rbac"),
            "audit_logging": True,
            "compliance_standards": []
        }
    
    def monitoring(self, module_name: str) -> Dict[str, Any]:
        """Monitoring module template"""
        print(f"\n{self.gen.Fore.CYAN if hasattr(self.gen, 'Fore') else ''}Monitoring Module Template")
        
        provider = self.gen.get_choice("Monitoring provider", ["prometheus", "langfuse", "datadog", "custom"], "prometheus")
        
        if provider == "langfuse":
            config = {
                "provider": "langfuse",
                "host": "${environments.${environment}.urls.langfuse_host}",
                "public_key": "${environments.${environment}.secrets.langfuse_public_key}",
                "secret_key": "${environments.${environment}.secrets.langfuse_secret_key}",
                "project_name": self.gen.manifest.get("project_id", "project"),
                "sample_rate": float(self.gen.get_input("Sample rate (0.0-1.0)", "1.0")),
                "metadata": {
                    "service": self.gen.manifest.get("project_id", "service"),
                    "environment": "${environment}",
                    "version": self.gen.manifest.get("version", "1.0.0")
                }
            }
            
            for env in ["development", "staging", "production"]:
                if env not in self.gen.environments:
                    self.gen.environments[env] = {"secrets": {}, "urls": {}}
                self.gen.environments[env]["urls"]["langfuse_host"] = "https://cloud.langfuse.com"
                self.gen.environments[env]["secrets"]["langfuse_public_key"] = "${LANGFUSE_PUBLIC_KEY}"
                self.gen.environments[env]["secrets"]["langfuse_secret_key"] = "${LANGFUSE_SECRET_KEY}"
        else:
            config = {
                "provider": provider,
                "metrics_enabled": True,
                "logging_level": self.gen.get_choice("Logging level", ["DEBUG", "INFO", "WARNING", "ERROR"], "INFO"),
                "tracing_enabled": True,
                "health_check_interval": int(self.gen.get_input("Health check interval (seconds)", "30")),
                "alerting_enabled": True
            }
        
        return config
    
    def model_registry(self, module_name: str) -> Dict[str, Any]:
        """Model registry template"""
        print(f"\n{self.gen.Fore.CYAN if hasattr(self.gen, 'Fore') else ''}Model Registry Template")
        
        registry_type = self.gen.get_choice("Registry type", ["mlflow", "wandb", "custom"], "mlflow")
        registry_url = self.gen.get_input("Registry URL", "http://localhost:5000")
        
        return {
            "registry_type": registry_type,
            "registry_url": registry_url,
            "auto_versioning": True,
            "model_validation": True,
            "metadata_tracking": True,
            "experiment_tracking": True
        }
    
    def data_pipeline(self, module_name: str) -> Dict[str, Any]:
        """Data pipeline template"""
        print(f"\n{self.gen.Fore.CYAN if hasattr(self.gen, 'Fore') else ''}Data Pipeline Template")
        
        pipeline_type = self.gen.get_choice("Pipeline type", ["batch", "streaming", "hybrid"], "batch")
        processing_engine = self.gen.get_choice("Processing engine", ["spark", "airflow", "dagster", "custom"], "airflow")
        
        return {
            "pipeline_type": pipeline_type,
            "data_sources": [],
            "data_sinks": [],
            "processing_engine": processing_engine,
            "schedule": self.gen.get_input("Schedule (cron format, optional)", ""),
            "data_quality_checks": True
        }
    
    def deployment(self, module_name: str) -> Dict[str, Any]:
        """Deployment module template"""
        print(f"\n{self.gen.Fore.CYAN if hasattr(self.gen, 'Fore') else ''}Deployment Module Template")
        
        strategy = self.gen.get_choice("Deployment strategy", ["blue_green", "canary", "rolling"], "blue_green")
        platform = self.gen.get_choice("Orchestration platform", ["k8s", "docker-compose", "ecs"], "k8s")
        
        return {
            "deployment_strategy": strategy,
            "container_registry": self.gen.get_input("Container registry URL", "docker.io"),
            "orchestration_platform": platform,
            "auto_scaling": True,
            "rollback_enabled": True,
            "environment_configs": {}
        }
    
    def resource_management(self, module_name: str) -> Dict[str, Any]:
        """Resource management template"""
        print(f"\n{self.gen.Fore.CYAN if hasattr(self.gen, 'Fore') else ''}Resource Management Template")
        
        return {
            "compute_resources": {},
            "storage_resources": {},
            "network_resources": {},
            "auto_scaling_policies": {},
            "cost_optimization": True,
            "resource_quotas": {}
        }
    
    def notifications(self, module_name: str) -> Dict[str, Any]:
        """Notifications module template"""
        print(f"\n{self.gen.Fore.CYAN if hasattr(self.gen, 'Fore') else ''}Notifications Module Template")
        
        return {
            "email_enabled": self.gen.get_choice("Enable email?", ["yes", "no"], "yes") == "yes",
            "slack_enabled": self.gen.get_choice("Enable Slack?", ["yes", "no"], "no") == "yes",
            "webhook_enabled": self.gen.get_choice("Enable webhooks?", ["yes", "no"], "no") == "yes",
            "notification_channels": {},
            "alert_rules": [],
            "escalation_policies": []
        }
    
    def backup_recovery(self, module_name: str) -> Dict[str, Any]:
        """Backup and recovery template"""
        print(f"\n{self.gen.Fore.CYAN if hasattr(self.gen, 'Fore') else ''}Backup & Recovery Template")
        
        frequency = self.gen.get_choice("Backup frequency", ["hourly", "daily", "weekly"], "daily")
        
        return {
            "backup_enabled": True,
            "backup_frequency": frequency,
            "retention_policy": self.gen.get_input("Retention policy", "30d"),
            "disaster_recovery_enabled": True,
            "backup_storage_type": self.gen.get_choice("Storage type", ["cloud", "local", "hybrid"], "cloud"),
            "restore_testing": True
        }
    
    def vault(self, module_name: str) -> Dict[str, Any]:
        """Vault module template"""
        print(f"\n{self.gen.Fore.CYAN if hasattr(self.gen, 'Fore') else ''}HashiCorp Vault Template")
        
        instance_name = self.gen.get_input("Vault instance name", "default-vault")
        vault_url = self.gen.get_input("Vault URL", "http://localhost:8200")
        auth_method = self.gen.get_choice("Auth method", ["token", "approle"], "token")
        
        instance = {
            "instance_name": instance_name,
            "vault_url": vault_url,
            "auth_method": auth_method,
            "kv_mount_point": "secret",
            "kv_version": 2,
            "verify_ssl": self.gen.get_choice("Verify SSL?", ["yes", "no"], "yes") == "yes"
        }
        
        if auth_method == "token":
            instance["vault_token"] = self.gen.get_input("Vault token", "myroot")
        else:
            instance["role_id"] = self.gen.get_input("Role ID", "env:VAULT_ROLE_ID")
            instance["secret_id"] = self.gen.get_input("Secret ID", "env:VAULT_SECRET_ID")
        
        return {
            "vault_instances": [instance],
            "encryption_enabled": False,
            "cache_secrets": True,
            "cache_ttl": 300
        }
    
    def langgraph_workflow(self, module_name: str) -> Dict[str, Any]:
        """LangGraph workflow template"""
        print(f"\n{self.gen.Fore.CYAN if hasattr(self.gen, 'Fore') else ''}LangGraph Workflow Template")
        
        workflow_name = self.gen.get_input("Workflow name", module_name)
        workflow_type = self.gen.get_choice("Workflow type", ["sequential", "parallel", "conditional"], "sequential")
        
        return {
            "workflow_name": workflow_name,
            "workflow_type": workflow_type,
            "nodes": [],
            "edges": [],
            "state_schema": {},
            "max_iterations": int(self.gen.get_input("Max iterations", "10")),
            "timeout_seconds": int(self.gen.get_input("Timeout (seconds)", "300")),
            "tracing_enabled": True
        }
    
    def generic(self, module_name: str) -> Dict[str, Any]:
        """Generic template for unknown module types"""
        return {}
