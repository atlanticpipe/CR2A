# CR2A - Clause Risk & Compliance Analyzer

## Overview

CR2A is an intelligent contract analysis platform that automatically identifies risks, compliance issues, and key terms in procurement and service contracts. Designed specifically for FDOT and internal Atlantic Pipe Services contracts, CR2A streamlines contract intake and produces executive-ready analysis reports.

**Status**: 🚀 Active Development (Rebuilding from scratch for production reliability)

---

## Features

✅ **Automated Contract Analysis**
- PDF, DOCX, and TXT file support
- Intelligent clause extraction and categorization
- Risk scoring and compliance validation
- Executive summaries and detailed findings

✅ **AI-Powered Intelligence**
- GPT-4 integration for semantic understanding
- Clause classification by type (indemnification, liability, warranty, etc.)
- Context-aware risk assessment
- Intelligent recommendation generation

✅ **Professional Reporting**
- PDF export with branded formatting
- Risk level visualization (High/Medium/Low)
- Detailed findings with remediation suggestions
- Compliance matrix against policy standards

✅ **Enterprise Integration**
- AWS S3 for secure file storage
- Lambda deployment for scalability
- CORS-enabled REST API
- GitHub Actions CI/CD automation

---

## Architecture

### System Layers

```
┌─────────────────────────────────────┐
│  Frontend (React/Vanilla JS)        │ webapp/
│  - Form submission                   │
│  - Results display                   │
│  - Dark mode theme                   │
└──────────────┬──────────────────────┘
               │ HTTP
┌──────────────▼──────────────────────┐
│  API Layer (Flask/FastAPI)          │ src/api/
│  - REST endpoints                    │
│  - Request validation                │
│  - Response formatting               │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  Core Logic (Analyzer)              │ src/core/
│  - Text normalization                │
│  - Clause extraction                 │
│  - Risk assessment                   │
│  - Compliance validation             │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  Services                            │ src/services/
│  - OpenAI API calls                  │
│  - AWS S3 storage                    │
│  - PDF generation                    │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  Data Layer                          │ schemas/
│  - Validation rules (JSON)           │
│  - Clause definitions (JSON)         │
│  - Output schemas (JSON)             │
└─────────────────────────────────────┘
```

---

## Project Structure

```
CR2A/
├── src/
│   ├── api/
│   │   └── main.py ..................... REST API endpoints
│   ├── core/
│   │   ├── analyzer.py ................. Main analysis engine
│   │   ├── validator.py ................ Compliance checker
│   │   └── config.py ................... Configuration loader
│   ├── services/
│   │   ├── openai_client.py ............ OpenAI API integration
│   │   ├── pdf_export.py ............... PDF report generation
│   │   └── storage.py .................. AWS S3 operations
│   ├── schemas/
│   │   ├── normalizer.py ............... Text processing
│   │   ├── policy_loader.py ............ Load policy rules
│   │   └── template_spec.py ............ Output templates
│   └── utils/
│       ├── cli.py ...................... Command-line tool
│       └── mime_utils.py ............... File type detection
├── schemas/ ............................ JSON data definitions
│   ├── clause_classification.json
│   ├── validation_rules.json
│   ├── output_schemas.json
│   ├── section_map.json
│   └── lambda-iam-policy.json
├── templates/ .......................... Report templates
│   ├── CR2A_Template.docx
│   └── pdf_field_map.json
├── webapp/ ............................. Frontend application
│   ├── index.html ...................... HTML structure
│   ├── styles.css ...................... Styling & themes
│   ├── app.js .......................... Client logic
│   ├── env.js .......................... Configuration
│   └── CNAME ........................... Domain setup
├── .github/workflows/ .................. CI/CD automation
├── requirements.txt .................... Python dependencies
├── .gitignore .......................... Git ignore rules
└── README.md ........................... This file
```

---

## Quick Start

### Prerequisites

- Python 3.9+
- AWS account (for S3 storage)
- OpenAI API key
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/atlanticpipe/CR2A.git
   cd CR2A
   git checkout test  # Switch to test branch for development
   ```

2. **Create Python virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   # Create .env file in project root
   cat > .env << EOF
   OPENAI_API_KEY="sk-..."
   AWS_ACCESS_KEY_ID="AKIA..."
   AWS_SECRET_ACCESS_KEY="..."
   AWS_REGION="us-east-1"
   AWS_S3_BUCKET="cr2a-contracts"
   FLASK_ENV="development"
   FLASK_DEBUG="1"
   EOF
   ```

### Testing Locally

#### Frontend Only (UI Testing)
```bash
cd webapp
python3 -m http.server 8000
# Visit http://localhost:8000
```

#### Backend Only (API Testing)
```bash
flask run
# In another terminal:
curl -X POST http://localhost:5000/analyze \
  -F "file=@contract.pdf" \
  -F "contract_id=TEST-001"
```

#### Full Stack (Frontend + Backend)
```bash
# Terminal 1: Start backend API
flask run

# Terminal 2: Start frontend server
cd webapp
python3 -m http.server 8000

# Visit http://localhost:8000
```

---

## API Endpoints

### Submit Contract for Analysis
```http
POST /analyze

Body:
  - file: PDF/DOCX/TXT file
  - contract_id: Unique identifier (e.g., FDOT-Bridge-2024-18)

Response:
  - analysis_id: Unique analysis ID
  - status: "queued" or "processing"
  - message: Status message
```

### Get Analysis Results
```http
GET /results/{analysis_id}

Response:
  - analysis_id: ID
  - contract_id: Contract ID
  - status: "complete" or "processing"
  - risk_level: "HIGH", "MEDIUM", or "LOW"
  - findings: Array of risk findings
  - summary: Executive summary
  - recommendations: Suggested improvements
  - timestamp: Analysis completion time
```

### Download PDF Report
```http
GET /download/{analysis_id}

Response: PDF file (application/pdf)
```

### Check Analysis Status
```http
GET /status/{analysis_id}

Response:
  - analysis_id: ID
  - status: "processing", "complete", or "error"
  - progress: Percentage complete
  - message: Status message
```

---

## Development Workflow

### Building Features Step-by-Step

This project is being rebuilt in phases:

1. **Phase 1** - Foundation (✅ CURRENT)
   - .gitignore setup
   - requirements.txt
   - README.md

2. **Phase 2** - Configuration & Schemas
   - JSON rule definitions
   - System configuration
   - Policy files

3. **Phase 3** - Utilities
   - Helper functions
   - CLI tool
   - File type detection

4. **Phase 4** - Core Logic
   - Analysis engine
   - Text processing
   - Validation system

5. **Phase 5** - Services
   - AWS S3 integration
   - OpenAI API client
   - PDF export

6. **Phase 6** - API Layer
   - REST endpoints
   - Request handling
   - Response formatting

7. **Phase 7** - Frontend
   - HTML/CSS/JavaScript
   - Form submission
   - Results display

8. **Phase 8** - Deployment
   - CI/CD workflows
   - Lambda function
   - GitHub Pages

### Running Tests

```bash
# Unit tests (when implemented)
pytest tests/

# With coverage
pytest --cov=src tests/

# Specific test
pytest tests/test_analyzer.py
```

---

## Configuration

### Environment Variables

```
OPENAI_API_KEY ........... OpenAI API key for GPT-4 calls
AWS_ACCESS_KEY_ID ....... AWS access key
AWS_SECRET_ACCESS_KEY ... AWS secret key
AWS_REGION .............. AWS region (default: us-east-1)
AWS_S3_BUCKET ........... S3 bucket for file storage
FLASK_ENV ............... Development or production
FLASK_DEBUG ............. Enable debug mode (0 or 1)
LOG_LEVEL ............... Logging level (DEBUG, INFO, WARNING, ERROR)
```

### File Limits

- Maximum file size: 500 MB
- Supported formats: PDF, DOCX, TXT
- Processing timeout: 5 minutes

---

## Deployment

### Deploy to AWS Lambda

```bash
# Push to main branch
git add .
git commit -m "Ready for production"
git push origin test  # Push to test first

# Create pull request and merge to main
# GitHub Actions automatically deploys to Lambda
```

### Deploy to GitHub Pages (Frontend)

```bash
# Push webapp changes
git add webapp/
git commit -m "Update frontend"
git push origin main

# GitHub Actions automatically deploys to GitHub Pages
# Visit: https://cr2a.atlanticpipe.us
```

---

## Troubleshooting

### Port Already in Use
```bash
# Use different port
python3 -m http.server 8001

# Or kill process on port 8000
lsof -i :8000
kill -9 <PID>
```

### API Key Errors
```bash
# Check .env file exists and has correct keys
cat .env

# Verify API key is valid
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### S3 Permission Errors
```bash
# Verify AWS credentials
aws configure list

# Check S3 bucket exists
aws s3 ls s3://cr2a-contracts/
```

---

## Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes and commit: `git commit -am 'Add feature'`
3. Push to branch: `git push origin feature/my-feature`
4. Create pull request to `test` branch first
5. After testing, merge to `main` for production deployment

---

## License

Copyright © 2024 Atlantic Pipe Services, LLC. All rights reserved.

---

## Support

For questions or issues, contact: support@atlanticpipe.us

---

## Roadmap

- [x] Phase 1: Project foundation
- [ ] Phase 2: Configuration & schemas
- [ ] Phase 3: Utilities & helpers
- [ ] Phase 4: Core analysis engine
- [ ] Phase 5: Cloud services integration
- [ ] Phase 6: REST API
- [ ] Phase 7: Web UI
- [ ] Phase 8: Production deployment
- [ ] Advanced: Multi-language support
- [ ] Advanced: Batch processing
- [ ] Advanced: Contract templates library
- [ ] Advanced: Custom policy rules UI

---

**Last Updated**: December 19, 2025
**Version**: 0.1.0 (Development)