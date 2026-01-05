"""
Complete CR2A Solution using Strands Agents
This provides a comprehensive solution for getting CR2A working with Strands integration
"""
import os
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import calculator, http_request

@tool
def install_missing_dependencies() -> Dict[str, Any]:
    """Install all missing dependencies for CR2A application.
    
    Returns:
        Status of dependency installation
    """
    dependencies = [
        "flask", "fastapi", "uvicorn", "mangum", "PyMuPDF", 
        "pytesseract", "Pillow", "boto3", "httpx==0.24.1", "pydantic",  # Pin httpx version
        "python-multipart", "jinja2", "requests", "openai>=1.0.0"      # Ensure compatible OpenAI version
    ]
    
    results = {
        "installed": [],
        "failed": [],
        "already_installed": [],
        "summary": {}
    }
    
    for dep in dependencies:
        try:
            result = subprocess.run([
                "pip", "install", dep
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                if "already satisfied" in result.stdout.lower():
                    results["already_installed"].append(dep)
                else:
                    results["installed"].append(dep)
            else:
                results["failed"].append({"package": dep, "error": result.stderr})
                
        except Exception as e:
            results["failed"].append({"package": dep, "error": str(e)})
    
    results["summary"] = {
        "total": len(dependencies),
        "installed": len(results["installed"]),
        "already_installed": len(results["already_installed"]),
        "failed": len(results["failed"])
    }
    
    return results

@tool
def setup_cr2a_environment() -> Dict[str, Any]:
    """Set up the complete CR2A environment with proper configuration.
    
    Returns:
        Status of environment setup
    """
    setup_steps = []
    
    # 1. Create .env file if it doesn't exist
    env_file = Path(".env")
    if not env_file.exists():
        env_content = """# CR2A Environment Configuration
OPENAI_API_KEY=your-openai-key-here
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
AWS_S3_BUCKET=cr2a-contracts
FLASK_ENV=development
FLASK_DEBUG=1
CORS_ALLOW_ORIGINS=http://localhost:3000,https://velmur.info
CR2A_LOG_LEVEL=INFO
STEP_FUNCTIONS_ARN=arn:aws:states:us-east-1:143895994429:stateMachine:cr2a-contract-analysis
DYNAMODB_TABLE=cr2a-jobs
"""
        env_file.write_text(env_content)
        setup_steps.append("✅ Created .env file")
    else:
        setup_steps.append("✅ .env file already exists")
    
    # 2. Check required directories
    required_dirs = ["src", "schemas", "templates", "webapp", "worker", "logs"]
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            setup_steps.append(f"✅ {dir_name}/ directory exists")
        else:
            setup_steps.append(f"⚠️ {dir_name}/ directory missing")
    
    # 3. Create logs directory if missing
    logs_dir = Path("logs")
    if not logs_dir.exists():
        logs_dir.mkdir()
        setup_steps.append("✅ Created logs/ directory")
    
    return {
        "setup_steps": setup_steps,
        "next_actions": [
            "Edit .env file with your actual API keys",
            "Ensure AWS credentials are configured",
            "Install any missing dependencies"
        ]
    }

@tool
def start_cr2a_development_server() -> Dict[str, Any]:
    """Start the CR2A development server with proper error handling.
    
    Returns:
        Status of server startup
    """
    try:
        # Check if main.py exists
        main_file = Path("src/api/main.py")
        if not main_file.exists():
            return {
                "success": False,
                "error": "src/api/main.py not found",
                "recommendation": "Ensure CR2A project structure is correct"
            }
        
        # Start the server
        cmd = ["uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"]
        
        # Use Popen for non-blocking start
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give it a moment to start
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            return {
                "success": True,
                "message": "CR2A backend server started successfully",
                "url": "http://127.0.0.1:8000",
                "health_check": "http://127.0.0.1:8000/health",
                "process_id": process.pid,
                "command": " ".join(cmd)
            }
        else:
            # Process died, get error output
            stdout, stderr = process.communicate()
            return {
                "success": False,
                "error": "Server failed to start",
                "stdout": stdout,
                "stderr": stderr,
                "recommendation": "Check the error messages above and install missing dependencies"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "recommendation": "Ensure uvicorn is installed: pip install uvicorn"
        }

@tool
def test_cr2a_health() -> Dict[str, Any]:
    """Test CR2A application health and API endpoints.
    
    Returns:
        Health check results
    """
    import requests
    
    tests = {
        "backend_health": {
            "url": "http://127.0.0.1:8000/health",
            "expected_status": 200
        },
        "upload_url_endpoint": {
            "url": "http://127.0.0.1:8000/upload-url?filename=test.pdf&size=1000",
            "expected_status": 200
        }
    }
    
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tests": {},
        "summary": {"passed": 0, "failed": 0, "total": len(tests)}
    }
    
    for test_name, test_config in tests.items():
        try:
            response = requests.get(test_config["url"], timeout=10)
            
            status = "✅ PASSED" if response.status_code == test_config["expected_status"] else "❌ FAILED"
            
            results["tests"][test_name] = {
                "status": status,
                "status_code": response.status_code,
                "expected": test_config["expected_status"],
                "response_time": f"{response.elapsed.total_seconds():.2f}s"
            }
            
            if response.status_code == test_config["expected_status"]:
                results["summary"]["passed"] += 1
            else:
                results["summary"]["failed"] += 1
                
        except requests.exceptions.ConnectionError:
            results["tests"][test_name] = {
                "status": "❌ FAILED",
                "error": "Connection refused - server not running"
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
def create_strands_cr2a_integration() -> Dict[str, Any]:
    """Create integration between Strands and CR2A for enhanced contract analysis.
    
    Returns:
        Status of integration creation
    """
    integration_code = '''"""
Strands-Enhanced CR2A Contract Analyzer
Replaces OpenAI client with Strands multi-provider agent
"""
from strands import Agent, tool
from strands.models import BedrockModel
from typing import Dict, Any
import json

@tool
def analyze_contract_clause(clause_text: str, clause_type: str) -> Dict[str, Any]:
    """Analyze a specific contract clause for risks and compliance.
    
    Args:
        clause_text: The contract clause text to analyze
        clause_type: Type of clause (liability, payment, indemnification, etc.)
    
    Returns:
        Analysis results with risks and recommendations
    """
    # Risk patterns by clause type
    risk_patterns = {
        "liability": ["unlimited", "consequential", "punitive", "indirect"],
        "payment": ["net 90", "net 60", "upon completion"],
        "indemnification": ["hold harmless", "defend", "indemnify"],
        "termination": ["immediate", "without cause", "no notice"]
    }
    
    analysis = {
        "clause_type": clause_type,
        "risks_found": [],
        "risk_level": "LOW",
        "recommendations": []
    }
    
    # Check for risk patterns
    clause_lower = clause_text.lower()
    patterns = risk_patterns.get(clause_type, [])
    
    for pattern in patterns:
        if pattern in clause_lower:
            analysis["risks_found"].append(pattern)
    
    # Determine risk level
    if len(analysis["risks_found"]) >= 2:
        analysis["risk_level"] = "HIGH"
    elif len(analysis["risks_found"]) == 1:
        analysis["risk_level"] = "MEDIUM"
    
    # Generate recommendations
    if analysis["risks_found"]:
        analysis["recommendations"].append(f"Review {clause_type} clause for risk mitigation")
        analysis["recommendations"].append("Consider adding liability caps or limitations")
    
    return analysis

def create_strands_cr2a_agent():
    """Create enhanced CR2A agent using Strands."""
    model = BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        region_name="us-east-1",
        temperature=0.1,
        max_tokens=4096,
    )
    
    return Agent(
        model=model,
        tools=[analyze_contract_clause],
        system_prompt="""You are an expert contract risk analyzer for the CR2A system.
        
        Analyze contracts for:
        - Risk allocation and liability issues
        - Payment terms and cash flow impact
        - Indemnification and insurance requirements
        - Compliance with company policies
        - Termination and dispute resolution clauses
        
        Provide specific, actionable recommendations for risk mitigation."""
    )

# Integration with existing CR2A
def enhance_cr2a_with_strands(contract_data: Dict[str, Any]) -> Dict[str, Any]:
    """Enhance CR2A analysis using Strands agent."""
    agent = create_strands_cr2a_agent()
    
    enhanced_data = contract_data.copy()
    
    # Process each section with Strands
    for section_key in ["SECTION_II", "SECTION_III", "SECTION_IV", "SECTION_V", "SECTION_VI"]:
        if section_key in contract_data:
            items = contract_data[section_key]
            for item in items:
                clauses = item.get("clauses", [])
                for clause in clauses:
                    clause_text = clause.get("clause_language", "")
                    if clause_text and clause_text != "Not present in contract.":
                        # Use Strands agent for enhanced analysis
                        response = agent(f"Analyze this contract clause: {clause_text}")
                        clause["strands_analysis"] = response
    
    return enhanced_data
'''
    
    try:
        integration_file = Path("strands_cr2a_integration.py")
        integration_file.write_text(integration_code)
        
        return {
            "success": True,
            "message": "Strands-CR2A integration created successfully",
            "file": str(integration_file.absolute()),
            "features": [
                "Multi-provider LLM support (Bedrock, OpenAI, Claude, etc.)",
                "Enhanced contract clause analysis",
                "Risk pattern detection",
                "Automated recommendations",
                "Integration with existing CR2A workflow"
            ]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def create_complete_cr2a_agent() -> Agent:
    """Create the complete CR2A management agent."""
    
    model = BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        region_name="us-east-1",
        temperature=0.1,
        max_tokens=4096,
    )
    
    agent = Agent(
        model=model,
        tools=[
            install_missing_dependencies,
            setup_cr2a_environment,
            start_cr2a_development_server,
            test_cr2a_health,
            create_strands_cr2a_integration,
            calculator,
            http_request
        ],
        system_prompt="""You are the complete CR2A (Contract Risk & Compliance Analyzer) management assistant.

Your mission is to get the CR2A application fully working and enhanced with Strands capabilities.

You can:
- Install missing dependencies and fix configuration issues
- Set up the development environment properly
- Start and manage the CR2A servers
- Test application health and API endpoints
- Create Strands integration for enhanced AI capabilities
- Troubleshoot and resolve issues

When helping with CR2A:
1. Always start with dependency and environment setup
2. Ensure all required components are installed
3. Start servers and verify they're working
4. Test API endpoints to confirm functionality
5. Integrate Strands for enhanced AI capabilities
6. Provide clear, actionable guidance

You understand both the existing CR2A architecture and how to enhance it with Strands agents for better contract analysis."""
    )
    
    return agent

if __name__ == "__main__":
    print("🚀 Complete CR2A Solution with Strands Integration")
    print("=" * 60)
    
    agent = create_complete_cr2a_agent()
    
    # Complete setup and testing
    response = agent("""
    Please help me get the CR2A application fully working with Strands integration:
    
    1. Install all missing dependencies
    2. Set up the environment properly
    3. Start the development server
    4. Test that everything is working
    5. Create Strands integration for enhanced contract analysis
    
    Walk me through each step and verify everything is working correctly.
    """)
    
    print(f"Agent Response:\n{response}")
    
    print("\n" + "=" * 60)
    print("✅ Complete CR2A Solution is ready!")
    print("\nThis solution provides:")
    print("- Automated dependency installation")
    print("- Environment setup and configuration")
    print("- Development server management")
    print("- Health testing and monitoring")
    print("- Strands integration for enhanced AI capabilities")
    print("- Multi-provider LLM support (Bedrock, OpenAI, Claude, etc.)")
    print("- Enhanced contract risk analysis")