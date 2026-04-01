"""
Anthropic Claude API Client for CR2A contract analysis.

Drop-in replacement for LocalModelClient — implements the same public interface
so that AnalysisEngine, QueryEngine, BidReviewEngine, and ChatOrchestrationThread
work without modification.
"""

import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AnthropicClient:
    """Client for contract analysis using the Anthropic Claude API."""

    MODELS = {
        "claude-sonnet": "claude-sonnet-4-20250514",
        "claude-opus": "claude-opus-4-20250514",
    }

    # Token limits (conservative defaults)
    MAX_TOKENS_ANALYSIS = 4096
    MAX_TOKENS_QUERY = 2048

    def __init__(
        self,
        api_key: str,
        model_name: str = "claude-sonnet",
    ):
        """
        Args:
            api_key: Anthropic API key.
            model_name: Model tier — 'claude-sonnet' or 'claude-opus'.
        """
        import anthropic

        self._model_name = model_name
        self._model_id = self.MODELS.get(model_name, self.MODELS["claude-sonnet"])
        self._client = anthropic.Anthropic(api_key=api_key)
        self._api_key = api_key
        self._loaded = False

        logger.info("AnthropicClient initialized with model: %s (%s)", model_name, self._model_id)

    # =========================================================================
    # Properties (matches LocalModelClient interface)
    # =========================================================================

    @property
    def model(self) -> str:
        """Return model identifier string for display/logging."""
        return self._model_id

    @property
    def model_name(self) -> str:
        """Return friendly model name."""
        return self._model_name

    # =========================================================================
    # Public Interface (matches LocalModelClient)
    # =========================================================================

    def ensure_loaded(self, progress_callback=None) -> None:
        """Validate API key. No model to load for API backend.

        Args:
            progress_callback: Optional callback(status_str, percent_int).
        """
        if self._loaded:
            return

        if progress_callback:
            progress_callback("Validating Claude API key...", 50)

        ok, error = self.validate_api_key()
        if not ok:
            raise RuntimeError(
                f"Anthropic API key validation failed.\n{error}\n"
                "Check your key in Settings or set the ANTHROPIC_API_KEY environment variable."
            )

        self._loaded = True

        if progress_callback:
            progress_callback("Claude API ready", 100)

        logger.info("Claude API key validated successfully")

    def validate_api_key(self):
        """Test API key with a minimal call.

        Returns:
            Tuple of (success: bool, error_message: str or None).
        """
        try:
            self._client.messages.create(
                model=self._model_id,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True, None
        except Exception as e:
            logger.warning("API key validation failed: %s", e)
            return False, str(e)

    def generate(
        self,
        system_message: str,
        user_message: str,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate a response from Claude.

        This is the core method called by AnalysisEngine for every AI task:
        batch analysis, single category, supplemental risks, overview, etc.

        Args:
            system_message: System prompt.
            user_message: User prompt.
            progress_callback: Optional callback(status_str, percent_int).
            max_tokens: Maximum output tokens (default: MAX_TOKENS_ANALYSIS).

        Returns:
            Raw text response from Claude.
        """
        if max_tokens is None:
            max_tokens = self.MAX_TOKENS_ANALYSIS

        if progress_callback:
            progress_callback("Calling Claude API...", 30)

        try:
            response = self._client.messages.create(
                model=self._model_id,
                max_tokens=max_tokens,
                system=system_message,
                messages=[{"role": "user", "content": user_message}],
            )

            text = response.content[0].text

            if progress_callback:
                progress_callback("Response received", 90)

            logger.debug(
                "Claude response: %d chars, %d input tokens, %d output tokens",
                len(text),
                response.usage.input_tokens,
                response.usage.output_tokens,
            )

            return text

        except Exception as e:
            logger.error("Claude API call failed: %s", e)
            raise RuntimeError(f"Claude API call failed: {e}") from e

    def analyze_contract(
        self,
        contract_text: str,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> Dict:
        """Analyze a full contract and return structured JSON.

        This method is called by the analysis engine's legacy path.
        The batched pipeline (used by default) calls generate() directly,
        so this method is mainly a fallback.

        Args:
            contract_text: Full contract text.
            progress_callback: Optional callback.

        Returns:
            Analysis result dictionary matching the CR2A schema.
        """
        system_msg = (
            "You are a contract analysis AI. Analyze the following contract "
            "and return a JSON object with the analysis results. "
            "Include clause locations, summaries, redline recommendations, "
            "and harmful language flags for each identified clause category."
        )

        response = self.generate(
            system_message=system_msg,
            user_message=contract_text,
            progress_callback=progress_callback,
            max_tokens=8192,
        )

        # Parse JSON from response
        return self._parse_json_response(response)

    def process_query(
        self,
        query: str,
        context: Dict,
        conversation_history: Optional[List] = None,
    ) -> str:
        """Answer a question about a contract.

        Args:
            query: The user's question.
            context: Dictionary with contract_text and optional analysis results.
            conversation_history: Prior conversation messages.

        Returns:
            Natural language response string.
        """
        system_msg = (
            "You are a contract analysis assistant for Atlantic Pipe Services (APS), "
            "a sewer and water infrastructure rehabilitation contractor. "
            "Answer questions about the loaded contract clearly and concisely. "
            "Cite specific sections and page numbers when possible."
        )

        # Build context from contract text and any prior analysis
        context_parts = []
        if context.get("contract_text"):
            # Truncate if very long to stay within reasonable token limits
            text = context["contract_text"]
            if len(text) > 100000:
                text = text[:100000] + "\n\n[... contract text truncated for length ...]"
            context_parts.append(f"CONTRACT TEXT:\n{text}")

        if context.get("analysis"):
            analysis_json = json.dumps(context["analysis"], indent=1)
            if len(analysis_json) < 20000:
                context_parts.append(f"\nPRIOR ANALYSIS:\n{analysis_json}")

        # Include conversation history
        if conversation_history:
            history = "\n".join(
                f"{m['role'].upper()}: {m['content']}"
                for m in conversation_history[-6:]
            )
            context_parts.append(f"\nCONVERSATION:\n{history}")

        context_parts.append(f"\nQUESTION: {query}")
        user_message = "\n\n".join(context_parts)

        return self.generate(
            system_message=system_msg,
            user_message=user_message,
            max_tokens=self.MAX_TOKENS_QUERY,
        )

    def process_with_tools(
        self,
        user_message: str,
        tool_registry,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        token_callback: Optional[Callable[[str], None]] = None,
        max_iterations: int = 5,
    ) -> List[Dict[str, str]]:
        """Process a user message with Claude's native tool_use.

        Replaces the ReAct text-parsing approach used by LocalModelClient
        with Claude's structured tool calling API.

        Args:
            user_message: The user's chat message.
            tool_registry: ToolRegistry instance with available tools.
            conversation_history: Prior messages for context.
            progress_callback: Optional progress callback.
            token_callback: Optional token streaming callback (not used for API).
            max_iterations: Max tool call rounds (default 5).

        Returns:
            List of message dicts: [{"role": ..., "content": ...}, ...]
        """
        # Build tool definitions for Claude's tool_use API
        tools = self._build_tool_definitions(tool_registry)

        # Build system prompt
        system_prompt = tool_registry.get_system_prompt()
        skill_prompt = tool_registry.get_skill_prompt("all")
        full_system = f"{system_prompt}\n\n{skill_prompt}"

        # Build messages for Claude API
        api_messages = []
        if conversation_history:
            for msg in conversation_history[-6:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant"):
                    api_messages.append({"role": role, "content": content})

        api_messages.append({"role": "user", "content": user_message})

        result_messages = []
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            if progress_callback:
                progress_callback(f"Thinking... (step {iteration})", int(20 + iteration * 15))

            try:
                response = self._client.messages.create(
                    model=self._model_id,
                    max_tokens=4096,
                    system=full_system,
                    messages=api_messages,
                    tools=tools,
                )
            except Exception as e:
                result_messages.append({
                    "role": "error",
                    "content": f"Claude API call failed: {e}",
                })
                break

            # Process response content blocks
            assistant_content = []
            has_tool_use = False

            for block in response.content:
                if block.type == "text":
                    text = block.text.strip()
                    if text:
                        assistant_content.append(block)
                        # Stream text to token_callback if available
                        if token_callback:
                            token_callback(text)
                        result_messages.append({"role": "assistant", "content": text})

                elif block.type == "tool_use":
                    has_tool_use = True
                    assistant_content.append(block)
                    tool_name = block.name
                    tool_args = block.input

                    result_messages.append({
                        "role": "tool_call",
                        "content": f"{tool_name}({', '.join(f'{k}=\"{v}\"' for k, v in tool_args.items())})",
                    })

                    if progress_callback:
                        progress_callback(f"Running {tool_name}...", int(30 + iteration * 15))

                    # Execute the tool
                    observation = tool_registry.execute(tool_name, tool_args)
                    result_messages.append({"role": "observation", "content": observation})

            # If no tool use, we're done
            if not has_tool_use:
                break

            # Feed tool results back to Claude for next iteration
            api_messages.append({"role": "assistant", "content": assistant_content})

            # Build tool_result messages for all tool_use blocks
            tool_results = []
            for block in assistant_content:
                if hasattr(block, 'type') and block.type == "tool_use":
                    # Find the corresponding observation
                    obs = tool_registry.execute(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": obs,
                    })

            if tool_results:
                api_messages.append({"role": "user", "content": tool_results})

            # Check stop reason
            if response.stop_reason == "end_turn":
                break

        else:
            result_messages.append({
                "role": "assistant",
                "content": "I've reached the maximum number of analysis steps. "
                           "Here's what I found so far based on the tool results above.",
            })

        if progress_callback:
            progress_callback("Complete", 100)

        return result_messages

    # =========================================================================
    # Cost Estimation
    # =========================================================================

    def estimate_cost(self, input_chars: int, max_output_tokens: int = 4096) -> Dict[str, float]:
        """Estimate API cost for an analysis call.

        Args:
            input_chars: Number of input characters.
            max_output_tokens: Expected output tokens.

        Returns:
            Dict with 'input_cost', 'output_cost', 'total_cost' in USD.
        """
        # Approximate: ~4 chars per token for English text
        input_tokens = input_chars / 4

        # Pricing per 1M tokens (as of 2025)
        if "sonnet" in self._model_id:
            input_price = 3.00    # $3/MTok input
            output_price = 15.00  # $15/MTok output
        else:  # opus
            input_price = 15.00   # $15/MTok input
            output_price = 75.00  # $75/MTok output

        input_cost = (input_tokens / 1_000_000) * input_price
        output_cost = (max_output_tokens / 1_000_000) * output_price
        total = input_cost + output_cost

        return {
            "input_tokens_est": int(input_tokens),
            "output_tokens_est": max_output_tokens,
            "input_cost": round(input_cost, 4),
            "output_cost": round(output_cost, 4),
            "total_cost": round(total, 4),
        }

    # =========================================================================
    # Internal helpers
    # =========================================================================

    def _build_tool_definitions(self, tool_registry) -> List[Dict[str, Any]]:
        """Convert ToolRegistry tools to Claude API tool definitions."""
        tools = []
        for name in tool_registry.get_tool_names():
            tool = tool_registry.get_tool(name)
            if tool is None:
                continue

            # Build input schema from tool parameters
            properties = {}
            required = []
            for param_name, param_desc in tool.parameters.items():
                properties[param_name] = {
                    "type": "string",
                    "description": param_desc,
                }
                required.append(param_name)

            tool_def = {
                "name": tool.name,
                "description": tool.description,
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            }
            tools.append(tool_def)

        return tools

    def _parse_json_response(self, text: str) -> Dict:
        """Parse JSON from Claude's response text.

        Claude generally produces valid JSON, but we still handle
        markdown code blocks and minor formatting.

        Args:
            text: Raw response text.

        Returns:
            Parsed dictionary.
        """
        # Strip markdown code blocks
        cleaned = text.strip()
        if cleaned.startswith("```"):
            # Remove opening ```json or ```
            cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned)
            cleaned = re.sub(r'\n?```\s*$', '', cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning("JSON parse failed: %s. Attempting recovery.", e)
            # Try to find JSON object in the text
            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            logger.error("Could not parse JSON from Claude response")
            return {}
