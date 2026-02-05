"""
OpenAI Client for Unified CR2A Application

This module provides the OpenAIClient class for analyzing contracts using OpenAI's API.
It implements structured prompts for JSON output, error handling, and retry logic.
"""

import json
import time
import logging
import re
from typing import Dict, Optional, Callable
from openai import OpenAI
from openai import APIError, APIConnectionError, RateLimitError, AuthenticationError

from src.schema_loader import SchemaLoader

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
        
        # Load comprehensive schema for contract analysis
        self._schema_loader = SchemaLoader()
        self._schema_loader.load_schema()  # Load schema on initialization
    
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
        
        Requirements:
            - 1.2: Instruct AI to analyze contracts according to ClauseBlock structure
            - 1.4: Instruct to omit clauses not found rather than including empty values
        """
        return """You are a Contract Analysis Engine specializing in comprehensive contract risk assessment. Analyze the provided contract and extract key information in a structured JSON format following the 8-section schema.

## ANALYSIS SECTIONS

You must analyze the contract across these 8 sections:

### Section I: Contract Overview (contract_overview)
Extract high-level contract information including:
- Project Title: The name or title of the project/contract
- Solicitation No.: Contract or solicitation number if present
- Owner: The party commissioning the work (client/owner)
- Contractor: The party performing the work
- Scope: Brief description of the contract scope
- General Risk Level: Overall risk assessment (Low, Medium, High, or Critical)
- Bid Model: Type of pricing model (Lump Sum, Unit Price, Cost Plus, Time & Materials, GMP, Design-Build, or Other)
- Notes: Any additional relevant observations

### Section II: Administrative & Commercial Terms (administrative_and_commercial_terms)
Analyze these 16 clause categories:
- Contract Term, Renewal & Extensions
- Bonding, Surety & Insurance
- Retainage & Progress Payments
- Pay-When-Paid / Pay-If-Paid
- Price Escalation
- Fuel Price Adjustment
- Change Orders
- Termination for Convenience
- Termination for Cause
- Bid Protest Procedures
- Bid Tabulation
- Contractor Qualification
- Release Orders
- Assignment & Novation
- Audit Rights
- Notice Requirements

### Section III: Technical & Performance Terms (technical_and_performance_terms)
Analyze these 17 clause categories:
- Scope of Work
- Performance Schedule
- Delays & Extensions of Time
- Liquidated Damages
- Warranty & Guarantees
- Inspection & Acceptance
- Quality Control / Quality Assurance
- Safety Requirements
- Site Conditions
- Differing Site Conditions
- Force Majeure
- Suspension of Work
- Acceleration
- Subcontracting
- Equipment & Materials
- Testing & Commissioning
- Punch List & Final Completion

### Section IV: Legal Risk & Enforcement (legal_risk_and_enforcement)
Analyze these 13 clause categories:
- Indemnification
- Duty to Defend
- Limitation of Liability
- Consequential Damages Waiver
- Dispute Resolution
- Governing Law & Jurisdiction
- Arbitration
- Mediation
- Litigation
- Attorneys' Fees
- Waiver of Jury Trial
- Sovereign Immunity
- Statute of Limitations

### Section V: Regulatory & Compliance Terms (regulatory_and_compliance_terms)
Analyze these 8 clause categories:
- Certified Payroll
- Prevailing Wage / Davis-Bacon
- Equal Employment Opportunity (EEO)
- Small Business / DBE Requirements
- Environmental Compliance
- Permits & Licenses
- OSHA Compliance
- Buy America / Buy American

### Section VI: Data, Technology & Deliverables (data_technology_and_deliverables)
Analyze these 7 clause categories:
- Data Ownership & Rights
- Intellectual Property
- AI / Technology Use
- Cybersecurity Requirements
- BIM / Digital Deliverables
- Document Retention
- Confidentiality / Non-Disclosure

### Section VII: Supplemental Operational Risks (supplemental_operational_risks)
Identify up to 9 additional risk areas not covered in the standard sections above. These are contract-specific risks that warrant attention.

### Section VIII: Final Analysis (final_analysis)
Provide a comprehensive summary including:
- Executive Summary: Overall assessment of the contract
- Top Risks: The most significant risks identified
- Recommended Actions: Priority actions for the contractor
- Negotiation Points: Key areas to negotiate before signing

## CLAUSEBLOCK STRUCTURE

For each clause category found in the contract, provide analysis using this ClauseBlock structure:

1. **Clause Language**: The verbatim or quoted text from the contract that contains this clause
2. **Clause Summary**: A plain-English summary explaining what the clause means and its implications
3. **Risk Triggers Identified**: A list of specific conditions, terms, or language that indicate potential risk
4. **Flow-Down Obligations**: A list of requirements that must be passed down to subcontractors
5. **Redline Recommendations**: A list of suggested changes, each containing:
   - action: "insert", "replace", or "delete"
   - text: The specific text to insert, the replacement text, or the text to delete
   - reference: (optional) Reference to standard clause or industry practice
6. **Harmful Language / Policy Conflicts**: A list of terms that conflict with standard business practices or policies

## CRITICAL INSTRUCTIONS

1. **RETURN ONLY FOUND CLAUSES**: Only include clause categories that are actually present in the contract text. Do not include categories that are not found. The application will automatically add missing categories for display purposes.

2. **JSON OUTPUT ONLY**: Output ONLY a valid JSON object. Do not include explanations, markdown formatting, code blocks, or any text outside the JSON structure. Start directly with { and end with }.

3. **ACCURACY**: Only extract information that is explicitly stated or clearly implied in the contract. Do not fabricate or assume clause content.

4. **COMPLETENESS**: For each clause found, provide all applicable ClauseBlock fields. If a specific field is not applicable, use an empty array [].

5. **RISK ASSESSMENT**: Be thorough in identifying risk triggers and harmful language. Consider the contractor's perspective when assessing risks.

6. **BE CONCISE**: Keep summaries and descriptions concise to avoid token limits. Focus on key information. Use brief, clear language. Avoid repetition.

7. **PRIORITIZE COMPLETENESS**: It's better to include all found categories with brief summaries than to provide detailed analysis of only a few categories."""
    
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
        
        This method uses the comprehensive 8-section schema from SchemaLoader
        to provide detailed instructions for contract analysis output.
        
        Args:
            contract_text: The contract text to analyze (may be full text or pre-extracted sections)
        
        Returns:
            Formatted user message with comprehensive schema and contract text
        
        Requirements:
            - 1.1: Include complete schema structure from output_schemas_v1.json with all 8 sections
            - 1.5: Request JSON output that validates against the output_schemas_v1.json schema
        """
        # Get comprehensive schema description from SchemaLoader
        schema_description = self._schema_loader.get_schema_for_prompt()
        
        # Detect if this is focused extraction (heuristic: much shorter than typical contract)
        is_focused = len(contract_text) < 50000  # Less than ~50KB suggests focused extraction
        
        if is_focused:
            contract_label = "EXTRACTED CONTRACT SECTIONS"
            extraction_note = """
NOTE: The text below contains pre-extracted sections that match the clause categories 
in the schema. These sections were identified using pattern matching to focus the 
analysis on relevant contract language."""
        else:
            contract_label = "CONTRACT TEXT"
            extraction_note = ""
        
        return f"""Analyze the following contract and provide a structured JSON response.

{schema_description}

---

{contract_label}:
{contract_text}

---
{extraction_note}

Provide your analysis as a valid JSON object matching the schema structure described above. Remember to:
1. Include schema_version field (e.g., "v1.0.0")
2. Only include clause categories that are actually found in the contract
3. Omit categories not present - the application will add them for display
4. Use the exact ClauseBlock structure for each clause found
5. Output ONLY valid JSON - no markdown, no code blocks, no explanations"""
    
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
        
        Supports both legacy and comprehensive schema formats.
        
        Args:
            context: Contract analysis result dictionary
        
        Returns:
            Formatted context string
        """
        parts = []
        
        # Check if this is comprehensive format (has contract_overview or clause_blocks)
        is_comprehensive = 'contract_overview' in context or 'clause_blocks' in context
        
        if is_comprehensive:
            # Handle comprehensive format
            
            # Add contract overview if present
            if "contract_overview" in context and context["contract_overview"]:
                overview = context["contract_overview"]
                parts.append("CONTRACT OVERVIEW:")
                for key, value in overview.items():
                    if value:
                        # Convert snake_case to Title Case for display
                        display_key = key.replace('_', ' ').title()
                        parts.append(f"  {display_key}: {value}")
                parts.append("")
            
            # Add clause blocks if present
            if "clause_blocks" in context and context["clause_blocks"]:
                parts.append("CONTRACT CLAUSES:")
                for block in context["clause_blocks"][:15]:  # Limit to first 15
                    section = block.get('_section', 'Unknown Section')
                    clause_name = block.get('_clause_name', 'Unknown Clause')
                    clause_language = block.get('Clause Language', block.get('clause_language', ''))
                    clause_summary = block.get('Clause Summary', block.get('clause_summary', ''))
                    
                    parts.append(f"  [{clause_name}]")
                    if clause_summary and clause_summary.lower() != 'not found':
                        parts.append(f"    Summary: {clause_summary}")
                    if clause_language and clause_language.lower() != 'not found':
                        parts.append(f"    Language: {clause_language}")
                    parts.append("")
        else:
            # Handle legacy format
            
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
        logger.debug(f"Formatted context length: {len(result)} chars, format: {'comprehensive' if is_comprehensive else 'legacy'}")
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
                    max_tokens=16000,  # Increased from 4000 to allow more complete responses
                    response_format={"type": "json_object"}
                )
                
                # Extract and parse JSON response
                response_text = response.choices[0].message.content
                if not response_text:
                    raise ValueError("Empty response from OpenAI API")
                
                # Try to parse JSON
                try:
                    result = json.loads(response_text)
                except json.JSONDecodeError as e:
                    # Log the error and try to repair the JSON
                    logger.warning(f"JSON parsing failed: {e}")
                    logger.debug(f"Response text (first 500 chars): {response_text[:500]}")
                    
                    # Try to repair common JSON issues
                    repaired_text = self._repair_json(response_text)
                    if repaired_text != response_text:
                        logger.info("Attempting to parse repaired JSON")
                        try:
                            result = json.loads(repaired_text)
                            logger.info("Successfully parsed repaired JSON")
                        except json.JSONDecodeError as e2:
                            logger.error(f"Repaired JSON still invalid: {e2}")
                            raise ValueError(f"Invalid JSON response from API: {e}") from e
                    else:
                        raise ValueError(f"Invalid JSON response from API: {e}") from e
                
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
    
    def _repair_json(self, json_text: str) -> str:
        """
        Attempt to repair common JSON formatting issues.
        
        Args:
            json_text: Potentially malformed JSON text
            
        Returns:
            Repaired JSON text (may still be invalid)
        """
        # Remove markdown code blocks if present
        if json_text.startswith("```"):
            json_text = re.sub(r'^```(?:json)?\s*', '', json_text)
            json_text = re.sub(r'\s*```$', '', json_text)
        
        # Try to find the JSON object boundaries
        # Look for the first { and last }
        start_idx = json_text.find('{')
        end_idx = json_text.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_text = json_text[start_idx:end_idx + 1]
        
        # Fix unterminated strings by truncating at the error point
        # This is a last resort - we'll try to close any open strings
        try:
            # Count quotes to see if we have an odd number (unterminated string)
            quote_count = json_text.count('"') - json_text.count('\\"')
            if quote_count % 2 != 0:
                # Find the last quote and try to close it
                last_quote = json_text.rfind('"')
                if last_quote != -1:
                    # Truncate before the unterminated string
                    # Look backwards for the previous complete field
                    truncate_point = json_text.rfind(',', 0, last_quote)
                    if truncate_point == -1:
                        truncate_point = json_text.rfind('{', 0, last_quote)
                    
                    if truncate_point != -1:
                        json_text = json_text[:truncate_point]
                        # Close any open braces
                        open_braces = json_text.count('{') - json_text.count('}')
                        json_text += '}' * open_braces
                        logger.info(f"Truncated JSON at unterminated string, added {open_braces} closing braces")
        except Exception as e:
            logger.warning(f"Error during JSON repair: {e}")
        
        return json_text
    
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
