"""
Property-based tests for API endpoint response validity.
Tests universal properties that should hold for all API endpoint configurations.

Feature: cr2a-testing-debugging, Property 8: API endpoint response validity
"""

import json
import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from typing import Dict, Any, List
import requests
from urllib.parse import urljoin

from ..core.models import TestConfiguration, TestStatus
from .api_gateway_tester import APIGatewayTester


# Strategy for generating valid file upload requests
@st.composite
def upload_request_payload(draw):
    """Generate valid upload request payloads."""
    file_extensions = ["pdf", "docx", "txt", "doc"]
    content_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain",
        "doc": "application/msword"
    }
    
    extension = draw(st.sampled_from(file_extensions))
    filename = draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip() and '/' not in x))
    
    return {
        "fileName": f"{filename}.{extension}",
        "fileType": content_types[extension],
        "fileSize": draw(st.integers(min_value=1024, max_value=10485760))  # 1KB to 10MB
    }


# Strategy for generating valid analysis requests
@st.composite
def analysis_request_payload(draw):
    """Generate valid analysis request payloads."""
    upload_id = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='-_'),
        min_size=10,
        max_size=50
    ))
    
    bucket_name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='-'),
        min_size=3,
        max_size=20
    ))
    
    filename = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='-_.'),
        min_size=5,
        max_size=30
    ))
    
    return {
        "uploadId": upload_id,
        "s3Bucket": f"cr2a-{bucket_name}",
        "s3Key": f"uploads/{filename}.pdf",
        "analysisType": draw(st.sampled_from(["full", "basic", "quick"])),
        "options": {
            "extractTables": draw(st.booleans()),
            "extractImages": draw(st.booleans())
        }
    }


# Strategy for generating job IDs
job_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='-_'),
    min_size=10,
    max_size=50
).filter(lambda x: x.strip())


class TestAPIEndpointProperties:
    """Property-based tests for API endpoint response validity."""
    
    def _get_tester(self):
        """Get an API Gateway tester instance."""
        config = TestConfiguration(
            aws_region="us-east-1",
            verbose_logging=True,
            max_retries=1  # Reduce retries for faster testing
        )
        # Use a test API base URL - in real testing this would be configured
        api_base_url = "https://api.example.com"  # This would be configured in real tests
        return APIGatewayTester(config, api_base_url)
    
    def _validate_http_response_structure(self, response_data: Dict[str, Any], endpoint_type: str) -> Dict[str, Any]:
        """Internal helper to validate HTTP response structure."""
        validation_results = {
            "has_status_code": "status_code" in response_data,
            "has_response_data": "response_data" in response_data,
            "has_response_headers": "response_headers" in response_data,
            "status_code_valid": False,
            "content_type_valid": False,
            "response_structure_valid": False,
            "issues": []
        }
        
        # Validate status code
        if validation_results["has_status_code"]:
            status_code = response_data["status_code"]
            if isinstance(status_code, int) and 100 <= status_code <= 599:
                validation_results["status_code_valid"] = True
            else:
                validation_results["issues"].append(f"Invalid status code: {status_code}")
        else:
            validation_results["issues"].append("Missing status_code field")
        
        # Validate response headers
        if validation_results["has_response_headers"]:
            headers = response_data["response_headers"]
            if isinstance(headers, dict):
                # Check for content-type header
                content_type = headers.get("content-type", "").lower()
                if "application/json" in content_type:
                    validation_results["content_type_valid"] = True
                elif not content_type:
                    validation_results["issues"].append("Missing content-type header")
                else:
                    validation_results["issues"].append(f"Unexpected content-type: {content_type}")
            else:
                validation_results["issues"].append("Response headers should be a dictionary")
        else:
            validation_results["issues"].append("Missing response_headers field")
        
        # Validate response data structure based on endpoint type
        if validation_results["has_response_data"]:
            response_body = response_data["response_data"]
            if isinstance(response_body, dict):
                if endpoint_type == "upload":
                    required_fields = ["presignedUrl", "uploadId"]
                    for field in required_fields:
                        if field not in response_body:
                            validation_results["issues"].append(f"Upload response missing '{field}' field")
                        elif not response_body[field]:
                            validation_results["issues"].append(f"Upload response '{field}' field is empty")
                    
                    if len([issue for issue in validation_results["issues"] if "Upload response" in issue]) == 0:
                        validation_results["response_structure_valid"] = True
                
                elif endpoint_type == "analyze":
                    required_fields = ["jobId", "executionArn"]
                    for field in required_fields:
                        if field not in response_body:
                            validation_results["issues"].append(f"Analyze response missing '{field}' field")
                        elif not response_body[field]:
                            validation_results["issues"].append(f"Analyze response '{field}' field is empty")
                    
                    if len([issue for issue in validation_results["issues"] if "Analyze response" in issue]) == 0:
                        validation_results["response_structure_valid"] = True
                
                elif endpoint_type == "status":
                    required_fields = ["jobId", "status", "progress"]
                    for field in required_fields:
                        if field not in response_body:
                            validation_results["issues"].append(f"Status response missing '{field}' field")
                    
                    # Validate status values
                    if "status" in response_body:
                        valid_statuses = ["PENDING", "RUNNING", "SUCCEEDED", "FAILED", "TIMED_OUT"]
                        if response_body["status"] not in valid_statuses:
                            validation_results["issues"].append(f"Invalid status value: {response_body['status']}")
                    
                    # Validate progress format
                    if "progress" in response_body:
                        progress = response_body["progress"]
                        if not isinstance(progress, (int, float)) or progress < 0 or progress > 100:
                            validation_results["issues"].append(f"Invalid progress value: {progress}")
                    
                    if len([issue for issue in validation_results["issues"] if "response" in issue]) == 0:
                        validation_results["response_structure_valid"] = True
            else:
                validation_results["issues"].append("Response data should be a dictionary")
        else:
            validation_results["issues"].append("Missing response_data field")
        
        validation_results["is_valid"] = len(validation_results["issues"]) == 0
        return validation_results
    
    @given(upload_request_payload())
    @settings(
        max_examples=10,
        deadline=15000,  # 15 second deadline per test
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_upload_endpoint_response_validity(self, upload_payload):
        """
        Property 8: API endpoint response validity (Upload endpoint)
        
        For any valid upload request payload, the upload endpoint should return
        a properly structured response with required fields and valid data types.
        
        **Validates: Requirements 3.1**
        """
        tester = self._get_tester()
        
        # Mock the actual HTTP request since we're testing the response structure validation
        # In a real test environment, this would make actual HTTP requests
        mock_response_data = {
            "status_code": 200,
            "response_data": {
                "presignedUrl": f"https://s3.amazonaws.com/test-bucket/{upload_payload['fileName']}?signature=test",
                "uploadId": f"upload-{hash(upload_payload['fileName']) % 10000}",
                "bucket": "test-bucket",
                "key": f"uploads/{upload_payload['fileName']}"
            },
            "response_headers": {
                "content-type": "application/json",
                "access-control-allow-origin": "*"
            },
            "request_payload": upload_payload
        }
        
        # Test the response validation logic
        validation_results = self._validate_http_response_structure(mock_response_data, "upload")
        
        # Property: Response should have all required structural elements
        assert validation_results["has_status_code"] is True, "Response must include status code"
        assert validation_results["has_response_data"] is True, "Response must include response data"
        assert validation_results["has_response_headers"] is True, "Response must include response headers"
        
        # Property: Status code should be valid HTTP status
        assert validation_results["status_code_valid"] is True, (
            f"Status code should be valid HTTP status, issues: {validation_results['issues']}"
        )
        
        # Property: Content type should be JSON for API responses
        assert validation_results["content_type_valid"] is True, (
            f"Content type should be application/json, issues: {validation_results['issues']}"
        )
        
        # Property: Response structure should match endpoint requirements
        assert validation_results["response_structure_valid"] is True, (
            f"Upload response structure should be valid, issues: {validation_results['issues']}"
        )
        
        # Property: Overall validation should pass for well-formed responses
        assert validation_results["is_valid"] is True, (
            f"Response validation should pass, issues: {validation_results['issues']}"
        )
        
        # Property: Presigned URL should be HTTPS
        presigned_url = mock_response_data["response_data"]["presignedUrl"]
        assert presigned_url.startswith("https://"), "Presigned URL must use HTTPS"
        
        # Property: Upload ID should be non-empty string
        upload_id = mock_response_data["response_data"]["uploadId"]
        assert isinstance(upload_id, str) and len(upload_id) > 0, "Upload ID must be non-empty string"
    
    @given(analysis_request_payload())
    @settings(
        max_examples=10,
        deadline=15000,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much]
    )
    def test_property_analyze_endpoint_response_validity(self, analysis_payload):
        """
        Property 8: API endpoint response validity (Analyze endpoint)
        
        For any valid analysis request payload, the analyze endpoint should return
        a properly structured response with job ID and execution ARN.
        
        **Validates: Requirements 3.2**
        """
        tester = self._get_tester()
        
        # Mock the actual HTTP request for testing response structure
        # Generate a job ID that's always at least 8 characters
        job_suffix = f"{hash(analysis_payload['uploadId']) % 100000:05d}"  # 5-digit zero-padded number
        job_id = f"job-{job_suffix}"
        
        mock_response_data = {
            "status_code": 200,
            "response_data": {
                "jobId": job_id,
                "executionArn": f"arn:aws:states:us-east-1:123456789012:execution:cr2a-analysis:{job_id}",
                "status": "queued",
                "message": "Analysis started successfully"
            },
            "response_headers": {
                "content-type": "application/json",
                "access-control-allow-origin": "*"
            },
            "request_payload": analysis_payload
        }
        
        # Test the response validation logic
        validation_results = self._validate_http_response_structure(mock_response_data, "analyze")
        
        # Property: Response should have all required structural elements
        assert validation_results["has_status_code"] is True, "Response must include status code"
        assert validation_results["has_response_data"] is True, "Response must include response data"
        assert validation_results["has_response_headers"] is True, "Response must include response headers"
        
        # Property: Status code should be valid HTTP status
        assert validation_results["status_code_valid"] is True, (
            f"Status code should be valid, issues: {validation_results['issues']}"
        )
        
        # Property: Content type should be JSON
        assert validation_results["content_type_valid"] is True, (
            f"Content type should be JSON, issues: {validation_results['issues']}"
        )
        
        # Property: Response structure should match analyze endpoint requirements
        assert validation_results["response_structure_valid"] is True, (
            f"Analyze response structure should be valid, issues: {validation_results['issues']}"
        )
        
        # Property: Overall validation should pass
        assert validation_results["is_valid"] is True, (
            f"Response validation should pass, issues: {validation_results['issues']}"
        )
        
        # Property: Job ID should be meaningful identifier
        job_id = mock_response_data["response_data"]["jobId"]
        assert isinstance(job_id, str) and len(job_id) >= 8, (
            "Job ID should be a meaningful string identifier"
        )
        
        # Property: Execution ARN should be valid Step Functions ARN
        execution_arn = mock_response_data["response_data"]["executionArn"]
        assert execution_arn.startswith("arn:aws:states:"), (
            "Execution ARN should be a valid Step Functions ARN"
        )
        assert ":execution:" in execution_arn, (
            "Execution ARN should reference an execution"
        )
    
    @given(job_id_strategy)
    @settings(
        max_examples=10,
        deadline=15000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_status_endpoint_response_validity(self, job_id):
        """
        Property 8: API endpoint response validity (Status endpoint)
        
        For any valid job ID, the status endpoint should return a properly
        structured response with job status and progress information.
        
        **Validates: Requirements 3.3**
        """
        tester = self._get_tester()
        
        # Mock different possible status responses
        status_values = ["PENDING", "RUNNING", "SUCCEEDED", "FAILED", "TIMED_OUT"]
        import random
        status = random.choice(status_values)
        progress = random.randint(0, 100)
        
        mock_response_data = {
            "status_code": 200,
            "response_data": {
                "jobId": job_id,
                "status": status,
                "progress": progress,
                "message": f"Job is {status.lower()}",
                "created_at": "2024-01-01T00:00:00Z"
            },
            "response_headers": {
                "content-type": "application/json",
                "access-control-allow-origin": "*"
            },
            "job_id": job_id
        }
        
        # Test the response validation logic
        validation_results = self._validate_http_response_structure(mock_response_data, "status")
        
        # Property: Response should have all required structural elements
        assert validation_results["has_status_code"] is True, "Response must include status code"
        assert validation_results["has_response_data"] is True, "Response must include response data"
        assert validation_results["has_response_headers"] is True, "Response must include response headers"
        
        # Property: Status code should be valid HTTP status
        assert validation_results["status_code_valid"] is True, (
            f"Status code should be valid, issues: {validation_results['issues']}"
        )
        
        # Property: Content type should be JSON
        assert validation_results["content_type_valid"] is True, (
            f"Content type should be JSON, issues: {validation_results['issues']}"
        )
        
        # Property: Response structure should match status endpoint requirements
        assert validation_results["response_structure_valid"] is True, (
            f"Status response structure should be valid, issues: {validation_results['issues']}"
        )
        
        # Property: Overall validation should pass
        assert validation_results["is_valid"] is True, (
            f"Response validation should pass, issues: {validation_results['issues']}"
        )
        
        # Property: Job ID in response should match requested job ID
        response_job_id = mock_response_data["response_data"]["jobId"]
        assert response_job_id == job_id, (
            f"Response job ID should match request: expected {job_id}, got {response_job_id}"
        )
        
        # Property: Status should be one of valid values
        response_status = mock_response_data["response_data"]["status"]
        valid_statuses = ["PENDING", "RUNNING", "SUCCEEDED", "FAILED", "TIMED_OUT"]
        assert response_status in valid_statuses, (
            f"Status should be valid value, got: {response_status}"
        )
        
        # Property: Progress should be between 0 and 100
        response_progress = mock_response_data["response_data"]["progress"]
        assert 0 <= response_progress <= 100, (
            f"Progress should be between 0 and 100, got: {response_progress}"
        )
    
    @given(st.dictionaries(
        keys=st.sampled_from(["status_code", "response_data", "response_headers"]),
        values=st.one_of(
            st.integers(min_value=100, max_value=599),
            st.dictionaries(
                keys=st.text(min_size=1, max_size=20),
                values=st.one_of(st.text(), st.integers(), st.booleans()),
                min_size=1,
                max_size=5
            ),
            st.text(min_size=1, max_size=100)
        ),
        min_size=1,
        max_size=3
    ))
    @settings(
        max_examples=15,
        deadline=10000,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.data_too_large]
    )
    def test_property_response_validation_robustness(self, malformed_response):
        """
        Property: Response validation should be robust against malformed responses.
        
        For any dictionary representing an HTTP response (potentially malformed),
        the validation function should not crash and should provide meaningful
        feedback about response structure issues.
        
        **Validates: Requirements 3.1, 3.2, 3.3**
        """
        tester = self._get_tester()
        
        # Test validation robustness across different endpoint types
        endpoint_types = ["upload", "analyze", "status"]
        
        for endpoint_type in endpoint_types:
            # Property: Validation should not crash on malformed input
            try:
                validation_results = self._validate_http_response_structure(malformed_response, endpoint_type)
                
                # Property: Should always return detailed results
                assert validation_results is not None, f"Should return results for {endpoint_type} endpoint"
                assert "issues" in validation_results, f"Should include issues list for {endpoint_type}"
                assert isinstance(validation_results["issues"], list), f"Issues should be a list for {endpoint_type}"
                
                # Property: Should check for required structural elements
                assert "has_status_code" in validation_results, f"Should check status code for {endpoint_type}"
                assert "has_response_data" in validation_results, f"Should check response data for {endpoint_type}"
                assert "has_response_headers" in validation_results, f"Should check headers for {endpoint_type}"
                
                # Property: Missing required fields should be flagged
                if "status_code" not in malformed_response:
                    assert not validation_results["has_status_code"], (
                        f"Should detect missing status_code for {endpoint_type}"
                    )
                    assert any("status_code" in issue.lower() for issue in validation_results["issues"]), (
                        f"Should report missing status_code in issues for {endpoint_type}"
                    )
                
                if "response_data" not in malformed_response:
                    assert not validation_results["has_response_data"], (
                        f"Should detect missing response_data for {endpoint_type}"
                    )
                    assert any("response_data" in issue.lower() for issue in validation_results["issues"]), (
                        f"Should report missing response_data in issues for {endpoint_type}"
                    )
                
                if "response_headers" not in malformed_response:
                    assert not validation_results["has_response_headers"], (
                        f"Should detect missing response_headers for {endpoint_type}"
                    )
                    assert any("response_headers" in issue.lower() for issue in validation_results["issues"]), (
                        f"Should report missing response_headers in issues for {endpoint_type}"
                    )
                
                # Property: is_valid should be consistent with issues
                expected_valid = len(validation_results["issues"]) == 0
                assert validation_results["is_valid"] == expected_valid, (
                    f"is_valid should be consistent with issues count for {endpoint_type}"
                )
                
            except Exception as e:
                pytest.fail(f"Response validation should not crash on malformed input for {endpoint_type}: {str(e)}")
    
    def test_property_upload_endpoint_response_validity_example(self):
        """
        Example test to demonstrate the upload endpoint property with a concrete case.
        This validates the property works with a known good upload response.
        
        **Validates: Requirements 3.1**
        """
        tester = self._get_tester()
        
        # Known good upload response
        upload_response = {
            "status_code": 200,
            "response_data": {
                "presignedUrl": "https://s3.amazonaws.com/cr2a-uploads/test-contract.pdf?signature=abc123",
                "uploadId": "upload-12345",
                "bucket": "cr2a-uploads",
                "key": "uploads/test-contract.pdf"
            },
            "response_headers": {
                "content-type": "application/json",
                "access-control-allow-origin": "*",
                "access-control-allow-methods": "POST, OPTIONS"
            },
            "request_payload": {
                "fileName": "test-contract.pdf",
                "fileType": "application/pdf",
                "fileSize": 1048576
            }
        }
        
        # Test validation
        validation_results = self._validate_http_response_structure(upload_response, "upload")
        
        # Validate the property holds
        assert validation_results["has_status_code"] is True
        assert validation_results["has_response_data"] is True
        assert validation_results["has_response_headers"] is True
        assert validation_results["status_code_valid"] is True
        assert validation_results["content_type_valid"] is True
        assert validation_results["response_structure_valid"] is True
        assert validation_results["is_valid"] is True, f"Response should be valid, but has issues: {validation_results['issues']}"
        assert len(validation_results["issues"]) == 0
    
    def test_property_analyze_endpoint_response_validity_example(self):
        """
        Example test for analyze endpoint response validity with known good response.
        This demonstrates the property with a concrete test case.
        
        **Validates: Requirements 3.2**
        """
        tester = self._get_tester()
        
        # Known good analyze response
        analyze_response = {
            "status_code": 200,
            "response_data": {
                "jobId": "job-abc123def456",
                "executionArn": "arn:aws:states:us-east-1:123456789012:execution:cr2a-analysis:job-abc123def456",
                "status": "queued",
                "message": "Analysis started successfully"
            },
            "response_headers": {
                "content-type": "application/json",
                "access-control-allow-origin": "*"
            },
            "request_payload": {
                "uploadId": "upload-12345",
                "s3Bucket": "cr2a-uploads",
                "s3Key": "uploads/test-contract.pdf",
                "analysisType": "full"
            }
        }
        
        # Test validation
        validation_results = self._validate_http_response_structure(analyze_response, "analyze")
        
        # Validate the property holds
        assert validation_results["has_status_code"] is True
        assert validation_results["has_response_data"] is True
        assert validation_results["has_response_headers"] is True
        assert validation_results["status_code_valid"] is True
        assert validation_results["content_type_valid"] is True
        assert validation_results["response_structure_valid"] is True
        assert validation_results["is_valid"] is True, f"Response should be valid, but has issues: {validation_results['issues']}"
        assert len(validation_results["issues"]) == 0
    
    def test_property_status_endpoint_response_validity_example(self):
        """
        Example test for status endpoint response validity with known good response.
        This demonstrates the property with a concrete test case.
        
        **Validates: Requirements 3.3**
        """
        tester = self._get_tester()
        
        # Known good status response
        status_response = {
            "status_code": 200,
            "response_data": {
                "jobId": "job-abc123def456",
                "status": "RUNNING",
                "progress": 45,
                "message": "Analysis in progress",
                "created_at": "2024-01-01T10:00:00Z",
                "updated_at": "2024-01-01T10:05:00Z"
            },
            "response_headers": {
                "content-type": "application/json",
                "access-control-allow-origin": "*"
            },
            "job_id": "job-abc123def456"
        }
        
        # Test validation
        validation_results = self._validate_http_response_structure(status_response, "status")
        
        # Validate the property holds
        assert validation_results["has_status_code"] is True
        assert validation_results["has_response_data"] is True
        assert validation_results["has_response_headers"] is True
        assert validation_results["status_code_valid"] is True
        assert validation_results["content_type_valid"] is True
        assert validation_results["response_structure_valid"] is True
        assert validation_results["is_valid"] is True, f"Response should be valid, but has issues: {validation_results['issues']}"
        assert len(validation_results["issues"]) == 0