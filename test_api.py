import requests
import json

BASE_URL = "http://localhost:8000"

def test_root_endpoint():
    """Test the root endpoint"""
    response = requests.get(f"{BASE_URL}/")
    print("Root Endpoint Response:", response.json())
    assert response.status_code == 200

def test_list_policies():
    """Test listing all policies"""
    response = requests.get(f"{BASE_URL}/policies")
    print("List Policies Response:", json.dumps(response.json(), indent=2))
    assert response.status_code == 200

def test_evaluate_policy():
    """Test evaluating a single policy"""
    # Sample input data for a data scientist trying to perform inference
    input_data = {
        "user": {"role": "data_scientist"},
        "action": "infer",
        "resource": {
            "type": "llm_model",
            "model_id": "gpt-4",
            "status": "approved",
            "monitoring": {"active": True}
        },
        "usecase": "customer_service"
    }
    
    # Use client ID and client secret in headers
    headers = {
        "X-Client-ID": "customer_service",
        "X-Client-Secret": "customer_service_secret_123"
    }
    
    payload = {
        "input_data": input_data
    }
    
    response = requests.post(f"{BASE_URL}/evaluate", json=payload, headers=headers)
    print("Evaluate Policy Response:", json.dumps(response.json(), indent=2))
    assert response.status_code == 200

def test_batch_evaluate():
    """Test batch evaluation of multiple policies"""
    # Sample input data for a business user trying to perform inference
    input_data = {
        "user": {"role": "business_user"},
        "action": "infer",
        "resource": {
            "type": "llm_model",
            "model_id": "gpt-4",
            "status": "approved",
            "monitoring": {"active": True}
        },
        "usecase": "customer_service"
    }
    
    # Use client ID and client secret in headers
    headers = {
        "X-Client-ID": "customer_service",
        "X-Client-Secret": "customer_service_secret_123"
    }
    
    response = requests.post(f"{BASE_URL}/batch-evaluate", json=input_data, headers=headers)
    print("Batch Evaluate Response:", json.dumps(response.json(), indent=2))
    assert response.status_code == 200

if __name__ == "__main__":
    print("Testing DSP AI Control Tower OPA Policy Evaluator API")
    
    try:
        test_root_endpoint()
        test_list_policies()
        test_evaluate_policy()
        test_batch_evaluate()
        print("\nAll tests passed successfully!")
    except Exception as e:
        print(f"\nTest failed: {str(e)}")
        print("Make sure the API server is running with 'python app.py'")
