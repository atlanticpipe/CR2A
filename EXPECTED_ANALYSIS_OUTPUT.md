# Expected Analysis Output Structure

## Overview

The CR2A application now displays a comprehensive 7-section analysis structure. Each section shows ALL clause categories, marking those not found in the contract with "⚠️ Not found in contract".

## Implementation Approach

**Problem**: Asking OpenAI to return ALL 69+ categories (including empty ones) causes JSON formatting errors and token limit issues.

**Solution**: Post-processing schema completion
1. **OpenAI Analysis**: OpenAI returns ONLY the clause categories actually found in the contract (reliable, no JSON errors)
2. **Schema Completion**: The `SchemaCompleter` class adds missing categories marked as "Not found" (guaranteed correct)
3. **UI Display**: The UI displays all categories, with "Not found" clauses shown in a gray box

This approach ensures:
- ✓ Reliable JSON responses from OpenAI (no formatting errors)
- ✓ Complete category coverage (all 69+ categories displayed)
- ✓ Clear indication of what's missing from the contract

## Implementation Files

- **src/schema_completer.py**: Adds missing categories with "Not found" markers
- **src/result_parser.py**: Calls schema completer after parsing OpenAI response
- **src/structured_analysis_view.py**: Detects and displays "Not found" clauses
- **src/openai_fallback_client.py**: Instructs OpenAI to return only found clauses

## Section Structure

### Section I: Contract Overview
Always displayed with 8 fields:
- Project Title
- Solicitation No.
- Owner
- Contractor
- Scope
- General Risk Level
- Bid Model
- Notes

### Section II: Administrative & Commercial Terms (16 categories)
1. Contract Term, Renewal & Extensions
2. Bonding, Surety, & Insurance Obligations
3. Retainage, Progress Payments & Final Payment Terms
4. Pay-When-Paid, Pay-If-Paid, or Owner Payment Contingencies
5. Price Escalation Clauses (Labor, Materials, Fuel, Inflation Adjustments)
6. Fuel Price Adjustment / Fuel Cost Caps
7. Change Orders, Scope Adjustments & Modifications
8. Termination for Convenience (Owner/Agency Right to Terminate Without Cause)
9. Termination for Cause / Default by Contractor
10. Bid Protest Procedures & Claims of Improper Award
11. Bid Tabulation, Competition & Award Process Requirements
12. Contractor Qualification, Licensing & Certification Requirements
13. Release Orders, Task Orders & Work Authorization Protocols
14. Assignment & Novation Restrictions (Transfer of Contract Rights)
15. Audit Rights, Recordkeeping & Document Retention Obligations
16. Notice Requirements & Claim Timeframes

### Section III: Technical & Performance Terms (17 categories)
1. Scope of Work (Work Inclusions, Exclusions & Defined Deliverables)
2. Performance Schedule, Time for Completion & Critical Path Obligations
3. Delays of Any Kind (Force Majeure, Acts of God, Weather, Owner-Caused, Unforeseen Events)
4. Suspension of Work, Work Stoppages & Agency Directives
5. Submittals, Documentation & Approval Requirements
6. Emergency & Contingency Work Obligations
7. Permits, Licensing & Regulatory Approvals for Work
8. Warranty, Guarantee & Defects Liability Periods
9. Use of APS Tools, Equipment, Materials or Supplies
10. Owner-Supplied Support, Utilities & Site Access Provisions
11. Field Ticket, Daily Work Log & Documentation Requirements
12. Mobilization & Demobilization Provisions
13. Utility Coordination, Locate Risk & Conflict Avoidance
14. Delivery Deadlines, Milestone Dates, Substantial & Final Completion Standards
15. Punch List, Closeout Procedures & Acceptance of Work
16. Worksite Coordination, Access Restrictions & Sequencing Obligations
17. Deliverables, Digital Submissions & Documentation Standards

### Section IV: Legal Risk & Enforcement (13 categories)
1. Indemnification, Defense & Hold Harmless Provisions
2. Duty to Defend vs. Indemnify Scope Clarifications
3. Limitations of Liability, Damage Caps & Waivers of Consequential Damages
4. Insurance Coverage, Additional Insured & Waiver of Subrogation Clauses
5. Dispute Resolution (Mediation, Arbitration, Litigation)
6. Flow-Down Clauses (Prime-to-Subcontract Risk Pass-Through)
7. Subcontracting Restrictions, Approval & Substitution Requirements
8. Background Screening, Security Clearance & Worker Eligibility Requirements
9. Safety Standards, OSHA Compliance & Site-Specific Safety Obligations
10. Site Conditions, Differing Site Conditions & Changed Circumstances Clauses
11. Environmental Hazards, Waste Disposal & Hazardous Materials Provisions
12. Conflicting Documents / Order of Precedence Clauses
13. Setoff & Withholding Rights (Owner's Right to Deduct or Withhold Payment)

### Section V: Regulatory & Compliance Terms (8 categories)
1. Certified Payroll, Recordkeeping & Reporting Obligations
2. Prevailing Wage, Davis-Bacon & Federal/State Wage Compliance
3. EEO, Non-Discrimination, MWBE/DBE Participation Requirements
4. Anti-Lobbying / Cone of Silence Provisions
5. Apprenticeship, Training & Workforce Development Requirements
6. Immigration / E-Verify Compliance Obligations
7. Worker Classification & Independent Contractor Restrictions
8. Drug-Free Workplace Programs & Substance Testing Requirements

### Section VI: Data, Technology & Deliverables (7 categories)
1. Data Ownership, Access & Rights to Digital Deliverables
2. AI / Technology Use Restrictions (Automation, Digital Tools, Proprietary Systems)
3. Digital Surveillance, GIS-Tagged Deliverables & Monitoring Requirements
4. GIS, Digital Workflow Integration & Electronic Submittals
5. Confidentiality, Data Security & Records Retention Obligations
6. Intellectual Property, Licensing & Ownership of Work Product
7. Cybersecurity Standards, Breach Notification & IT System Use Policies

### Section VII: Supplemental Operational Risks
Up to 9 additional risk areas not covered in Sections II-VI. These are contract-specific risks identified by the AI.

## Display Behavior

### Found Clauses
- Show full details with blue border
- Include:
  - Clause Language (verbatim text)
  - Clause Summary
  - Risk Triggers Identified
  - Flow-Down Obligations
  - Redline Recommendations
  - Harmful Language / Policy Conflicts

### Not Found Clauses
- Show gray box with "⚠️ Not found in contract"
- Collapsed by default
- Helps identify gaps in contract coverage

## Total Categories

- Section I: 8 fields (always present)
- Section II: 16 categories
- Section III: 17 categories
- Section IV: 13 categories
- Section V: 8 categories
- Section VI: 7 categories
- Section VII: 0-9 categories (variable)

**Total: 69+ clause categories across all sections**

## Benefits

1. **Comprehensive Coverage**: See what's in the contract AND what's missing
2. **Gap Analysis**: Quickly identify missing standard clauses
3. **Risk Assessment**: Understand what protections are absent
4. **Negotiation Tool**: Know what to request in contract negotiations

## Troubleshooting

### If sections are missing:
- Check that OpenAI returned the sections in the JSON
- Verify the JSON is valid (no parsing errors)
- Check application logs for errors

### If only a few items show per section:
- This is expected! OpenAI only returns found clauses
- The SchemaCompleter automatically adds missing categories
- Missing categories will show as "⚠️ Not found in contract"

### If "All passes failed" error:
- Check API key is valid
- Verify network connection
- Check application logs for specific error details

## Testing

Run `python test_schema_completion.py` to verify:
- Missing categories are added correctly
- Missing categories are marked as "Not found"
- Existing categories are preserved
- All section counts match expected values (16, 17, 13, 8, 7)
