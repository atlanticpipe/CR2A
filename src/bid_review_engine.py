"""
Bid Review Analysis Engine

Orchestrates bid specification checklist extraction using regex patterns
first, then AI enhancement for value extraction. Follows the same hybrid
approach as AnalysisEngine but produces ChecklistItem results instead of
ClauseBlock results.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from analyzer.bid_spec_patterns import (
    BID_ITEM_DESCRIPTIONS,
    BID_ITEM_MAP,
    BID_SPEC_PATTERNS,
    extract_bid_spec_items,
)
from src.bid_review_models import (
    BidChecklistResult,
    CIPPDesignRequirements,
    CIPPItems,
    ChecklistItem,
    Cleaning,
    CCTV,
    ManholeRehab,
    SiteConditions,
    SpincastItems,
    StandardContractItems,
)
from src.analysis_models import ContractMetadata

logger = logging.getLogger(__name__)

# Maximum characters of context to send per item to AI
MAX_CONTEXT_PER_ITEM = 3000
# Number of items to batch per AI call
ITEMS_PER_BATCH = 6


@dataclass
class PreparedBidReview:
    """Result of preparing a contract for bid review (text extraction + regex)."""
    contract_text: str
    file_path: str
    regex_results: Dict[str, List[Dict]] = field(default_factory=dict)
    page_count: int = 0
    file_size_bytes: int = 0


class BidReviewEngine:
    """
    Orchestrates bid specification review extraction.

    Uses regex extraction first, then AI enhancement to extract specific
    values from bid specification documents.
    """

    # AI system message for bid value extraction
    SYSTEM_MSG = (
        "You are a construction bid specification reviewer for a CIPP "
        "(cured-in-place pipe) and manhole rehabilitation contractor. "
        "You extract specific values, requirements, and details from bid "
        "specification documents.\n\n"
        "Rules:\n"
        "1. Only extract what is explicitly stated in the text provided\n"
        "2. If a value is not specified or not found, respond with \"NOT FOUND\"\n"
        "3. Include exact numbers with units (e.g., \"5%\", \"180 calendar days\", \"$500/day\")\n"
        "4. For yes/no items, state \"Yes\" or \"No\" followed by brief details\n"
        "5. For multiple options, list all that apply\n"
        "6. Never make assumptions or infer values not stated\n"
        "7. Be concise and factual. Do not provide legal analysis or risk assessment."
    )

    def __init__(self, ai_client):
        self.ai_client = ai_client

    def prepare_bid_review(
        self,
        contract_text: str,
        file_path: str = "",
        page_count: int = 0,
        file_size_bytes: int = 0,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> PreparedBidReview:
        """
        Prepare contract text for bid review by running regex extraction.

        Args:
            contract_text: Full extracted contract text
            file_path: Path to the source file
            page_count: Number of pages in the document
            file_size_bytes: File size in bytes
            progress_callback: Optional (message, percent) callback

        Returns:
            PreparedBidReview with regex results ready for AI enhancement
        """
        if progress_callback:
            progress_callback("Running bid spec pattern matching...", 10)

        regex_results = extract_bid_spec_items(contract_text)

        if progress_callback:
            progress_callback(
                f"Found regex matches for {len(regex_results)} items", 30
            )

        return PreparedBidReview(
            contract_text=contract_text,
            file_path=file_path,
            regex_results=regex_results,
            page_count=page_count,
            file_size_bytes=file_size_bytes,
        )

    def analyze_single_item(
        self,
        prepared: PreparedBidReview,
        item_key: str,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> Tuple[str, str, ChecklistItem]:
        """
        Analyze a single checklist item using regex context + AI.

        Returns:
            (section_key, display_name, ChecklistItem)
        """
        if item_key not in BID_ITEM_MAP:
            raise ValueError(f"Unknown bid item key: {item_key}")

        section_key, display_name = BID_ITEM_MAP[item_key]
        description = BID_ITEM_DESCRIPTIONS.get(item_key, display_name)

        # Gather context: regex matches + keyword search fallback
        context_parts = []
        regex_matches = prepared.regex_results.get(item_key, [])

        if regex_matches:
            for match in regex_matches[:3]:  # Top 3 matches
                context_parts.append(match["context"])
        else:
            # Fallback: keyword search in full text
            context_parts = self._keyword_search(
                prepared.contract_text, item_key, display_name
            )

        if not context_parts:
            # No context found at all
            return section_key, display_name, ChecklistItem(
                value="NOT FOUND",
                confidence="not_found",
                notes="No relevant text found in document",
            )

        # If regex captured a clean value, use it directly (deterministic, no AI needed)
        if regex_matches and regex_matches[0].get("captured_value"):
            captured = regex_matches[0]["captured_value"].strip()
            if captured and len(captured) > 1:
                logger.info("Using regex-captured value for %s: %s", item_key, captured[:80])
                return section_key, display_name, ChecklistItem(
                    value=captured,
                    location="",
                    confidence="high",
                    notes=f"Pattern match ({len(regex_matches)} match{'es' if len(regex_matches) > 1 else ''})",
                )

        # No clean captured value — use AI to extract from context
        context_text = self._merge_contexts(context_parts, MAX_CONTEXT_PER_ITEM)

        user_msg = self._build_single_item_prompt(
            display_name, description, context_text, None
        )

        if progress_callback:
            progress_callback(f"AI extracting: {display_name}...", 50)

        try:
            response = self.ai_client.generate(
                self.SYSTEM_MSG, user_msg, max_tokens=500
            )
            item = self._parse_single_response(response, regex_matches)
        except Exception as e:
            logger.error("AI error for %s: %s", item_key, e)
            item = ChecklistItem(
                value="ERROR",
                confidence="not_found",
                notes=str(e),
            )

        return section_key, display_name, item

    def analyze_all_items(
        self,
        prepared: PreparedBidReview,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        item_callback: Optional[Callable[[str, str, ChecklistItem], None]] = None,
        cancelled_check: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, ChecklistItem]:
        """
        Analyze all checklist items.

        Args:
            prepared: PreparedBidReview from prepare_bid_review()
            progress_callback: (message, percent) callback
            item_callback: (item_key, display_name, ChecklistItem) per-item callback
            cancelled_check: callable returning True if cancelled

        Returns:
            Dict of item_key -> ChecklistItem
        """
        all_keys = list(BID_ITEM_MAP.keys())
        total = len(all_keys)
        results = {}

        for i, item_key in enumerate(all_keys):
            if cancelled_check and cancelled_check():
                logger.info("Bid review cancelled at item %d/%d", i, total)
                break

            section_key, display_name = BID_ITEM_MAP[item_key]
            pct = int((i / total) * 100)

            if progress_callback:
                progress_callback(f"[{i+1}/{total}] {display_name}...", pct)

            try:
                _, _, item = self.analyze_single_item(prepared, item_key)
                results[item_key] = item

                if item_callback:
                    item_callback(item_key, display_name, item)

            except Exception as e:
                logger.error("Error analyzing %s: %s", item_key, e)
                results[item_key] = ChecklistItem(
                    value="ERROR", confidence="not_found", notes=str(e)
                )

        if progress_callback:
            progress_callback("Bid review complete!", 100)

        return results

    def build_result(
        self,
        prepared: PreparedBidReview,
        item_results: Dict[str, ChecklistItem],
        project_info: Optional[Dict[str, str]] = None,
    ) -> BidChecklistResult:
        """Assemble a BidChecklistResult from accumulated item results."""
        result = BidChecklistResult(
            project_info=project_info or {},
            metadata=ContractMetadata(
                filename=prepared.file_path.split("/")[-1].split("\\")[-1] if prepared.file_path else "unknown",
                analyzed_at=__import__("datetime").datetime.now(),
                page_count=prepared.page_count,
                file_size_bytes=prepared.file_size_bytes,
            ),
        )

        # Populate each section from item_results
        for item_key, checklist_item in item_results.items():
            self._set_item_on_result(result, item_key, checklist_item)

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _keyword_search(
        self, text: str, item_key: str, display_name: str, max_snippets: int = 3
    ) -> List[str]:
        """Simple keyword search fallback when regex finds nothing."""
        keywords = display_name.lower().split()
        # Add some domain-specific keywords from item_key
        keywords.extend(item_key.replace("_", " ").split())
        keywords = list(set(keywords))

        snippets = []
        text_lower = text.lower()
        for kw in keywords:
            if len(kw) < 3:
                continue
            idx = 0
            while idx < len(text_lower) and len(snippets) < max_snippets * 2:
                pos = text_lower.find(kw, idx)
                if pos == -1:
                    break
                start = max(0, pos - 300)
                end = min(len(text), pos + 300)
                snippets.append(text[start:end])
                idx = pos + len(kw)

        return snippets[:max_snippets]

    def _merge_contexts(self, parts: List[str], max_chars: int) -> str:
        """Merge context snippets, removing duplicates, respecting max length."""
        merged = []
        total_len = 0
        seen_starts = set()

        for part in parts:
            # Simple dedup: check if first 50 chars already seen
            sig = part[:50].strip().lower()
            if sig in seen_starts:
                continue
            seen_starts.add(sig)

            if total_len + len(part) > max_chars:
                remaining = max_chars - total_len
                if remaining > 100:
                    merged.append(part[:remaining] + "...")
                break
            merged.append(part)
            total_len += len(part)

        return "\n\n---\n\n".join(merged)

    def _build_single_item_prompt(
        self,
        display_name: str,
        description: str,
        context_text: str,
        regex_value: Optional[str] = None,
    ) -> str:
        """Build the user prompt for a single checklist item."""
        parts = [
            f"CHECKLIST ITEM: {display_name}",
            f"GUIDANCE: {description}",
        ]
        if regex_value:
            parts.append(f"POSSIBLE VALUE FOUND BY PATTERN MATCHING: {regex_value}")

        parts.append(
            "\nBelow are sections from a bid specification document. "
            "Extract the specific value or requirement for this checklist item."
        )
        parts.append(f"\n{context_text}")
        parts.append(
            "\nRespond in this EXACT format (3 lines only):\n"
            "VALUE: [the extracted value, or NOT FOUND]\n"
            "LOCATION: [where found in document, e.g. Section 00700, Article 4.2, or UNKNOWN]\n"
            "NOTES: [any conditions, exceptions, or additional details, or NONE]"
        )
        return "\n".join(parts)

    def _parse_single_response(
        self, response: str, regex_matches: List[Dict]
    ) -> ChecklistItem:
        """Parse the AI response into a ChecklistItem."""
        lines = response.strip().split("\n")
        value = ""
        location = ""
        notes = ""

        for line in lines:
            line_stripped = line.strip()
            upper = line_stripped.upper()
            if upper.startswith("VALUE:"):
                value = line_stripped[6:].strip()
            elif upper.startswith("LOCATION:"):
                location = line_stripped[9:].strip()
            elif upper.startswith("NOTES:"):
                notes = line_stripped[6:].strip()

        # If AI couldn't parse the format, use the full response as value
        if not value:
            value = response.strip()[:500]

        # Determine confidence
        if not value or value.upper() in ("NOT FOUND", "NOT SPECIFIED", "N/A", "NONE", "UNKNOWN"):
            confidence = "not_found"
            value = "NOT FOUND"
        elif regex_matches:
            # Both regex and AI agree
            confidence = "high"
        else:
            # AI-only (no regex confirmation)
            confidence = "medium"

        # Clean up location/notes
        if location.upper() in ("UNKNOWN", "N/A", "NONE", ""):
            location = ""
        if notes.upper() in ("NONE", "N/A", ""):
            notes = ""

        return ChecklistItem(
            value=value,
            location=location,
            confidence=confidence,
            notes=notes,
        )

    def _set_item_on_result(
        self, result: BidChecklistResult, item_key: str, item: ChecklistItem
    ):
        """Set a ChecklistItem on the appropriate field of BidChecklistResult."""
        section_key, display_name = BID_ITEM_MAP[item_key]

        # Handle nested sub-sections
        if section_key == "cipp.design_performance_requirements":
            if result.cipp.design_requirements is None:
                result.cipp.design_requirements = CIPPDesignRequirements()
            field_name = CIPPDesignRequirements.FIELD_MAP.get(display_name)
            if field_name:
                setattr(result.cipp.design_requirements, field_name, item)
            return

        if section_key == "manhole_rehab.spincast":
            if result.manhole_rehab.spincast is None:
                result.manhole_rehab.spincast = SpincastItems()
            field_name = SpincastItems.FIELD_MAP.get(display_name)
            if field_name:
                setattr(result.manhole_rehab.spincast, field_name, item)
            return

        # Top-level sections
        section_map = {
            "standard_contract_items": result.standard_contract_items,
            "site_conditions": result.site_conditions,
            "cleaning": result.cleaning,
            "cctv": result.cctv,
            "cipp": result.cipp,
            "manhole_rehab": result.manhole_rehab,
        }

        section_obj = section_map.get(section_key)
        if section_obj is None:
            logger.warning("Unknown section key: %s", section_key)
            return

        field_map = getattr(section_obj, "FIELD_MAP", {})
        field_name = field_map.get(display_name)
        if field_name:
            setattr(section_obj, field_name, item)
        else:
            logger.warning("No field mapping for %s in %s", display_name, section_key)
