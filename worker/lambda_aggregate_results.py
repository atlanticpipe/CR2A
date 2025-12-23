"""
Lambda: Aggregate Results
- Combines all chunk analyses into final contract analysis
"""
import json
import boto3
from datetime import datetime
from collections import defaultdict

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
jobs_table = dynamodb.Table('cr2a-jobs')

def lambda_handler(event, context):
    """Aggregate all chunk results into final analysis"""
    job_id = event['job_id']
    total_chunks = event['total_chunks']
    
    try:
        all_chunks = []
        all_clauses = []
        clause_counts = defaultdict(int)
        total_text_length = 0
        
        for chunk_index in range(total_chunks):
            chunk_key = f"results/{job_id}/chunks/chunk-{chunk_index}.json"
            
            try:
                response = s3_client.get_object(Bucket='cr2a-output', Key=chunk_key)
                chunk_data = json.loads(response['Body'].read())
                
                all_chunks.append(chunk_data)
                all_clauses.extend(chunk_data['clauses_found'])
                total_text_length += chunk_data['text_length']
                
                for clause_type, count in chunk_data['clause_summary'].items():
                    clause_counts[clause_type] += count
                    
            except s3_client.exceptions.NoSuchKey:
                print(f"Warning: Chunk {chunk_index} not found")
            except Exception as e:
                print(f"Error reading chunk {chunk_index}: {str(e)}")
        
        final_analysis = {
            'job_id': job_id,
            'completed_at': datetime.now().isoformat(),
            'total_chunks': total_chunks,
            'total_text_length': total_text_length,
            'total_clauses_found': len(all_clauses),
            'summary': {
                'clause_counts': dict(clause_counts),
                'top_clause_types': get_top_clauses(clause_counts, 5),
                'chunks_processed': len(all_chunks),
                'errors': total_chunks - len(all_chunks)
            },
            'all_clauses': all_clauses,
            'chunk_details': all_chunks,
            'recommendations': generate_recommendations(clause_counts, all_clauses)
        }
        
        result_key = f"results/{job_id}/final_analysis.json"
        s3_client.put_object(
            Bucket='cr2a-output',
            Key=result_key,
            Body=json.dumps(final_analysis, indent=2),
            ContentType='application/json'
        )
        
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
            'job_id': job_id,
            'status': 'completed',
            'result_key': result_key,
            'total_clauses_found': len(all_clauses),
            'chunks_processed': len(all_chunks)
        }
        
    except Exception as e:
        jobs_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression='SET #status = :status, error = :error',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'failed',
                ':error': f"Aggregation error: {str(e)}"
            }
        )
        raise


def get_top_clauses(clause_counts, top_n):
    """Get top N most common clause types"""
    sorted_clauses = sorted(clause_counts.items(), key=lambda x: x[1], reverse=True)
    return [{'type': clause_type, 'count': count} for clause_type, count in sorted_clauses[:top_n]]


def generate_recommendations(clause_counts, all_clauses):
    """Generate analysis recommendations based on findings"""
    recommendations = []
    
    critical_clauses = ['Payment', 'Termination', 'Governing Law', 'Limitation of Liability']
    
    for clause_type in critical_clauses:
        if clause_counts.get(clause_type, 0) == 0:
            recommendations.append({
                'severity': 'warning',
                'clause_type': clause_type,
                'message': f"No {clause_type} clause found. This is typically critical for contracts."
            })
    
    risk_clauses = {
        'Indemnification': 'Review indemnification scope and limitations',
        'Force Majeure': 'Ensure force majeure terms are appropriate for your business',
        'Dispute Resolution': 'Verify dispute resolution mechanism aligns with your preferences'
    }
    
    for clause_type, recommendation in risk_clauses.items():
        if clause_counts.get(clause_type, 0) > 0:
            recommendations.append({
                'severity': 'info',
                'clause_type': clause_type,
                'message': recommendation
            })
    
    total_clauses = sum(clause_counts.values())
    if total_clauses == 0:
        recommendations.append({
            'severity': 'critical',
            'message': 'No contract clauses were identified. Verify file format and content.'
        })
    
    return recommendations