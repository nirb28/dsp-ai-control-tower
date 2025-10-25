"""
LangGraph Document Summarizer Example

This example demonstrates how to use the LangGraph workflow module
for document summarization with the FD/CT/JWT architecture.

Prerequisites:
1. Control Tower running on http://localhost:9000
2. Front Door running on http://localhost:8080
3. APISIX gateway configured and running
4. Groq API key configured in environment

Architecture Flow:
    Client → FD2 (Get JWT) → JWT Service
    Client → FD2 (Workflow Request) → LangGraph Module → APISIX → Groq
"""

import os
import sys
import httpx
import json
from pathlib import Path


# Configuration
CONTROL_TOWER_URL = os.getenv("CONTROL_TOWER_URL", "http://localhost:9000")
FRONT_DOOR_URL = os.getenv("FRONT_DOOR_URL", "http://localhost:8080")
PROJECT_ID = "langgraph-summarizer"
JWT_MODULE = "summarizer-auth"
WORKFLOW_MODULE = "doc-summarizer-workflow"


# Sample document to summarize
SAMPLE_DOCUMENT = """
Artificial Intelligence has revolutionized numerous industries over the past decade, 
transforming how businesses operate and how we interact with technology. Machine learning 
algorithms have become increasingly sophisticated, enabling computers to perform complex 
tasks that previously required human intelligence.

Deep learning, a subset of machine learning, has been particularly successful in areas 
such as image recognition, natural language processing, and speech synthesis. Neural 
networks with multiple layers can now learn hierarchical representations of data, 
achieving remarkable performance on challenging tasks.

Large language models (LLMs) represent a significant milestone in AI development. Models 
like GPT-4, Claude, and LLaMA have demonstrated impressive capabilities in understanding 
and generating human-like text. These models can perform diverse tasks including translation, 
summarization, code generation, and creative writing, often without task-specific training.

The rise of AI has also brought important ethical considerations. Issues such as algorithmic 
bias, data privacy, potential job displacement, and the responsible use of AI technologies 
require careful attention. Organizations worldwide are developing frameworks for responsible 
AI development, emphasizing transparency, fairness, accountability, and human oversight.

Looking forward, AI is expected to continue evolving rapidly. Emerging areas include 
multimodal AI systems that can process multiple types of data simultaneously, neuromorphic 
computing that mimics biological neural networks, and AI systems with improved reasoning 
and planning capabilities. The integration of AI into everyday applications will likely 
accelerate, making AI literacy an increasingly important skill for the workforce.

However, challenges remain. These include improving model interpretability, reducing 
computational costs, ensuring robustness against adversarial attacks, and addressing 
the environmental impact of training large models. Researchers and practitioners are 
actively working on solutions to these challenges while exploring new frontiers in 
artificial intelligence.
"""


class LangGraphSummarizerClient:
    """Client for interacting with the LangGraph Summarizer workflow"""
    
    def __init__(
        self,
        front_door_url: str = FRONT_DOOR_URL,
        control_tower_url: str = CONTROL_TOWER_URL
    ):
        self.front_door_url = front_door_url
        self.control_tower_url = control_tower_url
        self.jwt_token = None
        self.client = httpx.Client(timeout=120.0)
    
    def get_jwt_token(self) -> str:
        """Get JWT token from Front Door"""
        print(f"\n📝 Getting JWT token from {PROJECT_ID}/{JWT_MODULE}...")
        
        token_url = f"{self.front_door_url}/{PROJECT_ID}/{JWT_MODULE}/token"
        
        # Request token with default credentials
        response = self.client.post(
            token_url,
            json={
                "username": "admin",
                "password": "password"
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get JWT token: {response.text}")
        
        data = response.json()
        self.jwt_token = data.get("access_token")
        
        print(f"✅ JWT token obtained successfully")
        print(f"   Token (first 20 chars): {self.jwt_token[:20]}...")
        
        return self.jwt_token
    
    def summarize_document(self, document: str) -> dict:
        """Submit document for summarization through LangGraph workflow"""
        if not self.jwt_token:
            self.get_jwt_token()
        
        print(f"\n📄 Submitting document for summarization...")
        print(f"   Document length: {len(document)} characters")
        
        # Call the workflow endpoint through Front Door
        workflow_url = f"{self.front_door_url}/{PROJECT_ID}/workflow/{WORKFLOW_MODULE}"
        
        headers = {
            "Authorization": f"Bearer {self.jwt_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "document": document,
            "workflow_params": {}
        }
        
        print(f"\n🔄 Executing workflow...")
        response = self.client.post(
            workflow_url,
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"Workflow execution failed: {response.text}")
        
        result = response.json()
        print(f"✅ Workflow completed successfully")
        
        return result
    
    def display_results(self, result: dict):
        """Display workflow results"""
        print("\n" + "=" * 80)
        print("SUMMARIZATION RESULTS")
        print("=" * 80)
        
        final_summary = result.get("final_summary", "")
        metadata = result.get("metadata", {})
        
        print(f"\n📝 Final Summary:")
        print("-" * 80)
        print(final_summary)
        print("-" * 80)
        
        print(f"\n Metadata:")
        print(f"   Workflow: {metadata.get('workflow_name')}")
        print(f"   Chunks processed: {metadata.get('num_chunks', 0)}")
        print(f"   Started at: {metadata.get('started_at')}")
        print(f"   Completed at: {metadata.get('completed_at')}")
        
        print("\n" + "=" * 80)
    
    def close(self):
        """Close the HTTP client"""
        self.client.close()


def main():
    """Run the document summarization example"""
    print("=" * 80)
    print("🚀 LangGraph Document Summarizer Example")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Control Tower: {CONTROL_TOWER_URL}")
    print(f"  Front Door: {FRONT_DOOR_URL}")
    print(f"  Project ID: {PROJECT_ID}")
    print(f"  JWT Module: {JWT_MODULE}")
    print(f"  Workflow Module: {WORKFLOW_MODULE}")
    
    try:
        # Create client
        client = LangGraphSummarizerClient()
        
        # Get JWT token
        client.get_jwt_token()
        
        # Summarize document
        result = client.summarize_document(SAMPLE_DOCUMENT)
        
        # Display results
        client.display_results(result)
        
        # Cleanup
        client.close()
        
        print("\n✅ Example completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
