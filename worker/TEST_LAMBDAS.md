# Testing Guide for CR2A Lambda Functions

## Quick Verification Checklist

### ✅ Step 1: Verify Deployment (AWS Console)

1. Go to AWS Lambda Console: https://console.aws.amazon.com/lambda/
2. Check each function exists and shows recent updates:
   - `cr2a-get-metadata`
   - `cr2a-calculate-chunks`
   - `cr2a-analyzer-worker`
   - `cr2a-aggregate-results`
3. Click each function and check:
   - **Last modified**: Should be recent (today's date)
   - **Code size**: Should be > 5 MB (includes PyPDF2 dependencies)
   - **Handler**: Should match the correct handler name
   - **Runtime**: Should be Python 3.11

### ✅ Step 2: Test Individual Lambda Functions

#### Test cr2a-get-metadata

**Upload a test PDF to S3:**
```bash
# Upload any PDF to test bucket
aws s3 cp test-contract.pdf s3://cr2a-upload/test-contract.pdf
```

**Test the Lambda:**
```bash
aws lambda invoke \
  --function-name cr2a-get-metadata \
  --payload '{
    "job_id": "test-001",
    "contract_id": "contract-001",
    "s3_bucket": "cr2a-upload",
    "s3_key": "test-contract.pdf",
    "llm_enabled": false
  }' \
  --cli-binary-format raw-in-base64-out \
  response.json

cat response.json
```

**Expected Output:**
```json
{
  "job_id": "test-001",
  "contract_id": "contract-001",
  "s3_bucket": "cr2a-upload",
  "s3_key": "test-contract.pdf",
  "llm_enabled": false,
  "metadata": {
    "file_type": "pdf",
    "pages": 45,
    "size": 1234567,
    "file_size_mb": 1.18,
    "estimated_chunks": 1,
    "chunk_size": 10000
  }
}
```

#### Test cr2a-calculate-chunks

```bash
aws lambda invoke \
  --function-name cr2a-calculate-chunks \
  --payload '{
    "job_id": "test-001",
    "contract_id": "contract-001",
    "s3_bucket": "cr2a-upload",
    "s3_key": "test-contract.pdf",
    "llm_enabled": false,
    "metadata": {
      "file_type": "pdf",
      "pages": 10,
      "size": 100000,
      "file_size_mb": 0.1,
      "estimated_chunks": 1,
      "chunk_size": 10000
    }
  }' \
  --cli-binary-format raw-in-base64-out \
  response.json

cat response.json
```

**Expected Output:**
```json
{
  "job_id": "test-001",
  "contract_id": "contract-001",
  "s3_bucket": "cr2a-upload",
  "s3_key": "test-contract.pdf",
  "llm_enabled": false,
  "metadata": {...},
  "chunk_plan": {
    "total_chunks": 1,
    "chunks": [
      {
        "chunk_index": 0,
        "start_page": 0,
        "end_page": 10,
        "page_count": 10,
        "job_id": "test-001",
        "s3_bucket": "cr2a-upload",
        "s3_key": "test-contract.pdf",
        "file_type": "pdf"
      }
    ]
  }
}
```

### ✅ Step 3: Test Full Workflow via API

This is the **real test** - testing the entire Step Functions workflow:

#### 3.1 Start Analysis

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "contract_id": "test-contract-001",
    "s3_bucket": "cr2a-upload",
    "s3_key": "test-contract.pdf",
    "llm_enabled": false
  }'
```

**Expected Response:**
```json
{
  "job_id": "abc123-def456-...",
  "status": "queued",
  "message": "Analysis started",
  "execution_arn": "arn:aws:states:us-east-1:..."
}
```

**Save the `job_id` from the response!**

#### 3.2 Monitor Progress

```bash
# Replace {job_id} with actual job_id from step 3.1
curl http://localhost:8000/status/{job_id}
```

**Watch for these stages:**

```json
// Stage 1: Just started
{
  "job_id": "...",
  "status": "processing",
  "progress": 0,
  "current_step": "Extracting Metadata",
  "started_at": "2025-12-23T12:00:00.000Z"
}

// Stage 2: Calculating chunks
{
  "status": "processing",
  "progress": 25,
  "current_step": "Calculating Chunks"
}

// Stage 3: Analyzing content
{
  "status": "processing",
  "progress": 50,
  "current_step": "Analyzing Content"
}

// Stage 4: Aggregating results
{
  "status": "processing",
  "progress": 75,
  "current_step": "Aggregating Results"
}

// Stage 5: Complete!
{
  "status": "completed",
  "progress": 100,
  "current_step": "Complete",
  "completed_at": "2025-12-23T12:05:30.000Z",
  "result_key": "results/abc123.../final_analysis.json"
}
```

#### 3.3 Get Results

```bash
# Replace {job_id} with actual job_id
curl http://localhost:8000/results/{job_id}
```

**Expected Response:**
```json
{
  "job_id": "...",
  "completed_at": "2025-12-23T12:05:30.000Z",
  "total_clauses_found": 45,
  "summary": {
    "clause_counts": {
      "Payment": 5,
      "Termination": 3,
      "Indemnification": 7,
      "Scope of Work": 12,
      ...
    },
    "top_clause_types": [
      {"type": "Scope of Work", "count": 12},
      {"type": "Indemnification", "count": 7},
      {"type": "Payment", "count": 5}
    ]
  },
  "recommendations": [...],
  "all_clauses": [...]
}
```

### ✅ Step 4: Check CloudWatch Logs

Verify Lambda functions are running correctly:

```bash
# Get latest logs for each function
aws logs tail /aws/lambda/cr2a-get-metadata --follow
aws logs tail /aws/lambda/cr2a-calculate-chunks --follow
aws logs tail /aws/lambda/cr2a-analyzer-worker --follow
aws logs tail /aws/lambda/cr2a-aggregate-results --follow
```

**What to look for:**
- ✅ `INFO` level messages showing progress
- ✅ File sizes, page counts, chunk counts
- ✅ "Processing job..." messages
- ✅ No ERROR or exception tracebacks
- ✅ "Deployment successful" messages

### ✅ Step 5: Check S3 Output

Verify results are being stored:

```bash
# List results for a job
aws s3 ls s3://cr2a-output/results/{job_id}/ --recursive
```

**Expected structure:**
```
results/{job_id}/
├── chunks/
│   ├── chunk-0.json
│   ├── chunk-1.json
│   └── chunk-2.json
└── final_analysis.json
```

**Download and check final analysis:**
```bash
aws s3 cp s3://cr2a-output/results/{job_id}/final_analysis.json .
cat final_analysis.json | jq .
```

### ✅ Step 6: Check DynamoDB Job Records

```bash
# Get job record
aws dynamodb get-item \
  --table-name cr2a-jobs \
  --key '{"job_id": {"S": "test-001"}}'
```

**Expected fields:**
- `status`: "completed"
- `progress`: 100
- `result_key`: "results/{job_id}/final_analysis.json"
- `completed_at`: timestamp
- No `error` field

## Common Issues and Solutions

### ❌ Status stays at 0% / "queued"

**Problem**: Step Functions execution not starting

**Check**:
1. Step Functions execution ARN in job record
2. Step Functions console for execution status
3. IAM role permissions for API Gateway → Step Functions

**Fix**: Check API Gateway integration and IAM permissions

### ❌ Execution starts but fails immediately

**Problem**: Lambda function error on first step

**Check**:
1. CloudWatch logs: `/aws/lambda/cr2a-get-metadata`
2. Look for ImportError, S3 access errors, or exceptions

**Fix**: 
- Ensure dependencies deployed correctly
- Verify S3 file exists and Lambda has read permissions
- Check Lambda execution role has S3 permissions

### ❌ Progress gets stuck at 50%

**Problem**: Map state (parallel chunk processing) failing

**Check**:
1. CloudWatch logs: `/aws/lambda/cr2a-analyzer-worker`
2. Step Functions execution visual workflow
3. Look for timeout or memory errors

**Fix**:
- Increase Lambda timeout (current: 15 minutes)
- Increase Lambda memory (current: 3008 MB)
- Check for S3 access issues

### ❌ "No clauses found" in results

**Problem**: Text extraction or clause detection not working

**Check**:
1. PDF file is valid and not scanned image
2. CloudWatch logs for extraction errors
3. Chunk analysis results in S3

**Fix**:
- Use text-based PDF (not scanned images)
- Verify PyPDF2 is extracting text correctly
- Check clause classification keywords

## Success Criteria

### ✅ Working System Shows:

1. **GitHub Actions**: All 4 Lambda deployments succeed (green checkmarks)
2. **API /analyze**: Returns job_id and execution_arn
3. **API /status**: Progress goes 0% → 25% → 50% → 75% → 100%
4. **API /results**: Returns clause analysis with counts
5. **CloudWatch**: Clean logs with no errors
6. **S3**: Results stored in `cr2a-output/results/{job_id}/`
7. **DynamoDB**: Job record shows "completed" status
8. **Step Functions**: Execution shows all green checkmarks

## Quick Test Command

Run this single command to test everything:

```bash
#!/bin/bash
# test-cr2a.sh

JOB_ID=$(curl -s -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "contract_id": "test-001",
    "s3_bucket": "cr2a-upload",
    "s3_key": "test-contract.pdf",
    "llm_enabled": false
  }' | jq -r '.job_id')

echo "Started job: $JOB_ID"
echo "Monitoring progress..."

while true; do
  STATUS=$(curl -s http://localhost:8000/status/$JOB_ID)
  PROGRESS=$(echo $STATUS | jq -r '.progress')
  STEP=$(echo $STATUS | jq -r '.current_step')
  STATE=$(echo $STATUS | jq -r '.status')
  
  echo "[$STATE] $PROGRESS% - $STEP"
  
  if [ "$STATE" = "completed" ] || [ "$STATE" = "failed" ]; then
    break
  fi
  
  sleep 5
done

echo "\nFinal results:"
curl -s http://localhost:8000/results/$JOB_ID | jq .
```

Run it:
```bash
chmod +x test-cr2a.sh
./test-cr2a.sh
```

You should see progress updates every 5 seconds and final results! 🎉
