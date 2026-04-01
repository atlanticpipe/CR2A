"""
Tri-layer document retrieval engine for contract analysis.

Three independent retrieval layers work together to find the most relevant
contract sections for any query (category analysis or free-form chat):

  Layer 1 — Regex Map:    TEMPLATE_PATTERNS matches → section IDs
  Layer 2 — Keyword Index: inverted index of category keywords → section IDs
  Layer 3 — TF-IDF:       cosine similarity between query and section vectors

Results are fused via Reciprocal Rank Fusion (RRF) and the top sections'
actual text is returned for the AI to read.
"""

import bisect
import logging
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

from analyzer.template_patterns import (
    CATEGORY_SEARCH_DESCRIPTIONS,
    CATEGORY_SECTION_HINTS,
    SectionBlock,
    TEMPLATE_PATTERNS,
    _score_match_by_section,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# English stopwords (common words to exclude from TF-IDF)
# ---------------------------------------------------------------------------
_STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "as", "be", "was", "were",
    "are", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "shall", "should", "may", "might", "can", "could",
    "not", "no", "if", "then", "than", "that", "this", "these", "those",
    "which", "who", "whom", "what", "when", "where", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "only",
    "own", "same", "so", "very", "just", "because", "about", "into", "through",
    "during", "before", "after", "above", "below", "between", "under", "again",
    "further", "once", "here", "there", "any", "its", "also", "up", "out",
    "off", "over", "per", "nor", "too", "our", "your", "their", "his", "her",
    "he", "she", "they", "we", "you", "me", "him", "us", "them", "my",
    "section", "article", "part", "page", "end",  # contract boilerplate
}

# ---------------------------------------------------------------------------
# Category keyword lists (snake_case keys matching TEMPLATE_PATTERNS)
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    # Administrative & Commercial
    "contract_term_renewal_extensions": [
        "contract term", "term of contract", "duration", "renewal", "extension",
        "expiration", "commence", "effective date", "termination date",
        "substantial completion", "final completion", "calendar days",
    ],
    "bonding_surety_insurance": [
        "bond", "bonding", "surety", "insurance", "performance bond", "payment bond",
        "bid bond", "surety company", "bond amount", "faithful performance",
        "bonds and insurance",
    ],
    "retainage_progress_payments": [
        "retainage", "retention", "holdback", "progress payment",
        "payment application", "milestone payment", "periodic payment",
        "final payment", "pay application",
    ],
    "pay_when_paid_if_paid": [
        "pay when paid", "pay if paid", "payment contingent", "conditioned upon",
        "receipt of payment", "owner payment", "payment condition",
    ],
    "price_escalation": [
        "price escalation", "cost adjustment", "inflation", "escalation clause",
        "price adjustment", "labor escalation", "material escalation",
        "fuel price", "fuel adjustment", "fuel surcharge", "fuel cost",
        "fuel escalation", "diesel",
        "adjustments to price", "producer price index", "ppi",
    ],
    "change_orders": [
        "change order", "change orders", "scope change", "field order",
        "change directive", "construction change", "work change", "extra work",
        "changes in the work", "modification of contract",
    ],
    "termination_for_convenience": [
        "termination for convenience", "terminate without cause",
        "owner may terminate", "right to terminate", "convenience termination",
        "termination", "terminate",
    ],
    "termination_for_cause": [
        "termination for cause", "termination for default", "default",
        "material breach", "failure to perform", "cure period", "right to cure",
        "termination", "terminate",
    ],
    "bid_protest": [
        "bid protest", "protest of award", "improper award", "challenge bid",
        "procurement protest", "contested award", "bid challenge",
    ],
    "bid_tabulation": [
        "bid tabulation", "bid opening", "bid evaluation", "lowest bidder",
        "responsive bid", "responsible bidder", "award criteria",
    ],
    "contractor_qualification": [
        "qualification", "licensing", "certification", "prequalification",
        "experience requirement", "contractor license", "qualified contractor",
    ],
    "release_orders": [
        "release order", "task order", "work authorization",
        "indefinite quantity", "delivery order", "indefinite delivery",
    ],
    "assignment_novation": [
        "assignment of contract", "novation", "transfer of contract", "assign rights",
        "consent to assign", "assignment restriction", "contract assignment",
    ],
    "audit_rights": [
        "audit", "audit rights", "inspection of records", "books and records",
        "recordkeeping", "document retention", "right to inspect",
    ],
    "notice_requirements": [
        "notice", "written notice", "notification", "notice to cure",
        "delay notice", "claim notice", "days notice", "notify in writing",
    ],
    # Technical & Performance
    "scope_of_work": [
        "scope of work", "work includes", "work exclusions", "deliverables",
        "summary of work", "description of work", "contract scope",
    ],
    "performance_schedule": [
        "performance schedule", "construction schedule", "critical path",
        "cpm schedule", "progress schedule", "time for completion",
        "schedule of work", "baseline schedule",
    ],
    "delays": [
        "delay", "delays", "force majeure", "acts of god", "weather delay",
        "excusable delay", "time extension", "unforeseen conditions",
        "compensable delay", "extension of time",
    ],
    "suspension_of_work": [
        "suspension", "suspend work", "stop work", "work stoppage",
        "suspension of work", "resumption", "standby",
        "delay performance", "stopped or delayed", "stoppage or delay",
        "right to delay", "stop the work",
    ],
    "submittals": [
        "submittal", "shop drawing", "product data", "sample",
        "submittal schedule", "review", "approval", "resubmittal",
    ],
    "emergency_work": [
        "emergency work", "emergency response", "urgent repair",
        "emergency service", "immediate action",
    ],
    "permits_licensing": [
        "permit", "license", "regulatory approval", "building permit",
        "permit fee", "inspection", "code compliance",
    ],
    "warranty": [
        "warranty", "guarantee", "defects liability", "correction of work",
        "warranty period", "workmanship", "materials warranty",
    ],
    "use_of_aps_tools": [
        "tools", "equipment", "materials", "supplies", "owner-furnished",
        "specified product", "proprietary", "sole source",
    ],
    "owner_supplied_support": [
        "owner furnished", "owner provided", "owner supplied", "site access",
        "utilities", "owner support", "furnished by owner",
    ],
    "field_ticket": [
        "field ticket", "daily log", "work log", "time and material",
        "force account", "daily report", "field report",
    ],
    "mobilization_demobilization": [
        "mobilization", "demobilization", "site setup", "site establishment",
        "mobilization payment", "move-in", "move-out",
    ],
    "utility_coordination": [
        "utility", "utility coordination", "utility locate", "utility conflict",
        "utility relocation", "underground utility", "one-call",
    ],
    "delivery_deadlines": [
        "delivery deadline", "milestone date", "substantial completion",
        "final completion", "completion date", "completion standard",
    ],
    "punch_list": [
        "punch list", "punchlist", "closeout", "final inspection",
        "acceptance of work", "certificate of completion", "final walkthrough",
    ],
    "worksite_coordination": [
        "worksite coordination", "access restriction", "sequencing",
        "interface", "coordination meeting", "other contractors",
    ],
    "deliverables": [
        "deliverable", "digital submission", "as-built", "documentation",
        "record drawing", "operation manual", "maintenance manual",
    ],
    "emergency_contingency": [
        "emergency contingency", "contingency plan", "emergency response",
        "disaster recovery", "contingency work",
    ],
    # Legal Risk & Enforcement
    "indemnification": [
        "indemnif", "hold harmless", "defend and indemnify", "save harmless",
        "indemnity", "indemnitor", "indemnitee",
    ],
    "duty_to_defend": [
        "duty to defend", "defense obligation", "legal defense",
        "defense cost", "obligation to defend",
    ],
    "limitation_of_liability": [
        "limitation of liability", "liability cap", "damage cap",
        "consequential damages", "waiver of damages", "maximum liability",
    ],
    "insurance_coverage": [
        "insurance", "additional insured", "waiver of subrogation",
        "policy limits", "certificate of insurance", "commercial general liability",
    ],
    "dispute_resolution": [
        "dispute resolution", "arbitration", "mediation", "litigation",
        "claims process", "dispute", "controversy",
    ],
    "flow_down_clauses": [
        "flow down", "flow-down", "flow down clause",
        "pass-through clause", "prime contract terms", "incorporate by reference",
        "subcontract shall include", "binding on subcontractor",
    ],
    "subcontracting": [
        "subcontract", "subcontractor", "subcontractor approval",
        "substitution", "subletting", "consent to subcontract",
    ],
    "background_screening": [
        "background check", "background screening", "security clearance",
        "criminal history", "worker eligibility", "fingerprint",
    ],
    "safety_osha": [
        "safety", "osha", "safety plan", "safety program", "accident prevention",
        "health and safety", "safety officer", "safety meeting",
    ],
    "site_conditions": [
        "site condition", "differing site condition", "subsurface",
        "changed condition", "concealed condition", "unforeseen condition",
        "access to work site", "site access", "free access",
        "work site", "work area", "other contractors",
    ],
    "environmental": [
        "environmental", "hazardous material", "waste disposal", "asbestos",
        "contamination", "pollution", "environmental compliance",
    ],
    "order_of_precedence": [
        "order of precedence", "conflicting documents", "document hierarchy",
        "interpretation", "conflict between", "priority of documents",
    ],
    "setoff_withholding": [
        "setoff", "set-off", "withhold", "withholding", "offset",
        "deduct from payment", "right to withhold",
    ],
    # Regulatory & Compliance
    "certified_payroll": [
        "certified payroll", "payroll record", "payroll report",
        "wage record", "payroll certification",
    ],
    "prevailing_wage": [
        "prevailing wage", "davis-bacon", "wage rate", "wage determination",
        "labor standards", "minimum wage", "wage compliance",
    ],
    "eeo": [
        "equal opportunity", "eeo", "non-discrimination", "affirmative action",
        "title vi", "civil rights", "nondiscrimination",
        "anti-discrimination", "discriminate", "discrimination",
    ],
    "mwbe_dbe": [
        "minority business", "dbe", "mbe", "wbe", "disadvantaged business",
        "small business", "participation goal", "utilization plan",
    ],
    "anti_lobbying": [
        "anti-lobbying", "lobbying", "cone of silence", "no contact",
        "lobbying restriction", "ex parte",
    ],
    "apprenticeship": [
        "apprentice", "apprenticeship", "training program",
        "workforce development", "on-the-job training",
    ],
    "e_verify": [
        "e-verify", "immigration", "i-9", "employment eligibility",
        "work authorization", "immigration compliance",
    ],
    "worker_classification": [
        "worker classification", "independent contractor", "employee",
        "misclassification", "employment status",
    ],
    "drug_free_workplace": [
        "drug-free", "drug free", "substance abuse", "drug testing",
        "alcohol testing", "substance testing", "drug policy",
    ],
    # Data, Technology & Deliverables
    "data_ownership": [
        "data ownership", "data rights", "digital deliverable",
        "intellectual property", "data access", "data transfer",
    ],
    "ai_technology_use": [
        "artificial intelligence", "ai", "automation", "digital tool",
        "technology restriction", "proprietary system",
    ],
    "digital_surveillance": [
        "surveillance", "monitoring", "gis-tagged", "gps tracking",
        "digital monitoring", "camera", "cctv",
    ],
    "gis_digital_workflow": [
        "gis", "digital workflow", "electronic submittal", "bim",
        "cad", "digital integration",
    ],
    "digital_deliverables": [
        "digital deliverable", "electronic submittal", "bim", "cad",
        "digital submission", "electronic format", "digital document",
    ],
    "document_retention": [
        "document retention", "records retention", "record keeping",
        "retention period", "preserve records", "data security",
    ],
    "confidentiality": [
        "confidential", "confidentiality", "non-disclosure", "nda",
        "proprietary information", "trade secret",
    ],
    "cybersecurity": [
        "cybersecurity", "data security", "breach notification",
        "data protection", "encryption", "information security",
    ],
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class IndexedContract:
    """Pre-computed search indexes over a parsed contract."""
    contract_text: str
    sections: List[SectionBlock]
    section_texts: List[str]
    section_headers: List[str]          # short header from parser (e.g. "1.2 bo")
    enriched_headers: List[str]         # full first-line header (e.g. "1.2 bonds and insurance")
    # Layer 1: regex map — cat_key → [(section_idx, score)]
    regex_map: Dict[str, List[Tuple[int, float]]] = field(default_factory=dict)
    # Layer 2: keyword inverted index — lowercase word/phrase → {section_idxs}
    keyword_index: Dict[str, Set[int]] = field(default_factory=dict)
    # Layer 3: TF-IDF
    tfidf_matrix: Optional[np.ndarray] = None   # (n_sections, vocab_size)
    vocabulary: Dict[str, int] = field(default_factory=dict)
    idf_vector: Optional[np.ndarray] = None


@dataclass
class RetrievalResult:
    """A single retrieved section with relevance metadata."""
    section_idx: int
    section_header: str
    section_text: str
    combined_score: float
    found_by: List[str]   # e.g. ['regex', 'keyword', 'tfidf']


# ---------------------------------------------------------------------------
# DocumentRetriever
# ---------------------------------------------------------------------------

class DocumentRetriever:
    """Tri-layer retrieval engine: regex + keyword + TF-IDF."""

    RRF_K = 60  # Reciprocal Rank Fusion constant

    def __init__(self):
        self._indexed: Optional[IndexedContract] = None

    @property
    def indexed(self) -> Optional[IndexedContract]:
        return self._indexed

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def index_contract(
        self,
        contract_text: str,
        section_index: List[SectionBlock],
        extracted_clauses: Dict[str, list],
    ) -> IndexedContract:
        """Build all three search indexes. Called once at contract load."""
        logger.info("Building retrieval index over %d sections...", len(section_index))

        # Extract actual section texts and enriched headers
        section_texts = []
        section_headers = []
        enriched_headers = []
        for sec in section_index:
            text = contract_text[sec.start_pos:sec.end_pos]
            section_texts.append(text)
            section_headers.append(sec.header_normalized)
            # Enrich header: extract full first line from section text
            # (the parser truncates subarticle headers to ~5 chars)
            first_line = text.strip().split('\n')[0].strip()[:120].lower()
            enriched_headers.append(first_line if first_line else sec.header_normalized)

        idx = IndexedContract(
            contract_text=contract_text,
            sections=section_index,
            section_texts=section_texts,
            section_headers=section_headers,
            enriched_headers=enriched_headers,
        )

        # Layer 1: regex map
        idx.regex_map = self._build_regex_map(extracted_clauses, section_index)
        logger.info("Layer 1 (regex): mapped %d categories to sections", len(idx.regex_map))

        # Layer 2: keyword inverted index
        idx.keyword_index = self._build_keyword_index(section_texts)
        logger.info("Layer 2 (keyword): indexed %d unique terms", len(idx.keyword_index))

        # Layer 3: TF-IDF
        idx.tfidf_matrix, idx.vocabulary, idx.idf_vector = self._build_tfidf(section_texts)
        logger.info("Layer 3 (TF-IDF): matrix %s, vocab %d",
                     idx.tfidf_matrix.shape if idx.tfidf_matrix is not None else "None",
                     len(idx.vocabulary))

        self._indexed = idx
        return idx

    # ---- Layer 1: Regex Map ----

    @staticmethod
    def _build_regex_map(
        extracted_clauses: Dict[str, list],
        section_index: List[SectionBlock],
    ) -> Dict[str, List[Tuple[int, float]]]:
        """Map each regex match position to its containing section."""
        if not section_index:
            return {}

        starts = [s.start_pos for s in section_index]
        regex_map: Dict[str, List[Tuple[int, float]]] = {}

        for cat_key, matches in extracted_clauses.items():
            seen_sections: Dict[int, float] = {}  # section_idx → best score
            for m in matches:
                pos = m.get("position", 0)
                # bisect to find containing section
                si = bisect.bisect_right(starts, pos) - 1
                si = max(0, min(si, len(section_index) - 1))
                score = m.get("section_score", 0.5)
                if si not in seen_sections or score > seen_sections[si]:
                    seen_sections[si] = score
            # Sort by score descending
            regex_map[cat_key] = sorted(
                seen_sections.items(), key=lambda x: -x[1]
            )

        return regex_map

    # ---- Layer 2: Keyword Inverted Index ----

    @staticmethod
    def _build_keyword_index(section_texts: List[str]) -> Dict[str, Set[int]]:
        """Build inverted index: lowercased word/phrase → {section indices}."""
        index: Dict[str, Set[int]] = defaultdict(set)
        for si, text in enumerate(section_texts):
            text_lower = text.lower()
            # Index individual words
            words = re.findall(r'[a-z]{2,}', text_lower)
            for w in words:
                if w not in _STOPWORDS:
                    index[w].add(si)
            # Index 2-word and 3-word phrases for multi-word keyword matching
            word_list = [w for w in words if w not in _STOPWORDS]
            for i in range(len(word_list) - 1):
                bigram = f"{word_list[i]} {word_list[i+1]}"
                index[bigram].add(si)
            for i in range(len(word_list) - 2):
                trigram = f"{word_list[i]} {word_list[i+1]} {word_list[i+2]}"
                index[trigram].add(si)
        return dict(index)

    # ---- Layer 3: TF-IDF ----

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Tokenize text into lowercase words, removing stopwords."""
        words = re.findall(r'[a-z]{2,}', text.lower())
        return [w for w in words if w not in _STOPWORDS]

    def _build_tfidf(
        self, section_texts: List[str]
    ) -> Tuple[Optional[np.ndarray], Dict[str, int], Optional[np.ndarray]]:
        """Build TF-IDF matrix over section texts using pure numpy."""
        if not section_texts:
            return None, {}, None

        n_sections = len(section_texts)

        # Build vocabulary from all sections
        doc_freq: Dict[str, int] = defaultdict(int)  # word → num sections containing it
        tokenized_docs: List[List[str]] = []

        for text in section_texts:
            tokens = self._tokenize(text)
            tokenized_docs.append(tokens)
            unique_tokens = set(tokens)
            for t in unique_tokens:
                doc_freq[t] += 1

        # Filter: keep terms appearing in at least 2 sections and at most 80% of sections
        max_df = int(0.8 * n_sections)
        vocabulary: Dict[str, int] = {}
        for word, df in doc_freq.items():
            if 2 <= df <= max_df:
                vocabulary[word] = len(vocabulary)

        if not vocabulary:
            logger.warning("TF-IDF vocabulary is empty after filtering")
            return None, {}, None

        vocab_size = len(vocabulary)

        # Compute TF-IDF matrix
        tfidf = np.zeros((n_sections, vocab_size), dtype=np.float32)
        idf = np.zeros(vocab_size, dtype=np.float32)

        # IDF: log(N / (1 + df))
        for word, col in vocabulary.items():
            idf[col] = math.log(n_sections / (1 + doc_freq[word]))

        # TF (normalized) × IDF
        for si, tokens in enumerate(tokenized_docs):
            if not tokens:
                continue
            tf = defaultdict(int)
            for t in tokens:
                if t in vocabulary:
                    tf[vocabulary[t]] += 1
            doc_len = len(tokens)
            for col, count in tf.items():
                tfidf[si, col] = (count / doc_len) * idf[col]

        # L2-normalize rows for cosine similarity
        norms = np.linalg.norm(tfidf, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        tfidf = tfidf / norms

        return tfidf, vocabulary, idf

    def _vectorize_query(self, query: str) -> Optional[np.ndarray]:
        """Convert a query string to a TF-IDF vector using the indexed vocabulary."""
        if self._indexed is None or not self._indexed.vocabulary:
            return None

        tokens = self._tokenize(query)
        if not tokens:
            return None

        vocab = self._indexed.vocabulary
        idf = self._indexed.idf_vector
        vec = np.zeros(len(vocab), dtype=np.float32)

        tf = defaultdict(int)
        for t in tokens:
            if t in vocab:
                tf[vocab[t]] += 1

        if not tf:
            return None

        doc_len = len(tokens)
        for col, count in tf.items():
            vec[col] = (count / doc_len) * idf[col]

        # L2-normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def _retrieve_layer0_header(self, cat_key: str) -> List[Tuple[int, float]]:
        """Layer 0 (highest priority): Match enriched section headers against category keywords.

        Uses the full first-line header extracted from each section's text
        (e.g. "1.2 bonds and insurance") rather than the truncated parser
        header (e.g. "1.2 bo").  Matching keywords against headers is far
        more reliable than body text because headers don't contain incidental
        mentions (e.g. "bond" in brickwork instructions).
        """
        if self._indexed is None:
            return []

        keywords = CATEGORY_KEYWORDS.get(cat_key, [])
        # Also include CATEGORY_SECTION_HINTS keywords for broader coverage
        hints = CATEGORY_SECTION_HINTS.get(cat_key, [])
        if not keywords and not hints:
            return []

        results: List[Tuple[int, float]] = []

        for si, header in enumerate(self._indexed.enriched_headers):
            if len(header) < 3:
                continue

            score = 0.0
            header_words_raw = set(re.findall(r'[a-z]+', header))
            # Build expanded set with singular forms (strip trailing 's')
            # so "bond" matches "bonds", "limitation" matches "limitations", etc.
            header_words = set(header_words_raw)
            for w in header_words_raw:
                if w.endswith('s') and len(w) > 3:
                    header_words.add(w[:-1])  # "bonds" → "bond"

            # Multi-word keyword phrase found in header (strongest signal)
            for kw in keywords:
                kw_lower = kw.lower()
                kw_words = kw_lower.split()
                if len(kw_words) >= 2:
                    # Exact phrase in header text (handles plurals via regex)
                    if re.search(re.escape(kw_lower).replace(r'\ ', r'\s+') + r's?\b', header):
                        score += 5.0
                    elif all(w in header_words for w in kw_words):
                        score += 3.0

            # Single-word keyword found as a whole word in header
            for kw in keywords:
                kw_lower = kw.lower()
                if len(kw_lower.split()) == 1 and kw_lower in header_words:
                    score += 1.5

            # Section hint keywords (e.g. section numbers like "00610")
            for hint_kw in hints:
                hint_lower = hint_kw.lower()
                # Section numbers (digits or short codes): substring match
                if hint_lower.isdigit() or len(hint_lower) <= 5:
                    if hint_lower in header:
                        score += 2.0
                else:
                    # Multi-word hint phrases: strong signal when found in header
                    hint_words = hint_lower.split()
                    if len(hint_words) >= 2:
                        if hint_lower in header:
                            score += 3.0  # Exact phrase match
                        elif all(w in header_words for w in hint_words):
                            score += 2.0  # All words present
                    else:
                        # Single-word textual hint: weak signal, easily
                        # causes false positives (e.g. "limitation" matching
                        # "highway limitations").  Score low.
                        if hint_lower in header_words:
                            score += 0.5

            # Require a minimum score to avoid noise from single weak matches
            # (e.g. one generic hint word matching an unrelated header)
            if score >= 1.5:
                results.append((si, score))

        results.sort(key=lambda x: -x[1])
        return results[:20]

    def _retrieve_layer1_regex(self, cat_key: str) -> List[Tuple[int, float]]:
        """Layer 1: return sections where regex patterns matched for this category."""
        if self._indexed is None:
            return []
        return self._indexed.regex_map.get(cat_key, [])

    def _retrieve_layer2_keyword(
        self, keywords: List[str], top_k: int = 20
    ) -> List[Tuple[int, float]]:
        """Layer 2: search keyword index for matching sections.

        Multi-word phrase matches score much higher than single-word matches.
        Individual-word fallback from multi-word keywords is heavily penalized
        to prevent noise (e.g. "bond" matching brickwork sections).
        """
        if self._indexed is None or not keywords:
            return []

        section_scores: Dict[int, float] = defaultdict(float)
        phrase_hits = 0  # Track how many multi-word phrases matched

        for kw in keywords:
            kw_lower = kw.lower().strip()
            kw_words = kw_lower.split()

            if len(kw_words) >= 2:
                # Multi-word keyword: try exact phrase match (high value)
                if kw_lower in self._indexed.keyword_index:
                    phrase_hits += 1
                    for si in self._indexed.keyword_index[kw_lower]:
                        section_scores[si] += 5.0
                # Do NOT fall back to individual words here — that causes
                # massive noise (e.g. "bond" from "performance bond" matching
                # brickwork sections).  Individual words are handled below
                # only for explicitly single-word keywords.
            else:
                # Single-word keyword: exact match only
                if kw_lower in self._indexed.keyword_index:
                    for si in self._indexed.keyword_index[kw_lower]:
                        section_scores[si] += 1.0

        # If no phrase matches and very few single-word matches, do a cautious
        # individual-word expansion — but ONLY for words >= 6 chars to avoid
        # generic noise from short words like "order", "work", "bond", "notice"
        if phrase_hits == 0 and len(section_scores) < 3:
            for kw in keywords:
                kw_words = kw.lower().strip().split()
                if len(kw_words) >= 2:
                    for w in kw_words:
                        if len(w) >= 6 and w not in _STOPWORDS and w in self._indexed.keyword_index:
                            for si in self._indexed.keyword_index[w]:
                                section_scores[si] += 0.2

        if not section_scores:
            return []

        # Normalize scores to 0-1 range
        max_score = max(section_scores.values())
        results = [(si, score / max_score) for si, score in section_scores.items()]
        results.sort(key=lambda x: -x[1])
        return results[:top_k]

    def _retrieve_layer3_tfidf(
        self, query_text: str, top_k: int = 20
    ) -> List[Tuple[int, float]]:
        """Layer 3: TF-IDF cosine similarity search."""
        if self._indexed is None or self._indexed.tfidf_matrix is None:
            return []

        query_vec = self._vectorize_query(query_text)
        if query_vec is None:
            return []

        # Cosine similarity (vectors are already L2-normalized)
        similarities = self._indexed.tfidf_matrix @ query_vec

        # Get top-k (only positive similarities)
        top_indices = np.argsort(similarities)[::-1][:top_k]
        results = []
        for si in top_indices:
            score = float(similarities[si])
            if score > 0:
                results.append((si, score))

        return results

    def _fuse_rrf(
        self,
        *ranked_lists: List[Tuple[int, float]],
        layer_names: List[str],
        layer_weights: Optional[List[float]] = None,
        top_k: int = 5,
    ) -> List[RetrievalResult]:
        """Reciprocal Rank Fusion across multiple ranked lists.

        Each layer can have a weight multiplier (default 1.0).  Higher weight
        means that layer's rankings contribute more to the fused score.
        """
        if self._indexed is None:
            return []

        if layer_weights is None:
            layer_weights = [1.0] * len(ranked_lists)

        section_rrf: Dict[int, float] = defaultdict(float)
        section_layers: Dict[int, List[str]] = defaultdict(list)

        for layer_idx, ranked in enumerate(ranked_lists):
            layer_name = layer_names[layer_idx] if layer_idx < len(layer_names) else f"layer{layer_idx}"
            weight = layer_weights[layer_idx] if layer_idx < len(layer_weights) else 1.0
            for rank, (si, _score) in enumerate(ranked):
                section_rrf[si] += weight / (self.RRF_K + rank + 1)
                if layer_name not in section_layers[si]:
                    section_layers[si].append(layer_name)

        # Sort by RRF score descending
        sorted_sections = sorted(section_rrf.items(), key=lambda x: -x[1])[:top_k]

        results = []
        for si, score in sorted_sections:
            results.append(RetrievalResult(
                section_idx=si,
                section_header=self._indexed.section_headers[si],
                section_text=self._indexed.section_texts[si],
                combined_score=score,
                found_by=section_layers[si],
            ))

        return results

    def retrieve_for_category(
        self, cat_key: str, top_k: int = 5
    ) -> List[RetrievalResult]:
        """Retrieve the most relevant sections for a template category."""
        if self._indexed is None:
            return []

        # Layer 0: Header matching (highest priority — 3x weight)
        l0 = self._retrieve_layer0_header(cat_key)

        # Layer 1: Regex map
        l1 = self._retrieve_layer1_regex(cat_key)

        # Layer 2: Keyword search
        keywords = CATEGORY_KEYWORDS.get(cat_key, [])
        l2 = self._retrieve_layer2_keyword(keywords)

        # Layer 3: TF-IDF similarity using category description
        description = CATEGORY_SEARCH_DESCRIPTIONS.get(cat_key, "")
        query_text = f"{description} {' '.join(keywords)}"
        l3 = self._retrieve_layer3_tfidf(query_text)

        # Fuse results — header layer gets 3x weight to prioritize sections
        # whose headers directly name the topic over body-text keyword noise
        results = self._fuse_rrf(
            l0, l1, l2, l3,
            layer_names=["header", "regex", "keyword", "tfidf"],
            layer_weights=[3.0, 1.0, 1.0, 1.0],
            top_k=top_k,
        )

        logger.debug(
            "retrieve_for_category(%s): %d results "
            "[header=%d, regex=%d, keyword=%d, tfidf=%d]",
            cat_key, len(results), len(l0), len(l1), len(l2), len(l3),
        )

        return results

    def retrieve_for_query(
        self, query: str, top_k: int = 5
    ) -> List[RetrievalResult]:
        """Retrieve sections relevant to a free-form question (chat)."""
        if self._indexed is None:
            return []

        query_lower = query.lower()

        # Layer 0: Header matching — search enriched headers for query words
        query_words_set = set(re.findall(r'[a-z]{2,}', query_lower)) - _STOPWORDS
        l0: List[Tuple[int, float]] = []
        for si, header in enumerate(self._indexed.enriched_headers):
            header_words = set(re.findall(r'[a-z]+', header))
            overlap = query_words_set & header_words
            if overlap:
                l0.append((si, float(len(overlap))))
        l0.sort(key=lambda x: -x[1])
        l0 = l0[:20]

        # Layer 1: Check if any regex patterns match the query terms in sections
        l1_all: Dict[int, float] = {}
        for cat_key, sec_list in self._indexed.regex_map.items():
            keywords = CATEGORY_KEYWORDS.get(cat_key, [])
            if any(kw.lower() in query_lower for kw in keywords):
                for si, score in sec_list:
                    if si not in l1_all or score > l1_all[si]:
                        l1_all[si] = score
        l1 = sorted(l1_all.items(), key=lambda x: -x[1])[:20]

        # Layer 2: Tokenize query, search keyword index
        query_words = list(query_words_set)
        l2 = self._retrieve_layer2_keyword(query_words)

        # Layer 3: TF-IDF
        l3 = self._retrieve_layer3_tfidf(query)

        results = self._fuse_rrf(
            l0, l1, l2, l3,
            layer_names=["header", "regex", "keyword", "tfidf"],
            layer_weights=[2.0, 1.0, 1.0, 1.0],
            top_k=top_k,
        )

        logger.debug(
            "retrieve_for_query('%s'): %d results "
            "[header=%d, regex=%d, keyword=%d, tfidf=%d]",
            query[:50], len(results), len(l0), len(l1), len(l2), len(l3),
        )

        return results

    # ------------------------------------------------------------------
    # Formatting for AI
    # ------------------------------------------------------------------

    def format_sections_for_ai(
        self, results: List[RetrievalResult], max_chars: int = 10000
    ) -> str:
        """Format retrieved sections into a prompt-ready string.

        Fits within the AI context window budget. Large sections are
        truncated at sentence boundaries.
        """
        if not results:
            return "(No relevant sections found.)"

        parts = []
        chars_used = 0
        per_section_budget = max_chars // max(len(results), 1)

        for r in results:
            header = r.section_header.upper() if r.section_header else f"Section {r.section_idx}"
            text = r.section_text.strip()

            # Truncate at sentence boundary if too long
            if len(text) > per_section_budget:
                text = self._truncate_at_sentence(text, per_section_budget)

            block = f"--- {header} ---\n{text}"

            if chars_used + len(block) > max_chars:
                remaining = max_chars - chars_used
                if remaining > 200:
                    block = block[:remaining - 3] + "..."
                else:
                    break

            parts.append(block)
            chars_used += len(block)

        return "\n\n".join(parts)

    @staticmethod
    def _truncate_at_sentence(text: str, max_chars: int) -> str:
        """Truncate text at the last sentence boundary before max_chars."""
        if len(text) <= max_chars:
            return text
        truncated = text[:max_chars]
        # Find last sentence-ending punctuation
        for end in ['. ', '.\n', ';\n', '\n\n']:
            pos = truncated.rfind(end)
            if pos > max_chars // 2:  # Keep at least half the budget
                return truncated[:pos + 1].rstrip()
        return truncated.rstrip() + "..."
