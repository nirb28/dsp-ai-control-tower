import json
import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

# Mock client credentials for testing
TEST_CLIENT_ID = "customer_service"
TEST_CLIENT_SECRET = "password"  # This matches the hashed secret in the customer_service.rego file

# Headers for authentication
AUTH_HEADERS = {
    "X-DSPAI-Client-ID": TEST_CLIENT_ID,
    "X-DSPAI-Client-Secret": TEST_CLIENT_SECRET
}


class TestHpcTemplateGeneration:
    """Tests for HPC template generation endpoints"""

    def test_jupyter_lab_template_generation(self):
        """Test the Jupyter Lab template generation endpoint"""
        # Test request data
        request_data = {
            "env_type": "training_dev",
            "username": "test_user",
            "conda_env": "pytorch",
            "port": 8888
        }

        # Make request to the endpoint
        response = client.post(
            "/templates/jupyter-lab",
            json=request_data,
            headers=AUTH_HEADERS
        )

        # Check response status code
        assert response.status_code == 200

        # Parse response data
        response_data = response.json()

        # Check response structure
        assert "template" in response_data
        assert "message" in response_data
        assert response_data["message"] == "Jupyter Lab template generated successfully"

        # Check template content
        template = response_data["template"]
        assert "job" in template
        assert template["job"]["account"] == "td_acct"
        assert template["job"]["partition"] == "td_part"
        assert template["job"]["tres_per_job"] == "gres/gpu:1"
        assert "MODEL_NAME: gpt-4, claude-2, llama-2-70b" in template["job"]["comment"]

    def test_jupyter_lab_invalid_env_type(self):
        """Test the Jupyter Lab template generation with an invalid environment type"""
        # Test request data with invalid env_type
        request_data = {
            "env_type": "nonexistent_env",
            "username": "test_user",
            "conda_env": "pytorch",
            "port": 8888
        }

        # Make request to the endpoint
        response = client.post(
            "/templates/jupyter-lab",
            json=request_data,
            headers=AUTH_HEADERS
        )

        # Check response status code
        assert response.status_code == 400
        assert "Environment type not defined" in response.json()["detail"]

    def test_model_deployment_template_generation(self):
        """Test the Model Deployment template generation endpoint"""
        # Test request data
        request_data = {
            "env_type": "inference_dev",
            "username": "test_user",
            "model_name": "sentiment_analysis",
            "conda_env": "pytorch",
            "script_path": "app.server",
            "model_dir": "/models/sentiment",
            "port": 8000,
            "workers": 2
        }

        # Make request to the endpoint
        response = client.post(
            "/templates/model-deployment",
            json=request_data,
            headers=AUTH_HEADERS
        )

        # Check response status code
        assert response.status_code == 200

        # Parse response data
        response_data = response.json()

        # Check response structure
        assert "template" in response_data
        assert "message" in response_data
        assert response_data["message"] == "Model Deployment template generated successfully"

        # Check template content
        template = response_data["template"]
        assert "job" in template
        assert template["job"]["account"] == "td_acct"
        assert template["job"]["partition"] == "td_part"
        assert template["job"]["tres_per_job"] == "gres/gpu:1"
        assert "MODEL_NAME: sentiment_analysis" in template["job"]["comment"]

    def test_model_deployment_invalid_env_type(self):
        """Test the Model Deployment template generation with an invalid environment type"""
        # Test request data with invalid env_type
        request_data = {
            "env_type": "nonexistent_env",
            "username": "test_user",
            "model_name": "sentiment_analysis",
            "conda_env": "pytorch",
            "script_path": "app.server",
            "model_dir": "/models/sentiment",
            "port": 8000,
            "workers": 2
        }

        # Make request to the endpoint
        response = client.post(
            "/templates/model-deployment",
            json=request_data,
            headers=AUTH_HEADERS
        )

        # Check response status code
        assert response.status_code == 400
        assert "Environment type not defined" in response.json()["detail"]

    def test_authentication_failure(self):
        """Test authentication failure with invalid credentials"""
        # Test request data
        request_data = {
            "env_type": "training_dev",
            "username": "test_user",
            "conda_env": "pytorch",
            "port": 8888
        }

        # Invalid headers
        invalid_headers = {
            "X-DSPAI-Client-ID": TEST_CLIENT_ID,
            "X-DSPAI-Client-Secret": "wrong_password"
        }

        # Make request to the endpoint
        response = client.post(
            "/templates/jupyter-lab",
            json=request_data,
            headers=invalid_headers
        )

        # Check response status code
        assert response.status_code == 401
        assert "Invalid client secret" in response.json()["detail"]
