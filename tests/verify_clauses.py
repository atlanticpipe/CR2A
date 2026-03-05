"""
Verify that clauses listed in Contract_5_Clauses.txt actually exist in Contract_5.pdf.

Strategy:
1. Parse each quoted clause from the clauses file
2. Extract key phrases (6-word sliding window) from each clause
3. Search for those phrases in the full contract text (normalized)
4. Report: CONFIRMED, PARTIAL, or NOT FOUND
"""

import re
import os
import unicodedata

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

def normalize(text):
    """Normalize text for comparison: lowercase, collapse whitespace, remove special quotes."""
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = text.replace('\u00ab', '"').replace('\u00bb', '"')
    text = text.replace('\u2013', '-').replace('\u2014', '-')
    text = unicodedata.normalize('NFKD', text)
    text = re.sub(r'[^\w\s]', ' ', text)  # Remove punctuation for matching
    text = re.sub(r'\s+', ' ', text)
    return text.lower().strip()

def extract_key_phrases(clause_text, phrase_len=6):
    """Extract sliding window phrases from clause text."""
    words = clause_text.split()
    if len(words) < phrase_len:
        return [' '.join(words)] if len(words) >= 4 else []
    phrases = []
    for i in range(0, len(words) - phrase_len + 1, max(1, phrase_len // 2)):
        phrases.append(' '.join(words[i:i + phrase_len]))
    return phrases

def parse_clauses_file(filepath):
    """Parse Contract_5_Clauses.txt into structured categories."""
    with open(filepath, 'r', encoding='cp1252') as f:
        lines = f.readlines()

    categories = []
    current_section = ""
    current_category = ""
    current_clause_lines = []

    section_pattern = re.compile(r'^(I{1,3}V?|V|VI{0,3})\.\s+(.+)')
    # Category: starts with "number. Text" but NOT "number) " which is a clause item
    category_pattern = re.compile(r'^(\d+)\.\s+([A-Z].+)')

    for line in lines:
        stripped = line.rstrip('\n').strip()
        if not stripped:
            continue

        # Skip first line (header)
        if stripped.startswith('Clause Risk'):
            continue

        # Check for main section header (Roman numerals)
        sec_match = section_pattern.match(stripped)
        if sec_match:
            # Save previous
            if current_category and current_clause_lines:
                categories.append({
                    'section': current_section,
                    'category': current_category,
                    'lines': current_clause_lines[:]
                })
            current_section = sec_match.group(2).strip()
            current_category = ""
            current_clause_lines = []
            continue

        # Check for category header
        cat_match = category_pattern.match(stripped)
        if cat_match:
            # Save previous category
            if current_category and current_clause_lines:
                categories.append({
                    'section': current_section,
                    'category': current_category,
                    'lines': current_clause_lines[:]
                })
            current_category = cat_match.group(2).strip()
            current_clause_lines = []
            continue

        # Everything else is clause content
        if current_category:
            current_clause_lines.append(stripped)

    # Save last
    if current_category and current_clause_lines:
        categories.append({
            'section': current_section,
            'category': current_category,
            'lines': current_clause_lines[:]
        })

    return categories

def extract_quoted_segments(lines):
    """Extract individually quoted text segments from clause lines."""
    combined = ' '.join(lines)

    segments = []

    # Find text between quote marks (including smart quotes)
    # Handle both "..." and "..." styles
    quote_pairs = [
        ('\u201c', '\u201d'),   # smart double quotes
        ('"', '"'),             # regular double quotes
    ]

    for open_q, close_q in quote_pairs:
        # Use a simple state machine to handle nested content
        i = 0
        while i < len(combined):
            start = combined.find(open_q, i)
            if start == -1:
                break
            end = combined.find(close_q, start + 1)
            if end == -1:
                break
            text = combined[start + 1:end].strip()
            if len(text) > 25:
                segments.append(text)
            i = end + 1

    # Deduplicate based on normalized first 100 chars
    seen = set()
    unique = []
    for seg in segments:
        key = normalize(seg)[:100]
        if key not in seen:
            seen.add(key)
            unique.append(seg)

    return unique

def verify_clause(clause_text, contract_norm, phrase_len=6):
    """Check if a clause exists in the contract text."""
    clause_norm = normalize(clause_text)
    phrases = extract_key_phrases(clause_norm, phrase_len)

    if not phrases:
        return 0.0, 0, 0, [], []

    matched = 0
    matched_list = []
    unmatched_list = []

    for phrase in phrases:
        if phrase in contract_norm:
            matched += 1
            matched_list.append(phrase)
        else:
            unmatched_list.append(phrase)

    score = matched / len(phrases) if phrases else 0
    return score, matched, len(phrases), matched_list, unmatched_list

def main():
    contract_text_path = os.path.join(SCRIPT_DIR, 'contract5_fulltext.txt')
    clauses_path = os.path.join(PROJECT_DIR, 'Contract_5_Clauses.txt')

    with open(contract_text_path, 'r', encoding='utf-8') as f:
        contract_text = f.read()
    contract_norm = normalize(contract_text)
    print(f"Contract text loaded: {len(contract_text):,} chars")

    categories = parse_clauses_file(clauses_path)
    print(f"Parsed {len(categories)} categories from clauses file\n")

    confirmed_list = []
    partial_list = []
    not_found_list = []
    not_present_list = []
    no_quotes_list = []

    total_clauses = 0
    total_confirmed = 0
    total_partial = 0
    total_not_found = 0

    for cat in categories:
        section = cat['section']
        category = cat['category']
        lines = cat['lines']

        # Check "not present"
        if any('not present in contract' in l.lower() for l in lines):
            not_present_list.append(f"{section} > {category}")
            continue

        # Extract quoted segments
        quotes = extract_quoted_segments(lines)

        if not quotes:
            no_quotes_list.append(f"{section} > {category}")
            continue

        print(f"{'='*90}")
        print(f"  {section} > {category}  ({len(quotes)} quoted segments)")
        print(f"{'='*90}")

        for i, quote in enumerate(quotes):
            total_clauses += 1
            score, matched, total, matched_p, unmatched_p = verify_clause(
                quote, contract_norm, phrase_len=6
            )

            preview = quote[:140].replace('\n', ' ')

            if score >= 0.7:
                status = "CONFIRMED"
                icon = "+"
                total_confirmed += 1
                confirmed_list.append({
                    'section': section, 'category': category,
                    'preview': preview, 'score': score,
                    'matched': matched, 'total': total
                })
            elif score >= 0.2:
                status = "PARTIAL "
                icon = "~"
                total_partial += 1
                partial_list.append({
                    'section': section, 'category': category,
                    'preview': preview, 'score': score,
                    'matched': matched, 'total': total,
                    'unmatched': unmatched_p[:3]
                })
            else:
                status = "NOT FOUND"
                icon = "X"
                total_not_found += 1
                not_found_list.append({
                    'section': section, 'category': category,
                    'preview': preview, 'score': score,
                    'matched': matched, 'total': total,
                    'unmatched': unmatched_p[:5]
                })

            print(f"  [{icon}] {status} ({score:.0%}, {matched}/{total}) \"{preview}\"")
            if status != "CONFIRMED" and unmatched_p:
                for up in unmatched_p[:2]:
                    print(f"        missing phrase: \"{up}\"")

        print()

    # ==================== SUMMARY ====================
    print("\n" + "#"*90)
    print("  VERIFICATION SUMMARY")
    print("#"*90)
    print(f"  Total quoted clauses checked:  {total_clauses}")
    print(f"  CONFIRMED  (>=70% match):      {total_confirmed}  ({total_confirmed/max(total_clauses,1)*100:.1f}%)")
    print(f"  PARTIAL    (20-70% match):      {total_partial}  ({total_partial/max(total_clauses,1)*100:.1f}%)")
    print(f"  NOT FOUND  (<20% match):        {total_not_found}  ({total_not_found/max(total_clauses,1)*100:.1f}%)")
    print(f"  Not present in contract:        {len(not_present_list)}")
    print(f"  No extractable quotes:          {len(no_quotes_list)}")

    if not_found_list:
        print(f"\n{'='*90}")
        print(f"  LIKELY HALLUCINATED - NOT FOUND IN CONTRACT")
        print(f"{'='*90}")
        for item in not_found_list:
            print(f"\n  [{item['score']:.0%}] {item['section']} > {item['category']}")
            print(f"       \"{item['preview']}\"")
            if item.get('unmatched'):
                for up in item['unmatched'][:3]:
                    print(f"       missing: \"{up}\"")

    if partial_list:
        print(f"\n{'='*90}")
        print(f"  PARTIAL MATCHES - MAY BE PARAPHRASED OR FROM DIFFERENT SOURCE")
        print(f"{'='*90}")
        for item in partial_list:
            print(f"\n  [{item['score']:.0%}] {item['section']} > {item['category']}")
            print(f"       \"{item['preview']}\"")
            if item.get('unmatched'):
                for up in item['unmatched'][:2]:
                    print(f"       missing: \"{up}\"")

    if not_present_list:
        print(f"\n{'='*90}")
        print(f"  MARKED 'NOT PRESENT IN CONTRACT'")
        print(f"{'='*90}")
        for item in not_present_list:
            print(f"  - {item}")

    if no_quotes_list:
        print(f"\n{'='*90}")
        print(f"  CATEGORIES WITH NO EXTRACTABLE QUOTED TEXT")
        print(f"{'='*90}")
        for item in no_quotes_list:
            print(f"  - {item}")

if __name__ == '__main__':
    main()
