"""
Tool Registry for CR2A Chat Interface.

Wraps backend engines (AnalysisEngine, BidReviewEngine, QueryEngine) as
callable tools for the ReAct-style chat loop. Loads tool/skill descriptions
from markdown files in the prompts/ directory.

Author: CR2A Development Team
Date: 2026-03-12
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


def _get_prompts_dir() -> Path:
    """Return path to the prompts/ directory."""
    src_dir = Path(__file__).resolve().parent
    candidates = [
        src_dir.parent / "prompts",
        src_dir / "prompts",
    ]
    for p in candidates:
        if p.exists():
            return p
    # Fallback: create it
    default = src_dir.parent / "prompts"
    default.mkdir(exist_ok=True)
    return default


def _load_prompt_file(filename: str) -> str:
    """Load a markdown prompt file, returning empty string if not found."""
    path = _get_prompts_dir() / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    logger.warning("Prompt file not found: %s", path)
    return ""


@dataclass
class Tool:
    """A callable tool that the chat AI can invoke."""
    name: str
    description: str
    parameters: Dict[str, str]  # param_name -> description
    handler: Callable[..., str]  # Returns string result


class ToolRegistry:
    """
    Registry of tools available to the chat AI.

    Each tool wraps a backend engine method and returns a string result
    suitable for insertion into the ReAct conversation loop.
    """

    def __init__(
        self,
        analysis_engine=None,
        bid_review_engine=None,
        query_engine=None,
        prepared_contract=None,
        prepared_bid_review=None,
        excel_builder=None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ):
        self.analysis_engine = analysis_engine
        self.bid_review_engine = bid_review_engine
        self.query_engine = query_engine
        self.prepared_contract = prepared_contract
        self.prepared_bid_review = prepared_bid_review
        self.excel_builder = excel_builder
        self.progress_callback = progress_callback
        self.item_callback: Optional[Callable[[str, str, str, dict], None]] = None

        # Accumulated results for context building
        self.category_results: Dict[str, dict] = {}
        self.bid_item_results: Dict[str, Any] = {}
        self.specs_text: str = ""

        # Build tool list
        self._tools: Dict[str, Tool] = {}
        self._register_tools()

    def _register_tools(self):
        """Register all available tools."""
        self._tools = {
            "analyze_contract_category": Tool(
                name="analyze_contract_category",
                description="Analyze a single contract clause category using AI.",
                parameters={"category": "Category key (e.g., 'change_orders')"},
                handler=self._handle_analyze_category,
            ),
            "analyze_bid_item": Tool(
                name="analyze_bid_item",
                description="Extract a single bid review checklist value.",
                parameters={"item": "Item key (e.g., 'bid_bond', 'retainage')"},
                handler=self._handle_analyze_bid_item,
            ),
            "query_contract": Tool(
                name="query_contract",
                description="Ask a free-form question about the loaded contract.",
                parameters={"question": "The question to answer"},
                handler=self._handle_query,
            ),
            "run_full_contract_analysis": Tool(
                name="run_full_contract_analysis",
                description="Analyze all contract clause categories sequentially.",
                parameters={},
                handler=self._handle_full_contract_analysis,
            ),
            "run_full_bid_review": Tool(
                name="run_full_bid_review",
                description="Extract all bid checklist items.",
                parameters={},
                handler=self._handle_full_bid_review,
            ),
            "run_specs_extraction": Tool(
                name="run_specs_extraction",
                description="Extract technical specification requirements.",
                parameters={},
                handler=self._handle_specs_extraction,
            ),
            "list_categories": Tool(
                name="list_categories",
                description="List all available contract analysis categories.",
                parameters={},
                handler=self._handle_list_categories,
            ),
            "list_bid_items": Tool(
                name="list_bid_items",
                description="List all available bid review checklist items.",
                parameters={},
                handler=self._handle_list_bid_items,
            ),
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_tool_names(self) -> List[str]:
        """Get list of all tool names."""
        return list(self._tools.keys())

    def execute(self, tool_name: str, args: Dict[str, str]) -> str:
        """
        Execute a tool by name with the given arguments.

        Returns:
            String result for the conversation.
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return f"Error: Unknown tool '{tool_name}'. Available: {', '.join(self._tools.keys())}"

        try:
            return tool.handler(**args)
        except TypeError as e:
            return f"Error calling {tool_name}: {e}"
        except Exception as e:
            logger.error("Tool %s failed: %s", tool_name, e, exc_info=True)
            return f"Error: {tool_name} failed — {e}"

    def get_system_prompt(self) -> str:
        """Assemble the full system prompt from markdown files."""
        parts = [
            _load_prompt_file("system.md"),
            _load_prompt_file("tools.md"),
        ]
        return "\n\n".join(p for p in parts if p)

    def get_skill_prompt(self, skill: str = "all") -> str:
        """Load skill-specific prompt(s)."""
        if skill == "all" or skill == "contract":
            parts = [_load_prompt_file("contract_skills.md")]
        if skill == "all" or skill == "bid_review":
            parts = [_load_prompt_file("bid_review_skills.md")]
        if skill == "all" or skill == "query":
            parts = [_load_prompt_file("query_skills.md")]
        if skill == "all":
            parts = [
                _load_prompt_file("contract_skills.md"),
                _load_prompt_file("bid_review_skills.md"),
                _load_prompt_file("query_skills.md"),
            ]
        return "\n\n".join(p for p in parts if p)

    def update_prepared_contract(self, prepared):
        """Update the prepared contract (after folder load)."""
        self.prepared_contract = prepared

    def update_prepared_bid_review(self, prepared):
        """Update the prepared bid review (after folder load)."""
        self.prepared_bid_review = prepared

    # ------------------------------------------------------------------
    # Tool handlers
    # ------------------------------------------------------------------

    def _handle_analyze_category(self, category: str) -> str:
        """Analyze a single contract clause category."""
        if not self.analysis_engine:
            return "Error: Analysis engine not initialized."
        if not self.prepared_contract:
            return "Error: No contract loaded. Load a folder first."

        result = self.analysis_engine.analyze_single_category(
            self.prepared_contract, category, self.progress_callback
        )
        if result is None:
            return f"Category '{category}' not found in the contract."

        section_key, display_name, clause_block, prompt_sent, ai_response = result

        # Store result
        self.category_results[category] = clause_block

        # Update Excel
        if self.excel_builder:
            contract_file = ""
            if self.prepared_contract and hasattr(self.prepared_contract, "file_path"):
                import os
                contract_file = os.path.basename(self.prepared_contract.file_path)
            self.excel_builder.update_contract_category(category, clause_block, contract_file)

        # Format response
        summary = clause_block.get("Clause Summary", "No summary available.")
        location = clause_block.get("Clause Location", "")
        page = clause_block.get("Clause Page", "")
        redlines = clause_block.get("Redline Recommendations", [])
        harmful = clause_block.get("Harmful Language / Policy Conflicts", [])

        parts = [f"**{display_name}**"]
        if location:
            parts.append(f"Location: {location}" + (f" (Page {page})" if page else ""))
        parts.append(f"Summary: {summary}")

        if redlines:
            parts.append("Recommendations:")
            for r in redlines:
                if isinstance(r, dict):
                    parts.append(f"  - {r.get('Action', '')}: {r.get('Text', '')}")
                elif isinstance(r, str):
                    parts.append(f"  - {r}")

        if harmful:
            parts.append("Harmful Language:")
            for h in (harmful if isinstance(harmful, list) else [harmful]):
                parts.append(f"  - {h}")

        return "\n".join(parts)

    def _handle_analyze_bid_item(self, item: str) -> str:
        """Analyze a single bid review checklist item."""
        if not self.bid_review_engine:
            return "Error: Bid review engine not initialized."
        if not self.prepared_bid_review:
            return "Error: No bid review prepared. Load a folder first."

        try:
            section_key, display_name, checklist_item = (
                self.bid_review_engine.analyze_single_item(
                    self.prepared_bid_review, item, self.progress_callback
                )
            )
        except ValueError as e:
            return f"Error: {e}"

        # Store result
        self.bid_item_results[item] = checklist_item

        # Update Excel
        if self.excel_builder:
            self.excel_builder.update_bid_review_item(item, checklist_item)

        # Format response
        parts = [f"**{display_name}**"]
        parts.append(f"Value: {checklist_item.value or 'Not found'}")
        if checklist_item.location:
            parts.append(f"Location: {checklist_item.location}")
        if checklist_item.page:
            parts.append(f"Page: {checklist_item.page}")
        parts.append(f"Confidence: {checklist_item.confidence}")
        if checklist_item.notes:
            parts.append(f"Notes: {checklist_item.notes}")

        return "\n".join(parts)

    def _handle_query(self, question: str) -> str:
        """Process a free-form question about the contract."""
        if not self.query_engine:
            return "Error: Query engine not initialized."

        # Build analysis context from accumulated results
        analysis_dict = self._build_analysis_context()
        return self.query_engine.process_query(question, analysis_dict)

    def _handle_full_contract_analysis(self) -> str:
        """Run full contract analysis across all categories."""
        if not self.analysis_engine:
            return "Error: Analysis engine not initialized."
        if not self.prepared_contract:
            return "Error: No contract loaded."

        cat_map = self.analysis_engine.CATEGORY_MAP
        total = len(cat_map)
        completed = 0
        errors = []

        for cat_key in cat_map:
            try:
                result = self.analysis_engine.analyze_single_category(
                    self.prepared_contract, cat_key, self.progress_callback
                )
                if result:
                    section_key, display_name, clause_block, _, status = result
                    if clause_block is not None:
                        self.category_results[cat_key] = clause_block
                        if self.excel_builder:
                            import os
                            cf = ""
                            if hasattr(self.prepared_contract, "file_path"):
                                cf = os.path.basename(self.prepared_contract.file_path)
                            self.excel_builder.update_contract_category(cat_key, clause_block, cf)
                        # Emit per-category result to GUI
                        if self.item_callback:
                            data = dict(clause_block) if isinstance(clause_block, dict) else {}
                            self.item_callback('contract', cat_key, display_name, data)
                    elif status == "NOT FOUND":
                        if self.item_callback:
                            self.item_callback('contract_not_found', cat_key, display_name, {})
                completed += 1
            except Exception as e:
                errors.append(f"{cat_key}: {e}")
                completed += 1

        summary = f"Analyzed {completed}/{total} contract categories."
        if errors:
            summary += f"\n{len(errors)} errors: " + "; ".join(errors[:5])

        # Count findings
        found = sum(1 for v in self.category_results.values()
                    if v and isinstance(v, dict) and v.get("Clause Summary"))
        excel_note = " Results saved to Excel workbook." if self.excel_builder else " (Excel workbook not available)"
        summary += f"\n{found} categories had findings.{excel_note}"
        return summary

    def _handle_full_bid_review(self) -> str:
        """Run full bid review across all items."""
        if not self.bid_review_engine:
            return "Error: Bid review engine not initialized."
        if not self.prepared_bid_review:
            return "Error: No bid review prepared."

        results = self.bid_review_engine.analyze_all_items(
            self.prepared_bid_review,
            progress_callback=self.progress_callback,
            item_callback=self._on_bid_item_complete,
        )

        self.bid_item_results.update(results)

        # Update Excel with full result
        if self.excel_builder and results:
            for item_key, item in results.items():
                self.excel_builder.update_bid_review_item(item_key, item)
        elif not self.excel_builder:
            logger.warning("Excel builder not available — bid review results not saved to workbook")

        found = sum(1 for v in results.values()
                    if hasattr(v, "confidence") and v.confidence != "not_found")
        excel_note = " Results saved to Excel workbook." if self.excel_builder else " (Excel workbook not available)"
        return (
            f"Bid review complete: {len(results)} items analyzed, "
            f"{found} values found.{excel_note}"
        )

    def _on_bid_item_complete(self, section_key: str, display_name: str, item):
        """Callback for per-item bid review completion."""
        logger.debug("Bid item complete: %s = %s", display_name,
                      item.value if hasattr(item, "value") else str(item))
        if self.item_callback:
            data = {
                'value': getattr(item, 'value', None) or '',
                'location': getattr(item, 'location', None) or '',
                'page': getattr(item, 'page', None) or '',
                'confidence': getattr(item, 'confidence', 'unknown'),
                'notes': getattr(item, 'notes', None) or '',
            }
            self.item_callback('bid_review', section_key, display_name, data)

    def _handle_specs_extraction(self) -> str:
        """Run specs extraction."""
        if not self.analysis_engine or not self.analysis_engine.ai_client:
            return ("Error: AI client not initialized. "
                    "Check Settings → AI Backend to ensure your backend is configured correctly.")

        # Use the specs analysis prompt directly
        contract_text = ""
        if self.prepared_contract and hasattr(self.prepared_contract, "contract_text"):
            contract_text = self.prepared_contract.contract_text
        if not contract_text:
            return "Error: No contract text available."

        system_msg = (
            "You are a construction specifications analyst. Extract all technical "
            "specifications, requirements, and standards from the contract document. "
            "Organize by category (CIPP, Manhole Rehab, Cleaning, CCTV, etc.). "
            "For each spec, note the required value and source section."
        )
        user_msg = (
            "Extract all technical specifications from this contract:\n\n"
            + contract_text[:6000]
        )

        try:
            raw = self.analysis_engine.ai_client.generate(
                system_msg, user_msg, max_tokens=2000,
                progress_callback=self.progress_callback
            )
            self.specs_text = raw.strip()

            if self.excel_builder:
                self.excel_builder.update_specs(self.specs_text)
            else:
                logger.warning("Excel builder not available — specs not saved to workbook")

            lines = [l for l in self.specs_text.split("\n") if l.strip()]
            excel_note = " Results saved to Excel workbook." if self.excel_builder else " (Excel workbook not available)"
            return (
                f"Specs extraction complete ({len(lines)} lines).{excel_note}"
                f"\n\n{self.specs_text}"
            )
        except Exception as e:
            return f"Specs extraction failed: {e}"

    def _handle_list_categories(self) -> str:
        """List all available contract analysis categories."""
        if self.analysis_engine:
            cat_map = self.analysis_engine.CATEGORY_MAP
        else:
            from analysis_engine import AnalysisEngine
            cat_map = AnalysisEngine.CATEGORY_MAP

        # Group by section
        sections: Dict[str, list] = {}
        for cat_key, (section_key, display_name) in cat_map.items():
            sections.setdefault(section_key, []).append((cat_key, display_name))

        parts = ["Available contract analysis categories:\n"]
        for section_key, items in sections.items():
            section_title = section_key.replace("_", " ").title()
            parts.append(f"\n**{section_title}**")
            for cat_key, display_name in items:
                parts.append(f"  - {cat_key}: {display_name}")

        return "\n".join(parts)

    def _handle_list_bid_items(self) -> str:
        """List all available bid review checklist items."""
        from analyzer.bid_spec_patterns import BID_ITEM_MAP

        sections: Dict[str, list] = {}
        for item_key, (section_key, display_name) in BID_ITEM_MAP.items():
            sections.setdefault(section_key, []).append((item_key, display_name))

        parts = ["Available bid review checklist items:\n"]
        for section_key, items in sections.items():
            section_title = section_key.replace("_", " ").title()
            parts.append(f"\n**{section_title}**")
            for item_key, display_name in items:
                parts.append(f"  - {item_key}: {display_name}")

        return "\n".join(parts)

    def _build_analysis_context(self) -> Dict[str, Any]:
        """Build an analysis result dict from accumulated tool results."""
        result = {"schema_version": "v1.0.0", "sections": {}}
        for cat_key, clause_block in self.category_results.items():
            result["sections"][cat_key] = clause_block
        return result

    # ------------------------------------------------------------------
    # ReAct parsing
    # ------------------------------------------------------------------

    @staticmethod
    def parse_tool_call(text: str) -> Optional[tuple]:
        """
        Parse a TOOL_CALL from AI response text.

        Expected format:
            TOOL_CALL: tool_name(param1="value1", param2="value2")

        Returns:
            (tool_name, {param: value}) or None if no tool call found.
        """
        pattern = r'TOOL_CALL:\s*(\w+)\(([^)]*)\)'
        match = re.search(pattern, text)
        if not match:
            return None

        tool_name = match.group(1)
        args_str = match.group(2).strip()

        args = {}
        if args_str:
            # Parse key="value" pairs
            arg_pattern = r'(\w+)\s*=\s*"([^"]*)"'
            for m in re.finditer(arg_pattern, args_str):
                args[m.group(1)] = m.group(2)

            # Also try key=value without quotes (for simple values)
            if not args:
                arg_pattern = r'(\w+)\s*=\s*([^,\s]+)'
                for m in re.finditer(arg_pattern, args_str):
                    args[m.group(1)] = m.group(2).strip('"\'')

        return (tool_name, args)
