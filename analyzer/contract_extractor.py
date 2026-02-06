"""Comprehensive contract clause extractor using regex patterns."""

import re
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class ComprehensiveContractExtractor:
    """Extract contract clauses using regex patterns."""
    
    def __init__(self):
        """Initialize extractor with comprehensive regex patterns."""
        self.clause_patterns = {
            # Section patterns: Section 1, Section 1.1, Section 1.1.1, etc.
            'section': [
                r'Section\s+([0-9]+(?:\.[0-9]+)*)\s*[:\-]?\s*([^\n]+?)(?=\n|$)',
                r'SECTION\s+([0-9]+(?:\.[0-9]+)*)\s*[:\-]?\s*([^\n]+?)(?=\n|$)',
                r'§\s*([0-9]+(?:\.[0-9]+)*)\s*[:\-]?\s*([^\n]+?)(?=\n|$)',
            ],
            # Article patterns: Article I, Article II, Article 1, etc.
            'article': [
                r'Article\s+([IVX]+|[0-9]+)\s*[:\-]?\s*([^\n]+?)(?=\n|$)',
                r'ARTICLE\s+([IVX]+|[0-9]+)\s*[:\-]?\s*([^\n]+?)(?=\n|$)',
            ],
            # Clause patterns: Clause 1, Clause A, etc.
            'clause': [
                r'Clause\s+([0-9]+|[A-Z])\s*[:\-]?\s*([^\n]+?)(?=\n|$)',
                r'CLAUSE\s+([0-9]+|[A-Z])\s*[:\-]?\s*([^\n]+?)(?=\n|$)',
            ],
            # Paragraph/subsection patterns
            'paragraph': [
                r'\(([a-z]|[0-9]+)\)\s*([^\n]+?)(?=\n|$)',
                r'\(([ivx]+)\)\s*([^\n]+?)(?=\n|$)',
            ],
            # Definition clauses
            'definition': [
                r'"([^"]+)"\s+(?:means|shall mean|is defined as)\s+([^.;]+)',
                r'([A-Z][A-Za-z\s]+)\s+(?:means|shall mean|is defined as)\s+([^.;]+)',
            ],
        }
        
        # Common contract clause types to search for
        self.important_clauses = {
            'termination': [
                r'termination[^.]*?(?:\.|;)',
                r'terminate[^.]*?(?:\.|;)',
                r'cancellation[^.]*?(?:\.|;)',
            ],
            'payment': [
                r'payment[^.]*?(?:\.|;)',
                r'compensation[^.]*?(?:\.|;)',
                r'fee[^.]*?(?:\.|;)',
                r'\$[0-9,]+(?:\.[0-9]{2})?',
            ],
            'liability': [
                r'liability[^.]*?(?:\.|;)',
                r'indemnif[^.]*?(?:\.|;)',
                r'damages[^.]*?(?:\.|;)',
            ],
            'confidentiality': [
                r'confidential[^.]*?(?:\.|;)',
                r'non-disclosure[^.]*?(?:\.|;)',
                r'proprietary[^.]*?(?:\.|;)',
            ],
            'intellectual_property': [
                r'intellectual property[^.]*?(?:\.|;)',
                r'copyright[^.]*?(?:\.|;)',
                r'patent[^.]*?(?:\.|;)',
                r'trademark[^.]*?(?:\.|;)',
            ],
            'governing_law': [
                r'governing law[^.]*?(?:\.|;)',
                r'jurisdiction[^.]*?(?:\.|;)',
            ],
            'force_majeure': [
                r'force majeure[^.]*?(?:\.|;)',
            ],
            'warranty': [
                r'warrant[^.]*?(?:\.|;)',
                r'guarantee[^.]*?(?:\.|;)',
            ],
        }
    
    def extract_all_clauses(self, text: str) -> Dict[str, List[Dict]]:
        """Extract all contract clauses from text.
        
        Args:
            text: Contract text to analyze
            
        Returns:
            Dictionary with clause types as keys and lists of extracted clauses
        """
        results = {
            'sections': [],
            'articles': [],
            'clauses': [],
            'paragraphs': [],
            'definitions': [],
            'important_clauses': {}
        }
        
        try:
            # Extract structured clauses (sections, articles, etc.)
            for clause_type, patterns in self.clause_patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                    for match in matches:
                        clause_data = {
                            'number': match.group(1),
                            'title': match.group(2).strip() if len(match.groups()) > 1 else '',
                            'position': match.start(),
                            'full_text': match.group(0)
                        }
                        
                        # Get context (surrounding text)
                        context_start = max(0, match.start() - 50)
                        context_end = min(len(text), match.end() + 200)
                        clause_data['context'] = text[context_start:context_end]
                        
                        if clause_type == 'section':
                            results['sections'].append(clause_data)
                        elif clause_type == 'article':
                            results['articles'].append(clause_data)
                        elif clause_type == 'clause':
                            results['clauses'].append(clause_data)
                        elif clause_type == 'paragraph':
                            results['paragraphs'].append(clause_data)
                        elif clause_type == 'definition':
                            results['definitions'].append(clause_data)
            
            # Extract important clause types
            for clause_category, patterns in self.important_clauses.items():
                category_matches = []
                for pattern in patterns:
                    matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                    for match in matches:
                        # Get full sentence context
                        sentence_start = text.rfind('.', 0, match.start()) + 1
                        sentence_end = text.find('.', match.end()) + 1
                        if sentence_end == 0:
                            sentence_end = len(text)
                        
                        category_matches.append({
                            'text': match.group(0),
                            'position': match.start(),
                            'context': text[sentence_start:sentence_end].strip()
                        })
                
                if category_matches:
                    results['important_clauses'][clause_category] = category_matches
            
            # Log extraction summary
            logger.info(f"Extracted {len(results['sections'])} sections, "
                       f"{len(results['articles'])} articles, "
                       f"{len(results['clauses'])} clauses")
            
        except Exception as e:
            logger.error(f"Error extracting clauses: {e}")
        
        return results
    
    def get_clause_summary(self, extraction_results: Dict) -> str:
        """Generate a summary of extracted clauses.
        
        Args:
            extraction_results: Results from extract_all_clauses()
            
        Returns:
            Human-readable summary string
        """
        summary_parts = []
        
        if extraction_results['sections']:
            summary_parts.append(f"Found {len(extraction_results['sections'])} sections")
        
        if extraction_results['articles']:
            summary_parts.append(f"Found {len(extraction_results['articles'])} articles")
        
        if extraction_results['important_clauses']:
            for category, matches in extraction_results['important_clauses'].items():
                summary_parts.append(f"Found {len(matches)} {category.replace('_', ' ')} clauses")
        
        return "\n".join(summary_parts) if summary_parts else "No clauses extracted"
    
    def create_focused_contract(self, text: str) -> Tuple[str, Dict]:
        """Create a focused version of the contract with extracted clauses.
        
        Args:
            text: Full contract text
            
        Returns:
            Tuple of (focused_contract_text, extraction_metadata)
        """
        try:
            # Extract all clauses
            extraction_results = self.extract_all_clauses(text)
            
            # Build focused contract text with all extracted clauses
            focused_parts = []
            
            # Add sections
            if extraction_results['sections']:
                focused_parts.append("=== SECTIONS ===")
                for section in extraction_results['sections']:
                    focused_parts.append(f"\n{section['full_text']}")
                    if section.get('context'):
                        focused_parts.append(section['context'])
            
            # Add articles
            if extraction_results['articles']:
                focused_parts.append("\n\n=== ARTICLES ===")
                for article in extraction_results['articles']:
                    focused_parts.append(f"\n{article['full_text']}")
                    if article.get('context'):
                        focused_parts.append(article['context'])
            
            # Add important clause categories
            if extraction_results['important_clauses']:
                focused_parts.append("\n\n=== KEY CLAUSES ===")
                for category, matches in extraction_results['important_clauses'].items():
                    focused_parts.append(f"\n--- {category.replace('_', ' ').title()} ---")
                    for match in matches:
                        focused_parts.append(match['context'])
            
            # Add definitions if found
            if extraction_results['definitions']:
                focused_parts.append("\n\n=== DEFINITIONS ===")
                for definition in extraction_results['definitions']:
                    focused_parts.append(f"\n{definition['full_text']}")
            
            # Join all parts
            focused_contract = "\n".join(focused_parts)
            
            # Create metadata
            metadata = {
                'original_length': len(text),
                'focused_length': len(focused_contract),
                'reduction_percent': ((len(text) - len(focused_contract)) / len(text) * 100) if len(text) > 0 else 0,
                'total_categories': (
                    len(extraction_results['sections']) +
                    len(extraction_results['articles']) +
                    len(extraction_results['important_clauses']) +
                    len(extraction_results['definitions'])
                ),
                'sections_found': len(extraction_results['sections']),
                'articles_found': len(extraction_results['articles']),
                'definitions_found': len(extraction_results['definitions']),
                'important_clause_categories': len(extraction_results['important_clauses'])
            }
            
            logger.info(f"Created focused contract: {metadata['total_categories']} categories, "
                       f"{metadata['reduction_percent']:.1f}% reduction")
            
            return focused_contract, metadata
            
        except Exception as e:
            logger.error(f"Error creating focused contract: {e}")
            # Return original text on error
            return text, {
                'original_length': len(text),
                'focused_length': len(text),
                'reduction_percent': 0,
                'total_categories': 0,
                'error': str(e)
            }
