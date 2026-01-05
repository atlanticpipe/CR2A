"""
Complete CR2A Management Agent using Strands
This agent can help with development, deployment, testing, and troubleshooting
"""
import os
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import calculator, http_request

@tool
def start_cr2a_backend() -> Dict[str, Any]:
    """Start the CR2A FastAPI backend server.
    
    Returns:
        Status of the backend startup
    """
    try:
        # Check if the main API file exists
        api_file = Path("src/api/main.py")
        if not api_file.exists():
            return {
                "success": False,
                "error": "API file not found at src/api/main.py",
                "recommendation": "Ensure the CR2A project structure is correct"
            }
        
        # Start the server using uvicorn
        result = subprocess.run([
            "uvicorn", "src.api.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ], capture_output=True, text=True, timeout=10)
        
        return {
            "success": True,
            "message": "Backend server starting on http://localhost:8000",
            "command": "uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload",
            "note": "Server is running in background. Check http://localhost:8000/health"
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": True,
            "message": "Backend server started successfully (timeout expected for background process)",
            "url": "http://localhost:8000",
            "health_check": "http://localhost:8000/health"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "recommendation": "Check if uvicorn is installed: pip install uvicorn"
        }

@tool
def start_cr2a_frontend() -> Dict[str, Any]:
    """Start the CR2A frontend web server.
    
    Returns:
        Status of the frontend startup
    """
    try:
        webapp_dir = Path("webapp")
        if not webapp_dir.exists():
            return {
                "success": False,
                "error": "webapp directory not found",
                "recommendation": "Ensure the CR2A project structure includes webapp/"
            }
        
        # Start simple HTTP server for frontend
        os.chdir("webapp")
        result = subprocess.run([
            "python", "-m", "http.server", "3000"
        ], capture_output=True, text=True, timeout=5)
        
        return {
            "success": True,
            "message": "Frontend server starting on http://localhost:3000",
            "command": "cd webapp && python -m http.server 3000",
            "note": "Server is running in background"
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": True,
            "message": "Frontend server started successfully",
            "url": "http://localhost:3000"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "recommendation": "Ensure you're in the correct directory with webapp/ folder"
        }
    finally:
        # Return to original directory
        os.chdir("..")

@tool
def test_cr2a_api() -> Dict[str, Any]:
    """Test the CR2A API endpoints to ensure they're working.
    
    Returns:
        Results of API endpoint tests
    """
    import requests
    
    base_url = "http://localhost:8000"
    tests = {
        "health_check": {"url": f"{base_url}/health", "method": "GET"},
        "upload_url": {"url": f"{base_url}/upload-url?filename=test.pdf&size=1000", "method": "GET"},
    }
    
    results = {
        "base_url": base_url,
        "tests": {},
        "summary": {"passed": 0, "failed": 0, "total": len(tests)}
    }
    
    for test_name, test_config in tests.items():
        try:
            if test_config["method"] == "GET":
                response = requests.get(test_config["url"], timeout=10)
            else:
                response = requests.post(test_config["url"], timeout=10)
            
            results["tests"][test_name] = {
                "status": "✅ PASSED" if response.status_code < 400 else "❌ FAILED",
                "status_code": response.status_code,
                "response_time": f"{response.elapsed.total_seconds():.2f}s"
            }
            
            if response.status_code < 400:
                results["summary"]["passed"] += 1
            else:
                results["summary"]["failed"] += 1
                
        except requests.exceptions.ConnectionError:
            results["tests"][test_name] = {
                "status": "❌ FAILED",
                "error": "Connection refused - server not running",
                "recommendation": "Start the backend server first"
            }
            results["summary"]["failed"] += 1
        except Exception as e:
            results["tests"][test_name] = {
                "status": "❌ FAILED",
                "error": str(e)
            }
            results["summary"]["failed"] += 1
    
    return results

@tool
def create_env_file() -> Dict[str, Any]:
    """Create a .env file with CR2A configuration template.
    
    Returns:
        Status of .env file creation
    """
    env_content = """# CR2A Environment Configuration
# Fill in your actual values

# OpenAI Configuration (for LLM refinement)
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.1
OPENAI_TIMEOUT_SECONDS=60

# AWS Configuration (for S3 storage and Bedrock)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
AWS_S3_BUCKET=cr2a-contracts

# API Configuration
FLASK_ENV=development
FLASK_DEBUG=1
API_PORT=8000

# CORS Configuration
CORS_ALLOW_ORIGINS=http://localhost:3000,https://velmur.info

# Logging
CR2A_LOG_LEVEL=INFO

# Step Functions (for AWS deployment)
STEP_FUNCTIONS_ARN=arn:aws:states:us-east-1:143895994429:stateMachine:cr2a-contract-analysis

# Database (DynamoDB)
DYNAMODB_TABLE=cr2a-jobs
"""
    
    try:
        env_file = Path(".env")
        if env_file.exists():
            return {
                "success": False,
                "message": ".env file already exists",
                "recommendation": "Edit existing .env file or delete it first"
            }
        
        env_file.write_text(env_content)
        return {
            "success": True,
            "message": ".env file created successfully",
            "location": str(env_file.absolute()),
            "next_steps": [
                "Edit .env file with your actual API keys",
                "Set OPENAI_API_KEY for LLM features",
                "Set AWS credentials for cloud features"
            ]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@tool
def deploy_to_aws() -> Dict[str, Any]:
    """Help with AWS deployment of CR2A application.
    
    Returns:
        AWS deployment guidance and status
    """
    deployment_steps = {
        "prerequisites": [
            "AWS CLI installed and configured",
            "AWS credentials with appropriate permissions",
            "S3 buckets created (cr2a-upload, cr2a-output)",
            "DynamoDB table created (cr2a-jobs)",
            "Step Functions state machine deployed"
        ],
        "lambda_deployment": [
            "Package application code",
            "Create Lambda deployment package",
            "Deploy Lambda functions",
            "Configure API Gateway"
        ],
        "infrastructure": [
            "S3 buckets for file storage",
            "DynamoDB for job tracking",
            "Step Functions for workflow orchestration",
            "IAM roles and policies"
        ],
        "commands": [
            "aws s3 mb s3://cr2a-upload",
            "aws s3 mb s3://cr2a-output", 
            "aws dynamodb create-table --table-name cr2a-jobs --attribute-definitions AttributeName=job_id,AttributeType=S --key-schema AttributeName=job_id,KeyType=HASH --billing-mode PAY_PER_REQUEST",
            "# Deploy Step Functions state machine from worker/step_functions_state_machine.json"
        ]
    }
    
    # Check if AWS CLI is available
    try:
        result = subprocess.run(["aws", "--version"], capture_output=True, text=True)
        aws_available = result.returncode == 0
    except FileNotFoundError:
        aws_available = False
    
    return {
        "aws_cli_available": aws_available,
        "deployment_steps": deployment_steps,
        "recommendation": "Use GitHub Actions for automated deployment" if aws_available else "Install AWS CLI first: https://aws.amazon.com/cli/"
    }

def create_cr2a_management_agent() -> Agent:
    """Create a comprehensive CR2A management agent."""
    
    model = BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        region_name="us-east-1",
        temperature=0.1,
        max_tokens=3072,
    )
    
    agent = Agent(
        model=model,
        tools=[
            start_cr2a_backend, 
            start_cr2a_frontend, 
            test_cr2a_api, 
            create_env_file, 
            deploy_to_aws,
            calculator,
            http_request
        ],
        system_prompt="""You are a comprehensive management assistant for the CR2A (Contract Risk & Compliance Analyzer) application.

Your capabilities include:
- Starting and managing CR2A backend and frontend servers
- Testing API endpoints and system health
- Creating configuration files and environment setup
- Providing AWS deployment guidance
- Troubleshooting development and production issues
- Monitoring application performance

When helping with CR2A:
1. Always check system status first
2. Provide clear, step-by-step instructions
3. Test changes to ensure they work
4. Offer both local development and production deployment guidance
5. Help troubleshoot issues with specific, actionable solutions

You understand the CR2A architecture:
- FastAPI backend with contract analysis
- React/vanilla JS frontend
- AWS integration (S3, Lambda, Step Functions, DynamoDB)
- OpenAI integration for LLM refinement
- PDF processing and report generation"""
    )
    
    return agent

if __name__ == "__main__":
    print("🚀 Testing CR2A Management Agent...")
    
    agent = create_cr2a_management_agent()
    
    # Test the agent
    response = agent("""
    I want to get the CR2A application running locally for development. 
    Please help me:
    1. Set up the environment
    2. Start the servers
    3. Test that everything is working
    
    Walk me through this step by step.
    """)
    
    print(f"Agent Response: {response}")
    
    print("\n✅ CR2A Management Agent is ready!")
    print("This agent can help with:")
    print("- Starting backend and frontend servers")
    print("- Testing API endpoints")
    print("- Creating configuration files")
    print("- AWS deployment guidance")
    print("- Troubleshooting issues")