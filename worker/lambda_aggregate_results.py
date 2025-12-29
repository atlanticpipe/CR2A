"""
Lambda: Aggregate Results
- Combines all chunk analyses into final contract analysis
- Final step in Step Functions workflow
"""
import json
import boto3
import logging
from datetime import datetime
from collections import defaultdict
from botocore.exceptions import ClientError

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
jobs_table = dynamodb.Table('cr2a-jobs')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Aggregate all chunk results into final analysis.
    
    Input (from Step Functions Map state results):
    {
        "job_id": "...",
        "s3_bucket": "...",
        "s3_key": "...",
        "llm_enabled": true,
        "chunk_plan": {
            "total_chunks": 2,
            "chunks": [...]
        },
        "chunk_results": [
            {"chunk_index": 0, "status": "completed", "clauses_found": 12, ...},
            {"chunk_index": 1, "status": "completed", "clauses_found": 8, ...}
        ]
    }
    
    Output (for final analysis):
    {
        "job_id": "...",
        "status": "completed",
        "llm_enabled": true,
        "result_key": "results/job_id/final_analysis.json",
        "filled_template_key": "results/job_id/filled_template.json",
        "total_clauses_found": 20,
        "chunks_processed": 2,
        "summary": {...}
    }
    """
    try:
        job_id = event.get('job_id')
        s3_bucket = event.get('s3_bucket')
        s3_key = event.get('s3_key')
        llm_enabled = event.get('llm_enabled', True)  # IMPORTANT: Capture from input
        chunk_results = event.get('chunk_results', [])
        chunk_plan = event.get('chunk_plan', {})
        total_chunks = chunk_plan.get('total_chunks', 0)
        
        logger.info(f"Aggregating results for job {job_id}")
        logger.info(f"Processing {len(chunk_results)} chunk results out of {total_chunks} expected")
        logger.info(f"LLM enabled for this job: {llm_enabled}")
        
        all_chunks = []
        all_clauses = []
        clause_counts = defaultdict(int)
        total_text_length = 0
        successful_chunks = 0
        failed_chunks = 0
        
        # Process results from Map state
        for result in chunk_results:
            chunk_index = result.get('chunk_index')
            status = result.get('status')
            
            if status != 'completed':
                logger.warning(f"Chunk {chunk_index} failed or has error status: {status}")
                failed_chunks += 1
                continue
            
            try:
                # Download chunk analysis from S3
                chunk_key = result.get('chunk_key')
                if not chunk_key:
                    logger.warning(f"Chunk {chunk_index} has no chunk_key")
                    failed_chunks += 1
                    continue
                
                response = s3_client.get_object(Bucket='cr2a-output', Key=chunk_key)
                chunk_data = json.loads(response['Body'].read())
                
                all_chunks.append(chunk_data)
                all_clauses.extend(chunk_data.get('clauses_found', []))
                total_text_length += chunk_data.get('text_length', 0)
                
                # Accumulate clause counts
                for clause_type, count in chunk_data.get('clause_summary', {}).items():
                    clause_counts[clause_type] += count
                
                successful_chunks += 1
                logger.info(f"Aggregated chunk {chunk_index}: {len(chunk_data.get('clauses_found', []))} clauses")
                
            except ClientError as e:
                logger.error(f"Error reading chunk {chunk_index}: {e}")
                failed_chunks += 1
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing chunk {chunk_index} JSON: {e}")
                failed_chunks += 1
            except Exception as e:
                logger.error(f"Unexpected error processing chunk {chunk_index}: {e}")
                failed_chunks += 1
        
        logger.info(f"Successfully processed {successful_chunks}/{total_chunks} chunks")
        
        # Build final analysis
        final_analysis = {
            'job_id': job_id,
            'completed_at': datetime.now().isoformat(),
            'total_chunks_expected': total_chunks,
            'chunks_processed': successful_chunks,
            'chunks_failed': failed_chunks,
            'total_text_length': total_text_length,
            'total_clauses_found': len(all_clauses),
            'summary': {
                'clause_counts': dict(clause_counts),
                'top_clause_types': get_top_clauses(clause_counts, 5),
                'chunks_processed': successful_chunks,
                'success_rate': round((successful_chunks / max(1, total_chunks)) * 100, 1),
                'errors': failed_chunks
            },
            'all_clauses': all_clauses[:500],  # Limit to first 500 for JSON size
            'clause_details': all_clauses,
            'chunk_summaries': [{
                'chunk_index': chunk.get('chunk_index'),
                'clauses_found': len(chunk.get('clauses_found', [])),
                'text_length': chunk.get('text_length')
            } for chunk in all_chunks],
            'recommendations': generate_recommendations(clause_counts, all_clauses)
        }
        
        # Store final analysis in S3
        result_key = f"results/{job_id}/final_analysis.json"
        try:
            s3_client.put_object(
                Bucket='cr2a-output',
                Key=result_key,
                Body=json.dumps(final_analysis, indent=2),
                ContentType='application/json'
            )
            logger.info(f"Stored final analysis at s3://cr2a-output/{result_key}")
        except ClientError as e:
            logger.error(f"Error storing final analysis: {e}")
            raise
        
        # Update job status in DynamoDB
        try:
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
            logger.info(f"Updated job {job_id} status to completed")
        except ClientError as e:
            logger.error(f"Error updating job status: {e}")
        
        # Return result for Step Functions - INCLUDE llm_enabled!
        return {
            'job_id': job_id,
            'status': 'completed',
            'llm_enabled': llm_enabled,  # CRITICAL: Pass this forward to CheckLLMEnabled state
            'result_key': result_key,
            'filled_template_key': f"results/{job_id}/filled_template.json",
            'total_clauses_found': len(all_clauses),
            'chunks_processed': successful_chunks,
            'summary': final_analysis['summary']
        }
        
    except Exception as e:
        logger.error(f"Error in aggregate_results: {str(e)}", exc_info=True)
        
        # Mark job as failed
        try:
            jobs_table.update_item(
                Key={'job_id': job_id},
                UpdateExpression='SET #status = :status, error = :error',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'failed',
                    ':error': f"Aggregation error: {str(e)}"
                }
            )
        except Exception as err:
            logger.error(f"Error updating job status to failed: {err}")
        
        raise


def get_top_clauses(clause_counts, top_n):
    """
    Get top N most common clause types.
    
    Returns list of dicts with type and count.
    """
    sorted_clauses = sorted(clause_counts.items(), key=lambda x: x[1], reverse=True)
    return [{'type': clause_type, 'count': count} for clause_type, count in sorted_clauses[:top_n]]


def generate_recommendations(clause_counts, all_clauses):
    """
    Generate analysis recommendations based on clause findings.
    
    Returns list of recommendation dicts with severity and message.
    """
    recommendations = []
    
    # Critical clauses that should always be present
    critical_clauses = ['Payment', 'Termination', 'Governing Law', 'Limitation of Liability']
    
    for clause_type in critical_clauses:
        if clause_counts.get(clause_type, 0) == 0:
            recommendations.append({
                'severity': 'warning',
                'clause_type': clause_type,
                'message': f"No {clause_type} clause found. This is typically critical for contracts."
            })
    
    # Risk clauses that should be reviewed
    risk_clauses = {
        'Indemnification': 'Review indemnification scope and limitations carefully',
        'Force Majeure': 'Ensure force majeure terms are appropriate for your business',
        'Dispute Resolution': 'Verify dispute resolution mechanism aligns with your preferences',
        'Confidentiality': 'Review confidentiality obligations and exceptions'
    }
    
    for clause_type, recommendation in risk_clauses.items():
        if clause_counts.get(clause_type, 0) > 0:
            recommendations.append({
                'severity': 'info',
                'clause_type': clause_type,
                'message': recommendation
            })
    
    # Check overall contract analysis success
    total_clauses = sum(clause_counts.values())
    if total_clauses == 0:
        recommendations.append({
            'severity': 'critical',
            'message': 'No contract clauses were identified. Verify file format and content.'
        })
    elif total_clauses < 5:
        recommendations.append({
            'severity': 'warning',
            'message': 'Very few clauses identified. Contract may be incomplete or file format not supported.'
        })
    
    return recommendations
