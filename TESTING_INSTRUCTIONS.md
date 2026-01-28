# Testing Instructions

## What Was Fixed

Three main issues have been resolved:

1. **Section 8 completely removed** - No Section VIII exists anywhere in the system
2. **AI filters by risk** - The AI only includes moderate+ risk clauses during analysis
3. **Renderer outputs everything** - The PDF displays all data from the JSON without filtering

## How to Test

### Run a New Analysis

**Using the GUI:**
```
python main.py
```
- Drag and drop a contract PDF
- Click "Start Analysis"
- Save the results

**Using the CLI:**
```
python run_api_mode.py "Contract #1.pdf"
```

### What to Look For in the Results

**In the JSON file:**
- Should only have 7 top-level sections (I-VII)
- No `final_analysis` field should exist at all
- Sections II-VII should only contain clauses with moderate or higher risk
- Each clause should have meaningful content in at least one of:
  - Risk Triggers Identified
  - Harmful Language / Policy Conflicts
  - Redline Recommendations

**In the PDF file:**
- Section I (Contract Overview) should display all 8 fields with data
- Sections II-VI should show complete clause information for all items in the JSON
- Section VII (Supplemental Operational Risks) may be empty if none identified
- Section VIII should NOT exist at all - the PDF should end at Section VII
- All data from the JSON should appear in the PDF

## Comparison: Before vs After

### Before:
- ❌ Section VIII appeared in output
- ❌ PDF showed only headers, no clause details
- ❌ Renderer was filtering data (incorrectly)
- ❌ Key mismatches prevented data from displaying

### After:
- ✅ Section VIII completely removed from all files
- ✅ PDF shows full clause details for everything in JSON
- ✅ AI filters during analysis (not renderer)
- ✅ Renderer outputs everything from JSON
- ✅ All key names properly matched

## Expected Behavior

### Analysis Phase (AI):
- Analyzes contract text
- Identifies clauses with moderate or higher risk
- Only includes those clauses in the JSON output
- Populates sections I-VII only

### Rendering Phase (PDF):
- Reads the JSON file
- Outputs all data to PDF
- No filtering or risk assessment
- Displays sections I-VII as they appear in JSON

## If You Encounter Issues

1. **Section VIII appears:**
   - This should not happen - Section VIII code has been completely removed
   - Check that you're using the updated files

2. **PDF missing data that's in JSON:**
   - Verify the JSON structure matches the schema
   - Check that key names are correct

3. **Too many low-risk clauses:**
   - The AI should be filtering these during analysis
   - Check the AI instructions in `openai_client.py`

4. **JSON has final_analysis field:**
   - This should not happen with the updated schema
   - The AI should not be generating this field

## Files to Review

- `renderer.py` - Rendering logic (no Section VIII code)
- `openai_client.py` - AI instructions (sections I-VII only)
- `output_schemas_v1.json` - JSON schema (7 sections)
- `validation_rules_v1.json` - Validation rules (7 sections)
- `contract_analysis_client.py` - Client validation (7 sections)
