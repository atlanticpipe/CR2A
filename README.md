# CR2A - Contract Review & Analysis

AI-powered contract analysis and Q&A system with version tracking and change comparison.

## Quick Start

### Desktop GUI (Recommended)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch the application
python src/qt_gui.py
# Or use the launcher: launch_gui.bat

# 3. Select your AI engine in Settings
# - OpenAI API (fast, cloud-based, requires API key)
# - Local AI (Pythia model, offline, no API costs)
```

### Command Line Interface

```bash
# 1. Set your OpenAI API key
setx OPENAI_API_KEY "sk-your-key-here"

# 2. Analyze a contract
python src/cli_main.py contract.pdf

# 3. Ask questions interactively
Your question: Who are the parties?
Your question: What is the contract value?
Your question: exit
```

## Features

### Core Features
- **Contract Analysis** - Extracts parties, terms, dates, risks, obligations, clauses
- **Natural Language Q&A** - Ask questions about analyzed contracts using OpenAI
- **Multiple Formats** - Supports PDF, DOCX, TXT files
- **Desktop GUI** - Modern PyQt5 interface with tabbed navigation
- **CLI Interface** - Command-line option for automation and scripting

### Advanced Features
- **Fuzzy Logic Matching** - Intelligent clause detection using semantic analysis to find categories even when exact terminology differs
- **Version Tracking** - Automatically detect and track contract versions
- **Change Comparison** - Visual diff between contract versions with color-coded highlighting
- **History Management** - Persistent storage of all analyzed contracts
- **Duplicate Detection** - Identifies potential duplicate contracts by hash and filename
- **Exhaustive Analysis** - Optional multi-pass verification with confidence scoring
- **Export Options** - Export analysis reports and chat logs

## Installation

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

## Usage

### Desktop GUI

The GUI provides four main tabs:

#### Upload Tab
- Select contract files (PDF, DOCX, TXT)
- Choose standard or exhaustive analysis mode
- Configure multi-pass verification options
- Automatic duplicate detection

#### Analysis Tab
- Structured view of analysis results
- Contract overview with metadata
- Clauses organized by category
- Identified risks and compliance issues
- Obligations and key terms

#### Chat Tab
- Ask questions about the analyzed contract
- Natural language Q&A powered by OpenAI
- View conversation history
- Export chat logs

#### History Tab
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

## Version Tracking

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

## Architecture

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
- **AI/ML**:
  - OpenAI GPT-4o API (cloud option)
  - Pythia 2.8B/1.4B via llama-cpp-python (local option)
- **Text Extraction**: PyPDF2, python-docx
- **Database**: SQLite (for version tracking)
- **Testing**: pytest, unittest

### AI Engine Options

CR2A supports two AI engines - choose the one that fits your needs:

#### OpenAI API (Cloud)
- **Speed**: Fast analysis (15-60 seconds per contract)
- **Requirements**: Internet connection + API key
- **Cost**: Pay-per-use (~$0.10-0.50 per contract)
- **Setup**: Instant - just enter API key
- **RAM**: 4GB minimum

#### Local AI (Pythia)
- **Speed**: Slower analysis (2-5 minutes per contract)
- **Requirements**: No internet or API key needed
- **Cost**: Free - runs entirely locally
- **Setup**: First-time download (~3GB model)
- **RAM**: 8GB minimum (16GB recommended)
- **Privacy**: 100% offline - no data leaves your computer

**Switching Engines**: File → Settings → AI Engine → Select your preference

### Fuzzy Logic Matching

CR2A includes an intelligent fuzzy logic system that improves clause detection accuracy:

#### How It Works
- **Semantic Analysis**: Pre-analyzes contract text to identify likely clause categories
- **Keyword Matching**: Uses 500+ domain-specific keywords to match contract language to categories
- **Confidence Scoring**: Assigns confidence scores (0-100) to each potential category match
- **Terminology Flexibility**: Finds clauses even when exact category names don't appear in the contract

#### Benefits
- **Higher Recall**: Detects 30-50+ relevant categories vs 7-10 without fuzzy matching
- **Better Coverage**: Identifies clauses by substance, not just exact keyword matches
- **Intelligent Prioritization**: Guides AI to check most likely categories first
- **Reduced False Negatives**: Catches clauses that would be missed by keyword-only search

#### Example Matches
- "Indemnification" category matches: "hold harmless", "defend and indemnify", "indemnitor shall"
- "Payment Terms" category matches: "compensation", "invoice", "remittance", "amount due"
- "Termination for Convenience" category matches: "owner may cancel", "terminate at will"

The fuzzy matcher runs automatically during contract analysis and provides suggestions to both OpenAI and Pythia engines.

## Performance

| Task | Time |
|------|------|
| Application startup | 2-3 seconds |
| Analysis (< 5 pages) | 15-30 seconds |
| Analysis (5-20 pages) | 30-60 seconds |
| Analysis (20-50 pages) | 60-120 seconds |
| Query response | 2-5 seconds |
| Version comparison | < 1 second |

## System Requirements

### For OpenAI API (Cloud)
- **OS:** Windows 10/11 (64-bit)
- **Python:** 3.11+
- **RAM:** 4 GB minimum
- **Disk:** 1 GB free space
- **Internet:** Required (broadband recommended)

### For Local AI (Pythia)
- **OS:** Windows 10/11 (64-bit)
- **Python:** 3.11+
- **RAM:** 8 GB minimum (16 GB recommended)
- **CPU:** 4+ cores @ 2.5GHz (8 cores @ 3.0GHz recommended)
- **Disk:** 5 GB free space (includes model cache)
- **Internet:** Only for first-time model download

**Note**: Local AI runs on CPU only - no GPU required

## Testing

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

## Troubleshooting

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

### Local AI model won't load

- **Insufficient memory**: Close other applications, try smaller model (Pythia 1.4B)
- **Model download failed**: Settings → AI Engine → Manage Models → Re-download
- **Model corrupted**: Delete and re-download from Model Manager
- **Alternative**: Switch to OpenAI API in Settings

### Local AI analysis is slow

- **Expected**: Local AI takes 2-5 minutes per contract (CPU-only)
- **Improve speed**: Close background applications, ensure 8+ CPU cores
- **Faster option**: Use OpenAI API (15-60 seconds per contract)

## Documentation

### User Guides
- **[User Manual](USER_MANUAL.md)** - Complete user guide
- **[Versioning Guide](docs/VERSIONING_USER_GUIDE.md)** - Version tracking features
- **[Local Model Guide](docs/LOCAL_MODEL_GUIDE.md)** - Local AI setup and fine-tuning

### Developer Documentation
- **[Database Schema](docs/DATABASE_SCHEMA.md)** - Versioning database structure
- **[Code Signing Guide](CODE_SIGNING_GUIDE.md)** - Building signed executables

## Building Executables

CR2A offers two distribution options:

### Option 1: Standard Build (Recommended for Most Users)

Small installer, model downloads on first use:

```bash
# Build the application
python build_tools/build.py --target gui

# Build the installer
python build_tools/build.py --target installer

# This creates:
# - dist/CR2A/CR2A.exe (main application)
# - dist/CR2A_Setup.exe (~8-10 MB installer)
#
# User experience:
# - Fast download and installation
# - Pythia model downloads on first use (3GB, one-time)
# - Requires internet for initial Local AI setup
```

### Option 2: Full Offline Build (Corporate/Airgapped Environments)

Large installer with bundled Pythia model:

```bash
# 1. Download Pythia model first (one-time setup, ~2.8 GB)
cd models
powershell -ExecutionPolicy Bypass -File download_pythia_2.8b.ps1

# Or manually download from:
# https://huggingface.co/TheBloke/pythia-2.8b-GGUF/resolve/main/pythia-2.8b.Q4_K_M.gguf
# Save as: models/pythia-2.8b-q4_k_m.gguf

# 2. Build with bundled model
cd ..
python build_tools/build.py --target gui-full

# 3. Build full installer
python build_tools/build.py --target installer-full

# This creates:
# - dist/CR2A_Full/CR2A.exe (application with bundled model)
# - dist/CR2A_Setup_Full.exe (~3-4 GB installer)
#
# User experience:
# - Large initial download (~3-4 GB)
# - No internet required after installation
# - Pythia available immediately on first run
# - Perfect for airgapped/corporate environments
```

### Build Targets Summary

| Target | Output | Size | Use Case |
|--------|--------|------|----------|
| `gui` | CR2A.exe | ~25 MB | Standard application |
| `gui-full` | CR2A.exe | ~3 GB | App with bundled model |
| `installer` | CR2A_Setup.exe | ~8 MB | Standard installer |
| `installer-full` | CR2A_Setup_Full.exe | ~3-4 GB | Offline installer |
| `cli` | ContractAnalysisCLI.exe | ~15 MB | Command-line tool |
| `all` | Both GUI & CLI | ~40 MB | All executables |

See [CODE_SIGNING_GUIDE.md](CODE_SIGNING_GUIDE.md) for code signing instructions.
See [BUNDLED_MODEL_SETUP.md](BUNDLED_MODEL_SETUP.md) for detailed bundled model setup.

## Configuration

Configuration is stored in:
- **Windows:** `%APPDATA%\CR2A\config.json`
- **Logs:** `%APPDATA%\CR2A\logs\cr2a.log`
- **Database:** `%APPDATA%\CR2A\versions.db`
- **History:** `%APPDATA%\CR2A\history\`
- **Local Models:** `%APPDATA%\CR2A\models\` (~3GB per model)

## Contributing

Contributions welcome! Areas for contribution:
- Additional analysis features
- UI/UX improvements
- Performance optimizations
- Test coverage
- Documentation

## Support

- **Documentation:** See [USER_MANUAL.md](USER_MANUAL.md)
- **Issues:** [GitHub Issues]
- **Logs:** Check `%APPDATA%\CR2A\logs\cr2a.log` for errors

## Attribution

### OpenContracts

Local AI model integration was inspired by architectural patterns from [OpenContracts](https://github.com/JSv4/OpenContracts):

- **Tool Architecture Pattern**: Framework-agnostic `CoreTool` dataclass for modular extraction functions
- **Evidence Tracking Pattern**: `SourceNode` approach for linking findings to source clauses
- **Streaming Events Pattern**: Event-driven response architecture for real-time updates

**License**: Patterns used under AGPL-3.0 with attribution
**Source**: OpenContracts (opencontractserver/llms/tools/core_tools.py)
**Adaptations**: Simplified for CR2A's contract analysis use case

CR2A's implementation is original code inspired by these patterns, not a derivative work.

## Acknowledgments

- **OpenAI** - GPT-4o API for cloud-based analysis and Q&A
- **EleutherAI** - Pythia models for local AI capability
- **OpenContracts** - Architectural patterns for local model integration (AGPL-3.0)
- **llama.cpp** - Efficient CPU inference engine
- **PyQt5** - Desktop GUI framework
- **Python Community** - Excellent libraries and tools

## License

[Your License Here]

---

**Ready to analyze contracts with version tracking!**

*Last Updated: February 5, 2026*
