# CR2A Quick Start Guide

## What Changed

The **test branch** now includes a complete **LLM-powered analysis pipeline** with **streaming progress updates**.

**Key Features:**
- ✅ GPT-4 performs all analysis (not just verification)
- ✅ Real-time progress streaming to frontend
- ✅ Async/await architecture for scalability
- ✅ REST API with Server-Sent Events
- ✅ Live progress bar and stage indicators

## 5-Minute Setup

### 1. Clone and Setup

```bash
git clone https://github.com/atlanticpipe/CR2A.git
cd CR2A
git checkout test

python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
cat > .env << EOF
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
EOF
```

### 3. Run Backend (Terminal 1)

```bash
export FLASK_APP=src.api.main
export FLASK_ENV=development
flask run
# Server running on http://localhost:5000
```

### 4. Run Frontend (Terminal 2)

```bash
cd webapp
python3 -m http.server 8000
# Open http://localhost:8000
```

### 5. Test It!

1. Open http://localhost:8000 in your browser
2. Upload a PDF/DOCX contract
3. Watch live progress streaming
4. View results with risk scores

## File Structure

```
CR2A/test
├── src/
│   ├── api/
│   │   └── main.py .................... Flask API with streaming endpoints
│   ├── core/
│   │   ├── llm_analyzer.py ............ LLM analysis engine (NEW)
│   │   └── config.py ................. Configuration management
│   └── services/
│       └── document_processor.py ...... Text extraction from PDFs/DOCX (NEW)
├── webapp/
│   ├── index.html .................... Web interface
│   ├── app.js ........................ Frontend logic with streaming (UPDATED)
│   └── styles.css .................... Styling
├── IMPLEMENTATION_GUIDE.md ........... Detailed technical guide (NEW)
└── QUICKSTART.md ..................... This file
```

## Key Components

### 1. LLM Analyzer (`src/core/llm_analyzer.py`)

**Purpose:** Orchestrates contract analysis using GPT-4

```python
analyzer = LLMAnalyzer(api_key="sk-...")

# Async with progress streaming
async for update in analyzer.analyze_streaming(
    contract_text=text,
    contract_id="FDOT-2024-001",
    analysis_id="unique-id"
):
    if isinstance(update, ProgressUpdate):
        print(f"{update.stage}: {update.percentage}%")
    elif isinstance(update, AnalysisResult):
        print(f"Done: {update.risk_level}")
```

**Analysis Pipeline:**
1. Extract clauses from contract
2. Assess risk for each clause
3. Check compliance issues
4. Generate executive summary
5. Create recommendations

### 2. Document Processor (`src/services/document_processor.py`)

**Supports:** PDF, DOCX, TXT files

```python
processor = DocumentProcessor()
text = processor.extract_text("contract.pdf")
```

### 3. API Layer (`src/api/main.py`)

**Key Endpoints:**

```bash
# Submit contract
POST /analyze
  Body: file + contract_id
  Returns: 202 Accepted + analysis_id

# Stream progress
GET /analyze/{analysis_id}/stream
  Returns: Server-Sent Events stream

# Get results
GET /results/{analysis_id}
  Returns: Complete analysis JSON

# Check status
GET /status/{analysis_id}
  Returns: Current progress
```

### 4. Frontend (`webapp/app.js`)

**Features:**
- File upload with validation
- SSE streaming for progress
- Real-time progress bar
- Results display with color-coded risks
- Download report button

## Common Tasks

### Test with cURL

**Submit analysis:**
```bash
curl -X POST http://localhost:5000/analyze \
  -F "file=@test_contract.pdf" \
  -F "contract_id=TEST-001"

# Response:
# {"analysis_id": "uuid-123", "status": "queued"}
```

**Stream progress:**
```bash
curl -N http://localhost:5000/analyze/uuid-123/stream

# Outputs:
# data: {"type": "progress", "data": {...}}
# data: {"type": "result", "data": {...}}
# data: {"type": "complete"}
```

**Get results:**
```bash
curl http://localhost:5000/results/uuid-123 | jq
```

### Test with Python

```python
import asyncio
from src.core.llm_analyzer import LLMAnalyzer

async def main():
    analyzer = LLMAnalyzer(api_key="sk-...")
    
    text = open("contract.txt").read()
    
    async for event in analyzer.analyze_streaming(
        contract_text=text,
        contract_id="TEST-001",
        analysis_id="test-123"
    ):
        print(event)

asyncio.run(main())
```

## API Response Format

### Analysis Result

```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "contract_id": "FDOT-2024-001",
  "risk_level": "HIGH",
  "overall_score": 78.5,
  "executive_summary": "This contract contains several high-risk clauses...",
  "findings": [
    {
      "clause_type": "Indemnification",
      "risk_level": "HIGH",
      "concern": "Unlimited indemnification obligation",
      "recommendation": "Cap indemnification at 12 months of fees"
    }
  ],
  "recommendations": [
    "Add cap on indemnification obligations",
    "Clarify termination for convenience provisions",
    ...
  ],
  "compliance_issues": [
    "Missing FDOT compliance clause",
    "Insufficient insurance requirements"
  ]
}
```

### Progress Stream Events

```json
// Progress update
{
  "type": "progress",
  "data": {
    "stage": "risk_assessment",
    "percentage": 45,
    "message": "Assessing risks for 5 clauses",
    "detail": null
  }
}

// Result
{
  "type": "result",
  "data": { /* full analysis result */ }
}

// Complete
{
  "type": "complete"
}

// Error
{
  "type": "error",
  "message": "Failed to parse PDF"
}
```

## Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional with defaults
OPENAI_MODEL=gpt-4o-mini
AWS_REGION=us-east-1
FLASK_ENV=development
FLASK_DEBUG=1
LOG_LEVEL=INFO
```

### AWS Secrets Manager (Production)

```bash
# Create secret
aws secretsmanager create-secret \
  --name openai-api-key \
  --secret-string "sk-..."

# Export ARN
export OPENAI_API_KEY_ARN=arn:aws:secretsmanager:us-east-1:...
```

The system automatically fetches from Secrets Manager if env var not found.

## Performance Notes

**Analysis Time:**
- Small contract (2-5 pages): 30-60 seconds
- Medium contract (5-20 pages): 2-5 minutes
- Large contract (20+ pages): 5-15 minutes

**API Costs (gpt-4o-mini):**
- ~$0.03-0.10 per analysis
- Scales with contract length

**Optimization Tips:**
- Use gpt-3.5-turbo for faster analysis
- Implement caching for repeated contracts
- Process clauses in batches
- Set reasonable timeout (default: 300s)

## Troubleshooting

### "OPENAI_API_KEY not found"
```bash
# Solution: Set env var
export OPENAI_API_KEY=sk-your-key
```

### "Failed to extract text from PDF"
```bash
# Solution: Verify pdfplumber is installed
pip install pdfplumber

# Check PDF isn't encrypted
```

### "Stream disconnected"
```bash
# Solution: Check API server logs
# Verify CORS is enabled (default: yes)
# Check browser console for errors
```

### "Analysis taking too long"
```bash
# Solution: 
# 1. Use smaller contract
# 2. Increase timeout: timeout = 600 in Flask
# 3. Use faster model: gpt-3.5-turbo
```

## Next Steps

1. **Read** `IMPLEMENTATION_GUIDE.md` for deep dive
2. **Deploy** to AWS Lambda using `schemas/lambda-iam-policy.json`
3. **Customize** analysis rules and templates
4. **Monitor** with CloudWatch logs
5. **Integrate** with your workflow

## Architecture Overview

```
Browser
   |
   | POST /analyze (file)
   v
[API] --POST--> OpenAI
   ^
   | SSE stream
   |
Browser (EventSource)
```

## Support

- **GitHub Issues:** https://github.com/atlanticpipe/CR2A/issues
- **Email:** support@atlanticpipe.us
- **Documentation:** See `IMPLEMENTATION_GUIDE.md`

---

**Version:** 0.2.0 (LLM Analysis + Streaming)  
**Last Updated:** December 23, 2025
