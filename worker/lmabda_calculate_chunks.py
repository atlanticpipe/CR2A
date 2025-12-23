"""
Lambda: Calculate Chunks
- Breaks contract into logical chunks for parallel processing
"""
import json
import boto3
import io
from PyPDF2 import PdfReader
from docx import Document

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    """Create chunk definitions based on contract size"""
    metadata = event['metadata']
    job_id = metadata['job_id']
    s3_bucket = metadata['s3_bucket']
    s3_key = metadata['s3_key']
    
    try:
        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        file_content = response['Body'].read()
        
        file_type = metadata['file_type']
        
        if file_type == 'pdf':
            chunks = create_pdf_chunks(file_content, metadata)
        elif file_type in ['docx', 'doc']:
            chunks = create_text_chunks(file_content, metadata)
        else:
            text = file_content.decode('utf-8')
            chunks = create_text_chunks(text, metadata)
        
        return {
            'job_id': job_id,
            's3_bucket': s3_bucket,
            's3_key': s3_key,
            'total_chunks': len(chunks),
            'chunks': chunks
        }
        
    except Exception as e:
        print(f"Error in calculate_chunks: {str(e)}")
        raise


def create_pdf_chunks(file_content, metadata):
    """Create chunks based on PDF pages"""
    pdf_reader = PdfReader(io.BytesIO(file_content))
    page_count = len(pdf_reader.pages)
    
    pages_per_chunk = max(50, page_count // metadata['estimated_chunks'])
    
    chunks = []
    chunk_index = 0
    
    for start_page in range(0, page_count, pages_per_chunk):
        end_page = min(start_page + pages_per_chunk, page_count)
        
        chunks.append({
            'chunk_index': chunk_index,
            'start_page': start_page,
            'end_page': end_page,
            'page_count': end_page - start_page,
            'job_id': metadata['job_id'],
            's3_bucket': metadata['s3_bucket'],
            's3_key': metadata['s3_key'],
            'file_type': metadata['file_type']
        })
        
        chunk_index += 1
    
    return chunks


def create_text_chunks(content, metadata):
    """Create chunks based on text size"""
    if isinstance(content, bytes):
        text = content.decode('utf-8')
    else:
        from docx import Document
        doc = Document(io.BytesIO(content))
        text = "\n".join([p.text for p in doc.paragraphs])
    
    chunk_size = metadata['chunk_size']
    chunks = []
    chunk_index = 0
    
    for start_pos in range(0, len(text), chunk_size):
        end_pos = min(start_pos + chunk_size, len(text))
        
        chunks.append({
            'chunk_index': chunk_index,
            'start_pos': start_pos,
            'end_pos': end_pos,
            'text_length': end_pos - start_pos,
            'job_id': metadata['job_id'],
            's3_bucket': metadata['s3_bucket'],
            's3_key': metadata['s3_key'],
            'file_type': metadata['file_type']
        })
        
        chunk_index += 1
    
    return chunks