"""
Lambda: Analyze Chunk (Worker Lambda)
- Processes a single chunk of the contract
"""
import json
import boto3
import io
import re
from datetime import datetime
from PyPDF2 import PdfReader
from docx import Document

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
jobs_table = dynamodb.Table('cr2a-jobs')

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
    """Process a single chunk of the contract"""
    job_id = event['job_id']
    chunk_index = event['chunk_index']
    s3_bucket = event['s3_bucket']
    s3_key = event['s3_key']
    file_type = event['file_type']
    
    try:
        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        file_content = response['Body'].read()
        
        if file_type == 'pdf':
            start_page = event['start_page']
            end_page = event['end_page']
            text = extract_pdf_pages(file_content, start_page, end_page)
        else:
            start_pos = event['start_pos']
            end_pos = event['end_pos']
            text = extract_text_range(file_content, start_pos, end_pos, file_type)
        
        chunk_analysis = analyze_text_chunk(text, chunk_index)
        
        chunk_key = f"results/{job_id}/chunks/chunk-{chunk_index}.json"
        s3_client.put_object(
            Bucket='cr2a-output',
            Key=chunk_key,
            Body=json.dumps(chunk_analysis, indent=2),
            ContentType='application/json'
        )
        
        return {
            'job_id': job_id,
            'chunk_index': chunk_index,
            'chunk_key': chunk_key,
            'clauses_found': len(chunk_analysis['clauses_found']),
            'status': 'completed'
        }
        
    except Exception as e:
        print(f"Error processing chunk {chunk_index}: {str(e)}")
        
        error_key = f"results/{job_id}/chunks/chunk-{chunk_index}-error.json"
        s3_client.put_object(
            Bucket='cr2a-output',
            Key=error_key,
            Body=json.dumps({'error': str(e), 'chunk_index': chunk_index}),
            ContentType='application/json'
        )
        
        raise


def extract_pdf_pages(file_content, start_page, end_page):
    """Extract specific pages from PDF"""
    pdf_reader = PdfReader(io.BytesIO(file_content))
    text = ""
    
    for page_num in range(start_page, min(end_page, len(pdf_reader.pages))):
        page = pdf_reader.pages[page_num]
        text += f"\n--- Page {page_num + 1} ---\n"
        text += page.extract_text()
    
    return text


def extract_text_range(file_content, start_pos, end_pos, file_type):
    """Extract text range from file"""
    if file_type in ['docx', 'doc']:
        doc = Document(io.BytesIO(file_content))
        full_text = "\n".join([p.text for p in doc.paragraphs])
        return full_text[start_pos:end_pos]
    else:
        text = file_content.decode('utf-8')
        return text[start_pos:end_pos]


def analyze_text_chunk(text, chunk_index):
    """Classify clauses in this chunk"""
    lines = text.split('\n')
    analysis = {
        'chunk_index': chunk_index,
        'text_length': len(text),
        'line_count': len(lines),
        'clauses_found': [],
        'clause_summary': {},
        'analyzed_at': datetime.now().isoformat()
    }
    
    for clause_type in CLAUSE_CLASSIFICATION:
        analysis['clause_summary'][clause_type] = 0
    
    for line_num, line in enumerate(lines):
        line_lower = line.lower()
        
        if not line_lower.strip():
            continue
        
        for clause_type, keywords in CLAUSE_CLASSIFICATION.items():
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', line_lower):
                    analysis['clauses_found'].append({
                        'type': clause_type,
                        'keyword': keyword,
                        'line_number': line_num,
                        'excerpt': line[:200]
                    })
                    analysis['clause_summary'][clause_type] += 1
                    break
    
    return analysis