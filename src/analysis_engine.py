"""
Analysis Engine Module

Orchestrates the contract analysis workflow by integrating ContractUploader,
OpenAIClient, and ResultParser components.

Supports both standard and exhaustive analysis modes.
"""

import logging
from typing import Optional, Callable, Union
from src.contract_uploader import ContractUploader
from src.openai_fallback_client import OpenAIClient
from src.result_parser import ResultParser
from src.analysis_models import AnalysisResult
from src.exhaustiveness_models import VerifiedAnalysisResult

# Import clause extractor for focused analysis
try:
    from analyzer.contract_extractor import ComprehensiveContractExtractor
    EXTRACTOR_AVAILABLE = True
except ImportError:
    EXTRACTOR_AVAILABLE = False
    logger.warning("ComprehensiveContractExtractor not available, will use full contract text")


logger = logging.getLogger(__name__)


class AnalysisEngine:
    """
    Orchestrates contract analysis workflow.
    
    This class integrates:
    - ContractUploader for text extraction
    - OpenAIClient for API calls
    - ResultParser for response parsing
    
    It provides a high-level interface for analyzing contracts with progress callbacks.
    """
    
    def __init__(self, openai_api_key: str, model: str = "gpt-4o"):
        """
        Initialize Analysis Engine with OpenAI API key.
        
        Args:
            openai_api_key: OpenAI API key for contract analysis
            model: Model to use for analysis (default: gpt-4o)
        
        Raises:
            ValueError: If API key is invalid
        """
        logger.info("Initializing AnalysisEngine")
        
        # Initialize components
        self.uploader = ContractUploader()
        self.openai_client = OpenAIClient(api_key=openai_api_key, model=model)
        self.parser = ResultParser()
        
        # Initialize clause extractor if available
        self.extractor = None
        if EXTRACTOR_AVAILABLE:
            try:
                self.extractor = ComprehensiveContractExtractor()
                logger.info("ComprehensiveContractExtractor initialized - will use focused clause extraction")
            except Exception as e:
                logger.warning(f"Failed to initialize ComprehensiveContractExtractor: {e}")
        else:
            logger.warning("ComprehensiveContractExtractor not available - will analyze full contract text")
        
        logger.info("AnalysisEngine initialized successfully")
    
    def analyze_contract(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        exhaustive: bool = False,
        num_passes: int = 2,
        confidence_threshold: float = 0.7
    ) -> Union[AnalysisResult, VerifiedAnalysisResult]:
        """
        Analyze contract and return structured result.
        
        This method orchestrates the complete analysis workflow:
        1. Validate file format
        2. Extract text from contract
        3. Send to OpenAI API for analysis
        4. Parse and validate response
        5. Return structured AnalysisResult
        
        When exhaustive mode is enabled, performs multi-pass analysis with
        verification, hallucination detection, and confidence scoring.
        
        Args:
            file_path: Path to the contract file (PDF or DOCX)
            progress_callback: Optional callback function(status_message, percent) 
                             for progress updates
            exhaustive: If True, use exhaustive multi-pass analysis with verification
            num_passes: Number of analysis passes for exhaustive mode (2-5, default 2)
            confidence_threshold: Minimum confidence threshold for exhaustive mode
        
        Returns:
            AnalysisResult object for standard mode, or
            VerifiedAnalysisResult object for exhaustive mode
        
        Raises:
            ValueError: If file is invalid or analysis fails
            Exception: If any component fails during analysis
        """
        logger.info("Starting contract analysis for: %s (exhaustive=%s)", file_path, exhaustive)
        
        # Use exhaustive analysis if requested
        if exhaustive:
            return self._analyze_exhaustively(
                file_path, progress_callback, num_passes, confidence_threshold
            )
        
        # Standard analysis mode
        return self._analyze_standard(file_path, progress_callback)
    
    def _analyze_exhaustively(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        num_passes: int = 2,
        confidence_threshold: float = 0.7
    ) -> VerifiedAnalysisResult:
        """
        Perform exhaustive multi-pass analysis with verification.
        
        Args:
            file_path: Path to the contract file
            progress_callback: Optional progress callback
            num_passes: Number of analysis passes (2-5)
            confidence_threshold: Minimum confidence threshold
            
        Returns:
            VerifiedAnalysisResult with confidence scores and verification
        """
        from src.exhaustiveness_gate import ExhaustivenessGate
        
        logger.info("Starting exhaustive analysis with %d passes", num_passes)
        
        try:
            # Validate file first
            if progress_callback:
                progress_callback("Validating file format...", 2)
            
            is_valid, error_msg = self.uploader.validate_format(file_path)
            if not is_valid:
                logger.error("File validation failed: %s", error_msg)
                raise ValueError(f"File validation failed: {error_msg}")
            
            # Create exhaustiveness gate
            gate = ExhaustivenessGate(
                analysis_engine=self,
                openai_client=self.openai_client,
                num_passes=num_passes,
                confidence_threshold=confidence_threshold
            )
            
            # Run exhaustive analysis
            result = gate.analyze_contract_exhaustively(
                file_path=file_path,
                progress_callback=progress_callback
            )
            
            logger.info("Exhaustive analysis completed successfully")
            return result
            
        except ValueError:
            raise
        except Exception as e:
            error_msg = f"Exhaustive analysis failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg) from e
    
    def _analyze_standard(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> AnalysisResult:
        """
        Perform standard single-pass analysis.
        
        Args:
            file_path: Path to the contract file
            progress_callback: Optional progress callback
            
        Returns:
            AnalysisResult object
        """
        logger.info("Starting standard contract analysis for: %s", file_path)
        
        try:
            # Step 1: Validate file format
            if progress_callback:
                progress_callback("Validating file format...", 5)
            
            is_valid, error_msg = self.uploader.validate_format(file_path)
            if not is_valid:
                logger.error("File validation failed: %s", error_msg)
                raise ValueError(f"File validation failed: {error_msg}")
            
            logger.info("File validation passed")
            
            # Step 2: Get file information
            if progress_callback:
                progress_callback("Extracting file information...", 10)
            
            file_info = self.uploader.get_file_info(file_path)
            logger.debug("File info: %s", file_info)
            
            # Step 3: Extract text from contract
            if progress_callback:
                progress_callback("Extracting text from contract...", 20)
            
            contract_text = self.uploader.extract_text(file_path)
            logger.info("Extracted %d characters from contract", len(contract_text))
            
            if not contract_text or not contract_text.strip():
                error_msg = "No text could be extracted from the contract"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Step 3.5: Extract focused clause sections (if extractor available)
            analysis_text = contract_text
            if self.extractor:
                if progress_callback:
                    progress_callback("Extracting relevant clause sections...", 25)
                
                try:
                    focused_contract, extraction_metadata = self.extractor.create_focused_contract(contract_text)
                    
                    # Log extraction statistics
                    original_len = extraction_metadata.get('original_length', len(contract_text))
                    focused_len = extraction_metadata.get('focused_length', len(focused_contract))
                    reduction_pct = extraction_metadata.get('reduction_percent', 0)
                    categories_found = extraction_metadata.get('total_categories', 0)
                    
                    logger.info(f"Clause extraction: {original_len} chars -> {focused_len} chars ({reduction_pct:.1f}% reduction)")
                    logger.info(f"Found {categories_found} clause categories")
                    
                    # Use focused contract if extraction found substantial content
                    # If less than 10% was extracted, fall back to full text
                    if focused_len >= original_len * 0.1:
                        analysis_text = focused_contract
                        logger.info("Using focused clause extraction for analysis")
                    else:
                        logger.warning(f"Clause extraction found minimal content ({focused_len} chars), using full contract")
                        analysis_text = contract_text
                        
                except Exception as e:
                    logger.warning(f"Clause extraction failed: {e}, using full contract text")
                    analysis_text = contract_text
            else:
                logger.info("Clause extractor not available, using full contract text")
            
            # Step 4: Analyze contract with OpenAI
            # Step 4: Analyze contract with OpenAI
            if progress_callback:
                progress_callback("Analyzing contract with AI...", 30)
            
            # Create a wrapper callback that adjusts progress range (30-90%)
            def openai_progress_callback(status: str, percent: int):
                if progress_callback:
                    # Map 0-100% from OpenAI to 30-90% overall
                    adjusted_percent = 30 + int(percent * 0.6)
                    progress_callback(status, adjusted_percent)
            
            api_response = self.openai_client.analyze_contract(
                analysis_text,  # Use focused text if extraction succeeded, otherwise full text
                progress_callback=openai_progress_callback
            )
            
            logger.info("Received analysis response from OpenAI")
            
            # Step 5: Parse and validate response
            if progress_callback:
                progress_callback("Parsing analysis results...", 95)
            
            # Use comprehensive parser to get ComprehensiveAnalysisResult
            analysis_result = self.parser.parse_api_response(
                api_response=api_response,
                filename=file_info['filename'],
                file_size_bytes=file_info['file_size_bytes'],
                page_count=file_info.get('page_count')
            )
            
            logger.info("Analysis completed successfully")
            logger.info(f"Result type: {type(analysis_result)}")
            
            # Log what sections we got
            if hasattr(analysis_result, 'contract_overview'):
                logger.info("Got ComprehensiveAnalysisResult with contract_overview")
            elif hasattr(analysis_result, 'clauses'):
                logger.info("Got old AnalysisResult with clauses - this is wrong!")
            
            if progress_callback:
                progress_callback("Analysis complete!", 100)
            
            return analysis_result
            
        except ValueError as e:
            # Re-raise ValueError with original message
            logger.error("Analysis failed with ValueError: %s", e)
            raise
        
        except Exception as e:
            # Wrap other exceptions with context
            error_msg = f"Analysis failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg) from e
    
    def validate_api_key(self) -> bool:
        """
        Validate OpenAI API key.
        
        Returns:
            True if API key is valid, False otherwise
        """
        logger.debug("Validating OpenAI API key")
        try:
            is_valid = self.openai_client.validate_api_key()
            logger.info("API key validation result: %s", is_valid)
            return is_valid
        except Exception as e:
            logger.error("API key validation failed: %s", e)
            return False
