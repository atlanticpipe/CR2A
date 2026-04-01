"""
Batch text extraction for all MSA contract PDFs.
Uses CR2A's ContractUploader to extract text, saves to .txt files for analysis.
"""
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.contract_uploader import ContractUploader

MSA_ROOT = Path(r"F:\APS Drive\Operations\Bids\4- Piggyback & Service Agreements\MSA Contracts")

# All contract PDFs to process (relative to MSA_ROOT)
CONTRACT_FILES = [
    # Gainesville
    r"Gainesville, City of (GCU)\2024-083_Atlantic_Pipe_Contract Fully Executed GRU.pdf",
    # Okaloosa
    r"Okaloosa County\79-24 Gravity Sewer Rehab\C25_4079_WS- Okaloosa Contract.pdf",
    # Orlando
    r"Orlando, City of\IFB 22-0161-3 EXPIRES 07.17.26 APS Executed.pdf",
    r"Orlando, City of\Amendment Two IFB22-0161-3.pdf",
    # Seminole County
    r"Seminole County\IFB 604819-24 LNF - Storm TV\IFB-604819-24 LNF_ CONTRACT APS_Signed.pdf",
    r"Seminole County\IFB-604150-21 LNF\IFB-604150-21_tc (Atlatic Pipe Services)_Original Contract.pdf",
    # South Daytona
    r"South Daytona\23-B-005 Sewer Rehab Services\Agreement with Atlantic Pipe Services, LLC - April 2023.pdf",
    r"South Daytona\23-B-005 Sewer Rehab Services\Contract Amendment - Storm.pdf",
    r"South Daytona\23-B-005 Sewer Rehab Services\Contract Renewal with Atlantic Pipe Services LLC.pdf",
    r"South Daytona\23-B-005 Sewer Rehab Services\Renewal Option Letter- APS 1.12.26.pdf",
    r"South Daytona\23-B-005 Sewer Rehab Services\APS Renewal 2.4.26 South Daytona.pdf",
    # St. Johns County
    r"St. Johns County\21-05 Countywide Pipe & Manhole Lining\21-05 CA #01 CTR REN #01 - EXECUTED - APS.pdf",
    r"St. Johns County\21-05 Countywide Pipe & Manhole Lining\21-05 CA#02 CTR REN#02 - APS_ FY 23 CONTRACT FOR USE.pdf",
    r"St. Johns County\21-05 Countywide Pipe & Manhole Lining\21-05 CA#04 CTR REN#04 - EXECUTED - APS.pdf",
    r"St. Johns County\21-05 Countywide Pipe & Manhole Lining\21-05 CA#05 CTR REN#04 - APS FINAL EXTENSION.pdf",
    r"St. Johns County\21-05 Countywide Pipe & Manhole Lining\St John's County Contract Renewal 2025.pdf",
    # TOHO Water Authority
    r"TOHO Water Authority\20-133 Gravity Sewer and Cleaning Inspection\20-133 APS Executed ACTUAL.pdf",
    r"TOHO Water Authority\20-133 Gravity Sewer and Cleaning Inspection\20-133 Updated and Signed.pdf",
    # The Villages
    r"The Villages\D1 24P-007 Atlantic Pipe Services LLC FE.pdf",
    r"The Villages\D2 24P-007 Atlantic Pipe Services LLC FE.pdf",
    r"The Villages\D3 24P-007 Atlantic Pipe Services LLC FE.pdf",
    r"The Villages\D4 24P-007 Atlantic Pipe Services LLC FE.pdf",
    r"The Villages\VCCDD 24P-007 Atlantic Pipe Services LLC FE.pdf",
    # Volusia
    r"Volusia\22-B-112LS Sewer Main Jet Vac Clean and Inspect\PUR - Master Agreements _ 12439A - 1 _   _ ATLANTIC PIPE SERVICES LLC _ 6_24_2025 _ VS8930.pdf",
    r"Volusia\22-B-112LS Sewer Main Jet Vac Clean and Inspect\Contract Renewal 05.27.2025.pdf",
    r"Volusia\23-B-105LS Coatings for Manhole and Wet Well\PUR - Master Agreements _ 12503 - 2 _   _ ATLANTIC PIPE SERVICES LLC _ 8_1_2023 _ VS8930.pdf",
]

OUTPUT_DIR = Path(__file__).parent / "extracted_texts"
OUTPUT_DIR.mkdir(exist_ok=True)

def main():
    uploader = ContractUploader()
    results = {}

    for rel_path in CONTRACT_FILES:
        full_path = MSA_ROOT / rel_path
        if not full_path.exists():
            print(f"SKIP (not found): {rel_path}")
            results[rel_path] = {"status": "not_found"}
            continue

        print(f"\nExtracting: {rel_path}")
        try:
            # Validate
            is_valid, err = uploader.validate_format(str(full_path))
            if not is_valid:
                print(f"  INVALID: {err}")
                results[rel_path] = {"status": "invalid", "error": err}
                continue

            # Get file info
            file_info = uploader.get_file_info(str(full_path))
            print(f"  Size: {file_info.get('file_size_bytes', 0) / 1024:.1f} KB, Pages: {file_info.get('page_count', '?')}")

            # Extract text
            text = uploader.extract_text(str(full_path))
            if not text or not text.strip():
                print(f"  WARNING: No text extracted")
                results[rel_path] = {"status": "empty", "file_info": file_info}
                continue

            # Save extracted text
            safe_name = rel_path.replace("\\", "__").replace("/", "__").replace(" ", "_")
            safe_name = safe_name.replace(".pdf", ".txt").replace(".PDF", ".txt")
            out_path = OUTPUT_DIR / safe_name
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)

            char_count = len(text)
            print(f"  OK: {char_count} chars -> {out_path.name}")
            results[rel_path] = {
                "status": "ok",
                "chars": char_count,
                "pages": file_info.get("page_count"),
                "output_file": str(out_path.name),
                "file_info": file_info,
            }

        except Exception as e:
            print(f"  ERROR: {e}")
            results[rel_path] = {"status": "error", "error": str(e)}

    # Save manifest
    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nManifest saved to: {manifest_path}")

    # Summary
    ok = sum(1 for r in results.values() if r["status"] == "ok")
    fail = len(results) - ok
    print(f"\nDone: {ok} extracted, {fail} failed/skipped out of {len(results)} total")

if __name__ == "__main__":
    main()
