# Project Structure

## Essential Files

### Executable
```
dist/
└── ContractAnalysisCLI.exe    # Standalone Windows executable (42.5 MB)
```

### Source Code
```
contract_analysis_cli.py       # Main CLI application
extract.py                     # PDF/DOCX text extraction with OCR
openai_client.py              # OpenAI API integration
validator.py                   # JSON schema validation
```

### Data Files
```
output_schemas_v1.json        # Output schema definition
validation_rules_v1.json      # Company-specific validation rules
```

### Build & Config
```
build_cli.bat                 # PyInstaller build script
config_template.txt           # API key configuration template
requirements_simple.txt       # Python dependencies
```

### Documentation
```
README.md                     # Main documentation
QUICK_START.txt              # Quick start guide
```

## How It Works

1. **User Input:** Drag PDF/DOCX onto `ContractAnalysisCLI.exe`
2. **Text Extraction:** `extract.py` extracts text (with OCR if needed)
3. **AI Analysis:** `openai_client.py` sends to OpenAI API
4. **Validation:** `validator.py` validates against schema
5. **Output:** Saves JSON file with analysis results

## Building

```bash
# Install dependencies
pip install -r requirements_simple.txt

# Build executable
build_cli.bat

# Output: dist/ContractAnalysisCLI.exe
```

## Distribution

**Minimal Package:**
- `dist/ContractAnalysisCLI.exe`
- `config.txt` (with API key)

**With Documentation:**
- Add `QUICK_START.txt`
- Add `README.md`

## File Sizes

- ContractAnalysisCLI.exe: 42.5 MB
- Source files: ~50 KB total
- Data files: ~20 KB total
