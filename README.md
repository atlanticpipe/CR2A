# CR2A - Clause Risk & Compliance Analyzer

## Overview

CR2A is an intelligent contract analysis platform that automatically identifies risks, compliance issues, and key terms in procurement and service contracts. Designed specifically for FDOT and internal Atlantic Pipe Services contracts, CR2A streamlines contract intake and produces executive-ready analysis reports.

**Status**: Active Development (Rebuilding from scratch for production reliability)

## Features

**Automated Contract Analysis**
- PDF, DOCX, and TXT file support
- Intelligent clause extraction and categorization
- Risk scoring and compliance validation
- Executive summaries and detailed findings

**AI-Powered Intelligence**
- GPT-4 integration for semantic understanding
- Clause classification by type (indemnification, liability, warranty, etc.)
- Context-aware risk assessment
- Intelligent recommendation generation

**Professional Reporting**
- PDF export with branded formatting
- Risk level visualization (High/Medium/Low)
- Detailed findings with remediation suggestions
- Compliance matrix against policy standards

**Enterprise Integration**
- AWS S3 for secure file storage
- Lambda deployment for scalability
- CORS-enabled REST API
- GitHub Actions CI/CD automation

## Architecture

### System Layers

┌─────────────────────────────────────┐
│  Frontend (React/Vanilla JS)        │ frontend/
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
│  Data Layer                          │ config/schemas/
│  - Validation rules (JSON)           │
│  - Clause definitions (JSON)         │
│  - Output schemas (JSON)             │
└─────────────────────────────────────┘

## Project Structure

CR2A/
├── frontend/ ........................... Frontend application
│   ├── services/ ....................... Service layer
│   │   ├── fileParser.js ............... File parsing service
│   │   ├── openaiService.js ............ OpenAI API integration
│   │   ├── pdfExporter.js .............. PDF report generation
│   │   └── promptBuilder.js ............ Prompt construction
│   ├── components/ ..................... UI components
│   ├── __tests__/ ...................... Frontend tests
│   │   ├── services/ ................... Service tests
│   │   ├── components/ ................. Component tests
│   │   ├── fixtures.js ................. Test fixtures
│   │   ├── setup.js .................... Test setup
│   │   └── app.test.js ................. App tests
│   ├── index.html ...................... HTML structure
│   ├── styles.css ...................... Styling & themes
│   ├── ui-enhancements.css ............. Additional UI styles
│   ├── app.js .......................... Client logic (DEPRECATED - use app_integrated.js)
│   ├── ui-manager.js ................... UI state management
│   ├── notifications.js ................ Notification system
│   ├── env.js .......................... Configuration
│   └── CNAME ........................... Domain setup
├── src/ ................................ Backend application code
│   ├── config/ ......................... Configuration files
│   │   ├── schemas/ .................... JSON data definitions
│   │   │   ├── clause_classification.json
│   │   │   ├── validation_rules.json
│   │   │   ├── output_schemas.json
│   │   │   └── section_map.json
│   │   └── templates/ .................. Report templates
│   │       ├── CR2A_Template.docx
│   │       └── pdf_field_map.json
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
├── scripts/ ............................ Utility scripts
│   └── cleanup_repo.py ................. Repository cleanup
├── tests/ .............................. Python tests
│   ├── test_analyzer.py
│   ├── test_cleanup.py
│   └── conftest.py
├── .kiro/ .............................. Kiro specs and config
│   └── specs/ .......................... Feature specifications
│       └── repository-reorganization/ .. Reorganization spec
├── .github/ ............................ GitHub configuration
│   ├── workflows/ ...................... CI/CD automation
│   │   ├── deploy-pages.yml
│   │   └── publish-layers.yml
│   └── actions/ ........................ Custom GitHub Actions
│       └── build-layer/ ................ Lambda layer builder
├── app_integrated.js ................... Main application entry
├── vitest.config.js .................... Vitest configuration
├── requirements.txt .................... Python dependencies
├── .gitignore .......................... Git ignore rules
└── README.md ........................... This file

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

2. **Create Python virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt

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

### Testing Locally

#### Frontend Only (UI Testing)
```bash
cd frontend
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
cd frontend
python3 -m http.server 8000

# Visit http://localhost:8000
```

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

## Development Workflow

### Building Features Step-by-Step

This project is being rebuilt in phases:

1. **Phase 1** - Foundation (CURRENT)
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
# JavaScript tests (Vitest)
npm test

# With coverage
npm run test:coverage

# Python tests
pytest tests/

# With coverage
pytest --cov=src tests/

# Specific test file
pytest tests/test_analyzer.py

# Run specific JavaScript test
npm test -- frontend/__tests__/services/fileParser.test.js
```

### Repository Cleanup

The repository includes a cleanup script to remove test artifacts, temporary files, and redundant scripts. This helps maintain a clean codebase and reduces repository size.

**What Gets Removed:**
- Test artifacts (.pytest_cache, .hypothesis, __pycache__ directories)
- Temporary output files (*_output.txt, *_RESULTS.md)
- Redundant test scripts (manual_config_check.py, quick_import_test.py, etc.)
- Redundant documentation (ERROR_HANDLING_GUIDE.txt, REORGANIZATION_STATE.md)
- Log files (logs/*.csv)
- Windows batch scripts (*.bat)
- Redundant requirements files (requirements-core.txt, requirements-minimal.txt, requirements-optional.txt)

**Protected Files (Never Removed):**
- All files in src/, frontend/, infrastructure/, config/, docs/, .kiro/
- .env, .gitignore, README.md, requirements.txt
- .git/ and .github/ directories

**Preview Changes (Dry Run):**
```bash
python scripts/cleanup_repo.py --dry-run
```

This shows what would be removed without actually deleting anything. Review the output to ensure no unexpected files are listed.

**Run Cleanup:**
```bash
python scripts/cleanup_repo.py
```

This removes all identified files and generates a detailed report at `.kiro/specs/repository-reorganization/cleanup-report.md`.

**Verbose Output:**
```bash
python scripts/cleanup_repo.py --verbose
```

Shows detailed logging during the cleanup process.

## Configuration

### Environment Variables

OPENAI_API_KEY ........... OpenAI API key for GPT-4 calls
AWS_ACCESS_KEY_ID ....... AWS access key
AWS_SECRET_ACCESS_KEY ... AWS secret key
AWS_REGION .............. AWS region (default: us-east-1)
AWS_S3_BUCKET ........... S3 bucket for file storage
FLASK_ENV ............... Development or production
FLASK_DEBUG ............. Enable debug mode (0 or 1)
LOG_LEVEL ............... Logging level (DEBUG, INFO, WARNING, ERROR)

### File Limits

- Maximum file size: 500 MB
- Supported formats: PDF, DOCX, TXT
- Processing timeout: 5 minutes

## Deployment

### Deploy to GitHub Pages (Frontend)

The CR2A frontend is automatically deployed to GitHub Pages whenever changes are pushed to the main branch. The deployment workflow validates required files, packages the static site, and publishes it to https://cr2a.atlanticpipe.us.

#### Automatic Deployment

```bash
# Push frontend changes to main branch
git add frontend/
git commit -m "Update frontend"
git push origin main

# GitHub Actions automatically:
# 1. Validates required files exist
# 2. Packages the static site
# 3. Deploys to GitHub Pages
# 4. Makes the site live at https://cr2a.atlanticpipe.us
```

#### Manual Deployment

You can manually trigger a deployment without pushing new code:

1. Go to the repository on GitHub
2. Click the **Actions** tab
3. Select **Deploy to GitHub Pages** workflow from the left sidebar
4. Click **Run workflow** button
5. Select the **main** branch
6. Click **Run workflow**

The workflow will deploy the current state of the main branch.

#### View Deployment Status

**Check Current Deployment:**
1. Go to the repository on GitHub
2. Click the **Actions** tab
3. View the most recent **Deploy to GitHub Pages** workflow run
4. Green checkmark = successful deployment
5. Red X = failed deployment (click for error details)

**View Deployment History:**
1. Go to the repository on GitHub
2. Click the **Environments** section (right sidebar)
3. Click **github-pages**
4. View all past deployments with timestamps and status

**Check Live Site:**
- Visit https://cr2a.atlanticpipe.us
- The site should reflect your latest deployed changes
- Check browser console for any loading errors

#### Troubleshooting Deployment Issues

**Deployment Fails with "Missing Required Files"**

The validation step checks for required files before deployment. If this fails:

```bash
# Check which files are missing
cat .github/workflows/validate-files.sh

# Ensure these files exist in your repository:
# - index.html
# - app_integrated.js
# - CNAME
# - frontend/ directory
# - config/ directory

# Verify files exist locally
ls -la index.html app_integrated.js CNAME
ls -la frontend/ config/

# If files are missing, restore them and push again
git add index.html app_integrated.js CNAME frontend/ config/
git commit -m "Restore required files"
git push origin main
```

**Deployment Fails with "Permission Denied"**

The workflow needs proper permissions to deploy to GitHub Pages:

1. Go to repository **Settings**
2. Click **Actions** → **General**
3. Scroll to **Workflow permissions**
4. Ensure **Read and write permissions** is selected
5. Check **Allow GitHub Actions to create and approve pull requests**
6. Click **Save**

Also verify GitHub Pages is enabled:

1. Go to repository **Settings**
2. Click **Pages** (left sidebar)
3. Under **Source**, select **GitHub Actions**
4. Click **Save**

**Deployment Succeeds but Site Shows 404**

If the workflow succeeds but the site doesn't load:

1. Check GitHub Pages is configured correctly:
   - Go to **Settings** → **Pages**
   - Verify **Source** is set to **GitHub Actions**
   - Verify custom domain is set to `cr2a.atlanticpipe.us`

2. Check CNAME file format:
   ```bash
   # CNAME should contain only the domain name
   cat CNAME
   # Should show: cr2a.atlanticpipe.us
   # NOT: https://cr2a.atlanticpipe.us
   # NOT: cr2a.atlanticpipe.us/
   ```

3. Wait 5-10 minutes for DNS propagation

4. Clear browser cache and try again

**Deployment Succeeds but Changes Don't Appear**

If your changes don't appear on the live site:

1. **Hard refresh the browser:**
   - Chrome/Firefox: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
   - Safari: Cmd+Option+R

2. **Check deployment timestamp:**
   - Go to **Actions** tab
   - Verify the workflow completed after your push
   - Check the deployment URL in the workflow output

3. **Verify files were committed:**
   ```bash
   # Check git status
   git status
   
   # Verify files are in the repository
   git ls-files | grep frontend
   ```

4. **Check browser console for errors:**
   - Open browser DevTools (F12)
   - Check Console tab for JavaScript errors
   - Check Network tab for failed file loads

**Workflow Stuck or Taking Too Long**

If the deployment workflow doesn't complete:

1. **Check workflow status:**
   - Go to **Actions** tab
   - Click on the running workflow
   - Check which step is running

2. **Cancel and retry:**
   - Click **Cancel workflow** button
   - Wait for cancellation to complete
   - Manually trigger the workflow again

3. **Check GitHub Status:**
   - Visit https://www.githubstatus.com/
   - Verify GitHub Actions and Pages are operational

**CNAME File Issues**

If you see errors related to the CNAME file:

```bash
# Verify CNAME format (domain only, no protocol or paths)
cat CNAME

# Correct format:
echo "cr2a.atlanticpipe.us" > CNAME

# Incorrect formats:
# https://cr2a.atlanticpipe.us  ❌ (has protocol)
# cr2a.atlanticpipe.us/         ❌ (has trailing slash)
# cr2a.atlanticpipe.us/path     ❌ (has path)

# Commit the corrected CNAME
git add CNAME
git commit -m "Fix CNAME format"
git push origin main
```

**Getting Help**

If you continue to experience issues:

1. Check the workflow logs for detailed error messages
2. Review the validation script output
3. Verify all required files are present and correctly formatted
4. Contact the development team with:
   - Link to the failed workflow run
   - Error messages from the logs
   - Steps you've already tried

### Deploy to AWS Lambda (Backend)

```bash
# Push to main branch
git add .
git commit -m "Ready for production"
git push origin test  # Push to test first

# Create pull request and merge to main
# GitHub Actions automatically deploys to Lambda
```

## Troubleshooting

### Port Already in Use
```bash
# Use different port
python3 -m http.server 8001

# Or kill process on port 8000
lsof -i :8000
kill -9 <PID>


### API Key Errors
```bash
# Check .env file exists and has correct keys
cat .env

# Verify API key is valid
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"


### S3 Permission Errors
```bash
# Verify AWS credentials
aws configure list

# Check S3 bucket exists
aws s3 ls s3://cr2a-contracts/

## License

Copyright © 2024 Atlantic Pipe Services, LLC. All rights reserved.