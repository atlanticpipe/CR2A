# 🚨 IMMEDIATE ACTION REQUIRED - Lambda Fix

## STATUS: All source files confirmed to exist ✓

All 10 orchestrator Python files exist in `src/orchestrator/` and were last updated 10 hours ago. They need to be copied to `cr2a-lambda-build/orchestrator/`.

## Files That Need To Be Copied

From `src/orchestrator/` to `cr2a-lambda-build/orchestrator/`:

1. ✅ `__init__.py` (exists in src)
2. ✅ `analyzer.py` (exists in src) ← **CRITICAL - This is what Lambda needs!**
3. ✅ `cli.py` (exists in src)
4. ✅ `config.py` (exists in src)
5. ✅ `mime_utils.py` (exists in src)
6. ✅ `models.py` (exists in src)
7. ✅ `openai_client.py` (exists in src)
8. ✅ `pdf_export.py` (exists in src)
9. ✅ `policy_loader.py` (exists in src)
10. ✅ `validator.py` (exists in src)

## Command To Fix This NOW

```bash
# Clone the repo if you haven't
git clone https://github.com/atlanticpipe/CR2A.git
cd CR2A

# Copy all orchestrator files
cp src/orchestrator/__init__.py cr2a-lambda-build/orchestrator/
cp src/orchestrator/analyzer.py cr2a-lambda-build/orchestrator/
cp src/orchestrator/cli.py cr2a-lambda-build/orchestrator/
cp src/orchestrator/config.py cr2a-lambda-build/orchestrator/
cp src/orchestrator/mime_utils.py cr2a-lambda-build/orchestrator/
cp src/orchestrator/models.py cr2a-lambda-build/orchestrator/
cp src/orchestrator/openai_client.py cr2a-lambda-build/orchestrator/
cp src/orchestrator/pdf_export.py cr2a-lambda-build/orchestrator/
cp src/orchestrator/policy_loader.py cr2a-lambda-build/orchestrator/
cp src/orchestrator/validator.py cr2a-lambda-build/orchestrator/

# Commit and push
git add cr2a-lambda-build/orchestrator/
git commit -m "Copy orchestrator files to Lambda build directory"
git push origin main

# Deploy to Lambda
cd cr2a-lambda-build
zip -r ../lambda-deployment.zip .
aws lambda update-function-code --function-name YOUR_FUNCTION_NAME --zip-file fileb://../lambda-deployment.zip
```

## Or Use The Script I Created

```bash
chmod +x copy_orchestrator_files.sh
./copy_orchestrator_files.sh
git add cr2a-lambda-build/orchestrator/
git commit -m "Copy orchestrator files to Lambda build"
git push
```

## Why This Happened

Your deployment process copies the `src/` directory but apparently never copied the orchestrator files to the Lambda build directory. The `cr2a-lambda-build/orchestrator/` only has the `config/` subdirectory.

## Verification

After copying, you should have:
```
cr2a-lambda-build/orchestrator/
├── __init__.py          ← NEW
├── analyzer.py          ← NEW (fixes the ImportError!)
├── cli.py               ← NEW
├── config.py            ← NEW
├── config/              ← EXISTING
│   └── runtime_v1.json
├── mime_utils.py        ← NEW
├── models.py            ← NEW
├── openai_client.py     ← NEW
├── pdf_export.py        ← NEW
├── policy_loader.py     ← NEW
└── validator.py         ← NEW
```

## Expected Result After Fix

Your Lambda logs should show:
```
✓ Lambda handler invoked
✓ Attempting to import Mangum handler from src.api.main
✓ Successfully imported Mangum handler
✓ Calling Mangum handler...
✓ Handler completed successfully
```

The wrapper I created (`lambda_handler.py`) diagnosed this perfectly!
