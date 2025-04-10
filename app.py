import os
import json
import subprocess
import hashlib
import secrets
from fastapi import FastAPI, HTTPException, Body, Depends, Header
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import uvicorn
import re

app = FastAPI(title="DSP AI Control Tower - OPA Policy Evaluator: /dspai-docs", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/dspai-docs", include_in_schema=False)
async def swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="FastAPI",
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

def extract_aihpc_config(policy_content: str, aihpc_env: str, aihpc_lane: str) -> Dict[str, str]:
    """Extract AIHPC configuration from policy content for a specific environment and lane"""
    # Extract aihpc configuration for the specified environment
    aihpc_match = re.search(r'aihpc\.' + aihpc_env + r'\s*:=\s*({[^}]+})', policy_content, re.DOTALL)
    if not aihpc_match:
        raise HTTPException(status_code=400, detail=f"AIHPC configuration not defined for environment: {aihpc_env}")
    
    # Extract the specific environment configuration
    env_match = re.search(rf'"{aihpc_lane}"\s*:\s*({{.*?}})', aihpc_match.group(1), re.DOTALL)
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

def hash_secret(secret: str, salt: str = None) -> tuple:
    """Hash a secret with a salt using SHA-256"""
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Create a hash with the salt
    hash_obj = hashlib.sha256((secret + salt).encode())
    hashed_secret = hash_obj.hexdigest()
    
    return hashed_secret, salt

async def authenticate_client(
    x_dspai_client_id: str = Header(..., description="Client ID (policy file name)", alias="X-DSPAI-Client-ID"),
    x_dspai_client_secret: str = Header(..., description="Client secret for authentication", alias="X-DSPAI-Client-Secret")
):
    """Authenticate client using client_id and client_secret from headers"""
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
    return {"message": "DSP AI Control Tower - OPA Policy Evaluator API. Swagger: /dspai-docs"}

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
                policies.append(policy_path)
    
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

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
