"""
Coverage Checker Module

Verifies exhaustive coverage of standard contract clause types.
"""

import logging
import json
from typing import List, Dict, Any, Optional

from src.exhaustiveness_models import (
    CoverageReport, PresenceStatus, VerifiedFinding, VerifiedAnalysisResult
)

logger = logging.getLogger(__name__)


class CoverageChecker:
    """
    Checks coverage of standard contract clause types.
    
    Maintains a checklist of expected clause types and verifies
    that all have been searched for and their presence/absence confirmed.
    """
    
    STANDARD_CLAUSE_TYPES = [
        "payment_terms",
        "liability",
        "termination",
        "confidentiality",
        "indemnification",
        "warranty",
        "intellectual_property",
        "dispute_resolution",
        "force_majeure",
        "assignment",
        "governing_law",
        "notice_provisions"
    ]
    
    # Mapping of clause type to common variations/aliases
    CLAUSE_TYPE_ALIASES = {
        "payment_terms": ["payment", "compensation", "fees", "pricing", "billing"],
        "liability": ["liability", "limitation of liability", "damages", "liability cap"],
        "termination": ["termination", "cancellation", "expiration", "term"],
        "confidentiality": ["confidentiality", "confidential", "nda", "non-disclosure", "proprietary"],
        "indemnification": ["indemnification", "indemnify", "hold harmless", "indemnity"],
        "warranty": ["warranty", "warranties", "representations", "guarantees"],
        "intellectual_property": ["intellectual property", "ip", "copyright", "patent", "trademark", "ownership"],
        "dispute_resolution": ["dispute", "arbitration", "mediation", "resolution", "litigation"],
        "force_majeure": ["force majeure", "act of god", "unforeseeable", "beyond control"],
        "assignment": ["assignment", "transfer", "assignability", "delegation"],
        "governing_law": ["governing law", "jurisdiction", "applicable law", "choice of law", "venue"],
        "notice_provisions": ["notice", "notification", "communications", "written notice"]
    }
    
    DEFAULT_COVERAGE_THRESHOLD = 50.0  # Minimum coverage percentage
    
    TARGETED_SEARCH_PROMPT = """You are a contract analysis expert. Your task is to determine if a specific clause type exists in the contract.

CLAUSE TYPE TO SEARCH FOR: {clause_type}
DESCRIPTION: {clause_description}

CONTRACT TEXT:
{contract_text}

INSTRUCTIONS:
1. Carefully search the contract for any provisions related to {clause_type}
2. Consider common variations and alternative phrasings
3. Determine if this clause type is present, absent, or uncertain

Respond in JSON format:
{{
    "status": "present" | "absent" | "uncertain",
    "evidence": "quote from contract if found, or explanation if not",
    "confidence": 0.0-1.0
}}"""

    CLAUSE_DESCRIPTIONS = {
        "payment_terms": "Terms related to payment amounts, schedules, methods, and conditions",
        "liability": "Limitations on liability, damage caps, and liability exclusions",
        "termination": "Conditions and procedures for ending the contract",
        "confidentiality": "Obligations to keep information confidential",
        "indemnification": "Obligations to compensate for losses or damages",
        "warranty": "Guarantees about the quality or performance of goods/services",
        "intellectual_property": "Ownership and rights to intellectual property",
        "dispute_resolution": "Methods for resolving disputes (arbitration, mediation, litigation)",
        "force_majeure": "Provisions for unforeseeable events beyond parties' control",
        "assignment": "Rights to transfer or assign the contract to another party",
        "governing_law": "Which jurisdiction's laws govern the contract",
        "notice_provisions": "Requirements for providing notices between parties"
    }

    def __init__(
        self,
        openai_client=None,
        coverage_threshold: float = DEFAULT_COVERAGE_THRESHOLD
    ):
        """
        Initialize the coverage checker.
        
        Args:
            openai_client: Optional OpenAI client for targeted searches
            coverage_threshold: Minimum coverage percentage threshold
        """
        self.openai_client = openai_client
        self.coverage_threshold = coverage_threshold
        logger.info(f"CoverageChecker initialized with threshold={coverage_threshold}%")

    
    def check_coverage(
        self,
        verified_clauses: List[VerifiedFinding],
        contract_text: Optional[str] = None
    ) -> CoverageReport:
        """
        Check coverage of standard clause types.
        
        Args:
            verified_clauses: List of verified clause findings
            contract_text: Optional contract text for targeted searches
            
        Returns:
            CoverageReport with found/not found clause types
        """
        logger.info("Checking coverage of standard clause types")
        
        # Extract clause types from verified findings
        found_types = set()
        uncertain_types = set()
        
        for finding in verified_clauses:
            clause_type = finding.finding_data.get('type', '').lower()
            
            # Map to standard type if possible
            standard_type = self._map_to_standard_type(clause_type)
            
            if standard_type:
                if finding.presence_status == PresenceStatus.PRESENT:
                    found_types.add(standard_type)
                elif finding.presence_status == PresenceStatus.UNCERTAIN:
                    uncertain_types.add(standard_type)
        
        # Determine not found types
        all_standard = set(self.STANDARD_CLAUSE_TYPES)
        not_found_types = all_standard - found_types - uncertain_types
        
        # If we have contract text and OpenAI client, do targeted searches for missing types
        if contract_text and self.openai_client and not_found_types:
            logger.info(f"Performing targeted searches for {len(not_found_types)} missing clause types")
            for clause_type in list(not_found_types):
                status = self.perform_targeted_search(clause_type, contract_text)
                if status == PresenceStatus.PRESENT:
                    found_types.add(clause_type)
                    not_found_types.discard(clause_type)
                elif status == PresenceStatus.UNCERTAIN:
                    uncertain_types.add(clause_type)
                    not_found_types.discard(clause_type)
        
        # Calculate coverage percentage
        coverage_percentage = (len(found_types) / len(self.STANDARD_CLAUSE_TYPES)) * 100
        is_below_threshold = coverage_percentage < self.coverage_threshold
        
        report = CoverageReport(
            clause_types_found=sorted(list(found_types)),
            clause_types_not_found=sorted(list(not_found_types)),
            clause_types_uncertain=sorted(list(uncertain_types)),
            coverage_percentage=coverage_percentage,
            is_below_threshold=is_below_threshold,
            threshold=self.coverage_threshold
        )
        
        logger.info(f"Coverage: {coverage_percentage:.1f}% ({len(found_types)}/{len(self.STANDARD_CLAUSE_TYPES)} types found)")
        
        return report
    
    def _map_to_standard_type(self, clause_type: str) -> Optional[str]:
        """
        Map a clause type to a standard type using aliases.
        
        Args:
            clause_type: Clause type to map
            
        Returns:
            Standard clause type or None if no match
        """
        clause_type_lower = clause_type.lower().strip()
        
        # Direct match
        if clause_type_lower in self.STANDARD_CLAUSE_TYPES:
            return clause_type_lower
        
        # Check aliases
        for standard_type, aliases in self.CLAUSE_TYPE_ALIASES.items():
            for alias in aliases:
                if alias in clause_type_lower or clause_type_lower in alias:
                    return standard_type
        
        return None
    
    def perform_targeted_search(
        self,
        clause_type: str,
        contract_text: str
    ) -> PresenceStatus:
        """
        Perform targeted search for a specific clause type.
        
        Args:
            clause_type: Type of clause to search for
            contract_text: Original contract text
            
        Returns:
            PresenceStatus indicating PRESENT, ABSENT, or UNCERTAIN
        """
        if not self.openai_client:
            logger.warning("No OpenAI client available for targeted search")
            return PresenceStatus.UNCERTAIN
        
        logger.debug(f"Targeted search for clause type: {clause_type}")
        
        # Truncate contract text if too long
        truncated_text = contract_text[:30000] if len(contract_text) > 30000 else contract_text
        
        description = self.CLAUSE_DESCRIPTIONS.get(clause_type, f"Provisions related to {clause_type}")
        
        prompt = self.TARGETED_SEARCH_PROMPT.format(
            clause_type=clause_type,
            clause_description=description,
            contract_text=truncated_text
        )
        
        try:
            response = self._call_openai(prompt)
            return self._parse_search_response(response)
        except Exception as e:
            logger.error(f"Targeted search failed: {e}")
            return PresenceStatus.UNCERTAIN
    
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
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    def _parse_search_response(self, response: str) -> PresenceStatus:
        """
        Parse OpenAI targeted search response.
        
        Args:
            response: JSON response from OpenAI
            
        Returns:
            PresenceStatus based on response
        """
        try:
            # Clean response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            
            data = json.loads(response)
            status = data.get("status", "uncertain").lower()
            
            if status == "present":
                return PresenceStatus.PRESENT
            elif status == "absent":
                return PresenceStatus.ABSENT
            else:
                return PresenceStatus.UNCERTAIN
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse search response: {e}")
            return PresenceStatus.UNCERTAIN
    
    def get_coverage_summary(self, report: CoverageReport) -> str:
        """
        Generate a human-readable coverage summary.
        
        Args:
            report: CoverageReport to summarize
            
        Returns:
            Formatted summary string
        """
        lines = []
        lines.append(f"Coverage: {report.coverage_percentage:.1f}%")
        
        if report.is_below_threshold:
            lines.append(f"⚠️ WARNING: Below threshold of {report.threshold:.1f}%")
        
        if report.clause_types_found:
            lines.append(f"\n✓ Found ({len(report.clause_types_found)}):")
            for ct in report.clause_types_found:
                lines.append(f"  - {ct.replace('_', ' ').title()}")
        
        if report.clause_types_not_found:
            lines.append(f"\n✗ Not Found ({len(report.clause_types_not_found)}):")
            for ct in report.clause_types_not_found:
                lines.append(f"  - {ct.replace('_', ' ').title()}")
        
        if report.clause_types_uncertain:
            lines.append(f"\n? Uncertain ({len(report.clause_types_uncertain)}):")
            for ct in report.clause_types_uncertain:
                lines.append(f"  - {ct.replace('_', ' ').title()}")
        
        return "\n".join(lines)
