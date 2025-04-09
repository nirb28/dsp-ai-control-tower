# DSP AI Control Tower - OPA Policy Evaluator

A FastAPI application that provides endpoints to evaluate OPA (Open Policy Agent) Rego policies with client authentication.

## Setup

1. Create and activate a virtual environment:
   ```
   # Create the virtual environment
   python -m venv venv
   
   # Activate the virtual environment
   # On Windows:
   .\venv\Scripts\activate
   # On Unix or MacOS:
   source venv/bin/activate
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python app.py
   ```

   The API will be available at http://localhost:8000

## Client Authentication

The API uses client authentication based on client ID and client secret:

1. Client ID: This is the name of the Rego policy file (without the .rego extension) in the `policies/clients/` directory.
2. Client Secret: This is defined in the Rego policy file as `client_secret := "your_secret_here"`.

Each request to the API must include both the client ID and client secret for authentication.

## API Endpoints

### GET /
- Returns a welcome message
- Response: `{"message": "DSP AI Control Tower - OPA Policy Evaluator API"}`

### GET /policies
- Lists all available Rego policies in the policies/clients directory
- Response: `{"policies": ["policies/clients/customer_service.rego", ...]}`

### POST /evaluate
- Evaluates input data against the policy associated with the client ID
- Request body:
  ```json
  {
    "input_data": {
      "user": {"role": "data_scientist"},
      "action": "infer",
      "resource": {
        "type": "llm_model",
        "model_id": "gpt-4",
        "status": "approved",
        "monitoring": {"active": true}
      },
      "usecase": "customer_service"
    },
    "client_id": "customer_service",
    "client_secret": "customer_service_secret_123"
  }
  ```
- Response:
  ```json
  {
    "result": {
      "result": [...]
    },
    "allow": true,
    "policy_path": "policies/clients/customer_service.rego"
  }
  ```

### POST /batch-evaluate
- Evaluates input data against the policy associated with the client ID
- Request body:
  ```json
  {
    "input_data": {
      "user": {"role": "business_user"},
      "action": "infer",
      "resource": {
        "type": "llm_model",
        "model_id": "gpt-4",
        "status": "approved",
        "monitoring": {"active": true}
      },
      "usecase": "customer_service"
    },
    "client_id": "customer_service",
    "client_secret": "customer_service_secret_123"
  }
  ```
- Response:
  ```json
  {
    "results": [
      {
        "policy_path": "policies/clients/customer_service.rego",
        "result": {...},
        "allow": true
      }
    ]
  }
  ```

### POST /templates/jupyter-lab
- Generates a Jupyter Lab job template for HPC Slurm cluster based on client policy
- Request headers:
  - `X-DSPAI-Client-ID`: Client ID (policy file name)
  - `X-DSPAI-Client-Secret`: Client secret for authentication
- Request body:
  ```json
  {
    "env_type": "training_dev",
    "username": "user123",
    "conda_env": "pytorch",
    "port": 8888
  }
  ```
- Response:
  ```json
  {
    "template": {
      "job": {
        "name": "customer_service",
        "account": "td_acct",
        "partition": "td_part",
        "tres_per_job": "gres/gpu:1",
        "time_limit": 480,
        "comment": "WORKBENCH:malts,JOB_TYPE:JupyterLab, MODEL_NAME: gpt-4, claude-2, llama-2-70b",
        "current_working_directory": "/core/trainingdev/malts/malts_training_dev/slurm_output",
        "environment": {
          "NVIDIA_VISIBLE_DEVICES": "all",
          "NVIDIA_DRIVER_CAPABILITIES": "compute,utility",
          "PATH": "/bin:/usr/bin/:/usr/local/bin/:/core/conda/bin",
          "LD_LIBRARY_PATH": "/lib/:/lib64/:/usr/local/lib",
          "WORKBENCH": "malts"
        },
        "script": "#!/bin/bash\n bash /core/app/scripts/slurm_jupyter_script.sh\necho \"Task completed.\""
      }
    },
    "message": "Jupyter Lab template generated successfully"
  }
  ```

### POST /templates/model-deployment
- Generates a Model Deployment job template for HPC Slurm cluster based on client policy
- Request headers:
  - `X-DSPAI-Client-ID`: Client ID (policy file name)
  - `X-DSPAI-Client-Secret`: Client secret for authentication
- Request body:
  ```json
  {
    "env_type": "inference_dev",
    "username": "user123",
    "model_name": "sentiment_analysis",
    "conda_env": "pytorch",
    "script_path": "app.server",
    "model_dir": "/models/sentiment",
    "port": 8000,
    "workers": 2
  }
  ```
- Response:
  ```json
  {
    "template": {
      "job": {
        "name": "customer_service",
        "account": "td_acct",
        "partition": "td_part",
        "tres_per_job": "gres/gpu:1",
        "time_limit": 10080,
        "comment": "WORKBENCH:malts,JOB_TYPE:ModelDeployment, MODEL_NAME: sentiment_analysis",
        "current_working_directory": "/home/user123/models/sentiment_analysis",
        "environment": {
          "NVIDIA_VISIBLE_DEVICES": "all",
          "NVIDIA_DRIVER_CAPABILITIES": "compute,utility",
          "PATH": "/bin:/usr/bin/:/usr/local/bin/:/core/conda/bin",
          "LD_LIBRARY_PATH": "/lib/:/lib64/:/usr/local/lib",
          "WORKBENCH": "malts",
          "MODEL_PATH": "/home/user123/models/sentiment_analysis",
          "LOG_DIR": "/home/user123/models/sentiment_analysis/logs"
        },
        "script": "#!/bin/bash\n source activate pytorch; python -m app.server --model-dir=/models/sentiment --port=8000 --workers=2\necho \"Model deployment completed.\""
      }
    },
    "message": "Model Deployment template generated successfully"
  }
  ```

## Example Usage

You can use curl or any HTTP client to interact with the API:

```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "input_data": {
      "user": {"role": "data_scientist"},
      "action": "infer",
      "resource": {
        "type": "llm_model",
        "model_id": "gpt-4",
        "status": "approved",
        "monitoring": {"active": true}
      },
      "usecase": "customer_service"
    },
    "client_id": "customer_service",
    "client_secret": "customer_service_secret_123"
  }'
```

## Example Usage for HPC Templates

You can use curl or any HTTP client to interact with the template generation endpoints:

```bash
# Generate a Jupyter Lab template
curl -X POST http://localhost:8000/templates/jupyter-lab \
  -H "Content-Type: application/json" \
  -H "X-DSPAI-Client-ID: customer_service" \
  -H "X-DSPAI-Client-Secret: password" \
  -d '{
    "env_type": "training_dev",
    "username": "user123",
    "conda_env": "pytorch",
    "port": 8888
  }'

# Generate a Model Deployment template
curl -X POST http://localhost:8000/templates/model-deployment \
  -H "Content-Type: application/json" \
  -H "X-DSPAI-Client-ID: customer_service" \
  -H "X-DSPAI-Client-Secret: password" \
  -d '{
    "env_type": "inference_dev",
    "username": "user123",
    "model_name": "sentiment_analysis",
    "conda_env": "pytorch",
    "script_path": "app.server",
    "model_dir": "/models/sentiment",
    "port": 8000,
    "workers": 2
  }'
```

## Adding a New Client

To add a new client:

1. Create a new Rego policy file in the `policies/clients/` directory (e.g., `new_client.rego`)
2. Add the client secret to the policy file:
   ```rego
   # Client authentication
   client_secret := "your_secure_secret_here"
   ```
3. Define the policy rules for this client in the same file

## Interactive API Documentation

FastAPI automatically generates interactive API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc