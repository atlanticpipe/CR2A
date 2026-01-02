# IAM Permission Troubleshooting Guide

## 🚨 Current Issue
The GitHub Actions role still cannot publish Lambda layers after the initial fix attempt.

**Error**: `AccessDeniedException: lambda:PublishLayerVersion on resource: arn:aws:lambda:us-east-1:143895994429:layer:cr2a-shared-deps`

## 🔍 Troubleshooting Steps

### Step 1: Verify Current IAM Policy
Check what permissions the role currently has:

```bash
# List all policies attached to the role
aws iam list-attached-role-policies --role-name cr2a-github-actions

# Get inline policies
aws iam list-role-policies --role-name cr2a-github-actions

# Get specific policy content (replace POLICY_NAME)
aws iam get-role-policy --role-name cr2a-github-actions --policy-name POLICY_NAME
```

### Step 2: Check Trust Policy
Verify the role can be assumed by GitHub Actions:

```bash
aws iam get-role --role-name cr2a-github-actions --query 'Role.AssumeRolePolicyDocument'
```

### Step 3: Verify Policy Application
The policy might not have been applied correctly. Here are the exact steps:

#### Option A: AWS Console Method
1. Go to [AWS IAM Console](https://console.aws.amazon.com/iam/)
2. Click **Roles** in the left sidebar
3. Search for and click **cr2a-github-actions**
4. In the **Permissions** tab, you should see attached policies
5. Click on the policy name to edit it
6. Add the Lambda layer permissions (see below)

#### Option B: AWS CLI Method
```bash
# Create a new policy document
cat > lambda-layer-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "LambdaLayerManagement",
      "Effect": "Allow",
      "Action": [
        "lambda:PublishLayerVersion",
        "lambda:GetLayerVersion",
        "lambda:GetLayerVersionByArn",
        "lambda:ListLayerVersions",
        "lambda:DeleteLayerVersion"
      ],
      "Resource": [
        "arn:aws:lambda:us-east-1:143895994429:layer:cr2a-*"
      ]
    }
  ]
}
EOF

# Apply the policy (replace POLICY_NAME with actual policy name)
aws iam put-role-policy --role-name cr2a-github-actions --policy-name cr2a-lambda-layer-policy --policy-document file://lambda-layer-policy.json
```

## 🔧 Complete Policy Template

If you need to create/update the complete policy, here's a comprehensive template:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "LambdaFunctionManagement",
      "Effect": "Allow",
      "Action": [
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration",
        "lambda:GetFunction",
        "lambda:GetFunctionConfiguration",
        "lambda:ListFunctions"
      ],
      "Resource": [
        "arn:aws:lambda:us-east-1:143895994429:function:cr2a-*"
      ]
    },
    {
      "Sid": "LambdaLayerManagement",
      "Effect": "Allow",
      "Action": [
        "lambda:PublishLayerVersion",
        "lambda:GetLayerVersion",
        "lambda:GetLayerVersionByArn",
        "lambda:ListLayerVersions",
        "lambda:DeleteLayerVersion"
      ],
      "Resource": [
        "arn:aws:lambda:us-east-1:143895994429:layer:cr2a-*"
      ]
    },
    {
      "Sid": "S3DeploymentAccess",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::cr2a-deployment",
        "arn:aws:s3:::cr2a-deployment/*"
      ]
    }
  ]
}
```

## 🕐 Common Issues

### Issue 1: Policy Not Applied
- **Symptom**: Same error after "updating" policy
- **Cause**: Policy wasn't actually saved or applied
- **Fix**: Double-check the policy was saved in AWS Console

### Issue 2: Wrong Policy Name
- **Symptom**: Policy seems to exist but permissions don't work
- **Cause**: Updated wrong policy or created duplicate
- **Fix**: List all policies and verify the correct one is attached

### Issue 3: IAM Propagation Delay
- **Symptom**: Policy looks correct but still getting errors
- **Cause**: IAM changes can take up to 5 minutes to propagate
- **Fix**: Wait 5 minutes and try again

### Issue 4: Resource ARN Mismatch
- **Symptom**: Policy exists but specific resources denied
- **Cause**: ARN in policy doesn't match actual resource
- **Fix**: Verify account ID and region in policy match the error

## 🧪 Test the Fix

After updating the policy, test it:

```bash
# Test layer listing (should work if permissions are correct)
aws lambda list-layer-versions --layer-name cr2a-shared-deps --region us-east-1

# If the above works, try the workflow again
gh workflow run publish-layers.yml -f force_rebuild_all=true
```

## 🚨 Emergency Workaround

If you need to deploy immediately while fixing IAM:

1. **Temporarily use the old workflows** that build layers inline:
   ```bash
   # These still work because they use existing function permissions
   gh workflow run deploy-lambda.yml
   gh workflow run deploy-worker-lambdas.yml
   ```

2. **Disable the layer workflow** until IAM is fixed:
   - Comment out the `publish-layers.yml` triggers temporarily

## 📞 Next Steps

1. **Verify current IAM policy** using the commands above
2. **Apply the correct policy** using Console or CLI method
3. **Wait 5 minutes** for IAM propagation
4. **Test with a simple AWS CLI command** first
5. **Re-run the workflow** once CLI test passes

The key is making sure the policy is actually applied to the correct role and includes the exact permissions needed for Lambda layer operations.