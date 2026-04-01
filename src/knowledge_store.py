"""
Knowledge Store — RAG-based learning system for CR2A.

Manages ~/.cr2a/knowledge/ directory containing markdown knowledge files
that accumulate from user feedback (accepted results and corrections).
Provides TF-IDF retrieval to inject relevant past knowledge into analysis prompts.

Three knowledge types:
  - Patterns: Accepted good analysis results (examples for the model)
  - Corrections: User-fixed results with lessons learned
  - Profiles: Aggregated patterns per contract type
"""

import logging
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Stopwords shared with document_retriever.py
_STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "as", "be", "was", "were",
    "are", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "shall", "should", "may", "might", "can", "could",
    "not", "no", "if", "then", "than", "that", "this", "these", "those",
    "such", "so", "any", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "only", "own", "same", "too", "very",
}


@dataclass
class KnowledgeEntry:
    """A single parsed knowledge markdown file."""
    file_path: Path
    entry_type: str          # "pattern" | "correction" | "profile"
    category: str            # category key (empty for profiles)
    contract_type: str       # "municipal" | "federal" | "private" | ""
    date: str
    source: str
    body: str                # markdown body without frontmatter
    tokens_estimate: int     # approximate token count
    feedback_type: str = ""  # "accepted" | "corrected_wrong" | "corrected_missed" | ""


class KnowledgeStore:
    """
    Manages ~/.cr2a/knowledge/ directory and provides TF-IDF retrieval
    over accumulated knowledge entries.
    """

    KNOWLEDGE_ROOT = Path.home() / ".cr2a" / "knowledge"
    SUBDIRS = ["patterns", "corrections", "profiles"]
    MAX_INJECTION_TOKENS = 1500

    def __init__(self):
        self._entries: List[KnowledgeEntry] = []
        self._tfidf_matrix: Optional[np.ndarray] = None
        self._vocabulary: Dict[str, int] = {}
        self._idf_vector: Optional[np.ndarray] = None
        self._category_index: Dict[str, List[int]] = defaultdict(list)
        self._type_index: Dict[str, List[int]] = defaultdict(list)

    # ---- Initialization ----

    def initialize(self) -> None:
        """Create knowledge directory structure if it does not exist."""
        for subdir in self.SUBDIRS:
            (self.KNOWLEDGE_ROOT / subdir).mkdir(parents=True, exist_ok=True)
        logger.info(f"Knowledge store initialized at {self.KNOWLEDGE_ROOT}")

    def load_and_index(self) -> int:
        """
        Scan all .md files under KNOWLEDGE_ROOT, parse frontmatter + body,
        build TF-IDF index over bodies. Returns count of entries loaded.
        """
        self._entries.clear()
        self._category_index.clear()
        self._type_index.clear()

        for subdir in self.SUBDIRS:
            subdir_path = self.KNOWLEDGE_ROOT / subdir
            if not subdir_path.exists():
                continue
            for md_file in sorted(subdir_path.glob("*.md")):
                entry = self._parse_knowledge_file(md_file)
                if entry:
                    idx = len(self._entries)
                    self._entries.append(entry)
                    if entry.category:
                        self._category_index[entry.category].append(idx)
                    if entry.contract_type:
                        self._type_index[entry.contract_type].append(idx)

        if self._entries:
            self._build_tfidf_index()

        count = len(self._entries)
        logger.info(f"Knowledge store loaded {count} entries "
                    f"({len(self._category_index)} categories, "
                    f"{len(self._type_index)} contract types)")
        return count

    # ---- Parsing ----

    def _parse_knowledge_file(self, path: Path) -> Optional[KnowledgeEntry]:
        """Parse a single knowledge markdown file with YAML-like frontmatter."""
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not read {path}: {e}")
            return None

        # Split on --- delimiters
        parts = re.split(r'^---\s*$', text, maxsplit=2, flags=re.MULTILINE)
        if len(parts) < 3:
            logger.warning(f"No valid frontmatter in {path}")
            return None

        frontmatter_text = parts[1]
        body = parts[2].strip()

        if not body:
            return None

        # Parse key: value pairs from frontmatter
        meta: Dict[str, str] = {}
        for match in re.finditer(r'^(\w+):\s*(.+)$', frontmatter_text, re.MULTILINE):
            key = match.group(1).strip()
            value = match.group(2).strip().strip('"').strip("'")
            meta[key] = value

        entry_type = meta.get("type", "pattern")
        tokens_est = int(meta.get("tokens_estimate", 0))
        if tokens_est == 0:
            tokens_est = int(len(body.split()) * 1.3)

        return KnowledgeEntry(
            file_path=path,
            entry_type=entry_type,
            category=meta.get("category", ""),
            contract_type=meta.get("contract_type", ""),
            date=meta.get("date", ""),
            source=meta.get("source", ""),
            body=body,
            tokens_estimate=tokens_est,
            feedback_type=meta.get("feedback_type", ""),
        )

    # ---- TF-IDF Index ----

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Tokenize text into lowercase words, removing stopwords."""
        words = re.findall(r'[a-z]{2,}', text.lower())
        return [w for w in words if w not in _STOPWORDS]

    def _build_tfidf_index(self) -> None:
        """Build TF-IDF matrix over all knowledge entry bodies."""
        bodies = [e.body for e in self._entries]
        n_docs = len(bodies)
        if n_docs == 0:
            return

        # Build vocabulary
        doc_freq: Dict[str, int] = defaultdict(int)
        tokenized_docs: List[List[str]] = []

        for body in bodies:
            tokens = self._tokenize(body)
            tokenized_docs.append(tokens)
            for t in set(tokens):
                doc_freq[t] += 1

        # Keep terms in at least 1 doc (relaxed — knowledge base may be small)
        # but at most 90% of docs
        max_df = max(int(0.9 * n_docs), 1)
        self._vocabulary = {}
        for word, df in doc_freq.items():
            if df <= max_df:
                self._vocabulary[word] = len(self._vocabulary)

        if not self._vocabulary:
            logger.warning("Knowledge TF-IDF vocabulary is empty")
            return

        vocab_size = len(self._vocabulary)

        # Compute TF-IDF matrix
        self._tfidf_matrix = np.zeros((n_docs, vocab_size), dtype=np.float32)
        self._idf_vector = np.zeros(vocab_size, dtype=np.float32)

        for word, col in self._vocabulary.items():
            self._idf_vector[col] = math.log(n_docs / (1 + doc_freq[word]))

        for di, tokens in enumerate(tokenized_docs):
            if not tokens:
                continue
            tf: Dict[int, int] = defaultdict(int)
            for t in tokens:
                if t in self._vocabulary:
                    tf[self._vocabulary[t]] += 1
            doc_len = len(tokens)
            for col, count in tf.items():
                self._tfidf_matrix[di, col] = (count / doc_len) * self._idf_vector[col]

        # L2-normalize rows
        norms = np.linalg.norm(self._tfidf_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._tfidf_matrix = self._tfidf_matrix / norms

    def _vectorize_query(self, query: str) -> Optional[np.ndarray]:
        """Convert a query string to a TF-IDF vector."""
        if not self._vocabulary or self._idf_vector is None:
            return None

        tokens = self._tokenize(query)
        if not tokens:
            return None

        vec = np.zeros(len(self._vocabulary), dtype=np.float32)
        tf: Dict[int, int] = defaultdict(int)
        for t in tokens:
            if t in self._vocabulary:
                tf[self._vocabulary[t]] += 1
        doc_len = len(tokens)
        for col, count in tf.items():
            vec[col] = (count / doc_len) * self._idf_vector[col]

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    # ---- Retrieval ----

    def retrieve_for_category(
        self,
        cat_key: str,
        contract_type: str = "",
        top_k: int = 5
    ) -> List[KnowledgeEntry]:
        """
        Retrieve the most relevant knowledge entries for a category.

        Strategy:
        1. Exact match on category_index[cat_key]
        2. Boost entries matching contract_type
        3. TF-IDF fallback if fewer than top_k exact matches
        4. Include contract_type profile if it exists
        5. Enforce MAX_INJECTION_TOKENS budget
        """
        if not self._entries:
            return []

        # Score each candidate: (score, index)
        scored: List[Tuple[float, int]] = []

        # Exact category matches get high base score
        exact_indices = set(self._category_index.get(cat_key, []))
        for idx in exact_indices:
            entry = self._entries[idx]
            score = 2.0
            # Corrections ranked higher than patterns; missed clauses even higher
            if entry.entry_type == "correction":
                if entry.feedback_type == "corrected_missed":
                    score += 1.5  # missed clauses are highest priority
                else:
                    score += 1.0
            # Boost matching contract type
            if contract_type and entry.contract_type == contract_type:
                score += 0.5
            # Recency boost: recent corrections are more relevant
            score += self._recency_boost(entry)
            scored.append((score, idx))

        # TF-IDF fallback for cross-category relevance
        if len(scored) < top_k and self._tfidf_matrix is not None:
            # Use category key with underscores replaced as query
            query = cat_key.replace("_", " ")
            qvec = self._vectorize_query(query)
            if qvec is not None:
                similarities = self._tfidf_matrix @ qvec
                for idx in np.argsort(similarities)[::-1]:
                    idx = int(idx)
                    if idx not in exact_indices and similarities[idx] > 0.05:
                        score = float(similarities[idx])
                        if contract_type and self._entries[idx].contract_type == contract_type:
                            score += 0.3
                        scored.append((score, idx))
                        if len(scored) >= top_k * 2:
                            break

        # Always include profile for the contract type
        profile_idx = None
        if contract_type:
            for idx in self._type_index.get(contract_type, []):
                if self._entries[idx].entry_type == "profile":
                    profile_idx = idx
                    break

        # Sort by score descending, deduplicate
        scored.sort(key=lambda x: x[0], reverse=True)
        seen = set()
        results: List[KnowledgeEntry] = []
        total_tokens = 0

        # Add profile first if it exists (costs tokens but always valuable)
        if profile_idx is not None:
            entry = self._entries[profile_idx]
            if entry.tokens_estimate <= self.MAX_INJECTION_TOKENS:
                results.append(entry)
                total_tokens += entry.tokens_estimate
                seen.add(profile_idx)

        for _score, idx in scored:
            if idx in seen:
                continue
            entry = self._entries[idx]
            if total_tokens + entry.tokens_estimate > self.MAX_INJECTION_TOKENS:
                continue
            results.append(entry)
            total_tokens += entry.tokens_estimate
            seen.add(idx)
            if len(results) >= top_k:
                break

        return results

    @staticmethod
    def _recency_boost(entry: KnowledgeEntry) -> float:
        """Boost score for recent entries (last 30 days: +0.3, 30-90: +0.1)."""
        if not entry.date:
            return 0.0
        try:
            entry_date = datetime.strptime(entry.date, "%Y-%m-%d")
            days_ago = (datetime.now() - entry_date).days
            if days_ago <= 30:
                return 0.3
            elif days_ago <= 90:
                return 0.1
        except (ValueError, TypeError):
            pass
        return 0.0

    def format_for_prompt(
        self,
        entries: List[KnowledgeEntry],
        max_tokens: int = 1500
    ) -> str:
        """
        Format retrieved knowledge entries into a concise prompt block.
        Truncates to fit within max_tokens budget.
        """
        if not entries:
            return ""

        lines = []
        total_tokens = 0

        for entry in entries:
            if total_tokens >= max_tokens:
                break

            if entry.entry_type == "profile":
                # Profiles: include as-is but truncated
                body = entry.body
                budget = max_tokens - total_tokens
                words = body.split()
                if len(words) * 1.3 > budget:
                    word_limit = int(budget / 1.3)
                    body = " ".join(words[:word_limit]) + "..."
                prefix = f"Profile ({entry.contract_type})"
                lines.append(f"- {prefix}: {body}")
                total_tokens += int(len(body.split()) * 1.3)

            elif entry.entry_type == "correction":
                # Corrections: extract the lesson (most concise signal)
                lesson_match = re.search(
                    r'##\s*Lesson\s*\n(.+?)(?:\n##|\Z)',
                    entry.body, re.DOTALL
                )
                if lesson_match:
                    lesson = lesson_match.group(1).strip()
                else:
                    # Fall back to the corrected text
                    corrected_match = re.search(
                        r'##\s*Corrected\s*\n(.+?)(?:\n##|\Z)',
                        entry.body, re.DOTALL
                    )
                    lesson = corrected_match.group(1).strip() if corrected_match else entry.body[:200]
                if entry.feedback_type == "corrected_missed":
                    prefix = "MISSED CLAUSE"
                else:
                    prefix = "Correction"
                if entry.contract_type:
                    prefix += f" ({entry.contract_type})"
                lines.append(f"- {prefix}: {lesson}")
                total_tokens += int(len(lesson.split()) * 1.3)

            elif entry.entry_type == "pattern":
                body = entry.body
                budget = max_tokens - total_tokens
                words = body.split()
                if len(words) * 1.3 > budget:
                    word_limit = int(budget / 1.3)
                    body = " ".join(words[:word_limit]) + "..."
                prefix = f"Pattern"
                if entry.contract_type:
                    prefix += f" ({entry.contract_type})"
                lines.append(f"- {prefix}: {body}")
                total_tokens += int(len(body.split()) * 1.3)

        return "\n".join(lines) if lines else ""

    # ---- Save Methods ----

    def save_pattern(
        self,
        cat_key: str,
        contract_type: str,
        summary: str,
        source_file: str
    ) -> Path:
        """Save an accepted analysis result as a pattern knowledge file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{cat_key}_{timestamp}.md"
        path = self.KNOWLEDGE_ROOT / "patterns" / filename

        tokens_est = int(len(summary.split()) * 1.3)
        date_str = datetime.now().strftime("%Y-%m-%d")

        content = (
            f"---\n"
            f"type: pattern\n"
            f"category: {cat_key}\n"
            f"contract_type: {contract_type}\n"
            f"date: {date_str}\n"
            f"source: {source_file}\n"
            f"tokens_estimate: {tokens_est}\n"
            f"---\n\n"
            f"{summary}\n"
        )

        path.write_text(content, encoding="utf-8")
        logger.info(f"Saved pattern: {path.name} ({cat_key}, {contract_type})")

        # Reload index to include new entry
        self.load_and_index()
        return path

    def save_correction(
        self,
        cat_key: str,
        contract_type: str,
        original_summary: str,
        corrected_summary: str,
        lesson: str,
        source_file: str,
        was_missed: bool = False
    ) -> Path:
        """Save a user correction as a correction knowledge file.

        Args:
            was_missed: True if the AI failed to find the clause at all (NOT FOUND),
                        False if the AI found it but got the analysis wrong.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{cat_key}_{timestamp}.md"
        path = self.KNOWLEDGE_ROOT / "corrections" / filename

        feedback_type = "corrected_missed" if was_missed else "corrected_wrong"

        body_parts = [
            f"## Original\n{original_summary}",
            f"\n## Corrected\n{corrected_summary}",
        ]
        if lesson:
            body_parts.append(f"\n## Lesson\n{lesson}")

        body = "\n".join(body_parts)
        tokens_est = int(len(body.split()) * 1.3)
        date_str = datetime.now().strftime("%Y-%m-%d")

        content = (
            f"---\n"
            f"type: correction\n"
            f"feedback_type: {feedback_type}\n"
            f"category: {cat_key}\n"
            f"contract_type: {contract_type}\n"
            f"date: {date_str}\n"
            f"source: {source_file}\n"
            f"tokens_estimate: {tokens_est}\n"
            f"---\n\n"
            f"{body}\n"
        )

        path.write_text(content, encoding="utf-8")
        logger.info(f"Saved correction ({feedback_type}): {path.name} ({cat_key}, {contract_type})")

        # Reload index to include new entry
        self.load_and_index()
        return path

    def update_profile(self, contract_type: str) -> Path:
        """
        Re-aggregate all patterns + corrections for a contract_type
        into a single profile markdown file.
        """
        path = self.KNOWLEDGE_ROOT / "profiles" / f"{contract_type}.md"

        # Gather all entries for this contract type
        relevant = [
            e for e in self._entries
            if e.contract_type == contract_type and e.entry_type in ("pattern", "correction")
        ]

        if not relevant:
            logger.info(f"No entries to aggregate for profile: {contract_type}")
            return path

        # Group by category, track corrections and missed counts
        by_category: Dict[str, List[str]] = defaultdict(list)
        correction_counts: Dict[str, int] = defaultdict(int)
        missed_counts: Dict[str, int] = defaultdict(int)
        for entry in relevant:
            if entry.category:
                # Use first line of body as summary
                first_line = entry.body.split("\n")[0].strip()
                if entry.entry_type == "correction":
                    correction_counts[entry.category] += 1
                    if entry.feedback_type == "corrected_missed":
                        missed_counts[entry.category] += 1
                    # For corrections, use the corrected text
                    corrected_match = re.search(
                        r'##\s*Corrected\s*\n(.+?)(?:\n##|\Z)',
                        entry.body, re.DOTALL
                    )
                    if corrected_match:
                        first_line = corrected_match.group(1).strip().split("\n")[0]
                by_category[entry.category].append(first_line)

        # Build profile body
        lines = []
        for cat_key, summaries in sorted(by_category.items()):
            display_name = cat_key.replace("_", " ").title()
            # Use the most recent summary
            annotation = ""
            if correction_counts[cat_key] >= 3:
                annotation += " [FREQUENTLY CORRECTED]"
            if missed_counts[cat_key] >= 2:
                annotation += " [COMMONLY MISSED]"
            lines.append(f"- {display_name}: {summaries[-1]}{annotation}")

        body = "\n".join(lines)
        date_str = datetime.now().strftime("%Y-%m-%d")

        content = (
            f"---\n"
            f"type: profile\n"
            f"contract_type: {contract_type}\n"
            f"date: {date_str}\n"
            f"entries_aggregated: {len(relevant)}\n"
            f"---\n\n"
            f"{body}\n"
        )

        path.write_text(content, encoding="utf-8")
        logger.info(f"Updated profile: {contract_type} ({len(relevant)} entries)")

        # Reload index
        self.load_and_index()
        return path

    def entry_count(self) -> int:
        """Return total number of loaded knowledge entries."""
        return len(self._entries)

    def get_stats(self, contract_type: str = "") -> str:
        """Return a human-readable summary of knowledge base contents."""
        patterns = sum(1 for e in self._entries if e.entry_type == "pattern")
        corrections = sum(1 for e in self._entries if e.entry_type == "correction")
        missed = sum(1 for e in self._entries
                     if e.entry_type == "correction" and e.feedback_type == "corrected_missed")
        parts = [f"{patterns} patterns", f"{corrections} corrections"]
        if missed:
            parts.append(f"{missed} missed clauses")
        if contract_type:
            ct_count = sum(1 for e in self._entries if e.contract_type == contract_type)
            parts.append(f"{ct_count} for {contract_type}")
        return ", ".join(parts)

    def seed_from_folder(
        self,
        folder_path: str,
        analysis_engine,
        categories: Optional[List[str]] = None,
        progress_callback=None
    ) -> int:
        """
        Bootstrap knowledge base from a folder of contract files.

        Runs analysis on each contract for high-value categories and saves
        results as pattern knowledge files.

        Args:
            folder_path: Path to folder containing contract files
            analysis_engine: AnalysisEngine instance for running analyses
            categories: Optional list of category keys to analyze (defaults to high-value set)
            progress_callback: Optional callback(message, percent)

        Returns:
            Number of patterns saved
        """
        folder = Path(folder_path)
        if not folder.is_dir():
            logger.error(f"Seed folder does not exist: {folder}")
            return 0

        # Default high-value categories
        if categories is None:
            categories = [
                "indemnification_defense_hold_harmless",
                "retainage_progress_payments",
                "insurance_requirements",
                "termination_provisions",
                "change_orders",
                "liquidated_damages",
                "dispute_resolution",
                "warranty_guarantees",
                "scope_of_work",
                "payment_contingencies",
            ]

        # Find contract files
        extensions = {".pdf", ".docx"}
        contract_files = [
            f for f in folder.iterdir()
            if f.suffix.lower() in extensions and not f.name.startswith("~")
        ]

        if not contract_files:
            logger.warning(f"No contract files found in {folder}")
            return 0

        logger.info(f"Seeding from {len(contract_files)} files in {folder}")
        saved_count = 0
        total_files = len(contract_files)

        for fi, contract_file in enumerate(contract_files):
            if progress_callback:
                pct = int(100 * fi / total_files)
                progress_callback(f"Seeding from {contract_file.name}...", pct)

            try:
                prepared = analysis_engine.prepare_contract(
                    str(contract_file), progress_callback=None
                )
                if not prepared:
                    continue

                # Detect contract type from content
                contract_type = self._detect_contract_type(prepared.contract_text)

                for cat_key in categories:
                    result = analysis_engine.analyze_single_category(
                        prepared, cat_key, progress_callback=None
                    )
                    if result and result[2] is not None:
                        _section_key, _display_name, clause_block, _prompt, _raw = result
                        summary = clause_block.get("Clause Summary", "")
                        if summary and summary.upper() != "NOT FOUND":
                            self.save_pattern(
                                cat_key, contract_type, summary, contract_file.name
                            )
                            saved_count += 1

            except Exception as e:
                logger.warning(f"Failed to seed from {contract_file.name}: {e}")
                continue

        if progress_callback:
            progress_callback(f"Seeding complete: {saved_count} patterns saved", 100)

        logger.info(f"Seeding complete: {saved_count} patterns from {total_files} files")
        return saved_count

    @staticmethod
    def _detect_contract_type(contract_text: str) -> str:
        """Detect contract type from content heuristics."""
        sample = contract_text[:3000].lower()

        federal_signals = ["far ", "dfars", "federal acquisition", "contracting officer",
                          "u.s. government", "united states government"]
        municipal_signals = ["city of", "county of", "town of", "village of",
                           "municipality", "public works department", "board of education",
                           "school district"]
        state_signals = ["state of", "state department", "state highway",
                        "department of transportation"]

        federal_hits = sum(1 for s in federal_signals if s in sample)
        municipal_hits = sum(1 for s in municipal_signals if s in sample)
        state_hits = sum(1 for s in state_signals if s in sample)

        if federal_hits >= 2:
            return "federal"
        if municipal_hits >= 1:
            return "municipal"
        if state_hits >= 2:
            return "state"
        return "private"
