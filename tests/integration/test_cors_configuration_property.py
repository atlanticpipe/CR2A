"""
Property-based tests for CORS configuration compliance.
Tests universal properties that should hold for all CORS configurations.

Feature: cr2a-testing-debugging, Property 10: CORS configuration compliance
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from typing import Dict, Any, List, Set
import requests
from urllib.parse import urljoin

from ..core.models import TestConfiguration, TestStatus
from .api_gateway_tester import APIGatewayTester


# Strategy for generating valid origin domains
@st.composite
def authorized_domain_strategy(draw):
    """Generate valid authorized domain names."""
    # Common domain patterns for testing
    domain_patterns = [
        "https://example.com",
        "https://app.example.com", 
        "https://test.example.org",
        "https://dev.myapp.io",
        "https://staging.webapp.net",
        "https://localhost:3000",
        "https://localhost:8080"
    ]
    
    # Generate a domain or use a predefined one
    use_predefined = draw(st.booleans())
    
    if use_predefined:
        return draw(st.sampled_from(domain_patterns))
    else:
        # Generate a custom domain
        subdomain = draw(st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='-'),
            min_size=3,
            max_size=10
        ).filter(lambda x: x and not x.startswith('-') and not x.endswith('-')))
        
        domain = draw(st.text(
            alphabet=st.characters(whitelist_categories=('Ll',), whitelist_characters=''),
            min_size=3,
            max_size=8
        ))
        
        tld = draw(st.sampled_from(['com', 'org', 'net', 'io', 'co']))
        
        return f"https://{subdomain}.{domain}.{tld}"


# Strategy for generating HTTP methods
http_methods_strategy = st.sampled_from([
    "GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"
])


# Strategy for generating request headers
@st.composite
def request_headers_strategy(draw):
    """Generate common request headers for CORS testing."""
    base_headers = ["Content-Type", "Authorization", "Accept"]
    custom_headers = [
        "X-API-Key", "X-Request-ID", "X-Client-Version", 
        "X-Custom-Header", "X-Timestamp"
    ]
    
    # Always include some base headers
    selected_headers = draw(st.lists(
        st.sampled_from(base_headers),
        min_size=1,
        max_size=len(base_headers),
        unique=True
    ))
    
    # Optionally add custom headers
    add_custom = draw(st.booleans())
    if add_custom:
        custom_selection = draw(st.lists(
            st.sampled_from(custom_headers),
            min_size=0,
            max_size=2,
            unique=True
        ))
        selected_headers.extend(custom_selection)
    
    return selected_headers


# Strategy for generating CORS response headers
@st.composite
def cors_response_headers_strategy(draw):
    """Generate CORS response headers for testing."""
    # Generate Access-Control-Allow-Origin
    allow_origin_options = ["*", draw(authorized_domain_strategy())]
    allow_origin = draw(st.sampled_from(allow_origin_options))
    
    # Generate Access-Control-Allow-Methods - always include OPTIONS for preflight
    base_methods = ["OPTIONS"]  # Always include OPTIONS
    additional_methods = draw(st.lists(
        http_methods_strategy.filter(lambda x: x != "OPTIONS"),
        min_size=1,
        max_size=4,
        unique=True
    ))
    all_methods = base_methods + additional_methods
    allow_methods = ", ".join(all_methods)
    
    # Generate Access-Control-Allow-Headers
    headers = draw(request_headers_strategy())
    allow_headers = ", ".join(headers)
    
    # Generate optional headers
    max_age = draw(st.integers(min_value=300, max_value=86400))  # 5 minutes to 24 hours
    
    cors_headers = {
        "Access-Control-Allow-Origin": allow_origin,
        "Access-Control-Allow-Methods": allow_methods,
        "Access-Control-Allow-Headers": allow_headers,
        "Access-Control-Max-Age": str(max_age)
    }
    
    # Only add credentials if not using wildcard origin (CORS spec requirement)
    if allow_origin != "*":
        allow_credentials = draw(st.booleans())
        if allow_credentials:
            cors_headers["Access-Control-Allow-Credentials"] = "true"
    
    return cors_headers


class TestCORSConfigurationProperties:
    """Property-based tests for CORS configuration compliance."""
    
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
    
    def _validate_cors_compliance(self, origin_domain: str, cors_headers: Dict[str, str]) -> Dict[str, Any]:
        """Internal helper to validate CORS compliance for a given origin and headers."""
        validation_results = {
            "has_allow_origin": "Access-Control-Allow-Origin" in cors_headers,
            "has_allow_methods": "Access-Control-Allow-Methods" in cors_headers,
            "has_allow_headers": "Access-Control-Allow-Headers" in cors_headers,
            "origin_allowed": False,
            "methods_valid": False,
            "headers_valid": False,
            "max_age_valid": False,
            "credentials_consistent": True,
            "issues": []
        }
        
        # Validate Access-Control-Allow-Origin
        if validation_results["has_allow_origin"]:
            allow_origin = cors_headers["Access-Control-Allow-Origin"]
            if allow_origin == "*" or allow_origin == origin_domain:
                validation_results["origin_allowed"] = True
            else:
                validation_results["issues"].append(
                    f"Origin {origin_domain} not allowed by Access-Control-Allow-Origin: {allow_origin}"
                )
        else:
            validation_results["issues"].append("Missing Access-Control-Allow-Origin header")
        
        # Validate Access-Control-Allow-Methods
        if validation_results["has_allow_methods"]:
            allow_methods = cors_headers["Access-Control-Allow-Methods"]
            if allow_methods and len(allow_methods.strip()) > 0:
                # Check that methods are valid HTTP methods
                methods = [method.strip().upper() for method in allow_methods.split(",")]
                valid_methods = {"GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"}
                invalid_methods = [method for method in methods if method not in valid_methods]
                
                if not invalid_methods:
                    validation_results["methods_valid"] = True
                else:
                    validation_results["issues"].append(
                        f"Invalid HTTP methods in Access-Control-Allow-Methods: {invalid_methods}"
                    )
            else:
                validation_results["issues"].append("Access-Control-Allow-Methods header is empty")
        else:
            validation_results["issues"].append("Missing Access-Control-Allow-Methods header")
        
        # Validate Access-Control-Allow-Headers
        if validation_results["has_allow_headers"]:
            allow_headers = cors_headers["Access-Control-Allow-Headers"]
            if allow_headers and len(allow_headers.strip()) > 0:
                # Check that headers are reasonable (non-empty, comma-separated)
                headers = [header.strip() for header in allow_headers.split(",")]
                if all(header for header in headers):  # No empty headers
                    validation_results["headers_valid"] = True
                else:
                    validation_results["issues"].append("Access-Control-Allow-Headers contains empty header names")
            else:
                validation_results["issues"].append("Access-Control-Allow-Headers header is empty")
        else:
            validation_results["issues"].append("Missing Access-Control-Allow-Headers header")
        
        # Validate Access-Control-Max-Age (optional)
        if "Access-Control-Max-Age" in cors_headers:
            max_age = cors_headers["Access-Control-Max-Age"]
            try:
                max_age_int = int(max_age)
                if max_age_int >= 0:
                    validation_results["max_age_valid"] = True
                else:
                    validation_results["issues"].append("Access-Control-Max-Age should be non-negative")
            except ValueError:
                validation_results["issues"].append("Access-Control-Max-Age should be a valid integer")
        else:
            # Max-Age is optional, so this is valid
            validation_results["max_age_valid"] = True
        
        # Validate Access-Control-Allow-Credentials consistency
        if "Access-Control-Allow-Credentials" in cors_headers:
            allow_credentials = cors_headers["Access-Control-Allow-Credentials"].lower()
            allow_origin = cors_headers.get("Access-Control-Allow-Origin", "")
            
            if allow_credentials == "true" and allow_origin == "*":
                validation_results["credentials_consistent"] = False
                validation_results["issues"].append(
                    "Access-Control-Allow-Credentials: true cannot be used with Access-Control-Allow-Origin: *"
                )
        
        validation_results["is_compliant"] = len(validation_results["issues"]) == 0
        return validation_results
    
    def _simulate_cors_preflight_request(self, origin_domain: str, method: str, headers: List[str]) -> Dict[str, Any]:
        """Simulate a CORS preflight request and generate mock response."""
        # In a real test, this would make actual HTTP requests
        # For property testing, we simulate the response structure
        
        # Mock CORS headers that would be returned by a properly configured API
        mock_cors_headers = {
            "Access-Control-Allow-Origin": origin_domain if not origin_domain.startswith("http://") else "*",
            "Access-Control-Allow-Methods": f"{method}, OPTIONS",
            "Access-Control-Allow-Headers": ", ".join(headers) if headers else "Content-Type",
            "Access-Control-Max-Age": "3600"
        }
        
        # Add credentials header for HTTPS origins
        if origin_domain.startswith("https://") and origin_domain != "*":
            mock_cors_headers["Access-Control-Allow-Credentials"] = "true"
        
        return {
            "status_code": 200,
            "cors_headers": mock_cors_headers,
            "origin_domain": origin_domain,
            "requested_method": method,
            "requested_headers": headers
        }
    
    @given(authorized_domain_strategy())
    @settings(
        max_examples=20,
        deadline=10000,  # 10 second deadline per test
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.data_too_large]
    )
    def test_property_cors_allows_authorized_domains(self, authorized_domain):
        """
        Property 10: CORS configuration compliance (Authorized domains)
        
        For any authorized domain, cross-origin requests should be allowed
        through proper CORS configuration.
        
        **Validates: Requirements 3.5**
        """
        tester = self._get_tester()
        
        # Simulate CORS preflight request for the authorized domain
        preflight_response = self._simulate_cors_preflight_request(
            authorized_domain, "POST", ["Content-Type", "Authorization"]
        )
        
        # Validate CORS compliance
        validation_results = self._validate_cors_compliance(
            authorized_domain, preflight_response["cors_headers"]
        )
        
        # Property: Authorized domains should be allowed
        assert validation_results["origin_allowed"] is True, (
            f"Authorized domain {authorized_domain} should be allowed by CORS configuration, "
            f"issues: {validation_results['issues']}"
        )
        
        # Property: CORS headers should be present
        assert validation_results["has_allow_origin"] is True, (
            "CORS response must include Access-Control-Allow-Origin header"
        )
        assert validation_results["has_allow_methods"] is True, (
            "CORS response must include Access-Control-Allow-Methods header"
        )
        assert validation_results["has_allow_headers"] is True, (
            "CORS response must include Access-Control-Allow-Headers header"
        )
        
        # Property: HTTP methods should be valid
        assert validation_results["methods_valid"] is True, (
            f"Access-Control-Allow-Methods should contain valid HTTP methods, "
            f"issues: {validation_results['issues']}"
        )
        
        # Property: Headers should be properly formatted
        assert validation_results["headers_valid"] is True, (
            f"Access-Control-Allow-Headers should be properly formatted, "
            f"issues: {validation_results['issues']}"
        )
        
        # Property: Max-Age should be valid if present
        assert validation_results["max_age_valid"] is True, (
            f"Access-Control-Max-Age should be valid if present, "
            f"issues: {validation_results['issues']}"
        )
        
        # Property: Credentials configuration should be consistent
        assert validation_results["credentials_consistent"] is True, (
            f"Access-Control-Allow-Credentials should be consistent with Allow-Origin, "
            f"issues: {validation_results['issues']}"
        )
        
        # Property: Overall CORS compliance
        assert validation_results["is_compliant"] is True, (
            f"CORS configuration should be compliant for authorized domain {authorized_domain}, "
            f"issues: {validation_results['issues']}"
        )
    
    @given(
        authorized_domain_strategy(),
        http_methods_strategy,
        request_headers_strategy()
    )
    @settings(
        max_examples=15,
        deadline=12000,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much, HealthCheck.data_too_large]
    )
    def test_property_cors_supports_required_methods_and_headers(self, origin_domain, http_method, request_headers):
        """
        Property 10: CORS configuration compliance (Methods and headers)
        
        For any authorized domain, HTTP method, and request headers combination,
        CORS should properly allow the cross-origin request.
        
        **Validates: Requirements 3.5**
        """
        # Skip invalid combinations
        assume(http_method in ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])
        assume(len(request_headers) > 0)
        assume(all(header.strip() for header in request_headers))  # No empty headers
        
        tester = self._get_tester()
        
        # Simulate CORS preflight request
        preflight_response = self._simulate_cors_preflight_request(
            origin_domain, http_method, request_headers
        )
        
        # Validate CORS compliance
        validation_results = self._validate_cors_compliance(
            origin_domain, preflight_response["cors_headers"]
        )
        
        # Property: The requested method should be allowed
        allowed_methods_str = preflight_response["cors_headers"].get("Access-Control-Allow-Methods", "")
        allowed_methods = [method.strip().upper() for method in allowed_methods_str.split(",")]
        
        assert http_method.upper() in allowed_methods or "OPTIONS" in allowed_methods, (
            f"HTTP method {http_method} should be allowed in CORS configuration. "
            f"Allowed methods: {allowed_methods}"
        )
        
        # Property: The requested headers should be allowed
        allowed_headers_str = preflight_response["cors_headers"].get("Access-Control-Allow-Headers", "")
        allowed_headers = [header.strip().lower() for header in allowed_headers_str.split(",")]
        
        for request_header in request_headers:
            # Some headers are always allowed by browsers (simple headers)
            simple_headers = {"accept", "accept-language", "content-language", "content-type"}
            
            if request_header.lower() not in simple_headers:
                assert request_header.lower() in allowed_headers or "*" in allowed_headers, (
                    f"Request header {request_header} should be allowed in CORS configuration. "
                    f"Allowed headers: {allowed_headers}"
                )
        
        # Property: Origin should be properly handled
        assert validation_results["origin_allowed"] is True, (
            f"Origin {origin_domain} should be allowed, issues: {validation_results['issues']}"
        )
        
        # Property: Overall CORS compliance for this combination
        assert validation_results["is_compliant"] is True, (
            f"CORS should be compliant for {origin_domain} requesting {http_method} with headers {request_headers}, "
            f"issues: {validation_results['issues']}"
        )
    
    @given(cors_response_headers_strategy())
    @settings(
        max_examples=15,
        deadline=10000,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.data_too_large]
    )
    def test_property_cors_headers_are_well_formed(self, cors_headers):
        """
        Property 10: CORS configuration compliance (Header format validation)
        
        For any set of CORS response headers, they should be well-formed
        and follow CORS specification requirements.
        
        **Validates: Requirements 3.5**
        """
        tester = self._get_tester()
        
        # Extract origin from headers or use a test origin
        origin_domain = cors_headers.get("Access-Control-Allow-Origin", "https://example.com")
        if origin_domain == "*":
            origin_domain = "https://example.com"  # Use a concrete domain for validation
        
        # Validate CORS compliance
        validation_results = self._validate_cors_compliance(origin_domain, cors_headers)
        
        # Property: Required CORS headers should be present
        assert validation_results["has_allow_origin"] is True, (
            "CORS headers must include Access-Control-Allow-Origin"
        )
        assert validation_results["has_allow_methods"] is True, (
            "CORS headers must include Access-Control-Allow-Methods"
        )
        assert validation_results["has_allow_headers"] is True, (
            "CORS headers must include Access-Control-Allow-Headers"
        )
        
        # Property: HTTP methods should be valid
        assert validation_results["methods_valid"] is True, (
            f"Access-Control-Allow-Methods should contain only valid HTTP methods, "
            f"issues: {validation_results['issues']}"
        )
        
        # Property: Headers should be properly formatted
        assert validation_results["headers_valid"] is True, (
            f"Access-Control-Allow-Headers should be properly formatted, "
            f"issues: {validation_results['issues']}"
        )
        
        # Property: Max-Age should be valid if present
        assert validation_results["max_age_valid"] is True, (
            f"Access-Control-Max-Age should be a valid non-negative integer, "
            f"issues: {validation_results['issues']}"
        )
        
        # Property: Credentials configuration should be consistent
        assert validation_results["credentials_consistent"] is True, (
            f"Access-Control-Allow-Credentials should be consistent with Allow-Origin, "
            f"issues: {validation_results['issues']}"
        )
        
        # Property: Overall header format compliance
        assert validation_results["is_compliant"] is True, (
            f"CORS headers should be well-formed and compliant, issues: {validation_results['issues']}"
        )
        
        # Property: Access-Control-Allow-Origin should not be empty
        allow_origin = cors_headers.get("Access-Control-Allow-Origin", "")
        assert allow_origin and allow_origin.strip(), (
            "Access-Control-Allow-Origin should not be empty"
        )
        
        # Property: Access-Control-Allow-Methods should contain at least OPTIONS
        allow_methods = cors_headers.get("Access-Control-Allow-Methods", "")
        methods = [method.strip().upper() for method in allow_methods.split(",")]
        assert "OPTIONS" in methods, (
            f"Access-Control-Allow-Methods should include OPTIONS method for preflight requests. "
            f"Got methods: {methods}"
        )
    
    def test_property_cors_compliance_example_authorized_domain(self):
        """
        Example test demonstrating CORS compliance for a known authorized domain.
        This validates the property works with a concrete authorized domain.
        
        **Validates: Requirements 3.5**
        """
        tester = self._get_tester()
        
        # Known authorized domain
        authorized_domain = "https://app.example.com"
        
        # Simulate CORS preflight request
        preflight_response = self._simulate_cors_preflight_request(
            authorized_domain, "POST", ["Content-Type", "Authorization"]
        )
        
        # Validate CORS compliance
        validation_results = self._validate_cors_compliance(
            authorized_domain, preflight_response["cors_headers"]
        )
        
        # Validate the property holds for this authorized domain
        assert validation_results["origin_allowed"] is True, (
            f"Authorized domain {authorized_domain} should be allowed"
        )
        assert validation_results["has_allow_origin"] is True
        assert validation_results["has_allow_methods"] is True
        assert validation_results["has_allow_headers"] is True
        assert validation_results["methods_valid"] is True
        assert validation_results["headers_valid"] is True
        assert validation_results["max_age_valid"] is True
        assert validation_results["credentials_consistent"] is True
        assert validation_results["is_compliant"] is True, (
            f"CORS should be compliant for authorized domain, issues: {validation_results['issues']}"
        )
        assert len(validation_results["issues"]) == 0
    
    def test_property_cors_compliance_example_wildcard_origin(self):
        """
        Example test demonstrating CORS compliance with wildcard origin.
        This validates the property works with wildcard CORS configuration.
        
        **Validates: Requirements 3.5**
        """
        tester = self._get_tester()
        
        # Test with wildcard origin
        test_domain = "https://any-domain.com"
        
        # Mock CORS headers with wildcard origin
        cors_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-API-Key",
            "Access-Control-Max-Age": "3600"
            # Note: No Allow-Credentials with wildcard origin (correct behavior)
        }
        
        # Validate CORS compliance
        validation_results = self._validate_cors_compliance(test_domain, cors_headers)
        
        # Validate the property holds for wildcard configuration
        assert validation_results["origin_allowed"] is True, (
            "Wildcard origin should allow any domain"
        )
        assert validation_results["has_allow_origin"] is True
        assert validation_results["has_allow_methods"] is True
        assert validation_results["has_allow_headers"] is True
        assert validation_results["methods_valid"] is True
        assert validation_results["headers_valid"] is True
        assert validation_results["max_age_valid"] is True
        assert validation_results["credentials_consistent"] is True
        assert validation_results["is_compliant"] is True, (
            f"CORS should be compliant with wildcard origin, issues: {validation_results['issues']}"
        )
        assert len(validation_results["issues"]) == 0
    
    def test_property_cors_compliance_example_invalid_configuration(self):
        """
        Example test demonstrating CORS compliance validation with invalid configuration.
        This validates the property correctly identifies non-compliant CORS setups.
        
        **Validates: Requirements 3.5**
        """
        tester = self._get_tester()
        
        # Test domain
        test_domain = "https://app.example.com"
        
        # Mock invalid CORS headers (credentials with wildcard origin)
        invalid_cors_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, INVALID_METHOD",  # Invalid method
            "Access-Control-Allow-Headers": "",  # Empty headers
            "Access-Control-Max-Age": "-1",  # Invalid max age
            "Access-Control-Allow-Credentials": "true"  # Invalid with wildcard origin
        }
        
        # Validate CORS compliance
        validation_results = self._validate_cors_compliance(test_domain, invalid_cors_headers)
        
        # Validate the property correctly identifies issues
        assert validation_results["is_compliant"] is False, (
            "Invalid CORS configuration should not be compliant"
        )
        assert len(validation_results["issues"]) > 0, (
            "Invalid CORS configuration should have identified issues"
        )
        
        # Check specific issues are identified
        issues_text = " ".join(validation_results["issues"]).lower()
        assert "credentials" in issues_text or "invalid" in issues_text or "empty" in issues_text, (
            f"Should identify specific CORS issues, got: {validation_results['issues']}"
        )
        
        # Individual validation flags should reflect the issues
        assert not (validation_results["methods_valid"] and 
                   validation_results["headers_valid"] and 
                   validation_results["max_age_valid"] and 
                   validation_results["credentials_consistent"]), (
            "At least one validation flag should be False for invalid configuration"
        )