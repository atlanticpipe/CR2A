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
