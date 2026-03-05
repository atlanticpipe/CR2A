"""
Hybrid Analysis Engine

Combines programmatic extraction (regex) with AI enhancement.

Architecture:
1. Regex finds ALL clauses systematically
2. AI verifies and enhances each clause (summary, risks, redlines)
3. Results are aggregated into comprehensive analysis

This is more efficient and accurate than pure AI analysis.
"""

import logging
import json
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

from analyzer.template_patterns import (
    extract_all_template_clauses,
    TEMPLATE_PATTERNS,
    CATEGORY_SEARCH_DESCRIPTIONS,
)
from src.fuzzy_matcher import FuzzyClauseMatcher

logger = logging.getLogger(__name__)

# Maximum number of clause blocks sent in a single AI API call.
# Smaller batches produce shorter prompts that the local 3B model handles more
# reliably (valid JSON output). 4 keeps prompts well within the 8K context window.
MAX_CLAUSES_PER_BATCH = 4

# Known generic placeholder strings that indicate the AI produced boilerplate
# rather than contract-specific analysis. Filtered out post-parse.
GENERIC_PLACEHOLDERS = frozenset({
    "specific risk condition 1",
    "specific risk condition 2",
    "specific risk condition 3",
    "obligation to pass to subcontractors",
    "problematic term or clause",
    "specific obligation",
    "specific harmful term",
    "risk condition",
})


@dataclass
class EnhancedClause:
    """A clause enhanced by AI analysis."""
    category: str
    clause_location: str
    clause_summary: str
    redline_recommendations: List[Dict]
    harmful_language_policy_conflicts: List[str]
    confidence: str  # 'high', 'medium', 'low'
    extraction_method: str  # 'regex' or 'ai_discovery'


class HybridAnalysisEngine:
    """
    Hybrid analysis combining programmatic extraction + AI enhancement.
    """

    def __init__(self, ai_client, use_fuzzy_matching: bool = True):
        """
        Initialize hybrid engine.

        Args:
            ai_client: AI client for AI enhancement
            use_fuzzy_matching: If True, use fuzzy logic to catch clauses missed by regex
        """
        self.ai_client = ai_client
        self.use_fuzzy_matching = use_fuzzy_matching
        self.fuzzy_matcher = FuzzyClauseMatcher(confidence_threshold=65.0) if use_fuzzy_matching else None
        logger.info(f"HybridAnalysisEngine initialized (fuzzy_matching={use_fuzzy_matching})")

    def analyze_contract_hybrid(
        self,
        contract_text: str,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Dict:
        """
        Analyze contract using hybrid approach:
        1. Programmatic extraction (regex) finds clauses
        2. AI verifies and enhances each clause
        3. Results aggregated

        Args:
            contract_text: Full contract text
            progress_callback: Progress callback(message, percent)

        Returns:
            Comprehensive analysis result dictionary
        """
        logger.info(f"Starting hybrid analysis ({len(contract_text)} chars)")

        if progress_callback:
            progress_callback("Extracting clauses programmatically...", 10)

        # Step 1A: Strict regex extraction
        extracted_clauses = extract_all_template_clauses(contract_text)

        regex_clauses = sum(len(clauses) for clauses in extracted_clauses.values())
        logger.info(f"Regex extraction found {regex_clauses} clauses across {len(extracted_clauses)} categories")

        # Step 1B: Fuzzy matching (catches clauses missed by strict regex)
        if self.use_fuzzy_matching and self.fuzzy_matcher:
            if progress_callback:
                progress_callback("Running fuzzy logic to find additional clauses...", 20)

            fuzzy_matches = self.fuzzy_matcher.find_matching_categories(contract_text, min_matches=25)
            logger.info(f"Fuzzy matching identified {len(fuzzy_matches)} likely categories")

            # For categories found by fuzzy but not regex, do targeted extraction
            for match in fuzzy_matches:
                category_key = self._normalize_category_name(match.category)
                if category_key not in extracted_clauses:
                    # Extract context around fuzzy match
                    fuzzy_clause = {
                        'category': category_key,
                        'matched_pattern': f'fuzzy:{match.keywords[0] if match.keywords else "semantic"}',
                        'matched_text': match.matched_text,
                        'context': match.matched_text,  # Fuzzy already provides context
                        'position': 0,
                        'confidence': f'fuzzy_{match.score:.0f}'
                    }

                    if category_key not in extracted_clauses:
                        extracted_clauses[category_key] = []
                    extracted_clauses[category_key].append(fuzzy_clause)

            fuzzy_added = sum(len(clauses) for clauses in extracted_clauses.values()) - regex_clauses
            logger.info(f"Fuzzy matching added {fuzzy_added} additional clause candidates")

        total_clauses = sum(len(clauses) for clauses in extracted_clauses.values())

        if progress_callback:
            progress_callback(f"Found {total_clauses} clauses (regex + fuzzy), enhancing with AI...", 30)

        # Step 2: AI enhancement (batched by section)
        section_groups = self._group_clauses_by_section(extracted_clauses)
        enhanced_results = {}

        total_sections = len(section_groups)
        logger.info(f"Processing {total_sections} sections with batched AI enhancement")

        for section_idx, (section_name, section_clauses) in enumerate(section_groups.items()):
            section_progress = 30 + int((section_idx / total_sections) * 60)

            if progress_callback:
                section_display = section_name.replace('_', ' ').title()
                progress_callback(
                    f"Analyzing {section_display} (Section {section_idx + 1}/{total_sections})...",
                    section_progress
                )

            try:
                # Batch enhance entire section with one API call
                section_enhanced = self._enhance_section_batch(
                    section_name=section_name,
                    section_clauses=section_clauses,
                    progress_callback=progress_callback,
                    current_percent=section_progress
                )

                # Merge section results into overall results
                enhanced_results.update(section_enhanced)

                logger.info(f"Section {section_idx + 1}/{total_sections} complete: {len(section_enhanced)} categories enhanced")

            except Exception as e:
                logger.error(f"Failed to enhance section {section_name}: {e}")
                # Continue with other sections even if one fails
                continue

        if progress_callback:
            progress_callback("Compiling final analysis...", 95)

        # Step 3: Compile into comprehensive result
        final_result = self._compile_comprehensive_result(enhanced_results, extracted_clauses)

        if progress_callback:
            progress_callback("Analysis complete!", 100)

        logger.info(f"Hybrid analysis complete: {len(enhanced_results)} categories with enhanced clauses")

        return final_result

    def _enhance_clause_with_ai(
        self,
        category: str,
        clause_text: str,
        matched_pattern: str
    ) -> Optional[EnhancedClause]:
        """
        Send extracted clause to AI for verification and enhancement.

        Args:
            category: Template category name
            clause_text: Extracted clause text
            matched_pattern: Regex pattern that matched

        Returns:
            EnhancedClause or None if verification failed
        """
        # Create focused prompt for AI enhancement
        prompt = f"""You are a contract analysis expert verifying and enhancing an extracted clause.

**Template Category:** {category.replace('_', ' ').title()}
**Matched Pattern:** {matched_pattern}

**Extracted Clause Text:**
{clause_text}

**Your Tasks:**
1. **Verify** this clause belongs to category "{category}" (if not, respond with "INVALID")
2. **Identify Location** - where in the contract this clause is found (section number, article, page)
3. **Summarize** - provide a brief, concise summary (1-2 sentences) of what the clause covers
4. **Suggest Redline Recommendations** - specific changes to reduce risk
5. **Flag Harmful Language** - terms conflicting with standard practices

**Output Format (JSON):**
{{
  "valid": true/false,
  "clause_location": "Section X, Article Y, Page Z",
  "clause_summary": "Brief summary of what the clause covers and its key obligations.",
  "redline_recommendations": [
    {{"action": "replace", "text": "...", "reason": "..."}}
  ],
  "harmful_language_policy_conflicts": ["...", "..."],
  "confidence": "high/medium/low"
}}

Output ONLY valid JSON, no explanations."""

        try:
            system_msg = "You are a contract analysis expert."
            content = self.ai_client.generate(system_msg, prompt)
            content = content.strip()

            # Remove markdown code blocks if present
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]

            result = json.loads(content)

            # Check if clause was validated
            if not result.get('valid', False):
                logger.debug(f"AI rejected clause for category {category}")
                return None

            # Create enhanced clause
            return EnhancedClause(
                category=category,
                clause_location=result.get('clause_location', clause_text[:200]),
                clause_summary=result.get('clause_summary', ''),
                redline_recommendations=result.get('redline_recommendations', []),
                harmful_language_policy_conflicts=result.get('harmful_language_policy_conflicts', []),
                confidence=result.get('confidence', 'medium'),
                extraction_method='regex+ai'
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"AI enhancement failed: {e}")
            return None

    def _filter_generic_placeholders(self, values: List[str]) -> List[str]:
        """Remove known generic AI placeholder strings from a list field."""
        return [v for v in values if v.strip().lower() not in GENERIC_PLACEHOLDERS]

    def _enhance_section_batch(
        self,
        section_name: str,
        section_clauses: Dict[str, List],
        progress_callback: Optional[Callable[[str, int], None]] = None,
        current_percent: int = 30
    ) -> Dict[str, List[EnhancedClause]]:
        """
        Enhance all clauses in a section with ONE batched AI call.

        Args:
            section_name: Section identifier (e.g., 'legal_risk_and_enforcement')
            section_clauses: Dict of category -> list of clauses for this section
            progress_callback: Progress callback function
            current_percent: Current progress percentage

        Returns:
            Dict of category -> list of EnhancedClause objects
        """
        import json
        logger.info(f"Batched enhancement for {section_name}: {len(section_clauses)} categories")

        # Flatten all clauses into a single list so we can sub-batch by count
        flat_items = []  # (clause_id, category, idx, clause_dict)
        for category, clauses in section_clauses.items():
            for idx, clause in enumerate(clauses):
                clause_id = f"{category}_{idx}"
                flat_items.append((clause_id, category, idx, clause))

        total = len(flat_items)
        logger.info(f"  {total} total clause candidates — splitting into sub-batches of {MAX_CLAUSES_PER_BATCH}")

        # Merge results from all sub-batches
        all_batch_results: Dict[str, dict] = {}

        for batch_start in range(0, total, MAX_CLAUSES_PER_BATCH):
            sub_batch = flat_items[batch_start:batch_start + MAX_CLAUSES_PER_BATCH]
            batch_num = batch_start // MAX_CLAUSES_PER_BATCH + 1
            total_batches = (total + MAX_CLAUSES_PER_BATCH - 1) // MAX_CLAUSES_PER_BATCH
            logger.info(f"  Sub-batch {batch_num}/{total_batches}: {len(sub_batch)} clauses")

            # Build prompt for this sub-batch
            clause_blocks = []
            for clause_id, category, idx, clause in sub_batch:
                category_display = category.replace('_', ' ').title()
                category_definition = CATEGORY_SEARCH_DESCRIPTIONS.get(category, category_display)
                clause_blocks.append(
                    f"\n### Category: {category_display}\n"
                    f"**Definition:** {category_definition}\n"
                    f"**Clause ID:** {clause_id}\n"
                    f"**Triggered by pattern:** `{clause.get('matched_pattern', 'N/A')}`\n"
                    f"**Matched phrase:** `{clause.get('matched_text', 'N/A')}`\n"
                    f"**Context:**\n{clause['context'][:800]}"
                )

            batch_prompt = f"""You are a contract analysis expert. Analyze the clauses below from a construction contract.

IMPORTANT VALIDATION RULE: Each clause block shows a Category Definition. You MUST compare the clause text against that definition. If the clause text does NOT clearly contain content matching the Category Definition, you MUST return "valid": false. Do not accept tangentially related, misplaced, or incidentally mentioned content as a match.

For EACH clause, return:
1. "valid": true if the clause text clearly matches its Category Definition, false otherwise.
2. "clause_location": Where in the contract this clause is found (section number, article, page reference).
3. "clause_summary": A brief, concise summary (1-2 sentences) of what the clause covers and its key obligations.
4. "redline_recommendations": Specific edits to reduce risk referencing actual clause language.
5. "harmful_language_policy_conflicts": Quote exact phrases conflicting with standard norms. Return [] if none.
6. "confidence": "high", "medium", or "low".

{"".join(clause_blocks)}

Output a JSON object keyed by Clause ID:
{{
  "clause_id": {{
    "valid": true,
    "clause_location": "Section X, Article Y, Page Z",
    "clause_summary": "Brief summary of what the clause covers.",
    "redline_recommendations": [{{"action": "replace", "text": "...", "reason": "..."}}],
    "harmful_language_policy_conflicts": ["..."],
    "confidence": "high"
  }}
}}

Output ONLY valid JSON."""

            try:
                system_msg = "You are a contract analysis expert."
                content = self.ai_client.generate(system_msg, batch_prompt)
                if not content:
                    logger.error(f"Empty response for sub-batch {batch_num}")
                    continue
                content = content.strip()

                # Strip markdown code blocks
                if content.startswith('```'):
                    parts = content.split('```')
                    if len(parts) >= 2:
                        content = parts[1]
                    if content.startswith('json'):
                        content = content[4:]

                # Extract JSON object from response
                first_brace = content.find('{')
                last_brace = content.rfind('}')
                if first_brace != -1 and last_brace > first_brace:
                    content = content[first_brace:last_brace + 1]

                # Fix trailing commas
                import re
                content = re.sub(r',\s*([}\]])', r'\1', content)

                # Fix unclosed braces
                open_b = content.count('{')
                close_b = content.count('}')
                if open_b > close_b:
                    content += '}' * (open_b - close_b)

                sub_results = json.loads(content)
                if isinstance(sub_results, dict):
                    all_batch_results.update(sub_results)
                    logger.info(f"  Sub-batch {batch_num} parsed: {len(sub_results)} clause results")
                else:
                    logger.warning(f"  Sub-batch {batch_num} returned non-dict: {type(sub_results)}")
            except json.JSONDecodeError as e:
                logger.error(f"Sub-batch {batch_num} JSON parse failed for {section_name}: {e}")
                logger.debug(f"  Response preview: {content[:300] if content else 'empty'}")
                continue
            except Exception as e:
                logger.error(f"Sub-batch {batch_num} failed for {section_name}: {e}")
                continue  # Skip this sub-batch, don't crash the whole section

        # Reconstruct enhanced clauses by category from merged results
        enhanced_by_category: Dict[str, List[EnhancedClause]] = {}
        for clause_id, category, idx, original in flat_items:
            if clause_id not in all_batch_results:
                continue
            result = all_batch_results[clause_id]
            if not result.get('valid', False):
                continue

            enhanced_clause = EnhancedClause(
                category=category,
                clause_location=result.get('clause_location', original['context'][:200]),
                clause_summary=result.get('clause_summary', ''),
                redline_recommendations=result.get('redline_recommendations', []),
                harmful_language_policy_conflicts=self._filter_generic_placeholders(
                    result.get('harmful_language_policy_conflicts', [])
                ),
                confidence=result.get('confidence', 'medium'),
                extraction_method='regex+ai_batch'
            )
            enhanced_by_category.setdefault(category, []).append(enhanced_clause)

        logger.info(f"Batch enhancement complete: {len(enhanced_by_category)} categories, {len(all_batch_results)} clauses processed")
        return enhanced_by_category

    def _normalize_category_name(self, category_name: str) -> str:
        """
        Normalize category names between different formats.

        Fuzzy matcher uses "Contract Term, Renewal & Extensions" format,
        template_patterns uses "contract_term_renewal_extensions" format.

        Args:
            category_name: Category name in any format

        Returns:
            Normalized category name (lowercase with underscores)
        """
        # Convert to lowercase
        normalized = category_name.lower()

        # Replace special characters with underscores
        normalized = normalized.replace(' & ', ' ')
        normalized = normalized.replace('&', ' ')
        normalized = normalized.replace(',', '')
        normalized = normalized.replace('/', ' ')
        normalized = normalized.replace('(', '')
        normalized = normalized.replace(')', '')

        # Replace spaces with underscores
        normalized = '_'.join(normalized.split())

        # Remove duplicate underscores
        while '__' in normalized:
            normalized = normalized.replace('__', '_')

        return normalized.strip('_')

    def _get_section_for_category(self, category: str) -> str:
        """
        Map category to section name for progress display.

        Args:
            category: Category name (e.g., 'indemnification')

        Returns:
            Human-readable section name
        """
        # Section mapping (same as in _compile_comprehensive_result)
        section_categories = {
            'administrative_and_commercial_terms': [
                'contract_term_renewal_extensions', 'bonding_surety_insurance',
                'retainage_progress_payments', 'pay_when_paid_if_paid',
                'price_escalation', 'fuel_price_adjustment', 'change_orders',
                'termination_for_convenience', 'termination_for_cause',
                'bid_protest', 'bid_tabulation', 'contractor_qualification',
                'release_orders', 'assignment_novation', 'audit_rights',
                'notice_requirements'
            ],
            'technical_and_performance_terms': [
                'scope_of_work', 'performance_schedule', 'delays',
                'suspension_of_work', 'submittals', 'emergency_work',
                'permits_licensing', 'warranty'
            ],
            'legal_risk_and_enforcement': [
                'indemnification', 'duty_to_defend', 'limitation_of_liability',
                'insurance_coverage', 'dispute_resolution', 'flow_down_clauses',
                'subcontracting', 'safety_osha', 'site_conditions',
                'environmental', 'order_of_precedence', 'setoff_withholding'
            ],
            'regulatory_and_compliance_terms': [
                'certified_payroll', 'prevailing_wage', 'eeo', 'mwbe_dbe',
                'apprenticeship', 'e_verify', 'worker_classification',
                'drug_free_workplace'
            ],
            'data_technology_and_deliverables': [
                'data_ownership', 'ai_technology_use',
                'cybersecurity', 'digital_deliverables', 'document_retention',
                'confidentiality'
            ]
        }

        section_names = {
            'administrative_and_commercial_terms': 'Section II Admin & Commercial',
            'technical_and_performance_terms': 'Section III Technical & Performance',
            'legal_risk_and_enforcement': 'Section IV Legal Risk',
            'regulatory_and_compliance_terms': 'Section V Regulatory & Compliance',
            'data_technology_and_deliverables': 'Section VI Data & Technology'
        }

        # Find which section this category belongs to
        for section_id, categories in section_categories.items():
            if category in categories:
                return section_names.get(section_id, section_id)

        return "Other"

    def _group_clauses_by_section(self, extracted_clauses: Dict[str, List]) -> Dict[str, Dict[str, List]]:
        """
        Group extracted clauses by section for batch processing.

        Args:
            extracted_clauses: Dict of category -> list of clauses

        Returns:
            Dict of section_name -> {category -> list of clauses}
        """
        # Section mapping (same structure as in _compile_comprehensive_result)
        section_mapping = {
            'administrative_and_commercial_terms': [
                'contract_term_renewal_extensions', 'bonding_surety_insurance',
                'retainage_progress_payments', 'pay_when_paid_if_paid',
                'price_escalation', 'fuel_price_adjustment', 'change_orders',
                'termination_for_convenience', 'termination_for_cause',
                'bid_protest', 'bid_tabulation', 'contractor_qualification',
                'release_orders', 'assignment_novation', 'audit_rights',
                'notice_requirements'
            ],
            'technical_and_performance_terms': [
                'scope_of_work', 'performance_schedule', 'delays',
                'suspension_of_work', 'submittals', 'emergency_work',
                'permits_licensing', 'warranty'
            ],
            'legal_risk_and_enforcement': [
                'indemnification', 'duty_to_defend', 'limitation_of_liability',
                'insurance_coverage', 'dispute_resolution', 'flow_down_clauses',
                'subcontracting', 'safety_osha', 'site_conditions',
                'environmental', 'order_of_precedence', 'setoff_withholding'
            ],
            'regulatory_and_compliance_terms': [
                'certified_payroll', 'prevailing_wage', 'eeo', 'mwbe_dbe',
                'apprenticeship', 'e_verify', 'worker_classification',
                'drug_free_workplace'
            ],
            'data_technology_and_deliverables': [
                'data_ownership', 'ai_technology_use',
                'cybersecurity', 'digital_deliverables', 'document_retention',
                'confidentiality'
            ]
        }

        # Group clauses by section
        section_groups = {}

        for section, categories in section_mapping.items():
            section_clauses = {}
            for category in categories:
                if category in extracted_clauses and extracted_clauses[category]:
                    section_clauses[category] = extracted_clauses[category]

            if section_clauses:
                section_groups[section] = section_clauses

        logger.info(f"Grouped {len(extracted_clauses)} categories into {len(section_groups)} sections for batch processing")

        return section_groups

    def _compile_comprehensive_result(
        self,
        enhanced_results: Dict[str, List[EnhancedClause]],
        extracted_clauses: Optional[Dict[str, List]] = None
    ) -> Dict:
        """
        Compile enhanced clauses into comprehensive analysis result.

        Args:
            enhanced_results: Dictionary of category -> enhanced clauses
            extracted_clauses: Raw extraction output (category -> clause list) for not-present markers

        Returns:
            Comprehensive analysis dictionary
        """
        result = {
            'analysis_method': 'hybrid_programmatic_ai',
            'total_clauses_found': sum(len(clauses) for clauses in enhanced_results.values()),
            'categories_found': len(enhanced_results),
            'categories_rejected_by_ai': 0,
            'sections': {}
        }

        # Map categories to sections
        section_mapping = {
            'administrative_and_commercial_terms': [
                'contract_term_renewal_extensions', 'bonding_surety_insurance',
                'retainage_progress_payments', 'pay_when_paid_if_paid',
                'price_escalation', 'fuel_price_adjustment', 'change_orders',
                'termination_for_convenience', 'termination_for_cause',
                'bid_protest', 'bid_tabulation', 'contractor_qualification',
                'release_orders', 'assignment_novation', 'audit_rights',
                'notice_requirements'
            ],
            'technical_and_performance_terms': [
                'scope_of_work', 'performance_schedule', 'delays',
                'suspension_of_work', 'submittals', 'emergency_work',
                'permits_licensing', 'warranty'
            ],
            'legal_risk_and_enforcement': [
                'indemnification', 'duty_to_defend', 'limitation_of_liability',
                'insurance_coverage', 'dispute_resolution', 'flow_down_clauses',
                'subcontracting', 'safety_osha', 'site_conditions',
                'environmental', 'order_of_precedence', 'setoff_withholding'
            ],
            'regulatory_and_compliance_terms': [
                'certified_payroll', 'prevailing_wage', 'eeo', 'mwbe_dbe',
                'apprenticeship', 'e_verify', 'worker_classification',
                'drug_free_workplace'
            ],
            'data_technology_and_deliverables': [
                'data_ownership', 'ai_technology_use',
                'cybersecurity', 'digital_deliverables', 'document_retention',
                'confidentiality'
            ]
        }

        # Organize by section
        for section, categories in section_mapping.items():
            section_clauses = {}
            for category in categories:
                if category in enhanced_results:
                    section_clauses[category] = [
                        {
                            'clause_location': clause.clause_location,
                            'clause_summary': clause.clause_summary,
                            'redline_recommendations': clause.redline_recommendations,
                            'harmful_language_policy_conflicts': clause.harmful_language_policy_conflicts,
                            'confidence': clause.confidence
                        }
                        for clause in enhanced_results[category]
                    ]
                elif extracted_clauses and category in extracted_clauses:
                    # Regex found candidates but AI rejected all as not matching the category definition
                    n = len(extracted_clauses[category])
                    result['categories_rejected_by_ai'] += 1
                    section_clauses[category] = [{
                        'not_present_in_contract': True,
                        'note': f"Regex found {n} candidate(s) but AI rejected all as not matching the category definition."
                    }]
                elif extracted_clauses is not None:
                    # Regex found nothing and AI was never invoked
                    section_clauses[category] = [{
                        'not_present_in_contract': True,
                        'note': f"No {category.replace('_', ' ')} clause found in this contract."
                    }]

            if section_clauses:
                result['sections'][section] = section_clauses

        return result
