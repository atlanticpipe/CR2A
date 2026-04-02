"""
Analysis Engine Module

Orchestrates the contract analysis workflow by integrating ContractUploader,
AI model client (local Llama or Anthropic Claude), and ResultParser components.

Supports local Llama models and Claude API backends for AI analysis.
"""

import logging
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable, Dict, List, Tuple, Any
from contract_uploader import ContractUploader, page_from_char_position
from result_parser import ResultParser
from analysis_models import AnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class PreparedContract:
    """Holds pre-processed contract data (text extraction + regex + sections) for on-demand analysis."""
    file_path: str
    contract_text: str
    file_info: dict
    section_index: list
    exclude_zones: list
    extracted_clauses: dict = field(default_factory=dict)  # {cat_key: [matches]}
    indexed: object = None  # IndexedContract from DocumentRetriever
    contract_type: str = ""  # "municipal" | "federal" | "state" | "private"


class AnalysisEngine:
    """
    Orchestrates contract analysis workflow.

    This class integrates:
    - ContractUploader for text extraction
    - LocalModelClient for AI inference (Llama 3.1 8B)
    - ResultParser for response parsing

    It provides a high-level interface for analyzing contracts with progress callbacks.
    """

    def __init__(
        self,
        local_model_name: str = "llama-3.2-3b-q4",
        gpu_mode: str = "auto",
        ram_reserved_os_mb: int = None,
        gpu_offload_layers: int = None,
        ai_backend: str = "local",
        api_key: str = None,
        claude_model: str = "claude-sonnet",
    ):
        """
        Initialize Analysis Engine with local Llama model or Claude API.

        Args:
            local_model_name: Name of local model to use (default: llama-3.2-3b-q4)
            gpu_mode: "auto" (auto-detect), "cpu" (force CPU), or "gpu" (force GPU)
            ram_reserved_os_mb: MB reserved for OS (None = auto-detect)
            gpu_offload_layers: Explicit GPU layer count (None = use gpu_mode)
            ai_backend: "local" for Llama models, "claude" for Anthropic Claude API
            api_key: Anthropic API key (required when ai_backend="claude")
            claude_model: Claude model tier — "claude-sonnet" or "claude-opus"

        Raises:
            ValueError: If model cannot be loaded or API key is invalid
        """
        self.ai_backend = ai_backend
        logger.info(f"Initializing AnalysisEngine (backend={ai_backend})")

        # Initialize components
        # Auto-detect Tesseract path for OCR support
        tesseract_path = self._find_tesseract()
        if tesseract_path:
            logger.info(f"Found Tesseract at: {tesseract_path}")
            self.uploader = ContractUploader(tesseract_path=tesseract_path)
        else:
            logger.warning("Tesseract not found, OCR may not work")
            self.uploader = ContractUploader()
        self.parser = ResultParser()

        # Initialize AI client based on backend selection
        if ai_backend == "claude":
            logger.info(f"Using Claude API backend: {claude_model}")
            from anthropic_client import AnthropicClient

            if not api_key:
                raise ValueError(
                    "Anthropic API key is required for Claude backend.\n\n"
                    "Set the ANTHROPIC_API_KEY environment variable or "
                    "enter your key in Settings."
                )

            try:
                self.ai_client = AnthropicClient(
                    api_key=api_key,
                    model_name=claude_model,
                )
                logger.info("Claude API client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Claude API client: {e}")
                raise ValueError(
                    f"Failed to initialize Claude API client.\n\n"
                    f"Error: {e}\n\n"
                    "Check your API key and internet connection."
                )
        else:
            # Initialize local model
            logger.info(f"Using local model: {local_model_name}")
            from local_model_client import LocalModelClient
            from model_manager import ModelManager

            model_mgr = ModelManager()
            try:
                model_path = model_mgr.get_model_path(local_model_name)

                # Determine n_gpu_layers: explicit offload_layers takes priority
                if gpu_offload_layers is not None:
                    n_gpu_layers = None  # let LocalModelClient use gpu_offload_layers
                elif gpu_mode == "cpu":
                    n_gpu_layers = 0
                elif gpu_mode == "gpu":
                    n_gpu_layers = -1
                else:
                    n_gpu_layers = None  # auto-detect

                self.ai_client = LocalModelClient(
                    model_path=str(model_path),
                    model_name=local_model_name,
                    n_gpu_layers=n_gpu_layers,
                    ram_reserved_os_mb=ram_reserved_os_mb,
                    gpu_offload_layers=gpu_offload_layers,
                )
                logger.info("Local model client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize local model: {e}")
                raise ValueError(
                    f"Failed to load local model '{local_model_name}'.\n\n"
                    f"Error: {e}\n\n"
                    "Please download the model first:\n"
                    "Settings → Manage Models → Download"
                )

        # Initialize knowledge store for RAG-based learning
        from knowledge_store import KnowledgeStore
        self.knowledge_store = KnowledgeStore()
        self.knowledge_store.initialize()
        self.knowledge_store.load_and_index()

        logger.info("AnalysisEngine initialized successfully")

    def _find_tesseract(self) -> Optional[str]:
        """
        Auto-detect Tesseract OCR executable path.

        Checks common installation locations on Windows, Linux, and macOS.

        Returns:
            Path to tesseract executable if found, None otherwise
        """
        # Check if tesseract is in PATH
        tesseract_in_path = shutil.which('tesseract')
        if tesseract_in_path:
            return tesseract_in_path

        # Check common Windows installation paths
        if os.name == 'nt':  # Windows
            common_paths = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                Path.home() / 'AppData' / 'Local' / 'Tesseract-OCR' / 'tesseract.exe',
            ]

            for path in common_paths:
                if isinstance(path, str):
                    path = Path(path)
                if path.exists():
                    return str(path)

        # Check common Unix/Linux/Mac paths
        else:
            common_paths = [
                '/usr/bin/tesseract',
                '/usr/local/bin/tesseract',
                '/opt/homebrew/bin/tesseract',  # macOS Homebrew ARM
                Path.home() / '.local' / 'bin' / 'tesseract',
            ]

            for path in common_paths:
                if isinstance(path, str):
                    path = Path(path)
                if path.exists():
                    return str(path)

        return None

    def analyze_contract(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> AnalysisResult:
        """
        Analyze contract and return structured result.

        Args:
            file_path: Path to the contract file (PDF or DOCX)
            progress_callback: Optional callback function(status_message, percent)
                             for progress updates

        Returns:
            AnalysisResult object

        Raises:
            ValueError: If file is invalid or analysis fails
            Exception: If any component fails during analysis
        """
        logger.info("Starting contract analysis for: %s", file_path)
        return self._analyze_standard(file_path, progress_callback)

    def prepare_contract(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> PreparedContract:
        """
        Prepare a contract for on-demand analysis (no AI calls).

        Extracts text, parses sections, runs regex extraction.
        Returns a PreparedContract that can be used with analyze_single_category().
        """
        from analyzer.template_patterns import (
            extract_all_template_clauses, parse_contract_sections, detect_exclude_zones
        )

        logger.info("Preparing contract: %s", file_path)

        if progress_callback:
            progress_callback("Validating file format...", 10)

        is_valid, error_msg = self.uploader.validate_format(file_path)
        if not is_valid:
            raise ValueError(f"File validation failed: {error_msg}")

        if progress_callback:
            progress_callback("Extracting file information...", 20)

        file_info = self.uploader.get_file_info(file_path)

        if progress_callback:
            progress_callback("Extracting text from contract...", 30)

        # Sub-range callback: map uploader's 0-100% into our 30-50% range
        def extraction_progress(status, pct):
            if progress_callback:
                mapped = 30 + int(pct * 20 / 100)
                progress_callback(status, mapped)

        contract_text = self.uploader.extract_text(file_path, progress_callback=extraction_progress)
        if not contract_text or not contract_text.strip():
            raise ValueError("No text could be extracted from the contract")

        logger.info("Extracted %d characters from contract", len(contract_text))

        if progress_callback:
            progress_callback("Parsing contract structure...", 50)

        exclude_zones = detect_exclude_zones(contract_text)
        section_index = parse_contract_sections(contract_text, exclude_zones=exclude_zones)
        logger.info(f"Section parsing: {len(section_index)} sections detected")

        if progress_callback:
            progress_callback("Running pattern matching...", 70)

        extracted_clauses = extract_all_template_clauses(contract_text, section_index=section_index)
        regex_count = sum(len(v) for v in extracted_clauses.values())
        logger.info(f"Regex extraction found {regex_count} clauses across {len(extracted_clauses)} categories")

        if progress_callback:
            progress_callback("Building search index...", 85)

        # Build tri-layer retrieval index (regex map + keyword + TF-IDF)
        from document_retriever import DocumentRetriever
        retriever = DocumentRetriever()
        indexed = retriever.index_contract(contract_text, section_index, extracted_clauses)
        logger.info("Retrieval index built: %d sections indexed", len(section_index))

        if progress_callback:
            progress_callback("Contract loaded!", 100)

        return PreparedContract(
            file_path=file_path,
            contract_text=contract_text,
            file_info=file_info,
            section_index=section_index,
            exclude_zones=exclude_zones,
            extracted_clauses=extracted_clauses,
            indexed=indexed,
        )

    def analyze_single_category(
        self,
        prepared: PreparedContract,
        cat_key: str,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Optional[Tuple[str, str, dict, str, str]]:
        """
        Analyze a single clause category using tri-layer retrieval + AI.

        Three retrieval layers (regex, keyword, TF-IDF) find the most relevant
        contract sections. The AI reads the actual section text and summarizes.

        Args:
            prepared: PreparedContract from prepare_contract()
            cat_key: Category key from CATEGORY_MAP (e.g., "change_orders")
            progress_callback: Optional progress callback

        Returns:
            Tuple of (section_key, display_name, clause_block_dict, prompt_sent, ai_response)
            or None if not found
        """
        mapping = self.CATEGORY_MAP.get(cat_key)
        if not mapping:
            logger.warning(f"Unknown category key: {cat_key}")
            return None

        section_key, display_name = mapping
        logger.info(f"Analyzing single category: {display_name} ({cat_key})")

        if progress_callback:
            progress_callback(f"Retrieving sections for {display_name}...", 10)

        # Use tri-layer retrieval to find the right sections
        from document_retriever import DocumentRetriever
        retriever = DocumentRetriever()
        retriever._indexed = prepared.indexed

        results = retriever.retrieve_for_category(cat_key, top_k=5)
        if not results:
            logger.info(f"No sections retrieved for {cat_key}")
            return (section_key, display_name, None, "(no sections retrieved)", "NOT FOUND")

        # Minimum retrieval confidence — if the best section was only found
        # by a single weak layer (TF-IDF alone) with a low score, skip the AI
        # call. This avoids wasting time on hallucinated summaries from
        # completely unrelated sections.
        top = results[0]
        if top.combined_score < 0.025 and len(top.found_by) == 1:
            logger.info(f"Low confidence retrieval for {cat_key} "
                       f"(score={top.combined_score:.4f}, layers={top.found_by}), skipping AI")
            return (section_key, display_name, None, "(low retrieval confidence)", "NOT FOUND")

        section_text = retriever.format_sections_for_ai(results)
        if not section_text or not section_text.strip():
            return (section_key, display_name, None, "(empty section text)", "NOT FOUND")

        # Derive clause location from the top retrieved section header
        clause_location = top.section_header.upper() if top.section_header else "See contract"
        layers = ", ".join(top.found_by) if top.found_by else "unknown"
        logger.info(f"Retrieved {len(results)} sections for {cat_key} "
                    f"(top: score={top.combined_score:.4f}, found by: {layers})")

        # Derive page number from character position in extracted text
        from contract_uploader import page_from_char_position
        clause_page = None
        section_block = prepared.section_index[top.section_idx] if top.section_idx < len(prepared.section_index) else None
        if section_block:
            clause_page = page_from_char_position(prepared.indexed.contract_text, section_block.start_pos)

        if progress_callback:
            progress_callback(f"AI analyzing {display_name}...", 30)

        from analyzer.template_patterns import CATEGORY_SEARCH_DESCRIPTIONS
        cat_desc = CATEGORY_SEARCH_DESCRIPTIONS.get(cat_key, display_name)

        # Retrieve relevant past knowledge for this category
        knowledge_block = ""
        if self.knowledge_store and self.knowledge_store.entry_count() > 0:
            knowledge_entries = self.knowledge_store.retrieve_for_category(
                cat_key, contract_type=getattr(prepared, 'contract_type', '')
            )
            if knowledge_entries:
                knowledge_context = self.knowledge_store.format_for_prompt(knowledge_entries)
                if knowledge_context:
                    knowledge_block = (
                        f'[Reference from past analyses]\n{knowledge_context}\n'
                        f'Use the above as context only. Base your summary on the contract text below.\n\n'
                    )

        user_msg = (
            f'Category: {cat_desc}\n\n'
            f'{knowledge_block}'
            f'Below are sections from a construction contract. '
            f'If there are multiple distinct clauses about {cat_desc} in different '
            f'sections, describe each separately with ||| between them, prefixing '
            f'each with its section header in [brackets].\n'
            f'Only describe what is written in the text below.\n'
            f'If the text below is completely unrelated to {cat_desc}, '
            f'respond with exactly "NOT FOUND" and nothing else.\n\n'
            f'{section_text}'
        )

        try:
            raw = self.ai_client.generate(
                self._PER_ITEM_SYSTEM_MSG,
                user_msg,
                progress_callback=progress_callback,
                max_tokens=600
            )

            clause_summary = raw.strip() if raw else ""

            # Strip common preamble the small model likes to add
            clause_summary = re.sub(
                r'^(?:Here is a summary.*?:\s*\n*)',
                '', clause_summary, flags=re.IGNORECASE
            ).strip()

            # Check if AI says not found — still return prompt/response so GUI can log them
            summary_upper = clause_summary.upper()
            stripped_text = re.sub(r'[^A-Z]', '', summary_upper)
            # Check first ~150 chars for NOT FOUND signals to avoid false matches
            # in long summaries that mention "not found" incidentally
            first_chunk = summary_upper[:150]
            is_not_found = (
                summary_upper.startswith("NOT FOUND")
                or summary_upper.startswith("N/A")
                or summary_upper.startswith("NONE FOUND")
                or summary_upper.startswith("NO RELEVANT")
                or summary_upper.startswith("THIS CLAUSE IS NOT")
                or "NOT FOUND" in first_chunk
                or (stripped_text.count("NOTFOUND") >= 1 and
                    len(stripped_text.replace("NOTFOUND", "")) < 50)
            )
            if is_not_found:
                logger.info(f"AI determined {cat_key} not present in retrieved sections")
                return (section_key, display_name, None, user_msg, raw)

            if clause_summary:
                # Parse multi-clause responses separated by |||
                clause_blocks = self._parse_multi_clause_response(
                    clause_summary, results, prepared, clause_location, clause_page
                )
                if clause_blocks:
                    logger.info(f"FOUND: {display_name} ({len(clause_blocks)} instance(s))")
                    if progress_callback:
                        progress_callback(f"Analyzed {display_name}!", 100)
                    # Return list of clause_blocks via the object slot
                    return (section_key, display_name, clause_blocks, user_msg, raw)
            else:
                fallback = self._regex_fallback_for_category(prepared, cat_key, section_key, display_name)
                if fallback:
                    return (*fallback, user_msg, raw or "(empty)")
                return None

        except Exception as e:
            logger.warning(f"AI failed for {cat_key}: {e}")
            fallback = self._regex_fallback_for_category(prepared, cat_key, section_key, display_name)
            if fallback:
                return (*fallback, user_msg, f"(AI error: {e})")
            return None

    def _parse_multi_clause_response(
        self,
        ai_text: str,
        results: list,
        prepared: 'PreparedContract',
        default_location: str,
        default_page: Optional[int],
    ) -> List[dict]:
        """Parse AI response that may contain multiple clause instances separated by |||.

        Returns a list of clause_block dicts.  For a single-clause response the list
        has one element.
        """
        from contract_uploader import page_from_char_position

        # Split on ||| delimiter
        parts = [p.strip() for p in ai_text.split("|||") if p.strip()]
        if not parts:
            return []

        # Build a lookup: section_header_upper → (section_block, RetrievalResult)
        header_lookup = {}
        for r in results:
            h = r.section_header.upper() if r.section_header else ""
            if h:
                si = r.section_idx
                sb = prepared.section_index[si] if si < len(prepared.section_index) else None
                header_lookup[h] = (sb, r)

        clause_blocks: List[dict] = []
        for part in parts:
            # Try to extract a [SECTION HEADER] prefix from the summary
            loc_match = re.match(r'^\[([^\]]+)\]\s*', part)
            if loc_match:
                location = loc_match.group(1).strip().upper()
                summary = part[loc_match.end():].strip()
            else:
                location = default_location
                summary = part

            if not summary:
                continue

            # Resolve page from the matched section header
            page = default_page
            if location in header_lookup:
                sb, _ = header_lookup[location]
                if sb:
                    p = page_from_char_position(prepared.indexed.contract_text, sb.start_pos)
                    if p:
                        page = p
            else:
                # Fuzzy: try substring match against retrieved headers
                for h, (sb, _) in header_lookup.items():
                    if location in h or h in location:
                        if sb:
                            p = page_from_char_position(prepared.indexed.contract_text, sb.start_pos)
                            if p:
                                page = p
                        location = h  # normalise to the canonical header
                        break

            block: dict = {
                "Clause Location": location,
                "Clause Summary": summary,
            }
            if page:
                block["Clause Page"] = page
            clause_blocks.append(block)

        return clause_blocks

    @staticmethod
    def _get_location_from_section_index(position: int, section_index: list) -> str:
        """Derive a human-readable clause location from character position + section index."""
        if not section_index:
            return "See contract text"
        for section in section_index:
            if section.start_pos <= position < section.end_pos:
                header = section.header_text.strip()
                if header:
                    # Clean up long headers — just take first 120 chars
                    if len(header) > 120:
                        header = header[:120] + "..."
                    return header
        return "See contract text"

    def _regex_fallback_for_category(
        self,
        prepared: PreparedContract,
        cat_key: str,
        section_key: str,
        display_name: str
    ) -> Optional[Tuple[str, str, dict]]:
        """Return regex-only result for a category if available."""
        if cat_key in prepared.extracted_clauses:
            best = prepared.extracted_clauses[cat_key][0]
            conf = str(best.get('confidence', ''))
            ctx = best.get('context', best.get('matched_text', ''))
            if not conf.startswith('fuzzy') and ctx:
                position = best.get('position', 0)
                location = self._get_location_from_section_index(
                    position, prepared.section_index
                )
                from contract_uploader import page_from_char_position
                page = page_from_char_position(prepared.indexed.contract_text, position)
                block = {
                    "Clause Location": location,
                    "Clause Summary": ctx[:300],
                }
                if page:
                    block["Clause Page"] = page
                return (section_key, display_name, block)
        return None

    def build_comprehensive_result(
        self,
        prepared: PreparedContract,
        category_results: Dict[str, dict],
        overview: Optional[dict] = None,
        supplemental: Optional[list] = None
    ) -> 'ComprehensiveAnalysisResult':
        """
        Assemble a ComprehensiveAnalysisResult from accumulated per-category results.

        Args:
            prepared: PreparedContract with file info
            category_results: dict of {cat_key: clause_block_dict}
            overview: Optional contract overview dict
            supplemental: Optional supplemental risks list
        """
        from analysis_models import ComprehensiveAnalysisResult
        from result_parser import ComprehensiveResultParser
        from schema_loader import SchemaLoader
        from schema_validator import SchemaValidator

        response = {
            "schema_version": "v1.0.0",
            "contract_overview": overview or {
                "Project Title": "Contract Analysis",
                "Solicitation No.": "",
                "Owner": "See contract",
                "Contractor": "See contract",
                "Scope": "See extracted clauses below",
                "General Risk Level": "Medium",
                "Bid Model": "Other",
                "Notes": f"On-demand analysis: {len(category_results)} categories analyzed"
            },
            "administrative_and_commercial_terms": {},
            "technical_and_performance_terms": {},
            "legal_risk_and_enforcement": {},
            "regulatory_and_compliance_terms": {},
            "data_technology_and_deliverables": {},
            "supplemental_operational_risks": supplemental or []
        }

        for cat_key, clause_block in category_results.items():
            mapping = self.CATEGORY_MAP.get(cat_key)
            if not mapping or not clause_block:
                continue
            section_key, display_name = mapping
            response[section_key][display_name] = clause_block

        schema_loader = SchemaLoader()
        schema_validator = SchemaValidator(schema_loader)
        parser = ComprehensiveResultParser(schema_validator)

        result = parser.parse_api_response(
            api_response=response,
            filename=prepared.file_info.get('filename', ''),
            file_size_bytes=prepared.file_info.get('file_size_bytes', 0),
            page_count=prepared.file_info.get('page_count')
        )

        return result

    def _analyze_standard(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> 'ComprehensiveAnalysisResult':
        """
        Perform per-item AI analysis:
        1. Extract text and parse contract into structural sections
        2. Regex extraction provides candidate hints per category
        3. Per-item AI loop: one focused call per category searches relevant sections
        4. AI finds clause text AND provides 6-field analysis in each call
        5. Supplemental risks and contract overview via separate AI calls

        Args:
            file_path: Path to the contract file
            progress_callback: Optional progress callback

        Returns:
            ComprehensiveAnalysisResult object
        """
        from analysis_models import ComprehensiveAnalysisResult
        from result_parser import ComprehensiveResultParser
        from schema_loader import SchemaLoader
        from schema_validator import SchemaValidator
        from analyzer.template_patterns import extract_all_template_clauses, parse_contract_sections, detect_exclude_zones

        logger.info("Starting per-item AI analysis for: %s", file_path)

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
                progress_callback("Extracting text from contract...", 15)

            # Sub-range callback: map uploader's 0-100% into our 15-20% range
            def extraction_progress(status, pct):
                if progress_callback:
                    mapped = 15 + int(pct * 5 / 100)
                    progress_callback(status, mapped)

            contract_text = self.uploader.extract_text(file_path, progress_callback=extraction_progress)
            logger.info("Extracted %d characters from contract", len(contract_text))

            if not contract_text or not contract_text.strip():
                error_msg = "No text could be extracted from the contract"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Step 3.5: Parse contract into structural sections
            if progress_callback:
                progress_callback("Parsing contract structure...", 20)

            exclude_zones = detect_exclude_zones(contract_text)
            section_index = parse_contract_sections(contract_text, exclude_zones=exclude_zones)
            logger.info(f"Section parsing: {len(section_index)} sections detected")

            # Step 4: Programmatic extraction with regex (fast, deterministic)
            if progress_callback:
                progress_callback("Extracting clauses with regex patterns...", 25)

            extracted_clauses = extract_all_template_clauses(contract_text, section_index=section_index)
            regex_count = sum(len(v) for v in extracted_clauses.values())
            logger.info(f"Regex extraction found {regex_count} clauses across {len(extracted_clauses)} categories")

            # Step 4.5: Build tri-layer retrieval index
            if progress_callback:
                progress_callback("Building search index...", 25)

            from document_retriever import DocumentRetriever
            retriever = DocumentRetriever()
            indexed = retriever.index_contract(contract_text, section_index, extracted_clauses)

            # Step 5: Hybrid batched AI analysis using retrieved sections
            if progress_callback:
                progress_callback("Starting batched AI analysis...", 28)

            response = self._hybrid_batch_analysis(
                extracted_clauses, section_index, progress_callback,
                indexed_contract=indexed
            )

            # Step 6: Supplemental risks (Section VII)
            if progress_callback:
                progress_callback("Scanning for supplemental risks...", 82)

            try:
                supplemental = self._find_supplemental_risks(
                    contract_text, section_index, response, progress_callback
                )
                response["supplemental_operational_risks"] = supplemental
            except Exception as e:
                logger.warning(f"Supplemental risk scan failed: {e}")

            # Step 7: Use AI to generate contract overview (regex can't do this)
            if progress_callback:
                progress_callback("Generating contract overview with AI...", 84)

            try:
                overview = self._extract_contract_overview(contract_text)
                if overview:
                    response["contract_overview"] = overview
            except Exception as e:
                logger.warning(f"AI overview generation failed, using placeholder: {e}")

            # Log result structure
            for key in ['administrative_and_commercial_terms', 'technical_and_performance_terms',
                        'legal_risk_and_enforcement', 'regulatory_and_compliance_terms',
                        'data_technology_and_deliverables', 'supplemental_operational_risks']:
                section_data = response.get(key)
                if section_data:
                    if isinstance(section_data, dict):
                        non_null = [k for k, v in section_data.items() if v]
                        logger.info(f"  {key}: {len(non_null)} categories with data")
                    elif isinstance(section_data, list):
                        logger.info(f"  {key}: {len(section_data)} items")
                else:
                    logger.info(f"  {key}: EMPTY/MISSING")

            # Step 8: Parse response into ComprehensiveAnalysisResult
            if progress_callback:
                progress_callback("Parsing analysis results...", 85)

            schema_loader = SchemaLoader()
            schema_validator = SchemaValidator(schema_loader)
            parser = ComprehensiveResultParser(schema_validator)

            result = parser.parse_api_response(
                api_response=response,
                filename=file_info['filename'],
                file_size_bytes=file_info['file_size_bytes'],
                page_count=file_info.get('page_count')
            )

            logger.info("Hybrid analysis completed successfully")
            logger.info(f"Result type: {type(result)}")

            if progress_callback:
                progress_callback("Analysis complete!", 100)

            return result

        except ValueError as e:
            logger.error("Analysis failed with ValueError: %s", e)
            raise

        except Exception as e:
            error_msg = f"Analysis failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg) from e

    def _parse_ai_json_response(self, raw_response: str) -> dict:
        """
        Parse JSON from AI model response with robust error recovery.

        Handles common issues from small local models:
        - Markdown code blocks (```json ... ```)
        - Leading/trailing text around JSON
        - Double curly braces {{ }}
        - Unquoted property names
        - Trailing commas
        - Unclosed braces (truncated output)
        """
        import json as _json
        import re as _re

        text = raw_response.strip()

        if not text:
            raise ValueError("AI model returned empty response")

        # Strip markdown code blocks
        text = _re.sub(r'^```(?:json)?\s*\n?', '', text)
        text = _re.sub(r'\n?\s*```\s*$', '', text)

        # Find the outermost JSON object
        first_brace = text.find('{')
        last_brace = text.rfind('}')

        if first_brace == -1:
            logger.error(f"No JSON object found in response: {text[:200]}")
            raise ValueError(f"AI model did not return JSON. Response starts with: {text[:100]}")

        if last_brace <= first_brace:
            # Only opening brace found — try to close it
            text = text[first_brace:] + '}'
        else:
            text = text[first_brace:last_brace + 1]

        # Fix double curly braces {{ }} -> { }
        text = _re.sub(r'\{\{', '{', text)
        text = _re.sub(r'\}\}', '}', text)

        # Attempt 1: Parse as-is
        try:
            return _json.loads(text)
        except _json.JSONDecodeError as e:
            logger.warning(f"JSON parse attempt 1 failed: {e}")

        # Attempt 2: Fix trailing commas and unclosed braces
        repaired = text
        repaired = _re.sub(r',\s*([}\]])', r'\1', repaired)

        open_b = repaired.count('{')
        close_b = repaired.count('}')
        if open_b > close_b:
            repaired += '}' * (open_b - close_b)

        open_sq = repaired.count('[')
        close_sq = repaired.count(']')
        if open_sq > close_sq:
            repaired += ']' * (open_sq - close_sq)

        try:
            return _json.loads(repaired)
        except _json.JSONDecodeError as e:
            logger.warning(f"JSON parse attempt 2 failed: {e}")

        # Attempt 3: Try to fix unquoted keys (common with small models)
        # Pattern: { key: "value" } -> { "key": "value" }
        fixed = _re.sub(
            r'(?<=[{,])\s*([a-zA-Z_][a-zA-Z0-9_ ]*)\s*:',
            lambda m: f' "{m.group(1).strip()}":',
            repaired
        )
        try:
            return _json.loads(fixed)
        except _json.JSONDecodeError as e:
            logger.error(f"All JSON parse attempts failed: {e}")
            logger.error(f"Response (first 500 chars): {text[:500]}")
            raise ValueError(
                f"AI model returned invalid JSON. Parse error: {e}\n"
                f"Response preview: {text[:200]}..."
            )

    # Mapping from regex snake_case category keys → (section_key, display_name)
    CATEGORY_MAP = {
        # Section II: Administrative & Commercial Terms
        "contract_term_renewal_extensions": ("administrative_and_commercial_terms", "Contract Term, Renewal & Extensions"),
        "bonding_surety_insurance": ("administrative_and_commercial_terms", "Bonding, Surety, & Insurance Obligations"),
        "retainage_progress_payments": ("administrative_and_commercial_terms", "Retainage, Progress Payments & Final Payment Terms"),
        "pay_when_paid_if_paid": ("administrative_and_commercial_terms", "Pay-When-Paid, Pay-If-Paid, or Owner Payment Contingencies"),
        "price_escalation": ("administrative_and_commercial_terms", "Price Escalation Clauses (Labor, Materials, Fuel, Inflation Adjustments)"),
        "change_orders": ("administrative_and_commercial_terms", "Change Orders, Scope Adjustments & Modifications"),
        "termination_for_convenience": ("administrative_and_commercial_terms", "Termination for Convenience (Owner/Agency Right to Terminate Without Cause)"),
        "termination_for_cause": ("administrative_and_commercial_terms", "Termination for Cause / Default by Contractor"),
        "bid_protest": ("administrative_and_commercial_terms", "Bid Protest Procedures & Claims of Improper Award"),
        "bid_tabulation": ("administrative_and_commercial_terms", "Bid Tabulation, Competition & Award Process Requirements"),
        "contractor_qualification": ("administrative_and_commercial_terms", "Contractor Qualification, Licensing & Certification Requirements"),
        "release_orders": ("administrative_and_commercial_terms", "Release Orders, Task Orders & Work Authorization Protocols"),
        "assignment_novation": ("administrative_and_commercial_terms", "Assignment & Novation Restrictions (Transfer of Contract Rights)"),
        "audit_rights": ("administrative_and_commercial_terms", "Audit Rights, Recordkeeping & Document Retention Obligations"),
        "notice_requirements": ("administrative_and_commercial_terms", "Notice Requirements & Claim Timeframes (Notice to Cure, Delay Notices, Termination Notices, etc.)"),
        # Section III: Technical & Performance Terms
        "scope_of_work": ("technical_and_performance_terms", "Scope of Work (Work Inclusions, Exclusions & Defined Deliverables)"),
        "performance_schedule": ("technical_and_performance_terms", "Performance Schedule, Time for Completion & Critical Path Obligations"),
        "delays": ("technical_and_performance_terms", "Delays of Any Kind (Force Majeure, Acts of God, Weather, Owner-Caused, Unforeseen Events)"),
        "suspension_of_work": ("technical_and_performance_terms", "Suspension of Work, Work Stoppages & Agency Directives"),
        "submittals": ("technical_and_performance_terms", "Submittals, Documentation & Approval Requirements"),
        "emergency_work": ("technical_and_performance_terms", "Emergency & Contingency Work Obligations"),
        "permits_licensing": ("technical_and_performance_terms", "Permits, Licensing & Regulatory Approvals for Work"),
        "warranty": ("technical_and_performance_terms", "Warranty, Guarantee & Defects Liability Periods"),
        "use_of_aps_tools": ("technical_and_performance_terms", "Use of APS Tools, Equipment, Materials or Supplies"),
        "owner_supplied_support": ("technical_and_performance_terms", "Owner-Supplied Support, Utilities & Site Access Provisions"),
        "field_ticket": ("technical_and_performance_terms", "Field Ticket, Daily Work Log & Documentation Requirements"),
        "mobilization_demobilization": ("technical_and_performance_terms", "Mobilization & Demobilization Provisions"),
        "utility_coordination": ("technical_and_performance_terms", "Utility Coordination, Locate Risk & Conflict Avoidance"),
        "delivery_deadlines": ("technical_and_performance_terms", "Delivery Deadlines, Milestone Dates, Substantial & Final Completion Standards"),
        "punch_list": ("technical_and_performance_terms", "Punch List, Closeout Procedures & Acceptance of Work"),
        "worksite_coordination": ("technical_and_performance_terms", "Worksite Coordination, Access Restrictions & Sequencing Obligations"),
        "deliverables": ("technical_and_performance_terms", "Deliverables, Digital Submissions & Documentation Standards"),
        "emergency_contingency": ("technical_and_performance_terms", "Emergency Contingency Plans & Disaster Recovery Provisions"),
        # Section IV: Legal Risk & Enforcement
        "indemnification": ("legal_risk_and_enforcement", "Indemnification, Defense & Hold Harmless Provisions"),
        "duty_to_defend": ("legal_risk_and_enforcement", "Duty to Defend vs. Indemnify Scope Clarifications"),
        "limitation_of_liability": ("legal_risk_and_enforcement", "Limitations of Liability, Damage Caps & Waivers of Consequential Damages"),
        "insurance_coverage": ("legal_risk_and_enforcement", "Insurance Coverage, Additional Insured & Waiver of Subrogation Clauses"),
        "dispute_resolution": ("legal_risk_and_enforcement", "Dispute Resolution (Mediation, Arbitration, Litigation)"),
        "flow_down_clauses": ("legal_risk_and_enforcement", "Flow-Down Clauses (Prime-to-Subcontract Risk Pass-Through)"),
        "subcontracting": ("legal_risk_and_enforcement", "Subcontracting Restrictions, Approval & Substitution Requirements"),
        "safety_osha": ("legal_risk_and_enforcement", "Safety Standards, OSHA Compliance & Site-Specific Safety Obligations"),
        "site_conditions": ("legal_risk_and_enforcement", "Site Conditions, Differing Site Conditions & Changed Circumstances Clauses"),
        "environmental": ("legal_risk_and_enforcement", "Environmental Hazards, Waste Disposal & Hazardous Materials Provisions"),
        "order_of_precedence": ("legal_risk_and_enforcement", "Conflicting Documents / Order of Precedence Clauses"),
        "setoff_withholding": ("legal_risk_and_enforcement", "Setoff & Withholding Rights (Owner's Right to Deduct or Withhold Payment)"),
        # Section V: Regulatory & Compliance Terms
        "certified_payroll": ("regulatory_and_compliance_terms", "Certified Payroll, Recordkeeping & Reporting Obligations"),
        "prevailing_wage": ("regulatory_and_compliance_terms", "Prevailing Wage, Davis-Bacon & Federal/State Wage Compliance"),
        "eeo": ("regulatory_and_compliance_terms", "EEO, Non-Discrimination, MWBE/DBE Participation Requirements"),
        "mwbe_dbe": ("regulatory_and_compliance_terms", "MWBE/DBE Participation Goals & Utilization Requirements"),
        "apprenticeship": ("regulatory_and_compliance_terms", "Apprenticeship, Training & Workforce Development Requirements"),
        "e_verify": ("regulatory_and_compliance_terms", "Immigration / E-Verify Compliance Obligations"),
        "worker_classification": ("regulatory_and_compliance_terms", "Worker Classification & Independent Contractor Restrictions"),
        "drug_free_workplace": ("regulatory_and_compliance_terms", "Drug-Free Workplace Programs & Substance Testing Requirements"),
        # Section VI: Data, Technology & Deliverables
        "data_ownership": ("data_technology_and_deliverables", "Data Ownership, Access & Rights to Digital Deliverables"),

        "ai_technology_use": ("data_technology_and_deliverables", "AI / Technology Use Restrictions (Automation, Digital Tools, Proprietary Systems)"),
        "cybersecurity": ("data_technology_and_deliverables", "Cybersecurity Standards, Breach Notification & IT System Use Policies"),
        "digital_deliverables": ("data_technology_and_deliverables", "Digital Deliverables, BIM/CAD Requirements & Electronic Submissions"),
        "document_retention": ("data_technology_and_deliverables", "Document Retention, Records Preservation & Data Security Policies"),
        "confidentiality": ("data_technology_and_deliverables", "Confidentiality, Data Security & Records Retention Obligations"),
    }

    def _build_result_from_extraction(self, extracted_clauses: dict) -> dict:
        """
        Build a complete analysis result directly from regex/fuzzy extraction.

        This is the PRIMARY data source for sections 2-7. Each extracted clause
        becomes a ClauseBlock with the matched text as Clause Language and
        auto-generated summaries.
        """
        result = {
            "schema_version": "v1.0.0",
            "contract_overview": {
                "Project Title": "Contract Analysis",
                "Solicitation No.": "",
                "Owner": "See contract",
                "Contractor": "See contract",
                "Scope": "See extracted clauses below",
                "General Risk Level": "Medium",
                "Bid Model": "Other",
                "Notes": f"Analysis extracted {sum(len(v) for v in extracted_clauses.values())} clauses across {len(extracted_clauses)} categories"
            },
            "administrative_and_commercial_terms": {},
            "technical_and_performance_terms": {},
            "legal_risk_and_enforcement": {},
            "regulatory_and_compliance_terms": {},
            "data_technology_and_deliverables": {},
            "supplemental_operational_risks": []
        }

        unmapped_clauses = []

        for category_key, clauses in extracted_clauses.items():
            if not clauses:
                continue

            # Look up section and display name
            mapping = self.CATEGORY_MAP.get(category_key)
            if not mapping:
                # Try fuzzy key matching (normalize both sides)
                normalized = category_key.lower().replace(' ', '_').replace('-', '_')
                mapping = self.CATEGORY_MAP.get(normalized)

            if not mapping:
                # Unmapped category → goes to supplemental_operational_risks
                best_match = clauses[0]
                clause_text = best_match.get('context', best_match.get('matched_text', ''))
                if len(clause_text) > 2000:
                    clause_text = clause_text[:2000] + "\n[...truncated]"
                cat_label = category_key.replace('_', ' ').title()
                unmapped_clauses.append({
                    "Clause Location": clause_text[:200],
                    "Clause Summary": "",
                    "Flow-Down Obligations": [],
                    "Redline Recommendations": [],
                    "Harmful Language / Policy Conflicts": []
                })
                continue

            section_key, display_name = mapping

            # Build ClauseBlock from extracted clauses
            # Use CONTEXT (full surrounding text) as Clause Language, not matched_text (tiny regex match)
            # Merge multiple matches for the same category to get comprehensive coverage
            all_contexts = []
            for clause in clauses:
                ctx = clause.get('context', '').strip()
                if ctx and ctx not in all_contexts:
                    all_contexts.append(ctx)

            # Combine all unique contexts for this category
            if all_contexts:
                clause_text = "\n\n".join(all_contexts)
            else:
                # Fallback to matched_text if no context available
                clause_text = clauses[0].get('matched_text', '')

            # Truncate very long clause text (keep generous limit for full clauses)
            if len(clause_text) > 5000:
                clause_text = clause_text[:5000] + "\n[...truncated]"

            clause_block = {
                "Clause Location": clause_text[:200],
                "Clause Summary": "",
                "Flow-Down Obligations": [],
                "Redline Recommendations": [],
                "Harmful Language / Policy Conflicts": []
            }

            # Add to the appropriate section (don't overwrite if already exists)
            section = result[section_key]
            if display_name not in section:
                section[display_name] = clause_block

        # Add unmapped clauses to supplemental (max 9 per schema)
        result["supplemental_operational_risks"] = unmapped_clauses[:9]

        return result

    _VALIDATE_SYSTEM_MSG = (
        "You are a contract clause validator. For each category below, determine "
        "if the text excerpt actually discusses that contract topic. "
        "Respond with ONLY a JSON object mapping category names to true or false. "
        "true = text is relevant to the category. false = text is NOT about this topic."
    )

    def _validate_categories_with_ai(
        self,
        extracted_clauses: dict,
        progress_callback=None
    ) -> dict:
        """
        Use one compact AI call to validate that each extracted category's text
        actually discusses the assigned topic. Removes false positives where
        regex matched keywords in wrong sections (TOC, project info, etc.).

        Returns filtered dict with only validated categories.
        On failure, returns the original dict unchanged.
        """
        if not extracted_clauses:
            return extracted_clauses

        # Build compact snippet list for AI validation
        snippet_lines = ["Validate these contract clause extractions:\n"]
        category_keys = []
        display_names = []

        for i, (cat_key, clauses) in enumerate(extracted_clauses.items(), 1):
            display_name = cat_key.replace('_', ' ').title()

            # Get a 200-char snippet from the first clause's context
            snippet = ""
            if clauses:
                snippet = clauses[0].get('context', clauses[0].get('matched_text', ''))
            snippet = snippet[:200].replace('\n', ' ').strip()

            if snippet:
                snippet_lines.append(f'{i}. "{display_name}": "{snippet}"')
                category_keys.append(cat_key)
                display_names.append(display_name)

        if not category_keys:
            return extracted_clauses

        snippet_lines.append("\nRespond with JSON only: {\"Category Name\": true/false, ...}")
        user_msg = "\n".join(snippet_lines)

        try:
            raw = self.ai_client.generate(
                self._VALIDATE_SYSTEM_MSG,
                user_msg,
                progress_callback=progress_callback
            )
            validation = self._parse_ai_json_response(raw)

            if not isinstance(validation, dict):
                logger.warning("AI validation returned non-dict, skipping")
                return extracted_clauses

            # Filter categories: keep those validated as true (default to keep)
            validated = {}
            for cat_key, display_name in zip(category_keys, display_names):
                # Check both display name and snake_case key
                is_valid = validation.get(display_name, validation.get(cat_key, True))
                if is_valid is True or is_valid == "true" or is_valid == "True":
                    validated[cat_key] = extracted_clauses[cat_key]
                else:
                    logger.info(f"AI validation rejected: {cat_key}")

            return validated

        except Exception as e:
            logger.warning(f"AI validation call failed: {e}")
            return extracted_clauses

    # Section keys used for batching AI enhancement
    _SECTION_KEYS = [
        "administrative_and_commercial_terms",
        "technical_and_performance_terms",
        "legal_risk_and_enforcement",
        "regulatory_and_compliance_terms",
        "data_technology_and_deliverables",
    ]

    _ENHANCE_SYSTEM_MSG = (
        "You are a construction contract risk analyst. Analyze each clause below "
        "and respond with ONLY valid JSON, nothing else.\n\n"
        "For each clause category, provide:\n"
        "- \"Clause Location\": string describing where in the contract (section, article, page)\n"
        "- \"Clause Page\": integer page number where the clause appears (use the --- Page N --- markers "
        "in the text; set to null if not determinable)\n"
        "- \"Clause Summary\": brief, concise summary (1-2 sentences) of what the clause covers\n"
        "- \"Flow-Down\": array of obligations that must flow down to subcontractors\n"
        "- \"Redlines\": array of objects with \"action\" (insert/replace/delete) and \"text\" fields\n"
        "- \"Harmful Language\": array of problematic language or policy conflicts\n\n"
        "JSON format: {\"Category Name\": {\"Clause Location\": \"...\", \"Clause Page\": 5, "
        "\"Clause Summary\": \"...\", "
        "\"Flow-Down\": [...], \"Redlines\": [{\"action\": \"...\", \"text\": \"...\"}], "
        "\"Harmful Language\": [...]}, ...}"
    )

    def _enhance_with_ai(
        self,
        result: dict,
        extracted_clauses: dict,
        progress_callback=None
    ) -> dict:
        """
        Enhance regex-extracted results with AI analysis.

        Processes each section's categories through the local AI model to fill
        all ClauseBlock fields (Risk Triggers, Flow-Down, Redlines,
        Harmful Language). Categories are batched by section to fit within
        the model's context window.

        On failure, keeps the regex-only result for that section (graceful degradation).
        """
        MAX_CATEGORY_CHARS = 800  # Truncate each category's text to fit context
        MAX_BATCH_SIZE = 10       # Split sections with >10 categories

        total_sections = len(self._SECTION_KEYS)
        progress_start = 55
        progress_end = 80

        for section_idx, section_key in enumerate(self._SECTION_KEYS):
            section_data = result.get(section_key, {})
            if not section_data or not isinstance(section_data, dict):
                continue

            # Collect categories that have Clause Language to enhance
            categories_to_enhance = {}
            for display_name, clause_block in section_data.items():
                clause_text = (clause_block.get("Clause Location") or clause_block.get("Clause Language", "")
                              if isinstance(clause_block, dict) else "")
                if isinstance(clause_block, dict) and clause_text:
                    text = clause_text
                    if len(text) > MAX_CATEGORY_CHARS:
                        text = text[:MAX_CATEGORY_CHARS] + "..."
                    categories_to_enhance[display_name] = text

            if not categories_to_enhance:
                continue

            # Split into batches if needed
            cat_items = list(categories_to_enhance.items())
            batches = []
            for i in range(0, len(cat_items), MAX_BATCH_SIZE):
                batches.append(cat_items[i:i + MAX_BATCH_SIZE])

            section_label = section_key.replace("_", " ").title()

            for batch_idx, batch in enumerate(batches):
                batch_label = f" (batch {batch_idx + 1}/{len(batches)})" if len(batches) > 1 else ""
                pct = progress_start + int(
                    (progress_end - progress_start)
                    * (section_idx * len(batches) + batch_idx)
                    / (total_sections * max(len(batches), 1))
                )

                if progress_callback:
                    progress_callback(
                        f"AI analyzing {section_label}{batch_label}...", pct
                    )

                # Build user message with category texts
                user_parts = ["Analyze these contract clauses:\n"]
                for display_name, text in batch:
                    user_parts.append(f"=== {display_name} ===")
                    user_parts.append(text)
                    user_parts.append("")
                user_parts.append("Respond with JSON only.")
                user_msg = "\n".join(user_parts)

                try:
                    raw = self.ai_client.generate(
                        self._ENHANCE_SYSTEM_MSG,
                        user_msg,
                        progress_callback=progress_callback
                    )
                    ai_result = self._parse_ai_json_response(raw)

                    if not isinstance(ai_result, dict):
                        logger.warning(f"AI returned non-dict for {section_key}, skipping")
                        continue

                    # Merge AI results into the existing clause blocks
                    for display_name, _ in batch:
                        ai_clause = ai_result.get(display_name, {})
                        if not isinstance(ai_clause, dict):
                            continue

                        existing = section_data.get(display_name, {})
                        if not isinstance(existing, dict):
                            continue

                        # Update Clause Location
                        location = ai_clause.get("Clause Location", "")
                        if isinstance(location, str) and location:
                            existing["Clause Location"] = location

                        # Update Clause Page
                        page_num = ai_clause.get("Clause Page")
                        if isinstance(page_num, (int, float)) and page_num > 0:
                            existing["Clause Page"] = int(page_num)

                        # Update Clause Summary
                        summary = ai_clause.get("Clause Summary", "")
                        if isinstance(summary, str) and summary:
                            existing["Clause Summary"] = summary

                        # Update Flow-Down
                        flowdown = ai_clause.get("Flow-Down", [])
                        if isinstance(flowdown, list) and flowdown:
                            existing["Flow-Down Obligations"] = [
                                str(f) for f in flowdown
                            ]

                        # Update Redlines
                        redlines = ai_clause.get("Redlines", [])
                        if isinstance(redlines, list) and redlines:
                            parsed_redlines = []
                            for r in redlines:
                                if isinstance(r, dict) and "action" in r and "text" in r:
                                    action = r["action"]
                                    if action in ("insert", "replace", "delete"):
                                        parsed_redlines.append({
                                            "action": action,
                                            "text": str(r["text"])
                                        })
                            if parsed_redlines:
                                existing["Redline Recommendations"] = parsed_redlines

                        # Update Harmful Language
                        harmful = ai_clause.get("Harmful Language", [])
                        if isinstance(harmful, list) and harmful:
                            existing["Harmful Language / Policy Conflicts"] = [
                                str(h) for h in harmful
                            ]

                except Exception as e:
                    logger.warning(
                        f"AI enhancement failed for {section_key}{batch_label}: {e}"
                    )
                    # Keep regex-only result for this batch

        return result

    # =========================================================================
    # Per-Item AI Analysis (focused per-category search)
    # =========================================================================

    _PER_ITEM_SYSTEM_MSG = (
        "You are a construction contract analyst. "
        "You will receive several labeled sections from a contract. "
        "If there is ONE relevant clause, write a 1-3 sentence summary. "
        "If there are MULTIPLE DISTINCT clauses about the topic in DIFFERENT sections "
        "(e.g., notifications to the Owner vs. notifications to residents), "
        "write a separate 1-3 sentence summary for each and separate them with ||| on its own line. "
        "Prefix each summary with the section header in square brackets, e.g. [ARTICLE 5 - NOTICES]. "
        "Do NOT use bullet points, numbered lists, bold text, or sub-categories. "
        "Do NOT include preamble like 'Here is a summary'. "
        "Just write plain flowing sentences about what the contract says."
    )

    _BATCH_SUMMARIZE_SYSTEM_MSG = (
        "You are a construction contract clause analyst. "
        "You will receive multiple clause excerpts, each labeled with an ID like ### clause_id. "
        "For each clause, write a 1-3 sentence summary stating key terms, obligations, and deadlines. "
        "Return your answer as a JSON object mapping each clause ID to its summary string. "
        "Example: {\"change_orders_0\": \"The contractor must submit change order requests in writing within 10 days. "
        "Owner approval is required before proceeding.\", \"retainage_0\": \"5% retainage is withheld from each progress payment.\"} "
        "Return ONLY the JSON object, no other text."
    )

    # Default batch size for summarization — adjusted dynamically for small context windows
    _SUMMARIZE_BATCH_SIZE = 4

    def _hybrid_batch_analysis(
        self,
        extracted_clauses: dict,
        section_index: list,
        progress_callback=None,
        indexed_contract=None
    ) -> dict:
        """
        Batch-summarize categories using tri-layer retrieval + AI.

        Uses DocumentRetriever to find the right sections for each category,
        then sends actual section text to AI in batches for summarization.

        Args:
            extracted_clauses: Output of extract_all_template_clauses()
            section_index: Parsed section index for location derivation
            progress_callback: Optional progress callback
            indexed_contract: IndexedContract from DocumentRetriever

        Returns:
            response dict matching the comprehensive schema
        """
        import json as _json
        from document_retriever import DocumentRetriever

        # Set up retriever with the indexed contract
        retriever = DocumentRetriever()
        retriever._indexed = indexed_contract

        # --- Retrieve sections for ALL categories that have regex hits ---
        all_cat_keys = [ck for ck in extracted_clauses if extracted_clauses[ck]]
        total = len(all_cat_keys)
        # Adapt batch size to available context window
        batch_size = self._SUMMARIZE_BATCH_SIZE
        ctx_size = getattr(self.ai_client, 'n_ctx', 0)
        if ctx_size and ctx_size <= 8192:
            batch_size = 2  # Smaller batches for 8K context to avoid overflow
        logger.info(f"Batch analysis: {total} categories to summarize, "
                     f"batch size {batch_size} (ctx={ctx_size or 'api'})")

        # --- Retrieve + derive locations per category ---
        retrieved_texts = {}  # cat_key -> section text for AI
        locations = {}  # cat_key -> location string

        if progress_callback:
            progress_callback("Retrieving relevant sections...", 15)

        # Limit per-category text for small context windows
        max_chars_per_cat = 1000 if (ctx_size and ctx_size <= 8192) else 1500

        for cat_key in all_cat_keys:
            if indexed_contract is not None:
                results = retriever.retrieve_for_category(cat_key, top_k=3)
                if results:
                    retrieved_texts[cat_key] = retriever.format_sections_for_ai(results, max_chars=max_chars_per_cat)
                    locations[cat_key] = results[0].section_header.upper() if results[0].section_header else "See contract"
                    continue

            # Fallback if no retriever or no results: use regex context
            best = extracted_clauses[cat_key][0]
            ctx = best.get('context', best.get('matched_text', ''))
            if len(ctx) > max_chars_per_cat:
                ctx = ctx[:max_chars_per_cat]
            retrieved_texts[cat_key] = ctx
            pos = best.get('position', 0)
            locations[cat_key] = self._get_location_from_section_index(pos, section_index)

        logger.info(f"Retrieved section text for {len(retrieved_texts)} categories")

        # --- Batch-summarize with AI ---
        summaries = {}  # cat_key -> summary string
        cat_list = list(retrieved_texts.keys())
        total_batches = (len(cat_list) + batch_size - 1) // batch_size

        for batch_start in range(0, len(cat_list), batch_size):
            sub_keys = cat_list[batch_start:batch_start + batch_size]
            batch_num = batch_start // batch_size + 1
            pct = 25 + int(55 * batch_num / max(total_batches, 1))

            if progress_callback:
                progress_callback(
                    f"AI summarizing clauses (batch {batch_num}/{total_batches})...", pct
                )

            # Build prompt — each category's retrieved section text keyed by ID
            batch_ids = []
            clause_blocks = []
            for cat_key in sub_keys:
                clause_id = f"{cat_key}_0"
                text = retrieved_texts[cat_key]
                # Inject knowledge context (400 token budget in batch mode)
                if self.knowledge_store and self.knowledge_store.entry_count() > 0:
                    k_entries = self.knowledge_store.retrieve_for_category(cat_key)
                    k_context = self.knowledge_store.format_for_prompt(k_entries, max_tokens=400)
                    if k_context:
                        text = f"[Past knowledge: {k_context}]\n\n{text}"
                clause_blocks.append(f"### {clause_id}\n{text}")
                batch_ids.append(clause_id)

            user_msg = (
                "Summarize each clause below in 1-3 sentences. "
                "State the key terms, obligations, conditions, and deadlines.\n\n"
                + "\n\n".join(clause_blocks)
                + "\n\nReturn a JSON object mapping each clause ID to its summary:\n"
                + "{" + ", ".join(f'"{cid}": "summary..."' for cid in batch_ids) + "}"
            )

            try:
                raw = self.ai_client.generate(
                    self._BATCH_SUMMARIZE_SYSTEM_MSG, user_msg,
                    progress_callback=None,
                    max_tokens=2000
                )

                if not raw:
                    logger.warning(f"Batch {batch_num}: empty AI response")
                    continue

                logger.info(f"Batch {batch_num}/{total_batches} response ({len(raw)} chars): {raw[:200]}...")

                # Try JSON parsing first
                batch_parsed = False
                try:
                    parsed = self._parse_ai_json_response(raw)
                    if isinstance(parsed, dict):
                        for cid, summary in parsed.items():
                            if isinstance(summary, str) and summary.strip():
                                summaries[cid] = summary.strip()
                        logger.info(f"Batch {batch_num}: {len(parsed)} summaries parsed from JSON")
                        batch_parsed = True
                except Exception as json_err:
                    logger.warning(f"Batch {batch_num} JSON parse failed: {json_err}")

                # Fallback: extract sections delimited by ### clause_id headers
                if not batch_parsed and raw.strip():
                    import re as _re
                    for cid in batch_ids:
                        pattern = _re.escape(cid) + r'[:\s]*\n?(.*?)(?=###|\Z)'
                        match = _re.search(pattern, raw, _re.DOTALL)
                        if match:
                            text = match.group(1).strip().strip('"\'').strip()
                            if len(text) > 20:
                                summaries[cid] = text[:500]
                    if any(cid in summaries for cid in batch_ids):
                        logger.info(f"Batch {batch_num}: summaries extracted via plain-text fallback")

            except Exception as e:
                logger.error(f"Batch {batch_num} summarization failed: {e}")
                continue

        # --- Build response dict ---
        response = {
            "schema_version": "v1.0.0",
            "contract_overview": {
                "Project Title": "Contract Analysis",
                "Solicitation No.": "",
                "Owner": "See contract",
                "Contractor": "See contract",
                "Scope": "See extracted clauses below",
                "General Risk Level": "Medium",
                "Bid Model": "Other",
                "Notes": ""
            },
            "administrative_and_commercial_terms": {},
            "technical_and_performance_terms": {},
            "legal_risk_and_enforcement": {},
            "regulatory_and_compliance_terms": {},
            "data_technology_and_deliverables": {},
            "supplemental_operational_risks": []
        }

        # Populate: one clause block per category
        summarized_count = 0
        fallback_count = 0
        for cat_key in all_cat_keys:
            mapping = self.CATEGORY_MAP.get(cat_key)
            if not mapping:
                continue
            section_key, display_name = mapping
            if display_name in response[section_key]:
                continue

            clause_id = f"{cat_key}_0"
            location = locations.get(cat_key, "See contract text")
            summary = summaries.get(clause_id, "")

            if not summary:
                # Fallback: use first 200 chars of retrieved text as summary
                ctx = retrieved_texts.get(cat_key, "")
                summary = ctx[:200] if ctx else ""
                fallback_count += 1
            else:
                summarized_count += 1

            if not location and not summary:
                continue

            response[section_key][display_name] = {
                "Clause Location": location,
                "Clause Summary": summary,
                "Redline Recommendations": [],
                "Harmful Language / Policy Conflicts": [],
            }

        found = sum(
            len(v) for v in response.values() if isinstance(v, dict) and v
        )
        logger.info(f"Hybrid batch analysis complete: {found} categories populated "
                     f"({summarized_count} AI-summarized, {fallback_count} regex-only fallback)")
        return response

    def _per_item_ai_analysis(
        self,
        contract_text: str,
        section_index: list,
        extracted_clauses: dict,
        exclude_zones: list,
        progress_callback=None
    ) -> dict:
        """
        Perform per-item AI analysis: one focused AI call per category.

        For each of 61 template categories:
        1. Get relevant section text using section_index + CATEGORY_SECTION_HINTS
        2. Get regex candidate as a hint (if available)
        3. Ask AI to find and analyze the specific clause type
        4. Parse response and build ClauseBlock

        This replaces the batch validate + build + enhance pipeline with
        focused per-item search matching the CR2A Prompt Script approach.

        Returns:
            dict with section keys populated with ClauseBlock dicts
        """
        from analyzer.template_patterns import (
            get_relevant_text_for_category,
            CATEGORY_SEARCH_DESCRIPTIONS,
            TEMPLATE_PATTERNS
        )

        result = {
            "schema_version": "v1.0.0",
            "contract_overview": {
                "Project Title": "Contract Analysis",
                "Solicitation No.": "",
                "Owner": "See contract",
                "Contractor": "See contract",
                "Scope": "See extracted clauses below",
                "General Risk Level": "Medium",
                "Bid Model": "Other",
                "Notes": ""
            },
            "administrative_and_commercial_terms": {},
            "technical_and_performance_terms": {},
            "legal_risk_and_enforcement": {},
            "regulatory_and_compliance_terms": {},
            "data_technology_and_deliverables": {},
            "supplemental_operational_risks": []
        }

        categories = list(self.CATEGORY_MAP.items())
        total = len(categories)
        found_count = 0

        for i, (cat_key, (section_key, display_name)) in enumerate(categories):
            # Progress: 25% to 80% across all categories
            pct = 25 + int(55 * i / total)
            if progress_callback:
                progress_callback(
                    f"Analyzing {display_name} ({i + 1}/{total})...", pct
                )

            logger.info(f"Per-item AI [{i+1}/{total}]: {display_name}")

            # 1. Get relevant section text
            section_text = get_relevant_text_for_category(
                contract_text, cat_key, section_index
            )

            if not section_text or not section_text.strip():
                logger.info(f"  No relevant text found for {cat_key}, skipping")
                continue

            # 2. Get regex candidate as hint (if any)
            regex_hint = ""
            if cat_key in extracted_clauses:
                best = extracted_clauses[cat_key][0]
                hint_text = best.get('context', best.get('matched_text', ''))
                if hint_text:
                    regex_hint = hint_text[:500]

            # 3. Build focused prompt
            description = CATEGORY_SEARCH_DESCRIPTIONS.get(cat_key, display_name)
            user_parts = [
                f'Find the "{display_name}" clause in this contract text.',
                f"",
                f"What to look for: {description}",
                f"",
                f"CONTRACT TEXT:",
                section_text,
            ]
            if regex_hint:
                user_parts.extend([
                    "",
                    "CANDIDATE TEXT (found by pattern matching - may be incorrect):",
                    regex_hint,
                ])
            user_parts.extend([
                "",
                "Return JSON only in this format:",
                '{"found": true, "clause_location": "Section X, Article Y", "clause_page": 5, '
                '"clause_summary": "...", "flow_down": [], "redlines": [], "harmful_language": []}',
                'Use the --- Page N --- markers in the text to determine clause_page (integer). '
                'Set clause_page to null if not determinable. Set found to false if not present.'
            ])
            user_msg = "\n".join(user_parts)

            # 4. Call AI
            try:
                raw = self.ai_client.generate(
                    self._PER_ITEM_SYSTEM_MSG,
                    user_msg,
                    progress_callback=progress_callback
                )
                ai_result = self._parse_ai_json_response(raw)

                if not isinstance(ai_result, dict):
                    logger.warning(f"  AI returned non-dict for {cat_key}")
                    continue

                if ai_result.get("found"):
                    # Build ClauseBlock from AI response
                    clause_location = ai_result.get("clause_location", "")
                    if not clause_location and regex_hint:
                        clause_location = regex_hint[:200]

                    clause_summary = ai_result.get("clause_summary", "")

                    # Extract page number — prefer AI answer but validate/fix
                    # using character position if AI couldn't find markers
                    raw_page = ai_result.get("clause_page")
                    clause_page = int(raw_page) if isinstance(raw_page, (int, float)) and raw_page > 0 else None

                    # If AI couldn't determine page, compute from regex
                    # match character position in the full contract text
                    if clause_page is None and cat_key in extracted_clauses:
                        best_pos = extracted_clauses[cat_key][0].get('position')
                        if best_pos is not None:
                            clause_page = page_from_char_position(contract_text, best_pos)

                    # Parse redlines with validation
                    raw_redlines = ai_result.get("redlines", [])
                    parsed_redlines = []
                    if isinstance(raw_redlines, list):
                        for r in raw_redlines:
                            if isinstance(r, dict) and "action" in r and "text" in r:
                                action = r["action"]
                                if action in ("insert", "replace", "delete"):
                                    parsed_redlines.append({
                                        "action": action,
                                        "text": str(r["text"])
                                    })

                    clause_block: Dict[str, Any] = {
                        "Clause Location": clause_location,
                        "Clause Summary": clause_summary,
                        "Flow-Down Obligations": [
                            str(f) for f in ai_result.get("flow_down", [])
                            if f
                        ],
                        "Redline Recommendations": parsed_redlines,
                        "Harmful Language / Policy Conflicts": [
                            str(h) for h in ai_result.get("harmful_language", [])
                            if h
                        ]
                    }
                    if clause_page is not None:
                        clause_block["Clause Page"] = clause_page

                    result[section_key][display_name] = clause_block
                    found_count += 1
                    logger.info(f"  FOUND: {display_name} (location: {clause_location}, page: {clause_page})")
                else:
                    # AI didn't find it — fallback to regex if high-confidence
                    if cat_key in extracted_clauses:
                        best = extracted_clauses[cat_key][0]
                        conf = str(best.get('confidence', ''))
                        ctx = best.get('context', '')
                        # Only use regex fallback if it wasn't a fuzzy match
                        if not conf.startswith('fuzzy') and ctx:
                            fallback_block = {
                                "Clause Location": ctx[:200],
                                "Clause Summary": "",
                                "Flow-Down Obligations": [],
                                "Redline Recommendations": [],
                                "Harmful Language / Policy Conflicts": []
                            }
                            # Compute page from regex position
                            best_pos = best.get('position')
                            if best_pos is not None:
                                fb_page = page_from_char_position(contract_text, best_pos)
                                if fb_page is not None:
                                    fallback_block["Clause Page"] = fb_page
                            result[section_key][display_name] = fallback_block
                            found_count += 1
                            logger.info(f"  REGEX FALLBACK: {display_name}")
                        else:
                            logger.info(f"  NOT FOUND: {display_name}")
                    else:
                        logger.info(f"  NOT FOUND: {display_name}")

            except Exception as e:
                logger.warning(f"  AI failed for {cat_key}: {e}")
                # Graceful degradation: use regex result if available
                if cat_key in extracted_clauses:
                    best = extracted_clauses[cat_key][0]
                    ctx = best.get('context', best.get('matched_text', ''))
                    if ctx:
                        err_block = {
                            "Clause Location": ctx[:200],
                            "Clause Summary": "",
                            "Flow-Down Obligations": [],
                            "Redline Recommendations": [],
                            "Harmful Language / Policy Conflicts": []
                        }
                        best_pos = best.get('position')
                        if best_pos is not None:
                            err_page = page_from_char_position(contract_text, best_pos)
                            if err_page is not None:
                                err_block["Clause Page"] = err_page
                        result[section_key][display_name] = err_block
                        found_count += 1

        logger.info(f"Per-item AI analysis complete: {found_count}/{total} categories found")
        result["contract_overview"]["Notes"] = (
            f"Per-item AI analysis found {found_count} of {total} categories"
        )
        return result

    _SUPPLEMENTAL_SYSTEM_MSG = (
        "You are a construction contract risk analyst. Identify supplemental "
        "operational risks not covered by the standard categories.\n"
        "Respond with ONLY valid JSON.\n\n"
        "Return an array of risk items:\n"
        '[{"title": "Risk Title", "clause_location": "Section X, Article Y, Page Z", '
        '"clause_summary": "Brief summary of the risk."}]\n\n'
        'If no additional risks found: []'
    )

    def _find_supplemental_risks(
        self,
        contract_text: str,
        section_index: list,
        result: dict,
        progress_callback=None
    ) -> list:
        """
        Find supplemental operational risks (Section VII) not covered by
        the 61 standard categories in Sections II-VI.

        Scans general conditions text for additional risk-bearing clauses
        and returns up to 9 supplemental risk items.
        """
        from analyzer.template_patterns import get_relevant_text_for_category, _is_general_conditions_section

        # Collect names of categories that were found
        found_categories = []
        for section_key in self._SECTION_KEYS:
            section_data = result.get(section_key, {})
            if isinstance(section_data, dict):
                found_categories.extend(section_data.keys())

        # Get general conditions text (Division 00-01)
        gc_text_parts = []
        total_chars = 0
        max_chars = 12000
        for section in section_index:
            if section.section_type == 'flat':
                gc_text_parts.append(contract_text[:max_chars])
                total_chars = max_chars
                break
            if _is_general_conditions_section(section.header_normalized):
                chunk = contract_text[section.start_pos:section.end_pos]
                header = f"[{section.header_text.strip()}]"
                part = f"{header}\n{chunk}"
                if total_chars + len(part) > max_chars:
                    remaining = max_chars - total_chars
                    if remaining > 200:
                        gc_text_parts.append(part[:remaining])
                    break
                gc_text_parts.append(part)
                total_chars += len(part)

        if not gc_text_parts:
            # Fallback: use first 12K of contract
            gc_text = contract_text[:max_chars]
        else:
            gc_text = "\n\n---\n\n".join(gc_text_parts)

        found_list = ", ".join(found_categories[:30])  # Cap list length
        user_msg = (
            f"The following categories have already been analyzed:\n"
            f"{found_list}\n\n"
            f"Identify up to 9 ADDITIONAL risk-bearing clauses in this contract "
            f"text that are NOT covered by the categories above.\n"
            f"Each risk should have a descriptive title, the verbatim clause text, "
            f"and specific risk triggers.\n\n"
            f"CONTRACT TEXT:\n{gc_text}\n\n"
            f"Return JSON array only."
        )

        try:
            raw = self.ai_client.generate(
                self._SUPPLEMENTAL_SYSTEM_MSG,
                user_msg,
                progress_callback=progress_callback
            )
            ai_result = self._parse_ai_json_response(raw)

            supplemental = []
            items = ai_result if isinstance(ai_result, list) else []

            for item in items[:9]:  # Max 9 per schema
                if not isinstance(item, dict):
                    continue
                clause_block = {
                    "Clause Location": str(item.get("clause_location", "")),
                    "Clause Summary": str(item.get("clause_summary", "")),
                    "Flow-Down Obligations": [],
                    "Redline Recommendations": [],
                    "Harmful Language / Policy Conflicts": []
                }
                supplemental.append(clause_block)

            logger.info(f"Supplemental risks: found {len(supplemental)} items")
            return supplemental

        except Exception as e:
            logger.warning(f"Supplemental risk scan failed: {e}")
            return []

    def _generate_contract_overview(
        self,
        contract_text: str,
        progress_callback=None
    ) -> dict:
        """
        DEPRECATED: Use _extract_contract_overview() instead, which is more robust.

        Use AI to extract contract overview (parties, scope, risk level).

        This is a small, focused prompt that the 3B model can handle well.
        """
        # Use only the first ~2000 chars of the contract for overview
        overview_text = contract_text[:3000]

        system_msg = (
            "Extract contract metadata. Respond with ONLY valid JSON, nothing else.\n"
            "Format: "
            '{"Project Title": "...", "Solicitation No.": "...", "Owner": "...", '
            '"Contractor": "...", "Scope": "brief description", '
            '"General Risk Level": "Low|Medium|High|Critical", '
            '"Bid Model": "Lump Sum|Unit Price|Cost Plus|Time & Materials|GMP|Design-Build|Other", '
            '"Notes": "..."}'
        )

        user_msg = f"Extract metadata from this contract:\n\n{overview_text}"

        try:
            raw = self.ai_client.generate(system_msg, user_msg, progress_callback=progress_callback)
            overview = self._parse_ai_json_response(raw)
            if isinstance(overview, dict) and "Project Title" in overview:
                return overview
            logger.warning("AI overview missing expected fields, using regex-only")
            return None
        except Exception as e:
            logger.warning(f"AI overview failed: {e}")
            return None

    def _build_extraction_text(
        self,
        original_text: str,
        extracted_clauses: dict
    ) -> str:
        """
        Build extraction text combining regex highlights + contract text.

        The AI receives TWO things:
        1. REGEX INDEX: Which categories were found and where (guides the AI)
        2. CONTRACT TEXT: Front matter + back matter of the contract (the actual content)

        For large documents (like 534-page construction specs), contract clauses
        are typically in the front matter (general conditions, terms) and back
        matter (exhibits, special conditions). The middle is often engineering
        drawings/specs that don't contain clauses.

        Args:
            original_text: Full contract text
            extracted_clauses: Dict of category -> list of clause matches

        Returns:
            Combined extraction text for AI prompt
        """
        # Budget: compute from model context size
        # Keep prompt small for fast CPU inference
        context_size = getattr(self.ai_client, 'DEFAULT_CONTEXT_SIZE', 8192)
        response_reserve = min(4000, context_size // 4)  # reserve for JSON output
        overhead_reserve = 1500  # tokens for system message + chat template
        available_tokens = context_size - response_reserve - overhead_reserve
        # ~3.5 chars per token (conservative estimate for Llama tokenizer)
        MAX_TOTAL_CHARS = max(int(available_tokens * 3.5), 10000)
        parts = []

        # ─── PART 1: REGEX EXTRACTION INDEX ───
        # This tells the AI which categories regex found and where
        parts.append("=" * 60)
        parts.append("REGEX EXTRACTION INDEX")
        parts.append("Pattern matching identified these clause categories:")
        parts.append("=" * 60)

        total_regex_matches = sum(len(v) for v in extracted_clauses.values())
        parts.append(f"\nTotal: {total_regex_matches} matches across {len(extracted_clauses)} categories\n")

        # List categories found with representative text snippets
        for category, clauses in sorted(extracted_clauses.items()):
            cat_display = category.replace('_', ' ').title()
            first_match = clauses[0].get('matched_text', '')[:100]
            parts.append(f"  - {cat_display} ({len(clauses)} match{'es' if len(clauses) > 1 else ''}): \"{first_match}...\"")

        parts.append("")

        # ─── PART 2: CONTRACT TEXT ───
        # Include substantial portions of the actual contract
        contract_len = len(original_text)

        if contract_len <= MAX_TOTAL_CHARS:
            # Small enough to include everything
            parts.append("=" * 60)
            parts.append("FULL CONTRACT TEXT")
            parts.append("=" * 60)
            parts.append(original_text)
        else:
            # Large document: include front matter + back matter
            # Front matter: first 60% of budget (general conditions, terms, specs)
            front_budget = int(MAX_TOTAL_CHARS * 0.60)
            # Back matter: last 30% of budget (exhibits, special conditions)
            back_budget = int(MAX_TOTAL_CHARS * 0.30)

            parts.append("=" * 60)
            parts.append("CONTRACT TEXT (FRONT MATTER - General Conditions & Terms)")
            parts.append("=" * 60)
            parts.append(original_text[:front_budget])

            parts.append("")
            parts.append("=" * 60)
            parts.append(f"[... {contract_len - front_budget - back_budget:,} characters of technical drawings/specs omitted ...]")
            parts.append("=" * 60)
            parts.append("")

            parts.append("=" * 60)
            parts.append("CONTRACT TEXT (BACK MATTER - Exhibits & Special Conditions)")
            parts.append("=" * 60)
            parts.append(original_text[-back_budget:])

        return "\n".join(parts)

    def _normalize_category_for_template(self, category_name: str) -> str:
        """
        Normalize fuzzy matcher category names to template_patterns format.

        Fuzzy matcher uses "Contract Term, Renewal & Extensions" format.
        Template patterns use "contract_term_renewal_extensions" format.

        Args:
            category_name: Category name in any format

        Returns:
            Normalized category name (lowercase with underscores)
        """
        normalized = category_name.lower()
        normalized = normalized.replace(' & ', ' ')
        normalized = normalized.replace('&', ' ')
        normalized = normalized.replace(',', '')
        normalized = normalized.replace('/', ' ')
        normalized = normalized.replace('(', '')
        normalized = normalized.replace(')', '')
        normalized = '_'.join(normalized.split())
        while '__' in normalized:
            normalized = normalized.replace('__', '_')
        return normalized.strip('_')

    def _extract_contract_overview(self, contract_text: str) -> dict:
        """
        Extract basic contract overview information (8 required fields).

        Uses AI for quick extraction of high-level contract information.
        This is separate from clause extraction and remains fast/reliable.

        Args:
            contract_text: Full contract text

        Returns:
            Dictionary with overview fields
        """
        import json

        logger.info("Extracting contract overview (8 fields)")

        # Create focused prompt for overview extraction
        prompt = f"""Extract the following 8 fields from this contract:

1. **Project Title**: The name or title of the project
2. **Solicitation Number**: Contract/solicitation/RFP number
3. **Owner**: The owner/client organization name
4. **Contractor**: The contractor/vendor organization name
5. **Scope**: Brief description of work scope (1-2 sentences)
6. **General Risk Level**: Overall risk assessment ("Low", "Medium", "High", or "Critical")
7. **Bid Model**: Pricing model ("Lump Sum", "Unit Price", "Cost Plus", "Time & Materials", "GMP", "Design-Build", or "Other")
8. **Notes**: Any notable observations about the contract

**Contract Text (first 5000 chars):**
{contract_text[:5000]}

**Output Format (JSON only):**
{{
  "project_title": "...",
  "solicitation_no": "...",
  "owner": "...",
  "contractor": "...",
  "scope": "...",
  "general_risk_level": "Medium",
  "bid_model": "Lump Sum",
  "notes": "..."
}}

Output ONLY valid JSON, no explanations."""

        try:
            # Make API call using Responses API for GPT-5 models
            logger.info(f"Using model: {self.ai_client.model} for overview extraction")

            system_msg = "You are a contract analysis expert. You must respond ONLY with valid JSON in the exact format specified, with no additional text before or after."

            content = self.ai_client.generate(system_msg, prompt)

            # Log response details for debugging
            logger.info(f"API response received")

            content = content.strip()

            # Log the raw response for debugging
            logger.info(f"Raw overview response (first 300 chars): {content[:300]}")

            # Remove markdown code blocks if present
            if content.startswith('```'):
                lines = content.split('\n')
                # Remove first line (```)
                lines = lines[1:]
                # Remove json language identifier if present
                if lines and lines[0].strip().lower() == 'json':
                    lines = lines[1:]
                # Find closing ``` and remove everything after
                for i, line in enumerate(lines):
                    if line.strip() == '```':
                        lines = lines[:i]
                        break
                content = '\n'.join(lines).strip()

            overview_data = json.loads(content)

            logger.info("Contract overview extracted successfully")
            return overview_data

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in contract overview: {e}")
            logger.error(f"Response content (first 500 chars): {content[:500] if 'content' in locals() else 'No response'}")
            # Return defaults if JSON parsing fails
            return {
                "project_title": "Unknown Project",
                "solicitation_no": "N/A",
                "owner": "Unknown",
                "contractor": "Unknown",
                "scope": "Contract analysis in progress",
                "general_risk_level": "Medium",
                "bid_model": "Other",
                "notes": f"Overview extraction failed: JSON parse error - {str(e)}"
            }
        except ValueError as e:
            # Catch our custom ValueError for empty/None content
            error_msg = str(e)
            logger.error(f"ValueError in overview extraction: {error_msg}")
            return {
                "project_title": "Unknown Project",
                "solicitation_no": "N/A",
                "owner": "Unknown",
                "contractor": "Unknown",
                "scope": "Contract analysis in progress",
                "general_risk_level": "Medium",
                "bid_model": "Other",
                "notes": f"Overview extraction failed: {error_msg}"
            }
        except Exception as e:
            # Catch any other exceptions including AI model errors
            import traceback
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"{error_type} in overview extraction: {error_msg}")
            logger.error(f"Full traceback: {traceback.format_exc()}")

            error_note = f"Overview extraction failed: {error_type} - {error_msg}"

            logger.warning(f"Failed to extract contract overview: {error_note}, using defaults")
            # Return defaults if extraction fails
            return {
                "project_title": "Unknown Project",
                "solicitation_no": "N/A",
                "owner": "Unknown",
                "contractor": "Unknown",
                "scope": "Contract analysis in progress",
                "general_risk_level": "Medium",
                "bid_model": "Other",
                "notes": error_note
            }

    def _build_comprehensive_result(
        self,
        hybrid_result: dict,
        overview_data: dict,
        file_info: dict
    ):
        """
        Build ComprehensiveAnalysisResult from hybrid analysis output.

        Args:
            hybrid_result: Output from HybridAnalysisEngine.analyze_contract_hybrid()
            overview_data: Contract overview fields
            file_info: File metadata (filename, size, pages)

        Returns:
            ComprehensiveAnalysisResult object
        """
        from analysis_models import (
            ComprehensiveAnalysisResult,
            ContractOverview,
            ContractMetadata,
            AdministrativeAndCommercialTerms,
            TechnicalAndPerformanceTerms,
            LegalRiskAndEnforcement,
            RegulatoryAndComplianceTerms,
            DataTechnologyAndDeliverables,
            ClauseBlock,
            RedlineRecommendation
        )
        from datetime import datetime

        logger.info("Building ComprehensiveAnalysisResult from hybrid output")

        # Build contract overview
        contract_overview = ContractOverview(
            project_title=overview_data.get('project_title', 'Unknown'),
            solicitation_no=overview_data.get('solicitation_no', 'N/A'),
            owner=overview_data.get('owner', 'Unknown'),
            contractor=overview_data.get('contractor', 'Unknown'),
            scope=overview_data.get('scope', ''),
            general_risk_level=overview_data.get('general_risk_level', 'Medium'),
            bid_model=overview_data.get('bid_model', 'Other'),
            notes=overview_data.get('notes', '')
        )

        # Build metadata
        metadata = ContractMetadata(
            filename=file_info['filename'],
            analyzed_at=datetime.now(),
            file_size_bytes=file_info['file_size_bytes'],
            page_count=file_info.get('page_count')
        )

        # Helper function to convert redline dicts to RedlineRecommendation objects
        def convert_redline(redline_dict):
            """Convert a redline dict to RedlineRecommendation object."""
            if isinstance(redline_dict, RedlineRecommendation):
                return redline_dict  # Already an object

            # Normalize action: map common variations to valid actions
            # Valid actions: "delete", "insert", "replace"
            action = redline_dict.get('action', 'insert').lower()
            action_mapping = {
                'add': 'insert',
                'insert': 'insert',
                'remove': 'delete',
                'delete': 'delete',
                'change': 'replace',
                'replace': 'replace',
                'modify': 'replace',
                'update': 'replace'
            }
            normalized_action = action_mapping.get(action, 'insert')

            # Convert dict to RedlineRecommendation
            # AI returns {"action": "...", "text": "...", "reason": "..."}
            # Schema expects {"action": "...", "text": "...", "reference": "..."}
            return RedlineRecommendation(
                action=normalized_action,
                text=redline_dict.get('text', ''),
                reference=redline_dict.get('reason') or redline_dict.get('reference')
            )

        # Helper function to merge multiple clauses into a single ClauseBlock
        def merge_clauses_to_block(clause_list: list) -> Optional[ClauseBlock]:
            """Merge multiple clause instances into a single ClauseBlock."""
            if not clause_list:
                return None

            # If only one clause, convert directly
            if len(clause_list) == 1:
                clause_data = clause_list[0]
                # Convert redline dicts to RedlineRecommendation objects
                redlines = [convert_redline(r) for r in clause_data.get('redline_recommendations', [])]

                return ClauseBlock(
                    clause_location=(clause_data.get('clause_location') or clause_data.get('clause_language', ''))[:200],
                    clause_summary=clause_data.get('clause_summary', ''),
                    redline_recommendations=redlines,
                    harmful_language_policy_conflicts=clause_data.get('harmful_language_policy_conflicts', [])
                )

            # Multiple clauses - merge them
            merged_location_parts = []
            merged_summary_parts = []
            merged_redlines = []
            merged_conflicts = []

            for i, clause_data in enumerate(clause_list):
                # Collect locations
                loc = clause_data.get('clause_location') or clause_data.get('clause_language', '')
                if loc:
                    merged_location_parts.append(f"[Instance {i+1}] {loc[:200]}")

                # Collect summaries
                summary = clause_data.get('clause_summary', '')
                if summary:
                    merged_summary_parts.append(summary)

                # Collect redlines (convert dicts to objects)
                for redline_dict in clause_data.get('redline_recommendations', []):
                    merged_redlines.append(convert_redline(redline_dict))

                # Collect conflicts (deduplicate)
                for conflict in clause_data.get('harmful_language_policy_conflicts', []):
                    if conflict not in merged_conflicts:
                        merged_conflicts.append(conflict)

            return ClauseBlock(
                clause_location="; ".join(merged_location_parts),
                clause_summary=" | ".join(merged_summary_parts) if merged_summary_parts else "",
                redline_recommendations=merged_redlines,
                harmful_language_policy_conflicts=merged_conflicts
            )

        # Extract sections from hybrid result
        sections = hybrid_result.get('sections', {})

        # Build Section II: Administrative and Commercial Terms
        # Note: Field names must match analysis_models.py exactly
        admin_section = sections.get('administrative_and_commercial_terms', {})
        administrative_terms = AdministrativeAndCommercialTerms(
            contract_term_renewal_extensions=merge_clauses_to_block(admin_section.get('contract_term_renewal_extensions', [])),
            bonding_surety_insurance=merge_clauses_to_block(admin_section.get('bonding_surety_insurance', [])),
            retainage_progress_payments=merge_clauses_to_block(admin_section.get('retainage_progress_payments', [])),
            pay_when_paid=merge_clauses_to_block(admin_section.get('pay_when_paid_if_paid', [])),  # Schema uses 'pay_when_paid'
            price_escalation=merge_clauses_to_block(admin_section.get('price_escalation', [])),
            change_orders=merge_clauses_to_block(admin_section.get('change_orders', [])),
            termination_for_convenience=merge_clauses_to_block(admin_section.get('termination_for_convenience', [])),
            termination_for_cause=merge_clauses_to_block(admin_section.get('termination_for_cause', [])),
            bid_protest_procedures=merge_clauses_to_block(admin_section.get('bid_protest', [])),  # Schema uses 'bid_protest_procedures'
            bid_tabulation=merge_clauses_to_block(admin_section.get('bid_tabulation', [])),
            contractor_qualification=merge_clauses_to_block(admin_section.get('contractor_qualification', [])),
            release_orders=merge_clauses_to_block(admin_section.get('release_orders', [])),
            assignment_novation=merge_clauses_to_block(admin_section.get('assignment_novation', [])),
            audit_rights=merge_clauses_to_block(admin_section.get('audit_rights', [])),
            notice_requirements=merge_clauses_to_block(admin_section.get('notice_requirements', []))
        )

        # Build Section III: Technical and Performance Terms
        # Map hybrid engine names to schema field names
        technical_section = sections.get('technical_and_performance_terms', {})
        technical_terms = TechnicalAndPerformanceTerms(
            scope_of_work=merge_clauses_to_block(technical_section.get('scope_of_work', [])),
            performance_schedule=merge_clauses_to_block(technical_section.get('performance_schedule', [])),
            delays=merge_clauses_to_block(technical_section.get('delays', [])),
            suspension_of_work=merge_clauses_to_block(technical_section.get('suspension_of_work', [])),
            submittals=merge_clauses_to_block(technical_section.get('submittals', [])),
            emergency_contingency=merge_clauses_to_block(technical_section.get('emergency_work', [])),  # Schema uses 'emergency_contingency'
            permits_licensing=merge_clauses_to_block(technical_section.get('permits_licensing', [])),
            warranty=merge_clauses_to_block(technical_section.get('warranty', [])),
            # Additional schema fields not in hybrid engine yet
            use_of_aps_tools=None,
            owner_supplied_support=None,
            field_ticket=None,
            mobilization_demobilization=None,
            utility_coordination=None,
            delivery_deadlines=None,
            punch_list=None,
            worksite_coordination=None,
            deliverables=None
        )

        # Build Section IV: Legal Risk and Enforcement
        # Map hybrid engine names to schema field names
        legal_section = sections.get('legal_risk_and_enforcement', {})
        legal_risk = LegalRiskAndEnforcement(
            indemnification=merge_clauses_to_block(legal_section.get('indemnification', [])),
            duty_to_defend=merge_clauses_to_block(legal_section.get('duty_to_defend', [])),
            limitations_of_liability=merge_clauses_to_block(legal_section.get('limitation_of_liability', [])),  # Schema uses plural
            insurance_coverage=merge_clauses_to_block(legal_section.get('insurance_coverage', [])),
            dispute_resolution=merge_clauses_to_block(legal_section.get('dispute_resolution', [])),
            flow_down_clauses=merge_clauses_to_block(legal_section.get('flow_down_clauses', [])),
            subcontracting_restrictions=merge_clauses_to_block(legal_section.get('subcontracting', [])),  # Schema uses 'subcontracting_restrictions'
            background_screening=None,  # Not in hybrid engine yet
            safety_standards=merge_clauses_to_block(legal_section.get('safety_osha', [])),  # Schema uses 'safety_standards'
            site_conditions=merge_clauses_to_block(legal_section.get('site_conditions', [])),
            environmental_hazards=merge_clauses_to_block(legal_section.get('environmental', [])),  # Schema uses 'environmental_hazards'
            conflicting_documents=merge_clauses_to_block(legal_section.get('order_of_precedence', [])),  # Schema uses 'conflicting_documents'
            setoff_withholding=merge_clauses_to_block(legal_section.get('setoff_withholding', []))
        )

        # Build Section V: Regulatory and Compliance Terms
        # Map hybrid engine names to schema field names
        regulatory_section = sections.get('regulatory_and_compliance_terms', {})
        # Combine eeo and mwbe_dbe into eeo_non_discrimination
        eeo_clauses = regulatory_section.get('eeo', []) + regulatory_section.get('mwbe_dbe', [])
        regulatory_terms = RegulatoryAndComplianceTerms(
            certified_payroll=merge_clauses_to_block(regulatory_section.get('certified_payroll', [])),
            prevailing_wage=merge_clauses_to_block(regulatory_section.get('prevailing_wage', [])),
            eeo_non_discrimination=merge_clauses_to_block(eeo_clauses),  # Schema combines EEO + MWBE/DBE
            anti_lobbying=None,  # Not in hybrid engine yet
            apprenticeship_training=merge_clauses_to_block(regulatory_section.get('apprenticeship', [])),  # Schema uses 'apprenticeship_training'
            immigration_everify=merge_clauses_to_block(regulatory_section.get('e_verify', [])),  # Schema uses 'immigration_everify'
            worker_classification=merge_clauses_to_block(regulatory_section.get('worker_classification', [])),
            drug_free_workplace=merge_clauses_to_block(regulatory_section.get('drug_free_workplace', []))
        )

        # Build Section VI: Data, Technology and Deliverables
        # Map hybrid engine names to schema field names
        data_section = sections.get('data_technology_and_deliverables', {})
        data_technology = DataTechnologyAndDeliverables(
            data_ownership=merge_clauses_to_block(data_section.get('data_ownership', [])),
            ai_technology_use=merge_clauses_to_block(data_section.get('ai_technology_use', [])),
            digital_surveillance=None,  # Not in hybrid engine yet
            gis_digital_workflow=None,  # Not in hybrid engine yet
            confidentiality=merge_clauses_to_block(data_section.get('confidentiality', [])),
            cybersecurity=merge_clauses_to_block(data_section.get('cybersecurity', []))
            # Note: digital_deliverables and document_retention don't exist in schema
        )

        # Section VII: Supplemental Operational Risks (empty for now - hybrid engine doesn't extract this)
        supplemental_risks = []

        # Build comprehensive result
        result = ComprehensiveAnalysisResult(
            schema_version="1.0",
            contract_overview=contract_overview,
            administrative_and_commercial_terms=administrative_terms,
            technical_and_performance_terms=technical_terms,
            legal_risk_and_enforcement=legal_risk,
            regulatory_and_compliance_terms=regulatory_terms,
            data_technology_and_deliverables=data_technology,
            supplemental_operational_risks=supplemental_risks,
            metadata=metadata
        )

        logger.info(f"ComprehensiveAnalysisResult built successfully")
        return result

    def validate_model(self) -> bool:
        """
        Validate that the AI model is loaded and ready.

        Returns:
            True if model is ready, False otherwise
        """
        logger.debug("Validating AI model")
        try:
            is_ready = self.ai_client is not None
            logger.info("Model validation result: %s", is_ready)
            return is_ready
        except Exception as e:
            logger.error("Model validation failed: %s", e)
            return False
