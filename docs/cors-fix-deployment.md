# CORS Fix Deployment via GitHub Workflows

## 🎯 Issue Resolution
**Problem**: CORS error blocking webapp requests to API Gateway  
**Error**: `Access to fetch at 'https://62k6wc3sqe.execute-api.us-east-1.amazonaws.com/prod/upload-url' from origin 'https://velmur.info' has been blocked by CORS policy`

## 🔧 Changes Made

### 1. Updated API Lambda Function (`src/api/main.py`)

**Enhanced CORS Configuration**:
```python
# Before - Generic CORS
allow_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["content-type", "authorization"],
)

# After - Specific CORS for webapp
allow_origins = os.getenv("CORS_ALLOW_ORIGINS", "https://velmur.info")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["content-type", "authorization", "x-amz-date", "x-api-key", "x-amz-security-token"],
)
```

**Key Improvements**:
- ✅ **Specific origin**: Defaults to `https://velmur.info` instead of wildcard
- ✅ **Credentials support**: Enables `allow_credentials=True` for auth headers
- ✅ **Complete methods**: Includes all HTTP methods needed by webapp
- ✅ **AWS headers**: Adds AWS-specific headers for S3 presigned URLs

### 2. Updated Deployment Workflow (`.github/workflows/deploy-lambda.yml`)

**Added Environment Variables**:
```yaml
aws lambda update-function-configuration \
  --environment Variables='{
    "CORS_ALLOW_ORIGINS": "https://velmur.info,https://www.velmur.info",
    "AWS_REGION": "us-east-1",
    "CR2A_LOG_LEVEL": "INFO"
  }'
```

**Benefits**:
- ✅ **Multiple domains**: Supports both `velmur.info` and `www.velmur.info`
- ✅ **Environment-driven**: CORS origins configurable via Lambda environment
- ✅ **Deployment automation**: Set automatically during GitHub workflow deployment

## 🚀 Deployment Process

### Automatic Deployment via GitHub
The CORS fix will be deployed automatically when you:

1. **Trigger the workflow**:
   ```bash
   # Deploy API Lambda with CORS fix
   gh workflow run deploy-lambda.yml
   ```

2. **Or push changes**:
   ```bash
   git add src/api/main.py .github/workflows/deploy-lambda.yml
   git commit -m "Fix CORS configuration for webapp"
   git push origin main
   ```

### What Happens During Deployment

1. **Layer Management**: Uses existing layers (no rebuild needed)
2. **Function Update**: Deploys updated `src/api/main.py` with CORS fix
3. **Environment Config**: Sets `CORS_ALLOW_ORIGINS` environment variable
4. **Configuration Update**: Updates Lambda function configuration
5. **Verification**: Confirms deployment success

## 📊 Expected Results

### Before Fix
```
❌ CORS Error: Access blocked by CORS policy
❌ Preflight requests fail
❌ Webapp cannot call API endpoints
❌ File uploads blocked
```

### After Fix
```
✅ CORS Headers: Proper Access-Control-Allow-Origin headers
✅ Preflight Success: OPTIONS requests handled correctly
✅ API Calls Work: Webapp can call all endpoints
✅ File Uploads: S3 presigned URL uploads work
```

## 🔍 Testing the Fix

### 1. Check CORS Headers
```bash
# Test preflight request
curl -X OPTIONS \
  -H "Origin: https://velmur.info" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type,Authorization" \
  https://62k6wc3sqe.execute-api.us-east-1.amazonaws.com/prod/upload-url

# Should return CORS headers:
# Access-Control-Allow-Origin: https://velmur.info
# Access-Control-Allow-Methods: GET,POST,PUT,DELETE,OPTIONS
# Access-Control-Allow-Headers: content-type,authorization,x-amz-date,x-api-key,x-amz-security-token
```

### 2. Test from Webapp
```javascript
// Test from velmur.info browser console
fetch('https://62k6wc3sqe.execute-api.us-east-1.amazonaws.com/prod/health')
  .then(response => response.json())
  .then(data => console.log('Success:', data))
  .catch(error => console.error('Error:', error));
```

### 3. Verify Environment Variables
```bash
# Check Lambda environment variables
aws lambda get-function-configuration \
  --function-name cr2a-api \
  --query 'Environment.Variables.CORS_ALLOW_ORIGINS'
```

## 🛡️ Security Considerations

### Production CORS Configuration
- ✅ **Specific origins**: Only allows `velmur.info` and `www.velmur.info`
- ✅ **No wildcards**: Prevents unauthorized cross-origin access
- ✅ **Credential support**: Enables secure authentication headers
- ✅ **Method restrictions**: Only allows necessary HTTP methods

### Environment Variable Security
- ✅ **Configurable**: CORS origins can be updated without code changes
- ✅ **Multiple domains**: Supports comma-separated origin list
- ✅ **Deployment-time**: Set during automated deployment process

## 📋 Troubleshooting

### If CORS Errors Persist

1. **Check deployment status**:
   ```bash
   gh workflow list
   gh run view <run-id>
   ```

2. **Verify environment variables**:
   ```bash
   aws lambda get-function-configuration --function-name cr2a-api
   ```

3. **Check function logs**:
   ```bash
   aws logs tail /aws/lambda/cr2a-api --follow
   ```

4. **Test specific endpoint**:
   ```bash
   curl -v -X OPTIONS -H "Origin: https://velmur.info" \
     https://62k6wc3sqe.execute-api.us-east-1.amazonaws.com/prod/upload-url
   ```

### Common Issues
- **Deployment not complete**: Wait for GitHub workflow to finish
- **Environment variables not set**: Check Lambda configuration
- **Cache issues**: Clear browser cache and try again
- **Multiple origins**: Ensure comma-separated format in environment variable

## ✅ Success Criteria

After successful deployment:
- ✅ No CORS errors in browser console
- ✅ Webapp can call `/upload-url` endpoint
- ✅ File uploads work without errors
- ✅ Status polling functions correctly
- ✅ Download links are accessible

The CORS fix will be deployed automatically through the GitHub workflow, ensuring the webapp can properly communicate with the API Gateway.