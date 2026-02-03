"""
Contract Chunker Module

Handles splitting large contracts into manageable chunks for API processing.
Preserves logical boundaries and includes overlap between chunks.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher

from src.exhaustiveness_models import ContractChunk
from src.analysis_models import AnalysisResult, Clause, Risk, ComplianceIssue, RedliningSuggestion

logger = logging.getLogger(__name__)

# Try to import tiktoken for accurate token estimation
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not available, using approximate token estimation")


class ContractChunker:
    """
    Splits large contracts into chunks that fit within API token limits.
    
    Preserves logical boundaries (sections, paragraphs) and includes
    overlap between chunks to avoid missing content at boundaries.
    """
    
    DEFAULT_MAX_TOKENS = 100000  # Conservative limit for GPT-4
    DEFAULT_OVERLAP_TOKENS = 500  # Overlap between chunks
    CHARS_PER_TOKEN_ESTIMATE = 4  # Approximate chars per token when tiktoken unavailable
    
    # Patterns for finding logical boundaries (in order of preference)
    SECTION_PATTERNS = [
        r'\n\s*(?:ARTICLE|SECTION|CHAPTER)\s+[IVXLCDM\d]+[.:]\s*',  # ARTICLE I, SECTION 1, etc.
        r'\n\s*\d+\.\s+[A-Z][A-Z\s]+\n',  # 1. DEFINITIONS
        r'\n\s*\d+\.\d+\s+',  # 1.1, 2.3, etc.
        r'\n\s*[a-z]\)\s+',  # a), b), etc.
        r'\n\s*\([a-z]\)\s+',  # (a), (b), etc.
        r'\n\n+',  # Double newlines (paragraph breaks)
        r'\n',  # Single newlines
    ]
    
    def __init__(
        self,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        overlap_tokens: int = DEFAULT_OVERLAP_TOKENS
    ):
        """
        Initialize the contract chunker.
        
        Args:
            max_tokens: Maximum tokens per chunk (default: 100000)
            overlap_tokens: Token overlap between chunks (default: 500)
        """
        self.max_tokens = max(1000, max_tokens)  # Minimum 1000 tokens
        self.overlap_tokens = min(overlap_tokens, max_tokens // 4)  # Max 25% overlap
        
        # Initialize tiktoken encoder if available
        self._encoder = None
        if TIKTOKEN_AVAILABLE:
            try:
                self._encoder = tiktoken.encoding_for_model("gpt-4")
                logger.debug("Using tiktoken for token estimation")
            except Exception as e:
                logger.warning(f"Failed to initialize tiktoken encoder: {e}")
        
        logger.info(f"ContractChunker initialized: max_tokens={self.max_tokens}, overlap_tokens={self.overlap_tokens}")
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Uses tiktoken for accurate GPT token estimation if available,
        otherwise falls back to character-based estimation.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        
        if self._encoder:
            try:
                return len(self._encoder.encode(text))
            except Exception as e:
                logger.warning(f"tiktoken encoding failed, using estimate: {e}")
        
        # Fallback: approximate based on characters
        return len(text) // self.CHARS_PER_TOKEN_ESTIMATE

    
    def find_logical_boundary(
        self,
        text: str,
        target_position: int,
        search_range: int = 1000
    ) -> int:
        """
        Find nearest logical boundary (section, paragraph) to target position.
        
        Searches within a range around the target position for the best
        logical boundary to split the text.
        
        Args:
            text: Contract text
            target_position: Target character position
            search_range: Characters to search before/after target
            
        Returns:
            Position of nearest logical boundary
        """
        if target_position <= 0:
            return 0
        if target_position >= len(text):
            return len(text)
        
        # Define search window
        search_start = max(0, target_position - search_range)
        search_end = min(len(text), target_position + search_range)
        search_text = text[search_start:search_end]
        
        best_boundary = target_position
        best_distance = search_range + 1
        
        # Try each pattern in order of preference
        for pattern in self.SECTION_PATTERNS:
            for match in re.finditer(pattern, search_text):
                # Calculate absolute position
                abs_position = search_start + match.start()
                distance = abs(abs_position - target_position)
                
                # Prefer boundaries closer to target
                if distance < best_distance:
                    best_distance = distance
                    best_boundary = abs_position
                    
                    # If we found a good boundary, stop searching this pattern
                    if distance < search_range // 4:
                        break
            
            # If we found a good boundary with this pattern, don't try lower-priority patterns
            if best_distance < search_range // 2:
                break
        
        logger.debug(f"Found boundary at {best_boundary} (target was {target_position}, distance {best_distance})")
        return best_boundary
    
    def chunk_contract(
        self,
        contract_text: str
    ) -> List[ContractChunk]:
        """
        Split contract into chunks while preserving logical boundaries.
        
        Args:
            contract_text: Full contract text
            
        Returns:
            List of ContractChunk objects with metadata
        """
        if not contract_text:
            logger.warning("Empty contract text provided")
            return []
        
        total_tokens = self.estimate_tokens(contract_text)
        logger.info(f"Chunking contract: {len(contract_text)} chars, ~{total_tokens} tokens")
        
        # If contract fits in one chunk, return as single chunk
        if total_tokens <= self.max_tokens:
            logger.info("Contract fits in single chunk")
            return [ContractChunk(
                chunk_index=0,
                total_chunks=1,
                text=contract_text,
                start_position=0,
                end_position=len(contract_text),
                overlap_start=0,
                overlap_end=0,
                estimated_tokens=total_tokens
            )]
        
        chunks = []
        current_position = 0
        chunk_index = 0
        
        # Calculate target chunk size in characters (approximate)
        target_chunk_chars = int(self.max_tokens * self.CHARS_PER_TOKEN_ESTIMATE * 0.9)  # 90% of max
        overlap_chars = int(self.overlap_tokens * self.CHARS_PER_TOKEN_ESTIMATE)
        
        while current_position < len(contract_text):
            # Calculate end position for this chunk
            chunk_end = min(current_position + target_chunk_chars, len(contract_text))
            
            # Find logical boundary near chunk end
            if chunk_end < len(contract_text):
                chunk_end = self.find_logical_boundary(contract_text, chunk_end)
            
            # Extract chunk text
            chunk_text = contract_text[current_position:chunk_end]
            chunk_tokens = self.estimate_tokens(chunk_text)
            
            # Determine overlap amounts
            overlap_start = overlap_chars if chunk_index > 0 else 0
            overlap_end = overlap_chars if chunk_end < len(contract_text) else 0
            
            chunks.append(ContractChunk(
                chunk_index=chunk_index,
                total_chunks=0,  # Will be updated after all chunks created
                text=chunk_text,
                start_position=current_position,
                end_position=chunk_end,
                overlap_start=overlap_start,
                overlap_end=overlap_end,
                estimated_tokens=chunk_tokens
            ))
            
            logger.debug(f"Created chunk {chunk_index}: pos {current_position}-{chunk_end}, ~{chunk_tokens} tokens")
            
            # Move to next chunk position (with overlap)
            current_position = max(current_position + 1, chunk_end - overlap_chars)
            chunk_index += 1
            
            # Safety check to prevent infinite loops
            if chunk_index > 1000:
                logger.error("Too many chunks created, breaking")
                break
        
        # Update total_chunks in all chunks
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total_chunks
        
        logger.info(f"Created {total_chunks} chunks from contract")
        return chunks

    
    def merge_chunk_results(
        self,
        chunk_results: List[AnalysisResult],
        chunks: List[ContractChunk]
    ) -> AnalysisResult:
        """
        Merge analysis results from multiple chunks.
        
        Handles deduplication of findings in overlapping regions.
        
        Args:
            chunk_results: Analysis results from each chunk
            chunks: Original chunk metadata for overlap detection
            
        Returns:
            Merged AnalysisResult with deduplicated findings
        """
        if not chunk_results:
            raise ValueError("No chunk results to merge")
        
        if len(chunk_results) == 1:
            return chunk_results[0]
        
        logger.info(f"Merging results from {len(chunk_results)} chunks")
        
        # Collect all findings with chunk source tracking
        all_clauses = []
        all_risks = []
        all_compliance_issues = []
        all_redlining_suggestions = []
        
        for i, result in enumerate(chunk_results):
            # Add chunk source to each finding
            for clause in result.clauses:
                clause_dict = clause.to_dict()
                clause_dict['_chunk_source'] = i
                all_clauses.append(clause_dict)
            
            for risk in result.risks:
                risk_dict = risk.to_dict()
                risk_dict['_chunk_source'] = i
                all_risks.append(risk_dict)
            
            for issue in result.compliance_issues:
                issue_dict = issue.to_dict()
                issue_dict['_chunk_source'] = i
                all_compliance_issues.append(issue_dict)
            
            for suggestion in result.redlining_suggestions:
                suggestion_dict = suggestion.to_dict()
                suggestion_dict['_chunk_source'] = i
                all_redlining_suggestions.append(suggestion_dict)
        
        # Deduplicate findings
        deduped_clauses = self._deduplicate_finding_dicts(all_clauses, 'text')
        deduped_risks = self._deduplicate_finding_dicts(all_risks, 'description')
        deduped_compliance = self._deduplicate_finding_dicts(all_compliance_issues, 'issue')
        deduped_redlining = self._deduplicate_finding_dicts(all_redlining_suggestions, 'original_text')
        
        logger.info(f"Deduplication: clauses {len(all_clauses)}->{len(deduped_clauses)}, "
                   f"risks {len(all_risks)}->{len(deduped_risks)}, "
                   f"compliance {len(all_compliance_issues)}->{len(deduped_compliance)}, "
                   f"redlining {len(all_redlining_suggestions)}->{len(deduped_redlining)}")
        
        # Convert back to model objects
        merged_clauses = [Clause.from_dict({k: v for k, v in c.items() if not k.startswith('_')}) for c in deduped_clauses]
        merged_risks = [Risk.from_dict({k: v for k, v in r.items() if not k.startswith('_')}) for r in deduped_risks]
        merged_compliance = [ComplianceIssue.from_dict({k: v for k, v in ci.items() if not k.startswith('_')}) for ci in deduped_compliance]
        merged_redlining = [RedliningSuggestion.from_dict({k: v for k, v in rs.items() if not k.startswith('_')}) for rs in deduped_redlining]
        
        # Use metadata from first result
        merged_result = AnalysisResult(
            metadata=chunk_results[0].metadata,
            clauses=merged_clauses,
            risks=merged_risks,
            compliance_issues=merged_compliance,
            redlining_suggestions=merged_redlining
        )
        
        return merged_result
    
    def _deduplicate_finding_dicts(
        self,
        findings: List[Dict[str, Any]],
        text_key: str,
        similarity_threshold: float = 0.85
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate findings based on text similarity.
        
        Args:
            findings: List of finding dictionaries to deduplicate
            text_key: Key containing the text to compare
            similarity_threshold: Minimum similarity to consider duplicate
            
        Returns:
            Deduplicated list of findings
        """
        if not findings:
            return []
        
        deduplicated = []
        
        for finding in findings:
            finding_text = finding.get(text_key, '')
            is_duplicate = False
            
            for existing in deduplicated:
                existing_text = existing.get(text_key, '')
                similarity = self._calculate_similarity(finding_text, existing_text)
                
                if similarity >= similarity_threshold:
                    is_duplicate = True
                    # Merge chunk sources
                    if '_chunk_sources' not in existing:
                        existing['_chunk_sources'] = [existing.get('_chunk_source', 0)]
                    existing['_chunk_sources'].append(finding.get('_chunk_source', 0))
                    break
            
            if not is_duplicate:
                finding['_chunk_sources'] = [finding.get('_chunk_source', 0)]
                deduplicated.append(finding)
        
        return deduplicated
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity ratio between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity ratio between 0.0 and 1.0
        """
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()
        
        if text1 == text2:
            return 1.0
        
        return SequenceMatcher(None, text1, text2).ratio()
    
    def deduplicate_findings(
        self,
        findings: List[Any],
        text_attr: str = 'text',
        similarity_threshold: float = 0.85
    ) -> List[Any]:
        """
        Remove duplicate findings based on text similarity.
        
        Args:
            findings: List of findings to deduplicate
            text_attr: Attribute name containing the text to compare
            similarity_threshold: Minimum similarity to consider duplicate
            
        Returns:
            Deduplicated list of findings
        """
        if not findings:
            return []
        
        deduplicated = []
        
        for finding in findings:
            finding_text = getattr(finding, text_attr, '') if hasattr(finding, text_attr) else str(finding)
            is_duplicate = False
            
            for existing in deduplicated:
                existing_text = getattr(existing, text_attr, '') if hasattr(existing, text_attr) else str(existing)
                similarity = self._calculate_similarity(finding_text, existing_text)
                
                if similarity >= similarity_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                deduplicated.append(finding)
        
        return deduplicated
