"""
API Gateway endpoint tester for CR2A integration testing.
Tests upload, analyze, and status endpoints with CORS configuration.
"""

import json
import time
import requests
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urljoin

from ..core.base import BaseTestFramework
from ..core.models import TestResult, TestStatus, TestConfiguration


class APIGatewayTester(BaseTestFramework):
    """Tester for API Gateway endpoint functionality and CORS configuration."""
    
    def __init__(self, config: TestConfiguration, api_base_url: str):
        super().__init__(config)
        self.api_base_url = api_base_url.rstrip('/')
        self.endpoints = {
            "upload": "/upload",
            "analyze": "/analyze", 
            "status": "/status"
        }
        self.timeout = 30  # seconds
    
    def test_upload_endpoint(self) -> TestResult:
        """Test the upload endpoint for S3 presigned URL generation."""
        def _test_upload():
            url = urljoin(self.api_base_url, self.endpoints["upload"])
            
            # Test POST request for presigned URL
            payload = {
                "fileName": "test-contract.pdf",
                "fileType": "application/pdf",
                "fileSize": 1024000  # 1MB
            }
            
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            
            response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            
            result = {
                "status_code": response.status_code,
                "response_data": response_data,
                "response_headers": dict(response.headers),
                "request_payload": payload
            }
            
            # Validate response structure
            if response.status_code == 200:
                if "presignedUrl" not in response_data:
                    raise ValueError("Response missing 'presignedUrl' field")
                
                if "uploadId" not in response_data:
                    raise ValueError("Response missing 'uploadId' field")
                
                # Validate presigned URL format
                presigned_url = response_data["presignedUrl"]
                if not presigned_url.startswith("https://"):
                    raise ValueError("Presigned URL should use HTTPS")
                
                if "s3" not in presigned_url.lower():
                    raise ValueError("Presigned URL should be an S3 URL")
            
            elif response.status_code >= 400:
                error_msg = response_data.get("error", f"HTTP {response.status_code}")
                raise ValueError(f"Upload endpoint returned error: {error_msg}")
            
            return result
        
        result = self.execute_test_with_timing(
            "test_upload_endpoint",
            lambda: self.retry_operation(_test_upload)
        )
        
        if result.status == TestStatus.PASS and result.details:
            status_code = result.details["status_code"]
            if status_code == 200:
                result.message = "Upload endpoint returned valid presigned URL"
            else:
                result.status = TestStatus.FAIL
                result.message = f"Upload endpoint returned status {status_code}"
        
        return result
    
    def test_analyze_endpoint(self) -> TestResult:
        """Test the analyze endpoint for Step Functions execution initiation."""
        def _test_analyze():
            url = urljoin(self.api_base_url, self.endpoints["analyze"])
            
            # Test POST request to start analysis
            payload = {
                "uploadId": "test-upload-123",
                "s3Bucket": "cr2a-test-bucket",
                "s3Key": "uploads/test-contract.pdf",
                "analysisType": "full",
                "options": {
                    "extractTables": True,
                    "extractImages": False
                }
            }
            
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            
            response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            
            result = {
                "status_code": response.status_code,
                "response_data": response_data,
                "response_headers": dict(response.headers),
                "request_payload": payload
            }
            
            # Validate response structure
            if response.status_code == 200:
                if "jobId" not in response_data:
                    raise ValueError("Response missing 'jobId' field")
                
                if "executionArn" not in response_data:
                    raise ValueError("Response missing 'executionArn' field")
                
                # Validate job ID format
                job_id = response_data["jobId"]
                if not job_id or len(job_id) < 10:
                    raise ValueError("Job ID should be a meaningful identifier")
                
                # Validate execution ARN format
                execution_arn = response_data["executionArn"]
                if not execution_arn.startswith("arn:aws:states:"):
                    raise ValueError("Execution ARN should be a valid Step Functions ARN")
            
            elif response.status_code >= 400:
                error_msg = response_data.get("error", f"HTTP {response.status_code}")
                raise ValueError(f"Analyze endpoint returned error: {error_msg}")
            
            return result
        
        result = self.execute_test_with_timing(
            "test_analyze_endpoint",
            lambda: self.retry_operation(_test_analyze)
        )
        
        if result.status == TestStatus.PASS and result.details:
            status_code = result.details["status_code"]
            if status_code == 200:
                result.message = "Analyze endpoint started Step Functions execution successfully"
            else:
                result.status = TestStatus.FAIL
                result.message = f"Analyze endpoint returned status {status_code}"
        
        return result
    
    def test_status_endpoint(self) -> TestResult:
        """Test the status endpoint for job status and progress information."""
        def _test_status():
            # Test with a sample job ID
            job_id = "test-job-123"
            url = urljoin(self.api_base_url, f"{self.endpoints['status']}/{job_id}")
            
            response = requests.get(
                url,
                headers={"Accept": "application/json"},
                timeout=self.timeout
            )
            
            response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            
            result = {
                "status_code": response.status_code,
                "response_data": response_data,
                "response_headers": dict(response.headers),
                "job_id": job_id
            }
            
            # Validate response structure
            if response.status_code == 200:
                required_fields = ["jobId", "status", "progress"]
                for field in required_fields:
                    if field not in response_data:
                        raise ValueError(f"Response missing required field: '{field}'")
                
                # Validate status values
                valid_statuses = ["PENDING", "RUNNING", "SUCCEEDED", "FAILED", "TIMED_OUT"]
                status = response_data["status"]
                if status not in valid_statuses:
                    raise ValueError(f"Invalid status value: {status}. Expected one of: {valid_statuses}")
                
                # Validate progress format
                progress = response_data["progress"]
                if not isinstance(progress, (int, float)) or progress < 0 or progress > 100:
                    raise ValueError("Progress should be a number between 0 and 100")
            
            elif response.status_code == 404:
                # Job not found is acceptable for testing
                result["job_not_found"] = True
            
            elif response.status_code >= 400:
                error_msg = response_data.get("error", f"HTTP {response.status_code}")
                raise ValueError(f"Status endpoint returned error: {error_msg}")
            
            return result
        
        result = self.execute_test_with_timing(
            "test_status_endpoint",
            lambda: self.retry_operation(_test_status)
        )
        
        if result.status == TestStatus.PASS and result.details:
            status_code = result.details["status_code"]
            if status_code == 200:
                result.message = "Status endpoint returned valid job status information"
            elif status_code == 404:
                result.message = "Status endpoint correctly returned 404 for non-existent job"
            else:
                result.status = TestStatus.FAIL
                result.message = f"Status endpoint returned unexpected status {status_code}"
        
        return result
    
    def test_cors_configuration(self) -> TestResult:
        """Test CORS configuration for cross-origin requests."""
        def _test_cors():
            cors_results = {}
            
            # Test each endpoint for CORS headers
            for endpoint_name, endpoint_path in self.endpoints.items():
                url = urljoin(self.api_base_url, endpoint_path)
                
                # Send OPTIONS request (preflight)
                options_response = requests.options(
                    url,
                    headers={
                        "Origin": "https://example.com",
                        "Access-Control-Request-Method": "POST",
                        "Access-Control-Request-Headers": "Content-Type"
                    },
                    timeout=self.timeout
                )
                
                cors_headers = {
                    "access-control-allow-origin": options_response.headers.get("Access-Control-Allow-Origin"),
                    "access-control-allow-methods": options_response.headers.get("Access-Control-Allow-Methods"),
                    "access-control-allow-headers": options_response.headers.get("Access-Control-Allow-Headers"),
                    "access-control-max-age": options_response.headers.get("Access-Control-Max-Age")
                }
                
                cors_results[endpoint_name] = {
                    "status_code": options_response.status_code,
                    "cors_headers": cors_headers,
                    "has_cors": any(header for header in cors_headers.values() if header is not None)
                }
            
            # Check if CORS is properly configured
            cors_issues = []
            for endpoint_name, endpoint_result in cors_results.items():
                if not endpoint_result["has_cors"]:
                    cors_issues.append(f"{endpoint_name} endpoint missing CORS headers")
                elif endpoint_result["cors_headers"]["access-control-allow-origin"] is None:
                    cors_issues.append(f"{endpoint_name} endpoint missing Access-Control-Allow-Origin header")
            
            return {
                "cors_results": cors_results,
                "cors_issues": cors_issues,
                "cors_properly_configured": len(cors_issues) == 0
            }
        
        result = self.execute_test_with_timing(
            "test_cors_configuration",
            lambda: self.retry_operation(_test_cors)
        )
        
        if result.status == TestStatus.PASS and result.details:
            if result.details["cors_properly_configured"]:
                result.message = "CORS is properly configured for all endpoints"
            else:
                result.status = TestStatus.FAIL
                result.message = f"CORS configuration issues: {'; '.join(result.details['cors_issues'])}"
        
        return result
    
    def test_error_handling(self) -> TestResult:
        """Test API error handling with invalid requests."""
        def _test_error_handling():
            error_test_results = []
            
            # Test 1: Invalid JSON payload
            url = urljoin(self.api_base_url, self.endpoints["upload"])
            response = requests.post(
                url,
                data="invalid json",
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            
            error_test_results.append({
                "test": "invalid_json",
                "status_code": response.status_code,
                "expected_4xx": response.status_code >= 400 and response.status_code < 500,
                "has_error_message": "error" in response.text.lower()
            })
            
            # Test 2: Missing required fields
            response = requests.post(
                url,
                json={},  # Empty payload
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            
            error_test_results.append({
                "test": "missing_fields",
                "status_code": response.status_code,
                "expected_4xx": response.status_code >= 400 and response.status_code < 500,
                "has_error_message": "error" in response.text.lower()
            })
            
            # Test 3: Invalid endpoint
            invalid_url = urljoin(self.api_base_url, "/nonexistent")
            response = requests.get(invalid_url, timeout=self.timeout)
            
            error_test_results.append({
                "test": "invalid_endpoint",
                "status_code": response.status_code,
                "expected_404": response.status_code == 404
            })
            
            # Validate error handling
            error_handling_issues = []
            for test_result in error_test_results:
                test_name = test_result["test"]
                
                if test_name in ["invalid_json", "missing_fields"]:
                    if not test_result["expected_4xx"]:
                        error_handling_issues.append(f"{test_name} should return 4xx status code")
                    if not test_result["has_error_message"]:
                        error_handling_issues.append(f"{test_name} should include error message")
                
                elif test_name == "invalid_endpoint":
                    if not test_result["expected_404"]:
                        error_handling_issues.append(f"{test_name} should return 404 status code")
            
            return {
                "error_test_results": error_test_results,
                "error_handling_issues": error_handling_issues,
                "error_handling_proper": len(error_handling_issues) == 0
            }
        
        result = self.execute_test_with_timing(
            "test_error_handling",
            lambda: self.retry_operation(_test_error_handling)
        )
        
        if result.status == TestStatus.PASS and result.details:
            if result.details["error_handling_proper"]:
                result.message = "API error handling is working correctly"
            else:
                result.status = TestStatus.FAIL
                result.message = f"API error handling issues: {'; '.join(result.details['error_handling_issues'])}"
        
        return result
    
    def run_comprehensive_endpoint_tests(self) -> List[TestResult]:
        """Run all endpoint tests and return comprehensive results."""
        test_results = []
        
        # Run all individual tests
        test_results.append(self.test_upload_endpoint())
        test_results.append(self.test_analyze_endpoint())
        test_results.append(self.test_status_endpoint())
        test_results.append(self.test_cors_configuration())
        test_results.append(self.test_error_handling())
        
        return test_results
    
    def get_endpoint_health_summary(self) -> Dict[str, Any]:
        """Get a summary of endpoint health status."""
        test_results = self.run_comprehensive_endpoint_tests()
        
        summary = {
            "total_tests": len(test_results),
            "passed_tests": sum(1 for result in test_results if result.status == TestStatus.PASS),
            "failed_tests": sum(1 for result in test_results if result.status == TestStatus.FAIL),
            "error_tests": sum(1 for result in test_results if result.status == TestStatus.ERROR),
            "overall_health": "HEALTHY" if all(result.status == TestStatus.PASS for result in test_results) else "UNHEALTHY",
            "test_details": [
                {
                    "test_name": result.test_name,
                    "status": result.status.value,
                    "message": result.message,
                    "execution_time": result.execution_time
                }
                for result in test_results
            ]
        }
        
        return summary
    
    def test_api_endpoints(self) -> TestResult:
        """Test all API Gateway endpoints comprehensively."""
        test_name = "test_api_endpoints"
        
        try:
            # Run all endpoint tests
            endpoint_results = self.run_comprehensive_endpoint_tests()
            
            # Analyze results
            total_tests = len(endpoint_results)
            passed_tests = sum(1 for result in endpoint_results if result.status == TestStatus.PASS)
            failed_tests = sum(1 for result in endpoint_results if result.status == TestStatus.FAIL)
            error_tests = sum(1 for result in endpoint_results if result.status == TestStatus.ERROR)
            
            # Determine overall status
            if error_tests > 0:
                status = TestStatus.ERROR
                message = f"API endpoint testing encountered {error_tests} errors"
            elif failed_tests > 0:
                status = TestStatus.FAIL
                message = f"API endpoint testing failed {failed_tests} out of {total_tests} tests"
            elif passed_tests > 0:
                status = TestStatus.PASS
                message = f"All {total_tests} API endpoint tests passed successfully"
            else:
                status = TestStatus.SKIP
                message = "No API endpoint tests were executed"
            
            return TestResult(
                test_name=test_name,
                status=status,
                message=message,
                details={
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "failed_tests": failed_tests,
                    "error_tests": error_tests,
                    "endpoint_results": [
                        {
                            "test_name": result.test_name,
                            "status": result.status.value,
                            "message": result.message
                        }
                        for result in endpoint_results
                    ]
                }
            )
            
        except Exception as e:
            return TestResult(
                test_name=test_name,
                status=TestStatus.ERROR,
                message=f"API endpoint testing failed: {str(e)}"
            )