#!/usr/bin/env python3
"""
Lambda layer management script for CR2A testing framework.
Handles creation, updating, and management of Lambda layers with dependencies.
"""

import os
import json
import zipfile
import tempfile
import shutil
import boto3
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError, NoCredentialsError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LambdaLayerManager:
    """Manages Lambda layers for CR2A testing framework."""
    
    def __init__(self, aws_region: str = "us-east-1"):
        """Initialize Lambda layer manager."""
        self.aws_region = aws_region
        self.lambda_client = None
        
        # Layer configurations
        self.layer_configs = {
            "cr2a-test-dependencies": {
                "description": "Core dependencies for CR2A testing framework",
                "requirements_files": ["requirements-core.txt", "requirements-testing.txt"],
                "compatible_runtimes": ["python3.12"],
                "compatible_architectures": ["x86_64"]
            },
            "cr2a-openai-layer": {
                "description": "OpenAI client dependencies for CR2A testing",
                "requirements_files": ["requirements-optional.txt"],
                "compatible_runtimes": ["python3.12"],
                "compatible_architectures": ["x86_64"]
            }
        }
    
    def _initialize_client(self):
        """Initialize AWS Lambda client."""
        try:
            self.lambda_client = boto3.client('lambda', region_name=self.aws_region)
            # Test credentials
            self.lambda_client.list_layers(MaxItems=1)
            logger.info(f"Lambda client initialized for region: {self.aws_region}")
        except NoCredentialsError:
            logger.error("AWS credentials not found. Please configure AWS credentials.")
            raise
        except ClientError as e:
            logger.error(f"Failed to initialize Lambda client: {e}")
            raise
    
    def install_packages_to_directory(self, requirements_files: List[str], target_dir: Path) -> bool:
        """Install packages from requirements files to target directory."""
        logger.info(f"Installing packages to {target_dir}")
        
        # Create python directory for Lambda layer structure
        python_dir = target_dir / "python"
        python_dir.mkdir(parents=True, exist_ok=True)
        
        success = True
        
        for req_file in requirements_files:
            req_path = Path(req_file)
            if not req_path.exists():
                logger.warning(f"Requirements file not found: {req_file}")
                continue
            
            logger.info(f"Installing from {req_file}")
            
            try:
                # Try pip install with specific options for Lambda layers
                result = subprocess.run([
                    "pip", "install", "-r", str(req_path),
                    "-t", str(python_dir),
                    "--no-deps",
                    "--platform", "linux_x86_64",
                    "--implementation", "cp",
                    "--python-version", "3.12",
                    "--only-binary=:all:",
                    "--upgrade"
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode != 0:
                    logger.warning(f"pip install with --no-deps failed: {result.stderr}")
                    
                    # Fallback: try without --no-deps and platform-specific options
                    result = subprocess.run([
                        "pip", "install", "-r", str(req_path),
                        "-t", str(python_dir),
                        "--upgrade"
                    ], capture_output=True, text=True, timeout=300)
                    
                    if result.returncode != 0:
                        logger.error(f"Failed to install from {req_file}: {result.stderr}")
                        success = False
                        continue
                
                logger.info(f"Successfully installed packages from {req_file}")
                
            except subprocess.TimeoutExpired:
                logger.error(f"Timeout installing packages from {req_file}")
                success = False
            except Exception as e:
                logger.error(f"Unexpected error installing from {req_file}: {e}")
                success = False
        
        return success
    
    def create_layer_zip(self, layer_name: str, layer_dir: Path) -> Optional[Path]:
        """Create zip file for Lambda layer."""
        logger.info(f"Creating zip file for layer: {layer_name}")
        
        zip_path = layer_dir.parent / f"{layer_name}.zip"
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                for root, dirs, files in os.walk(layer_dir):
                    # Skip __pycache__ directories and .pyc files
                    dirs[:] = [d for d in dirs if d != '__pycache__']
                    
                    for file in files:
                        if file.endswith('.pyc'):
                            continue
                        
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(layer_dir.parent)
                        zipf.write(file_path, arcname)
            
            zip_size = zip_path.stat().st_size
            logger.info(f"Created layer zip: {zip_path} ({zip_size / 1024 / 1024:.1f} MB)")
            
            # Check size limit (50MB for direct upload, 250MB for S3)
            if zip_size > 50 * 1024 * 1024:
                logger.warning(f"Layer zip is large ({zip_size / 1024 / 1024:.1f} MB). Consider using S3 upload.")
            
            return zip_path
            
        except Exception as e:
            logger.error(f"Failed to create layer zip: {e}")
            return None
    
    def publish_layer_version(self, layer_name: str, zip_path: Path) -> Optional[str]:
        """Publish new version of Lambda layer."""
        if not self.lambda_client:
            self._initialize_client()
        
        if layer_name not in self.layer_configs:
            logger.error(f"Unknown layer configuration: {layer_name}")
            return None
        
        config = self.layer_configs[layer_name]
        
        logger.info(f"Publishing layer version: {layer_name}")
        
        try:
            with open(zip_path, 'rb') as zip_file:
                zip_content = zip_file.read()
                
                # Check if we need to use S3 (for large files)
                if len(zip_content) > 50 * 1024 * 1024:
                    logger.error("Layer zip too large for direct upload. S3 upload not implemented yet.")
                    return None
                
                response = self.lambda_client.publish_layer_version(
                    LayerName=layer_name,
                    Description=config['description'],
                    Content={'ZipFile': zip_content},
                    CompatibleRuntimes=config['compatible_runtimes'],
                    CompatibleArchitectures=config['compatible_architectures']
                )
            
            layer_arn = response['LayerVersionArn']
            version = response['Version']
            
            logger.info(f"Published layer version {version}: {layer_arn}")
            return layer_arn
            
        except ClientError as e:
            logger.error(f"Failed to publish layer {layer_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error publishing layer {layer_name}: {e}")
            return None
    
    def create_or_update_layer(self, layer_name: str) -> Optional[str]:
        """Create or update a Lambda layer."""
        if layer_name not in self.layer_configs:
            logger.error(f"Unknown layer: {layer_name}")
            return None
        
        config = self.layer_configs[layer_name]
        
        logger.info(f"Creating/updating layer: {layer_name}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Install packages
            success = self.install_packages_to_directory(
                config['requirements_files'], 
                temp_path
            )
            
            if not success:
                logger.error(f"Failed to install packages for layer {layer_name}")
                return None
            
            # Create zip file
            zip_path = self.create_layer_zip(layer_name, temp_path)
            if not zip_path:
                return None
            
            # Publish layer
            layer_arn = self.publish_layer_version(layer_name, zip_path)
            return layer_arn
    
    def list_layer_versions(self, layer_name: str) -> List[Dict[str, Any]]:
        """List all versions of a Lambda layer."""
        if not self.lambda_client:
            self._initialize_client()
        
        try:
            response = self.lambda_client.list_layer_versions(LayerName=layer_name)
            return response.get('LayerVersions', [])
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.info(f"Layer {layer_name} not found")
                return []
            else:
                logger.error(f"Failed to list layer versions for {layer_name}: {e}")
                return []
    
    def delete_layer_version(self, layer_name: str, version_number: int) -> bool:
        """Delete a specific version of a Lambda layer."""
        if not self.lambda_client:
            self._initialize_client()
        
        try:
            self.lambda_client.delete_layer_version(
                LayerName=layer_name,
                VersionNumber=version_number
            )
            logger.info(f"Deleted layer version {layer_name}:{version_number}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete layer version {layer_name}:{version_number}: {e}")
            return False
    
    def cleanup_old_versions(self, layer_name: str, keep_versions: int = 3) -> int:
        """Clean up old versions of a layer, keeping only the most recent ones."""
        versions = self.list_layer_versions(layer_name)
        
        if len(versions) <= keep_versions:
            logger.info(f"Layer {layer_name} has {len(versions)} versions, no cleanup needed")
            return 0
        
        # Sort by version number (descending) and keep the most recent
        versions.sort(key=lambda x: x['Version'], reverse=True)
        versions_to_delete = versions[keep_versions:]
        
        deleted_count = 0
        for version_info in versions_to_delete:
            version_number = version_info['Version']
            if self.delete_layer_version(layer_name, version_number):
                deleted_count += 1
        
        logger.info(f"Cleaned up {deleted_count} old versions of layer {layer_name}")
        return deleted_count
    
    def get_layer_info(self, layer_name: str) -> Optional[Dict[str, Any]]:
        """Get information about the latest version of a layer."""
        versions = self.list_layer_versions(layer_name)
        
        if not versions:
            return None
        
        # Get the latest version (highest version number)
        latest_version = max(versions, key=lambda x: x['Version'])
        
        return {
            'layer_name': layer_name,
            'layer_arn': latest_version['LayerArn'],
            'layer_version_arn': latest_version['LayerVersionArn'],
            'version': latest_version['Version'],
            'description': latest_version.get('Description', ''),
            'created_date': latest_version['CreatedDate'],
            'compatible_runtimes': latest_version.get('CompatibleRuntimes', []),
            'compatible_architectures': latest_version.get('CompatibleArchitectures', [])
        }
    
    def create_all_layers(self) -> Dict[str, Optional[str]]:
        """Create or update all configured layers."""
        results = {}
        
        for layer_name in self.layer_configs.keys():
            logger.info(f"Processing layer: {layer_name}")
            layer_arn = self.create_or_update_layer(layer_name)
            results[layer_name] = layer_arn
        
        return results


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage CR2A Lambda layers")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--action", choices=["create", "list", "info", "cleanup", "delete"], 
                       default="create", help="Action to perform")
    parser.add_argument("--layer", help="Specific layer name")
    parser.add_argument("--version", type=int, help="Layer version number (for delete)")
    parser.add_argument("--keep", type=int, default=3, help="Number of versions to keep (for cleanup)")
    
    args = parser.parse_args()
    
    # Initialize layer manager
    manager = LambdaLayerManager(aws_region=args.region)
    
    if args.action == "create":
        if args.layer:
            # Create specific layer
            layer_arn = manager.create_or_update_layer(args.layer)
            if layer_arn:
                print(f"Successfully created/updated layer: {layer_arn}")
            else:
                print(f"Failed to create/update layer: {args.layer}")
        else:
            # Create all layers
            results = manager.create_all_layers()
            
            print("Layer Creation Results:")
            for layer_name, layer_arn in results.items():
                if layer_arn:
                    print(f"  {layer_name}: SUCCESS - {layer_arn}")
                else:
                    print(f"  {layer_name}: FAILED")
    
    elif args.action == "list":
        if args.layer:
            versions = manager.list_layer_versions(args.layer)
            print(f"Versions for layer {args.layer}:")
            for version in versions:
                print(f"  Version {version['Version']}: {version['LayerVersionArn']}")
        else:
            print("Available layers:")
            for layer_name in manager.layer_configs.keys():
                versions = manager.list_layer_versions(layer_name)
                print(f"  {layer_name}: {len(versions)} versions")
    
    elif args.action == "info":
        if not args.layer:
            print("--layer required for info action")
            return
        
        info = manager.get_layer_info(args.layer)
        if info:
            print(f"Layer Information for {args.layer}:")
            for key, value in info.items():
                print(f"  {key}: {value}")
        else:
            print(f"Layer {args.layer} not found")
    
    elif args.action == "cleanup":
        if args.layer:
            deleted = manager.cleanup_old_versions(args.layer, args.keep)
            print(f"Cleaned up {deleted} old versions of {args.layer}")
        else:
            total_deleted = 0
            for layer_name in manager.layer_configs.keys():
                deleted = manager.cleanup_old_versions(layer_name, args.keep)
                total_deleted += deleted
            print(f"Cleaned up {total_deleted} old layer versions total")
    
    elif args.action == "delete":
        if not args.layer or not args.version:
            print("--layer and --version required for delete action")
            return
        
        success = manager.delete_layer_version(args.layer, args.version)
        if success:
            print(f"Successfully deleted {args.layer} version {args.version}")
        else:
            print(f"Failed to delete {args.layer} version {args.version}")


if __name__ == "__main__":
    main()