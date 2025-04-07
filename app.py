import os
import json
import subprocess
import hashlib
import secrets
from fastapi import FastAPI, HTTPException, Body, Depends, Header
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import uvicorn
import re

app = FastAPI(title="DSP AI Control Tower - OPA Policy Evaluator: /dspai-docs", docs_url="/dspai-docs", redoc_url=None)

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
    return {"message": "DSP AI Control Tower - OPA Policy Evaluator API"}

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
            "opa.exe", "eval", 
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

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
