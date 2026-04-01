"""
Batch Excel generation for MSA contract analyses.
Reads CR2A analysis JSON files and produces CR2A_Analysis.xlsx workbooks
in each MSA contract directory using ExcelTemplateBuilder.
"""
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.excel_template_builder import ExcelTemplateBuilder, CONTRACT_ANALYSIS_SECTIONS

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

MSA_ROOT = Path(r"F:\APS Drive\Operations\Bids\4- Piggyback & Service Agreements\MSA Contracts")
ANALYSES_DIR = Path(__file__).parent / "analyses"

# Map analysis JSON files → (MSA directory, contract PDF filename)
ANALYSIS_MAP = {
    # Gainesville
    "gainesville_gcu.json": (
        r"Gainesville, City of (GCU)",
        "2024-083_Atlantic_Pipe_Contract Fully Executed GRU.pdf"
    ),
    # Okaloosa
    "okaloosa_county.json": (
        r"Okaloosa County\79-24 Gravity Sewer Rehab",
        "C25_4079_WS- Okaloosa Contract.pdf"
    ),
    # Orlando
    "orlando_ifb22-0161-3.json": (
        r"Orlando, City of",
        "IFB 22-0161-3 EXPIRES 07.17.26 APS Executed.pdf"
    ),
    "orlando_amendment_two.json": (
        r"Orlando, City of",
        "Amendment Two IFB22-0161-3.pdf"
    ),
    # Seminole County
    "seminole_ifb604819-24_storm_tv.json": (
        r"Seminole County\IFB 604819-24 LNF - Storm TV",
        "IFB-604819-24 LNF_ CONTRACT APS_Signed.pdf"
    ),
    "seminole_ifb604150-21_original.json": (
        r"Seminole County\IFB-604150-21 LNF",
        "IFB-604150-21_tc (Atlatic Pipe Services)_Original Contract.pdf"
    ),
    # South Daytona
    "south_daytona_original_agreement.json": (
        r"South Daytona\23-B-005 Sewer Rehab Services",
        "Agreement with Atlantic Pipe Services, LLC - April 2023.pdf"
    ),
    "south_daytona_amendment_storm.json": (
        r"South Daytona\23-B-005 Sewer Rehab Services",
        "Contract Amendment - Storm.pdf"
    ),
    "south_daytona_renewal.json": (
        r"South Daytona\23-B-005 Sewer Rehab Services",
        "Contract Renewal with Atlantic Pipe Services LLC.pdf"
    ),
    "south_daytona_renewal_letter_jan2026.json": (
        r"South Daytona\23-B-005 Sewer Rehab Services",
        "Renewal Option Letter- APS 1.12.26.pdf"
    ),
    "south_daytona_renewal_feb2026.json": (
        r"South Daytona\23-B-005 Sewer Rehab Services",
        "APS Renewal 2.4.26 South Daytona.pdf"
    ),
    # St. Johns County
    "st_johns_ca01_ren01.json": (
        r"St. Johns County\21-05 Countywide Pipe & Manhole Lining",
        "21-05 CA #01 CTR REN #01 - EXECUTED - APS.pdf"
    ),
    "st_johns_ca02_ren02.json": (
        r"St. Johns County\21-05 Countywide Pipe & Manhole Lining",
        "21-05 CA#02 CTR REN#02 - APS_ FY 23 CONTRACT FOR USE.pdf"
    ),
    "st_johns_ca04_ren04.json": (
        r"St. Johns County\21-05 Countywide Pipe & Manhole Lining",
        "21-05 CA#04 CTR REN#04 - EXECUTED - APS.pdf"
    ),
    "st_johns_ca05_final_extension.json": (
        r"St. Johns County\21-05 Countywide Pipe & Manhole Lining",
        "21-05 CA#05 CTR REN#04 - APS FINAL EXTENSION.pdf"
    ),
    "st_johns_renewal_2025.json": (
        r"St. Johns County\21-05 Countywide Pipe & Manhole Lining",
        "St John's County Contract Renewal 2025.pdf"
    ),
    # TOHO Water Authority
    "toho_20-133.json": (
        r"TOHO Water Authority\20-133 Gravity Sewer and Cleaning Inspection",
        "20-133 APS Executed ACTUAL.pdf"
    ),
    # The Villages
    "the_villages_d1.json": (
        r"The Villages",
        "D1 24P-007 Atlantic Pipe Services LLC FE.pdf"
    ),
    "the_villages_d2.json": (
        r"The Villages",
        "D2 24P-007 Atlantic Pipe Services LLC FE.pdf"
    ),
    "the_villages_d3.json": (
        r"The Villages",
        "D3 24P-007 Atlantic Pipe Services LLC FE.pdf"
    ),
    "the_villages_d4.json": (
        r"The Villages",
        "D4 24P-007 Atlantic Pipe Services LLC FE.pdf"
    ),
    "the_villages_vccdd.json": (
        r"The Villages",
        "VCCDD 24P-007 Atlantic Pipe Services LLC FE.pdf"
    ),
    # Volusia
    "volusia_22b112ls_master.json": (
        r"Volusia\22-B-112LS Sewer Main Jet Vac Clean and Inspect",
        "PUR - Master Agreements _ 12439A - 1 _   _ ATLANTIC PIPE SERVICES LLC _ 6_24_2025 _ VS8930.pdf"
    ),
    "volusia_22b112ls_renewal.json": (
        r"Volusia\22-B-112LS Sewer Main Jet Vac Clean and Inspect",
        "Contract Renewal 05.27.2025.pdf"
    ),
    "volusia_23b105ls_coatings.json": (
        r"Volusia\23-B-105LS Coatings for Manhole and Wet Well",
        "PUR - Master Agreements _ 12503 - 2 _   _ ATLANTIC PIPE SERVICES LLC _ 8_1_2023 _ VS8930.pdf"
    ),
}

# Build a set of all valid category keys
ALL_CAT_KEYS = set()
for _section_title, items in CONTRACT_ANALYSIS_SECTIONS:
    for cat_key, _label in items:
        ALL_CAT_KEYS.add(cat_key)

# Map section_key → cat_key → display_name (reverse lookup from analysis JSON)
SECTION_KEY_TO_CATS = {}
for _section_title, items in CONTRACT_ANALYSIS_SECTIONS:
    for cat_key, display_label in items:
        SECTION_KEY_TO_CATS[display_label] = cat_key


def load_analysis(json_path: Path) -> dict:
    """Load and validate a CR2A analysis JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_clause_blocks(analysis: dict) -> dict:
    """Extract cat_key → clause_block(s) from analysis JSON.

    Returns dict of {cat_key: clause_block_or_list}
    """
    results = {}

    section_keys = [
        "administrative_and_commercial_terms",
        "technical_and_performance_terms",
        "legal_risk_and_enforcement",
        "regulatory_and_compliance_terms",
        "data_technology_and_deliverables",
    ]

    for section_key in section_keys:
        section_data = analysis.get(section_key, {})
        if not section_data or not isinstance(section_data, dict):
            continue

        for display_name, clause_data in section_data.items():
            if clause_data is None:
                continue

            # Look up cat_key from display_name
            cat_key = SECTION_KEY_TO_CATS.get(display_name)
            if not cat_key:
                # Try fuzzy match
                for label, key in SECTION_KEY_TO_CATS.items():
                    if display_name.lower().startswith(label.lower()[:30]):
                        cat_key = key
                        break

            if not cat_key:
                logger.warning(f"  No cat_key found for display name: {display_name}")
                continue

            results[cat_key] = clause_data

    return results


def write_analysis_to_excel(builder: ExcelTemplateBuilder, analysis: dict, contract_file: str):
    """Write a full analysis to the Excel workbook."""
    clause_blocks = extract_clause_blocks(analysis)

    written = 0
    for cat_key, clause_data in clause_blocks.items():
        if isinstance(clause_data, list):
            if len(clause_data) == 1:
                success = builder.update_contract_category(cat_key, clause_data[0], contract_file)
            else:
                success = builder.update_contract_category_multi(cat_key, clause_data, contract_file)
        elif isinstance(clause_data, dict):
            success = builder.update_contract_category(cat_key, clause_data, contract_file)
        else:
            continue

        if success:
            written += 1

    return written


def main():
    print("\n" + "=" * 60)
    print("  CR2A Batch Excel Generation")
    print("=" * 60)

    # Group analyses by MSA directory
    dir_analyses = {}
    for json_file, (msa_dir, contract_pdf) in ANALYSIS_MAP.items():
        json_path = ANALYSES_DIR / json_file
        if not json_path.exists():
            print(f"  SKIP (not found): {json_file}")
            continue

        if msa_dir not in dir_analyses:
            dir_analyses[msa_dir] = []
        dir_analyses[msa_dir].append((json_path, contract_pdf))

    print(f"\nFound {sum(len(v) for v in dir_analyses.values())} analyses across {len(dir_analyses)} directories\n")

    for msa_dir, analyses in dir_analyses.items():
        full_dir = MSA_ROOT / msa_dir
        print(f"\n{'='*60}")
        print(f"  {msa_dir}")
        print(f"{'='*60}")

        if not full_dir.exists():
            print(f"  ERROR: Directory not found: {full_dir}")
            continue

        # Get all contract files in this directory
        contract_files = [pdf for _, pdf in analyses]

        # Initialize workbook
        builder = ExcelTemplateBuilder(full_dir, contract_files)
        try:
            excel_path = builder.initialize_workbook()
            print(f"  Workbook: {excel_path}")
        except Exception as e:
            print(f"  ERROR initializing workbook: {e}")
            continue

        # Write each analysis
        for json_path, contract_pdf in analyses:
            print(f"\n  Processing: {json_path.name} -> {contract_pdf}")
            try:
                analysis = load_analysis(json_path)
                written = write_analysis_to_excel(builder, analysis, contract_pdf)
                print(f"  Written {written} categories to Excel")
            except Exception as e:
                print(f"  ERROR: {e}")
                logger.error("Failed to process %s", json_path, exc_info=True)

    print(f"\n{'='*60}")
    print("  Done!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
