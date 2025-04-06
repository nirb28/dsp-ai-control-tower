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
    
    # Use client ID and client secret in headers with the DSPAI prefix
    headers = {
        "X-DSPAI-Client-ID": "customer_service",
        "X-DSPAI-Client-Secret": "password"  # This matches the hashed secret in the policy file
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
    
    # Use client ID and client secret in headers with the DSPAI prefix
    headers = {
        "X-DSPAI-Client-ID": "customer_service",
        "X-DSPAI-Client-Secret": "password"  # This matches the hashed secret in the policy file
    }
    
    response = requests.post(f"{BASE_URL}/batch-evaluate", json=input_data, headers=headers)
    print("Batch Evaluate Response:", json.dumps(response.json(), indent=2))
    assert response.status_code == 200

def test_generate_client_secret():
    """Test generating a hashed client secret"""
    payload = {
        "client_id": "test_client",
        "plain_secret": "test_secret"
    }
    
    response = requests.post(f"{BASE_URL}/generate-client-secret", json=payload)
    print("Generate Client Secret Response:", json.dumps(response.json(), indent=2))
    assert response.status_code == 200
    assert "hashed_secret" in response.json()
    assert "salt" in response.json()

if __name__ == "__main__":
    print("Testing DSP AI Control Tower OPA Policy Evaluator API")
    
    try:
        test_root_endpoint()
        test_list_policies()
        test_generate_client_secret()
        test_evaluate_policy()
        test_batch_evaluate()
        print("\nAll tests passed successfully!")
    except Exception as e:
        print(f"\nTest failed: {str(e)}")
        print("Make sure the API server is running with 'python app.py'")
