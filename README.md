# CR2A - Contract Review & Analysis

AI-powered contract analysis and Q&A system with version tracking and change comparison.

## 🚀 Quick Start

### Desktop GUI (Recommended)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch the application
python src/qt_gui.py
# Or use the launcher: launch_gui.bat

# 3. Configure your OpenAI API key in Settings
# The app will prompt you on first launch
```

### Command Line Interface

```bash
# 1. Set your OpenAI API key
setx OPENAI_API_KEY "sk-your-key-here"

# 2. Analyze a contract
python src/cli_main.py contract.pdf

# 3. Ask questions interactively
❓ Your question: Who are the parties?
❓ Your question: What is the contract value?
❓ Your question: exit
```

## 📋 Features

### Core Features
- ✅ **Contract Analysis** - Extracts parties, terms, dates, risks, obligations, clauses
- ✅ **Natural Language Q&A** - Ask questions about analyzed contracts using OpenAI
- ✅ **Multiple Formats** - Supports PDF, DOCX, TXT files
- ✅ **Desktop GUI** - Modern PyQt5 interface with tabbed navigation
- ✅ **CLI Interface** - Command-line option for automation and scripting

### Advanced Features
- ✅ **Version Tracking** - Automatically detect and track contract versions
- ✅ **Change Comparison** - Visual diff between contract versions with color-coded highlighting
- ✅ **History Management** - Persistent storage of all analyzed contracts
- ✅ **Duplicate Detection** - Identifies potential duplicate contracts by hash and filename
- ✅ **Exhaustive Analysis** - Optional multi-pass verification with confidence scoring
- ✅ **Export Options** - Export analysis reports and chat logs

## 📦 Installation

### Prerequisites
- **Python 3.11+**
- **Windows 10/11** (primary platform)
- **OpenAI API Key** - Get one from [OpenAI Platform](https://platform.openai.com/api-keys)

### Setup

```bash
# 1. Clone the repository
git clone <repository-url>
cd CR2A

# 2. Create virtual environment (recommended)
python -m venv venv311
venv311\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the application
python src/qt_gui.py
```

The application will prompt you to enter your OpenAI API key on first launch.

## 🎯 Usage

### Desktop GUI

The GUI provides four main tabs:

#### 📄 Upload Tab
- Select contract files (PDF, DOCX, TXT)
- Choose standard or exhaustive analysis mode
- Configure multi-pass verification options
- Automatic duplicate detection

#### 📊 Analysis Tab
- Structured view of analysis results
- Contract overview with metadata
- Clauses organized by category
- Identified risks and compliance issues
- Obligations and key terms

#### 💬 Chat Tab
- Ask questions about the analyzed contract
- Natural language Q&A powered by OpenAI
- View conversation history
- Export chat logs

#### 📜 History Tab
- View all previously analyzed contracts
- See version information for each contract
- Load historical analyses
- Compare different versions side-by-side
- Delete old analyses

### Command Line Interface

```bash
# Analyze a contract
python src/cli_main.py contract.pdf

# The CLI will:
# 1. Extract text from the document
# 2. Analyze with OpenAI
# 3. Display a summary
# 4. Save results to JSON
# 5. Enter interactive Q&A mode

# Interactive commands:
# - Type any question to ask about the contract
# - 'summary' - Show analysis summary again
# - 'help' - Show available commands
# - 'exit' - Quit the application
```

## 🔄 Version Tracking

CR2A automatically tracks contract versions and changes:

### How It Works

1. **Upload a Contract** - First upload creates version 1
2. **Upload Updated Version** - CR2A detects potential duplicates by:
   - File hash (exact matches)
   - Filename similarity (fuzzy matching)
3. **Confirm Version Update** - You confirm if it's an updated version
4. **Automatic Comparison** - CR2A compares versions and identifies:
   - Modified clauses
   - Added clauses
   - Deleted clauses
   - Unchanged clauses
5. **View Changes** - Use the History tab to compare any two versions

### Version Comparison Features

- **Side-by-side diff view** with color-coded changes
- **Change summary** showing counts of modifications
- **Clause-level tracking** with version numbers
- **Text-level highlighting** showing exact changes within clauses

## 🏗️ Architecture

### Application Structure

```
CR2A Desktop Application (PyQt5)
├── Upload Tab → File selection & analysis options
├── Analysis Tab → Structured results display
├── Chat Tab → Q&A interface
└── History Tab → Version tracking & comparison

Core Components:
├── Analysis Engine → OpenAI-powered contract analysis
├── Query Engine → OpenAI-powered Q&A
├── Contract Uploader → Text extraction (PDF/DOCX/TXT)
├── Versioning System → Change tracking & comparison
└── History Store → Persistent storage
```

### Technology Stack

- **GUI Framework**: PyQt5
- **AI/ML**: OpenAI GPT-4o API
- **Text Extraction**: PyPDF2, python-docx
- **Database**: SQLite (for version tracking)
- **Testing**: pytest, unittest

### OpenAI-Only Design

- Uses OpenAI API for all AI operations
- No local LLM required
- No GPU required
- Lower memory usage
- Faster startup

## 📊 Performance

| Task | Time |
|------|------|
| Application startup | 2-3 seconds |
| Analysis (< 5 pages) | 15-30 seconds |
| Analysis (5-20 pages) | 30-60 seconds |
| Analysis (20-50 pages) | 60-120 seconds |
| Query response | 2-5 seconds |
| Version comparison | < 1 second |

## 🔧 System Requirements

### Minimum
- **OS:** Windows 10/11 (64-bit)
- **Python:** 3.11+
- **RAM:** 4 GB
- **Disk:** 1 GB free space
- **Internet:** Required for OpenAI API

### Recommended
- **RAM:** 8 GB+
- **Disk:** 2 GB free space
- **Internet:** Broadband connection

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run specific test suites
pytest tests/unit/           # Unit tests
pytest tests/integration/    # Integration tests
pytest tests/manual/         # Manual test scripts

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run performance benchmarks
python tests/performance_benchmark.py
```

## 🐛 Troubleshooting

### "OPENAI_API_KEY not set" (CLI)

```bash
setx OPENAI_API_KEY "sk-your-key-here"
```

### "No text extracted from PDF"

- PDF may be image-based (scanned)
- Install Tesseract OCR for automatic OCR support
- Ensure PDF is not password-protected

### GUI won't start

```bash
# Check PyQt5 installation
pip install --upgrade PyQt5

# Or use CLI version
python src/cli_main.py contract.pdf
```

### Analysis fails with API error

- Verify your OpenAI API key is valid
- Check your internet connection
- Ensure you have sufficient API credits
- Check OpenAI service status

### Version comparison not working

- Ensure versioning system initialized correctly
- Check logs in `%APPDATA%\CR2A\logs\`
- Try restarting the application

## 📖 Documentation

### User Guides
- **[User Manual](USER_MANUAL.md)** - Complete user guide
- **[Versioning Guide](docs/VERSIONING_USER_GUIDE.md)** - Version tracking features

### Developer Documentation
- **[Database Schema](docs/DATABASE_SCHEMA.md)** - Versioning database structure
- **[Code Signing Guide](CODE_SIGNING_GUIDE.md)** - Building signed executables

## 🔨 Building Executables

```bash
# Build the application
python -m build_tools.build

# This creates:
# - dist/CR2A.exe (main application)
# - dist/CR2A_Setup.exe (installer)
```

See [CODE_SIGNING_GUIDE.md](CODE_SIGNING_GUIDE.md) for code signing instructions.

## 📝 Configuration

Configuration is stored in:
- **Windows:** `%APPDATA%\CR2A\config.json`
- **Logs:** `%APPDATA%\CR2A\logs\cr2a.log`
- **Database:** `%APPDATA%\CR2A\versions.db`
- **History:** `%APPDATA%\CR2A\history\`

## 🤝 Contributing

Contributions welcome! Areas for contribution:
- Additional analysis features
- UI/UX improvements
- Performance optimizations
- Test coverage
- Documentation

## 📧 Support

- **Documentation:** See [USER_MANUAL.md](USER_MANUAL.md)
- **Issues:** [GitHub Issues]
- **Logs:** Check `%APPDATA%\CR2A\logs\cr2a.log` for errors

## 🎉 Acknowledgments

- **OpenAI** - GPT API for analysis and Q&A
- **PyQt5** - Desktop GUI framework
- **Python Community** - Excellent libraries and tools

## 📄 License

[Your License Here]

---

**Ready to analyze contracts with version tracking!** 🚀

*Last Updated: February 5, 2026*
