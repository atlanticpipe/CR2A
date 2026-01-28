# Contract Analysis Tool - Simplification Plan

## Goal
Remove installers and GUI complexity, leaving a simple drag-and-drop CLI executable that users can use directly in Windows File Explorer.

## Current State

### Files to Keep (Core Functionality)
- `run_api_mode.py` - CLI entry point (already perfect for this)
- `extract.py` - Text extraction
- `openai_client.py` - AI analysis
- `validator.py` - Result validation
- `renderer.py` - PDF generation
- `output_schemas_v1.json` - JSON schema
- `validation_rules_v1.json` - Validation rules
- `requirements_simple.txt` - Minimal dependencies (no GUI)
- `ContractAnalysisCLI.exe` - Already built CLI executable

### Files to Remove
- `build.bat` - GUI installer builder
- `build_installer.bat` - Windows installer builder
- `installers/` folder - NSIS installer scripts
- `release/` folder - GUI app releases
- `main.py` - GUI entry point
- `gui.py` - GUI code
- `contract_analysis_api.py` - API server (not needed)
- `contract_analysis_client.py` - API client (not needed)
- `requirements.txt` - Full dependencies (includes GUI)
- `requirements_api.txt` - API dependencies (not needed)
- `build_cli_version.bat` - Can be simplified
- `run_contract_analysis.bat` - Redundant with drag-and-drop

### Files to Keep (Documentation/Utilities)
- `README.md` - Update for CLI-only usage
- `set_api_key.bat` - Helpful utility
- `set_api_key.ps1` - Helpful utility
- `cleanup_repo.bat` - Useful for development
- `.gitignore` - Version control

## New Simplified Structure

```
CR2A/
├── ContractAnalysisCLI.exe          # Main executable (drag & drop target)
├── README.md                         # Updated usage instructions
├── SETUP_GUIDE.md                    # API key and OCR setup
├── set_api_key.bat                   # Quick API key setup
├── set_api_key.ps1                   # PowerShell version
│
├── src/                              # Source code (for developers)
│   ├── run_api_mode.py              # CLI entry point
│   ├── extract.py
│   ├── openai_client.py
│   ├── validator.py
│   ├── renderer.py
│   ├── output_schemas_v1.json
│   ├── validation_rules_v1.json
│   └── requirements.txt             # Minimal dependencies
│
├── build/                            # Build artifacts (gitignored)
├── dist/                             # Distribution (gitignored)
│
└── dev/                              # Development tools
    ├── build_cli.bat                # Simple build script
    └── cleanup.bat                  # Cleanup script
```

## Implementation Steps

### Phase 1: Cleanup (Remove Unnecessary Files)
1. Delete `installers/` folder
2. Delete `release/` folder
3. Delete `main.py` (GUI entry point)
4. Delete `gui.py` (GUI code)
5. Delete `contract_analysis_api.py`
6. Delete `contract_analysis_client.py`
7. Delete `build.bat` (GUI builder)
8. Delete `build_installer.bat`
9. Delete `run_contract_analysis.bat` (redundant)
10. Delete `requirements.txt` and `requirements_api.txt`
11. Rename `requirements_simple.txt` to `requirements.txt`

### Phase 2: Reorganize Structure
1. Create `src/` folder
2. Move Python source files to `src/`:
   - `run_api_mode.py`
   - `extract.py`
   - `openai_client.py`
   - `validator.py`
   - `renderer.py`
   - `output_schemas_v1.json`
   - `validation_rules_v1.json`
3. Create `dev/` folder
4. Move/create development tools in `dev/`:
   - Simplified `build_cli.bat`
   - `cleanup.bat`

### Phase 3: Update Build Script
Create a simple `dev/build_cli.bat`:
```batch
@echo off
echo Building Contract Analysis CLI...
cd ..
python -m PyInstaller ^
    --name="ContractAnalysisCLI" ^
    --onefile ^
    --console ^
    --add-data="src/output_schemas_v1.json;." ^
    --add-data="src/validation_rules_v1.json;." ^
    --hidden-import=pytesseract ^
    --hidden-import=pdf2image ^
    --hidden-import=PIL ^
    --hidden-import=pdfminer ^
    --hidden-import=docx ^
    --hidden-import=reportlab ^
    --hidden-import=openai ^
    --hidden-import=jsonschema ^
    src/run_api_mode.py

if exist "dist\ContractAnalysisCLI.exe" (
    echo Build successful!
    echo Executable: dist\ContractAnalysisCLI.exe
) else (
    echo Build failed!
)
pause
```

### Phase 4: Update Documentation

#### New README.md Structure:
```markdown
# Contract Analysis Tool

Simple drag-and-drop contract analysis powered by AI.

## Quick Start

1. **Set your OpenAI API key** (one-time setup)
   - Double-click `set_api_key.bat`
   - Enter your API key when prompted
   - Get a key from: https://platform.openai.com/api-keys

2. **Analyze a contract**
   - Drag a PDF or DOCX file onto `ContractAnalysisCLI.exe`
   - Wait for analysis to complete (30-60 seconds)
   - Find results in the same folder as your contract:
     - `[filename]_analysis.json` - Structured data
     - `[filename]_analysis.pdf` - Professional report

## Requirements

- Windows 10/11
- OpenAI API key (required)
- Tesseract OCR (optional, for scanned PDFs)

## Usage Examples

**Drag and Drop:**
- Drag `Contract.pdf` onto `ContractAnalysisCLI.exe`

**Command Line:**
```
ContractAnalysisCLI.exe "C:\Documents\Contract.pdf"
```

## Troubleshooting

- **API Key Error**: Run `set_api_key.bat` to configure
- **OCR Fails**: Install Tesseract (see SETUP_GUIDE.md)
- **Check Logs**: Look for `error.log` in the same folder

## For Developers

Source code is in the `src/` folder.

To rebuild:
```
cd dev
build_cli.bat
```
```

#### New SETUP_GUIDE.md:
```markdown
# Setup Guide

## 1. OpenAI API Key (Required)

### Quick Setup
1. Double-click `set_api_key.bat`
2. Enter your API key
3. Restart any open command prompts

### Manual Setup
1. Get API key from: https://platform.openai.com/api-keys
2. Set environment variable:
   - Windows: `setx OPENAI_API_KEY "sk-your-key-here"`
   - PowerShell: Use `set_api_key.ps1`

## 2. Tesseract OCR (Optional)

Only needed for scanned PDFs.

### Installation
1. Download: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to default location
3. Add to PATH or install will do it automatically

### Verification
```
tesseract --version
```

## 3. Poppler (Optional)

Only needed for scanned PDFs.

### Installation
1. Download: https://github.com/oschwartz10612/poppler-windows/releases
2. Extract to `C:\Program Files\poppler`
3. Add `C:\Program Files\poppler\Library\bin` to PATH

### Verification
```
pdftoppm -v
```
```

### Phase 5: Update .gitignore
```
# Build artifacts
build/
dist/
*.spec

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Logs
*.log
error.log

# Test files
Contract*.pdf
Contract*_analysis.json
Contract*_analysis.pdf

# OS
.DS_Store
Thumbs.db
```

## Benefits of This Approach

### For Users
1. **Simple**: Just drag and drop files onto the .exe
2. **No Installation**: Single executable, no installer needed
3. **Portable**: Copy the .exe anywhere and it works
4. **Fast**: No GUI overhead, direct to analysis
5. **Visible Progress**: Console shows what's happening

### For Developers
1. **Clean Structure**: Clear separation of source and distribution
2. **Easy to Build**: Single simple build script
3. **Easy to Maintain**: No GUI complexity
4. **Easy to Debug**: Console output shows everything
5. **Smaller Codebase**: Removed ~40% of files

### For Distribution
1. **Single File**: Just distribute `ContractAnalysisCLI.exe`
2. **No Dependencies**: Everything bundled in the .exe
3. **No Installer**: Users just copy and run
4. **Easy Updates**: Replace the .exe file

## Migration Path

### For Existing Users
1. They already have `ContractAnalysisCLI.exe` - it works!
2. Just remove the GUI version
3. Update documentation

### For New Users
1. Download `ContractAnalysisCLI.exe`
2. Run `set_api_key.bat` once
3. Start dragging and dropping contracts

## File Size Comparison

**Before (with GUI):**
- ContractAnalysisApp.exe: ~80-100 MB
- Installer: ~100-120 MB
- Total distribution: ~200 MB

**After (CLI only):**
- ContractAnalysisCLI.exe: ~60-70 MB
- No installer needed
- Total distribution: ~70 MB

## Testing Plan

1. **Build Test**
   - Run `dev/build_cli.bat`
   - Verify .exe is created
   - Check file size is reasonable

2. **Functionality Test**
   - Drag a PDF onto the .exe
   - Verify analysis completes
   - Check JSON and PDF outputs

3. **Error Handling Test**
   - Test without API key (should show clear error)
   - Test with invalid file (should show clear error)
   - Test with scanned PDF without OCR (should handle gracefully)

4. **Documentation Test**
   - Follow README.md from scratch
   - Verify all links work
   - Ensure instructions are clear

## Rollout Plan

1. **Backup Current State**
   - Commit all current changes
   - Tag as `v1.0-gui-version`

2. **Implement Changes**
   - Execute Phase 1-5 above
   - Test thoroughly

3. **Update Repository**
   - Commit simplified version
   - Tag as `v2.0-cli-only`
   - Update GitHub README

4. **Notify Users**
   - Announce simplification
   - Provide migration guide
   - Highlight benefits

## Future Enhancements

Once simplified, easy to add:
1. **Batch Processing**: Analyze multiple files at once
2. **Watch Folder**: Auto-analyze files dropped in a folder
3. **Configuration File**: Customize analysis parameters
4. **Output Templates**: Different report formats
5. **Cloud Integration**: Save to cloud storage

All without GUI complexity!
