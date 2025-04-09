package dspai.policy
import rego.v1

# Declare version
version := 1
project := "customer_service"
# Client authentication
# The secret is now hashed with SHA-256 and salt
client_secret := "db4a2b9e13a5b84c2c01a95e937ae816f9065ccb03f01f6cedc1baf310fe9ec9" # Hash of "password" with the salt below

client_salt := "0123456789abcdef0123456789abcdef" # Example salt

# Default deny all access
default allow := false

aihpc := {
	"training_dev": {"account": "td_acct", "partition": "td_part", "num_gpu": 1, },
	"training_prod": {"account": "td_acct", "partition": "td_part", },
	"inference_dev": {"account": "td_acct", "partition": "td_part", "num_gpu": 1, },
	"inference_prod": {"account": "td_acct", "partition": "td_part", },
}

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
	"business_user": ["infer"],
}

# Define user IDs with their assigned roles
user_roles := {
	"user789": "ml_engineer",
	"user101": "business_user",
}

# Define group IDs with their assigned roles
group_roles := {
	"group002": "data_scientist",
	"group003": "ml_engineer",
	"group004": "business_user",
}

# Helper function to find index of an item in an array
indexOf(arr, val) := i if {
	arr[i] == val
} else := -1

# Get role for a user based on user ID and group memberships
# Returns the highest privilege role if user belongs to multiple groups
get_user_role(user_id, group_ids) := role if {
	# Check if user has a direct role assignment
	user_roles[user_id]
	role := user_roles[user_id]
} else := role if {
	# Check if user belongs to any groups with roles
	user_groups := [group_id | group_id = group_ids[_]; group_roles[group_id]]
	count(user_groups) > 0

	# Get all roles from user's groups
	group_assigned_roles := [group_roles[g] | g = user_groups[_]]

	# Define role hierarchy (higher index = higher privilege)
	role_hierarchy := ["business_user", "ml_engineer", "data_scientist", "llm_admin"]

	# Find the highest privilege role
	highest_role_index := max([indexOf(role_hierarchy, r) | r = group_assigned_roles[_]])
	role := role_hierarchy[highest_role_index]
} else := "unauthorized"

# Determine the effective role for the user
effective_role := role if {
	# If input.user has a direct role field, use that (backward compatibility)
	input.user.role
	role := input.user.role
} else := role if {
	# Otherwise, determine role from user ID and groups
	input.user.id
	groups := object.get(input.user, "groups", [])
	role := get_user_role(input.user.id, groups)
} else := "unauthorized"

# Check if model is allowed for customer service
model_allowed_for_usecase if {
	some i
	allowed_models[i] == input.resource.model_id
}

# Check if user has required role
has_role if {
	role := effective_role
	roles[role]
}

# Check if action is allowed for role
action_allowed_for_role if {
	some i
	role := effective_role
	roles[role][i] == input.action
}

# Simplified allow rule - combines all conditions
allow if {
	# Validate input
	valid_input

	# Basic authorization checks
	has_role
	action_allowed_for_role

	# Model-specific checks
	model_allowed_for_usecase

	# Action-specific validations
	action_valid
}

# Action-specific validations
action_valid if {
	input.action == "read"
}

action_valid if {
	input.action == "create"
}

action_valid if {
	input.action == "update"
}

action_valid if {
	input.action == "delete"
}

action_valid if {
	input.action == "deploy"
	valid_deploy
}

action_valid if {
	input.action == "train"
	valid_train
}

action_valid if {
	input.action == "infer"
	valid_infer
}

# Training validation
valid_train if {}

# Must have approved training data
#input.resource.training_data.approved == true

# Must have risk assessment
#input.resource.risk_assessment.completed == true
#input.resource.risk_assessment.approved == true

# Must have MRM review for training
#input.resource.mrm_review.completed == true
#input.resource.mrm_review.approved == true

# Inference validation
valid_infer if {}

# Model must be in approved state
#input.resource.status == "approved"
# Must have active monitoring
#input.resource.monitoring.active == true

# Deployment validation
valid_deploy if {}

# Must have all required approvals
#input.resource.approvals.security == true
#input.resource.approvals.compliance == true
#input.resource.approvals.mrm == true
# Must have deployment plan
#input.resource.deployment_plan.exists == true
#input.resource.deployment_plan.approved == true
