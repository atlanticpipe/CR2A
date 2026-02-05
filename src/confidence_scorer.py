"""
Confidence Scorer Module

Calculates confidence scores for analysis findings based on
pass agreement, verification results, and other factors.
"""

import logging
from typing import Optional, Dict, Any

from src.exhaustiveness_models import PresenceStatus

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """
    Calculates confidence scores for analysis findings.
    
    Uses pass agreement, verification results, and base confidence
    factors to compute final confidence scores.
    """
    
    BASE_CONFIDENCE_FACTOR = 0.9
    DEFAULT_THRESHOLD = 0.7
    
    # Adjustment factors for verification results
    VERIFICATION_BOOST = 0.1  # Boost for verified findings
    HALLUCINATION_PENALTY = 0.5  # Penalty for potential hallucinations
    
    def __init__(self, base_confidence_factor: float = BASE_CONFIDENCE_FACTOR):
        """
        Initialize the confidence scorer.
        
        Args:
            base_confidence_factor: Base factor for confidence calculation (default: 0.9)
        """
        self.base_confidence_factor = max(0.1, min(1.0, base_confidence_factor))
        logger.debug(f"ConfidenceScorer initialized with base_confidence_factor={self.base_confidence_factor}")
    
    def calculate_confidence(
        self,
        passes_with_finding: int,
        total_passes: int,
        is_verified: bool = False,
        is_hallucinated: bool = False
    ) -> float:
        """
        Calculate confidence score for a finding.
        
        Formula: (passes_with_finding / total_passes) * base_confidence_factor
        Adjusted by verification result if available.
        
        Args:
            passes_with_finding: Number of passes containing this finding
            total_passes: Total number of analysis passes
            is_verified: Whether the finding was verified against contract text
            is_hallucinated: Whether the finding was flagged as potential hallucination
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Validate inputs
        if total_passes <= 0:
            logger.warning("Invalid total_passes <= 0, returning 0.0")
            return 0.0
        
        if passes_with_finding < 0:
            passes_with_finding = 0
        
        if passes_with_finding > total_passes:
            passes_with_finding = total_passes
        
        # Base confidence calculation
        pass_ratio = passes_with_finding / total_passes
        confidence = pass_ratio * self.base_confidence_factor
        
        # Apply verification boost
        if is_verified and not is_hallucinated:
            confidence = min(1.0, confidence + self.VERIFICATION_BOOST)
        
        # Apply hallucination penalty
        if is_hallucinated:
            confidence = max(0.0, confidence - self.HALLUCINATION_PENALTY)
        
        # Clamp to valid range
        confidence = max(0.0, min(1.0, confidence))
        
        logger.debug(f"Calculated confidence: {confidence:.3f} "
                    f"(passes={passes_with_finding}/{total_passes}, "
                    f"verified={is_verified}, hallucinated={is_hallucinated})")
        
        return confidence
    
    def meets_threshold(
        self,
        confidence: float,
        threshold: float = DEFAULT_THRESHOLD
    ) -> bool:
        """
        Check if confidence meets the threshold.
        
        Args:
            confidence: Confidence score to check
            threshold: Minimum confidence threshold (default: 0.7)
            
        Returns:
            True if confidence >= threshold
        """
        return confidence >= threshold
    
    def determine_presence_status(
        self,
        confidence: float,
        passes_with_finding: int,
        total_passes: int,
        has_conflicts: bool = False
    ) -> PresenceStatus:
        """
        Determine presence status based on confidence and pass agreement.
        
        Args:
            confidence: Calculated confidence score
            passes_with_finding: Number of passes containing this finding
            total_passes: Total number of analysis passes
            has_conflicts: Whether there are conflicts for this finding
            
        Returns:
            PresenceStatus indicating PRESENT, ABSENT, or UNCERTAIN
        """
        # If there are conflicts, status is uncertain
        if has_conflicts:
            return PresenceStatus.UNCERTAIN
        
        # High confidence (>= 0.8) and found in all passes = PRESENT
        if confidence >= 0.8 and passes_with_finding == total_passes:
            return PresenceStatus.PRESENT
        
        # Not found in any pass = ABSENT
        if passes_with_finding == 0:
            return PresenceStatus.ABSENT
        
        # Low confidence or partial agreement = UNCERTAIN
        if confidence < 0.5:
            return PresenceStatus.UNCERTAIN
        
        # Medium confidence with majority agreement = PRESENT
        if confidence >= 0.7 and passes_with_finding > total_passes / 2:
            return PresenceStatus.PRESENT
        
        # Default to UNCERTAIN
        return PresenceStatus.UNCERTAIN
    
    def calculate_average_confidence(
        self,
        confidence_scores: list
    ) -> float:
        """
        Calculate average confidence score from a list of scores.
        
        Args:
            confidence_scores: List of confidence scores
            
        Returns:
            Average confidence score, or 0.0 if list is empty
        """
        if not confidence_scores:
            return 0.0
        
        return sum(confidence_scores) / len(confidence_scores)
    
    def adjust_for_chunk_agreement(
        self,
        base_confidence: float,
        chunks_with_finding: int,
        total_chunks: int
    ) -> float:
        """
        Adjust confidence based on chunk agreement for large documents.
        
        Findings that appear in multiple chunks get a slight boost.
        
        Args:
            base_confidence: Base confidence score
            chunks_with_finding: Number of chunks containing this finding
            total_chunks: Total number of chunks
            
        Returns:
            Adjusted confidence score
        """
        if total_chunks <= 1:
            return base_confidence
        
        # Calculate chunk agreement ratio
        chunk_ratio = chunks_with_finding / total_chunks
        
        # Small boost for findings in multiple chunks (max 0.05)
        chunk_boost = min(0.05, chunk_ratio * 0.1)
        
        adjusted = min(1.0, base_confidence + chunk_boost)
        
        logger.debug(f"Chunk adjustment: {base_confidence:.3f} -> {adjusted:.3f} "
                    f"(chunks={chunks_with_finding}/{total_chunks})")
        
        return adjusted
