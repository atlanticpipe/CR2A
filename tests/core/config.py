"""
Configuration management for the CR2A testing framework.
Handles loading and validation of test configuration settings.
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import asdict
from .models import TestConfiguration


class ConfigurationManager:
    """Manages test configuration loading and validation."""
    
    DEFAULT_CONFIG_FILE = "test_config.json"
    
    @classmethod
    def load_from_file(cls, config_path: Optional[str] = None) -> TestConfiguration:
        """Load configuration from JSON file."""
        config_path = config_path or cls.DEFAULT_CONFIG_FILE
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            return TestConfiguration(**config_data)
        else:
            # Return default configuration if file doesn't exist
            return TestConfiguration()
    
    @classmethod
    def load_from_env(cls) -> TestConfiguration:
        """Load configuration from environment variables."""
        return TestConfiguration(
            aws_region=os.getenv('AWS_REGION', 'us-east-1'),
            lambda_timeout=int(os.getenv('LAMBDA_TIMEOUT', '30')),
            max_retries=int(os.getenv('MAX_RETRIES', '3')),
            parallel_execution=os.getenv('PARALLEL_EXECUTION', 'false').lower() == 'true',
            verbose_logging=os.getenv('VERBOSE_LOGGING', 'true').lower() == 'true',
            save_artifacts=os.getenv('SAVE_ARTIFACTS', 'true').lower() == 'true',
            artifact_path=os.getenv('ARTIFACT_PATH', './test-artifacts')
        )
    
    @classmethod
    def save_to_file(cls, config: TestConfiguration, config_path: Optional[str] = None) -> str:
        """Save configuration to JSON file."""
        config_path = config_path or cls.DEFAULT_CONFIG_FILE
        
        with open(config_path, 'w') as f:
            json.dump(asdict(config), f, indent=2)
        
        return config_path
    
    @classmethod
    def get_cr2a_resource_names(cls) -> Dict[str, str]:
        """Get CR2A resource names from environment or defaults."""
        return {
            'state_machine_name': os.getenv('CR2A_STATE_MACHINE_NAME', 'cr2a-contract-analysis'),
            'api_gateway_id': os.getenv('CR2A_API_GATEWAY_ID', ''),
            'lambda_functions': {
                'api': os.getenv('CR2A_API_LAMBDA', 'cr2a-api'),
                'analyzer': os.getenv('CR2A_ANALYZER_LAMBDA', 'cr2a-analyzer'),
                'llm_refine': os.getenv('CR2A_LLM_REFINE_LAMBDA', 'cr2a-llm-refine'),
                'calculate_chunks': os.getenv('CR2A_CALCULATE_CHUNKS_LAMBDA', 'cr2a-calculate-chunks'),
                'analyze_chunk': os.getenv('CR2A_ANALYZE_CHUNK_LAMBDA', 'cr2a-analyze-chunk'),
                'aggregate_results': os.getenv('CR2A_AGGREGATE_RESULTS_LAMBDA', 'cr2a-aggregate-results'),
                'get_metadata': os.getenv('CR2A_GET_METADATA_LAMBDA', 'cr2a-get-metadata')
            },
            'dynamodb_tables': {
                'jobs': os.getenv('CR2A_JOBS_TABLE', 'cr2a-jobs'),
                'results': os.getenv('CR2A_RESULTS_TABLE', 'cr2a-results')
            },
            's3_buckets': {
                'documents': os.getenv('CR2A_DOCUMENTS_BUCKET', 'cr2a-documents'),
                'results': os.getenv('CR2A_RESULTS_BUCKET', 'cr2a-results')
            }
        }
    
    @classmethod
    def validate_aws_credentials(cls) -> bool:
        """Validate that AWS credentials are available."""
        try:
            import boto3
            session = boto3.Session()
            credentials = session.get_credentials()
            return credentials is not None
        except Exception:
            return False