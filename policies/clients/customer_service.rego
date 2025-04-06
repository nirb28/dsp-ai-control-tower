package dspai.policy

import rego.v1

# Client authentication
# The secret is now hashed with SHA-256 and salt
client_secret := "db4a2b9e13a5b84c2c01a95e937ae816f9065ccb03f01f6cedc1baf310fe9ec9" # Hash of "password" with the salt below
client_salt := "0123456789abcdef0123456789abcdef" # Example salt

# Declare version
version = 1

# Default deny all access
default allow := false

# Input schema validation
valid_input if {
    input.user
    input.action
    input.resource
    input.usecase == "customer_service"
    input.resource.type == "llm_model"
}

# Define allowed models for customer service
allowed_models := ["gpt-4", "claude-2", "llama-2-70b"]

# Define roles and their permissions
roles := {
    "llm_admin": ["create", "read", "update", "delete", "deploy", "train", "infer"],
    "data_scientist": ["read", "train", "infer"],
    "ml_engineer": ["read", "deploy", "infer"],
    "business_user": ["infer"]
}

# Check if model is allowed for customer service
model_allowed_for_usecase if {
    some i
    allowed_models[i] == input.resource.model_id
}

# Check if user has required role
has_role if {
    some role
    role == input.user.role
    roles[role]
}

# Check if action is allowed for role
action_allowed_for_role if {
    some i
    roles[input.user.role][i] == input.action
}

# Main allow rule for basic actions (read, create, update, delete)
allow if {
    # Validate input
    valid_input
    
    # Basic authorization checks
    has_role
    action_allowed_for_role
    
    # Model-specific checks
    model_allowed_for_usecase
    
    # Only for basic actions
    basic_action
}

# Check if action is a basic action
basic_action if {
    input.action == "read"
}

basic_action if {
    input.action == "create"
}

basic_action if {
    input.action == "update"
}

basic_action if {
    input.action == "delete"
}

# Allow rule for train action
allow if {
    # Validate input
    valid_input
    
    # Basic authorization checks
    has_role
    action_allowed_for_role
    
    # Model-specific checks
    model_allowed_for_usecase
    
    # Specific to train action
    input.action == "train"
    valid_train
}

# Allow rule for deploy action
allow if {
    # Validate input
    valid_input
    
    # Basic authorization checks
    has_role
    action_allowed_for_role
    
    # Model-specific checks
    model_allowed_for_usecase
    
    # Specific to deploy action
    input.action == "deploy"
    valid_deploy
}

# Allow rule for infer action
allow if {
    # Validate input
    valid_input
    
    # Basic authorization checks
    has_role
    action_allowed_for_role
    
    # Model-specific checks
    model_allowed_for_usecase
    
    # Specific to infer action
    input.action == "infer"
    valid_infer
}

# Training validation
valid_train if {
    # Must have approved training data
    input.resource.training_data.approved == true
    
    # Must have risk assessment
    input.resource.risk_assessment.completed == true
    input.resource.risk_assessment.approved == true
    
    # Must have MRM review for training
    input.resource.mrm_review.completed == true
    input.resource.mrm_review.approved == true
}

# Inference validation
valid_infer if {
    # Model must be in approved state
    input.resource.status == "approved"
    
    # Must have active monitoring
    input.resource.monitoring.active == true
}

# Deployment validation
valid_deploy if {
    # Must have all required approvals
    input.resource.approvals.security == true
    input.resource.approvals.compliance == true
    input.resource.approvals.mrm == true
    
    # Must have deployment plan
    input.resource.deployment_plan.exists == true
    input.resource.deployment_plan.approved == true
}
