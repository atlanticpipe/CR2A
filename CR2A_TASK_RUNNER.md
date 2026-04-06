# CR2A Task Runner

## Configuration

```
CONTRACT_FOLDER = "F:\APS Drive\Operations\Bids\4- Piggyback & Service Agreements\MSA Contracts\TOHO Water Authority"

CR2A_ROOT = c:\Users\mcarroll\OneDrive - Atlantic Pipe Services, LLC\Documents\CR2A
```

## Rules

- Stay inside `CONTRACT_FOLDER`. Do not read, write, or reference any file outside this exact path. No parent directories, no sibling folders. Reading CR2A_ROOT for schemas/patterns/templates is the only exception.
- Scan metadata first. Before reading file contents, list the folder and check file names/extensions/sizes to identify relevant contracts (`.pdf`, `.docx`). Skip non-contract files unless a task specifically requires them.
- Save all outputs to `CONTRACT_FOLDER/.cr2a/`. Create it if it doesn't exist.
- Use CR2A schema v1.0.0 for all JSON outputs (`config/output_schemas_v1.json` for contract analysis, `config/bid_checklist_schema_v1.json` for bid review).
- One JSON file per contract in `.cr2a/analyses/`, named by sanitized contract filename.
- If a task's output already exists and is current, skip it and report as complete.

---

## Tasks

### Phase 1: Document Preparation

- [x] 1. Scan & inventory contract folder
  - List all files in `CONTRACT_FOLDER` (recursive, one level deep only)
  - For each file report: filename, extension, size, contract-document likelihood based on name/extension
  - Save inventory to `.cr2a/inventory.json`
  - Print summary table of findings
  - _Output: `.cr2a/inventory.json`_

- [x] 2. Extract text from contract documents
  - Read `.cr2a/inventory.json` for the file list (or scan if inventory missing)
  - Extract full text from each `.pdf` and `.docx` contract file only
  - Save each to `.cr2a/<sanitized_filename>.txt`
  - Save manifest to `.cr2a/extraction_manifest.json` with status, char count, page count per file
  - _Requires: Task 1_
  - _Output: `.cr2a/*.txt`, `.cr2a/extraction_manifest.json`_

- [x] 3. Convert contracts to AI-optimized markdown
  - Load each `.cr2a/<contract>.txt`
  - Detect section/article hierarchy (`ARTICLE 1`, `Section 3.2`, `1.01`, etc.) and convert to markdown headings (`##`, `###`, `####`) preserving original numbering
  - Insert page boundary markers: `---` + `<!-- Page N -->` at each page break
  - Convert tabular data (bid schedules, unit price tables, insurance matrices) to markdown tables; use code blocks when alignment is ambiguous
  - Clean OCR artifacts: remove repeated headers/footers, fix broken hyphenation, collapse whitespace, fix obvious OCR errors
  - Tag document zones with HTML comments: `<!-- COVER PAGE -->`, `<!-- TABLE OF CONTENTS -->`, `<!-- GENERAL CONDITIONS -->`, `<!-- SPECIAL CONDITIONS -->`, `<!-- SUPPLEMENTAL CONDITIONS -->`, `<!-- TECHNICAL SPECIFICATIONS -->`, `<!-- BID SCHEDULE / PRICING -->`, `<!-- EXHIBITS / ATTACHMENTS -->`, `<!-- AMENDMENTS / ADDENDA -->`
  - Normalize legal cross-references into consistent format
  - Flag unstructurable passages with `<!-- UNSTRUCTURED: reason -->`
  - Never invent structure not present in the original; never drop content
  - Page numbers must match original PDF (1-based)
  - Save to `.cr2a/markdown/<contract_name>.md`
  - Update `.cr2a/extraction_manifest.json` with markdown status, section count, detected zones
  - _Requires: Task 2_
  - _Output: `.cr2a/markdown/*.md`_

### Phase 2: Analysis

- [x] 4. Full contract analysis (all 60+ clause categories)
  - Load markdown from `.cr2a/markdown/` (fall back to `.cr2a/*.txt`)
  - For each contract, analyze all clause categories across: Section II Administrative & Commercial (16), Section III Technical & Performance (17), Section IV Legal Risk & Enforcement (13), Section V Regulatory & Compliance (8), Section VI Data Technology & Deliverables (6), Section VII Supplemental Operational Risks (up to 9), Section VIII Final Analysis
  - Each clause produces a ClauseBlock: `{ "Clause Location", "Clause Summary", "Clause Page", "Redline Recommendations": [{"action": "insert|replace|delete", "text": "..."}], "Harmful Language / Policy Conflicts": ["..."] }`
  - Include `contract_overview`: Project Title, Solicitation No., Owner, Contractor, Scope, General Risk Level, Bid Model, Notes
  - Assemble per `CR2A_ROOT/config/output_schemas_v1.json`
  - Save each to `.cr2a/analyses/<contract_name>.json`
  - _Requires: Task 3_
  - _Output: `.cr2a/analyses/*.json`_

- [x] 5. Bid specification review checklist
  - Load markdown from `.cr2a/markdown/` (fall back to `.cr2a/*.txt`)
  - Extract per `CR2A_ROOT/config/bid_checklist_schema_v1.json`: Project Info (name, owner, bid date, estimator, location), Standard Contract Items (pre-bid, submission format, bid bond, P&P bonds, contract time, LDs, warranty, license, insurance, DBE goals, hours, subcontracting, funding, certified payroll, retainage, safety, qualifications), Site Conditions (access, restoration, bypass, traffic, disposal, hydrant meter), Cleaning (method, passes, notifications), CCTV (NASSCO, format, notifications), CIPP (all sub-items), Manhole Rehab (all sub-items)
  - Each item includes: `value`, `location`, `confidence`, `page`
  - Save to `.cr2a/analyses/<contract_name>_bid_review.json`
  - _Requires: Task 3_
  - _Output: `.cr2a/analyses/*_bid_review.json`_

- [x] 6. Price & escalation cross-contract comparison
  - Load all analysis JSONs from `.cr2a/analyses/`
  - Extract and compare across contracts: Price Escalation Clauses (index type: PPI/CPI/fixed %, caps, timing, notice periods), Fuel Price Adjustment (surcharge mechanisms, diesel index, caps), Contract Term & Renewals (duration, options, auto vs mutual), Retainage & Payment Terms (net days, retainage %, release conditions), Change Order Provisions (markup, thresholds, time limits)
  - Build comparison matrix: contracts as columns, escalation features as rows
  - Flag: no escalation mechanism, caps below inflation, unfavorable payment terms (net 45+, high retainage), missing fuel adjustment
  - Produce per-contract recommendations
  - Save to `.cr2a/analyses/price_escalation_comparison.json`
  - _Requires: Task 4_
  - _Output: `.cr2a/analyses/price_escalation_comparison.json`_

### Phase 3: Deliverables

- [x] 7. Generate Excel workbook
  - Load all analysis JSONs from `.cr2a/analyses/`
  - Follow template structure from `CR2A_ROOT/src/excel_template_builder.py`
  - One worksheet per contract with all clause categories: Location, Summary, Redline Recommendations, Policy Conflicts
  - Include contract overview on each sheet
  - Add Bid Review worksheet per contract if bid review results exist
  - Save to `.cr2a/CR2A_Analysis.xlsx`
  - _Requires: Task 4 and/or Task 5_
  - _Output: `.cr2a/CR2A_Analysis.xlsx`_

- [x] 8. Risk summary report
  - Load all analysis JSONs from `.cr2a/analyses/`
  - Count clauses with Redline Recommendations by section
  - Count Harmful Language / Policy Conflicts by section
  - General Risk Level distribution across contracts
  - Top 10 most common risk findings
  - Per-contract risk scores and portfolio-wide trends
  - Save to `.cr2a/analyses/risk_summary.json`
  - _Requires: Task 4_
  - _Output: `.cr2a/analyses/risk_summary.json`_

### On-Demand

- [ ] 9. Single-category deep dive: `CATEGORY = <specify category>`
  - Load markdown from `.cr2a/markdown/` for all contracts
  - For the specified category only, extract with full clause text quotes
  - Compare provisions across all contracts in the folder
  - Highlight most and least favorable terms
  - Valid categories: any from Sections II-VI (e.g., "Indemnification, Defense & Hold Harmless Provisions")
  - Save to `.cr2a/analyses/deep_dive_<category>.json`
  - _Requires: Task 3_
  - _Output: `.cr2a/analyses/deep_dive_<category>.json`_

- [ ] 10. Run all (Tasks 1-8)
  - Execute Tasks 1 through 8 in sequence
  - Skip any task whose output already exists and is current
  - Report progress after each task completes
