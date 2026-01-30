# Contract Analysis CLI

AI-powered contract analysis tool with drag-and-drop interface for Windows.

## Features

- **Drag & Drop Interface** - Drop PDF or DOCX files onto the executable
- **AI Analysis** - Powered by OpenAI gpt-4o-mini
- **OCR Support** - Handles scanned PDFs (requires Tesseract & Poppler)
- **JSON Output** - Structured analysis data
- **Standalone** - No Python installation required (42.5 MB)

## Quick Start

### For End Users

1. **Get the executable:**
   - Download `dist/ContractAnalysisCLI.exe`

2. **Set up API key:**
   
   **Option A: Config File (Easiest for distribution)**
   - Create `config.txt` in the same folder as the .exe
   - Put your OpenAI API key on the first line:
     ```
     sk-your-api-key-here
     ```
   
   **Option B: Environment Variable**
   ```powershell
   [System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-your-key", "User")
   ```

3. **Use it:**
   - Drag a contract file onto `ContractAnalysisCLI.exe`
   - Wait for analysis (1-4 minutes)
   - Find `<filename>_analysis.json` in the same folder

### For Developers

1. **Install dependencies:**
   ```bash
   pip install -r requirements_simple.txt
   ```

2. **Run from source:**
   ```bash
   python contract_analysis_cli.py "contract.pdf"
   ```

3. **Build executable:**
   ```bash
   build_cli.bat
   ```

## Requirements

**Required:**
- Windows 10/11 (64-bit)
- OpenAI API key
- Internet connection

**Optional (for scanned PDFs):**
- Tesseract OCR v5.3.3+
- Poppler v24.08.0+

## Output

The tool generates a JSON file with:
- Contract overview
- Parties involved
- Financial terms
- Timeline and milestones
- Risk assessment
- Key clauses and provisions
- Recommendations

## Processing Times

| Document Type | Pages | Time |
|--------------|-------|------|
| Text PDF | 10 | ~1 min |
| Scanned PDF | 15 | 3-4 min |
| DOCX | 10 | ~1 min |

## Distribution

To share with others:

1. Copy `dist/ContractAnalysisCLI.exe`
2. Create `config.txt` with your API key
3. Share both files together
4. Users just drag and drop - no setup needed!

See `QUICK_START.txt` for detailed instructions.

## Project Structure

```
.
├── dist/
│   └── ContractAnalysisCLI.exe    # Standalone executable
├── contract_analysis_cli.py       # Main CLI script
├── extract.py                     # PDF/DOCX text extraction
├── openai_client.py              # OpenAI API integration
├── validator.py                   # JSON schema validation
├── output_schemas_v1.json        # Output schema definition
├── validation_rules_v1.json      # Validation rules
├── build_cli.bat                 # Build script
├── config_template.txt           # API key config template
├── requirements_simple.txt       # Python dependencies
├── QUICK_START.txt              # User guide
└── README.md                     # This file
```

## Troubleshooting

**"API key not found"**
- Create `config.txt` with your API key, or
- Set `OPENAI_API_KEY` environment variable

**"Authentication failed"**
- Check API key is correct
- Verify OpenAI account has credits

**Window closes immediately**
- Run from Command Prompt to see errors
- Check that config.txt exists and contains valid key

**"Tesseract not found" (scanned PDFs only)**
- Install Tesseract OCR
- Add to PATH: `C:\Program Files\Tesseract-OCR`

## Security Notes

⚠️ **Important:**
- The `config.txt` file contains your API key in plain text
- Only share with trusted users
- Use secure channels for distribution
- Set usage limits in OpenAI dashboard
- Monitor usage regularly

## Version

- **Version:** 1.0
- **Build Date:** January 28, 2026
- **Platform:** Windows 10/11 (64-bit)
- **Size:** 42.5 MB
- **AI Model:** OpenAI gpt-4o-mini

## License

See LICENSE file for details.
