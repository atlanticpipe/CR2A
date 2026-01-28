# How to Use the Contract Analysis Tool

**Status:** ✅ CLI Version Ready  
**Location:** `dist/ContractAnalysisCLI.exe`

---

## ✅ The Working Version

The **CLI (Command Line) version** is ready and working. This version doesn't have a GUI but works perfectly for analyzing contracts.

**File:** `dist/ContractAnalysisCLI.exe` (45.7 MB)

---

## 🚀 How to Use It

### Method 1: Drag and Drop (Easiest)

1. Find your contract file (PDF or DOCX)
2. Drag it onto `ContractAnalysisCLI.exe`
3. A console window opens showing progress
4. Wait 1-5 minutes for analysis
5. Check the output files in the same folder as your contract

### Method 2: Command Line

1. Open Command Prompt or PowerShell
2. Navigate to the folder with the .exe
3. Run:
   ```
   ContractAnalysisCLI.exe "path\to\your\contract.pdf"
   ```

### Method 3: From File Explorer

1. Double-click `ContractAnalysisCLI.exe`
2. When prompted, enter the path to your contract file
3. Press Enter and wait for analysis

---

## 📋 Before First Use

**Set your API key once:**

```powershell
.\set_api_key.ps1
```

Then restart your computer (or log out and back in).

---

## 📊 What You'll See

When you run the CLI version, you'll see:

```
======================================================================
CONTRACT ANALYSIS TOOL - API Mode
======================================================================

📄 Input file: Contract #1.pdf

📖 Step 1/4: Extracting text from document...
Standard extraction returned only 0 characters
Attempting OCR extraction (this may take a minute)...
Converting PDF to images for OCR...
Processing 15 pages with OCR...
✓ OCR extraction successful: 23522 characters

📋 Step 2/4: Loading schema and validation rules...
✓ Schema and rules loaded

🤖 Step 3/4: Analyzing contract with AI...
   (This may take 30-60 seconds...)
✓ AI analysis complete

✅ Step 4/4: Validating results...
✓ Validation passed

💾 JSON saved: Contract #1_analysis.json
📄 PDF saved: Contract #1_analysis.pdf

======================================================================
✅ ANALYSIS COMPLETE!
======================================================================
```

---

## 📁 Output Files

After analysis, you'll find two files in the same folder as your contract:

1. **`[filename]_analysis.json`** - Structured data (for integration)
2. **`[filename]_analysis.pdf`** - Professional report (for reading)

---

## ⚠️ About the GUI Version

The GUI version (`ContractAnalysisApp.exe`) has a PySimpleGUI compatibility issue. 

**Use the CLI version instead** - it has the same functionality and is actually easier to troubleshoot!

---

## 🆘 Troubleshooting

### "API key not configured"
```powershell
.\set_api_key.ps1
```
Then restart your computer.

### "Tesseract not found" (for scanned PDFs)
Install Tesseract OCR:
- Download: https://github.com/UB-Mannheim/tesseract/wiki
- Install and add to PATH
- See `OCR_SETUP_GUIDE.md` for details

### "Unable to get page count" (for scanned PDFs)
Install Poppler:
- Run: `.\install_poppler.ps1`
- Or see `OCR_SETUP_GUIDE.md` for manual installation

---

## 📦 Distribution

To give this to others:

**Share the `release_cli/` folder** which contains:
- `ContractAnalysisCLI.exe` - The application
- `USAGE.txt` - Quick instructions
- `README.txt` - Full documentation
- `API_KEY_SETUP.txt` - API key setup
- `OCR_SETUP_GUIDE.txt` - OCR installation

They just need to:
1. Set their API key
2. Run the .exe with a contract file
3. Done!

---

## ✅ Summary

**Working Version:** `dist/ContractAnalysisCLI.exe`

**Usage:**
- Drag and drop a contract onto the .exe, OR
- Run from command line: `ContractAnalysisCLI.exe "contract.pdf"`

**Requirements:**
- OpenAI API key (set once)
- Tesseract + Poppler (optional, for scanned PDFs)

**That's it! The CLI version works perfectly.**

---

**End of Guide**
