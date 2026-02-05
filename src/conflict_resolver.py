"""
Conflict Resolver Module

Resolves conflicts between analysis passes through targeted verification.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from src.exhaustiveness_models import (
    Conflict, ConflictResolution, VerifiedFinding, PresenceStatus
)
from src.verification_layer import VerificationLayer
from src.confidence_scorer import ConfidenceScorer

logger = logging.getLogger(__name__)


@dataclass
class TargetedVerificationResult:
    """Result of targeted verification for a conflict."""
    resolved: bool
    winning_pass: Optional[int]
    confidence: float
    explanation: str


class ConflictResolver:
    """
    Resolves conflicts between analysis passes.
    
    Uses targeted verification to resolve disagreements and
    provides explanations when automatic resolution fails.
    """
    
    CONFLICT_RESOLUTION_PROMPT = """You are a contract analysis expert. Your task is to resolve a conflict between different analysis results.

CONFLICT TYPE: {conflict_type}
FINDING TYPE: {finding_type}

CONFLICTING FINDINGS:
{findings_description}

CONTRACT TEXT (relevant section):
{contract_text}

INSTRUCTIONS:
1. Analyze each conflicting finding against the contract text
2. Determine which finding (if any) is most accurate
3. Provide a clear explanation for your decision

Respond in JSON format:
{{
    "resolved": true/false,
    "winning_pass": pass_number or null if unresolved,
    "confidence": 0.0-1.0,
    "explanation": "detailed explanation of resolution"
}}"""

    def __init__(
        self,
        verification_layer: VerificationLayer,
        openai_client,
        confidence_scorer: Optional[ConfidenceScorer] = None
    ):
        """
        Initialize with verification layer and OpenAI client.
        
        Args:
            verification_layer: VerificationLayer for finding verification
            openai_client: OpenAI client for API calls
            confidence_scorer: Optional confidence scorer for score updates
        """
        self.verification_layer = verification_layer
        self.openai_client = openai_client
        self.confidence_scorer = confidence_scorer or ConfidenceScorer()
        logger.info("ConflictResolver initialized")
    
    def resolve_conflict(
        self,
        conflict: Conflict,
        contract_text: str
    ) -> ConflictResolution:
        """
        Attempt to resolve a conflict through verification.
        
        Args:
            conflict: The conflict to resolve
            contract_text: Original contract text
            
        Returns:
            ConflictResolution with resolved finding or both options
        """
        logger.info(f"Resolving conflict: {conflict.conflict_id} ({conflict.conflict_type})")
        
        # Perform targeted verification
        verification_result = self.perform_targeted_verification(conflict, contract_text)
        
        if verification_result.resolved and verification_result.winning_pass is not None:
            # Create resolved finding from winning pass
            winning_data = conflict.pass_findings.get(verification_result.winning_pass, {})
            
            resolved_finding = VerifiedFinding(
                finding_type=conflict.finding_type,
                finding_data=winning_data,
                confidence_score=verification_result.confidence,
                presence_status=PresenceStatus.PRESENT if verification_result.confidence >= 0.7 else PresenceStatus.UNCERTAIN,
                passes_found_in=1,
                total_passes=len(conflict.pass_findings),
                is_verified=True,
                verification_source=None,
                is_hallucinated=False
            )
            
            return ConflictResolution(
                conflict=conflict,
                is_resolved=True,
                resolved_finding=resolved_finding,
                unresolved_options=None,
                resolution_method="verification",
                explanation=verification_result.explanation
            )
        else:
            # Create unresolved options from all pass findings
            unresolved_options = []
            for pass_num, finding_data in conflict.pass_findings.items():
                option = VerifiedFinding(
                    finding_type=conflict.finding_type,
                    finding_data=finding_data,
                    confidence_score=0.5,  # Low confidence for unresolved
                    presence_status=PresenceStatus.UNCERTAIN,
                    passes_found_in=1,
                    total_passes=len(conflict.pass_findings),
                    is_verified=False,
                    verification_source=None,
                    is_hallucinated=False
                )
                unresolved_options.append(option)
            
            return ConflictResolution(
                conflict=conflict,
                is_resolved=False,
                resolved_finding=None,
                unresolved_options=unresolved_options,
                resolution_method="manual",
                explanation=verification_result.explanation or "Unable to automatically resolve conflict"
            )

    
    def perform_targeted_verification(
        self,
        conflict: Conflict,
        contract_text: str
    ) -> TargetedVerificationResult:
        """
        Perform targeted verification pass for a specific conflict.
        
        Args:
            conflict: The conflict requiring verification
            contract_text: Original contract text
            
        Returns:
            TargetedVerificationResult with verification outcome
        """
        logger.debug(f"Performing targeted verification for conflict {conflict.conflict_id}")
        
        # Format findings for prompt
        findings_description = self._format_conflict_findings(conflict)
        
        # Get relevant contract section
        relevant_text = self._get_relevant_section(contract_text, conflict)
        
        prompt = self.CONFLICT_RESOLUTION_PROMPT.format(
            conflict_type=conflict.conflict_type,
            finding_type=conflict.finding_type,
            findings_description=findings_description,
            contract_text=relevant_text
        )
        
        try:
            response = self._call_openai(prompt)
            result = self._parse_resolution_response(response)
            
            logger.debug(f"Targeted verification result: resolved={result.resolved}")
            return result
            
        except Exception as e:
            logger.error(f"Targeted verification failed: {e}")
            return TargetedVerificationResult(
                resolved=False,
                winning_pass=None,
                confidence=0.0,
                explanation=f"Verification failed: {str(e)}"
            )
    
    def _format_conflict_findings(self, conflict: Conflict) -> str:
        """
        Format conflict findings for the resolution prompt.
        
        Args:
            conflict: Conflict with pass findings
            
        Returns:
            Formatted string describing each pass's finding
        """
        lines = []
        for pass_num, finding in conflict.pass_findings.items():
            lines.append(f"Pass {pass_num}:")
            if conflict.finding_type == "clause":
                lines.append(f"  Type: {finding.get('type', 'unknown')}")
                lines.append(f"  Risk Level: {finding.get('risk_level', 'unknown')}")
                lines.append(f"  Text: {finding.get('text', '')[:200]}...")
            elif conflict.finding_type == "risk":
                lines.append(f"  Severity: {finding.get('severity', 'unknown')}")
                lines.append(f"  Description: {finding.get('description', '')[:200]}...")
            else:
                lines.append(f"  Data: {json.dumps(finding, indent=2)[:300]}...")
            lines.append("")
        
        return "\n".join(lines)
    
    def _get_relevant_section(
        self,
        contract_text: str,
        conflict: Conflict,
        max_length: int = 10000
    ) -> str:
        """
        Get relevant contract section for conflict resolution.
        
        Args:
            contract_text: Full contract text
            conflict: Conflict to resolve
            max_length: Maximum length of returned text
            
        Returns:
            Relevant section of contract text
        """
        if len(contract_text) <= max_length:
            return contract_text
        
        # Try to find relevant text based on conflict findings
        search_terms = []
        for finding in conflict.pass_findings.values():
            if 'text' in finding:
                search_terms.append(finding['text'][:100])
            if 'description' in finding:
                search_terms.append(finding['description'][:100])
        
        # Search for first matching term
        contract_lower = contract_text.lower()
        best_pos = 0
        
        for term in search_terms:
            pos = contract_lower.find(term.lower()[:50])
            if pos != -1:
                best_pos = pos
                break
        
        # Extract section around found position
        start = max(0, best_pos - max_length // 2)
        end = min(len(contract_text), start + max_length)
        
        return contract_text[start:end]
    
    def _call_openai(self, prompt: str) -> str:
        """
        Call OpenAI API with the given prompt.
        
        Args:
            prompt: Prompt to send to OpenAI
            
        Returns:
            Response text from OpenAI
        """
        try:
            response = self.openai_client.client.chat.completions.create(
                model=self.openai_client.model,
                messages=[
                    {"role": "system", "content": "You are a contract analysis expert. Always respond in valid JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    def _parse_resolution_response(self, response: str) -> TargetedVerificationResult:
        """
        Parse OpenAI conflict resolution response.
        
        Args:
            response: JSON response from OpenAI
            
        Returns:
            TargetedVerificationResult object
        """
        try:
            # Clean response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            
            data = json.loads(response)
            
            return TargetedVerificationResult(
                resolved=data.get("resolved", False),
                winning_pass=data.get("winning_pass"),
                confidence=float(data.get("confidence", 0.5)),
                explanation=data.get("explanation", "")
            )
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse resolution response: {e}")
            return TargetedVerificationResult(
                resolved=False,
                winning_pass=None,
                confidence=0.0,
                explanation=f"Failed to parse response"
            )
    
    def resolve_all_conflicts(
        self,
        conflicts: List[Conflict],
        contract_text: str
    ) -> List[ConflictResolution]:
        """
        Resolve all conflicts in a list.
        
        Args:
            conflicts: List of conflicts to resolve
            contract_text: Original contract text
            
        Returns:
            List of ConflictResolution objects
        """
        resolutions = []
        
        for conflict in conflicts:
            resolution = self.resolve_conflict(conflict, contract_text)
            resolutions.append(resolution)
        
        resolved_count = sum(1 for r in resolutions if r.is_resolved)
        logger.info(f"Resolved {resolved_count}/{len(conflicts)} conflicts")
        
        return resolutions
