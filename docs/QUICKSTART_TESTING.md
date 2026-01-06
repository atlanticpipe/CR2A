# CR2A Testing - 5 Minute Quick Start

## 🚀 Fastest Way to Test: Demo Mode (No Backend)

**Time: 1 minute**

```bash
# Terminal 1
cd CR2A/webapp
python3 -m http.server 8000

# Then in browser:
# 1. Open http://localhost:8000
# 2. Click "Run Demo" button
# 3. Watch timeline simulate: Queued → OCR → Validation → LLM → Export
# 4. Click "Download Report" when complete
```

✅ **Tests:** Frontend UI, state management, mock workflow

---

## 🔗 Frontend + Local Backend (5 minutes)

**Time: 2 minutes setup + 3 minutes testing**

### Terminal 1: Start Backend
```bash
cd CR2A

# Setup once:
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run:
export FLASK_APP=src/api/main.py
export FLASK_ENV=development
flask run
# → Backend at http://localhost:5000
```

### Terminal 2: Start Frontend
```bash
cd CR2A/webapp
python3 -m http.server 8000
# → Frontend at http://localhost:8000
```

### In Browser:
```javascript
// Console (F12):
// Update API URL to point to local backend
window.CR2A_API_BASE = "http://localhost:5000";
location.reload();

// Then:
// 1. Fill in Contract ID: "TEST-001"
// 2. Select a file from your computer
// 3. Click Submit
// 4. Watch the timeline (you'll hit Step 2/3 of the main workflow)
```

✅ **Tests:** Frontend + API integration, file upload flow

---

## 🧪 Test Individual Components via Console

### Test 1: File Upload Handler
```javascript
// In browser console (F12):
const mockFile = new File(['contract'], 'test.pdf', { type: 'application/pdf' });
const fileInput = document.querySelector("#file-input");
fileInput.files = { 0: mockFile, length: 1 };
fileInput.dispatchEvent(new Event('change'));
console.log(document.querySelector("#file-name").textContent);
// → Should show "test.pdf (0.00 MB)"
```

### Test 2: API Configuration
```javascript
// In browser console:
console.log(window._env);
// → Should show:
// {
//   API_BASE_URL: "http://localhost:5000",
//   API_AUTH_TOKEN: "Bearer mvp-token"
// }
```

### Test 3: Check API Endpoints
```bash
# Terminal (with backend running):

# Health check
curl http://localhost:5000/health

# Get presigned URL
curl "http://localhost:5000/upload-url?filename=test.pdf&contentType=application/pdf&size=1024" \
  -H "Authorization: Bearer mvp-token"
```

---

## 🔍 Test Python Code Directly

### Test Document Analysis
```bash
# Terminal:
cd CR2A

# Create test script
cat > test_analyzer.py << 'EOF'
from src.core.analyzer import analyze_to_json
from pathlib import Path

# Test with test_config.json (simple text file)
result = analyze_to_json(
    input_path="test_config.json",
    repo_root=".",
    ocr="auto"
)

print("Success! Keys:", list(result.keys()))
print("Section I:", result.get("SECTION_I", {}))
EOF

python3 test_analyzer.py
```

✅ **Tests:** Core analysis logic

---

## 📋 Complete Test Matrix

| Test | Command | Time | Scope |
|------|---------|------|-------|
| **Demo Mode** | Click "Run Demo" | 1 min | Frontend only |
| **Frontend + Backend** | Start 2 terminals | 5 min | Frontend + API |
| **API Endpoints** | curl commands | 2 min | Backend endpoints |
| **Analyzer** | `python3 test_analyzer.py` | 2 min | Analysis core logic |
| **Full Pipeline** | With AWS config | 10 min | End-to-end |

---

## 🎯 Testing Checklist

### ✅ Step 1: User Uploads File

- [ ] Open http://localhost:8000
- [ ] Form displays (Contract ID input, file upload, LLM toggle)
- [ ] Drag & drop file works
- [ ] File name shows in UI
- [ ] "Submit" button clickable

### ✅ Step 2: Request Presigned URL

- [ ] Backend `/upload-url` endpoint returns presigned URL
- [ ] Presigned URL has correct S3 bucket and key

**Test:**
```bash
curl "http://localhost:5000/upload-url?filename=test.pdf&contentType=application/pdf&size=1024"
```

### ✅ Step 3: Upload File to S3 (or local)

- [ ] File uploads successfully via presigned URL
- [ ] Browser shows "Upload complete"

**Or test locally:**
```bash
# Using /upload-local endpoint
curl -X POST http://localhost:5000/upload-local \
  -F "file=@test_config.json" \
  -F "key=uploads/test/test.json"
```

### ✅ Step 4: Submit Analysis

- [ ] Job ID returned
- [ ] Timeline shows "Queued" → "Processing"
- [ ] Status polling starts

**Test:**
```bash
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"key": "uploads/test.pdf", "contract_id": "TEST-001", "llm_enabled": false}'
```

---

## 🐛 Troubleshooting

### Issue: "API_BASE_URL not set"
```javascript
// Fix in console:
window.CR2A_API_BASE = "http://localhost:5000";
location.reload();
```

### Issue: CORS Error
- Ensure backend running on same port as curl command
- Check `API_BASE_URL` matches Flask server

### Issue: File Upload Fails
- Check file size < 500 MB
- Verify contract ID is filled in
- Check Network tab (F12) for response details

### Issue: Backend Import Error
```bash
# Ensure Python path includes src:
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
flask run
```

### Issue: Port Already in Use
```bash
# Use different port:
python3 -m http.server 8001
# Update window.CR2A_API_BASE = "http://localhost:5001"
```

---

## 📖 Key Files by Purpose

**Want to test...**

| Goal | File | How |
|------|------|-----|
| **Frontend UI** | `webapp/app.js` | Browser console + demo mode |
| **File Upload** | `webapp/app.js` line 201 | Set breakpoint in VS Code |
| **API Endpoints** | `src/api/main.py` | curl commands |
| **Document Parsing** | `src/core/analyzer.py` | Python REPL or debug script |
| **Clause Classification** | `worker/lambda_analyze_chunk.py` | Unit test or debug script |

---

## 🔗 Next Steps

1. **Start with Demo Mode** - Click "Run Demo" (1 min)
2. **Run Full Stack Locally** - Start backend + frontend (5 min)
3. **Test API Endpoints** - Use curl from terminal (2 min)
4. **Debug in VS Code** - Set breakpoints and step through (5 min)
5. **Write Unit Tests** - Add to `tests/` directory (10 min)

---

## 💡 Pro Tips

**Tip 1: Keep frontend and backend URLs in sync**
```javascript
// In webapp/env.js:
window._env = {
  API_BASE_URL: "http://localhost:5000",  // Must match flask run port
  API_AUTH_TOKEN: "Bearer mvp-token"
};
```

**Tip 2: Use VS Code REST Client extension**
- Install: "REST Client" by Huachao Zheng
- Create `.http` file with test requests
- Click "Send Request" to test endpoints

**Tip 3: Monitor logs in real-time**
```bash
# Terminal 3 (while backend running):
export FLASK_ENV=development
export CR2A_LOG_LEVEL=DEBUG
# See all request/response logs
```

**Tip 4: Use browser DevTools Network tab**
- F12 → Network tab
- Reload page to capture all requests
- Click each request to inspect headers/body/response

---

## ⚡ One-Liner Commands

```bash
# Demo mode only
cd CR2A/webapp && python3 -m http.server 8000

# Backend only
cd CR2A && flask run

# Backend + Frontend (2 terminals)
# Terminal 1:
cd CR2A && flask run
# Terminal 2:
cd CR2A/webapp && python3 -m http.server 8000

# Test API endpoint
curl http://localhost:5000/health

# Test with file
curl -F "file=@test_config.json" http://localhost:5000/upload-local
```

---

## 📞 Still Stuck?

1. Check browser console (F12) for JavaScript errors
2. Check backend terminal for Flask errors
3. Check Network tab (F12) for HTTP errors
4. Review detailed debugging guides in `docs/` folder
