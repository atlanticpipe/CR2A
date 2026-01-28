"""
Contract Analysis API Usage Examples

This file demonstrates various ways to use the Contract Analysis API,
including direct API calls, client library usage, and integration examples.

Run with: python api_examples.py
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict

# Import the API client
import contract_analysis_client


def example_1_basic_usage():
    """Example 1: Basic usage with environment variables"""
    print("=== Example 1: Basic Usage ===")
    
    # Set environment variables
    os.environ['CONTRACT_API_KEY'] = 'your-secret-api-key'
    os.environ['CONTRACT_API_URL'] = 'http://localhost:8000'
    
    try:
        # Create client from environment
        client = contract_analysis_client.create_client_from_env()
        
        # Check API health
        health = client.health_check()
        print(f"API Health: {health}")
        
        # Get schema information
        schema = client.get_schema()
        print(f"Schema version: {schema['schema']['$id']}")
        
    except contract_analysis_client.ContractAnalysisError as e:
        print(f"Error: {e}")


def example_2_file_analysis():
    """Example 2: Analyze a contract file"""
    print("\n=== Example 2: File Analysis ===")
    
    # Use the sample PDF from the workspace
    pdf_path = "Clause Risk & Compliance Summary 4.pdf"
    
    if not Path(pdf_path).exists():
        print(f"Sample PDF not found at {pdf_path}")
        return
    
    try:
        # Analyze with direct API key
        api_key = "your-secret-api-key"
        result = contract_analysis_client.analyze_contract_file(
            file_path=pdf_path,
            api_key=api_key,
            base_url="http://localhost:8000"
        )
        
        # Display results
        print("Analysis completed successfully!")
        print(f"Schema version: {result['data']['schema_version']}")
        print(f"Contractor: {result['data']['contract_overview']['Contractor']}")
        print(f"Risk level: {result['data']['contract_overview']['General Risk Level']}")
        
        # Show structure of results
        data = result['data']
        print(f"\nAnalysis sections found: {len(data)}")
        for section_name in data.keys():
            if section_name != 'schema_version':
                print(f"  - {section_name}")
        
        # Save results to file
        output_path = "api_analysis_result.json"
        client = contract_analysis_client.ContractAnalysisClient(
            api_key=api_key,
            base_url="http://localhost:8000"
        )
        client.save_analysis_to_file(result, output_path)
        print(f"Results saved to: {output_path}")
        
    except contract_analysis_client.ContractAnalysisError as e:
        print(f"Error: {e}")


def example_3_programmatic_client():
    """Example 3: Using the client class programmatically"""
    print("\n=== Example 3: Programmatic Client Usage ===")
    
    try:
        # Create client instance
        client = contract_analysis_client.ContractAnalysisClient(
            api_key="your-secret-api-key",
            base_url="http://localhost:8000",
            timeout=600  # Longer timeout for large files
        )
        
        # Check API status
        health = client.health_check()
        print(f"API Status: {health['status']}")
        
        # Get validation rules
        rules = client.get_validation_rules()
        print(f"Validation rules loaded: {len(rules['rules'])} rules")
        
        # Example with sample file (if available)
        sample_pdf = "Clause Risk & Compliance Summary 4.pdf"
        if Path(sample_pdf).exists():
            print(f"Analyzing sample PDF: {sample_pdf}")
            result = client.analyze_contract(sample_pdf)
            print(f"Analysis completed in {result['metadata']['processing_timestamp']}")
        
    except contract_analysis_client.ContractAnalysisError as e:
        print(f"Error: {e}")


def example_4_web_integration():
    """Example 4: Web application integration pattern"""
    print("\n=== Example 4: Web Integration Pattern ===")
    
    # This example shows how to integrate with a web application
    # where files are uploaded via web forms
    
    def analyze_uploaded_file(file_content: bytes, filename: str, api_key: str) -> Dict:
        """
        Simulate web application file upload analysis
        
        Args:
            file_content: File bytes from web upload
            filename: Original filename
            api_key: API authentication key
            
        Returns:
            Analysis results
        """
        client = contract_analysis_client.ContractAnalysisClient(
            api_key=api_key,
            base_url="http://localhost:8000"
        )
        
        # Analyze from bytes (useful for web apps)
        result = client.analyze_contract_from_bytes(
            file_content=file_content,
            filename=filename
        )
        
        return result
    
    # Example usage (commented out to avoid errors)
    """
    # In a real web application, you would do something like:
    if request.method == 'POST':
        file = request.files['contract']
        file_content = file.read()
        filename = file.filename
        
        result = analyze_uploaded_file(file_content, filename, API_KEY)
        return jsonify(result)
    """
    
    print("Web integration pattern defined (example function above)")
    print("Use analyze_contract_from_bytes() for web applications")


def example_5_batch_processing():
    """Example 5: Batch processing multiple files"""
    print("\n=== Example 5: Batch Processing ===")
    
    def analyze_multiple_contracts(file_paths: list, api_key: str) -> list:
        """
        Analyze multiple contract files
        
        Args:
            file_paths: List of file paths to analyze
            api_key: API authentication key
            
        Returns:
            List of analysis results
        """
        client = contract_analysis_client.ContractAnalysisClient(
            api_key=api_key,
            base_url="http://localhost:8000"
        )
        
        results = []
        for file_path in file_paths:
            try:
                print(f"Analyzing: {file_path}")
                result = client.analyze_contract(file_path)
                results.append({
                    'file': file_path,
                    'success': True,
                    'data': result
                })
            except contract_analysis_client.ContractAnalysisError as e:
                print(f"Error analyzing {file_path}: {e}")
                results.append({
                    'file': file_path,
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    # Example file list (using available files)
    available_files = [
        "Clause Risk & Compliance Summary 4.pdf",
        # Add more contract files here as needed
    ]
    
    existing_files = [f for f in available_files if Path(f).exists()]
    
    if existing_files:
        results = analyze_multiple_contracts(existing_files, "your-secret-api-key")
        
        successful = sum(1 for r in results if r['success'])
        print(f"\nBatch processing complete: {successful}/{len(results)} successful")
        
        # Save batch results
        batch_output = "batch_analysis_results.json"
        with open(batch_output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Batch results saved to: {batch_output}")
    else:
        print("No contract files available for batch processing")


def example_6_error_handling():
    """Example 6: Comprehensive error handling"""
    print("\n=== Example 6: Error Handling ===")
    
    def analyze_with_error_handling(file_path: str, api_key: str) -> Dict:
        """
        Analyze contract with comprehensive error handling
        
        Returns detailed error information for debugging
        """
        try:
            result = contract_analysis_client.analyze_contract_file(
                file_path=file_path,
                api_key=api_key
            )
            return {
                'success': True,
                'result': result,
                'error': None
            }
            
        except contract_analysis_client.ContractAnalysisError as e:
            return {
                'success': False,
                'result': None,
                'error': {
                    'type': 'ContractAnalysisError',
                    'message': str(e),
                    'file': file_path
                }
            }
        except FileNotFoundError as e:
            return {
                'success': False,
                'result': None,
                'error': {
                    'type': 'FileNotFoundError',
                    'message': str(e),
                    'file': file_path
                }
            }
        except Exception as e:
            return {
                'success': False,
                'result': None,
                'error': {
                    'type': 'UnexpectedError',
                    'message': str(e),
                    'file': file_path
                }
            }
    
    # Test with various scenarios
    test_cases = [
        "Clause Risk & Compliance Summary 4.pdf",  # Should work if exists
        "nonexistent.pdf",  # File not found
        "README.md",  # Wrong file type
    ]
    
    for test_file in test_cases:
        print(f"\nTesting: {test_file}")
        result = analyze_with_error_handling(test_file, "your-secret-api-key")
        
        if result['success']:
            print("✓ Analysis successful")
        else:
            error = result['error']
            print(f"✗ Error: {error['type']} - {error['message']}")


async def example_7_async_analysis():
    """Example 7: Asynchronous analysis (for multiple files)"""
    print("\n=== Example 7: Asynchronous Analysis ===")
    
    async def analyze_async(file_path: str, api_key: str) -> Dict:
        """Analyze a single file asynchronously"""
        # Note: This is a simplified example
        # In practice, you'd use aiohttp or similar for true async HTTP
        import threading
        
        def analyze_in_thread():
            return contract_analysis_client.analyze_contract_file(
                file_path=file_path,
                api_key=api_key
            )
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, analyze_in_thread)
        return result
    
    # Example async analysis
    sample_file = "Clause Risk & Compliance Summary 4.pdf"
    if Path(sample_file).exists():
        print(f"Starting async analysis of: {sample_file}")
        # result = await analyze_async(sample_file, "your-secret-api-key")
        # print(f"Async analysis completed: {result['metadata']['processing_timestamp']}")
        print("Async example defined (requires aiohttp for full implementation)")
    else:
        print("Sample file not available for async example")


def main():
    """Run all examples"""
    print("Contract Analysis API Examples")
    print("=" * 50)
    
    # Run examples
    example_1_basic_usage()
    example_2_file_analysis()
    example_3_programmatic_client()
    example_4_web_integration()
    example_5_batch_processing()
    example_6_error_handling()
    
    # Async example (commented out as it requires additional setup)
    # asyncio.run(example_7_async_analysis())
    
    print("\n" + "=" * 50)
    print("Examples completed!")
    print("\nTo run the API server:")
    print("  python contract_analysis_api.py")
    print("\nTo use the client:")
    print("  python contract_analysis_client.py path/to/contract.pdf")


if __name__ == "__main__":
    main()
