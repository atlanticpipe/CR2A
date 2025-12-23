# CR2A LLM Analysis Implementation Guide

## Overview

This guide documents the implementation of **LLM-powered contract analysis** with **streaming progress updates** in the CR2A system. The test branch now includes a complete analysis pipeline that uses GPT-4 for the entire analysis process—not just verification and refinement.

## What's New

### Phase 4: LLM Analyzer Engine
**File:** `src/core/llm_analyzer.py`

The core analysis engine that orchestrates the entire contract analysis workflow:

```
Input Contract Text
    ↓
[1] Extract Clauses (LLM)
    ↓
[2] Assess Risks (LLM per clause)
    ↓
[3] Check Compliance (LLM)
    ↓
[4] Generate Summary (LLM)
    ↓
[5] Generate Recommendations (LLM)
    ↓
AnalysisResult Output
```

#### Key Components

**LLMAnalyzer Class**
- `analyze()` - Synchronous analysis (blocking)
- `analyze_streaming()` - Asynchronous analysis with progress updates (non-blocking)

**Data Classes**
- `AnalysisStage` - Enum of progress stages
- `ProgressUpdate` - Progress event structure
- `ClauseFinding` - Individual clause risk assessment
- `AnalysisResult` - Complete analysis output

#### Usage Example

```python
from src.core.llm_analyzer import LLMAnalyzer

# Initialize
analyzer = LLMAnalyzer(api_key="sk-...", model="gpt-4o-mini")

# Synchronous analysis (blocking)
result = analyzer.analyze(
    contract_text=document_text,
    contract_id="FDOT-2024-001",
    analysis_id="unique-analysis-id"
)

# Asynchronous with streaming (non-blocking)
async for update in analyzer.analyze_streaming(...):
    if isinstance(update, ProgressUpdate):
        print(f"{update.stage}: {update.percentage}%")
    elif isinstance(update, AnalysisResult):
        print(f"Complete: {update.risk_level}")
```

### Phase 5: Document Processor Service
**File:** `src/services/document_processor.py`

Handles text extraction from various document formats:

```python
from src.services.document_processor import DocumentProcessor

processor = DocumentProcessor()

# Supports: PDF, DOCX, TXT
text = processor.extract_text("/path/to/contract.pdf")
info = processor.get_file_info("/path/to/contract.pdf")
```

**Features:**
- PDF extraction with `pdfplumber` (handles complex layouts)
- DOCX extraction with `python-docx` (includes tables)
- TXT extraction with fallback encoding handling
- File size and format metadata

### Phase 6: REST API with Streaming
**File:** `src/api/main.py`

Flask REST API with **Server-Sent Events (SSE)** for progress streaming.

#### Endpoints

**POST /analyze**
```bash
curl -X POST http://localhost:5000/analyze \
  -F "file=@contract.pdf" \
  -F "contract_id=FDOT-2024-001"

Response (202 Accepted):
{
  "analysis_id": "uuid-here",
  "contract_id": "FDOT-2024-001",
  "status": "queued",
  "submitted_at": "2024-12-23T15:00:00Z"
}
```

**GET /analyze/{analysis_id}/stream** (Server-Sent Events)
```bash
curl http://localhost:5000/analyze/uuid-here/stream

Stream Events:
data: {"type": "progress", "data": {"stage": "clause_extraction", "percentage": 25, "message": "..."}}
data: {"type": "progress", "data": {...}}
data: {"type": "result", "data": {"risk_level": "HIGH", ...}}
data: {"type": "complete"}
```

**GET /status/{analysis_id}**
```bash
curl http://localhost:5000/status/uuid-here

Response:
{
  "analysis_id": "uuid-here",
  "status": "processing",
  "progress": {"stage": "risk_assessment", "percentage": 45, ...}
}
```

**GET /results/{analysis_id}**
```bash
curl http://localhost:5000/results/uuid-here

Response:
{
  "analysis_id": "uuid-here",
  "contract_id": "FDOT-2024-001",
  "risk_level": "HIGH",
  "overall_score": 78.5,
  "findings": [...],
  "recommendations": [...]
}
```

**GET /download/{analysis_id}**
- Download report as PDF (currently returns JSON, implement PDF export)

**GET /analyses**
- List all analyses with pagination

#### API Design Pattern

The streaming API uses a **deferred async pattern**:

1. **Client** POSTs file → **Server** returns `202 Accepted` with `analysis_id`
2. **Client** connects to SSE stream with `analysis_id`
3. **Server** processes async and yields progress events
4. **Server** yields final result and closes stream
5. **Client** handles completion or polls `/status` and `/results`

This allows:
- Long-running analyses without timeouts
- Real-time progress updates
- Decoupled submission and result retrieval
- Graceful error handling

### Phase 7: Frontend with Live Progress
**Files:** `webapp/app.js`, `webapp/index.html`

#### Key Features

**Progress Streaming**
```javascript
// EventSource connected to SSE stream
const eventSource = new EventSource(`/analyze/${analysisId}/stream`);

eventSource.addEventListener('message', (event) => {
    const message = JSON.parse(event.data);
    
    if (message.type === 'progress') {
        updateProgressBar(message.data.percentage);
        updateStageIndicator(message.data.stage);
    } else if (message.type === 'result') {
        displayResults(message.data);
    }
});
```

**Result Display**
- Risk level badge with color coding
- Finding cards with clause type, risk level, concern, recommendation
- Compliance issues list
- Actionable recommendations
- Download button (for PDF export)

**UI/UX Enhancements**
- File validation before upload
- Progress bar with percentage
- Stage-by-stage indicator
- Error messaging with auto-dismiss
- Result cards with risk highlighting

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Browser)                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  HTML Form → Submit File → Connect SSE → Display Viz   │ │
│  │  webapp/index.html, webapp/app.js                      │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────┬──────────────────────────────────────────┘
                  │ HTTP/SSE
┌─────────────────▼──────────────────────────────────────────┐
│                   API Layer (Flask)                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  POST /analyze → 202 Accepted + analysis_id           │ │
│  │  GET /analyze/{id}/stream → SSE with progress         │ │
│  │  GET /status/{id}, GET /results/{id}                  │ │
│  │  src/api/main.py                                      │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────┬──────────────────────────────────────────┘
                  │
        ┌─────────┴────────────┐
        │                      │
    ┌───▼────────────────┐  ┌──▼──────────────────┐
    │ Document Processing│  │ LLM Analysis Engine │
    │ src/services/      │  │ src/core/llm_      │
    │ document_processor │  │ analyzer.py        │
    │                    │  │                    │
    │ • PDF extraction   │  │ • Clause extract   │
    │ • DOCX extraction  │  │ • Risk assessment  │
    │ • TXT parsing      │  │ • Compliance check │
    │                    │  │ • Summary gen      │
    └────────────────────┘  │ • Recommend gen    │
                            └────────────────────┘
                                    │
                                    ▼
                            OpenAI API (GPT-4)
```

## Development Workflow

### 1. Local Testing

**Setup**
```bash
git clone https://github.com/atlanticpipe/CR2A.git
git checkout test
cd CR2A

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Configure Environment**
```bash
cat > .env << EOF
OPENAI_API_KEY="sk-..."
AWS_REGION="us-east-1"
OPENAI_MODEL="gpt-4o-mini"
FLASK_DEBUG="1"
EOF
```

**Run Locally**

*Terminal 1: API Server*
```bash
FLASK_APP=src.api.main FLASK_ENV=development python -m flask run
```

*Terminal 2: Frontend*
```bash
cd webapp
python3 -m http.server 8000
```

Visit: `http://localhost:8000`

### 2. API Testing with cURL

**Submit Analysis**
```bash
curl -X POST http://localhost:5000/analyze \
  -F "file=@test_contract.pdf" \
  -F "contract_id=TEST-001"
```

**Stream Progress**
```bash
curl -N http://localhost:5000/analyze/{analysis_id}/stream | grep -o 'data:.*'
```

**Get Results**
```bash
curl http://localhost:5000/results/{analysis_id} | jq
```

### 3. Testing with Python

```python
import asyncio
from src.core.llm_analyzer import LLMAnalyzer

async def test():
    analyzer = LLMAnalyzer(api_key="sk-...")
    
    contract_text = """Sample contract clause about indemnification..."""
    
    async for update in analyzer.analyze_streaming(
        contract_text=contract_text,
        contract_id="TEST-001",
        analysis_id="test-123"
    ):
        print(f"{update}")

asyncio.run(test())
```

## Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|----------|
| `OPENAI_API_KEY` | (required) | OpenAI API key for GPT calls |
| `AWS_REGION` | `us-east-1` | AWS region for S3 and Secrets Manager |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model to use for analysis |
| `FLASK_ENV` | `development` | Flask environment |
| `FLASK_DEBUG` | `0` | Enable Flask debug mode |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

### Secret Resolution Order

The system uses `get_secret_env_or_aws()` for flexible secret management:

1. Check environment variable
2. If not found, check AWS Secrets Manager ARN env var
3. If ARN found, fetch secret from Secrets Manager
4. Cache locally for downstream library access

**Example:**
```python
api_key = get_secret_env_or_aws("OPENAI_API_KEY", "OPENAI_API_KEY_ARN")
```

## Cost Optimization

### API Calls Per Analysis

**Current Implementation:**
- 1 call: Clause extraction
- N calls: Risk assessment (1 per clause, limited to first 20)
- 1 call: Compliance check
- 1 call: Summary generation
- 1 call: Recommendation generation

**Total: ~24 API calls per analysis**

### Cost Estimate (using gpt-4o-mini @ $0.15/$0.60 per 1M tokens)

- Avg contract: 5,000 tokens
- Per analysis: ~200k tokens processed
- **Cost per analysis: ~$0.03-0.10**

### Optimization Opportunities

1. **Batch Processing**: Process multiple clauses in single call
2. **Caching**: Cache clause types and risk assessments
3. **Cheaper Models**: Use gpt-3.5-turbo for initial filtering
4. **Sampling**: Analyze representative clauses, not all

## Error Handling

### API Layer

```
File Upload → Validation → Extract Text → LLM Analysis → Result
              ↓
          413 if >500MB
          400 if invalid format
          500 if extraction fails
          502 if LLM API down
```

### Frontend

- Automatic retry on network errors (3 attempts)
- Graceful degradation if SSE unavailable
- Error messages displayed to user with dismissal
- Stream error handling with connection fallback

### LLM Analyzer

- JSON parsing failures return None/empty lists
- API errors caught and logged
- Timeout handling (built into OpenAI SDK)
- Graceful degradation on partial failures

## Production Deployment

### AWS Lambda Setup

```bash
# Package dependencies
zip -r lambda-deployment.zip src/ requirements.txt

# Deploy to Lambda
aws lambda create-function \
  --function-name cr2a-analyzer \
  --zip-file fileb://lambda-deployment.zip \
  --handler src.api.main.app \
  --runtime python3.11 \
  --timeout 300 \
  --memory-size 1024 \
  --environment Variables={OPENAI_API_KEY_ARN=arn:aws:...}
```

### S3 Storage

- Upload contracts to S3 before analysis
- Store results in S3 with analysis_id key
- Enable versioning for audit trail

### GitHub Actions CI/CD

```yaml
# .github/workflows/deploy.yml
name: Deploy to Lambda
on: [push]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: aws-actions/configure-aws-credentials@v1
      - run: pip install -r requirements.txt
      - run: zip -r deployment.zip src/
      - run: aws lambda update-function-code --function-name cr2a-analyzer --zip-file fileb://deployment.zip
```

## Next Steps

### Planned Enhancements

1. **PDF Export** - Generate branded PDF reports
2. **Batch Processing** - Multiple contracts at once
3. **Custom Rules** - Configurable analysis rules per client
4. **Template Library** - Pre-analyzed contract templates
5. **Dashboard** - Analytics and reporting
6. **Multi-language** - Support non-English contracts
7. **Webhook Integration** - Notify on completion
8. **Database** - Persistent result storage

### Testing Roadmap

- [ ] Unit tests for LLM analyzer
- [ ] Integration tests for API endpoints
- [ ] E2E tests for full workflow
- [ ] Performance benchmarks
- [ ] Cost tracking and optimization

## Troubleshooting

### API Key Issues
```
Error: OPENAI_API_KEY not found
Solution: Set OPENAI_API_KEY env var or configure AWS Secrets Manager
```

### PDF Extraction Failures
```
Error: Failed to extract text from PDF
Solution: Ensure pdfplumber is installed and PDF is not encrypted
```

### Streaming Disconnects
```
Error: Stream error in browser console
Solution: Check API server logs, verify CORS settings
```

### Timeout Issues
```
Error: Analysis takes >5 minutes
Solution: Increase Lambda/Flask timeout, optimize clause extraction
```

## References

- OpenAI API Docs: https://platform.openai.com/docs
- pdfplumber Docs: https://github.com/jsvine/pdfplumber
- Flask Streaming: https://flask.palletsprojects.com/en/latest/patterns/streaming/
- Server-Sent Events: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events

---

**Last Updated:** December 23, 2025
**Status:** Phase 7 Complete (Phases 1-7 Functional)
