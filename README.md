# CR2A - Contract Review & Analysis

AI-powered contract analysis and Q&A system using OpenAI.

## 🚀 Quick Start

### CLI Version (Recommended - No GUI Required)

```bash
# 1. Set your OpenAI API key
setx OPENAI_API_KEY "sk-your-key-here"

# 2. Analyze a contract
python src/cli_main.py test_contract.txt

# 3. Ask questions interactively
❓ Your question: Who are the parties?
❓ Your question: What is the contract value?
❓ Your question: exit
```

### GUI Version (Requires tkinter)

```bash
python src/main.py
```

## 📋 Features

- ✅ **Contract Analysis** - Extracts parties, terms, dates, risks, obligations
- ✅ **Natural Language Q&A** - Ask questions about analyzed contracts
- ✅ **Multiple Formats** - Supports PDF, DOCX, TXT
- ✅ **OCR Support** - Handles scanned/image-based PDFs
- ✅ **CLI & GUI** - Choose your interface
- ✅ **JSON Export/Import** - Save and load analysis results

## 📦 Installation

```bash
# Clone the repository
git clone <repository-url>
cd CR2A

# Install dependencies
pip install -r requirements.txt

# Set OpenAI API key
setx OPENAI_API_KEY "sk-your-key-here"
```

## 📖 Documentation

### Quick Guides

- **[Final Summary](docs/guides/FINAL_SUMMARY.md)** - Complete overview and solution
- **[CLI Guide](docs/guides/CLI_GUIDE.md)** - Command-line interface usage
- **[Quick Reference](docs/guides/QUICK_REFERENCE.md)** - Quick commands

### Detailed Guides

- **[Testing Guide](docs/guides/TESTING_GUIDE.md)** - How to test the application
- **[OCR Setup Guide](docs/guides/OCR_SETUP_GUIDE.md)** - Tesseract OCR configuration
- **[Integration Summary](docs/guides/INTEGRATION_SUMMARY.md)** - Technical details

### Developer Documentation

- **[Build Guide](docs/developer/BUILD_GUIDE.md)** - Building executables
- **[Testing Guide](docs/developer/TESTING_GUIDE.md)** - Running tests
- **[Documentation Index](docs/developer/DOCUMENTATION_INDEX.md)** - All docs

## 🎯 Usage Examples

### Analyze a Contract

```bash
# Text file
python src/cli_main.py contract.txt

# PDF file
python src/cli_main.py contract.pdf

# Word document
python src/cli_main.py contract.docx

# Pre-analyzed JSON
python src/cli_main.py contract_analysis.json
```

### Interactive Q&A

After analysis, ask questions:

```
❓ Your question: What are the payment terms?
💡 Answer: The initial license fee is $125,000...

❓ Your question: When does the contract expire?
💡 Answer: The initial term is 3 years from January 15, 2026...

❓ Your question: What are the risks?
💡 Answer: The identified risks include...
```

### Commands

| Command | Description |
|---------|-------------|
| `<question>` | Ask any question |
| `summary` | Show analysis summary |
| `help` | Show help |
| `exit` | Exit |

## 🔧 System Requirements

### Minimum

- **OS:** Windows 10/11, Linux, macOS
- **Python:** 3.11+
- **RAM:** 2 GB
- **Disk:** 500 MB
- **Internet:** Required for analysis

### Recommended

- **RAM:** 4 GB+
- **Disk:** 1 GB
- **Internet:** Broadband

## 🏗️ Architecture

### OpenAI-Only Design

- **Analysis Engine** - Uses OpenAI API for contract analysis
- **Query Engine** - Uses OpenAI API for Q&A
- **Contract Uploader** - Extracts text from PDF/DOCX/TXT
- **OCR Support** - Tesseract for scanned documents

### No Local LLM Required

- ✅ No large model downloads
- ✅ No GPU required
- ✅ Lower memory usage
- ✅ Faster startup

## 📊 Performance

| Task | Time |
|------|------|
| Startup | 3 seconds |
| Analysis (< 5 pages) | 15-30 seconds |
| Analysis (5-20 pages) | 30-60 seconds |
| Query response | 2-5 seconds |

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run specific test suite
pytest tests/unit/
pytest tests/integration/

# Run with coverage
pytest tests/ --cov=src
```

## 🐛 Troubleshooting

### "OPENAI_API_KEY not set"

```bash
setx OPENAI_API_KEY "sk-your-key-here"
```

### "No text extracted from PDF"

- PDF may be image-based (scanned)
- Install Tesseract OCR for automatic OCR support
- See [OCR Setup Guide](docs/guides/OCR_SETUP_GUIDE.md)

### "tkinter DLL load failed"

- Use the CLI version instead: `python src/cli_main.py`
- See [CLI Guide](docs/guides/CLI_GUIDE.md)

## 📝 License

[Your License Here]

## 🤝 Contributing

Contributions welcome! Please read the contributing guidelines first.

## 📧 Support

- **Documentation:** See `docs/guides/`
- **Issues:** [GitHub Issues]
- **Logs:** `%APPDATA%\CR2A\logs\cr2a.log`

## 🎉 Acknowledgments

- OpenAI for GPT API
- Tesseract OCR for text recognition
- Python community for excellent libraries

---

**Ready to analyze contracts!** 🚀

*Last Updated: February 3, 2026*
