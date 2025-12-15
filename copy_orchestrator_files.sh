#!/bin/bash
# Script to copy orchestrator files from src/ to cr2a-lambda-build/
# This fixes the missing orchestrator.analyzer import error

echo "Copying orchestrator files to Lambda build directory..."

# Create orchestrator directory if it doesn't exist
mkdir -p cr2a-lambda-build/orchestrator

# Copy all Python files from src/orchestrator to cr2a-lambda-build/orchestrator
cp src/orchestrator/__init__.py cr2a-lambda-build/orchestrator/
cp src/orchestrator/analyzer.py cr2a-lambda-build/orchestrator/
cp src/orchestrator/cli.py cr2a-lambda-build/orchestrator/
cp src/orchestrator/config.py cr2a-lambda-build/orchestrator/
cp src/orchestrator/mime_utils.py cr2a-lambda-build/orchestrator/
cp src/orchestrator/models.py cr2a-lambda-build/orchestrator/
cp src/orchestrator/openai_client.py cr2a-lambda-build/orchestrator/
cp src/orchestrator/pdf_export.py cr2a-lambda-build/orchestrator/
cp src/orchestrator/policy_loader.py cr2a-lambda-build/orchestrator/
cp src/orchestrator/validator.py cr2a-lambda-build/orchestrator/

echo "✓ Copied all orchestrator Python files"
echo ""
echo "Files in cr2a-lambda-build/orchestrator/:"
ls -1 cr2a-lambda-build/orchestrator/
echo ""
echo "Now run: cd cr2a-lambda-build && zip -r ../lambda-deployment.zip ."
echo "Then upload lambda-deployment.zip to your Lambda function"
