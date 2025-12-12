#!/usr/bin/env python3
"""
Update your existing Lambda function with the current code.
"""

import boto3
import zipfile
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path

def create_deployment_package():
    """Create a deployment package for your existing Lambda function."""
    
    project_root = Path(__file__).parent
    src_dir = project_root / "src"
    
    print("Creating deployment package...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        package_dir = temp_path / "package"
        package_dir.mkdir()
        
        # Install dependencies
        print("Installing dependencies...")
        subprocess.run([
            sys.executable, "-m", "pip", "install",
            "-r", str(project_root / "requirements.txt"),
            "-t", str(package_dir),
            "--upgrade"
        ], check=True)
        
        # Copy source code
        print("Copying source code...")
        shutil.copytree(src_dir, package_dir / "src")
        
        # Copy other necessary directories
        for dir_name in ["schemas", "templates", "contract-analysis-policy-bundle", "orchestrator"]:
            src_path = project_root / dir_name
            if src_path.exists():
                if src_path.is_dir():
                    shutil.copytree(src_path, package_dir / dir_name)
                else:
                    shutil.copy2(src_path, package_dir / dir_name)
        
        # Create zip file
        zip_path = project_root / "lambda-deployment.zip"
        print(f"Creating zip file: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in package_dir.rglob('*'):
                if root.is_file():
                    arcname = root.relative_to(package_dir)
                    zipf.write(root, arcname)
        
        print(f"Package created: {zip_path}")
        print(f"Size: {zip_path.stat().st_size / 1024 / 1024:.1f} MB")
        
        return zip_path

def update_lambda_function(function_name, zip_path):
    """Update your existing Lambda function."""
    
    print(f"Updating Lambda function: {function_name}")
    
    try:
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        
        with open(zip_path, 'rb') as f:
            zip_content = f.read()
        
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        print("Lambda function updated successfully!")
        print(f"Version: {response['Version']}")
        print(f"Last Modified: {response['LastModified']}")
        
        return True
        
    except Exception as e:
        print(f"Failed to update Lambda function: {e}")
        return False

if __name__ == "__main__":
    # You can change this to your actual Lambda function name
    function_name = input("Enter your Lambda function name: ").strip()
    
    if not function_name:
        print("Function name is required")
        sys.exit(1)
    
    # Create deployment package
    zip_path = create_deployment_package()
    
    # Update Lambda function
    success = update_lambda_function(function_name, zip_path)
    
    if success:
        print("\n Your Lambda function has been updated!")
        print("You can now test your API endpoints.")
    else:
        print("\n Update failed. Check your AWS credentials and function name.")
    
    sys.exit(0 if success else 1)