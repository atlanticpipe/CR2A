# GitHub Actions OIDC Setup Guide

## 🔐 OIDC Authentication Warning

If you see this warning in your GitHub Actions:
```
It looks like you might be trying to authenticate with OIDC. Did you mean to set the `id-token` permission?
```

This means your workflow is using AWS credentials but missing the proper OIDC permissions.

## ✅ Proper OIDC Setup

### 1. Workflow Permissions
Ensure your workflows have the correct permissions:

```yaml
permissions:
  id-token: write    # Required for OIDC
  contents: read     # Required for checkout
```

### 2. AWS Credentials Configuration
Use the `aws-actions/configure-aws-credentials@v4` action with OIDC:

```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_LAMBDA_DEPLOY_ROLE_ARN }}
    aws-region: ${{ env.AWS_REGION }}
    # No need for aws-access-key-id or aws-secret-access-key with OIDC
```

### 3. Complete Job Example
```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_LAMBDA_DEPLOY_ROLE_ARN }}
          aws-region: us-east-1
      
      - name: Use build-layer action
        uses: ./.github/actions/build-layer
        with:
          layer-name: 'my-layer'
          layer-type: 'dependencies'
          requirements-files: 'requirements.txt'
```

## 🏗️ Using the Build-Layer Composite Action

### Prerequisites
1. **AWS credentials must be configured** before calling the action
2. **Proper permissions** must be set at the job level
3. **Required files** must exist in the repository

### Example Usage

#### Building a Dependencies Layer
```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_LAMBDA_DEPLOY_ROLE_ARN }}
    aws-region: us-east-1

- name: Build dependencies layer
  uses: ./.github/actions/build-layer
  with:
    layer-name: 'cr2a-shared-deps'
    layer-type: 'dependencies'
    requirements-files: 'requirements-core.txt,requirements-optional.txt'
    python-version: '3.11'
    aws-region: 'us-east-1'
```

#### Building a Shared Code Layer
```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_LAMBDA_DEPLOY_ROLE_ARN }}
    aws-region: us-east-1

- name: Build shared code layer
  uses: ./.github/actions/build-layer
  with:
    layer-name: 'cr2a-shared-code'
    layer-type: 'shared-code'
    source-paths: 'src,schemas,templates'
    aws-region: 'us-east-1'
```

## 🔧 AWS IAM Role Setup

### Required IAM Permissions
Your AWS IAM role needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:PublishLayerVersion",
        "lambda:GetLayerVersion",
        "lambda:ListLayerVersions",
        "lambda:DeleteLayerVersion"
      ],
      "Resource": [
        "arn:aws:lambda:*:*:layer:cr2a-*"
      ]
    }
  ]
}
```

### Trust Policy for OIDC
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/YOUR_REPO:*"
        }
      }
    }
  ]
}
```

## 🚨 Common Issues and Solutions

### Issue 1: "Credentials could not be loaded"
**Cause**: AWS credentials not configured before calling the action
**Solution**: Always configure AWS credentials first:

```yaml
# ❌ Wrong order
- name: Build layer
  uses: ./.github/actions/build-layer
  with: ...

- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with: ...

# ✅ Correct order
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with: ...

- name: Build layer
  uses: ./.github/actions/build-layer
  with: ...
```

### Issue 2: "id-token permission" warning
**Cause**: Missing OIDC permissions
**Solution**: Add permissions to job:

```yaml
jobs:
  my-job:
    runs-on: ubuntu-latest
    permissions:
      id-token: write    # Add this
      contents: read
    steps: ...
```

### Issue 3: "Access denied" when publishing layer
**Cause**: IAM role lacks Lambda permissions
**Solution**: Update IAM role with required Lambda permissions (see above)

## 📋 Checklist for OIDC Setup

- [ ] Job has `id-token: write` permission
- [ ] Job has `contents: read` permission  
- [ ] AWS credentials configured before composite action
- [ ] IAM role has Lambda layer permissions
- [ ] IAM role has proper trust policy for OIDC
- [ ] Repository secrets contain correct role ARN
- [ ] AWS region is specified correctly

## 🔗 Related Documentation

- [GitHub OIDC Documentation](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [AWS Configure Credentials Action](https://github.com/aws-actions/configure-aws-credentials)
- [AWS Lambda Layers Documentation](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html)