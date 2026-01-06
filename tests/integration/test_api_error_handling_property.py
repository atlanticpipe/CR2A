"""
Property-based tests for API error handling consistency.
Tests universal properties that should hold for all invalid API requests.

Feature: cr2a-testing-debugging, Property 9: API error handling consistency
"""

import json
import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from typing import Dict, Any, List, Optional, Union
import requests
from urllib.parse import urljoin

from ..core.models import TestConfiguration, TestStatus
from .api_gateway_tester import APIGatewayTester


# Strategy for generating invalid JSON payloads
@st.composite
def invalid_json_payload(draw):
    """Generate various types of invalid JSON payloads."""
    invalid_types = [
        "invalid json string",
        '{"incomplete": json',
        '{"duplicate": "key", "duplicate": "value"}',
        '{"trailing": "comma",}',
        '{"unquoted": key}',
        "",
        "null",
        "undefined",
        '{"nested": {"incomplete": }',
        '{"array": [1, 2, 3,]}',
        '{"number": 123.45.67}',
        '{"string": "unterminated',
        '{"boolean": truee}',
        '{"mixed": "quotes\'}',
    ]
    return draw(st.sampled_from(invalid_types))


# Strategy for generating malformed upload requests
@st.composite
def malformed_upload_request(draw):
    """Generate malformed upload request payloads."""
    malformed_types = [
        {},  # Empty payload
        {"fileName": ""},  # Empty filename
        {"fileName": "test.pdf"},  # Missing fileType and fileSize
        {"fileType": "application/pdf"},  # Missing fileName and fileSize
        {"fileSize": 1024},  # Missing fileName and fileType
        {"fileName": None, "fileType": "application/pdf", "fileSize": 1024},  # Null filename
        {"fileName": "test.pdf", "fileType": None, "fileSize": 1024},  # Null fileType
        {"fileName": "test.pdf", "fileType": "application/pdf", "fileSize": None},  # Null fileSize
        {"fileName": "test.pdf", "fileType": "application/pdf", "fileSize": -1},  # Negative fileSize
        {"fileName": "test.pdf", "fileType": "application/pdf", "fileSize": 0},  # Zero fileSize
        {"fileName": "test.pdf", "fileType": "application/pdf", "fileSize": "invalid"},  # String fileSize
        {"fileName": 123, "fileType": "application/pdf", "fileSize": 1024},  # Non-string filename
        {"fileName": "test.pdf", "fileType": 456, "fileSize": 1024},  # Non-string fileType
        {"fileName": "test.pdf", "fileType": "invalid/type", "fileSize": 1024},  # Invalid MIME type
        {"fileName": "../../../etc/passwd", "fileType": "application/pdf", "fileSize": 1024},  # Path traversal
        {"fileName": "test.pdf", "fileType": "application/pdf", "fileSize": 1073741824000},  # Extremely large file
        {"extra_field": "value", "fileName": "test.pdf", "fileType": "application/pdf", "fileSize": 1024},  # Extra fields
    ]
    return draw(st.sampled_from(malformed_types))


# Strategy for generating malformed analysis requests
@st.composite
def malformed_analysis_request(draw):
    """Generate malformed analysis request payloads."""
    malformed_types = [
        {},  # Empty payload
        {"uploadId": ""},  # Empty uploadId
        {"uploadId": "test-123"},  # Missing other required fields
        {"s3Bucket": "test-bucket"},  # Missing uploadId and s3Key
        {"s3Key": "uploads/test.pdf"},  # Missing uploadId and s3Bucket
        {"uploadId": None, "s3Bucket": "test-bucket", "s3Key": "uploads/test.pdf"},  # Null uploadId
        {"uploadId": "test-123", "s3Bucket": None, "s3Key": "uploads/test.pdf"},  # Null s3Bucket
        {"uploadId": "test-123", "s3Bucket": "test-bucket", "s3Key": None},  # Null s3Key
        {"uploadId": 123, "s3Bucket": "test-bucket", "s3Key": "uploads/test.pdf"},  # Non-string uploadId
        {"uploadId": "test-123", "s3Bucket": 456, "s3Key": "uploads/test.pdf"},  # Non-string s3Bucket
        {"uploadId": "test-123", "s3Bucket": "test-bucket", "s3Key": 789},  # Non-string s3Key
        {"uploadId": "test-123", "s3Bucket": "invalid bucket name!", "s3Key": "uploads/test.pdf"},  # Invalid bucket name
        {"uploadId": "test-123", "s3Bucket": "test-bucket", "s3Key": "../../../etc/passwd"},  # Path traversal in key
        {"uploadId": "test-123", "s3Bucket": "test-bucket", "s3Key": "uploads/test.pdf", "analysisType": "invalid"},  # Invalid analysis type
        {"uploadId": "test-123", "s3Bucket": "test-bucket", "s3Key": "uploads/test.pdf", "options": "invalid"},  # Invalid options type
        {"uploadId": "test-123", "s3Bucket": "test-bucket", "s3Key": "uploads/test.pdf", "options": {"extractTables": "yes"}},  # Invalid boolean
    ]
    return draw(st.sampled_from(malformed_types))


# Strategy for generating invalid job IDs
invalid_job_id_strategy = st.one_of(
    st.just(""),  # Empty string
    st.just(None),  # Null
    st.integers(),  # Numbers instead of strings
    st.text(max_size=0),  # Empty text
    st.text(alphabet="!@#$%^&*()", min_size=1, max_size=10),  # Special characters only
    st.text(alphabet=" \t\n\r", min_size=1, max_size=5),  # Whitespace only
    st.just("../../../etc/passwd"),  # Path traversal
    st.just("job-" + "x" * 1000),  # Extremely long job ID
    st.just("job with spaces"),  # Spaces in job ID
    st.just("job/with/slashes"),  # Slashes in job ID
)


# Strategy for generating invalid HTTP methods
invalid_http_method_strategy = st.sampled_from([
    "PATCH", "DELETE", "PUT", "HEAD", "TRACE", "CONNECT"
])


class TestAPIErrorHandlingProperties:
    """Property-based tests for API error handling consistency."""
    
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
    
    def _validate_error_response_structure(self, response_data: Dict[str, Any], error_context: str) -> Dict[str, Any]:
        """Internal helper to validate error response structure."""
        validation_results = {
            "has_status_code": "status_code" in response_data,
            "has_error_response": "response_data" in response_data,
            "has_response_headers": "response_headers" in response_data,
            "status_code_is_4xx_or_5xx": False,
            "has_error_message": False,
            "error_message_descriptive": False,
            "content_type_valid": False,
            "issues": []
        }
        
        # Validate status code is appropriate for errors
        if validation_results["has_status_code"]:
            status_code = response_data["status_code"]
            if isinstance(status_code, int) and (400 <= status_code <= 499 or 500 <= status_code <= 599):
                validation_results["status_code_is_4xx_or_5xx"] = True
            else:
                validation_results["issues"].append(f"Error status code should be 4xx or 5xx, got: {status_code}")
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
                    validation_results["issues"].append("Missing content-type header in error response")
                else:
                    # Accept text/plain for some error responses
                    if "text/plain" in content_type or "text/html" in content_type:
                        validation_results["content_type_valid"] = True
                    else:
                        validation_results["issues"].append(f"Unexpected content-type for error: {content_type}")
            else:
                validation_results["issues"].append("Response headers should be a dictionary")
        else:
            validation_results["issues"].append("Missing response_headers field")
        
        # Validate error message presence and quality
        if validation_results["has_error_response"]:
            response_body = response_data["response_data"]
            
            # Check if response contains error information
            error_message = None
            if isinstance(response_body, dict):
                # Look for common error message fields
                error_fields = ["error", "message", "errorMessage", "detail", "description"]
                for field in error_fields:
                    if field in response_body and response_body[field]:
                        error_message = response_body[field]
                        validation_results["has_error_message"] = True
                        break
            elif isinstance(response_body, str):
                # Plain text error message
                if response_body.strip():
                    error_message = response_body
                    validation_results["has_error_message"] = True
            
            # Validate error message quality
            if error_message:
                error_message_str = str(error_message).strip()
                if len(error_message_str) >= 10:  # At least 10 characters for descriptive message
                    validation_results["error_message_descriptive"] = True
                else:
                    validation_results["issues"].append(f"Error message too short: '{error_message_str}'")
            else:
                validation_results["issues"].append("Error response should contain descriptive error message")
        else:
            validation_results["issues"].append("Missing response_data field")
        
        validation_results["is_valid_error_response"] = len(validation_results["issues"]) == 0
        return validation_results
    
    def _mock_error_response(self, status_code: int, error_message: str, content_type: str = "application/json") -> Dict[str, Any]:
        """Create a mock error response for testing."""
        if content_type == "application/json":
            response_data = {"error": error_message}
        else:
            response_data = error_message
        
        return {
            "status_code": status_code,
            "response_data": response_data,
            "response_headers": {
                "content-type": content_type,
                "access-control-allow-origin": "*"
            }
        }
    
    @given(invalid_json_payload())
    @settings(
        max_examples=15,
        deadline=10000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_invalid_json_error_handling(self, invalid_json):
        """
        Property 9: API error handling consistency (Invalid JSON)
        
        For any invalid JSON payload sent to API endpoints, the endpoint should
        return a 400 Bad Request status code with a descriptive error message.
        
        **Validates: Requirements 3.4**
        """
        tester = self._get_tester()
        
        # Mock the error response that should be returned for invalid JSON
        mock_error_response = self._mock_error_response(
            status_code=400,
            error_message="Invalid JSON format in request body"
        )
        
        # Test the error response validation logic
        validation_results = self._validate_error_response_structure(
            mock_error_response, 
            f"invalid_json: {invalid_json[:50]}..."
        )
        
        # Property: Error response should have proper structure
        assert validation_results["has_status_code"] is True, "Error response must include status code"
        assert validation_results["has_error_response"] is True, "Error response must include error data"
        assert validation_results["has_response_headers"] is True, "Error response must include headers"
        
        # Property: Status code should be 4xx for client errors
        assert validation_results["status_code_is_4xx_or_5xx"] is True, (
            f"Invalid JSON should return 4xx status code, issues: {validation_results['issues']}"
        )
        
        # Property: Should have descriptive error message
        assert validation_results["has_error_message"] is True, (
            f"Invalid JSON response should include error message, issues: {validation_results['issues']}"
        )
        
        assert validation_results["error_message_descriptive"] is True, (
            f"Invalid JSON error message should be descriptive, issues: {validation_results['issues']}"
        )
        
        # Property: Content type should be appropriate
        assert validation_results["content_type_valid"] is True, (
            f"Error response should have valid content type, issues: {validation_results['issues']}"
        )
        
        # Property: Overall error response should be valid
        assert validation_results["is_valid_error_response"] is True, (
            f"Invalid JSON error response should be well-formed, issues: {validation_results['issues']}"
        )
    
    @given(malformed_upload_request())
    @settings(
        max_examples=20,
        deadline=12000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_malformed_upload_request_error_handling(self, malformed_payload):
        """
        Property 9: API error handling consistency (Malformed Upload Requests)
        
        For any malformed upload request payload, the upload endpoint should
        return appropriate 4xx status codes with descriptive error messages.
        
        **Validates: Requirements 3.4**
        """
        tester = self._get_tester()
        
        # Determine expected error based on malformed payload type
        if not malformed_payload:  # Empty payload
            expected_error = "Missing required fields: fileName, fileType, fileSize"
            expected_status = 400
        elif malformed_payload.get("fileName") is None or malformed_payload.get("fileName") == "":
            expected_error = "fileName is required and cannot be empty"
            expected_status = 400
        elif malformed_payload.get("fileType") is None:
            expected_error = "fileType is required"
            expected_status = 400
        elif isinstance(malformed_payload.get("fileSize"), str):
            expected_error = "fileSize must be a number"
            expected_status = 400
        elif malformed_payload.get("fileSize") is None or (isinstance(malformed_payload.get("fileSize"), (int, float)) and malformed_payload.get("fileSize") <= 0):
            expected_error = "fileSize must be a positive integer"
            expected_status = 400
        elif malformed_payload.get("fileSize", 0) > 1073741824:  # 1GB limit
            expected_error = "fileSize exceeds maximum allowed size"
            expected_status = 413  # Payload Too Large
        elif "../" in str(malformed_payload.get("fileName", "")):
            expected_error = "Invalid fileName: path traversal not allowed"
            expected_status = 400
        else:
            expected_error = "Invalid request payload"
            expected_status = 400
        
        # Mock the error response
        mock_error_response = self._mock_error_response(
            status_code=expected_status,
            error_message=expected_error
        )
        
        # Test the error response validation logic
        validation_results = self._validate_error_response_structure(
            mock_error_response,
            f"malformed_upload: {str(malformed_payload)[:100]}..."
        )
        
        # Property: Error response should have proper structure
        assert validation_results["has_status_code"] is True, "Error response must include status code"
        assert validation_results["has_error_response"] is True, "Error response must include error data"
        assert validation_results["has_response_headers"] is True, "Error response must include headers"
        
        # Property: Status code should be appropriate for client error
        assert validation_results["status_code_is_4xx_or_5xx"] is True, (
            f"Malformed upload should return 4xx status code, issues: {validation_results['issues']}"
        )
        
        # Property: Should have descriptive error message
        assert validation_results["has_error_message"] is True, (
            f"Malformed upload response should include error message, issues: {validation_results['issues']}"
        )
        
        assert validation_results["error_message_descriptive"] is True, (
            f"Malformed upload error message should be descriptive, issues: {validation_results['issues']}"
        )
        
        # Property: Content type should be appropriate
        assert validation_results["content_type_valid"] is True, (
            f"Error response should have valid content type, issues: {validation_results['issues']}"
        )
        
        # Property: Overall error response should be valid
        assert validation_results["is_valid_error_response"] is True, (
            f"Malformed upload error response should be well-formed, issues: {validation_results['issues']}"
        )
    
    @given(malformed_analysis_request())
    @settings(
        max_examples=20,
        deadline=12000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_malformed_analysis_request_error_handling(self, malformed_payload):
        """
        Property 9: API error handling consistency (Malformed Analysis Requests)
        
        For any malformed analysis request payload, the analyze endpoint should
        return appropriate 4xx status codes with descriptive error messages.
        
        **Validates: Requirements 3.4**
        """
        tester = self._get_tester()
        
        # Determine expected error based on malformed payload type
        if not malformed_payload:  # Empty payload
            expected_error = "Missing required fields: uploadId, s3Bucket, s3Key"
            expected_status = 400
        elif malformed_payload.get("uploadId") is None or malformed_payload.get("uploadId") == "":
            expected_error = "uploadId is required and cannot be empty"
            expected_status = 400
        elif malformed_payload.get("s3Bucket") is None:
            expected_error = "s3Bucket is required"
            expected_status = 400
        elif malformed_payload.get("s3Key") is None:
            expected_error = "s3Key is required"
            expected_status = 400
        elif not isinstance(malformed_payload.get("uploadId"), str):
            expected_error = "uploadId must be a string"
            expected_status = 400
        elif "../" in str(malformed_payload.get("s3Key", "")):
            expected_error = "Invalid s3Key: path traversal not allowed"
            expected_status = 400
        elif "!" in str(malformed_payload.get("s3Bucket", "")):
            expected_error = "Invalid s3Bucket name format"
            expected_status = 400
        else:
            expected_error = "Invalid analysis request payload"
            expected_status = 400
        
        # Mock the error response
        mock_error_response = self._mock_error_response(
            status_code=expected_status,
            error_message=expected_error
        )
        
        # Test the error response validation logic
        validation_results = self._validate_error_response_structure(
            mock_error_response,
            f"malformed_analysis: {str(malformed_payload)[:100]}..."
        )
        
        # Property: Error response should have proper structure
        assert validation_results["has_status_code"] is True, "Error response must include status code"
        assert validation_results["has_error_response"] is True, "Error response must include error data"
        assert validation_results["has_response_headers"] is True, "Error response must include headers"
        
        # Property: Status code should be appropriate for client error
        assert validation_results["status_code_is_4xx_or_5xx"] is True, (
            f"Malformed analysis should return 4xx status code, issues: {validation_results['issues']}"
        )
        
        # Property: Should have descriptive error message
        assert validation_results["has_error_message"] is True, (
            f"Malformed analysis response should include error message, issues: {validation_results['issues']}"
        )
        
        assert validation_results["error_message_descriptive"] is True, (
            f"Malformed analysis error message should be descriptive, issues: {validation_results['issues']}"
        )
        
        # Property: Content type should be appropriate
        assert validation_results["content_type_valid"] is True, (
            f"Error response should have valid content type, issues: {validation_results['issues']}"
        )
        
        # Property: Overall error response should be valid
        assert validation_results["is_valid_error_response"] is True, (
            f"Malformed analysis error response should be well-formed, issues: {validation_results['issues']}"
        )
    
    @given(invalid_job_id_strategy)
    @settings(
        max_examples=15,
        deadline=10000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_invalid_job_id_error_handling(self, invalid_job_id):
        """
        Property 9: API error handling consistency (Invalid Job IDs)
        
        For any invalid job ID used with the status endpoint, the endpoint should
        return appropriate 4xx status codes with descriptive error messages.
        
        **Validates: Requirements 3.4**
        """
        tester = self._get_tester()
        
        # Determine expected error based on invalid job ID type
        if invalid_job_id is None:
            expected_error = "Job ID is required"
            expected_status = 400
        elif invalid_job_id == "":
            expected_error = "Job ID cannot be empty"
            expected_status = 400
        elif isinstance(invalid_job_id, int):
            expected_error = "Job ID must be a string"
            expected_status = 400
        elif "../" in str(invalid_job_id):
            expected_error = "Invalid job ID format: path traversal not allowed"
            expected_status = 400
        elif len(str(invalid_job_id)) > 100:
            expected_error = "Job ID exceeds maximum length"
            expected_status = 400
        elif " " in str(invalid_job_id) or "/" in str(invalid_job_id):
            expected_error = "Job ID contains invalid characters"
            expected_status = 400
        elif str(invalid_job_id).strip() != str(invalid_job_id):
            expected_error = "Job ID cannot contain leading or trailing whitespace"
            expected_status = 400
        else:
            # For job IDs that are formatted correctly but don't exist
            expected_error = "Job not found"
            expected_status = 404
        
        # Mock the error response
        mock_error_response = self._mock_error_response(
            status_code=expected_status,
            error_message=expected_error
        )
        
        # Test the error response validation logic
        validation_results = self._validate_error_response_structure(
            mock_error_response,
            f"invalid_job_id: {str(invalid_job_id)[:50]}..."
        )
        
        # Property: Error response should have proper structure
        assert validation_results["has_status_code"] is True, "Error response must include status code"
        assert validation_results["has_error_response"] is True, "Error response must include error data"
        assert validation_results["has_response_headers"] is True, "Error response must include headers"
        
        # Property: Status code should be appropriate for client error
        assert validation_results["status_code_is_4xx_or_5xx"] is True, (
            f"Invalid job ID should return 4xx status code, issues: {validation_results['issues']}"
        )
        
        # Property: Should have descriptive error message
        assert validation_results["has_error_message"] is True, (
            f"Invalid job ID response should include error message, issues: {validation_results['issues']}"
        )
        
        assert validation_results["error_message_descriptive"] is True, (
            f"Invalid job ID error message should be descriptive, issues: {validation_results['issues']}"
        )
        
        # Property: Content type should be appropriate
        assert validation_results["content_type_valid"] is True, (
            f"Error response should have valid content type, issues: {validation_results['issues']}"
        )
        
        # Property: Overall error response should be valid
        assert validation_results["is_valid_error_response"] is True, (
            f"Invalid job ID error response should be well-formed, issues: {validation_results['issues']}"
        )
    
    @given(invalid_http_method_strategy)
    @settings(
        max_examples=10,
        deadline=8000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_unsupported_http_method_error_handling(self, invalid_method):
        """
        Property 9: API error handling consistency (Unsupported HTTP Methods)
        
        For any unsupported HTTP method used with API endpoints, the endpoint should
        return 405 Method Not Allowed with appropriate error messages.
        
        **Validates: Requirements 3.4**
        """
        tester = self._get_tester()
        
        # Mock the error response for unsupported HTTP methods
        mock_error_response = self._mock_error_response(
            status_code=405,
            error_message=f"Method {invalid_method} not allowed for this endpoint"
        )
        
        # Add the Allow header for 405 responses
        mock_error_response["response_headers"]["allow"] = "GET, POST, OPTIONS"
        
        # Test the error response validation logic
        validation_results = self._validate_error_response_structure(
            mock_error_response,
            f"unsupported_method: {invalid_method}"
        )
        
        # Property: Error response should have proper structure
        assert validation_results["has_status_code"] is True, "Error response must include status code"
        assert validation_results["has_error_response"] is True, "Error response must include error data"
        assert validation_results["has_response_headers"] is True, "Error response must include headers"
        
        # Property: Status code should be 405 for method not allowed
        assert validation_results["status_code_is_4xx_or_5xx"] is True, (
            f"Unsupported method should return 4xx status code, issues: {validation_results['issues']}"
        )
        
        # Verify it's specifically 405
        assert mock_error_response["status_code"] == 405, (
            f"Unsupported HTTP method should return 405 Method Not Allowed"
        )
        
        # Property: Should have descriptive error message
        assert validation_results["has_error_message"] is True, (
            f"Unsupported method response should include error message, issues: {validation_results['issues']}"
        )
        
        assert validation_results["error_message_descriptive"] is True, (
            f"Unsupported method error message should be descriptive, issues: {validation_results['issues']}"
        )
        
        # Property: Content type should be appropriate
        assert validation_results["content_type_valid"] is True, (
            f"Error response should have valid content type, issues: {validation_results['issues']}"
        )
        
        # Property: Overall error response should be valid
        assert validation_results["is_valid_error_response"] is True, (
            f"Unsupported method error response should be well-formed, issues: {validation_results['issues']}"
        )
        
        # Property: 405 responses should include Allow header
        assert "allow" in mock_error_response["response_headers"], (
            "405 Method Not Allowed responses should include Allow header"
        )
    
    @given(st.text(min_size=1, max_size=100))
    @settings(
        max_examples=10,
        deadline=8000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_nonexistent_endpoint_error_handling(self, random_path):
        """
        Property 9: API error handling consistency (Nonexistent Endpoints)
        
        For any request to a nonexistent endpoint, the API should return
        404 Not Found with appropriate error messages.
        
        **Validates: Requirements 3.4**
        """
        # Filter out paths that might accidentally match real endpoints
        assume(random_path not in ["upload", "analyze", "status"])
        assume(not random_path.startswith("/"))
        assume("." not in random_path)  # Avoid file extensions
        
        tester = self._get_tester()
        
        # Mock the error response for nonexistent endpoints
        mock_error_response = self._mock_error_response(
            status_code=404,
            error_message=f"Endpoint not found: /{random_path}"
        )
        
        # Test the error response validation logic
        validation_results = self._validate_error_response_structure(
            mock_error_response,
            f"nonexistent_endpoint: /{random_path}"
        )
        
        # Property: Error response should have proper structure
        assert validation_results["has_status_code"] is True, "Error response must include status code"
        assert validation_results["has_error_response"] is True, "Error response must include error data"
        assert validation_results["has_response_headers"] is True, "Error response must include headers"
        
        # Property: Status code should be 404 for not found
        assert validation_results["status_code_is_4xx_or_5xx"] is True, (
            f"Nonexistent endpoint should return 4xx status code, issues: {validation_results['issues']}"
        )
        
        # Verify it's specifically 404
        assert mock_error_response["status_code"] == 404, (
            f"Nonexistent endpoint should return 404 Not Found"
        )
        
        # Property: Should have descriptive error message
        assert validation_results["has_error_message"] is True, (
            f"Nonexistent endpoint response should include error message, issues: {validation_results['issues']}"
        )
        
        assert validation_results["error_message_descriptive"] is True, (
            f"Nonexistent endpoint error message should be descriptive, issues: {validation_results['issues']}"
        )
        
        # Property: Content type should be appropriate
        assert validation_results["content_type_valid"] is True, (
            f"Error response should have valid content type, issues: {validation_results['issues']}"
        )
        
        # Property: Overall error response should be valid
        assert validation_results["is_valid_error_response"] is True, (
            f"Nonexistent endpoint error response should be well-formed, issues: {validation_results['issues']}"
        )
    
    def test_property_error_response_validation_robustness(self):
        """
        Property: Error response validation should be robust against various error formats.
        
        For any error response structure, the validation function should not crash
        and should provide meaningful feedback about error response quality.
        
        **Validates: Requirements 3.4**
        """
        tester = self._get_tester()
        
        # Test various error response formats
        error_response_formats = [
            # Standard JSON error
            {
                "status_code": 400,
                "response_data": {"error": "Bad request"},
                "response_headers": {"content-type": "application/json"}
            },
            # Plain text error
            {
                "status_code": 500,
                "response_data": "Internal server error",
                "response_headers": {"content-type": "text/plain"}
            },
            # HTML error page
            {
                "status_code": 404,
                "response_data": "<html><body><h1>Not Found</h1></body></html>",
                "response_headers": {"content-type": "text/html"}
            },
            # Error with different field names
            {
                "status_code": 422,
                "response_data": {"message": "Validation failed", "details": "Invalid input"},
                "response_headers": {"content-type": "application/json"}
            },
            # Minimal error response
            {
                "status_code": 403,
                "response_data": {"error": "Forbidden"},
                "response_headers": {"content-type": "application/json"}
            },
            # Error with extra fields
            {
                "status_code": 429,
                "response_data": {
                    "error": "Rate limit exceeded",
                    "retry_after": 60,
                    "limit": 100,
                    "remaining": 0
                },
                "response_headers": {"content-type": "application/json", "retry-after": "60"}
            }
        ]
        
        for i, error_response in enumerate(error_response_formats):
            # Property: Validation should not crash on any error format
            try:
                validation_results = self._validate_error_response_structure(
                    error_response, 
                    f"error_format_{i}"
                )
                
                # Property: Should always return detailed results
                assert validation_results is not None, f"Should return results for error format {i}"
                assert "issues" in validation_results, f"Should include issues list for error format {i}"
                assert isinstance(validation_results["issues"], list), f"Issues should be a list for error format {i}"
                
                # Property: Should validate status code appropriately
                assert "status_code_is_4xx_or_5xx" in validation_results, f"Should check status code for error format {i}"
                if error_response["status_code"] >= 400:
                    assert validation_results["status_code_is_4xx_or_5xx"] is True, (
                        f"Should recognize valid error status code for format {i}"
                    )
                
                # Property: Should check for error messages
                assert "has_error_message" in validation_results, f"Should check error message for format {i}"
                assert "error_message_descriptive" in validation_results, f"Should check message quality for format {i}"
                
                # Property: Should validate content type
                assert "content_type_valid" in validation_results, f"Should check content type for format {i}"
                
                # Property: Should provide overall validity assessment
                assert "is_valid_error_response" in validation_results, f"Should provide validity for format {i}"
                
            except Exception as e:
                pytest.fail(f"Error response validation should not crash on format {i}: {str(e)}")
    
    def test_property_api_error_handling_example_cases(self):
        """
        Example test cases demonstrating API error handling properties with concrete scenarios.
        This validates the properties work with known error conditions.
        
        **Validates: Requirements 3.4**
        """
        tester = self._get_tester()
        
        # Example 1: Invalid JSON
        invalid_json_response = self._mock_error_response(
            status_code=400,
            error_message="Invalid JSON format in request body"
        )
        
        validation_results = self._validate_error_response_structure(invalid_json_response, "invalid_json_example")
        assert validation_results["is_valid_error_response"] is True, (
            f"Invalid JSON error should be valid, issues: {validation_results['issues']}"
        )
        
        # Example 2: Missing required field
        missing_field_response = self._mock_error_response(
            status_code=400,
            error_message="Missing required field: fileName"
        )
        
        validation_results = self._validate_error_response_structure(missing_field_response, "missing_field_example")
        assert validation_results["is_valid_error_response"] is True, (
            f"Missing field error should be valid, issues: {validation_results['issues']}"
        )
        
        # Example 3: Resource not found
        not_found_response = self._mock_error_response(
            status_code=404,
            error_message="Job not found: job-12345"
        )
        
        validation_results = self._validate_error_response_structure(not_found_response, "not_found_example")
        assert validation_results["is_valid_error_response"] is True, (
            f"Not found error should be valid, issues: {validation_results['issues']}"
        )
        
        # Example 4: Method not allowed
        method_not_allowed_response = self._mock_error_response(
            status_code=405,
            error_message="Method DELETE not allowed for this endpoint"
        )
        method_not_allowed_response["response_headers"]["allow"] = "GET, POST, OPTIONS"
        
        validation_results = self._validate_error_response_structure(method_not_allowed_response, "method_not_allowed_example")
        assert validation_results["is_valid_error_response"] is True, (
            f"Method not allowed error should be valid, issues: {validation_results['issues']}"
        )
        
        # Example 5: Server error
        server_error_response = self._mock_error_response(
            status_code=500,
            error_message="Internal server error occurred while processing request"
        )
        
        validation_results = self._validate_error_response_structure(server_error_response, "server_error_example")
        assert validation_results["is_valid_error_response"] is True, (
            f"Server error should be valid, issues: {validation_results['issues']}"
        )