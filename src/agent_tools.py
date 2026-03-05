"""
Agent Tools for Contract Analysis

This module provides modular tools for contract extraction and analysis,
inspired by OpenContracts' tool architecture pattern.

Architecture Pattern Source: OpenContracts (AGPL-3.0)
- CoreTool dataclass for framework-agnostic tool definitions
- Modular extraction functions
- Tool registry pattern
Source: https://github.com/JSv4/OpenContracts
Files: opencontractserver/llms/tools/core_tools.py

License: Patterns used under AGPL-3.0 with attribution
"""

import re
import logging
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ContractTool:
    """
    Framework-agnostic tool definition for contract analysis.

    This pattern is inspired by OpenContracts' CoreTool architecture,
    allowing tools to work across different LLM frameworks.

    Attributes:
        name: Tool identifier (snake_case)
        description: Human-readable description of what the tool does
        callable: Function that implements the tool
        schema: JSON Schema describing inputs/outputs
        category: Tool category (extraction, search, analysis, etc.)

    Source Pattern: OpenContracts CoreTool
    (opencontractserver/llms/tools/core_tools.py)
    """
    name: str
    description: str
    callable: Callable
    schema: Dict[str, Any]
    category: str = "general"


# =============================================================================
# Contract Search Tools
# =============================================================================

def search_contract_text(
    query: str,
    contract_text: str,
    context_chars: int = 200
) -> List[Dict[str, Any]]:
    """
    Search contract for specific terms and return matching sections.

    Args:
        query: Search term or phrase
        contract_text: Full contract text
        context_chars: Characters of context to include around matches

    Returns:
        List of matches with context:
        [
            {
                "match": "exact matched text",
                "context": "surrounding context",
                "position": char_offset,
                "line_number": line_num
            },
            ...
        ]
    """
    matches = []
    query_lower = query.lower()

    # Split into lines for line number tracking
    lines = contract_text.split('\n')

    char_offset = 0
    for line_num, line in enumerate(lines, 1):
        line_lower = line.lower()

        # Find all occurrences in this line
        start = 0
        while True:
            idx = line_lower.find(query_lower, start)
            if idx == -1:
                break

            # Calculate global character position
            global_pos = char_offset + idx

            # Extract context
            context_start = max(0, global_pos - context_chars)
            context_end = min(len(contract_text), global_pos + len(query) + context_chars)
            context = contract_text[context_start:context_end]

            matches.append({
                "match": line[idx:idx + len(query)],
                "context": context,
                "position": global_pos,
                "line_number": line_num
            })

            start = idx + 1

        char_offset += len(line) + 1  # +1 for newline

    logger.info(f"search_contract_text: found {len(matches)} matches for '{query}'")
    return matches


def find_clauses_by_pattern(
    contract_text: str,
    pattern: str,
    max_results: int = 50
) -> List[Dict[str, Any]]:
    """
    Find clauses matching a regex pattern.

    Args:
        contract_text: Full contract text
        pattern: Regex pattern
        max_results: Maximum number of results to return

    Returns:
        List of matching clauses with metadata
    """
    matches = []

    try:
        regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)

        for match in regex.finditer(contract_text):
            if len(matches) >= max_results:
                break

            matches.append({
                "text": match.group(0),
                "position": match.start(),
                "groups": match.groups() if match.groups() else []
            })

    except re.error as e:
        logger.error(f"Invalid regex pattern: {e}")
        return []

    logger.info(f"find_clauses_by_pattern: found {len(matches)} matches")
    return matches


# =============================================================================
# Party Extraction Tools
# =============================================================================

def extract_parties(contract_text: str) -> List[Dict[str, str]]:
    """
    Extract party names and roles from contract.

    Looks for common patterns like:
    - "This Agreement is entered into by and between [PARTY] and [PARTY]"
    - "CONTRACTOR: [Name]"
    - "OWNER: [Name]"

    Args:
        contract_text: Full contract text

    Returns:
        List of parties:
        [
            {"name": "Party Name", "role": "Contractor", "confidence": 0.9},
            ...
        ]
    """
    parties = []

    # Pattern 1: "between X and Y"
    between_pattern = r'between\s+([A-Z][A-Za-z\s&,.]+?)\s+and\s+([A-Z][A-Za-z\s&,.]+?)[\s,.]'
    for match in re.finditer(between_pattern, contract_text, re.IGNORECASE):
        parties.append({
            "name": match.group(1).strip(),
            "role": "Party",
            "confidence": 0.7
        })
        parties.append({
            "name": match.group(2).strip(),
            "role": "Party",
            "confidence": 0.7
        })

    # Pattern 2: "ROLE: Name" format
    role_pattern = r'(CONTRACTOR|OWNER|CLIENT|VENDOR|SUPPLIER|CUSTOMER|COMPANY):\s*([A-Z][A-Za-z\s&,.]+?)(?:\n|,|;)'
    for match in re.finditer(role_pattern, contract_text):
        parties.append({
            "name": match.group(2).strip(),
            "role": match.group(1).capitalize(),
            "confidence": 0.9
        })

    # Deduplicate by name (case-insensitive)
    seen = set()
    unique_parties = []
    for party in parties:
        name_lower = party["name"].lower()
        if name_lower not in seen:
            seen.add(name_lower)
            unique_parties.append(party)

    logger.info(f"extract_parties: found {len(unique_parties)} unique parties")
    return unique_parties


# =============================================================================
# Financial Terms Extraction
# =============================================================================

def find_financial_terms(contract_text: str) -> Dict[str, Any]:
    """
    Extract monetary amounts and payment terms.

    Args:
        contract_text: Full contract text

    Returns:
        Dictionary with financial information:
        {
            "amounts": [{"value": "$1,000", "context": "..."}],
            "percentages": [{"value": "10%", "context": "..."}],
            "payment_terms": ["30 days", "net 60", ...]
        }
    """
    result = {
        "amounts": [],
        "percentages": [],
        "payment_terms": []
    }

    # Find dollar amounts
    dollar_pattern = r'\$[\d,]+(?:\.\d{2})?'
    for match in re.finditer(dollar_pattern, contract_text):
        context_start = max(0, match.start() - 50)
        context_end = min(len(contract_text), match.end() + 50)
        context = contract_text[context_start:context_end]

        result["amounts"].append({
            "value": match.group(0),
            "context": context,
            "position": match.start()
        })

    # Find percentages
    percent_pattern = r'\d+(?:\.\d+)?%'
    for match in re.finditer(percent_pattern, contract_text):
        context_start = max(0, match.start() - 50)
        context_end = min(len(contract_text), match.end() + 50)
        context = contract_text[context_start:context_end]

        result["percentages"].append({
            "value": match.group(0),
            "context": context,
            "position": match.start()
        })

    # Find payment terms
    payment_terms_patterns = [
        r'net\s+\d+\s+days?',
        r'\d+\s+days?\s+(?:from|after)',
        r'upon\s+(?:completion|delivery|receipt)',
        r'within\s+\d+\s+(?:days?|weeks?|months?)'
    ]

    for pattern in payment_terms_patterns:
        for match in re.finditer(pattern, contract_text, re.IGNORECASE):
            result["payment_terms"].append(match.group(0))

    logger.info(f"find_financial_terms: amounts={len(result['amounts'])}, percentages={len(result['percentages'])}")
    return result


# =============================================================================
# Date Extraction
# =============================================================================

def extract_dates(contract_text: str) -> List[Dict[str, Any]]:
    """
    Extract dates from contract.

    Recognizes formats:
    - MM/DD/YYYY
    - Month DD, YYYY
    - DD Month YYYY

    Args:
        contract_text: Full contract text

    Returns:
        List of dates with context:
        [
            {"date": "01/15/2024", "context": "...", "type": "effective_date"},
            ...
        ]
    """
    dates = []

    # Pattern 1: MM/DD/YYYY
    slash_pattern = r'\b(\d{1,2}/\d{1,2}/\d{4})\b'
    for match in re.finditer(slash_pattern, contract_text):
        context_start = max(0, match.start() - 100)
        context_end = min(len(contract_text), match.end() + 100)
        context = contract_text[context_start:context_end]

        # Determine date type from context
        date_type = "unknown"
        if any(term in context.lower() for term in ["effective", "commenc"]):
            date_type = "effective_date"
        elif any(term in context.lower() for term in ["expir", "termination", "end"]):
            date_type = "expiration_date"

        dates.append({
            "date": match.group(1),
            "context": context,
            "type": date_type,
            "position": match.start()
        })

    # Pattern 2: Month DD, YYYY (e.g., "January 15, 2024")
    month_pattern = r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b'
    for match in re.finditer(month_pattern, contract_text, re.IGNORECASE):
        context_start = max(0, match.start() - 100)
        context_end = min(len(contract_text), match.end() + 100)
        context = contract_text[context_start:context_end]

        dates.append({
            "date": f"{match.group(1)} {match.group(2)}, {match.group(3)}",
            "context": context,
            "type": "unknown",
            "position": match.start()
        })

    logger.info(f"extract_dates: found {len(dates)} dates")
    return dates


# =============================================================================
# Risk Identification
# =============================================================================

def identify_risk_clauses(contract_text: str) -> List[Dict[str, Any]]:
    """
    Identify high-risk contract clauses.

    Looks for keywords associated with risk:
    - Liability, indemnification, damages
    - Termination, breach, default
    - Force majeure, acts of god
    - Confidentiality, non-disclosure

    Args:
        contract_text: Full contract text

    Returns:
        List of potential risk clauses with risk level
    """
    risk_keywords = {
        "high": [
            "unlimited liability",
            "indemnify and hold harmless",
            "joint and several liability",
            "liquidated damages",
            "penalty"
        ],
        "medium": [
            "liability",
            "indemnif",
            "breach",
            "default",
            "termination",
            "force majeure",
            "warranty",
            "representations"
        ],
        "low": [
            "confidential",
            "non-disclosure",
            "proprietary"
        ]
    }

    risk_clauses = []

    for risk_level, keywords in risk_keywords.items():
        for keyword in keywords:
            pattern = re.escape(keyword)
            for match in re.finditer(pattern, contract_text, re.IGNORECASE):
                # Get paragraph containing the match
                para_start = contract_text.rfind('\n\n', 0, match.start())
                para_end = contract_text.find('\n\n', match.end())

                if para_start == -1:
                    para_start = 0
                if para_end == -1:
                    para_end = len(contract_text)

                clause_text = contract_text[para_start:para_end].strip()

                risk_clauses.append({
                    "text": clause_text,
                    "keyword": keyword,
                    "risk_level": risk_level,
                    "position": match.start()
                })

    # Deduplicate by position
    seen_positions = set()
    unique_clauses = []
    for clause in risk_clauses:
        pos_key = clause["position"] // 100  # Group by ~100 char ranges
        if pos_key not in seen_positions:
            seen_positions.add(pos_key)
            unique_clauses.append(clause)

    logger.info(f"identify_risk_clauses: found {len(unique_clauses)} risk clauses")
    return unique_clauses


# =============================================================================
# Tool Registry
# =============================================================================

# Tool definitions following OpenContracts CoreTool pattern
CONTRACT_TOOLS = [
    ContractTool(
        name="search_contract_text",
        description="Search contract for specific terms and return matching sections with context",
        callable=search_contract_text,
        schema={
            "parameters": {
                "query": {"type": "string", "description": "Search term or phrase"},
                "contract_text": {"type": "string", "description": "Full contract text"},
                "context_chars": {"type": "integer", "description": "Context size", "default": 200}
            },
            "returns": {"type": "array", "items": {"type": "object"}}
        },
        category="search"
    ),
    ContractTool(
        name="extract_parties",
        description="Extract party names and roles from contract",
        callable=extract_parties,
        schema={
            "parameters": {
                "contract_text": {"type": "string", "description": "Full contract text"}
            },
            "returns": {"type": "array", "items": {"type": "object"}}
        },
        category="extraction"
    ),
    ContractTool(
        name="find_financial_terms",
        description="Extract monetary amounts, percentages, and payment terms",
        callable=find_financial_terms,
        schema={
            "parameters": {
                "contract_text": {"type": "string", "description": "Full contract text"}
            },
            "returns": {"type": "object"}
        },
        category="extraction"
    ),
    ContractTool(
        name="extract_dates",
        description="Extract all dates from contract and classify them",
        callable=extract_dates,
        schema={
            "parameters": {
                "contract_text": {"type": "string", "description": "Full contract text"}
            },
            "returns": {"type": "array", "items": {"type": "object"}}
        },
        category="extraction"
    ),
    ContractTool(
        name="identify_risk_clauses",
        description="Identify high-risk contract clauses based on keywords",
        callable=identify_risk_clauses,
        schema={
            "parameters": {
                "contract_text": {"type": "string", "description": "Full contract text"}
            },
            "returns": {"type": "array", "items": {"type": "object"}}
        },
        category="analysis"
    ),
    ContractTool(
        name="find_clauses_by_pattern",
        description="Find clauses matching a regex pattern",
        callable=find_clauses_by_pattern,
        schema={
            "parameters": {
                "contract_text": {"type": "string"},
                "pattern": {"type": "string"},
                "max_results": {"type": "integer", "default": 50}
            },
            "returns": {"type": "array"}
        },
        category="search"
    )
]


def get_tool_by_name(name: str) -> Optional[ContractTool]:
    """
    Get tool by name from registry.

    Args:
        name: Tool name

    Returns:
        ContractTool instance or None if not found
    """
    for tool in CONTRACT_TOOLS:
        if tool.name == name:
            return tool
    return None


def get_tools_by_category(category: str) -> List[ContractTool]:
    """
    Get all tools in a category.

    Args:
        category: Tool category (search, extraction, analysis)

    Returns:
        List of ContractTool instances
    """
    return [tool for tool in CONTRACT_TOOLS if tool.category == category]
