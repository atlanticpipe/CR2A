"""
Contract Analysis API Client

Python client library for interacting with the Contract Analysis API server.
Provides easy-to-use methods for uploading documents and retrieving structured
risk analysis results that match the Clause Risk & Compliance Summary format.

Usage:
    from contract_analysis_client import ContractAnalysisClient
    
    client = ContractAnalysisClient(api_key="your-api-key", base_url="http://localhost:8000")
    result = client.analyze_contract("path/to/contract.pdf")
    print(result["data"]["contract_overview"]["Contractor"])
"""

import os
import json
import requests
from pathlib import Path
from typing import Dict, Optional, Union
from urllib.parse import urljoin


class ContractAnalysisError(Exception):
    """Custom exception for Contract Analysis API errors"""
    pass


class ContractAnalysisClient:
    """
    Client for interacting with the Contract Analysis API
    
    Args:
        api_key: API key for authentication
        base_url: Base URL of the API server (default: http://localhost:8000)
        timeout: Request timeout in seconds (default: 300)
    """
    
    def __init__(
        self, 
        api_key: str, 
        base_url: str = "http://localhost:8000",
        timeout: int = 300
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}'
        })
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        **kwargs
    ) -> Dict:
        """Make HTTP request to API server"""
        url = urljoin(self.base_url, endpoint)
        
        # Set default timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise ContractAnalysisError(f"API request failed: {str(e)}")
        except json.JSONDecodeError as e:
            raise ContractAnalysisError(f"Invalid JSON response: {str(e)}")
    
    def health_check(self) -> Dict:
        """Check API server health"""
        return self._make_request('GET', '/health')
    
    def get_schema(self) -> Dict:
        """Get the JSON schema used for contract analysis"""
        return self._make_request('GET', '/schema')
    
    def get_validation_rules(self) -> Dict:
        """Get the validation rules used for compliance checking"""
        return self._make_request('GET', '/validation-rules')
    
    def analyze_contract(
        self, 
        file_path: Union[str, Path], 
        validate_response: bool = True
    ) -> Dict:
        """
        Analyze a contract document and return structured results
        
        Args:
            file_path: Path to PDF or DOCX file
            validate_response: Whether to validate response format (default: True)
            
        Returns:
            Dictionary containing analysis results with the following structure:
            {
                "success": bool,
                "message": str,
                "data": {
                    "schema_version": str,
                    "contract_overview": {...},
                    "administrative_and_commercial_terms": {...},
                    "technical_and_performance_terms": {...},
                    "legal_risk_and_enforcement": {...},
                    "regulatory_and_compliance_terms": {...},
                    "data_technology_and_deliverables": {...},
                    "supplemental_operational_risks": [...],
                    "final_analysis": {...}
                },
                "metadata": {...}
            }
            
        Raises:
            ContractAnalysisError: If file is invalid or analysis fails
        """
        # Validate file path
        file_path = Path(file_path)
        if not file_path.exists():
            raise ContractAnalysisError(f"File not found: {file_path}")
        
        if not file_path.is_file():
            raise ContractAnalysisError(f"Path is not a file: {file_path}")
        
        # Validate file extension
        supported_extensions = {'.pdf', '.docx'}
        if file_path.suffix.lower() not in supported_extensions:
            raise ContractAnalysisError(
                f"Unsupported file format: {file_path.suffix}. "
                f"Supported formats: {', '.join(supported_extensions)}"
            )
        
        # Check file size (client-side check before upload)
        file_size = file_path.stat().st_size
        max_size = 50 * 1024 * 1024  # 50MB
        if file_size > max_size:
            raise ContractAnalysisError(f"File size {file_size} exceeds limit of {max_size} bytes")
        
        # Prepare file for upload
        with open(file_path, 'rb') as file:
            files = {'file': (file_path.name, file, 'application/octet-stream')}
            
            # Make API request
            response = self._make_request(
                'POST', 
                '/analyze-contract',
                files=files
            )
        
        # Validate response structure if requested
        if validate_response:
            self._validate_response_structure(response)
        
        return response
    
    def _validate_response_structure(self, response: Dict) -> None:
        """Validate that API response has expected structure"""
        if not isinstance(response, dict):
            raise ContractAnalysisError("Response is not a valid JSON object")
        
        if not response.get('success', False):
            error_msg = response.get('error', 'Unknown error')
            raise ContractAnalysisError(f"API returned error: {error_msg}")
        
        # Check for required fields
        data = response.get('data', {})
        if not isinstance(data, dict):
            raise ContractAnalysisError("Response data is not a valid object")
        
        # Validate schema version
        schema_version = data.get('schema_version')
        if not schema_version or not schema_version.startswith('v1.'):
            raise ContractAnalysisError(f"Invalid or missing schema version: {schema_version}")
        
        # Validate required sections
        required_sections = [
            'contract_overview',
            'administrative_and_commercial_terms',
            'technical_and_performance_terms',
            'legal_risk_and_enforcement',
            'regulatory_and_compliance_terms',
            'data_technology_and_deliverables',
            'supplemental_operational_risks',
            'final_analysis'
        ]
        
        for section in required_sections:
            if section not in data:
                raise ContractAnalysisError(f"Missing required section: {section}")
    
    def analyze_contract_from_bytes(
        self, 
        file_content: bytes, 
        filename: str,
        validate_response: bool = True
    ) -> Dict:
        """
        Analyze a contract from file bytes (useful for web applications)
        
        Args:
            file_content: File content as bytes
            filename: Original filename (used for validation)
            validate_response: Whether to validate response format
            
        Returns:
            Dictionary containing analysis results
            
        Raises:
            ContractAnalysisError: If file is invalid or analysis fails
        """
        # Validate filename
        if not filename.lower().endswith(('.pdf', '.docx')):
            raise ContractAnalysisError(
                f"Unsupported file format: {filename}. Supported: .pdf, .docx"
            )
        
        # Check file size
        file_size = len(file_content)
        max_size = 50 * 1024 * 1024  # 50MB
        if file_size > max_size:
            raise ContractAnalysisError(f"File size {file_size} exceeds limit of {max_size} bytes")
        
        # Prepare file for upload
        files = {'file': (filename, file_content, 'application/octet-stream')}
        
        # Make API request
        response = self._make_request(
            'POST',
            '/analyze-contract',
            files=files
        )
        
        # Validate response structure if requested
        if validate_response:
            self._validate_response_structure(response)
        
        return response
    
    def save_analysis_to_file(self, analysis_result: Dict, output_path: Union[str, Path]) -> None:
        """
        Save analysis results to a JSON file
        
        Args:
            analysis_result: Analysis results from API
            output_path: Path where to save the JSON file
        """
        output_path = Path(output_path)
        
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save JSON file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, indent=2, ensure_ascii=False)
        
        print(f"Analysis results saved to: {output_path}")


def create_client_from_env() -> ContractAnalysisClient:
    """
    Create API client using environment variables
    
    Environment variables:
        CONTRACT_API_KEY: API key for authentication
        CONTRACT_API_URL: Base URL of API server (optional, defaults to localhost:8000)
    
    Returns:
        ContractAnalysisClient instance
        
    Raises:
        ContractAnalysisError: If required environment variables are missing
    """
    api_key = os.getenv('CONTRACT_API_KEY')
    if not api_key:
        raise ContractAnalysisError(
            "CONTRACT_API_KEY environment variable is required. "
            "Set it to your API key or pass api_key directly to ContractAnalysisClient()"
        )
    
    base_url = os.getenv('CONTRACT_API_URL', 'http://localhost:8000')
    
    return ContractAnalysisClient(api_key=api_key, base_url=base_url)


# Convenience functions for simple usage
def analyze_contract_file(
    file_path: Union[str, Path], 
    api_key: Optional[str] = None,
    base_url: str = "http://localhost:8000"
) -> Dict:
    """
    Convenience function to analyze a contract file in one call
    
    Args:
        file_path: Path to contract file
        api_key: API key (optional, will use env var if not provided)
        base_url: API server URL
        
    Returns:
        Analysis results dictionary
    """
    if api_key is None:
        client = create_client_from_env()
    else:
        client = ContractAnalysisClient(api_key=api_key, base_url=base_url)
    
    return client.analyze_contract(file_path)


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python contract_analysis_client.py <file_path> [api_key] [base_url]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    api_key = sys.argv[2] if len(sys.argv) > 2 else None
    base_url = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:8000"
    
    try:
        result = analyze_contract_file(file_path, api_key, base_url)
        print("Analysis completed successfully!")
        print(f"Schema version: {result['data']['schema_version']}")
        print(f"Contractor: {result['data']['contract_overview']['Contractor']}")
        print(f"Risk level: {result['data']['contract_overview']['General Risk Level']}")
    except ContractAnalysisError as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
