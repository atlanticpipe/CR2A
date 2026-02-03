"""
OpenAI Client for Unified CR2A Application

This module provides the OpenAIClient class for analyzing contracts using OpenAI's API.
It implements structured prompts for JSON output, error handling, and retry logic.
"""

import json
import time
import logging
from typing import Dict, Optional, Callable
from openai import OpenAI
from openai import APIError, APIConnectionError, RateLimitError, AuthenticationError

logger = logging.getLogger(__name__)


class OpenAIClient:
    """
    Client for interacting with OpenAI API to analyze contracts.
    
    This class handles:
    - Contract analysis using GPT-4 or GPT-3.5-turbo
    - Structured JSON output generation
    - API key validation
    - Error handling and retry logic with exponential backoff
    - Rate limit handling
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Initialize OpenAI client with API key.
        
        Args:
            api_key: OpenAI API key (should start with 'sk-')
            model: Model to use for analysis (default: gpt-4o)
        
        Raises:
            ValueError: If API key format is invalid
        """
        if not api_key or not isinstance(api_key, str):
            raise ValueError("API key must be a non-empty string")
        
        if not api_key.startswith('sk-'):
            raise ValueError("Invalid API key format. API keys should start with 'sk-'")
        
        self.api_key = api_key
        self.model = model
        self.client = OpenAI(api_key=api_key)
        self._max_retries = 3
        self._base_delay = 1.0  # Base delay for exponential backoff in seconds
    
    def analyze_contract(
        self, 
        contract_text: str,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Dict:
        """
        Analyze contract and return structured result.
        
        This method sends the contract text to OpenAI API and requests a structured
        JSON response containing clauses, risks, compliance issues, and redlining suggestions.
        
        Args:
            contract_text: Extracted contract text to analyze
            progress_callback: Optional callback function(status_message, percent) for progress updates
        
        Returns:
            Analysis result dictionary with structure:
            {
                "contract_metadata": {...},
                "clauses": [...],
                "risks": [...],
                "compliance_issues": [...],
                "redlining_suggestions": [...]
            }
        
        Raises:
            ValueError: If contract_text is empty
            APIError: If OpenAI API returns an error
            APIConnectionError: If network connection fails
            RateLimitError: If rate limit is exceeded after retries
            AuthenticationError: If API key is invalid
        """
        if not contract_text or not contract_text.strip():
            raise ValueError("Contract text cannot be empty")
        
        if progress_callback:
            progress_callback("Preparing contract analysis request...", 10)
        
        # Build the analysis prompt
        system_message = self._build_system_message()
        user_message = self._build_user_message(contract_text)
        
        if progress_callback:
            progress_callback("Sending request to OpenAI API...", 30)
        
        # Make API call with retry logic
        result = self._make_api_call_with_retry(
            system_message, 
            user_message,
            progress_callback
        )
        
        if progress_callback:
            progress_callback("Analysis complete", 100)
        
        return result
    
    def process_query(
        self,
        query: str,
        context: Dict,
        conversation_history: Optional[list] = None
    ) -> str:
        """
        Process a user query about a contract using OpenAI API.
        
        This method sends a user's natural language question along with relevant
        contract context to OpenAI and returns a conversational response.
        
        Args:
            query: User's natural language question about the contract
            context: Relevant contract data (clauses, risks, metadata, etc.)
            conversation_history: Optional list of previous messages in format
                                [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        
        Returns:
            Natural language response string from OpenAI
        
        Raises:
            ValueError: If query is empty or context is invalid
            APIError: If OpenAI API returns an error
            APIConnectionError: If network connection fails
            RateLimitError: If rate limit is exceeded after retries
            AuthenticationError: If API key is invalid
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        if not context or not isinstance(context, dict):
            raise ValueError("Context must be a non-empty dictionary")
        
        # Build system prompt for contract Q&A
        system_message = self._build_query_system_message()
        
        # Build user message with query and context
        user_message = self._build_query_user_message(query, context)
        
        # Build messages list with conversation history if provided
        messages = [{"role": "system", "content": system_message}]
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": user_message})
        
        # Make API call with retry logic
        try:
            response = self._make_query_api_call_with_retry(messages)
            return response
        except (RateLimitError, APIConnectionError, AuthenticationError, APIError) as e:
            # Re-raise to be handled by caller (QueryEngine)
            raise
    
    def validate_api_key(self) -> bool:
        """
        Validate API key by making a minimal test request.
        
        Returns:
            True if API key is valid, False otherwise
        
        Note:
            This method makes an actual API call to verify the key works.
            It uses minimal tokens to reduce cost.
        """
        try:
            # Make a minimal API call to test the key
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Test"}
                ],
                max_tokens=5
            )
            return response is not None
        except AuthenticationError:
            return False
        except Exception:
            # Other errors don't necessarily mean the key is invalid
            # (could be network issues, rate limits, etc.)
            return True
    
    def _build_system_message(self) -> str:
        """
        Build the system message for contract analysis.
        
        Returns:
            System message string with instructions for the AI
        """
        return """You are a Contract Analysis Engine. Analyze the provided contract and extract key information in a structured JSON format.

Your analysis should include:
1. Contract metadata (parties, dates, type)
2. Key clauses with risk assessment
3. Identified risks with severity levels
4. Compliance issues
5. Redlining suggestions for problematic clauses

Output ONLY a valid JSON object. Do not include explanations or markdown formatting."""
    
    def _build_query_system_message(self) -> str:
        """
        Build the system message for contract Q&A.
        
        Returns:
            System message string with instructions for the AI
        """
        return """You are a Contract Analysis Assistant. Your role is to answer questions about analyzed contracts based on the provided context.

Guidelines:
- Provide clear, accurate answers based on the contract context
- Reference specific clauses, risks, or compliance issues when relevant
- If the answer is not in the provided context, say so clearly
- Be concise but thorough
- Use professional language appropriate for legal/business contexts"""
    
    def _build_user_message(self, contract_text: str) -> str:
        """
        Build the user message containing the contract text and output schema.
        
        Args:
            contract_text: The contract text to analyze
        
        Returns:
            Formatted user message with contract and schema
        """
        schema = {
            "contract_metadata": {
                "filename": "string",
                "analyzed_at": "ISO 8601 datetime",
                "page_count": "integer",
                "parties": [
                    {
                        "name": "string",
                        "role": "string (e.g., 'contractor', 'client')"
                    }
                ],
                "contract_type": "string",
                "effective_date": "string"
            },
            "clauses": [
                {
                    "id": "string (e.g., 'clause_1')",
                    "type": "string (e.g., 'payment_terms', 'liability', 'termination')",
                    "text": "string (excerpt from contract)",
                    "page": "integer",
                    "risk_level": "string ('low', 'medium', 'high')"
                }
            ],
            "risks": [
                {
                    "id": "string (e.g., 'risk_1')",
                    "clause_id": "string (reference to clause)",
                    "severity": "string ('low', 'medium', 'high', 'critical')",
                    "description": "string",
                    "recommendation": "string"
                }
            ],
            "compliance_issues": [
                {
                    "id": "string (e.g., 'compliance_1')",
                    "regulation": "string (e.g., 'GDPR', 'CCPA')",
                    "issue": "string",
                    "severity": "string ('low', 'medium', 'high')"
                }
            ],
            "redlining_suggestions": [
                {
                    "clause_id": "string (reference to clause)",
                    "original_text": "string",
                    "suggested_text": "string",
                    "rationale": "string"
                }
            ]
        }
        
        return f"""Analyze the following contract and provide a structured JSON response following this schema:

{json.dumps(schema, indent=2)}

CONTRACT TEXT:
{contract_text}

Provide your analysis as a JSON object matching the schema above."""
    
    def _build_query_user_message(self, query: str, context: Dict) -> str:
        """
        Build the user message for contract Q&A.
        
        Args:
            query: User's question
            context: Relevant contract data
        
        Returns:
            Formatted user message with query and context
        """
        # Format context as readable text
        context_text = self._format_context_for_query(context)
        
        return f"""Based on the following contract information, please answer this question:

QUESTION: {query}

CONTRACT CONTEXT:
{context_text}

Please provide a clear and accurate answer based on the information above."""
    
    def _format_context_for_query(self, context: Dict) -> str:
        """
        Format contract context as readable text for query processing.
        
        Args:
            context: Contract analysis result dictionary
        
        Returns:
            Formatted context string
        """
        parts = []
        
        # Add metadata if present
        if "contract_metadata" in context:
            metadata = context["contract_metadata"]
            parts.append("CONTRACT METADATA:")
            if "filename" in metadata:
                parts.append(f"  Filename: {metadata['filename']}")
            if "contract_type" in metadata:
                parts.append(f"  Type: {metadata['contract_type']}")
            if "parties" in metadata and metadata["parties"]:
                parties_str = ", ".join([p.get("name", "Unknown") for p in metadata["parties"]])
                parts.append(f"  Parties: {parties_str}")
            if "effective_date" in metadata:
                parts.append(f"  Effective Date: {metadata['effective_date']}")
            parts.append("")
        
        # Add clauses if present - include FULL text for better answers
        if "clauses" in context and context["clauses"]:
            parts.append("CONTRACT CLAUSES:")
            for clause in context["clauses"][:15]:  # Limit to first 15 clauses
                clause_type = clause.get("type", "Unknown")
                clause_text = clause.get("text", "")  # Include full text
                risk_level = clause.get("risk_level", "unknown")
                page = clause.get("page", "?")
                parts.append(f"  [{clause_type}] (Page {page}, Risk: {risk_level})")
                parts.append(f"    {clause_text}")
                parts.append("")
        
        # Add risks if present
        if "risks" in context and context["risks"]:
            parts.append("IDENTIFIED RISKS:")
            for risk in context["risks"][:10]:  # Limit to first 10 risks
                severity = risk.get("severity", "unknown")
                description = risk.get("description", "")
                recommendation = risk.get("recommendation", "")
                parts.append(f"  - [{severity.upper()}] {description}")
                if recommendation:
                    parts.append(f"    Recommendation: {recommendation}")
            parts.append("")
        
        # Add compliance issues if present
        if "compliance_issues" in context and context["compliance_issues"]:
            parts.append("COMPLIANCE ISSUES:")
            for issue in context["compliance_issues"][:10]:  # Limit to first 10 issues
                regulation = issue.get("regulation", "Unknown")
                issue_desc = issue.get("issue", "")
                severity = issue.get("severity", "unknown")
                parts.append(f"  - [{regulation}] {issue_desc} (Severity: {severity})")
            parts.append("")
        
        result = "\n".join(parts) if parts else "No contract context available"
        logger.debug(f"Formatted context length: {len(result)} chars")
        return result
    
    def _make_api_call_with_retry(
        self,
        system_message: str,
        user_message: str,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Dict:
        """
        Make API call with exponential backoff retry logic.
        
        Args:
            system_message: System message for the API
            user_message: User message containing contract and schema
            progress_callback: Optional progress callback
        
        Returns:
            Parsed JSON response from API
        
        Raises:
            APIError: If API returns an error after all retries
            APIConnectionError: If network connection fails after all retries
            RateLimitError: If rate limit exceeded after all retries
            AuthenticationError: If API key is invalid
        """
        last_exception = None
        
        for attempt in range(self._max_retries):
            try:
                if progress_callback and attempt > 0:
                    progress_callback(f"Retrying API call (attempt {attempt + 1}/{self._max_retries})...", 40 + (attempt * 10))
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.0,  # Deterministic output
                    max_tokens=4000,
                    response_format={"type": "json_object"}
                )
                
                # Extract and parse JSON response
                response_text = response.choices[0].message.content
                if not response_text:
                    raise ValueError("Empty response from OpenAI API")
                
                result = json.loads(response_text)
                
                if progress_callback:
                    progress_callback("Parsing analysis results...", 90)
                
                return result
            
            except RateLimitError as e:
                last_exception = e
                if attempt < self._max_retries - 1:
                    delay = self._handle_rate_limit(attempt)
                    if progress_callback:
                        progress_callback(f"Rate limit hit. Waiting {delay:.1f}s before retry...", 40)
                    time.sleep(delay)
                else:
                    # Re-raise the original exception with additional context
                    raise
            
            except APIConnectionError as e:
                last_exception = e
                if attempt < self._max_retries - 1:
                    delay = self._calculate_backoff_delay(attempt)
                    if progress_callback:
                        progress_callback(f"Connection error. Retrying in {delay:.1f}s...", 40)
                    time.sleep(delay)
                else:
                    # Re-raise the original exception
                    raise
            
            except AuthenticationError as e:
                # Don't retry authentication errors - re-raise immediately
                raise
            
            except json.JSONDecodeError as e:
                # Don't retry JSON parsing errors - raise as ValueError
                raise ValueError(f"Invalid JSON response from API: {e}") from e
            
            except APIError as e:
                last_exception = e
                if attempt < self._max_retries - 1:
                    delay = self._calculate_backoff_delay(attempt)
                    if progress_callback:
                        progress_callback(f"API error. Retrying in {delay:.1f}s...", 40)
                    time.sleep(delay)
                else:
                    # Re-raise the original exception
                    raise
        
        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise ValueError("Unknown error during API call")
    
    def _handle_rate_limit(self, attempt: int) -> float:
        """
        Calculate delay for rate limit with exponential backoff.
        
        Args:
            attempt: Current attempt number (0-indexed)
        
        Returns:
            Delay in seconds
        """
        # Exponential backoff: 1s, 2s, 4s, 8s, etc.
        delay = self._base_delay * (2 ** attempt)
        # Cap at 60 seconds
        return min(delay, 60.0)
    
    def _calculate_backoff_delay(self, attempt: int) -> float:
        """
        Calculate delay for general errors with exponential backoff.
        
        Args:
            attempt: Current attempt number (0-indexed)
        
        Returns:
            Delay in seconds
        """
        # Exponential backoff: 1s, 2s, 4s
        delay = self._base_delay * (2 ** attempt)
        # Cap at 10 seconds for non-rate-limit errors
        return min(delay, 10.0)
    
    def _make_query_api_call_with_retry(self, messages: list) -> str:
        """
        Make query API call with exponential backoff retry logic.
        
        Args:
            messages: List of message dictionaries for the chat API
        
        Returns:
            Response text from OpenAI
        
        Raises:
            APIError: If API returns an error after all retries
            APIConnectionError: If network connection fails after all retries
            RateLimitError: If rate limit exceeded after all retries
            AuthenticationError: If API key is invalid
        """
        last_exception = None
        
        for attempt in range(self._max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,  # Slightly creative for conversational responses
                    max_tokens=1000
                )
                
                # Extract response text
                response_text = response.choices[0].message.content
                if not response_text:
                    raise ValueError("Empty response from OpenAI API")
                
                return response_text
            
            except RateLimitError as e:
                last_exception = e
                if attempt < self._max_retries - 1:
                    delay = self._handle_rate_limit(attempt)
                    time.sleep(delay)
                else:
                    raise
            
            except APIConnectionError as e:
                last_exception = e
                if attempt < self._max_retries - 1:
                    delay = self._calculate_backoff_delay(attempt)
                    time.sleep(delay)
                else:
                    raise
            
            except AuthenticationError as e:
                # Don't retry authentication errors
                raise
            
            except APIError as e:
                last_exception = e
                if attempt < self._max_retries - 1:
                    delay = self._calculate_backoff_delay(attempt)
                    time.sleep(delay)
                else:
                    raise
        
        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise ValueError("Unknown error during API call")
