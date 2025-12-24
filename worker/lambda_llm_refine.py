"""
Lambda: LLM Refinement Stage
- Wraps the existing LLMAnalyzer from src/core/llm_analyzer.py
- Calls GPT-4o-mini for verification and enhancement
- Returns risk scores, recommendations, compliance checks
"""
import json
import boto3
import logging
import os
from datetime import datetime
from botocore.exceptions import ClientError
from dataclasses import asdict
import sys

# Add Lambda layer path
sys.path.insert(0, '/var/task')

from src.core.llm_analyzer import LLMAnalyzer

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
jobs_table = dynamodb.Table('cr2a-jobs')

# Environment
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')


def update_job_progress(job_id, step_name, percent=None):
    """Update DynamoDB with current progress"""
    try:
        update_expr = 'SET current_step = :step, updated_at = :time'
        values = {
            ':step': step_name,
            ':time': datetime.now().isoformat()
        }
        
        if percent is not None:
            update_expr += ', progress = :progress'
            values[':progress'] = percent
        
        jobs_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=values
        )
        logger.info(f"Updated job {job_id}: {step_name}")
    except Exception as e:
        logger.error(f"Failed to update job progress: {e}")


def lambda_handler(event, context):
    """
    Lambda handler for LLM refinement using LLMAnalyzer.
    
    Input from Step Functions:
    {
        "job_id": "uuid",
        "contract_id": "contract-123",
        "s3_bucket": "cr2a-output",
        "contract_text_key": "uploads/job_id/contract.txt",
        "llm_enabled": true
    }
    """
    
    job_id = event.get('job_id')
    contract_id = event.get('contract_id', f"contract-{job_id}")
    analysis_id = event.get('analysis_id', f"analysis-{job_id}")
    s3_bucket = event.get('s3_bucket', 'cr2a-output')
    contract_text_key = event.get('contract_text_key')
    contract_text = event.get('contract_text', '')
    llm_enabled = event.get('llm_enabled', True)
    
    logger.info(f"Starting LLM refinement for job {job_id}")
    
    try:
        update_job_progress(job_id, "LLM Refinement: Initializing", 5)
        
        if not llm_enabled:
            logger.info(f"LLM disabled for job {job_id}, skipping refinement")
            update_job_progress(job_id, "LLM Refinement: Skipped (disabled)", 100)
            
            return {
                'job_id': job_id,
                'llm_status': 'skipped',
                'message': 'LLM refinement disabled'
            }
        
        # Initialize LLMAnalyzer
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        analyzer = LLMAnalyzer(api_key=OPENAI_API_KEY, model=OPENAI_MODEL)
        logger.info(f"Initialized LLMAnalyzer with model {OPENAI_MODEL}")
        
        # Get contract text from S3 if needed
        if contract_text_key and not contract_text:
            logger.info(f"Downloading contract text from S3: {contract_text_key}")
            update_job_progress(job_id, "LLM Refinement: Downloading contract", 10)
            try:
                response = s3_client.get_object(Bucket=s3_bucket, Key=contract_text_key)
                contract_text = response['Body'].read().decode('utf-8')
            except ClientError as e:
                logger.error(f"Failed to download contract: {e}")
                raise ValueError(f"Cannot access contract from S3: {e}")
        
        if not contract_text or len(contract_text.strip()) < 100:
            raise ValueError("Contract text is empty or too short")
        
        logger.info(f"Starting LLMAnalyzer with {len(contract_text)} characters")
        update_job_progress(job_id, "LLM Refinement: Calling OpenAI GPT-4o-mini", 30)
        
        try:
            # Call the LLM analyzer (synchronous)
            analysis_result = analyzer.analyze(
                contract_text=contract_text,
                contract_id=contract_id,
                analysis_id=analysis_id
            )
            
            logger.info(f"LLM analysis completed")
            logger.info(f"Risk: {analysis_result.risk_level}, Score: {analysis_result.overall_score:.1f}")
            logger.info(f"Findings: {len(analysis_result.findings)}, Recommendations: {len(analysis_result.recommendations)}")
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {str(e)}", exc_info=True)
            update_job_progress(job_id, f"LLM Refinement: Failed - {type(e).__name__}", 100)
            
            try:
                jobs_table.update_item(
                    Key={'job_id': job_id},
                    UpdateExpression='SET llm_error = :error, llm_status = :status',
                    ExpressionAttributeValues={
                        ':error': f"{type(e).__name__}: {str(e)[:200]}",
                        ':status': 'failed'
                    }
                )
            except Exception as err:
                logger.error(f"Failed to update error: {err}")
            
            # Re-raise so Step Functions can retry
            raise
        
        # Serialize to JSON
        logger.info("Serializing analysis result")
        update_job_progress(job_id, "LLM Refinement: Storing results", 70)
        
        result_dict = {
            'analysis_id': analysis_result.analysis_id,
            'contract_id': analysis_result.contract_id,
            'risk_level': analysis_result.risk_level,
            'overall_score': analysis_result.overall_score,
            'executive_summary': analysis_result.executive_summary,
            'findings': [asdict(f) for f in analysis_result.findings],
            'recommendations': analysis_result.recommendations,
            'compliance_issues': analysis_result.compliance_issues,
            'metadata': analysis_result.metadata,
            'refined_at': datetime.now().isoformat(),
            'llm_model': OPENAI_MODEL
        }
        
        # Store to S3
        refined_key = f"results/{job_id}/llm_refined_analysis.json"
        try:
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=refined_key,
                Body=json.dumps(result_dict, indent=2),
                ContentType='application/json'
            )
            logger.info(f"Stored refined analysis at s3://{s3_bucket}/{refined_key}")
        except ClientError as e:
            logger.error(f"Failed to store to S3: {e}")
            raise
        
        # Update job completion
        update_job_progress(job_id, "LLM Refinement: Complete", 100)
        
        try:
            jobs_table.update_item(
                Key={'job_id': job_id},
                UpdateExpression='SET refined_key = :key, llm_status = :status, llm_score = :score, completed_at = :time',
                ExpressionAttributeValues={
                    ':key': refined_key,
                    ':status': 'completed',
                    ':score': analysis_result.overall_score,
                    ':time': datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Failed to update completion: {e}")
        
        logger.info(f"Job {job_id} completed successfully")
        
        return {
            'job_id': job_id,
            'refined_key': refined_key,
            'llm_status': 'completed',
            'risk_level': analysis_result.risk_level,
            'overall_score': analysis_result.overall_score,
            'findings_count': len(analysis_result.findings),
            'recommendations_count': len(analysis_result.recommendations)
        }
    
    except Exception as e:
        logger.exception(f"Unhandled error: {str(e)}")
        
        try:
            jobs_table.update_item(
                Key={'job_id': job_id},
                UpdateExpression='SET #status = :status, error = :error',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'failed',
                    ':error': f"LLM Lambda: {str(e)[:200]}"
                }
            )
        except Exception as err:
            logger.error(f"Failed to mark job failed: {err}")
        
        raise
