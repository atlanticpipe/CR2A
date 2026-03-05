"""
Test regex extraction against verified clauses from Contract_5_Verified_Clauses.md.

Runs extract_all_template_clauses() on Contract_5.pdf text, then checks whether
each of the 53 verified clauses is captured in the regex output.
"""

import os
import sys
import re
import unicodedata

# Add project root to path
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from analyzer.template_patterns import extract_all_template_clauses, TEMPLATE_PATTERNS

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def normalize(text):
    """Normalize for comparison."""
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = text.replace('\u2013', '-').replace('\u2014', '-')
    text = unicodedata.normalize('NFKD', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.lower().strip()


def extract_key_phrases(text, phrase_len=6):
    words = text.split()
    if len(words) < phrase_len:
        return [' '.join(words)] if len(words) >= 4 else []
    phrases = []
    for i in range(0, len(words) - phrase_len + 1, max(1, phrase_len // 2)):
        phrases.append(' '.join(words[i:i + phrase_len]))
    return phrases


def phrase_match_score(needle_text, haystack_text, phrase_len=6):
    """What fraction of needle's phrases appear in haystack."""
    needle_norm = normalize(needle_text)
    haystack_norm = normalize(haystack_text)
    phrases = extract_key_phrases(needle_norm, phrase_len)
    if not phrases:
        return 0.0
    matched = sum(1 for p in phrases if p in haystack_norm)
    return matched / len(phrases)


# Map section+category names from the markdown to regex category keys
CATEGORY_MAP = {
    "Bonding, Surety, & Insurance Obligations": "bonding_surety_insurance",
    "Retainage, Progress Payments & Final Payment Terms": "retainage_progress_payments",
    "Pay-When-Paid, Pay-If-Paid, or Owner Payment Contingencies": "pay_when_paid_if_paid",
    "Price Escalation Clauses (Labor, Materials, Fuel, Inflation Adjustments)": "price_escalation",
    "Change Orders, Scope Adjustments & Modifications": "change_orders",
    "Bid Protest Procedures & Claims of Improper Award": "bid_protest",
    "Bid Tabulation, Competition & Award Process Requirements": "bid_tabulation",
    "Performance Schedule, Time for Completion & Critical Path Obligations": "performance_schedule",
    "Suspension of Work, Work Stoppages & Agency Directives": "suspension_of_work",
    "Submittals, Documentation & Approval Requirements": "submittals",
    "Mobilization & Demobilization Provisions": "mobilization_demobilization",
    "Utility Coordination, Locate Risk & Conflict Avoidance": "utility_coordination",
    "Insurance Coverage, Additional Insured & Waiver of Subrogation Clauses": "insurance_coverage",
    "Subcontracting Restrictions, Approval & Substitution Requirements": "subcontracting",
    "Safety Standards, OSHA Compliance & Site-Specific Safety Obligations": "safety_osha",
    "Site Conditions, Differing Site Conditions & Changed Circumstances Clauses": "site_conditions",
    "Environmental Hazards, Waste Disposal & Hazardous Materials Provisions": "environmental",
    "Setoff & Withholding Rights (Owner's Right to Deduct or Withhold Payment)": "setoff_withholding",
    "Digital Surveillance, GIS-Tagged Deliverables & Monitoring Requirements": "digital_deliverables",
    "Intellectual Property, Licensing & Ownership of Work Product": "intellectual_property",
}


def parse_verified_clauses(md_path):
    """Parse Contract_5_Verified_Clauses.md into list of (category_name, clause_text)."""
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    clauses = []
    current_category = None
    current_quote_lines = []
    in_quote = False

    for line in lines:
        stripped = line.rstrip('\n')

        # Category header: ### N. Category Name
        cat_match = re.match(r'^### \d+\.\s+(.+)', stripped)
        if cat_match:
            # Flush previous quote
            if current_category and current_quote_lines:
                text = ' '.join(current_quote_lines).strip()
                if text and not text.startswith('*Match'):
                    clauses.append((current_category, text))
                current_quote_lines = []

            current_category = cat_match.group(1).strip()
            in_quote = False
            continue

        # Quote block lines
        if stripped.startswith('> '):
            content = stripped[2:]
            if content.startswith('*Match confidence:'):
                # End of this quote - flush
                if current_category and current_quote_lines:
                    text = ' '.join(current_quote_lines).strip()
                    if text:
                        clauses.append((current_category, text))
                current_quote_lines = []
                in_quote = False
            elif content == '':
                continue
            else:
                current_quote_lines.append(content)
                in_quote = True
            continue

        # Non-quote line while in quote means quote ended
        if in_quote and not stripped.startswith('>'):
            if current_category and current_quote_lines:
                text = ' '.join(current_quote_lines).strip()
                if text:
                    clauses.append((current_category, text))
            current_quote_lines = []
            in_quote = False

    # Flush last
    if current_category and current_quote_lines:
        text = ' '.join(current_quote_lines).strip()
        if text:
            clauses.append((current_category, text))

    return clauses


def main():
    # Load contract text
    contract_path = os.path.join(SCRIPT_DIR, 'contract5_fulltext.txt')
    with open(contract_path, 'r', encoding='utf-8') as f:
        contract_text = f.read()

    print(f"Contract text: {len(contract_text):,} chars")
    print(f"Regex categories defined: {len(TEMPLATE_PATTERNS)}")
    print()

    # Step 1: Run regex extraction
    print("Running extract_all_template_clauses()...")
    extracted = extract_all_template_clauses(contract_text)

    total_regex_hits = sum(len(v) for v in extracted.values())
    print(f"Regex found: {total_regex_hits} clause hits across {len(extracted)} categories")
    print()

    # Show what regex found per category
    print("=" * 90)
    print("  REGEX EXTRACTION RESULTS")
    print("=" * 90)
    for cat, clauses in sorted(extracted.items()):
        print(f"  {cat:50s} -> {len(clauses)} hit(s)")
    print()

    # Step 2: Load verified clauses
    md_path = os.path.join(PROJECT_DIR, 'Contract_5_Verified_Clauses.md')
    verified = parse_verified_clauses(md_path)
    print(f"Verified clauses loaded: {len(verified)}")
    print()

    # Step 3: Check each verified clause against regex output
    print("=" * 90)
    print("  MATCHING VERIFIED CLAUSES TO REGEX OUTPUT")
    print("=" * 90)

    found = []
    missed = []

    for cat_name, clause_text in verified:
        # Map category name to regex key
        regex_key = CATEGORY_MAP.get(cat_name)

        if not regex_key:
            # Try fuzzy key lookup
            norm_name = cat_name.lower().replace(' & ', ' ').replace('&', ' ')
            norm_name = norm_name.replace(',', '').replace('/', ' ')
            norm_name = norm_name.replace('(', '').replace(')', '')
            norm_name = '_'.join(norm_name.split())
            for key in TEMPLATE_PATTERNS:
                if key in norm_name or norm_name in key:
                    regex_key = key
                    break

        clause_preview = clause_text[:100].replace('\n', ' ')

        if not regex_key:
            missed.append({
                'category': cat_name,
                'regex_key': None,
                'clause': clause_preview,
                'reason': 'No matching regex category found'
            })
            print(f"  [X] NO CATEGORY: {cat_name}")
            print(f"       \"{clause_preview}\"")
            print()
            continue

        if regex_key not in extracted:
            missed.append({
                'category': cat_name,
                'regex_key': regex_key,
                'clause': clause_preview,
                'reason': f'Regex category "{regex_key}" had 0 hits'
            })
            print(f"  [X] NO HITS: {cat_name} (regex_key: {regex_key})")
            print(f"       \"{clause_preview}\"")
            print()
            continue

        # Check if any regex hit's context contains this verified clause
        best_score = 0.0
        best_hit = None
        for hit in extracted[regex_key]:
            context = hit.get('context', '')
            score = phrase_match_score(clause_text, context)
            if score > best_score:
                best_score = score
                best_hit = hit

        # Also check aggregated coverage across ALL hits in this category.
        # The AI pipeline processes all hits together, so a clause that spans
        # multiple hits' contexts is still "found" by the extractor.
        needle_norm = normalize(clause_text)
        phrases = extract_key_phrases(needle_norm)
        if phrases:
            all_contexts_norm = ' '.join(
                normalize(h.get('context', '')) for h in extracted[regex_key]
            )
            matched = sum(1 for p in phrases if p in all_contexts_norm)
            agg_score = matched / len(phrases)
            if agg_score > best_score:
                best_score = agg_score

        if best_score >= 0.4:
            found.append({
                'category': cat_name,
                'regex_key': regex_key,
                'clause': clause_preview,
                'score': best_score,
                'pattern': best_hit.get('matched_pattern', '') if best_hit else ''
            })
            print(f"  [+] FOUND ({best_score:.0%}): {cat_name}")
            print(f"       \"{clause_preview}\"")
        else:
            missed.append({
                'category': cat_name,
                'regex_key': regex_key,
                'clause': clause_preview,
                'reason': f'Best context overlap: {best_score:.0%}',
                'best_hit_pattern': best_hit.get('matched_pattern', '') if best_hit else '',
                'best_hit_context_preview': (best_hit.get('context', '')[:100] if best_hit else '')
            })
            print(f"  [X] MISSED ({best_score:.0%}): {cat_name}")
            print(f"       Verified: \"{clause_preview}\"")
            if best_hit:
                ctx_preview = best_hit.get('context', '')[:100].replace('\n', ' ')
                print(f"       Best hit: \"{ctx_preview}\"")
                print(f"       Pattern:  {best_hit.get('matched_pattern', '')}")

        print()

    # Summary
    print("=" * 90)
    print("  SUMMARY")
    print("=" * 90)
    print(f"  Verified clauses:     {len(verified)}")
    print(f"  Found by regex:       {len(found)}  ({len(found)/len(verified)*100:.1f}%)")
    print(f"  Missed by regex:      {len(missed)}  ({len(missed)/len(verified)*100:.1f}%)")
    print()

    if missed:
        # Group missed by reason
        print("  MISSED BREAKDOWN:")
        reasons = {}
        for m in missed:
            r = m['reason'].split(':')[0] if ':' in m['reason'] else m['reason']
            reasons.setdefault(r, []).append(m)
        for reason, items in sorted(reasons.items(), key=lambda x: -len(x[1])):
            print(f"    {reason}: {len(items)}")
            for item in items:
                print(f"      - {item['category']}: \"{item['clause'][:70]}\"")
        print()

    # Categories in regex that had NO verified clauses (potential false positives)
    verified_keys = set(CATEGORY_MAP.get(cat, '') for cat, _ in verified)
    extra_regex_cats = set(extracted.keys()) - verified_keys - {''}
    if extra_regex_cats:
        print(f"  REGEX CATEGORIES WITH HITS BUT NO VERIFIED CLAUSES ({len(extra_regex_cats)}):")
        for cat in sorted(extra_regex_cats):
            print(f"    - {cat} ({len(extracted[cat])} hits)")


if __name__ == '__main__':
    main()
