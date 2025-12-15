# Lambda Deployment Instructions

## Problem Diagnosis

Your Lambda function was completing execution without running any handler code. The logs showed:
- Function initialization: ✓ Successful
- Handler execution: ✗ Missing (no application logs)
- Duration: 2.8 seconds (environment loading but no handler invocation)

## Root Cause

The Lambda handler configuration was either:
1. Not set correctly (missing or wrong path)
2. Unable to import the Mangum handler from `src.api.main`
3. Missing dependencies (mangum package)

## Solution Implemented

Created `lambda_handler.py` - a wrapper with comprehensive logging that:
- Logs all import attempts and errors
- Shows directory structure and Python environment
- Provides detailed error messages for debugging
- Returns proper HTTP error responses on failure

## Deployment Steps

### Step 1: Update Lambda Handler Configuration

1. Go to AWS Lambda Console
2. Select your CR2A Lambda function
3. Go to **Configuration** → **General configuration**
4. Click **Edit**
5. Set the **Handler** field to: `lambda_handler.handler`
6. Click **Save**

### Step 2: Deploy the Updated Code

You need to redeploy your Lambda function with the new `lambda_handler.py` file:

**Option A: ZIP Upload**
```bash
cd cr2a-lambda-build
zip -r ../lambda-deployment.zip .
aws lambda update-function-code --function-name YOUR_FUNCTION_NAME --zip-file fileb://../lambda-deployment.zip
```

**Option B: Manual Upload**
1. Create a ZIP of the entire `cr2a-lambda-build` directory
2. Go to Lambda Console → Code tab
3. Click "Upload from" → ".zip file"
4. Upload your ZIP file

### Step 3: Verify Dependencies

Ensure the `python/` directory contains all required dependencies:
- mangum
- fastapi
- boto3
- All other packages from requirements.txt

If dependencies are missing, install them:
```bash
pip install -t cr2a-lambda-build/python/ mangum fastapi
```

### Step 4: Test the Function

After deployment:
1. Go to Lambda Console → Test tab
2. Create a test event (use API Gateway AWS Proxy template)
3. Click **Test**
4. Check CloudWatch Logs

## Expected Log Output

With the new wrapper, you should see detailed logs:

```
================================================================================
Lambda handler invoked
Python version: 3.13.x
Working directory: /var/task
Directory contents: ['src', 'python', 'orchestrator', ...]
Event type: <class 'dict'>
Event keys: dict_keys(['resource', 'path', 'httpMethod', ...])
================================================================================
Attempting to import Mangum handler from src.api.main
Successfully imported Mangum handler
Handler type: <class 'mangum.adapter.Mangum'>
Calling Mangum handler...
Handler completed successfully
```

## Troubleshooting

### If You See ImportError

**Log message:** `ImportError: No module named 'src'`

**Solution:** The deployment package structure is wrong. Ensure:
- `src/` directory is at the root of the ZIP
- `src/api/main.py` exists
- All `__init__.py` files are present

### If You See "No module named 'mangum'"

**Solution:** Install mangum in the python/ directory:
```bash
pip install -t cr2a-lambda-build/python/ mangum
```

### If Logs Still Show No Output

1. Verify handler is set to `lambda_handler.handler`
2. Check that `lambda_handler.py` is at the root of your deployment package
3. Ensure the file was deployed (check Lambda console code viewer)

## Alternative Handler Paths

If you prefer not to use the wrapper, you can try:

1. **Direct Mangum handler:** `src.api.main.handler`
   - Only works if all dependencies are properly installed
   - Less visibility into import errors

2. **Keep the wrapper:** `lambda_handler.handler` (RECOMMENDED)
   - Provides detailed error logging
   - Makes debugging much easier

## Next Steps

1. Update Lambda handler configuration
2. Redeploy with lambda_handler.py
3. Test and check logs
4. If you see import errors, fix the package structure
5. Once working, the wrapper will call your FastAPI app via Mangum

## Questions?

Check the logs after each test. The wrapper provides:
- Exact error messages
- Directory structure
- Python path information
- Import success/failure details

This will tell you exactly what's wrong.
