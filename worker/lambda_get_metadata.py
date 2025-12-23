"""
Lambda: Get Metadata
- Extract metadata from contract (page count, size, etc)
- Input from Step Functions state machine
"""
import json
import boto3
import logging
from io import BytesIO
from PyPDF2 import PdfReader
from botocore.exceptions import ClientError

s3 = boto3.client('s3')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Extract metadata from contract.
    
    Step Functions Input:
    {
        "job_id": "...",
        "contract_id": "...",
        "s3_bucket": "...",
        "s3_key": "...",
        "llm_enabled": true
    }
    
    Step Functions Output:
    {
        "job_id": "...",
        "contract_id": "...",
        "s3_bucket": "...",
        "s3_key": "...",
        "llm_enabled": true,
        "metadata": {
            "file_type": "pdf",
            "pages": 45,
            "size": 1234567,
            "file_size_mb": 1.18,
            "estimated_chunks": 1
        }
    }
    """
    try:
        # Extract input from Step Functions
        job_id = event.get('job_id')
        contract_id = event.get('contract_id')
        s3_bucket = event.get('s3_bucket')
        s3_key = event.get('s3_key')
        llm_enabled = event.get('llm_enabled', True)
        
        logger.info(f"Processing job {job_id} for contract {contract_id}")
        logger.info(f"Downloading from s3://{s3_bucket}/{s3_key}")
        
        # Get file from S3
        try:
            response = s3.get_object(Bucket=s3_bucket, Key=s3_key)
            file_content = response['Body'].read()
        except ClientError as e:
            logger.error(f"Error downloading from S3: {e}")
            raise ValueError(f"Cannot access S3 file: {e}")
        
        file_size = len(file_content)
        file_size_mb = round(file_size / 1024 / 1024, 2)
        
        logger.info(f"File size: {file_size_mb} MB")
        
        # Determine file type and extract metadata
        file_type = determine_file_type(s3_key, file_content)
        logger.info(f"Detected file type: {file_type}")
        
        if file_type == 'pdf':
            pages = extract_pdf_metadata(file_content)
        else:
            pages = 1  # For non-PDF files, treat as single page
        
        logger.info(f"File has {pages} pages")
        
        # Estimate number of chunks (max 50 pages per chunk)
        estimated_chunks = max(1, pages // 50)
        
        # Prepare metadata output
        metadata = {
            'file_type': file_type,
            'pages': pages,
            'size': file_size,
            'file_size_mb': file_size_mb,
            'estimated_chunks': estimated_chunks,
            'chunk_size': 10000  # Characters per chunk for text files
        }
        
        logger.info(f"Metadata extracted: {metadata}")
        
        # Return in Step Functions format (pass through all input fields + metadata)
        return {
            'job_id': job_id,
            'contract_id': contract_id,
            's3_bucket': s3_bucket,
            's3_key': s3_key,
            'llm_enabled': llm_enabled,
            'metadata': metadata
        }
        
    except Exception as e:
        logger.error(f"Error in get_metadata: {str(e)}", exc_info=True)
        # Step Functions will catch this exception and fail the execution
        raise


def determine_file_type(s3_key, file_content):
    """
    Determine file type from key extension and magic bytes.
    
    Returns: 'pdf', 'docx', 'doc', or 'txt'
    """
    key_lower = s3_key.lower()
    
    # Check magic bytes
    if file_content.startswith(b'%PDF'):
        return 'pdf'
    elif file_content.startswith(b'PK\x03\x04'):
        return 'docx'
    elif file_content.startswith(b'\xd0\xcf\x11\xe0'):
        return 'doc'
    
    # Fall back to extension
    if key_lower.endswith('.pdf'):
        return 'pdf'
    elif key_lower.endswith('.docx'):
        return 'docx'
    elif key_lower.endswith('.doc'):
        return 'doc'
    
    # Default to text
    return 'txt'


def extract_pdf_metadata(file_content):
    """
    Extract page count from PDF.
    
    Returns: number of pages
    """
    try:
        pdf_file = BytesIO(file_content)
        pdf_reader = PdfReader(pdf_file)
        page_count = len(pdf_reader.pages)
        logger.info(f"PDF page count: {page_count}")
        return page_count
    except Exception as e:
        logger.warning(f"Error reading PDF metadata: {e}. Using default 1 page.")
        return 1
