"""
Verification Layer Module

Verifies findings against original contract text using OpenAI API.
Detects hallucinations and validates query responses.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from src.exhaustiveness_models import SourceReference, VerifiedQueryResponse

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of verifying a finding."""
    is_verified: bool
    supporting_text: Optional[str]
    confidence_adjustment: float  # Positive for boost, negative for penalty
    explanation: str


@dataclass
class HallucinationCheckResult:
    """Result of checking for hallucination."""
    is_hallucinated: bool
    reason: str
    confidence: float  # Confidence in the hallucination determination


@dataclass
class QueryVerificationResult:
    """Result of verifying a query answer."""
    is_verified: bool
    verification_status: str  # "verified", "partially_verified", "unverified", "not_found"
    verified_portions: List[str]
    unverified_portions: List[str]
    source_references: List[SourceReference]
    explanation: str


class VerificationLayer:
    """
    Verifies findings against original contract text.
    
    Uses OpenAI API to cross-check that findings are supported
    by actual contract content.
    """
    
    VERIFICATION_PROMPT_TEMPLATE = """You are a contract verification assistant. Your task is to verify if a finding is supported by the contract text.

FINDING TO VERIFY:
Type: {finding_type}
Content: {finding_content}

CONTRACT TEXT (relevant section):
{contract_text}

INSTRUCTIONS:
1. Search the contract text for evidence supporting this finding
2. Determine if the finding is accurately represented in the contract
3. If found, quote the exact supporting text
4. If not found or inaccurate, explain why

Respond in JSON format:
{{
    "is_verified": true/false,
    "supporting_text": "exact quote from contract if found, null if not",
    "explanation": "brief explanation of verification result"
}}"""

    HALLUCINATION_CHECK_PROMPT_TEMPLATE = """You are a contract analysis auditor. Your task is to determine if a finding might be hallucinated (made up or not supported by the contract).

FINDING TO CHECK:
Type: {finding_type}
Content: {finding_content}

CONTRACT TEXT:
{contract_text}

INSTRUCTIONS:
1. Carefully search the contract for any mention of this finding
2. Check if the finding could be reasonably inferred from the contract
3. Determine if this finding appears to be fabricated or unsupported

Respond in JSON format:
{{
    "is_hallucinated": true/false,
    "reason": "explanation of why this is or isn't hallucinated",
    "confidence": 0.0-1.0 (confidence in your determination)
}}"""

    QUERY_VERIFICATION_PROMPT_TEMPLATE = """You are a contract query verification assistant. Your task is to verify if an answer to a question is supported by the contract.

QUESTION: {query}

ANSWER TO VERIFY:
{answer}

CONTRACT TEXT:
{contract_text}

INSTRUCTIONS:
1. Check each claim in the answer against the contract
2. Identify which parts are verified by the contract
3. Identify which parts cannot be verified
4. Provide source references for verified information

Respond in JSON format:
{{
    "is_verified": true/false,
    "verification_status": "verified" | "partially_verified" | "unverified" | "not_found",
    "verified_portions": ["list of verified claims"],
    "unverified_portions": ["list of unverified claims"],
    "source_references": [
        {{"text_excerpt": "quote from contract", "page_number": null}}
    ],
    "explanation": "brief explanation"
}}"""

    def __init__(self, openai_client):
        """
        Initialize with OpenAI client for verification calls.
        
        Args:
            openai_client: OpenAI client instance for API calls
        """
        self.openai_client = openai_client
        logger.info("VerificationLayer initialized")

    
    def verify_finding(
        self,
        finding: Dict[str, Any],
        contract_text: str,
        finding_type: str = "clause"
    ) -> VerificationResult:
        """
        Verify a single finding against contract text.
        
        Args:
            finding: The finding to verify (as dictionary)
            contract_text: Original contract text
            finding_type: Type of finding (clause, risk, etc.)
            
        Returns:
            VerificationResult with status and supporting evidence
        """
        logger.debug(f"Verifying {finding_type} finding")
        
        # Format finding content for prompt
        finding_content = self._format_finding_for_prompt(finding, finding_type)
        
        # Truncate contract text if too long (use relevant portion)
        truncated_text = self._get_relevant_contract_section(contract_text, finding_content)
        
        # Build verification prompt
        prompt = self.VERIFICATION_PROMPT_TEMPLATE.format(
            finding_type=finding_type,
            finding_content=finding_content,
            contract_text=truncated_text
        )
        
        try:
            # Call OpenAI for verification
            response = self._call_openai(prompt)
            result = self._parse_verification_response(response)
            
            logger.debug(f"Verification result: verified={result.is_verified}")
            return result
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return VerificationResult(
                is_verified=False,
                supporting_text=None,
                confidence_adjustment=-0.1,
                explanation=f"Verification failed: {str(e)}"
            )
    
    def detect_hallucination(
        self,
        finding: Dict[str, Any],
        contract_text: str,
        finding_type: str = "clause"
    ) -> HallucinationCheckResult:
        """
        Check if a finding is potentially hallucinated.
        
        Args:
            finding: The finding to check
            contract_text: Original contract text
            finding_type: Type of finding
            
        Returns:
            HallucinationCheckResult with is_hallucinated flag and reason
        """
        logger.debug(f"Checking {finding_type} for hallucination")
        
        finding_content = self._format_finding_for_prompt(finding, finding_type)
        truncated_text = self._get_relevant_contract_section(contract_text, finding_content)
        
        prompt = self.HALLUCINATION_CHECK_PROMPT_TEMPLATE.format(
            finding_type=finding_type,
            finding_content=finding_content,
            contract_text=truncated_text
        )
        
        try:
            response = self._call_openai(prompt)
            result = self._parse_hallucination_response(response)
            
            logger.debug(f"Hallucination check: is_hallucinated={result.is_hallucinated}")
            return result
            
        except Exception as e:
            logger.error(f"Hallucination check failed: {e}")
            return HallucinationCheckResult(
                is_hallucinated=False,  # Default to not hallucinated on error
                reason=f"Check failed: {str(e)}",
                confidence=0.0
            )
    
    def verify_query_answer(
        self,
        query: str,
        answer: str,
        contract_text: str
    ) -> QueryVerificationResult:
        """
        Verify a query answer against contract text.
        
        Args:
            query: User's question
            answer: Generated answer
            contract_text: Original contract text
            
        Returns:
            QueryVerificationResult with verification status and sources
        """
        logger.debug(f"Verifying query answer: {query[:50]}...")
        
        # Truncate contract text if needed
        truncated_text = contract_text[:50000] if len(contract_text) > 50000 else contract_text
        
        prompt = self.QUERY_VERIFICATION_PROMPT_TEMPLATE.format(
            query=query,
            answer=answer,
            contract_text=truncated_text
        )
        
        try:
            response = self._call_openai(prompt)
            result = self._parse_query_verification_response(response)
            
            logger.debug(f"Query verification: status={result.verification_status}")
            return result
            
        except Exception as e:
            logger.error(f"Query verification failed: {e}")
            return QueryVerificationResult(
                is_verified=False,
                verification_status="unverified",
                verified_portions=[],
                unverified_portions=[answer],
                source_references=[],
                explanation=f"Verification failed: {str(e)}"
            )
    
    def _call_openai(self, prompt: str) -> str:
        """
        Call OpenAI API with the given prompt.
        
        Args:
            prompt: Prompt to send to OpenAI
            
        Returns:
            Response text from OpenAI
        """
        try:
            # Use the chat completion method
            response = self.openai_client.client.chat.completions.create(
                model=self.openai_client.model,
                messages=[
                    {"role": "system", "content": "You are a contract verification assistant. Always respond in valid JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistent verification
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise

    
    def _format_finding_for_prompt(
        self,
        finding: Dict[str, Any],
        finding_type: str
    ) -> str:
        """
        Format a finding for inclusion in a prompt.
        
        Args:
            finding: Finding dictionary
            finding_type: Type of finding
            
        Returns:
            Formatted string representation
        """
        if finding_type == "clause":
            return f"Clause Type: {finding.get('type', 'unknown')}\nText: {finding.get('text', '')}"
        elif finding_type == "risk":
            return f"Risk: {finding.get('description', '')}\nSeverity: {finding.get('severity', 'unknown')}"
        elif finding_type == "compliance":
            return f"Compliance Issue: {finding.get('issue', '')}\nRegulation: {finding.get('regulation', 'unknown')}"
        elif finding_type == "redlining":
            return f"Original Text: {finding.get('original_text', '')}\nSuggested Change: {finding.get('suggested_text', '')}"
        else:
            return json.dumps(finding, indent=2)
    
    def _get_relevant_contract_section(
        self,
        contract_text: str,
        finding_content: str,
        max_length: int = 10000
    ) -> str:
        """
        Get the most relevant section of contract text for verification.
        
        Args:
            contract_text: Full contract text
            finding_content: Content to search for
            max_length: Maximum length of returned text
            
        Returns:
            Relevant section of contract text
        """
        if len(contract_text) <= max_length:
            return contract_text
        
        # Try to find the finding content in the contract
        finding_lower = finding_content.lower()
        contract_lower = contract_text.lower()
        
        # Search for key phrases from the finding
        key_phrases = [phrase.strip() for phrase in finding_lower.split('\n') if len(phrase.strip()) > 20]
        
        best_position = 0
        for phrase in key_phrases[:3]:  # Check first 3 key phrases
            pos = contract_lower.find(phrase[:50])  # Search for first 50 chars
            if pos != -1:
                best_position = pos
                break
        
        # Extract section around the found position
        start = max(0, best_position - max_length // 2)
        end = min(len(contract_text), start + max_length)
        
        return contract_text[start:end]
    
    def _parse_verification_response(self, response: str) -> VerificationResult:
        """
        Parse OpenAI verification response.
        
        Args:
            response: JSON response from OpenAI
            
        Returns:
            VerificationResult object
        """
        try:
            # Clean response (remove markdown code blocks if present)
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            
            data = json.loads(response)
            
            is_verified = data.get("is_verified", False)
            confidence_adjustment = 0.1 if is_verified else -0.1
            
            return VerificationResult(
                is_verified=is_verified,
                supporting_text=data.get("supporting_text"),
                confidence_adjustment=confidence_adjustment,
                explanation=data.get("explanation", "")
            )
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse verification response: {e}")
            return VerificationResult(
                is_verified=False,
                supporting_text=None,
                confidence_adjustment=0.0,
                explanation=f"Failed to parse response: {response[:100]}"
            )
    
    def _parse_hallucination_response(self, response: str) -> HallucinationCheckResult:
        """
        Parse OpenAI hallucination check response.
        
        Args:
            response: JSON response from OpenAI
            
        Returns:
            HallucinationCheckResult object
        """
        try:
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            
            data = json.loads(response)
            
            return HallucinationCheckResult(
                is_hallucinated=data.get("is_hallucinated", False),
                reason=data.get("reason", ""),
                confidence=float(data.get("confidence", 0.5))
            )
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse hallucination response: {e}")
            return HallucinationCheckResult(
                is_hallucinated=False,
                reason=f"Failed to parse response",
                confidence=0.0
            )
    
    def _parse_query_verification_response(self, response: str) -> QueryVerificationResult:
        """
        Parse OpenAI query verification response.
        
        Args:
            response: JSON response from OpenAI
            
        Returns:
            QueryVerificationResult object
        """
        try:
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            
            data = json.loads(response)
            
            # Parse source references
            source_refs = []
            for ref in data.get("source_references", []):
                source_refs.append(SourceReference(
                    clause_id=ref.get("clause_id"),
                    page_number=ref.get("page_number"),
                    text_excerpt=ref.get("text_excerpt", "")
                ))
            
            return QueryVerificationResult(
                is_verified=data.get("is_verified", False),
                verification_status=data.get("verification_status", "unverified"),
                verified_portions=data.get("verified_portions", []),
                unverified_portions=data.get("unverified_portions", []),
                source_references=source_refs,
                explanation=data.get("explanation", "")
            )
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse query verification response: {e}")
            return QueryVerificationResult(
                is_verified=False,
                verification_status="unverified",
                verified_portions=[],
                unverified_portions=[],
                source_references=[],
                explanation=f"Failed to parse response"
            )
