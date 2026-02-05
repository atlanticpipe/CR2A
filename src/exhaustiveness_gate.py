"""
Exhaustiveness Gate Module

Main orchestrator that coordinates the verification workflow for
exhaustive contract analysis with multi-pass verification.
"""

import logging
import time
from datetime import datetime
from typing import Optional, Callable, List, Dict, Any

from src.analysis_models import AnalysisResult, ComprehensiveAnalysisResult
from src.exhaustiveness_models import (
    PresenceStatus, VerifiedFinding, VerifiedAnalysisResult,
    VerificationMetadata, CoverageReport, ConflictResolution,
    VerifiedQueryResponse, SourceReference
)
from src.contract_chunker import ContractChunker
from src.confidence_scorer import ConfidenceScorer
from src.result_comparator import ResultComparator
from src.verification_layer import VerificationLayer
from src.conflict_resolver import ConflictResolver
from src.coverage_checker import CoverageChecker

logger = logging.getLogger(__name__)


class ExhaustivenessGate:
    """
    Orchestrates exhaustive contract analysis with verification.
    
    Wraps the existing AnalysisEngine to provide multi-pass analysis,
    hallucination detection, and confidence scoring.
    """
    
    MIN_PASSES = 2
    MAX_PASSES = 5
    DEFAULT_PASSES = 2
    DEFAULT_CONFIDENCE_THRESHOLD = 0.7
    
    def __init__(
        self,
        analysis_engine,
        openai_client,
        num_passes: int = DEFAULT_PASSES,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        max_tokens_per_chunk: int = 100000
    ):
        """
        Initialize the exhaustiveness gate.
        
        Args:
            analysis_engine: Existing analysis engine instance
            openai_client: OpenAI client for verification calls
            num_passes: Number of analysis passes (2-5, default 2)
            confidence_threshold: Minimum confidence for findings (default 0.7)
            max_tokens_per_chunk: Maximum tokens per chunk for large documents
        """
        self.analysis_engine = analysis_engine
        self.openai_client = openai_client
        
        # Clamp num_passes to valid range
        self.num_passes = max(self.MIN_PASSES, min(self.MAX_PASSES, num_passes))
        if num_passes != self.num_passes:
            logger.warning(f"num_passes clamped from {num_passes} to {self.num_passes}")
        
        self.confidence_threshold = confidence_threshold
        
        # Initialize components
        self.chunker = ContractChunker(max_tokens=max_tokens_per_chunk)
        self.scorer = ConfidenceScorer()
        self.comparator = ResultComparator()
        self.verification_layer = VerificationLayer(openai_client)
        self.conflict_resolver = ConflictResolver(
            self.verification_layer, openai_client, self.scorer
        )
        self.coverage_checker = CoverageChecker(openai_client)
        
        logger.info(f"ExhaustivenessGate initialized: passes={self.num_passes}, "
                   f"threshold={self.confidence_threshold}")

    
    def analyze_contract_exhaustively(
        self,
        file_path: str,
        contract_text: Optional[str] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> VerifiedAnalysisResult:
        """
        Perform exhaustive multi-pass analysis with verification.
        
        Args:
            file_path: Path to contract file
            contract_text: Optional pre-extracted contract text
            progress_callback: Optional progress callback
            
        Returns:
            VerifiedAnalysisResult with confidence scores and presence status
        """
        start_time = time.time()
        logger.info(f"Starting exhaustive analysis: {file_path}")
        
        if progress_callback:
            progress_callback("Starting exhaustive analysis...", 0)
        
        # Extract contract text if not provided
        if not contract_text:
            contract_text = self.analysis_engine.uploader.extract_text(file_path)
        
        # Apply clause extraction if available
        analysis_text = contract_text
        if self.analysis_engine.extractor:
            if progress_callback:
                progress_callback("Extracting relevant clause sections...", 3)
            
            try:
                focused_contract, extraction_metadata = self.analysis_engine.extractor.create_focused_contract(contract_text)
                
                # Log extraction statistics
                original_len = extraction_metadata.get('original_length', len(contract_text))
                focused_len = extraction_metadata.get('focused_length', len(focused_contract))
                reduction_pct = extraction_metadata.get('reduction_percent', 0)
                categories_found = extraction_metadata.get('total_categories', 0)
                
                logger.info(f"Exhaustive mode clause extraction: {original_len} chars -> {focused_len} chars ({reduction_pct:.1f}% reduction)")
                logger.info(f"Found {categories_found} clause categories")
                
                # Use focused contract if extraction found substantial content
                if focused_len >= original_len * 0.1:
                    analysis_text = focused_contract
                    logger.info("Using focused clause extraction for exhaustive analysis")
                else:
                    logger.warning(f"Clause extraction found minimal content, using full contract")
                    analysis_text = contract_text
                    
            except Exception as e:
                logger.warning(f"Clause extraction failed: {e}, using full contract text")
                analysis_text = contract_text
        
        # Check if chunking is needed
        chunks = self.chunker.chunk_contract(analysis_text)
        total_chunks = len(chunks)
        logger.info(f"Contract split into {total_chunks} chunks")
        
        if progress_callback:
            progress_callback(f"Contract split into {total_chunks} chunks", 5)
        
        # Perform multi-pass analysis
        pass_results = []
        pass_timestamps = []
        total_tokens = sum(c.estimated_tokens for c in chunks)
        
        for pass_num in range(self.num_passes):
            if progress_callback:
                base_progress = 5 + (pass_num * 30 // self.num_passes)
                progress_callback(f"Analysis pass {pass_num + 1}/{self.num_passes}...", base_progress)
            
            logger.info(f"Starting analysis pass {pass_num + 1}/{self.num_passes}")
            pass_timestamps.append(datetime.now())
            
            # Analyze each chunk
            chunk_results = []
            chunk_errors = []
            for chunk_idx, chunk in enumerate(chunks):
                try:
                    # Use a temporary file approach or direct text analysis
                    logger.info(f"Analyzing chunk {chunk_idx + 1}/{len(chunks)} ({chunk.estimated_tokens} tokens)")
                    result = self._analyze_chunk(chunk.text, file_path)
                    logger.info(f"Chunk {chunk_idx + 1} analysis successful")
                    chunk_results.append(result)
                except Exception as e:
                    error_msg = f"Chunk {chunk_idx + 1} analysis failed: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    chunk_errors.append(error_msg)
                    continue
            
            # Merge chunk results
            if chunk_results:
                merged_result = self.chunker.merge_chunk_results(chunk_results, chunks)
                pass_results.append(merged_result)
        
        if not pass_results:
            # Provide detailed error message about what went wrong
            error_details = "\n".join(chunk_errors) if chunk_errors else "Unknown error during analysis"
            error_msg = f"All analysis passes failed. Details:\n{error_details}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if progress_callback:
            progress_callback("Comparing analysis passes...", 40)
        
        # Compare passes and identify consensus/conflicts
        comparison = self.comparator.compare_passes(pass_results)
        
        if progress_callback:
            progress_callback("Verifying findings...", 50)
        
        # Verify findings and detect hallucinations
        verified_clauses = self._verify_findings(
            comparison.consensus_findings + comparison.flagged_findings,
            contract_text,
            "clause",
            progress_callback,
            50, 70
        )
        
        # Separate by finding type
        verified_risks = [f for f in verified_clauses if f.finding_type == "risk"]
        verified_compliance = [f for f in verified_clauses if f.finding_type == "compliance"]
        verified_redlining = [f for f in verified_clauses if f.finding_type == "redlining"]
        verified_clauses = [f for f in verified_clauses if f.finding_type == "clause"]
        
        if progress_callback:
            progress_callback("Resolving conflicts...", 75)
        
        # Resolve conflicts
        conflict_resolutions = self.conflict_resolver.resolve_all_conflicts(
            comparison.conflicts, contract_text
        )
        
        if progress_callback:
            progress_callback("Checking coverage...", 85)
        
        # Check coverage
        coverage_report = self.coverage_checker.check_coverage(
            verified_clauses, contract_text
        )
        
        # Calculate metadata
        all_findings = verified_clauses + verified_risks + verified_compliance + verified_redlining
        
        # Count findings from comprehensive results (count all clause blocks across all sections)
        total_before = 0
        for r in pass_results:
            # Count clause blocks in each section
            admin_count = sum(1 for field in vars(r.administrative_and_commercial_terms).values() if field is not None)
            tech_count = sum(1 for field in vars(r.technical_and_performance_terms).values() if field is not None)
            legal_count = sum(1 for field in vars(r.legal_risk_and_enforcement).values() if field is not None)
            reg_count = sum(1 for field in vars(r.regulatory_and_compliance_terms).values() if field is not None)
            data_count = sum(1 for field in vars(r.data_technology_and_deliverables).values() if field is not None)
            supp_count = len(r.supplemental_operational_risks)
            total_before += admin_count + tech_count + legal_count + reg_count + data_count + supp_count
        
        total_after = len(all_findings)
        hallucinations = sum(1 for f in all_findings if f.is_hallucinated)
        avg_confidence = self.scorer.calculate_average_confidence(
            [f.confidence_score for f in all_findings]
        ) if all_findings else 0.0
        
        duration = time.time() - start_time
        
        metadata = VerificationMetadata(
            num_passes=self.num_passes,
            pass_timestamps=pass_timestamps,
            total_findings_before_verification=total_before,
            total_findings_after_verification=total_after,
            hallucinations_detected=hallucinations,
            conflicts_found=len(comparison.conflicts),
            conflicts_resolved=sum(1 for r in conflict_resolutions if r.is_resolved),
            average_confidence_score=avg_confidence,
            verification_duration_seconds=duration,
            chunks_processed=total_chunks,
            total_tokens_processed=total_tokens
        )
        
        if progress_callback:
            progress_callback("Analysis complete!", 100)
        
        # Build final result
        result = VerifiedAnalysisResult(
            base_result=pass_results[0].to_dict() if pass_results else {},
            verified_clauses=verified_clauses,
            verified_risks=verified_risks,
            verified_compliance_issues=verified_compliance,
            verified_redlining_suggestions=verified_redlining,
            verification_metadata=metadata,
            coverage_report=coverage_report,
            conflicts=conflict_resolutions
        )
        
        logger.info(f"Exhaustive analysis complete: {total_after} verified findings, "
                   f"{hallucinations} hallucinations detected, {duration:.1f}s")
        
        return result

    
    def _analyze_chunk(self, chunk_text: str, file_path: str) -> ComprehensiveAnalysisResult:
        """
        Analyze a single chunk of contract text.
        
        Args:
            chunk_text: Text of the chunk to analyze
            file_path: Original file path for metadata
            
        Returns:
            ComprehensiveAnalysisResult for the chunk
        """
        # Use the OpenAI client directly for chunk analysis
        try:
            logger.info(f"Sending chunk to OpenAI ({len(chunk_text)} chars)")
            response = self.openai_client.analyze_contract(chunk_text)
            logger.info(f"OpenAI response received: {type(response)}")
            
            if not isinstance(response, dict):
                raise ValueError(f"Expected dict response from OpenAI, got {type(response)}")
            
            logger.debug(f"Response keys: {list(response.keys())}")
            
            # Parse the response into a ComprehensiveAnalysisResult
            from src.result_parser import ComprehensiveResultParser
            from src.schema_loader import SchemaLoader
            from src.schema_validator import SchemaValidator
            
            # Create parser with required dependencies
            schema_loader = SchemaLoader()
            schema_validator = SchemaValidator(schema_loader)
            parser = ComprehensiveResultParser(schema_validator)
            
            # Get file info for metadata
            file_info = self.analysis_engine.uploader.get_file_info(file_path)
            
            logger.info("Parsing API response into ComprehensiveAnalysisResult")
            result = parser.parse_api_response(
                api_response=response,
                filename=file_info['filename'],
                file_size_bytes=file_info['file_size_bytes'],
                page_count=file_info.get('page_count')
            )
            
            logger.info(f"Parsed result successfully: schema_version={result.schema_version}")
            return result
            
        except Exception as e:
            logger.error(f"Chunk analysis failed with error: {type(e).__name__}: {str(e)}", exc_info=True)
            raise
    
    def _verify_findings(
        self,
        findings: List[Dict[str, Any]],
        contract_text: str,
        default_type: str,
        progress_callback: Optional[Callable[[str, int], None]],
        progress_start: int,
        progress_end: int
    ) -> List[VerifiedFinding]:
        """
        Verify a list of findings against contract text.
        
        Args:
            findings: List of finding dictionaries
            contract_text: Original contract text
            default_type: Default finding type
            progress_callback: Optional progress callback
            progress_start: Starting progress percentage
            progress_end: Ending progress percentage
            
        Returns:
            List of VerifiedFinding objects
        """
        verified = []
        total = len(findings)
        
        for i, finding in enumerate(findings):
            if progress_callback and total > 0:
                progress = progress_start + ((progress_end - progress_start) * i // total)
                progress_callback(f"Verifying finding {i+1}/{total}...", progress)
            
            finding_type = finding.get('type', default_type)
            finding_data = finding.get('data', finding)
            passes_found = finding.get('passes_found_in', [0])
            
            # Calculate base confidence
            confidence = self.scorer.calculate_confidence(
                passes_with_finding=len(passes_found),
                total_passes=self.num_passes
            )
            
            # Verify finding
            verification = self.verification_layer.verify_finding(
                finding_data, contract_text, finding_type
            )
            
            # Check for hallucination
            hallucination_check = self.verification_layer.detect_hallucination(
                finding_data, contract_text, finding_type
            )
            
            # Adjust confidence based on verification
            if verification.is_verified:
                confidence = min(1.0, confidence + verification.confidence_adjustment)
            
            if hallucination_check.is_hallucinated:
                confidence = max(0.0, confidence - 0.5)
            
            # Determine presence status
            presence_status = self.scorer.determine_presence_status(
                confidence=confidence,
                passes_with_finding=len(passes_found),
                total_passes=self.num_passes,
                has_conflicts=False
            )
            
            verified_finding = VerifiedFinding(
                finding_type=finding_type,
                finding_data=finding_data,
                confidence_score=confidence,
                presence_status=presence_status,
                passes_found_in=len(passes_found),
                total_passes=self.num_passes,
                is_verified=verification.is_verified,
                verification_source=verification.supporting_text,
                is_hallucinated=hallucination_check.is_hallucinated,
                chunk_sources=finding.get('_chunk_sources', [])
            )
            
            verified.append(verified_finding)
        
        return verified
    
    def verify_query_response(
        self,
        query: str,
        response: str,
        contract_text: str,
        analysis_result: Optional[ComprehensiveAnalysisResult] = None
    ) -> VerifiedQueryResponse:
        """
        Verify a query response against the contract.
        
        Args:
            query: User's question
            response: Generated response to verify
            contract_text: Original contract text
            analysis_result: Optional analysis result for context
            
        Returns:
            VerifiedQueryResponse with verification status and sources
        """
        logger.info(f"Verifying query response: {query[:50]}...")
        
        # Use verification layer to verify the answer
        verification = self.verification_layer.verify_query_answer(
            query, response, contract_text
        )
        
        # Build source references
        source_refs = verification.source_references
        
        # Calculate confidence based on verification status
        if verification.verification_status == "verified":
            confidence = 0.95
        elif verification.verification_status == "partially_verified":
            confidence = 0.7
        elif verification.verification_status == "not_found":
            confidence = 0.3
        else:
            confidence = 0.5
        
        return VerifiedQueryResponse(
            query=query,
            response=response,
            is_verified=verification.is_verified,
            verification_status=verification.verification_status,
            verified_portions=verification.verified_portions,
            unverified_portions=verification.unverified_portions,
            source_references=source_refs,
            confidence_score=confidence
        )
