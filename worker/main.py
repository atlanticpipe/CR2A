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

# Load configuration from S3 or embed them
CLAUSE_CLASSIFICATION = {
    "Definitions": ["definition", "means", "shall mean", "as used herein"],
    "Scope of Work": ["scope", "services", "work", "deliverable", "sow"],
    "Payment": ["payment", "fee", "compensation", "invoice", "billing"],
    "Insurance": ["insurance", "insured", "coverage", "policy", "certificate"],
    # ... include all from your clause_classification.json
}

VALIDATION_RULES = {
    "section_order": ["I", "II", "III", "IV", "V", "VI"],
    "require_all_sections": True,
    "closing_line_exact": "All applicable clauses for [Item #/Title] have been identified and analyzed."
}

def lambda_handler(event, context):
    """Worker Lambda for contract analysis"""
    job_id = event['job_id']
    s3_key = event['s3_key']
    
    try:
        # Update status to processing
        jobs_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression='SET #status = :status, started_at = :started',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'processing',
                ':started': datetime.now().isoformat()
            }
        )
        
        # Download contract from S3
        response = s3_client.get_object(Bucket='cr2a-upload', Key=s3_key)
        file_content = response['Body'].read()
        
        # Extract text based on file type
        file_type = s3_key.split('.')[-1].lower()
        if file_type == 'pdf':
            extracted_text = extract_from_pdf(file_content)
        elif file_type in ['docx', 'doc']:
            extracted_text = extract_from_docx(file_content)
        else:
            extracted_text = file_content.decode('utf-8')
        
        # Analyze contract
        analysis_result = analyze_contract(extracted_text, job_id)
        
        # Validate against rules
        validation_result = validate_analysis(analysis_result)
        
        # Prepare final result
        final_result = {
            'job_id': job_id,
            'analysis': analysis_result,
            'validation': validation_result,
            'completed_at': datetime.now().isoformat()
        }
        
        # Store in S3
        result_key = f"results/{job_id}/analysis.json"
        s3_client.put_object(
            Bucket='cr2a-output',
            Key=result_key,
            Body=json.dumps(final_result, indent=2),
            ContentType='application/json'
        )
        
        # Update DynamoDB with completion
        jobs_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression='SET #status = :status, completed_at = :completed, result_key = :result, progress = :progress',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'completed',
                ':completed': datetime.now().isoformat(),
                ':result': result_key,
                ':progress': 100
            }
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({'job_id': job_id, 'status': 'completed'})
        }
        
    except Exception as e:
        # Log error and update status
        jobs_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression='SET #status = :status, error = :error',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'failed',
                ':error': str(e)
            }
        )
        raise


def extract_from_pdf(file_content):
    """Extract text from PDF"""
    pdf_reader = PdfReader(io.BytesIO(file_content))
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text


def extract_from_docx(file_content):
    """Extract text from DOCX"""
    doc = Document(io.BytesIO(file_content))
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text


def analyze_contract(text, job_id):
    """
    Classify clauses and extract contract information
    """
    lines = text.split('\n')
    analysis = {
        'sections': {},
        'clauses_found': [],
        'extracted_data': {}
    }
    
    progress = 0
    total_lines = len(lines)
    
    current_section = None
    
    for idx, line in enumerate(lines):
        # Update progress periodically
        if idx % 100 == 0:
            progress = min(int((idx / total_lines) * 100), 95)
            jobs_table.update_item(
                Key={'job_id': job_id},
                UpdateExpression='SET progress = :progress',
                ExpressionAttributeValues={':progress': progress}
            )
        
        line_lower = line.lower()
        
        # Check section headers (I, II, III, etc.)
        for section in VALIDATION_RULES['section_order']:
            if re.match(f"^{section}\\.", line):
                current_section = section
                analysis['sections'][section] = {'header': line, 'content': []}
        
        # Classify clauses
        for clause_type, keywords in CLAUSE_CLASSIFICATION.items():
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', line_lower):
                    analysis['clauses_found'].append({
                        'type': clause_type,
                        'keyword': keyword,
                        'line': line,
                        'section': current_section
                    })
                    break
        
        # Add to current section
        if current_section and current_section in analysis['sections']:
            analysis['sections'][current_section]['content'].append(line)
    
    return analysis


def validate_analysis(analysis):
    """
    Validate analysis against rules
    """
    validation = {
        'passed': True,
        'issues': [],
        'warnings': []
    }
    
    # Check all required sections present
    sections_found = set(analysis['sections'].keys())
    required_sections = set(VALIDATION_RULES['section_order'])
    
    missing_sections = required_sections - sections_found
    if missing_sections:
        validation['passed'] = False
        validation['issues'].append(f"Missing sections: {missing_sections}")
    
    # Check clause extraction
    if len(analysis['clauses_found']) == 0:
        validation['warnings'].append("No clauses found - verify contract format")
    
    # Check closing line
    all_content = ' '.join([' '.join(v['content']) for v in analysis['sections'].values()])
    if VALIDATION_RULES['closing_line_exact'] not in all_content:
        validation['warnings'].append("Closing line not found in expected format")
    
    return validation