package dspai.policy.tests

import rego.v1
import data.dspai.policy

# Test valid customer service access for data scientist
test_allow_data_scientist_infer if {
    # Mock input for data scientist performing inference
    mock_input := {
        "user": {"role": "data_scientist"},
        "action": "infer",
        "resource": {
            "type": "llm_model",
            "model_id": "gpt-4",
            "status": "approved",
            "monitoring": {"active": true}
        },
        "usecase": "customer_service"
    }
    
    # Assert that access is allowed
    policy.allow with input as mock_input
}

# Test valid customer service access for llm_admin
test_allow_llm_admin_deploy if {
    # Mock input for llm_admin performing deployment
    mock_input := {
        "user": {"role": "llm_admin"},
        "action": "deploy",
        "resource": {
            "type": "llm_model",
            "model_id": "claude-2",
            "approvals": {
                "security": true,
                "compliance": true,
                "mrm": true
            },
            "deployment_plan": {
                "exists": true,
                "approved": true
            }
        },
        "usecase": "customer_service"
    }
    
    # Assert that access is allowed
    policy.allow with input as mock_input
}

# Test valid customer service access for ml_engineer
test_allow_ml_engineer_deploy if {
    # Mock input for ml_engineer performing deployment
    mock_input := {
        "user": {"role": "ml_engineer"},
        "action": "deploy",
        "resource": {
            "type": "llm_model",
            "model_id": "llama-2-70b",
            "approvals": {
                "security": true,
                "compliance": true,
                "mrm": true
            },
            "deployment_plan": {
                "exists": true,
                "approved": true
            }
        },
        "usecase": "customer_service"
    }
    
    # Assert that access is allowed
    policy.allow with input as mock_input
}

# Test valid customer service access for business_user
test_allow_business_user_infer if {
    # Mock input for business_user performing inference
    mock_input := {
        "user": {"role": "business_user"},
        "action": "infer",
        "resource": {
            "type": "llm_model",
            "model_id": "gpt-4",
            "status": "approved",
            "monitoring": {"active": true}
        },
        "usecase": "customer_service"
    }
    
    # Assert that access is allowed
    policy.allow with input as mock_input
}

# Test invalid action for role
test_deny_business_user_train if {
    # Mock input for business_user attempting to train (not allowed)
    mock_input := {
        "user": {"role": "business_user"},
        "action": "train",
        "resource": {
            "type": "llm_model",
            "model_id": "gpt-4",
            "training_data": {"approved": true},
            "risk_assessment": {
                "completed": true,
                "approved": true
            },
            "mrm_review": {
                "completed": true,
                "approved": true
            }
        },
        "usecase": "customer_service"
    }
    
    # Assert that access is denied
    not policy.allow with input as mock_input
}

# Test invalid model for customer service
test_deny_invalid_model if {
    # Mock input with invalid model
    mock_input := {
        "user": {"role": "data_scientist"},
        "action": "infer",
        "resource": {
            "type": "llm_model",
            "model_id": "gpt-3",  # Not in allowed models
            "status": "approved",
            "monitoring": {"active": true}
        },
        "usecase": "customer_service"
    }
    
    # Assert that access is denied
    not policy.allow with input as mock_input
}

# Test missing required field for train action
test_deny_missing_train_requirements if {
    # Mock input missing required training approvals
    mock_input := {
        "user": {"role": "data_scientist"},
        "action": "train",
        "resource": {
            "type": "llm_model",
            "model_id": "gpt-4",
            "training_data": {"approved": true},
            "risk_assessment": {
                "completed": true,
                "approved": false  # Missing approval
            },
            "mrm_review": {
                "completed": true,
                "approved": true
            }
        },
        "usecase": "customer_service"
    }
    
    # Assert that access is denied
    not policy.allow with input as mock_input
}
