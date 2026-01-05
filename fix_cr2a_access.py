"""
Fix CR2A Access Issues
Resolves local development and production access problems
"""
from strands import Agent, tool
from strands.models import BedrockModel
from pathlib import Path
import json

@tool
def create_local_env_config() -> dict:
    """Create local development environment configuration for CR2A frontend.
    
    Returns:
        Status of local environment setup
    """
    # Create local development env.js
    local_env_content = '''(() => {
  "use strict";
  // Local development configuration
  const injected = typeof window !== "undefined" && window._env ? window._env : {};
  window._env = {
    API_BASE_URL: injected.API_BASE_URL || "http://localhost:8000",
    API_AUTH_TOKEN: injected.API_AUTH_TOKEN || "Bearer local-dev-token",
  };
})();'''
    
    try:
        # Backup original env.js
        env_file = Path("webapp/env.js")
        backup_file = Path("webapp/env.js.backup")
        
        if env_file.exists() and not backup_file.exists():
            backup_file.write_text(env_file.read_text())
        
        # Write local development config
        env_file.write_text(local_env_content)
        
        return {
            "success": True,
            "message": "Local development environment configured",
            "changes": [
                "API_BASE_URL set to http://localhost:8000",
                "API_AUTH_TOKEN set for local development",
                "Original env.js backed up to env.js.backup"
            ],
            "next_steps": [
                "Start frontend server: cd webapp && python -m http.server 3000",
                "Access application at: http://localhost:3000"
            ]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@tool
def start_frontend_server() -> dict:
    """Start the CR2A frontend development server.
    
    Returns:
        Status of frontend server startup
    """
    import subprocess
    import os
    
    try:
        webapp_dir = Path("webapp")
        if not webapp_dir.exists():
            return {
                "success": False,
                "error": "webapp directory not found"
            }
        
        # Change to webapp directory and start server
        original_dir = os.getcwd()
        os.chdir("webapp")
        
        # Start HTTP server in background
        process = subprocess.Popen([
            "python", "-m", "http.server", "3000"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Return to original directory
        os.chdir(original_dir)
        
        return {
            "success": True,
            "message": "Frontend server started successfully",
            "url": "http://localhost:3000",
            "process_id": process.pid,
            "note": "Server running in background"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@tool
def check_server_status() -> dict:
    """Check the status of both backend and frontend servers.
    
    Returns:
        Status of all servers
    """
    import requests
    import subprocess
    
    status = {
        "backend": {"url": "http://localhost:8000", "status": "unknown"},
        "frontend": {"url": "http://localhost:3000", "status": "unknown"},
        "summary": {}
    }
    
    # Check backend
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            status["backend"]["status"] = "✅ Running"
            status["backend"]["response"] = response.json()
        else:
            status["backend"]["status"] = f"❌ Error {response.status_code}"
    except requests.exceptions.ConnectionError:
        status["backend"]["status"] = "❌ Not running"
    except Exception as e:
        status["backend"]["status"] = f"❌ Error: {e}"
    
    # Check frontend
    try:
        response = requests.get("http://localhost:3000", timeout=5)
        if response.status_code == 200:
            status["frontend"]["status"] = "✅ Running"
        else:
            status["frontend"]["status"] = f"❌ Error {response.status_code}"
    except requests.exceptions.ConnectionError:
        status["frontend"]["status"] = "❌ Not running"
    except Exception as e:
        status["frontend"]["status"] = f"❌ Error: {e}"
    
    # Check if processes are running
    try:
        result = subprocess.run(["netstat", "-an"], capture_output=True, text=True)
        if ":8000" in result.stdout:
            status["backend"]["port_status"] = "✅ Port 8000 in use"
        else:
            status["backend"]["port_status"] = "❌ Port 8000 not in use"
            
        if ":3000" in result.stdout:
            status["frontend"]["port_status"] = "✅ Port 3000 in use"
        else:
            status["frontend"]["port_status"] = "❌ Port 3000 not in use"
    except:
        pass
    
    # Summary
    backend_ok = "✅" in status["backend"]["status"]
    frontend_ok = "✅" in status["frontend"]["status"]
    
    status["summary"] = {
        "backend_running": backend_ok,
        "frontend_running": frontend_ok,
        "both_running": backend_ok and frontend_ok,
        "ready_for_development": backend_ok and frontend_ok
    }
    
    return status

@tool
def create_production_env_config() -> dict:
    """Create production environment configuration for deployment.
    
    Returns:
        Production configuration details
    """
    # Production env.js for AWS deployment
    prod_env_content = '''(() => {
  "use strict";
  // Production configuration for AWS deployment
  const injected = typeof window !== "undefined" && window._env ? window._env : {};
  window._env = {
    API_BASE_URL: injected.API_BASE_URL || "https://62k6wc3sqe.execute-api.us-east-1.amazonaws.com/prod",
    API_AUTH_TOKEN: injected.API_AUTH_TOKEN || "",
  };
})();'''
    
    return {
        "production_config": prod_env_content,
        "deployment_steps": [
            "Update API_BASE_URL to your actual API Gateway URL",
            "Set proper API_AUTH_TOKEN for production authentication",
            "Deploy to GitHub Pages or your hosting platform",
            "Ensure CORS is configured for your domain"
        ],
        "velmur_info_issue": {
            "likely_cause": "403 Forbidden suggests authentication or CORS issues",
            "solutions": [
                "Check if the API Gateway has proper CORS configuration",
                "Verify the Lambda authorizer is working correctly",
                "Ensure the domain is properly configured in DNS",
                "Check if there are any IP restrictions or WAF rules"
            ]
        }
    }

@tool
def troubleshoot_connection_issues() -> dict:
    """Troubleshoot common CR2A connection issues.
    
    Returns:
        Troubleshooting guide and solutions
    """
    return {
        "common_issues": {
            "ERR_CONNECTION_REFUSED": {
                "cause": "Server not running or wrong port",
                "solutions": [
                    "Ensure backend server is running on port 8000",
                    "Check if frontend is configured to use localhost:8000",
                    "Verify no firewall is blocking the connection",
                    "Try accessing http://localhost:8000/health directly"
                ]
            },
            "403_Forbidden": {
                "cause": "Authentication or authorization issues",
                "solutions": [
                    "Check API Gateway CORS configuration",
                    "Verify Lambda authorizer settings",
                    "Ensure proper authentication tokens",
                    "Check domain DNS configuration"
                ]
            },
            "CORS_Error": {
                "cause": "Cross-origin request blocked",
                "solutions": [
                    "Add localhost:3000 to CORS_ALLOW_ORIGINS",
                    "Update API Gateway CORS settings",
                    "Check preflight request handling"
                ]
            }
        },
        "quick_fixes": [
            "Restart both backend and frontend servers",
            "Clear browser cache and cookies",
            "Check browser developer console for errors",
            "Verify environment configuration files"
        ],
        "development_checklist": [
            "✅ Backend running on http://localhost:8000",
            "✅ Frontend running on http://localhost:3000", 
            "✅ env.js configured for local development",
            "✅ CORS allows localhost origins",
            "✅ No firewall blocking connections"
        ]
    }

def create_access_fix_agent() -> Agent:
    """Create agent to fix CR2A access issues."""
    
    model = BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        region_name="us-east-1",
        temperature=0.1,
        max_tokens=2048,
    )
    
    agent = Agent(
        model=model,
        tools=[
            create_local_env_config,
            start_frontend_server,
            check_server_status,
            create_production_env_config,
            troubleshoot_connection_issues
        ],
        system_prompt="""You are a CR2A access troubleshooting specialist.

Your expertise includes:
- Fixing local development server configuration
- Resolving frontend/backend connection issues
- Troubleshooting CORS and authentication problems
- Setting up proper environment configurations
- Diagnosing production deployment issues

When helping with access issues:
1. First check the status of all servers
2. Configure the frontend for local development
3. Start any missing servers
4. Verify connections are working
5. Provide troubleshooting guidance for any remaining issues

Always provide clear, step-by-step solutions."""
    )
    
    return agent

if __name__ == "__main__":
    print("🔧 CR2A Access Fix Agent")
    print("=" * 50)
    
    agent = create_access_fix_agent()
    
    response = agent("""
    I'm having access issues with CR2A:
    1. Getting ERR_CONNECTION_REFUSED when trying to access the IP address
    2. Getting 403 error when accessing velmur.info domain
    
    Please help me:
    1. Fix the local development setup so I can access CR2A locally
    2. Start the frontend server properly
    3. Troubleshoot the connection issues
    4. Explain what might be causing the 403 on the production domain
    """)
    
    print(f"Agent Response:\n{response}")
    
    print("\n" + "=" * 50)
    print("✅ Access Fix Agent Ready!")
    print("\nThis agent can help with:")
    print("- Local development configuration")
    print("- Frontend/backend server management")
    print("- Connection troubleshooting")
    print("- Production deployment issues")