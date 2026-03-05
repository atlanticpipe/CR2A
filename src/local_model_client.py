"""
Local Model Client for Contract Analysis

This module provides the LocalModelClient class for analyzing contracts using
an embedded LLM (Llama 3.1 or compatible) via llama-cpp-python. It maintains
interface compatibility with OpenAIClient while running entirely locally.

Supports:
- Llama 3.2 3B Instruct (recommended for CPU, fast)
- Llama 3.1 8B Instruct (higher quality, slower on CPU)
- Legacy Pythia models (backwards compatibility)
- Any GGUF-format model via llama-cpp-python
"""

import json
import logging
import re
import multiprocessing
from pathlib import Path
from typing import Dict, Optional, Callable, List

logger = logging.getLogger(__name__)

# Try to import llama-cpp-python (optional dependency)
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    logger.warning("llama-cpp-python not available. Install with: pip install llama-cpp-python")

from src.schema_loader import SchemaLoader
from src.fuzzy_matcher import FuzzyClauseMatcher


class LocalModelClient:
    """
    Client for contract analysis using a local LLM.

    Provides a local alternative to OpenAIClient, running models entirely
    on CPU without external API calls. Maintains the same interface for
    seamless integration with AnalysisEngine.

    Supports Llama 3.1 Instruct (recommended) and legacy Pythia models.
    Auto-detects the correct chat template based on model name.
    """

    # Default settings - tuned for fast CPU inference
    DEFAULT_CONTEXT_SIZE = 8192   # 8K tokens (fast on CPU; overridden per model)
    DEFAULT_TEMPERATURE = 0.0     # Deterministic for contract analysis
    MAX_TOKENS_ANALYSIS = 4000    # Contract analysis responses (keep short for speed)
    MAX_TOKENS_QUERY = 500        # Chat query responses

    # Model-specific context sizes
    MODEL_CONTEXT_SIZES = {
        "llama-3.2-3b": 8192,    # 8K context, fast on CPU
        "llama-3.1-8b": 16384,   # 16K context, slower but more capable
        "pythia": 4096,           # Legacy model
    }

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_name: str = "llama-3.2-3b-q4",
        n_ctx: int = DEFAULT_CONTEXT_SIZE,
        n_threads: Optional[int] = None,
        n_gpu_layers: int = 0,
        temperature: float = DEFAULT_TEMPERATURE
    ):
        """
        Initialize local model client.

        Args:
            model_path: Path to GGUF model file (if None, must be set before use)
            model_name: Name identifier for the model
            n_ctx: Context window size (tokens)
            n_threads: CPU threads to use (auto-detects if None)
            n_gpu_layers: GPU layers to offload (0 = CPU-only)
            temperature: Sampling temperature (0.0 = deterministic)

        Raises:
            ImportError: If llama-cpp-python is not installed
        """
        if not LLAMA_CPP_AVAILABLE:
            raise ImportError(
                "llama-cpp-python is required for local models.\n"
                "Install with: pip install llama-cpp-python"
            )

        self.model_path = Path(model_path) if model_path else None
        self.model_name = model_name
        self.n_threads = n_threads or multiprocessing.cpu_count()
        self.n_gpu_layers = n_gpu_layers
        self.temperature = temperature

        # Auto-configure context size based on model if not explicitly set
        if n_ctx == self.DEFAULT_CONTEXT_SIZE:
            self.n_ctx = self._get_model_context_size()
            self.DEFAULT_CONTEXT_SIZE = self.n_ctx
        else:
            self.n_ctx = n_ctx
            self.DEFAULT_CONTEXT_SIZE = n_ctx

        # Lazy loading - model loads on first use
        self._model: Optional[Llama] = None
        self._model_loaded = False

        # Load schema for prompt construction
        self._schema_loader = SchemaLoader()
        self._schema_loader.load_schema()

        # Initialize fuzzy matcher for intelligent category detection
        self._fuzzy_matcher = FuzzyClauseMatcher(confidence_threshold=65.0)

        logger.info(
            f"LocalModelClient initialized: model={model_name}, "
            f"ctx={n_ctx}, threads={self.n_threads}"
        )

    # =========================================================================
    # Properties (interface compatibility with OpenAIClient)
    # =========================================================================

    @property
    def model(self) -> str:
        """Model name for interface compatibility with OpenAIClient."""
        return self.model_name

    # =========================================================================
    # Public Interface (matches OpenAIClient)
    # =========================================================================

    def generate(
        self,
        system_message: str,
        user_message: str,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate a text response from the local model.

        Unified interface matching OpenAIClient.generate(). Callers send
        system + user messages and receive raw text back. JSON parsing
        is the caller's responsibility.

        Args:
            system_message: System/instruction message for the model
            user_message: User input/prompt
            progress_callback: Optional callback for progress updates
            max_tokens: Optional max output tokens (default: MAX_TOKENS_ANALYSIS)

        Returns:
            Raw text response from the model

        Raises:
            RuntimeError: If model is not loaded or inference fails
        """
        if not self._model_loaded:
            if progress_callback:
                progress_callback("Loading AI model...", 5)
            self._load_model(progress_callback)

        return self._run_inference(
            system_message=system_message,
            user_message=user_message,
            max_tokens=max_tokens or self.MAX_TOKENS_ANALYSIS,
            progress_callback=progress_callback,
            progress_start=55,
            progress_end=85
        )

    def analyze_contract(
        self,
        contract_text: str,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Dict:
        """
        Analyze contract and return structured result.

        Args:
            contract_text: Extracted contract text to analyze
            progress_callback: Optional callback function(status_message, percent)

        Returns:
            Analysis result dictionary matching the CR2A schema

        Raises:
            ValueError: If contract_text is empty
            RuntimeError: If model fails to load or inference fails
        """
        if not contract_text or not contract_text.strip():
            raise ValueError("Contract text cannot be empty")

        # Load model on first use
        if not self._model_loaded:
            if progress_callback:
                progress_callback("Loading AI model into memory...", 5)
            self._load_model(progress_callback)

        if progress_callback:
            progress_callback("Preparing analysis prompt...", 10)

        # Build analysis prompt
        system_message = self._build_system_message()
        user_message = self._build_user_message(contract_text)

        if progress_callback:
            progress_callback("Running local AI inference...", 20)

        # Run inference with progress tracking
        response_text = self._run_inference(
            system_message=system_message,
            user_message=user_message,
            max_tokens=self.MAX_TOKENS_ANALYSIS,
            progress_callback=progress_callback,
            progress_start=20,
            progress_end=90
        )

        if progress_callback:
            progress_callback("Parsing response...", 95)

        # Parse JSON response
        try:
            result = self._parse_json_response(response_text)

            if progress_callback:
                progress_callback("Analysis complete", 100)

            return result
        except Exception as e:
            logger.error(f"Failed to parse model response: {e}")
            raise RuntimeError(f"Failed to parse model output: {e}")

    def process_query(
        self,
        query: str,
        context: Dict,
        conversation_history: Optional[List] = None
    ) -> str:
        """
        Process a user query about a contract.

        Args:
            query: User's natural language question about the contract
            context: Relevant contract data (clauses, risks, metadata, etc.)
            conversation_history: Optional list of previous messages

        Returns:
            Natural language response string

        Raises:
            ValueError: If query is empty or context is invalid
            RuntimeError: If model fails to load or inference fails
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if not context or not isinstance(context, dict):
            raise ValueError("Context must be a non-empty dictionary")

        # Load model on first use
        if not self._model_loaded:
            self._load_model()

        # Build query prompt
        system_message = self._build_query_system_message()
        user_message = self._build_query_user_message(query, context)

        # Run inference
        response_text = self._run_inference(
            system_message=system_message,
            user_message=user_message,
            max_tokens=self.MAX_TOKENS_QUERY,
            temperature=0.7  # More conversational
        )

        return response_text.strip()

    def validate_api_key(self) -> bool:
        """
        Validate model availability (no API key needed for local models).

        Returns:
            True if model file exists and can be loaded, False otherwise
        """
        if not self.model_path or not self.model_path.exists():
            logger.warning(f"Model file not found: {self.model_path}")
            return False

        try:
            if not self._model_loaded:
                self._load_model()
            return True
        except Exception as e:
            logger.error(f"Model validation failed: {e}")
            return False

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _is_llama_model(self) -> bool:
        """Check if the current model is a Llama model (vs legacy Pythia)."""
        name = self.model_name.lower()
        return 'llama' in name or 'meta' in name

    def _get_model_context_size(self) -> int:
        """Auto-detect appropriate context size based on model name."""
        name = self.model_name.lower()
        for key, ctx_size in self.MODEL_CONTEXT_SIZES.items():
            if key in name:
                logger.info(f"Auto-configured context size: {ctx_size} for model {self.model_name}")
                return ctx_size
        return 8192  # Safe default for unknown models

    def _load_model(
        self,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> None:
        """
        Load model from GGUF file (lazy loading pattern).

        Args:
            progress_callback: Optional callback for loading progress

        Raises:
            RuntimeError: If model file doesn't exist or loading fails
        """
        if self._model_loaded:
            return

        if not self.model_path or not self.model_path.exists():
            raise RuntimeError(
                f"Model file not found: {self.model_path}\n\n"
                "Please download the model first:\n"
                "Settings -> Manage Models -> Download Model"
            )

        logger.info(f"Loading model from: {self.model_path}")

        try:
            self._model = Llama(
                model_path=str(self.model_path),
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_gpu_layers=self.n_gpu_layers,
                verbose=False
            )

            self._model_loaded = True
            logger.info("Model loaded successfully")

            if progress_callback:
                progress_callback("Model loaded successfully", 10)

        except Exception as e:
            logger.error(f"Failed to load model: {e}", exc_info=True)
            raise RuntimeError(
                f"Failed to load model: {e}\n\n"
                "Possible causes:\n"
                "- Corrupted model file (try re-downloading)\n"
                "- Insufficient memory (need 8GB+ free RAM for Llama 3.1 8B)\n"
                "- Incompatible model format (need GGUF)\n\n"
                "Try: Settings -> Manage Models -> Delete and re-download"
            )

    def _format_prompt(
        self,
        system_message: str,
        user_message: str
    ) -> str:
        """
        Format prompt using the appropriate chat template.

        Auto-detects Llama 3.1 vs Pythia based on model name.

        Args:
            system_message: System instructions
            user_message: User input

        Returns:
            Formatted prompt string
        """
        if self._is_llama_model():
            # Llama 3.1 Instruct chat template
            return (
                f"<|begin_of_text|>"
                f"<|start_header_id|>system<|end_header_id|>\n\n"
                f"{system_message}<|eot_id|>"
                f"<|start_header_id|>user<|end_header_id|>\n\n"
                f"{user_message}<|eot_id|>"
                f"<|start_header_id|>assistant<|end_header_id|>\n\n"
            )
        else:
            # Legacy Pythia template
            return (
                f"### System:\n{system_message}\n\n"
                f"### Human:\n{user_message}\n\n"
                f"### Assistant:\n"
            )

    def _get_stop_sequences(self) -> list:
        """Get appropriate stop sequences for the current model."""
        if self._is_llama_model():
            return ["<|eot_id|>", "<|end_of_text|>"]
        else:
            return ["### Human:", "### System:"]

    def _run_inference(
        self,
        system_message: str,
        user_message: str,
        max_tokens: int,
        temperature: Optional[float] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        progress_start: int = 0,
        progress_end: int = 100
    ) -> str:
        """
        Run model inference with progress tracking.

        Args:
            system_message: System instructions
            user_message: User input
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (uses default if None)
            progress_callback: Optional progress callback
            progress_start: Starting progress percentage
            progress_end: Ending progress percentage

        Returns:
            Generated text response

        Raises:
            RuntimeError: If inference fails
        """
        if not self._model_loaded:
            raise RuntimeError("Model not loaded")

        temp = temperature if temperature is not None else self.temperature

        # Format prompt with appropriate template
        prompt = self._format_prompt(system_message, user_message)
        stop_sequences = self._get_stop_sequences()

        prompt_chars = len(prompt)
        logger.info(f"Running inference: max_tokens={max_tokens}, temp={temp}, prompt_chars={prompt_chars}")

        # Warn if prompt is too large for context
        estimated_prompt_tokens = prompt_chars // 3  # Conservative estimate
        if estimated_prompt_tokens > self.n_ctx - max_tokens:
            logger.warning(
                f"Prompt may exceed context window: ~{estimated_prompt_tokens} tokens "
                f"+ {max_tokens} output > {self.n_ctx} context"
            )

        try:
            import time
            output_tokens = []
            tokens_generated = 0
            start_time = time.time()

            if progress_callback:
                progress_callback("Processing prompt (this may take a moment)...", progress_start)

            for token_output in self._model(
                prompt,
                max_tokens=max_tokens,
                temperature=temp,
                stop=stop_sequences,
                stream=True
            ):
                if isinstance(token_output, dict):
                    choice = token_output.get('choices', [{}])[0]
                    text = choice.get('text', '')
                    output_tokens.append(text)
                    tokens_generated += 1

                    # Update progress every 10 tokens (frequent updates for responsiveness)
                    if progress_callback and tokens_generated % 10 == 0:
                        elapsed = time.time() - start_time
                        tokens_per_sec = tokens_generated / max(elapsed, 0.1)
                        progress_pct = progress_start + int(
                            (tokens_generated / max_tokens) * (progress_end - progress_start)
                        )
                        progress_pct = min(progress_pct, progress_end)
                        progress_callback(
                            f"Generating ({tokens_generated} tokens, {tokens_per_sec:.1f} tok/s)...",
                            progress_pct
                        )

            response_text = ''.join(output_tokens)
            elapsed = time.time() - start_time

            logger.info(
                f"Inference complete: {tokens_generated} tokens in {elapsed:.1f}s "
                f"({tokens_generated / max(elapsed, 0.1):.1f} tok/s)"
            )

            return response_text

        except Exception as e:
            logger.error(f"Inference failed: {e}", exc_info=True)
            raise RuntimeError(f"Local model inference failed: {e}")

    def _parse_json_response(self, response_text: str) -> Dict:
        """
        Parse and repair JSON response from model output.

        Handles markdown code blocks, truncated responses, malformed JSON.

        Args:
            response_text: Raw model output

        Returns:
            Parsed JSON dictionary

        Raises:
            json.JSONDecodeError: If JSON cannot be parsed or repaired
        """
        text = response_text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'\s*```$', '', text)

        first_brace = text.find('{')
        last_brace = text.rfind('}')

        if first_brace == -1 or last_brace == -1:
            raise json.JSONDecodeError(
                "No JSON object found in response",
                text,
                0
            )

        text = text[first_brace:last_brace + 1]

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"Initial JSON parse failed: {e}")

            # Attempt repair: close unclosed braces
            repaired = text
            open_braces = repaired.count('{')
            close_braces = repaired.count('}')

            if open_braces > close_braces:
                repaired += '}' * (open_braces - close_braces)

            # Fix trailing commas
            repaired = re.sub(r',\s*([}\]])', r'\1', repaired)

            try:
                return json.loads(repaired)
            except json.JSONDecodeError as e2:
                logger.error(f"JSON repair failed: {e2}")
                logger.debug(f"Original text: {text[:500]}...")
                raise json.JSONDecodeError(
                    "Failed to parse model output as JSON",
                    text,
                    e.pos
                )

    def _build_system_message(self) -> str:
        """Build system message for contract analysis."""
        return """You are a Contract Analysis Engine specializing in comprehensive contract risk assessment.

Your task is to analyze contracts and return a structured JSON response with ALL relevant clauses found in the contract.

CRITICAL INSTRUCTIONS:

1. EXTRACT BASED ON SUBSTANCE, NOT TERMINOLOGY: Include a clause category if the contract contains provisions that address that topic, even if the exact category name is not used.

2. PRIORITIZE COMPLETENESS OVER DETAIL: It is CRITICAL to include ALL relevant clause categories found, even with brief summaries. Most contracts will have content for 30-50+ categories. Use concise summaries (1-2 sentences).

3. OUTPUT ONLY VALID JSON: No markdown, no explanations, no code blocks. Start directly with { and end with }.

4. ACCURACY: Only extract information that is explicitly stated or clearly implied in the contract.

5. BE CONCISE BUT COMPLETE: Keep individual summaries brief (1-2 sentences) to allow coverage of ALL found categories.

Output Format:
Return a JSON object with these exact keys:
- schema_version (e.g., "v1.0.0")
- contract_overview
- administrative_and_commercial_terms
- technical_and_performance_terms
- legal_risk_and_enforcement
- regulatory_and_compliance_terms
- data_technology_and_deliverables
- supplemental_operational_risks

Each clause must follow the ClauseBlock structure with all required fields."""

    def _build_user_message(self, contract_text: str) -> str:
        """Build user message for contract analysis with fuzzy category suggestions."""
        schema_description = self._schema_loader.get_schema_for_prompt()

        # Use fuzzy matching to suggest likely categories
        try:
            fuzzy_matches = self._fuzzy_matcher.find_matching_categories(
                contract_text,
                min_matches=25
            )

            suggested_categories = {}
            for match in fuzzy_matches:
                section = match.section
                if section not in suggested_categories:
                    suggested_categories[section] = []
                suggested_categories[section].append(match.category)

            fuzzy_suggestions = "\n\nFUZZY LOGIC ANALYSIS:\n\n"
            fuzzy_suggestions += "Based on semantic analysis, these categories are likely present:\n\n"

            for section, categories in suggested_categories.items():
                section_name = section.replace('_', ' ').title()
                fuzzy_suggestions += f"\n{section_name}:\n"
                for cat in categories:
                    fuzzy_suggestions += f"- {cat}\n"

            fuzzy_suggestions += "\nPriority: Focus on these categories first, then check all others systematically.\n"

        except Exception as e:
            logger.warning(f"Fuzzy matching failed: {e}")
            fuzzy_suggestions = ""

        return f"""{schema_description}
{fuzzy_suggestions}

CONTRACT TEXT:
{contract_text}

IMPORTANT:
1. Return ONLY the JSON response
2. Include ONLY clauses found in the contract
3. Omit categories not present in the contract
4. Use exact clause language from the contract
5. Provide accurate risk assessments
6. Use the fuzzy logic suggestions above as a starting point, but check ALL categories systematically

Begin JSON response:"""

    def _build_query_system_message(self) -> str:
        """Build system message for contract Q&A."""
        return """You are a Contract Analysis Assistant helping users understand contracts.

Guidelines:
- Answer questions based on the provided contract context
- Reference specific clauses when relevant
- Be clear and concise
- Use professional but accessible language
- If information isn't in the context, say so
- Don't make up information"""

    def _build_query_user_message(self, query: str, context: Dict) -> str:
        """Build user message for contract Q&A."""
        context_text = "Contract Context:\n"

        if 'contract_metadata' in context:
            metadata = context['contract_metadata']
            context_text += f"- Parties: {metadata.get('parties', 'Unknown')}\n"
            context_text += f"- Date: {metadata.get('effective_date', 'Unknown')}\n"

        # Include retrieved raw contract sections (from tri-layer retrieval)
        if '_retrieved_sections' in context and context['_retrieved_sections']:
            context_text += f"\nRelevant Contract Sections:\n{context['_retrieved_sections']}\n"

        if 'clauses' in context and context['clauses']:
            context_text += "\nAnalyzed Clauses:\n"
            for clause in context['clauses'][:10]:
                context_text += f"- {clause.get('title', 'Untitled')}\n"

        return f"""{context_text}

User Question: {query}

Please answer based on the contract context provided above."""


# Backwards compatibility alias
PythiaModelClient = LocalModelClient
