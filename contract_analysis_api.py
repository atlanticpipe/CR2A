"""
Contract Analysis API Server

FastAPI-based REST API server for contract analysis using OpenAI's GPT models.
Provides endpoints for PDF upload, contract analysis, and structured JSON responses
that match the Clause Risk & Compliance Summary template format.

Features:
- PDF file upload and validation
- OpenAI API integration with structured JSON schema
- Response validation against company policies
- Comprehensive error handling
- API key authentication
- OpenAPI/Swagger documentation
"""

import os
import json
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import uvicorn

# Import existing contract analysis modules
import extract
import openai_client
import validator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Contract Analysis API",
    description="API for analyzing contract documents using AI to generate structured risk and compliance summaries",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
    openapi_url="/openapi.json"
)

# Add CORS middleware for web client support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key authentication
API_KEY = os.getenv("CONTRACT_API_KEY", "your-secret-api-key")
security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key for authentication"""
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return credentials.credentials

# Load schema and policy content
def load_schema_content() -> str:
    """Load the JSON schema content for API calls"""
    schema_path = Path(__file__).parent / 'output_schemas_v1.json'
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_data = json.load(f)
        return json.dumps(schema_data, indent=2)

def load_policy_content() -> str:
    """Load the policy rules content for API calls"""
    policy_path = Path(__file__).parent / 'validation_rules_v1.json'
    with open(policy_path, 'r', encoding='utf-8') as f:
        policy_data = json.load(f)
        return json.dumps(policy_data, indent=2)

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Contract Analysis API",
        "version": "1.0.0",
        "description": "AI-powered contract analysis for risk and compliance assessment",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "contract-analysis-api"
    }

@app.post("/analyze-contract")
async def analyze_contract(
    file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key)
):
    """
    Analyze a contract document (PDF or DOCX) and return structured risk analysis
    
    Args:
        file: PDF or DOCX file to analyze
        api_key: API key for authentication
        
    Returns:
        JSON response with analysis results matching the Clause Risk & Compliance Summary format
        
    Raises:
        HTTPException: If file is invalid, processing fails, or API key is unauthorized
    """
    # Validate file type
    if not file.filename.lower().endswith(('.pdf', '.docx')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF or DOCX document"
        )
    
    # Validate file size (max 50MB)
    file_size = 0
    content = await file.read()
    file_size = len(content)
    
    if file_size > 50 * 1024 * 1024:  # 50MB
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 50MB limit"
        )
    
    # Create temporary file
    temp_dir = None
    temp_file_path = None
    
    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, file.filename)
        
        # Write uploaded content to temporary file
        with open(temp_file_path, 'wb') as temp_file:
            temp_file.write(content)
        
        logger.info(f"Processing file: {file.filename} ({file_size} bytes)")
        
        # Step 1: Extract text from uploaded file
        try:
            contract_text = extract.extract_text(temp_file_path)
            if not contract_text:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Failed to extract text from document"
                )
        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Text extraction failed: {str(e)}"
            )
        
        logger.info(f"Extracted {len(contract_text)} characters from contract")
        
        # Step 2: Call OpenAI API with schema and rules
        try:
            schema_content = load_schema_content()
            rules_content = load_policy_content()
            analysis_result = openai_client.analyze_contract(contract_text, schema_content, rules_content)
        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"AI analysis failed: {str(e)}"
            )
        
        logger.info("Successfully received analysis from OpenAI API")
        
        # Step 3: Validate the response against schema and policy
        try:
            is_valid, validation_error = validator.validate_analysis_result(analysis_result)
            if not is_valid:
                logger.error(f"Validation failed: {validation_error}")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Response validation failed: {validation_error}"
                )
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Response validation error: {str(e)}"
            )
        
        logger.info("Successfully validated analysis results")
        
        # Return successful response
        return {
            "success": True,
            "message": "Contract analysis completed successfully",
            "data": analysis_result,
            "metadata": {
                "file_name": file.filename,
                "file_size": file_size,
                "processing_timestamp": datetime.utcnow().isoformat(),
                "schema_version": analysis_result.get("schema_version", "v1.0.0")
            }
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error during processing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
    finally:
        # Clean up temporary files
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {temp_file_path}: {str(e)}")
        
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to clean up temp directory {temp_dir}: {str(e)}")

@app.get("/schema")
async def get_schema(api_key: str = Depends(verify_api_key)):
    """Get the JSON schema used for contract analysis responses"""
    try:
        schema_content = load_schema_content()
        return {
            "success": True,
            "schema": json.loads(schema_content)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load schema: {str(e)}"
        )

@app.get("/validation-rules")
async def get_validation_rules(api_key: str = Depends(verify_api_key)):
    """Get the validation rules used for compliance checking"""
    try:
        rules_content = load_policy_content()
        return {
            "success": True,
            "rules": json.loads(rules_content)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load validation rules: {str(e)}"
        )

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with proper JSON response"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error",
            "status_code": 500
        }
    )

if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.getenv("PORT", 8000))
    
    # Print startup information
    print("🚀 Starting Contract Analysis API Server...")
    print(f"📋 API Documentation: http://localhost:{port}/docs")
    print(f"🔗 ReDoc: http://localhost:{port}/redoc")
    print(f"🏥 Health Check: http://localhost:{port}/health")
    print(f"🔑 API Key required: {API_KEY}")
    
    # Start server
    uvicorn.run(
        "contract_analysis_api:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
