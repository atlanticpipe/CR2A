from __future__ import annotations        # Enable postponed evaluation of annotations
import json                                # JSON serialization/deserialization
import os                                  # OS environment variables & paths
import tempfile                            # Temporary directory creation
import uuid                                # Generate unique identifiers
import logging                             # Application logging
import boto3                               # AWS SDK
from botocore.exceptions import ClientError
from datetime import datetime, timezone    # DateTime handling
from pathlib import Path                   # Path manipulation (cross-platform)
from typing import Any, Dict, List, Optional  # Type hints
from urllib.parse import urlparse          # Parse S3 URIs
from fastapi import FastAPI, File, HTTPException, Query, UploadFile  # FastAPI components
from fastapi.middleware.cors import CORSMiddleware  # CORS support
from fastapi.responses import RedirectResponse     # 307 redirect for downloads
from pydantic import BaseModel             # Data validation models

# Core business logic
from src.core.analyzer import analyze_to_json
from src.core.validator import validate_filled_template

# OpenAI service
from src.services.openai_client import OpenAIClientError, refine_cr2a

# PDF export service
from src.services.pdf_export import export_pdf_from_filled_json

# Storage/S3 utilities
from src.services.storage import (
    get_s3_client,
    load_upload_bucket,          # Get cr2a-upload bucket name
    load_output_bucket,          # Get cr2a-output bucket name
    build_output_key,            # Construct S3 key path
    build_s3_uri,                # Build s3://bucket/key format
    download_from_s3,            # Download file from S3
    upload_artifacts,            # Upload analysis results
    generate_download_url,       # Create presigned GET URL
    generate_upload_url,         # Create presigned PUT URL
    MAX_FILE_MB,                 # File size limit in MB
    MAX_FILE_BYTES,              # File size limit in bytes
    UPLOAD_EXPIRES_SECONDS,      # URL expiration time
    UPLOAD_PREFIX,               # S3 prefix for uploads
    OUTPUT_BUCKET,               # S3 output bucket name
    OUTPUT_PREFIX,               # S3 prefix for outputs
    OUTPUT_EXPIRES_SECONDS,      # Download URL expiration
    AWS_REGION,                  # AWS region (us-east-1)
)

# Schema management
from src.schemas.policy_loader import load_validation_rules, load_output_schema
from src.schemas.normalizer import normalize_to_schema
from src.schemas.template_spec import CR2A_TEMPLATE_SPEC

# Utility functions
from src.utils.mime_utils import infer_extension_from_content_type_or_magic, infer_mime_type

# Configure logging
LOG_LEVEL = os.getenv("CR2A_LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("src.api.main").setLevel(LOG_LEVEL)
logging.getLogger("src.services.openai_client").setLevel(LOG_LEVEL)
logger = logging.getLogger(__name__)    # Logger for this module

# AWS SDK Clients
try:
    s3_client = boto3.client('s3')
    lambda_client = boto3.client('lambda')
    dynamodb = boto3.resource('dynamodb')
    jobs_table = dynamodb.Table('cr2a-jobs')
    stepfunctions_client = boto3.client('stepfunctions')
except Exception as e:
    logger.error(f"Failed to initialize AWS clients: {e}")
    raise

STEP_FUNCTIONS_ARN = os.getenv('STEP_FUNCTIONS_ARN', 'arn:aws:states:us-east-1:143895994429:stateMachine:cr2a-contract-analysis')

RUN_OUTPUT_ROOT = Path(os.getenv("RUN_OUTPUT_ROOT", "/tmp/cr2a_runs")).expanduser()
REPO_ROOT = Path(__file__).resolve().parents   # Repository root path

app = FastAPI(title="CR2A API", version="0.1.1")
allow_origins = os.getenv("CORS_ALLOW_ORIGINS", "https://velmur.info")
if allow_origins == "*":
    logger.warning("CORS_ALLOW_ORIGINS set to wildcard (*) - this is insecure for production")
origins: List[str] = [o.strip() for o in allow_origins.split(",")] if allow_origins and allow_origins != "*" else ["https://velmur.info"]

# Add CORS middleware to app
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,              # Allow requests from velmur.info
    allow_credentials=True,              # Allow cookies/auth headers
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["content-type", "authorization", "x-amz-date", "x-api-key", "x-amz-security-token"],
)

class UploadUrlResponse(BaseModel):
    uploadUrl: str              # Presigned S3 PUT URL
    url: str                    # Alternative URL field
    upload_method: str = "PUT"  # HTTP method (PUT or POST)
    fields: Optional[dict] = None  # Form fields (for POST uploads)
    bucket: str                 # S3 bucket name
    key: str                    # S3 object key
    expires_in: int             # URL expiration seconds
    headers: Optional[Dict[str, str]] = None  # Required headers

class AnalysisRequestPayload(BaseModel):
    contract_id: str            # User-provided contract identifier
    contract_uri: Optional[str] = None  # S3 URI if bypassing presign
    key: Optional[str] = None   # S3 key from presigned upload
    llm_enabled: bool = True    # Enable LLM refinement

class AnalysisResponse(BaseModel):
    run_id: str                 # Unique run identifier
    status: str                 # "completed", "failed", etc.
    completed_at: datetime      # ISO 8601 timestamp
    manifest: dict              # Analysis metadata
    download_url: Optional[str] = None      # Presigned PDF URL
    filled_template_url: Optional[str] = None  # Presigned JSON URL
    error: Optional[dict] = None            # Error details if failed

class JobResponse(BaseModel):
    job_id: str                 # Step Functions execution ID
    status: str                 # "queued", "processing", "completed", "failed"
    message: str                # Human-readable status message
    status_url: str             # URL to GET /status/{job_id}

def _http_error(status: int, category: str, message: str) -> HTTPException:
    """Standardized error envelope for consistent API responses."""
    return HTTPException(status_code=status, detail={"category": category, "message": message})

def _parse_execution_progress(events: List[Dict]) -> Dict[str, Any]:
    """
    Extract progress information from Step Functions execution history.
    Maps Lambda function names to user-friendly step names and calculates progress.
    """
    
    STEP_MAPPING = {
        'cr2a-get-metadata': 'Extracting Metadata',
        'cr2a-calculate-chunks': 'Calculating Chunks',
        'cr2a-analyzer-worker': 'Analyzing Content',
        'cr2a-aggregate-results': 'Aggregating Results',
    }
    
    EXPECTED_STEPS = [
        'Extracting Metadata',
        'Calculating Chunks',
        'Analyzing Content',
        'Aggregating Results',
    ]

    completed_steps = set()      # Tracks which steps have completed
    current_step = None          # Current executing step
    step_status = None           # Status of current step (running/completed/failed)
    execution_started = False    # Whether execution has begun

    for event in events:
        event_type = event.get('type', '')
        
        if event_type == 'ExecutionStarted':
            execution_started = True

        elif event_type == 'TaskStateEntered':
            details = event.get('stateEnteredEventDetails', {})
            resource = details.get('resource', '')
            
            if resource:
                # Extract function name from ARN
                # arn:aws:lambda:region:account:function:name -> name
                func_name = resource.split(':')[-1] if ':' in resource else resource
                user_step = STEP_MAPPING.get(func_name, func_name)
                current_step = user_step
                step_status = 'running'

        elif event_type == 'TaskSucceeded':
            details = event.get('taskSucceededEventDetails', {})
            resource = details.get('resource', '')
            
            if resource:
                func_name = resource.split(':')[-1] if ':' in resource else resource
                user_step = STEP_MAPPING.get(func_name, func_name)
                completed_steps.add(user_step)
                current_step = user_step
                step_status = 'completed'

        elif event_type == 'TaskFailed':
            details = event.get('taskFailedEventDetails', {})
            resource = details.get('resource', '')
            
            if resource:
                func_name = resource.split(':')[-1] if ':' in resource else resource
                user_step = STEP_MAPPING.get(func_name, func_name)
                current_step = user_step
                step_status = 'failed'

        elif event_type == 'LambdaFunctionFailed' or event_type == 'LambdaFunctionScheduleFailed':
            step_status = 'failed'
            if 'stateEnteredEventDetails' in event:
                details = event.get('stateEnteredEventDetails', {})
                resource = details.get('resource', '')
                if resource:
                    func_name = resource.split(':')[-1] if ':' in resource else resource
                    current_step = STEP_MAPPING.get(func_name, func_name)

    # Calculate progress percentage
    steps_completed = len(completed_steps)
    total_steps = len(EXPECTED_STEPS)
    progress_percent = int((steps_completed / total_steps) * 100) if total_steps > 0 else 0

    # If execution started but no steps tracked yet
    if execution_started and not current_step:
        current_step = 'Starting analysis...'
        step_status = 'pending'
        progress_percent = 5

    logger.debug("Parsed execution progress", extra={"job_id": "unknown"})

    return {
        'current_step': current_step or 'Starting...',
        'steps_completed': steps_completed,
        'total_steps': total_steps,
        'progress_percent': progress_percent,
        'step_status': step_status or 'pending',
    }

@app.get("/health")
def health():
    """Health check endpoint."""
    return {"ok": True, "version": app.version}

@app.get("/upload-url", response_model=UploadUrlResponse)
def upload_url(
    filename: str = Query(..., description="Original filename"),
    contentType: str = Query("application/octet-stream", description="MIME type"),
    size: int = Query(..., description="File size in bytes"),
):
    """Generate a presigned S3 upload URL."""
    
    if size > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {size} bytes. Limit is {MAX_FILE_BYTES} bytes ({MAX_FILE_MB} MB).",
        )
    
    try:
        result = generate_upload_url(filename, contentType)
        return UploadUrlResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Presign failed: {e}")

@app.post("/upload-local")
async def upload_local(file: UploadFile = File(...), key: str = Query(...)):
    """Minimal local upload handler for when S3 is unavailable."""
    
    size = 0
    dest = RUN_OUTPUT_ROOT / "uploads" / key
    
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create upload directory: {e}")
        raise HTTPException(status_code=500, detail=f"Directory creation failed: {e}")
    
    try:
        with dest.open("wb") as fh:
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                size += len(chunk)
                
                if size > MAX_FILE_BYTES:
                    raise _http_error(400, "ValidationError", f"File exceeds {MAX_FILE_MB} MB")
                
                fh.write(chunk)
    except HTTPException:
        if dest.exists():
            dest.unlink()
        raise
    except Exception as e:
        logger.error(f"File write failed: {e}")
        if dest.exists():
            dest.unlink()
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
    finally:
        try:
            await file.close()
        except Exception as e:
            logger.warning(f"Failed to close upload file: {e}")
    
    return {"location": f"file://{dest}"}

@app.post("/analyze", response_model=JobResponse)
async def analyze_contract(payload: AnalysisRequestPayload):
    """
    Analyze a contract asynchronously using Step Functions.
    
    Args:
        payload: AnalysisRequestPayload with:
        - key: S3 key of uploaded contract (from /upload-url presign)
        - contract_id: Identifier for this contract
        - llm_enabled: Whether to apply LLM refinement (default: true)
    
    Returns:
        JobResponse with job_id and status tracking URL
    """
    
    try:
        # Validate that we have either a key or contract_uri
        if not payload.key and not payload.contract_uri:
            raise _http_error(
                400,
                "ValidationError",
                "Provide either 'key' (from presigned upload) or 'contract_uri' (S3 URI)"
            )

        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Determine S3 key: use provided key or extract from URI
        s3_key = payload.key
        if not s3_key and payload.contract_uri:
            parsed = urlparse(payload.contract_uri)
            s3_key = parsed.path.lstrip('/')
        
        # Get upload bucket name
        upload_bucket = load_upload_bucket()
        
        # Create job record in DynamoDB
        jobs_table.put_item(
            Item={
                'job_id': job_id,
                'status': 'queued',
                'progress': 0,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'contract_id': payload.contract_id,
                'llm_enabled': payload.llm_enabled,
                's3_bucket': upload_bucket,
                's3_key': s3_key,
            }
        )

        # Prepare Step Functions input
        execution_input = {
            'job_id': job_id,
            'contract_id': payload.contract_id,
            's3_bucket': upload_bucket,
            's3_key': s3_key,
            'llm_enabled': payload.llm_enabled,
        }
        
        logger.info(
            "Starting contract analysis",
            extra={
                "job_id": job_id,
                "contract_id": payload.contract_id,
                "s3_key": s3_key,
                "llm_enabled": payload.llm_enabled,
            }
        )
        
        # Start Step Functions execution
        response = stepfunctions_client.start_execution(
            stateMachineArn=STEP_FUNCTIONS_ARN,
            name=f"analysis-{job_id}",
            input=json.dumps(execution_input)
        )

        # Update job with execution ARN
        try:
            update_response = jobs_table.update_item(
                Key={'job_id': job_id},
                UpdateExpression='SET execution_arn = :arn, #status = :status, updated_at = :updated_at',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':arn': response['executionArn'],
                    ':status': 'processing',
                    ':updated_at': datetime.now(timezone.utc).isoformat()
                },
                ReturnValues='ALL_NEW'  # Verify write succeeded
            )
            logger.info(f"Updated job record", extra={
                "job_id": job_id,
                "execution_arn": update_response['Attributes'].get('execution_arn')
            })
        except ClientError as e:
            logger.error(f"DynamoDB update failed: {e.response['Error']['Code']}", extra={
                "job_id": job_id,
                "execution_arn": response['executionArn']
            })
            raise _http_error(500, "DatabaseError", str(e))

        return JobResponse(
            job_id=job_id,
            status='queued',
            message='Analysis started. Use /status/{job_id} to check progress.',
            status_url=f'/status/{job_id}'
        )

    except HTTPException:
        # Explicitly catch and re-raise FastAPI HTTPException
        raise
    except Exception as e:
        logger.exception("Failed to start analysis", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """
    Check the status of an analysis job with real-time Step Functions progress.
    
    Returns:
    - Current execution status (queued, processing, completed, failed)
    - Progress percentage
    - Current step name (from Step Functions)
    - Results URL when complete
    """
    
    try:
        # Get job record from DynamoDB
        response = jobs_table.get_item(Key={'job_id': job_id})
        if 'Item' not in response:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        job = response['Item']
        
        # Query Step Functions for live execution status
        if 'execution_arn' in job:
            try:
                execution = stepfunctions_client.describe_execution(
                    executionArn=job['execution_arn']
                )

                # Map Step Functions status to UI-friendly status
                sf_status = execution.get('status', 'UNKNOWN')
                status_map = {
                    'RUNNING': 'processing',
                    'SUCCEEDED': 'completed',
                    'FAILED': 'failed',
                    'TIMED_OUT': 'failed',
                    'ABORTED': 'failed',
                }
                
                job['status'] = status_map.get(sf_status, 'processing')
                job['step_functions_status'] = sf_status

                # Extract progress info from execution history
                history = stepfunctions_client.get_execution_history(
                    executionArn=job['execution_arn'],
                    maxItems=100
                )
                
                # Parse execution events to determine current step
                progress_info = _parse_execution_progress(history['events'])
                job.update(progress_info)

                # Log progress for debugging
                logger.info("Step Functions progress", extra={"job_id": job_id, "progress": progress_info})
                
                # If execution is complete, capture output
                if sf_status == 'SUCCEEDED':
                    try:
                        output = json.loads(execution.get('output', '{}'))
                        job['result_key'] = output.get('result_key')
                        job['filled_template_key'] = output.get('filled_template_key')
                        if execution.get('stopDate'):
                            job['completed_at'] = execution['stopDate'].isoformat()
                    except (json.JSONDecodeError, AttributeError):
                        pass
                
                # If execution failed, capture error
                elif sf_status == 'FAILED':
                    job['error'] = {
                        'cause': execution.get('cause', 'Unknown error'),
                        'error': execution.get('error', 'UNKNOWN'),
                    }
            
            except Exception as e:
                logger.warning(
                    "Failed to query Step Functions",
                    extra={"job_id": job_id, "execution_arn": job.get('execution_arn'), "error": str(e)}
                )
                # Don't fail the response; return what we have from DynamoDB
        # Generate presigned result URL if job is complete
        if job.get('status') == 'completed' and job.get('result_key'):
            try:
                result_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': load_output_bucket(),
                        'Key': job['result_key']
                    },
                    ExpiresIn=36000
                )
                
                job['result_url'] = result_url
                
                if job.get('filled_template_key'):
                    template_url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={
                            'Bucket': load_output_bucket(),
                            'Key': job['filled_template_key']
                        },
                        ExpiresIn=3600
                    )
                    job['filled_template_url'] = template_url
            
            except Exception as e:
                logger.warning(
                    "Failed to generate presigned URLs",
                    extra={"job_id": job_id, "error": str(e)}
                )
        
        return job

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get job status", extra={"job_id": job_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/runs/{run_id}/report")
def download_report(run_id: str):
    """Download analysis PDF report."""
    key = build_output_key(run_id, "cr2a_export.pdf")
    url = generate_download_url(key)
    return RedirectResponse(url=url, status_code=307)

@app.get("/runs/{run_id}/filled-template")
def download_json(run_id: str):
    """Download filled template JSON."""
    key = build_output_key(run_id, "filled_template.json")
    url = generate_download_url(key)
    return RedirectResponse(url=url, status_code=307)

from mangum import Mangum

handler = Mangum(app, lifespan="off", api_gateway_base_path="/prod")