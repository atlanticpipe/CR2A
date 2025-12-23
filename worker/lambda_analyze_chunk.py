"""
Lambda: Analyze Chunk (Worker Lambda)
- Processes a single chunk of the contract
- Runs in parallel via Step Functions Map state
"""
import json
import boto3
import io
import re
import logging
from datetime import datetime
from io import BytesIO
from PyPDF2 import PdfReader
from docx import Document
from botocore.exceptions import ClientError

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
jobs_table = dynamodb.Table('cr2a-jobs')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

CLAUSE_CLASSIFICATION = {
    "Definitions": ["definition", "means", "shall mean", "as used herein", "defined term"],
    "Scope of Work": ["scope", "services", "work", "deliverable", "sow", "perform"],
    "Payment": ["payment", "fee", "compensation", "invoice", "billing", "payable"],
    "Insurance": ["insurance", "insured", "coverage", "policy", "certificate", "coi"],
    "Indemnification": ["indemnify", "indemnification", "hold harmless", "defend"],
    "Termination": ["terminate", "termination", "for cause", "for convenience", "notice"],
    "Confidentiality": ["confidential", "non-disclosure", "nda", "proprietary"],
    "Intellectual Property": ["intellectual property", "ip", "ownership", "license"],
    "Governing Law": ["governing law", "jurisdiction", "venue", "choice of law"],
    "Dispute Resolution": ["dispute", "arbitration", "mediate", "mediation"],
    "Force Majeure": ["force majeure", "act of god", "beyond reasonable control"],
    "Warranties": ["warranty", "warranties", "representations", "guarantee"],
    "Limitation of Liability": ["limitation of liability", "liability cap", "consequential"],
    "Assignment": ["assign", "assignment", "transfer", "subcontract"],
    "Change Orders": ["change order", "amend", "amendment", "modification"],
    "Compliance": ["comply", "compliance", "laws", "regulations", "gdpr", "hipaa"],
    "Audit": ["audit", "inspection", "records", "books", "access"],
    "Schedule": ["schedule", "timeline", "delivery", "due date", "deadline"]
}


def lambda_handler(event, context):
    """
    Process a single chunk of the contract.
    
    Input (from Step Functions Map state iteration):
    {
        "chunk_index": 0,
        "start_page": 0,
        "end_page": 50,
        "page_count": 50,
        "job_id": "...",
        "s3_bucket": "...",
        "s3_key": "...",
        "file_type": "pdf"
    }
    
    Output (for Step Functions aggregation):
    {
        "chunk_index": 0,
        "status": "completed",
        "clauses_found": 12,
        "chunk_key": "results/job_id/chunks/chunk-0.json",
        "text_length": 45000
    }
    """
    try:
        chunk_index = event.get('chunk_index')
        job_id = event.get('job_id')
        s3_bucket = event.get('s3_bucket')
        s3_key = event.get('s3_key')
        file_type = event.get('file_type', 'pdf')
        
        logger.info(f"Processing chunk {chunk_index} of job {job_id}")
        
        # Download file from S3
        try:
            response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
            file_content = response['Body'].read()
        except ClientError as e:
            logger.error(f"Error downloading from S3: {e}")
            raise ValueError(f"Cannot access S3 file: {e}")
        
        # Extract text chunk based on file type
        if file_type == 'pdf':
            start_page = event.get('start_page')
            end_page = event.get('end_page')
            text = extract_pdf_pages(file_content, start_page, end_page)
        elif file_type in ['docx', 'doc']:
            start_pos = event.get('start_pos')
            end_pos = event.get('end_pos')
            text = extract_docx_range(file_content, start_pos, end_pos)
        else:
            start_pos = event.get('start_pos')
            end_pos = event.get('end_pos')
            text = extract_text_range(file_content, start_pos, end_pos)
        
        logger.info(f"Extracted {len(text)} characters for chunk {chunk_index}")
        
        # Analyze text chunk for clauses
        chunk_analysis = analyze_text_chunk(text, chunk_index)
        logger.info(f"Found {len(chunk_analysis['clauses_found'])} clause references")
        
        # Store chunk analysis in S3
        chunk_key = f"results/{job_id}/chunks/chunk-{chunk_index}.json"
        try:
            s3_client.put_object(
                Bucket='cr2a-output',
                Key=chunk_key,
                Body=json.dumps(chunk_analysis, indent=2),
                ContentType='application/json'
            )
            logger.info(f"Stored chunk analysis at s3://cr2a-output/{chunk_key}")
        except ClientError as e:
            logger.error(f"Error storing chunk result: {e}")
            raise
        
        # Return result for Step Functions aggregation
        return {
            'chunk_index': chunk_index,
            'status': 'completed',
            'clauses_found': len(chunk_analysis['clauses_found']),
            'chunk_key': chunk_key,
            'text_length': len(text),
            'analyzed_at': chunk_analysis['analyzed_at']
        }
        
    except Exception as e:
        logger.error(f"Error processing chunk {chunk_index}: {str(e)}", exc_info=True)
        
        # Store error for later review
        try:
            error_key = f"results/{job_id}/chunks/chunk-{chunk_index}-error.json"
            s3_client.put_object(
                Bucket='cr2a-output',
                Key=error_key,
                Body=json.dumps({'error': str(e), 'chunk_index': chunk_index, 'timestamp': datetime.now().isoformat()}),
                ContentType='application/json'
            )
        except Exception as err:
            logger.error(f"Error storing error record: {err}")
        
        # Let Step Functions handle the error
        raise


def extract_pdf_pages(file_content, start_page, end_page):
    """
    Extract specific pages from PDF and return text.
    """
    try:
        pdf_reader = PdfReader(BytesIO(file_content))
        text = ""
        
        for page_num in range(start_page, min(end_page, len(pdf_reader.pages))):
            try:
                page = pdf_reader.pages[page_num]
                text += f"\n--- Page {page_num + 1} ---\n"
                text += page.extract_text() or "[Unable to extract text from page]"
            except Exception as e:
                logger.warning(f"Error extracting page {page_num}: {e}")
                text += f"\n--- Page {page_num + 1} [Error: {str(e)}] ---\n"
        
        return text
    except Exception as e:
        logger.error(f"Error extracting PDF pages: {e}")
        raise


def extract_docx_range(file_content, start_pos, end_pos):
    """
    Extract text range from DOCX file.
    """
    try:
        doc = Document(BytesIO(file_content))
        full_text = "\n".join([p.text for p in doc.paragraphs])
        return full_text[start_pos:end_pos]
    except Exception as e:
        logger.error(f"Error extracting DOCX range: {e}")
        raise


def extract_text_range(file_content, start_pos, end_pos):
    """
    Extract text range from plain text file.
    """
    try:
        text = file_content.decode('utf-8') if isinstance(file_content, bytes) else file_content
        return text[start_pos:end_pos]
    except Exception as e:
        logger.error(f"Error extracting text range: {e}")
        raise


def analyze_text_chunk(text, chunk_index):
    """
    Classify clauses in this text chunk.
    
    Returns analysis dict with clause findings.
    """
    lines = text.split('\n')
    analysis = {
        'chunk_index': chunk_index,
        'text_length': len(text),
        'line_count': len(lines),
        'clauses_found': [],
        'clause_summary': {},
        'analyzed_at': datetime.now().isoformat()
    }
    
    # Initialize clause counts
    for clause_type in CLAUSE_CLASSIFICATION:
        analysis['clause_summary'][clause_type] = 0
    
    # Scan text for clause keywords
    for line_num, line in enumerate(lines):
        line_lower = line.lower()
        
        # Skip empty lines
        if not line_lower.strip():
            continue
        
        # Check each clause type
        for clause_type, keywords in CLAUSE_CLASSIFICATION.items():
            for keyword in keywords:
                # Use word boundary regex for more accurate matching
                if re.search(r'\b' + re.escape(keyword) + r'\b', line_lower):
                    analysis['clauses_found'].append({
                        'type': clause_type,
                        'keyword': keyword,
                        'line_number': line_num,
                        'excerpt': line[:200]
                    })
                    analysis['clause_summary'][clause_type] += 1
                    break  # Only count once per line
    
    logger.info(f"Chunk {chunk_index}: Found {len(analysis['clauses_found'])} clause references")
    return analysis
