# IAM Policy Update for Lambda Layer Publishing

## 🚨 Issue

The GitHub Actions role `arn:aws:sts::143895994429:assumed-role/cr2a-github-actions/GitHubActions` is missing permissions to publish Lambda layers.

**Error**: `AccessDeniedException: User is not authorized to perform: lambda:PublishLayerVersion`

## 🔧 Required IAM Policy Updates

### Current Missing Permissions
The GitHub Actions role needs additional Lambda layer permissions to support the new `publish-layers.yml` workflow.

### Required Lambda Layer Permissions

Add these permissions to the `cr2a-github-actions` IAM role policy:

```json
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
```

### Complete IAM Policy Template

Here's what the complete policy should look like (merge with existing permissions):

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
      "Sid": "S3DeploymentBucket",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::cr2a-deployment/*"
      ]
    },
    {
      "Sid": "S3BucketAccess",
      "Effect": "Allow", 
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::cr2a-deployment"
      ]
    }
  ]
}
```

## 🛠️ How to Apply the Policy Update

### Option 1: AWS Console
1. Go to AWS IAM Console
2. Navigate to Roles → `cr2a-github-actions`
3. Click on the attached policy
4. Edit the policy to add the Lambda layer permissions
5. Save the changes

### Option 2: AWS CLI
```bash
# Get the current policy
aws iam get-role-policy --role-name cr2a-github-actions --policy-name <policy-name>

# Update the policy with the new permissions
aws iam put-role-policy --role-name cr2a-github-actions --policy-name <policy-name> --policy-document file://updated-policy.json
```

### Option 3: Terraform/CloudFormation
If you're using Infrastructure as Code, update your IAM role definition to include the new Lambda layer permissions.

## 📋 Verification Steps

After updating the IAM policy:

1. **Test the workflow**:
   ```bash
   gh workflow run publish-layers.yml -f force_rebuild_all=true
   ```

2. **Check the logs** for successful layer publishing

3. **Verify layer creation**:
   ```bash
   aws lambda list-layer-versions --layer-name cr2a-shared-code
   aws lambda list-layer-versions --layer-name cr2a-shared-deps
   ```

## 🔍 Layer Names Used

The workflows create these layers (ensure IAM policy covers all):
- `cr2a-shared-code` - Shared code layer (src/, schemas/, templates/)
- `cr2a-shared-deps` - Dependency layer (pip packages)

## ⚠️ Security Considerations

### Principle of Least Privilege
The policy is scoped to:
- **Specific account**: `143895994429`
- **Specific region**: `us-east-1` 
- **Specific layer prefix**: `cr2a-*`

### Resource Restrictions
- Only allows operations on layers starting with `cr2a-`
- Prevents accidental modification of other layers
- Maintains security boundaries

## 🚀 Next Steps

1. **Apply the IAM policy update** using one of the methods above
2. **Wait 1-2 minutes** for IAM changes to propagate
3. **Re-run the failed workflow** or trigger a new deployment
4. **Monitor the logs** to confirm successful layer publishing

## 📞 Troubleshooting

If you continue to see permission errors:

1. **Check policy attachment**: Ensure the policy is attached to the correct role
2. **Verify resource ARNs**: Confirm account ID and region match
3. **Check trust policy**: Ensure the role can be assumed by GitHub Actions
4. **Wait for propagation**: IAM changes can take a few minutes to take effect

The error should resolve once the Lambda layer permissions are added to the GitHub Actions IAM role.