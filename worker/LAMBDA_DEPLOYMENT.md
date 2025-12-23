# Lambda Deployment Guide for CR2A Step Functions Workflow

This guide explains how to deploy the Lambda functions used in the CR2A contract analysis Step Functions workflow.

## Overview

The workflow uses 4 Lambda functions:

1. **cr2a-get-metadata** - Extract metadata from contract (page count, file size, etc)
2. **cr2a-calculate-chunks** - Break contract into chunks for parallel processing
3. **cr2a-analyzer-worker** - Analyze individual chunks for contract clauses (runs in parallel)
4. **cr2a-aggregate-results** - Combine all chunk analyses into final report

## Prerequisites

- AWS Lambda functions already created in AWS Console
- IAM role with permissions for S3, DynamoDB, and CloudWatch Logs
- Python 3.11+ runtime
- boto3, PyPDF2, python-docx dependencies available

## Deployment Steps

### Step 1: Install Dependencies Locally

```bash
cd worker

# Create a temporary directory for the Lambda package
mkdir lambda-package
cd lambda-package

# Install dependencies to this directory
pip install -r ../requirements.txt -t .
```

### Step 2: Copy Lambda Code

For **cr2a-get-metadata**:

```bash
# Copy the function file
cp ../lambda_get_metadata.py .

# Create deployment package
zip -r function.zip .

# Upload to Lambda
aws lambda update-function-code \
  --function-name cr2a-get-metadata \
  --zip-file fileb://function.zip \
  --region us-east-1

cd ..
rm -rf lambda-package
```

Repeat for each function:

```bash
# cr2a-calculate-chunks
mkdir lambda-package
cd lambda-package
pip install -r ../requirements.txt -t .
cp ../lmabda_calculate_chunks.py .
zip -r function.zip .
aws lambda update-function-code --function-name cr2a-calculate-chunks --zip-file fileb://function.zip --region us-east-1
cd ..
rm -rf lambda-package

# cr2a-analyzer-worker
mkdir lambda-package
cd lambda-package
pip install -r ../requirements.txt -t .
cp ../lambda_analyze_chunk.py .
zip -r function.zip .
aws lambda update-function-code --function-name cr2a-analyzer-worker --zip-file fileb://function.zip --region us-east-1
cd ..
rm -rf lambda-package

# cr2a-aggregate-results
mkdir lambda-package
cd lambda-package
pip install -r ../requirements.txt -t .
cp ../lambda_aggregate_results.py .
zip -r function.zip .
aws lambda update-function-code --function-name cr2a-aggregate-results --zip-file fileb://function.zip --region us-east-1
cd ..
rm -rf lambda-package
```

### Step 3: Verify IAM Permissions

Ensure the Lambda execution role has these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::cr2a-upload/*",
        "arn:aws:s3:::cr2a-output/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:PutItem"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:*:table/cr2a-jobs"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:*:*"
    }
  ]
}
```

### Step 4: Configure Lambda Function Settings

For each function, set:

- **Runtime**: Python 3.11
- **Timeout**: 15 minutes (900 seconds) for analyzer, 5 minutes for others
- **Memory**: 3008 MB (maximum available)
- **Handler**: 
  - cr2a-get-metadata: `lambda_get_metadata.lambda_handler`
  - cr2a-calculate-chunks: `lmabda_calculate_chunks.lambda_handler`
  - cr2a-analyzer-worker: `lambda_analyze_chunk.lambda_handler`
  - cr2a-aggregate-results: `lambda_aggregate_results.lambda_handler`

### Step 5: Test Individual Functions

Test each function with sample Step Functions input:

```bash
# Test get-metadata
aws lambda invoke \
  --function-name cr2a-get-metadata \
  --payload '{
    "job_id": "test-job",
    "contract_id": "test-contract",
    "s3_bucket": "cr2a-upload",
    "s3_key": "test.pdf",
    "llm_enabled": true
  }' \
  response.json

cat response.json
```

## Troubleshooting

### ImportError: No module named 'PyPDF2'

**Cause**: Dependencies not included in Lambda package

**Fix**:
1. Ensure `pip install -r ../requirements.txt -t .` includes all packages
2. Verify zip contains `lib/python3.11/site-packages/` directory
3. Redeploy with dependencies

### Lambda Timeout

**Cause**: Function takes too long to process

**Fix**:
1. Increase timeout to 900 seconds (15 minutes) for analyzer function
2. Reduce chunk size if needed
3. Check CloudWatch logs for slow operations

### S3 Access Denied

**Cause**: Lambda role missing S3 permissions

**Fix**:
1. Verify IAM role has `s3:GetObject` and `s3:PutObject` permissions
2. Check S3 bucket names in code match actual buckets
3. Ensure S3 bucket policies allow Lambda role access

### DynamoDB Access Issues

**Cause**: Lambda role missing DynamoDB permissions

**Fix**:
1. Verify IAM role has `dynamodb:GetItem`, `UpdateItem`, `PutItem` permissions
2. Ensure table name in code matches actual table name (`cr2a-jobs`)
3. Verify table exists in us-east-1 region

## Deployment Automation

For automated deployments, use the provided bash script:

```bash
./deploy_lambdas.sh
```

This script:
1. Installs all dependencies
2. Creates deployment packages
3. Updates all Lambda functions
4. Validates deployments

## Testing the Full Workflow

Once all Lambda functions are deployed:

1. Upload a contract to S3
2. Call the `/analyze` API endpoint with the S3 key
3. Monitor job progress with `/status/{job_id}`
4. Check CloudWatch logs for each Lambda function
5. Verify output in S3 `cr2a-output` bucket

## Key Changes from Previous Version

1. **Fixed Step Functions Integration**: Lambda functions now receive proper Step Functions input and return correct output format
2. **Improved Error Handling**: Better error logging and exception handling throughout
3. **Proper Input/Output Flow**: Each function passes correct data to next step
4. **CloudWatch Logging**: Detailed logging for debugging
5. **DynamoDB Integration**: Job status tracking and progress updates

## Next Steps

After deployment:
1. Test with sample contracts
2. Monitor CloudWatch logs
3. Verify S3 output structure
4. Check DynamoDB job records
5. Adjust chunk sizes and timeout values based on file sizes
