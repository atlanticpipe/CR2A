"""
Lambda: Calculate Chunks
- Breaks contract into logical chunks for parallel processing
- Receives metadata output from GetMetadata step
"""
import json
import boto3
import io
import logging
from io import BytesIO
from PyPDF2 import PdfReader
from docx import Document
from botocore.exceptions import ClientError

s3_client = boto3.client('s3')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Create chunk definitions based on contract size.
    
    Input (from Step Functions GetMetadata output):
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
            "estimated_chunks": 1,
            "chunk_size": 10000
        }
    }
    
    Output (for Step Functions ProcessChunks Map state):
    {
        "job_id": "...",
        "contract_id": "...",
        "s3_bucket": "...",
        "s3_key": "...",
        "llm_enabled": true,
        "metadata": {...},
        "chunk_plan": {
            "total_chunks": 2,
            "chunks": [
                {"chunk_index": 0, "start_page": 0, "end_page": 50, ...},
                {"chunk_index": 1, "start_page": 50, "end_page": 100, ...}
            ]
        }
    }
    """
    try:
        # Extract from Step Functions input
        job_id = event.get('job_id')
        contract_id = event.get('contract_id')
        s3_bucket = event.get('s3_bucket')
        s3_key = event.get('s3_key')
        llm_enabled = event.get('llm_enabled')
        metadata = event.get('metadata', {})
        
        logger.info(f"Calculating chunks for job {job_id}")
        logger.info(f"Metadata: {metadata}")
        
        # Download file from S3
        try:
            response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
            file_content = response['Body'].read()
        except ClientError as e:
            logger.error(f"Error downloading from S3: {e}")
            raise ValueError(f"Cannot access S3 file: {e}")
        
        file_type = metadata.get('file_type', 'pdf')
        logger.info(f"File type: {file_type}")
        
        # Create chunks based on file type
        if file_type == 'pdf':
            chunks = create_pdf_chunks(file_content, metadata, job_id, s3_bucket, s3_key)
        elif file_type in ['docx', 'doc']:
            chunks = create_docx_chunks(file_content, metadata, job_id, s3_bucket, s3_key)
        else:
            chunks = create_text_chunks(file_content, metadata, job_id, s3_bucket, s3_key)
        
        logger.info(f"Created {len(chunks)} chunks")
        
        # Return in Step Functions format
        return {
            'job_id': job_id,
            'contract_id': contract_id,
            's3_bucket': s3_bucket,
            's3_key': s3_key,
            'llm_enabled': llm_enabled,
            'metadata': metadata,
            'chunk_plan': {
                'total_chunks': len(chunks),
                'chunks': chunks
            }
        }
        
    except Exception as e:
        logger.error(f"Error in calculate_chunks: {str(e)}", exc_info=True)
        raise


def create_pdf_chunks(file_content, metadata, job_id, s3_bucket, s3_key):
    """
    Create chunks based on PDF pages.
    
    Returns list of chunk specifications for Map state iteration.
    """
    try:
        pdf_reader = PdfReader(BytesIO(file_content))
        page_count = len(pdf_reader.pages)
        logger.info(f"PDF has {page_count} pages")
        
        # Estimate pages per chunk (max 50 pages per chunk for safety)
        pages_per_chunk = max(50, page_count // max(1, metadata.get('estimated_chunks', 1)))
        logger.info(f"Chunks will have {pages_per_chunk} pages each")
        
        chunks = []
        chunk_index = 0
        
        for start_page in range(0, page_count, pages_per_chunk):
            end_page = min(start_page + pages_per_chunk, page_count)
            
            chunk = {
                'chunk_index': chunk_index,
                'start_page': start_page,
                'end_page': end_page,
                'page_count': end_page - start_page,
                'job_id': job_id,
                's3_bucket': s3_bucket,
                's3_key': s3_key,
                'file_type': 'pdf'
            }
            chunks.append(chunk)
            logger.info(f"Chunk {chunk_index}: pages {start_page}-{end_page}")
            chunk_index += 1
        
        return chunks
        
    except Exception as e:
        logger.error(f"Error creating PDF chunks: {e}")
        raise


def create_docx_chunks(file_content, metadata, job_id, s3_bucket, s3_key):
    """
    Create chunks based on DOCX content.
    
    Returns list of chunk specifications for Map state iteration.
    """
    try:
        doc = Document(BytesIO(file_content))
        full_text = "\n".join([p.text for p in doc.paragraphs])
        logger.info(f"DOCX has {len(full_text)} characters")
        
        chunk_size = metadata.get('chunk_size', 10000)
        chunks = []
        chunk_index = 0
        
        for start_pos in range(0, len(full_text), chunk_size):
            end_pos = min(start_pos + chunk_size, len(full_text))
            
            chunk = {
                'chunk_index': chunk_index,
                'start_pos': start_pos,
                'end_pos': end_pos,
                'text_length': end_pos - start_pos,
                'job_id': job_id,
                's3_bucket': s3_bucket,
                's3_key': s3_key,
                'file_type': 'docx'
            }
            chunks.append(chunk)
            logger.info(f"Chunk {chunk_index}: chars {start_pos}-{end_pos}")
            chunk_index += 1
        
        return chunks
        
    except Exception as e:
        logger.error(f"Error creating DOCX chunks: {e}")
        raise


def create_text_chunks(file_content, metadata, job_id, s3_bucket, s3_key):
    """
    Create chunks based on text content.
    
    Returns list of chunk specifications for Map state iteration.
    """
    try:
        text = file_content.decode('utf-8') if isinstance(file_content, bytes) else file_content
        logger.info(f"Text file has {len(text)} characters")
        
        chunk_size = metadata.get('chunk_size', 10000)
        chunks = []
        chunk_index = 0
        
        for start_pos in range(0, len(text), chunk_size):
            end_pos = min(start_pos + chunk_size, len(text))
            
            chunk = {
                'chunk_index': chunk_index,
                'start_pos': start_pos,
                'end_pos': end_pos,
                'text_length': end_pos - start_pos,
                'job_id': job_id,
                's3_bucket': s3_bucket,
                's3_key': s3_key,
                'file_type': 'text'
            }
            chunks.append(chunk)
            logger.info(f"Chunk {chunk_index}: chars {start_pos}-{end_pos}")
            chunk_index += 1
        
        return chunks
        
    except Exception as e:
        logger.error(f"Error creating text chunks: {e}")
        raise
