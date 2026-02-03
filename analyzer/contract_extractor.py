"""
Contract Section Extractor
Uses regex patterns to identify and extract relevant sections from contracts.
This reduces the amount of text sent to the AI API.
"""

import re
from typing import Dict, List, Tuple


# Common section headers and their variations
SECTION_PATTERNS = {
    'payment_terms': [
        r'payment\s+terms?',
        r'compensation',
        r'price',
        r'contract\s+(?:price|value|amount)',
        r'payment\s+schedule',
        r'invoicing',
        r'retainage',
        r'progress\s+payments?'
    ],
    'scope_of_work': [
        r'scope\s+of\s+work',
        r'work\s+to\s+be\s+performed',
        r'services',
        r'deliverables',
        r'project\s+description'
    ],
    'term_duration': [
        r'term\s+(?:of\s+)?(?:contract|agreement)',
        r'contract\s+period',
        r'duration',
        r'commencement',
        r'effective\s+date',
        r'expiration'
    ],
    'termination': [
        r'termination',
        r'cancellation',
        r'early\s+termination',
        r'termination\s+for\s+convenience',
        r'termination\s+for\s+cause'
    ],
    'indemnification': [
        r'indemnif(?:y|ication)',
        r'hold\s+harmless',
        r'defend',
        r'liability'
    ],
    'insurance': [
        r'insurance',
        r'coverage',
        r'additional\s+insured',
        r'waiver\s+of\s+subrogation'
    ],
    'warranties': [
        r'warrant(?:y|ies)',
        r'guarantee',
        r'defects?\s+liability'
    ],
    'dispute_resolution': [
        r'dispute\s+resolution',
        r'arbitration',
        r'mediation',
        r'litigation',
        r'governing\s+law'
    ],
    'change_orders': [
        r'change\s+orders?',
        r'modifications?',
        r'amendments?',
        r'scope\s+changes?'
    ],
    'delays': [
        r'delays?',
        r'force\s+majeure',
        r'excusable\s+delays?',
        r'time\s+extensions?'
    ],
    'parties': [
        r'parties',
        r'contractor',
        r'owner',
        r'client',
        r'vendor',
        r'between.*and'
    ]
}


def extract_section_context(text: str, start_pos: int, context_chars: int = 2000) -> str:
    """
    Extract text around a found pattern with context.
    
    Args:
        text: Full contract text
        start_pos: Position where pattern was found
        context_chars: Number of characters to include before and after
    
    Returns:
        Text snippet with context
    """
    start = max(0, start_pos - context_chars)
    end = min(len(text), start_pos + context_chars)
    return text[start:end]


def find_section_by_patterns(text: str, patterns: List[str]) -> List[Tuple[int, str]]:
    """
    Find all occurrences of patterns in text.
    
    Args:
        text: Contract text to search
        patterns: List of regex patterns
    
    Returns:
        List of (position, matched_text) tuples
    """
    matches = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            matches.append((match.start(), match.group()))
    return matches


def extract_relevant_sections(contract_text: str, max_chars: int = 100000) -> Dict[str, str]:
    """
    Extract relevant sections from contract using pattern matching.
    
    Args:
        contract_text: Full contract text
        max_chars: Maximum characters to extract (to stay within token limits)
    
    Returns:
        Dictionary mapping section names to extracted text
    """
    sections = {}
    total_chars = 0
    
    # Track which parts of the contract we've already extracted
    extracted_ranges = []
    
    for section_name, patterns in SECTION_PATTERNS.items():
        matches = find_section_by_patterns(contract_text, patterns)
        
        if matches:
            # Get context around each match
            section_texts = []
            for pos, matched_text in matches:
                # Check if we've already extracted this area
                already_extracted = False
                for start, end in extracted_ranges:
                    if start <= pos <= end:
                        already_extracted = True
                        break
                
                if not already_extracted:
                    context = extract_section_context(contract_text, pos, context_chars=1500)
                    section_texts.append(context)
                    
                    # Mark this range as extracted
                    context_start = max(0, pos - 1500)
                    context_end = min(len(contract_text), pos + 1500)
                    extracted_ranges.append((context_start, context_end))
                    
                    total_chars += len(context)
                    
                    # Stop if we've extracted enough
                    if total_chars >= max_chars:
                        break
            
            if section_texts:
                sections[section_name] = '\n\n---\n\n'.join(section_texts)
        
        if total_chars >= max_chars:
            break
    
    return sections


def extract_key_information(contract_text: str) -> Dict[str, any]:
    """
    Extract key information using regex patterns.
    
    Args:
        contract_text: Full contract text
    
    Returns:
        Dictionary with extracted information
    """
    info = {}
    
    # Extract dates
    date_pattern = r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'
    dates = re.findall(date_pattern, contract_text, re.IGNORECASE)
    if dates:
        info['dates_found'] = dates[:5]  # First 5 dates
    
    # Extract dollar amounts
    money_pattern = r'\$[\d,]+(?:\.\d{2})?'
    amounts = re.findall(money_pattern, contract_text)
    if amounts:
        info['amounts_found'] = amounts[:10]  # First 10 amounts
    
    # Extract percentages
    percent_pattern = r'\b\d+(?:\.\d+)?%'
    percentages = re.findall(percent_pattern, contract_text)
    if percentages:
        info['percentages_found'] = percentages[:10]
    
    # Extract email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, contract_text)
    if emails:
        info['emails_found'] = emails
    
    # Extract phone numbers
    phone_pattern = r'\b(?:\+?1[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b'
    phones = re.findall(phone_pattern, contract_text)
    if phones:
        info['phones_found'] = phones
    
    return info


def create_focused_contract(contract_text: str, max_chars: int = 100000) -> Tuple[str, Dict]:
    """
    Create a focused version of the contract with only relevant sections.
    
    Args:
        contract_text: Full contract text
        max_chars: Maximum characters for focused version
    
    Returns:
        Tuple of (focused_text, metadata)
    """
    # Extract relevant sections
    sections = extract_relevant_sections(contract_text, max_chars)
    
    # Extract key information
    key_info = extract_key_information(contract_text)
    
    # Build focused contract text
    focused_parts = []
    
    # Add a summary header
    focused_parts.append("=== EXTRACTED RELEVANT SECTIONS ===\n")
    
    # Add each section
    for section_name, section_text in sections.items():
        focused_parts.append(f"\n=== {section_name.upper().replace('_', ' ')} ===\n")
        focused_parts.append(section_text)
    
    focused_text = '\n'.join(focused_parts)
    
    # Create metadata
    metadata = {
        'original_length': len(contract_text),
        'focused_length': len(focused_text),
        'reduction_percent': round((1 - len(focused_text) / len(contract_text)) * 100, 1),
        'sections_extracted': list(sections.keys()),
        'key_info': key_info
    }
    
    return focused_text, metadata


def should_use_extraction(contract_text: str, token_limit: int = 100000) -> bool:
    """
    Determine if we should use extraction or send full contract.
    
    Args:
        contract_text: Full contract text
        token_limit: Token limit for decision
    
    Returns:
        True if extraction should be used
    """
    # Rough estimate: 1 token ≈ 4 characters
    estimated_tokens = len(contract_text) // 4
    return estimated_tokens > token_limit


# Example usage
if __name__ == "__main__":
    # Test with sample text
    sample_contract = """
    CONSTRUCTION CONTRACT
    
    This agreement is made on January 15, 2024 between ABC Construction (Contractor)
    and State DOT (Owner).
    
    PAYMENT TERMS
    The contract price is $5,000,000. Payment shall be made within 30 days of invoice.
    Retainage of 10% will be held until final completion.
    
    SCOPE OF WORK
    Contractor shall perform all work necessary to complete the highway construction
    project as described in the attached specifications.
    
    TERMINATION
    Either party may terminate this agreement with 30 days written notice.
    Owner may terminate for convenience with payment for work performed.
    
    INDEMNIFICATION
    Contractor shall indemnify and hold harmless Owner from all claims arising
    from Contractor's performance of the work.
    """
    
    focused, metadata = create_focused_contract(sample_contract)
    print("Original length:", metadata['original_length'])
    print("Focused length:", metadata['focused_length'])
    print("Reduction:", metadata['reduction_percent'], "%")
    print("\nSections found:", metadata['sections_extracted'])
    print("\nFocused contract:")
    print(focused)
