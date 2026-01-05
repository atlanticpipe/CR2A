"""
Development and debugging agents for CR2A application
These agents help with development, testing, and troubleshooting
"""
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from strands import Agent, tool
from strands.models import BedrockModel

@tool
def check_cr2a_dependencies() -> Dict[str, Any]:
    """Check if all CR2A dependencies are properly installed and configured.
    
    Returns:
        Status of dependencies and configuration
    """
    status = {
        "python_packages": {},
        "aws_config": {},
        "openai_config": {},
        "file_structure": {},
        "issues": [],
        "recommendations": []
    }
    
    # Check Python packages
    required_packages = [
        "flask", "fastapi", "boto3", "httpx", "pydantic", 
        "PyMuPDF", "pytesseract", "Pillow", "pathlib"
    ]
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            status["python_packages"][package] = "✅ Installed"
        except ImportError:
            status["python_packages"][package] = "❌ Missing"
            status["issues"].append(f"Missing package: {package}")
            status["recommendations"].append(f"Install {package}: pip install {package}")
    
    # Check AWS configuration
    try:
        import boto3
        session = boto3.Session()
        credentials = session.get_credentials()
        if credentials:
            status["aws_config"]["credentials"] = "✅ Found"
        else:
            status["aws_config"]["credentials"] = "❌ Missing"
            status["issues"].append("AWS credentials not configured")
            status["recommendations"].append("Run 'aws configure' or set AWS environment variables")
    except Exception as e:
        status["aws_config"]["error"] = str(e)
        status["issues"].append(f"AWS configuration error: {e}")
    
    # Check OpenAI configuration
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        status["openai_config"]["api_key"] = "✅ Found"
    else:
        status["openai_config"]["api_key"] = "❌ Missing"
        status["issues"].append("OPENAI_API_KEY not set")
        status["recommendations"].append("Set OPENAI_API_KEY environment variable")
    
    # Check file structure
    required_dirs = ["src", "schemas", "templates", "webapp", "worker"]
    for dir_name in required_dirs:
        if Path(dir_name).exists():
            status["file_structure"][dir_name] = "✅ Exists"
        else:
            status["file_structure"][dir_name] = "❌ Missing"
            status["issues"].append(f"Missing directory: {dir_name}")
    
    return status

@tool
def run_cr2a_tests() -> Dict[str, Any]:
    """Run CR2A application tests and return results.
    
    Returns:
        Test results and any failures
    """
    results = {
        "tests_run": [],
        "passed": [],
        "failed": [],
        "errors": [],
        "summary": {}
    }
    
    # Test core analyzer
    try:
        from src.core.analyzer import analyze_to_json
        results["tests_run"].append("analyzer_import")
        results["passed"].append("analyzer_import")
    except Exception as e:
        results["tests_run"].append("analyzer_import")
        results["failed"].append("analyzer_import")
        results["errors"].append(f"Analyzer import failed: {e}")
    
    # Test API main
    try:
        from src.api.main import app
        results["tests_run"].append("api_import")
        results["passed"].append("api_import")
    except Exception as e:
        results["tests_run"].append("api_import")
        results["failed"].append("api_import")
        results["errors"].append(f"API import failed: {e}")
    
    # Test OpenAI client
    try:
        from src.services.openai_client import refine_cr2a
        results["tests_run"].append("openai_client_import")
        results["passed"].append("openai_client_import")
    except Exception as e:
        results["tests_run"].append("openai_client_import")
        results["failed"].append("openai_client_import")
        results["errors"].append(f"OpenAI client import failed: {e}")
    
    # Summary
    results["summary"] = {
        "total": len(results["tests_run"]),
        "passed": len(results["passed"]),
        "failed": len(results["failed"]),
        "success_rate": f"{len(results['passed'])/len(results['tests_run'])*100:.1f}%" if results["tests_run"] else "0%"
    }
    
    return results

@tool
def analyze_cr2a_logs(log_file_path: str = "logs") -> Dict[str, Any]:
    """Analyze CR2A application logs for errors and patterns.
    
    Args:
        log_file_path: Path to log files or directory
    
    Returns:
        Log analysis with error patterns and recommendations
    """
    analysis = {
        "files_analyzed": [],
        "error_patterns": {},
        "warnings": [],
        "recommendations": [],
        "summary": {}
    }
    
    log_path = Path(log_file_path)
    
    if log_path.is_dir():
        log_files = list(log_path.glob("*.log")) + list(log_path.glob("*.csv"))
    elif log_path.is_file():
        log_files = [log_path]
    else:
        return {"error": f"Log path not found: {log_file_path}"}
    
    error_keywords = [
        "error", "exception", "failed", "timeout", "connection",
        "unauthorized", "forbidden", "not found", "invalid"
    ]
    
    for log_file in log_files:
        try:
            analysis["files_analyzed"].append(str(log_file))
            content = log_file.read_text(encoding="utf-8", errors="ignore")
            
            for keyword in error_keywords:
                count = content.lower().count(keyword)
                if count > 0:
                    if keyword not in analysis["error_patterns"]:
                        analysis["error_patterns"][keyword] = 0
                    analysis["error_patterns"][keyword] += count
            
            # Look for specific CR2A issues
            if "openai" in content.lower() and "error" in content.lower():
                analysis["warnings"].append("OpenAI API errors detected")
                analysis["recommendations"].append("Check OPENAI_API_KEY and rate limits")
            
            if "aws" in content.lower() and ("denied" in content.lower() or "unauthorized" in content.lower()):
                analysis["warnings"].append("AWS permission issues detected")
                analysis["recommendations"].append("Check AWS credentials and IAM permissions")
                
        except Exception as e:
            analysis["warnings"].append(f"Could not read {log_file}: {e}")
    
    # Summary
    total_errors = sum(analysis["error_patterns"].values())
    analysis["summary"] = {
        "files_processed": len(analysis["files_analyzed"]),
        "total_error_mentions": total_errors,
        "most_common_error": max(analysis["error_patterns"].items(), key=lambda x: x[1])[0] if analysis["error_patterns"] else None
    }
    
    return analysis

@tool
def generate_cr2a_config() -> Dict[str, Any]:
    """Generate configuration files and environment setup for CR2A.
    
    Returns:
        Generated configuration content and setup instructions
    """
    config = {
        "env_template": {},
        "docker_compose": {},
        "requirements_check": {},
        "setup_commands": []
    }
    
    # Environment template
    config["env_template"] = {
        "content": """# CR2A Environment Configuration
# Copy this to .env and fill in your values

# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.1
OPENAI_TIMEOUT_SECONDS=60

# AWS Configuration
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
AWS_S3_BUCKET=cr2a-contracts

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=1
FLASK_PORT=5000

# CORS Configuration
CORS_ALLOW_ORIGINS=http://localhost:8000,https://velmur.info

# Logging
CR2A_LOG_LEVEL=INFO

# Step Functions
STEP_FUNCTIONS_ARN=arn:aws:states:us-east-1:143895994429:stateMachine:cr2a-contract-analysis
""",
        "filename": ".env.template"
    }
    
    # Setup commands
    config["setup_commands"] = [
        "python -m venv .venv",
        ".venv\\Scripts\\activate",  # Windows
        "pip install -r requirements.txt",
        "copy .env.template .env",
        "# Edit .env with your API keys",
        "aws configure",  # Optional AWS setup
        "flask run",  # Start backend
        "cd webapp && python -m http.server 8000"  # Start frontend
    ]
    
    return config

def create_dev_agent() -> Agent:
    """Create a development and debugging agent for CR2A."""
    
    model = BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        region_name="us-east-1",
        temperature=0.2,
        max_tokens=2048,
    )
    
    agent = Agent(
        model=model,
        tools=[check_cr2a_dependencies, run_cr2a_tests, analyze_cr2a_logs, generate_cr2a_config],
        system_prompt="""You are a development and debugging assistant for the CR2A (Contract Risk & Compliance Analyzer) application.

Your expertise includes:
- Diagnosing configuration and dependency issues
- Analyzing application logs and error patterns
- Running tests and validating system health
- Generating configuration files and setup instructions
- Troubleshooting AWS, OpenAI, and Flask integration issues

When helping with CR2A development:
1. Always start by checking dependencies and configuration
2. Run tests to identify specific issues
3. Analyze logs for error patterns
4. Provide clear, actionable solutions
5. Generate configuration files when needed

Be thorough in your analysis and provide step-by-step solutions."""
    )
    
    return agent

if __name__ == "__main__":
    print("🛠️ Testing CR2A Development Agent...")
    
    agent = create_dev_agent()
    
    # Test the agent
    response = agent("Check the current status of the CR2A application and identify any issues that need to be resolved.")
    print(f"Agent Response: {response}")
    
    print("\n✅ CR2A Development Agent is ready!")
    print("This agent can help with:")
    print("- Dependency checking")
    print("- Running tests")
    print("- Log analysis")
    print("- Configuration generation")