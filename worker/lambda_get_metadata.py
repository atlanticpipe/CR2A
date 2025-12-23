"""
Lambda: Get Contract Metadata
- Determines contract size, page count, and processing strategy
"""
import json
import boto3
import io
from PyPDF2 import PdfReader
from docx import Document

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
jobs_table = dynamodb.Table('cr2a-jobs')

def lambda_handler(event, context):
    """Analyze contract and determine metadata for chunking strategy"""
    job_id = event['job_id']
    s3_bucket = event['s3_bucket']
    s3_key = event['s3_key']
    
    try:
        # Download contract
        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        file_content = response['Body'].read()
        
        # Extract metadata based on file type
        file_type = s3_key.split('.')[-1].lower()
        
        if file_type == 'pdf':
            pdf_reader = PdfReader(io.BytesIO(file_content))
            page_count = len(pdf_reader.pages)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        elif file_type in ['docx', 'doc']:
            doc = Document(io.BytesIO(file_content))
            text = "\n".join([p.text for p in doc.paragraphs])
            page_count = max(1, len(text) // 2500)
        else:
            text = file_content.decode('utf-8')
            page_count = max(1, len(text) // 2500)
        
        text_length = len(text)
        file_size_mb = len(file_content) / (1024 * 1024)
        
        chunk_size = 50000
        estimated_chunks = max(1, (text_length // chunk_size) + 1)
        
        metadata = {
            'job_id': job_id,
            's3_bucket': s3_bucket,
            's3_key': s3_key,
            'file_type': file_type,
            'file_size_mb': round(file_size_mb, 2),
            'page_count': page_count,
            'text_length': text_length,
            'estimated_chunks': estimated_chunks,
            'chunk_size': chunk_size,
            'estimated_processing_time_minutes': estimated_chunks * 10
        }
        
        jobs_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression='SET metadata = :metadata',
            ExpressionAttributeValues={':metadata': metadata}
        )
        
        return metadata
        
    except Exception as e:
        jobs_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression='SET #status = :status, error = :error',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'failed',
                ':error': f"Metadata error: {str(e)}"
            }
        )
        raise