# OIDC Permissions Fix for GitHub Workflows

## 🚨 Issue Resolved
**Error**: `Credentials could not be loaded, please check your action inputs: Could not load credentials from any providers`  
**Root Cause**: Missing `id-token: write` permission for OIDC authentication in workflow jobs

## 🔧 Fix Applied

### Updated Workflow Jobs with OIDC Permissions

#### 1. `deploy-lambda.yml` - Fixed `get_layer_arns` job
```yaml
# Before - Missing permissions
get_layer_arns:
  runs-on: ubuntu-latest
  outputs: ...

# After - Added OIDC permissions
get_layer_arns:
  runs-on: ubuntu-latest
  permissions:
    id-token: write    # Required for OIDC authentication
    contents: read     # Required for checkout
  outputs: ...
```

#### 2. `deploy-worker-lambdas.yml` - Fixed `get_layer_arn` job
```yaml
# Before - Missing permissions
get_layer_arn:
  runs-on: ubuntu-latest
  outputs: ...

# After - Added OIDC permissions
get_layer_arn:
  runs-on: ubuntu-latest
  permissions:
    id-token: write    # Required for OIDC authentication
    contents: read     # Required for checkout
  outputs: ...
```

## 📋 OIDC Permission Requirements

### Required Permissions for AWS Authentication
Every job that uses `aws-actions/configure-aws-credentials@v4` needs:

```yaml
permissions:
  id-token: write    # Allows GitHub to generate OIDC tokens
  contents: read     # Allows access to repository contents
```

### Why This is Needed
- **OIDC Authentication**: GitHub Actions uses OpenID Connect to authenticate with AWS
- **Token Generation**: `id-token: write` allows GitHub to create JWT tokens
- **AWS Role Assumption**: AWS IAM role trusts GitHub's OIDC provider
- **Secure Authentication**: No need to store AWS credentials as secrets

## ✅ Jobs with Correct Permissions

### Already Fixed Jobs
These jobs already had proper OIDC permissions:
- ✅ `deploy_api` in `deploy-lambda.yml`
- ✅ `deploy_functions` in `deploy-worker-lambdas.yml`
- ✅ `verify_deployment` jobs in both workflows
- ✅ All jobs in `publish-layers.yml`

### Newly Fixed Jobs
These jobs were missing permissions and are now fixed:
- ✅ `get_layer_arns` in `deploy-lambda.yml`
- ✅ `get_layer_arn` in `deploy-worker-lambdas.yml`

## 🔍 How to Identify Missing OIDC Permissions

### Error Symptoms
```
Error: Credentials could not be loaded, please check your action inputs
It looks like you might be trying to authenticate with OIDC. Did you mean to set the `id-token` permission?
```

### Quick Check
Look for jobs that:
1. Use `aws-actions/configure-aws-credentials@v4`
2. Don't have `permissions:` block
3. Or have `permissions:` but missing `id-token: write`

### Fix Template
```yaml
job_name:
  runs-on: ubuntu-latest
  permissions:
    id-token: write    # Add this
    contents: read     # Add this
  steps:
    - uses: actions/checkout@v4
    - uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: ${{ secrets.AWS_LAMBDA_DEPLOY_ROLE_ARN }}
        aws-region: us-east-1
```

## 🚀 Deployment Impact

### Immediate Benefits
- ✅ **Workflows run successfully** without credential errors
- ✅ **Layer ARNs retrieved** properly from AWS
- ✅ **Function deployments proceed** without authentication failures
- ✅ **CORS fix deployment** can now complete successfully

### No Breaking Changes
- ✅ **Existing functionality preserved**
- ✅ **Same IAM role used** (`cr2a-github-actions`)
- ✅ **No additional AWS permissions needed**
- ✅ **Backward compatible** with existing workflows

## 📊 Workflow Status After Fix

### `deploy-lambda.yml`
```
✅ detect_changes - No AWS calls (no permissions needed)
✅ get_layer_arns - Fixed with OIDC permissions
✅ deploy_api - Already had OIDC permissions
✅ verify_deployment - Already had OIDC permissions
```

### `deploy-worker-lambdas.yml`
```
✅ detect_changes - No AWS calls (no permissions needed)
✅ get_layer_arn - Fixed with OIDC permissions
✅ deploy_functions - Already had OIDC permissions
✅ verify_deployment - Already had OIDC permissions
```

### `publish-layers.yml`
```
✅ All jobs already had proper OIDC permissions
```

## 🎉 Result

The OIDC permissions fix ensures that:
- **All workflows run without authentication errors**
- **Layer ARNs are properly retrieved from AWS**
- **CORS fix can be deployed successfully**
- **Future deployments work reliably**

The workflows are now properly configured for secure OIDC authentication with AWS.