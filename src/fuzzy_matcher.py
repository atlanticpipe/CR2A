"""Fuzzy Logic Matcher for Contract Clause Detection

This module provides fuzzy string matching capabilities to help identify
relevant clause categories in contract text even when exact terminology
is not present. Uses RapidFuzz for high-performance fuzzy matching.

The fuzzy matcher helps address the issue where contracts use different
terminology for the same concepts (e.g., "hold harmless" vs "indemnification").
"""

from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
import re
from rapidfuzz import fuzz, process


@dataclass
class FuzzyMatch:
    """Represents a fuzzy match between contract text and a clause category.

    Attributes:
        category: The matched clause category name.
        score: Match confidence score (0-100).
        matched_text: The portion of contract text that matched.
        section: The section this category belongs to.
        keywords: Keywords that contributed to the match.
    """
    category: str
    score: float
    matched_text: str
    section: str
    keywords: List[str]


class FuzzyClauseMatcher:
    """Fuzzy logic matcher for identifying relevant clause categories.

    This class uses fuzzy string matching algorithms to identify which
    clause categories are likely present in a contract, even when the
    exact category names don't appear in the text.

    Attributes:
        confidence_threshold: Minimum confidence score (0-100) for matches.
        keyword_mappings: Dictionary mapping clause categories to their keywords.
    """

    # Keyword mappings for each clause category
    # Maps category names to lists of related terms/keywords
    KEYWORD_MAPPINGS = {
        # Administrative & Commercial Terms
        "Contract Term, Renewal & Extensions": [
            "contract term", "term of contract", "duration", "renewal", "extension",
            "expiration", "commence", "effective date", "termination date"
        ],
        "Payment Terms & Invoicing": [
            "payment", "invoice", "invoicing", "compensation", "pay", "billing",
            "payment schedule", "payment terms", "remittance", "amount due"
        ],
        "Retainage & Progress Payments": [
            "retainage", "retention", "holdback", "progress payment", "draw",
            "payment application", "milestone payment", "periodic payment"
        ],
        "Bonding, Surety, & Insurance Obligations": [
            "bond", "bonding", "surety", "performance bond", "payment bond",
            "insurance", "liability insurance", "coverage", "policy"
        ],
        "Change Orders & Extra Work": [
            "change order", "modification", "amendment", "extra work", "additional work",
            "scope change", "variation", "adjustment", "supplemental work"
        ],
        "Notice Requirements & Effective Service": [
            "notice", "notification", "notify", "written notice", "service",
            "delivery", "communication", "inform", "advise in writing"
        ],
        "Pricing Model & Unit Rates": [
            "pricing", "price", "unit price", "unit rate", "cost", "rate",
            "lump sum", "fixed price", "unit cost", "cost breakdown"
        ],
        "Subcontracting & Assignment Restrictions": [
            "subcontract", "subcontractor", "assignment", "delegate", "substitution",
            "assign", "transfer", "novation", "subletting"
        ],
        "Termination for Convenience": [
            "termination for convenience", "terminate", "cancellation",
            "early termination", "owner may terminate", "right to terminate"
        ],
        "Termination for Cause/Default": [
            "termination for cause", "default", "breach", "termination for default",
            "material breach", "failure to perform", "cure period"
        ],

        # Technical & Performance Terms
        "Schedule, Milestones, & Time-Related Damages": [
            "schedule", "milestone", "completion date", "deadline", "time is of the essence",
            "substantial completion", "final completion", "critical path"
        ],
        "Delay Damages & Liquidated Damages": [
            "liquidated damages", "delay damages", "damages for delay", "LD",
            "daily damages", "penalty", "time extension"
        ],
        "Force Majeure & Excusable Delays": [
            "force majeure", "excusable delay", "unavoidable delay", "acts of god",
            "unforeseeable", "beyond control", "epidemic", "pandemic", "natural disaster"
        ],
        "Performance Standards & Acceptance Criteria": [
            "performance standard", "specification", "acceptance criteria",
            "quality standard", "workmanship", "conformance", "compliance with specs"
        ],
        "Testing & Commissioning": [
            "testing", "test", "commissioning", "startup", "performance test",
            "acceptance test", "inspection", "functional test", "trial run"
        ],
        "Warranties & Guarantees": [
            "warranty", "guarantee", "warranted", "guaranteed", "defect",
            "workmanship warranty", "materials warranty", "warranty period"
        ],
        "Defect Correction & Punch List": [
            "defect", "punch list", "punchlist", "correction", "repair",
            "deficiency", "remedy", "fix", "rework", "non-conformance"
        ],
        "Site Access & Coordination": [
            "site access", "access", "coordination", "site conditions",
            "workspace", "premises", "entry", "right of way", "possession"
        ],

        # Legal Risk & Enforcement
        "Indemnification": [
            "indemnify", "indemnification", "hold harmless", "defend",
            "indemnity", "save harmless", "indemnitor", "indemnitee"
        ],
        "Limitation of Liability": [
            "limitation of liability", "limit liability", "cap on damages",
            "liability cap", "maximum liability", "sole remedy", "exclusive remedy"
        ],
        "Consequential Damages Waiver": [
            "consequential damages", "indirect damages", "waive", "waiver",
            "incidental damages", "lost profits", "special damages"
        ],
        "Dispute Resolution (ADR, Arbitration, Litigation)": [
            "dispute resolution", "arbitration", "mediation", "litigation",
            "ADR", "alternative dispute resolution", "claim", "controversy"
        ],
        "Governing Law & Venue": [
            "governing law", "choice of law", "venue", "jurisdiction",
            "forum", "applicable law", "laws of", "subject to laws"
        ],
        "Attorney Fees & Cost Allocation": [
            "attorney fees", "attorneys' fees", "legal fees", "cost",
            "prevailing party", "litigation costs", "court costs"
        ],
        "Severability & Survival": [
            "severability", "severable", "survival", "survive",
            "invalid provision", "unenforceable", "remain in effect"
        ],
        "Compliance Certification & Attestation": [
            "certification", "certify", "attestation", "attest",
            "represent and warrant", "compliance certificate", "sworn statement"
        ],

        # Regulatory & Compliance Terms
        "Davis-Bacon & Prevailing Wage": [
            "davis-bacon", "prevailing wage", "wage rate", "labor standards",
            "certified payroll", "wage determination"
        ],
        "Buy America / BABA Provisions": [
            "buy america", "BABA", "domestic content", "american made",
            "manufactured in USA", "US produced", "iron and steel"
        ],
        "DBE/MBE/WBE Goals": [
            "DBE", "MBE", "WBE", "disadvantaged business", "minority business",
            "women-owned business", "small business", "participation goal"
        ],
        "Environmental & Safety Compliance": [
            "environmental", "safety", "OSHA", "EPA", "hazardous materials",
            "MSDS", "safety plan", "environmental compliance", "pollution"
        ],
        "Permits & Regulatory Approvals": [
            "permit", "license", "approval", "authorization", "regulatory",
            "consent", "clearance", "certification", "inspection"
        ],
        "Labor & Employment Requirements": [
            "labor", "employment", "worker", "employee", "employment practices",
            "equal opportunity", "non-discrimination", "background check"
        ],

        # Data, Technology & Deliverables
        "Document Retention & Recordkeeping": [
            "document retention", "recordkeeping", "maintain records", "record",
            "preserve documents", "retention period", "archive", "file"
        ],
        "Confidentiality & NDA": [
            "confidential", "confidentiality", "NDA", "non-disclosure",
            "proprietary", "trade secret", "confidential information"
        ],

        "Software/Data Escrow": [
            "escrow", "source code", "software escrow", "data escrow",
            "escrow agent", "release conditions", "deposit materials"
        ],
        "Electronic Signature & Communications": [
            "electronic signature", "e-signature", "digital signature",
            "electronic communication", "email", "facsimile", "electronic delivery"
        ],
        "Cybersecurity & Data Protection": [
            "cybersecurity", "data protection", "data security", "breach",
            "data breach", "security incident", "encryption", "firewall"
        ],
    }

    # Section mappings for each category
    SECTION_MAPPINGS = {
        "Contract Term, Renewal & Extensions": "administrative_and_commercial_terms",
        "Payment Terms & Invoicing": "administrative_and_commercial_terms",
        "Retainage & Progress Payments": "administrative_and_commercial_terms",
        "Bonding, Surety, & Insurance Obligations": "administrative_and_commercial_terms",
        "Change Orders & Extra Work": "administrative_and_commercial_terms",
        "Notice Requirements & Effective Service": "administrative_and_commercial_terms",
        "Pricing Model & Unit Rates": "administrative_and_commercial_terms",
        "Subcontracting & Assignment Restrictions": "administrative_and_commercial_terms",
        "Termination for Convenience": "administrative_and_commercial_terms",
        "Termination for Cause/Default": "administrative_and_commercial_terms",
        "Schedule, Milestones, & Time-Related Damages": "technical_and_performance_terms",
        "Delay Damages & Liquidated Damages": "technical_and_performance_terms",
        "Force Majeure & Excusable Delays": "technical_and_performance_terms",
        "Performance Standards & Acceptance Criteria": "technical_and_performance_terms",
        "Testing & Commissioning": "technical_and_performance_terms",
        "Warranties & Guarantees": "technical_and_performance_terms",
        "Defect Correction & Punch List": "technical_and_performance_terms",
        "Site Access & Coordination": "technical_and_performance_terms",
        "Indemnification": "legal_risk_and_enforcement",
        "Limitation of Liability": "legal_risk_and_enforcement",
        "Consequential Damages Waiver": "legal_risk_and_enforcement",
        "Dispute Resolution (ADR, Arbitration, Litigation)": "legal_risk_and_enforcement",
        "Governing Law & Venue": "legal_risk_and_enforcement",
        "Attorney Fees & Cost Allocation": "legal_risk_and_enforcement",
        "Severability & Survival": "legal_risk_and_enforcement",
        "Compliance Certification & Attestation": "legal_risk_and_enforcement",
        "Davis-Bacon & Prevailing Wage": "regulatory_and_compliance_terms",
        "Buy America / BABA Provisions": "regulatory_and_compliance_terms",
        "DBE/MBE/WBE Goals": "regulatory_and_compliance_terms",
        "Environmental & Safety Compliance": "regulatory_and_compliance_terms",
        "Permits & Regulatory Approvals": "regulatory_and_compliance_terms",
        "Labor & Employment Requirements": "regulatory_and_compliance_terms",
        "Document Retention & Recordkeeping": "data_technology_and_deliverables",
        "Confidentiality & NDA": "data_technology_and_deliverables",

        "Software/Data Escrow": "data_technology_and_deliverables",
        "Electronic Signature & Communications": "data_technology_and_deliverables",
        "Cybersecurity & Data Protection": "data_technology_and_deliverables",
    }

    def __init__(self, confidence_threshold: float = 65.0):
        """Initialize the fuzzy matcher.

        Args:
            confidence_threshold: Minimum confidence score (0-100) for matches.
                Default is 65.0, which provides a good balance between
                recall and precision.
        """
        self.confidence_threshold = confidence_threshold
        self.keyword_mappings = self.KEYWORD_MAPPINGS
        self.section_mappings = self.SECTION_MAPPINGS

    def find_matching_categories(
        self,
        contract_text: str,
        min_matches: int = 20
    ) -> List[FuzzyMatch]:
        """Find clause categories that likely appear in the contract text.

        Uses fuzzy string matching to identify relevant categories even when
        exact terminology is not present. This helps ensure comprehensive
        extraction across all applicable categories.

        Args:
            contract_text: The full contract text to analyze.
            min_matches: Minimum number of category matches to return.
                If fewer high-confidence matches are found, the threshold
                is lowered to meet this minimum.

        Returns:
            List of FuzzyMatch objects sorted by confidence score (highest first).
        """
        # Normalize contract text
        normalized_text = self._normalize_text(contract_text)

        # Extract meaningful phrases from contract (3-5 word phrases)
        contract_phrases = self._extract_phrases(normalized_text)

        matches = []

        # Check each category against contract text
        for category, keywords in self.keyword_mappings.items():
            # Find best matching keyword for this category
            best_match = self._find_best_keyword_match(
                category,
                keywords,
                contract_phrases,
                normalized_text
            )

            if best_match:
                matches.append(best_match)

        # Sort by confidence score (descending)
        matches.sort(key=lambda x: x.score, reverse=True)

        # Ensure we return at least min_matches categories
        if len(matches) < min_matches:
            # Lower threshold and retry
            original_threshold = self.confidence_threshold
            self.confidence_threshold = max(40.0, self.confidence_threshold - 15.0)

            matches = self.find_matching_categories(contract_text, min_matches=0)

            # Restore original threshold
            self.confidence_threshold = original_threshold

        # Take top matches that meet threshold
        filtered_matches = [
            m for m in matches
            if m.score >= self.confidence_threshold
        ]

        # Ensure minimum count
        if len(filtered_matches) < min_matches and matches:
            filtered_matches = matches[:min_matches]

        return filtered_matches

    def get_category_suggestions(
        self,
        contract_text: str,
        section: Optional[str] = None
    ) -> List[str]:
        """Get a list of suggested category names for the contract.

        Args:
            contract_text: The contract text to analyze.
            section: Optional section name to filter suggestions.

        Returns:
            List of category names that likely apply to this contract.
        """
        matches = self.find_matching_categories(contract_text)

        if section:
            matches = [m for m in matches if m.section == section]

        return [m.category for m in matches]

    def _normalize_text(self, text: str) -> str:
        """Normalize text for fuzzy matching.

        Args:
            text: Raw text to normalize.

        Returns:
            Normalized lowercase text with standardized whitespace.
        """
        # Convert to lowercase
        text = text.lower()

        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)

        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\-,.]', ' ', text)

        return text.strip()

    def _extract_phrases(self, text: str, max_phrases: int = 500) -> List[str]:
        """Extract meaningful phrases from text for matching.

        Samples phrases from across the ENTIRE document (not just the start)
        to ensure coverage of all contract sections.

        Args:
            text: Normalized text to extract phrases from.
            max_phrases: Maximum number of phrases to extract.

        Returns:
            List of 3-5 word phrases sampled across the full document.
        """
        words = text.split()
        total_words = len(words)

        if total_words <= 5000:
            # Short document — use all words (original behavior)
            phrases = []
            for i in range(total_words - 2):
                phrases.append(' '.join(words[i:i+3]))
            for i in range(total_words - 3):
                phrases.append(' '.join(words[i:i+4]))
            for i in range(total_words - 4):
                phrases.append(' '.join(words[i:i+5]))
            return phrases[:max_phrases]

        # Long document — sample evenly across the entire text
        # We want max_phrases total, split across 3/4/5-word phrases
        phrases_per_size = max_phrases // 3
        step = max(1, total_words // phrases_per_size)

        phrases = []
        for i in range(0, total_words - 2, step):
            phrases.append(' '.join(words[i:i+3]))
        for i in range(0, total_words - 3, step):
            phrases.append(' '.join(words[i:i+4]))
        for i in range(0, total_words - 4, step):
            phrases.append(' '.join(words[i:i+5]))

        return phrases[:max_phrases]

    def _find_best_keyword_match(
        self,
        category: str,
        keywords: List[str],
        contract_phrases: List[str],
        contract_text: str
    ) -> Optional[FuzzyMatch]:
        """Find the best fuzzy match between keywords and contract text.

        Args:
            category: The clause category name.
            keywords: List of keywords associated with this category.
            contract_phrases: Extracted phrases from contract text.
            contract_text: Full normalized contract text.

        Returns:
            FuzzyMatch object if a good match is found, None otherwise.
        """
        best_score = 0.0
        best_keyword = None
        best_matched_text = ""

        # Check each keyword against contract phrases
        for keyword in keywords:
            # Use RapidFuzz to find best match
            result = process.extractOne(
                keyword,
                contract_phrases,
                scorer=fuzz.token_set_ratio
            )

            if result:
                matched_phrase, score, _ = result

                if score > best_score:
                    best_score = score
                    best_keyword = keyword
                    best_matched_text = matched_phrase

        # Also check for exact substring matches (these get bonus points)
        for keyword in keywords:
            if keyword in contract_text:
                # Exact match - boost score significantly
                best_score = max(best_score, 95.0)
                best_keyword = keyword
                # Extract surrounding context
                idx = contract_text.index(keyword)
                start = max(0, idx - 50)
                end = min(len(contract_text), idx + len(keyword) + 50)
                best_matched_text = contract_text[start:end].strip()
                break

        if best_score >= self.confidence_threshold:
            section = self.section_mappings.get(category, "unknown")

            return FuzzyMatch(
                category=category,
                score=best_score,
                matched_text=best_matched_text[:200],  # Limit length
                section=section,
                keywords=[best_keyword] if best_keyword else []
            )

        return None

    def match_clause_to_category(
        self,
        clause_text: str,
        candidate_categories: Optional[List[str]] = None
    ) -> Optional[Tuple[str, float]]:
        """Match a specific clause text to the most appropriate category.

        Args:
            clause_text: The clause text to categorize.
            candidate_categories: Optional list of categories to consider.
                If None, all categories are considered.

        Returns:
            Tuple of (category_name, confidence_score) or None if no good match.
        """
        if candidate_categories is None:
            candidate_categories = list(self.keyword_mappings.keys())

        normalized_clause = self._normalize_text(clause_text)
        best_category = None
        best_score = 0.0

        for category in candidate_categories:
            if category not in self.keyword_mappings:
                continue

            keywords = self.keyword_mappings[category]

            # Check how many keywords appear in the clause
            matches = 0
            for keyword in keywords:
                if keyword in normalized_clause:
                    matches += 1

            # Calculate score based on keyword presence
            keyword_score = (matches / len(keywords)) * 100

            # Also use fuzzy matching for category name itself
            category_score = fuzz.partial_ratio(
                category.lower(),
                normalized_clause
            )

            # Weighted combination
            combined_score = (keyword_score * 0.7) + (category_score * 0.3)

            if combined_score > best_score:
                best_score = combined_score
                best_category = category

        if best_score >= self.confidence_threshold:
            return (best_category, best_score)

        return None
