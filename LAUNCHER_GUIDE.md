# CR2A Launcher Guide

## Quick Start

### Running the GUI Application
```bash
run_cr2a.bat
```
This launches the PyQt5 desktop GUI application.

### Running the CLI Application
```bash
run_cli.bat contract.pdf
```
This runs the command-line interface for quick contract analysis.

## Prerequisites

1. **Virtual Environment**: Ensure `venv311` is set up with all dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. **OpenAI API Key**: Set your API key as an environment variable:
   ```bash
   set OPENAI_API_KEY=sk-your-key-here
   ```

3. **Optional - Tesseract OCR**: For scanned PDFs, install Tesseract OCR:
   - See `docs/guides/OCR_SETUP_GUIDE.md` for installation instructions

## File Structure

### Launchers
- `run_cr2a.bat` - Launch PyQt5 GUI application
- `run_cli.bat` - Launch CLI application (requires file argument)

### Source Files
- `src/qt_gui.py` - PyQt5 GUI application
- `src/cli_main.py` - CLI application

### Build Tools
- `build_tools/build.py` - Build system for creating executables (not yet configured for PyQt5)

## Supported File Formats

- **PDF** - Portable Document Format
- **DOCX** - Microsoft Word documents
- **TXT** - Plain text files
- **JSON** - Previously analyzed contracts (CLI only)

## Troubleshooting

### "OPENAI_API_KEY not set"
Set your API key:
```bash
set OPENAI_API_KEY=sk-your-key-here
```

### "File not found" (CLI)
Ensure you provide the full path or run from the correct directory:
```bash
run_cli.bat "C:\path\to\contract.pdf"
```

### PyQt5 Import Error
Install PyQt5:
```bash
pip install PyQt5>=5.15.0
```

### OCR Not Working
Install Tesseract OCR and Poppler - see `docs/guides/OCR_SETUP_GUIDE.md`

## Next Steps

- For detailed CLI usage: See `docs/guides/CLI_GUIDE.md`
- For building executables: See `docs/user/DISTRIBUTION_GUIDE.md`
- For development: See `docs/developer/DOCUMENTATION_INDEX.md`
