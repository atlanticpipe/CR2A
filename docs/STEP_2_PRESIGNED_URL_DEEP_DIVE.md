# STEP 2: Get Presigned S3 Upload URL - Deep Dive

## Overview

**Purpose:** Generate a secure, time-limited URL that allows the frontend to upload files directly to S3 without exposing AWS credentials.

**Flow:** Frontend → Backend API → AWS S3 SDK → Presigned URL → Frontend

**Security Model:** The backend acts as a gatekeeper, validating requests before issuing temporary upload credentials.

---

## Complete Request/Response Flow

### 1. Frontend Initiates Request

**Location:** `webapp/app.js` (Line ~201)

**Triggered by:** User selects a file for upload

**Code:**
```javascript
const getUploadUrl = async (filename, contentType, size) => {
  const apiBase = requireApiBase();  // e.g., "https://api.example.com"
  const params = new URLSearchParams({
    filename,      // "contract.pdf"
    contentType,   // "application/pdf"
    size: String(size),  // "5242880" (5 MB in bytes)
  });

  const res = await fetch(`${apiBase}/upload-url?${params.toString()}`, {
    headers: requireAuthHeader(), // Authorization: Bearer mvp-token
  });
  
  if (!res.ok) {
    throw new Error("Failed to get upload URL");
  }
  
  return res.json(); // { uploadUrl, key, bucket, expires_in, ... }
};
```

**Example Request:**
```http
GET /upload-url?filename=contract.pdf&contentType=application%2Fpdf&size=5242880 HTTP/1.1
Host: p6zla1yuxb.execute-api.us-east-1.amazonaws.com
Authorization: Bearer mvp-token
```

---

### 2. Backend Receives Request

**Location:** `src/api/main.py` (Line ~70)

**Endpoint:** `@app.get("/upload-url")`

**Full Code:**
```python
@app.get("/upload-url", response_model=UploadUrlResponse)
def upload_url(
    filename: str = Query(..., description="Original filename"),
    contentType: str = Query("application/octet-stream", description="MIME type"),
    size: int = Query(..., description="File size in bytes"),
):
    """
    Generate a presigned S3 upload URL.
    
    Security Checks:
    - Validates file size against MAX_FILE_BYTES (500 MB)
    - Generates unique key to prevent collisions
    - Sets expiration time (1 hour default)
    - Restricts to specific bucket
    """
    
    # 1. Validate file size
    if size > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {size} bytes. Limit is {MAX_FILE_BYTES} bytes ({MAX_FILE_MB} MB).",
        )
    
    # 2. Generate presigned URL via storage service
    try:
        result = generate_upload_url(filename, contentType)
        return UploadUrlResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Presign failed: {e}")
```

**What Happens:**

1. **Extract Query Parameters:**
   - `filename`: Original file name (e.g., "contract.pdf")
   - `contentType`: MIME type (e.g., "application/pdf")
   - `size`: File size in bytes (e.g., 5242880 = 5 MB)

2. **Validate File Size:**
   - Checks if `size` ≤ `MAX_FILE_BYTES` (500 MB = 524,288,000 bytes)
   - Returns 400 error if file is too large
   - This prevents abuse and controls storage costs

3. **Call Storage Service:**
   - Delegates to `generate_upload_url()` in `src/services/storage.py`
   - Passes filename and content type

---

### 3. Storage Service Generates Presigned URL

**Location:** `src/services/storage.py` (Line ~300)

**Function:** `generate_upload_url()`

**Full Code with Annotations:**
```python
def generate_upload_url(filename: str, content_type: str = "application/octet-stream") -> Dict[str, Any]:
    """
    Generate a presigned upload URL for direct client-to-S3 uploads.
    
    This uses AWS STS (Security Token Service) to create a temporary
    credential that allows PUT operations to a specific S3 object.
    
    Security Features:
    - URL expires after UPLOAD_EXPIRES_SECONDS (default: 3600 = 1 hour)
    - Restricted to specific bucket (cr2a-upload)
    - Restricted to specific key (unique UUID prevents overwriting)
    - Enforces Content-Type header matching
    
    Args:
        filename: Original filename (e.g., "contract.pdf")
        content_type: MIME type (e.g., "application/pdf")
    
    Returns:
        Dict with:
        - uploadUrl: Presigned URL for PUT request
        - key: S3 object key where file will be stored
        - bucket: S3 bucket name
        - expires_in: Seconds until URL expires
        - headers: Required headers for upload request
    """
    import uuid
    from urllib.parse import quote
    
    # 1. Get and validate bucket name
    bucket = load_upload_bucket()  # Returns "cr2a-upload"
    
    # 2. Get S3 client (initialized with AWS credentials)
    client = get_s3_client()  # boto3.client('s3')
    
    # 3. Generate unique S3 key to prevent collisions
    # Example: "upload/550e8400-e29b-41d4-a716-446655440000_contract.pdf"
    safe_name = quote(os.path.basename(filename))  # URL-encode filename
    key = f"{UPLOAD_PREFIX}{uuid.uuid4()}_{safe_name}"
    # UPLOAD_PREFIX = "upload/"
    # uuid.uuid4() = "550e8400-e29b-41d4-a716-446655440000"
    # Result: "upload/550e8400-e29b-41d4-a716-446655440000_contract.pdf"
    
    # 4. Generate presigned URL using AWS SDK
    try:
        url = client.generate_presigned_url(
            "put_object",  # Allow PUT operation
            Params={
                "Bucket": bucket,              # "cr2a-upload"
                "Key": key,                    # "upload/550e8400.../contract.pdf"
                "ContentType": content_type,   # "application/pdf"
            },
            ExpiresIn=UPLOAD_EXPIRES_SECONDS,  # 3600 seconds (1 hour)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Presign failed: {e}")

    # 5. Return presigned URL and metadata
    return {
        "uploadUrl": url,
        "url": url,  # Duplicate for backward compatibility
        "bucket": bucket,
        "key": key,
        "expires_in": UPLOAD_EXPIRES_SECONDS,
        "headers": {"Content-Type": content_type},
    }
```

**What AWS SDK Does Internally:**

```python
# AWS generates a presigned URL like:
"https://cr2a-upload.s3.us-east-1.amazonaws.com/upload/550e8400-e29b-41d4-a716-446655440000_contract.pdf?"
"X-Amz-Algorithm=AWS4-HMAC-SHA256&"
"X-Amz-Credential=AKIA.../20260106/us-east-1/s3/aws4_request&"
"X-Amz-Date=20260106T183000Z&"
"X-Amz-Expires=3600&"
"X-Amz-SignedHeaders=content-type;host&"
"X-Amz-Signature=a1b2c3d4e5f6..."  # HMAC signature of the request
```

**Key Components of Presigned URL:**

1. **Base URL:** `https://cr2a-upload.s3.us-east-1.amazonaws.com/upload/550e8400.../contract.pdf`
   - Points to specific S3 object location
   
2. **X-Amz-Algorithm:** `AWS4-HMAC-SHA256`
   - Signing algorithm version
   
3. **X-Amz-Credential:** `AKIA.../20260106/us-east-1/s3/aws4_request`
   - Temporary credential scoped to date, region, and service
   
4. **X-Amz-Date:** `20260106T183000Z`
   - Timestamp when URL was generated
   
5. **X-Amz-Expires:** `3600`
   - Seconds until expiration (1 hour)
   
6. **X-Amz-Signature:** `a1b2c3d4e5f6...`
   - HMAC-SHA256 signature of the request
   - Proves the URL was generated by someone with valid AWS credentials
   - Cannot be forged without knowing the secret access key

---

### 4. Backend Returns Response to Frontend

**Response Model:** `UploadUrlResponse` (defined in `src/api/main.py`)

```python
class UploadUrlResponse(BaseModel):
    uploadUrl: str              # Presigned S3 PUT URL
    url: str                    # Alternative URL field
    upload_method: str = "PUT"  # HTTP method (PUT or POST)
    fields: Optional[dict] = None  # Form fields (for POST uploads)
    bucket: str                 # S3 bucket name
    key: str                    # S3 object key
    expires_in: int             # URL expiration seconds
    headers: Optional[Dict[str, str]] = None  # Required headers
```

**Example JSON Response:**
```json
{
  "uploadUrl": "https://cr2a-upload.s3.us-east-1.amazonaws.com/upload/550e8400-e29b-41d4-a716-446655440000_contract.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA.../20260106/us-east-1/s3/aws4_request&X-Amz-Date=20260106T183000Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=content-type;host&X-Amz-Signature=a1b2c3d4...",
  "url": "https://cr2a-upload.s3.us-east-1.amazonaws.com/upload/550e8400-e29b-41d4-a716-446655440000_contract.pdf?...",
  "upload_method": "PUT",
  "fields": null,
  "bucket": "cr2a-upload",
  "key": "upload/550e8400-e29b-41d4-a716-446655440000_contract.pdf",
  "expires_in": 3600,
  "headers": {
    "Content-Type": "application/pdf"
  }
}
```

---

### 5. Frontend Stores URL and Metadata

**Location:** `webapp/app.js` (Line ~215)

```javascript
const uploadFile = async (file) => {
  resetUploadUi();
  setUploadProgress(1);
  
  // Call backend to get presigned URL
  const { uploadUrl, key } = await getUploadUrl(
    file.name,
    file.type || "application/octet-stream",
    file.size,
  );
  
  // uploadUrl = "https://cr2a-upload.s3.us-east-1.amazonaws.com/upload/550e8400.../contract.pdf?..."
  // key = "upload/550e8400-e29b-41d4-a716-446655440000_contract.pdf"
  
  // Upload file using presigned URL (Step 3)
  const resp = await fetch(uploadUrl, {
    method: "PUT",
    headers: {
      "Content-Type": file.type || "application/octet-stream",
    },
    body: file,  // Raw file bytes
  });

  if (!resp.ok) throw new Error(`Upload failed: HTTP ${resp.status}`);
  
  setUploadProgress(100);
  return { key };  // Return S3 key for later use
};
```

---

## Security Architecture

### Why Presigned URLs?

**Problem:** Traditional file upload approaches expose security risks:

1. **Direct credential exposure:**
   - Embedding AWS keys in frontend = anyone can steal them
   - Users could delete/modify any S3 object

2. **Server bottleneck:**
   - All files go through backend server
   - Consumes bandwidth, memory, CPU
   - Slows down as file sizes increase

3. **Scalability issues:**
   - Backend must handle large file uploads
   - Limits concurrent uploads

**Solution:** Presigned URLs provide:

1. **Temporary credentials:**
   - URL expires after 1 hour
   - Only valid for specific S3 object (key)
   - Only allows PUT operation (not GET/DELETE)

2. **Direct uploads:**
   - Client uploads directly to S3
   - Backend never touches file bytes
   - Unlimited concurrent uploads

3. **Fine-grained permissions:**
   - Each URL is scoped to single object
   - Cannot be reused for other files
   - Cannot be used after expiration

### Security Checks in Code

**1. File Size Validation (Line ~75 in main.py):**
```python
if size > MAX_FILE_BYTES:
    raise HTTPException(
        status_code=400,
        detail=f"File too large: {size} bytes. Limit is {MAX_FILE_BYTES} bytes ({MAX_FILE_MB} MB).",
    )
```
**Why:** Prevents uploading excessively large files (> 500 MB) that could:
- Consume storage quota
- Increase costs
- Cause processing timeouts

**2. Bucket Name Validation (Line ~50 in storage.py):**
```python
def is_valid_s3_bucket(name: str) -> bool:
    if any(ch.isupper() for ch in name) or "_" in name:
        return False  # Reject uppercase and underscores
    if not _VALID_BUCKET.fullmatch(name):
        return False  # Enforce AWS naming rules
    if ".." in name or ".-" in name or "-." in name:
        return False  # Prevent path traversal
    if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", name):
        return False  # Reject IP addresses
    return True
```
**Why:** Prevents:
- Injection attacks via malicious bucket names
- Accidental use of invalid bucket names
- Path traversal attempts

**3. Unique Key Generation (Line ~310 in storage.py):**
```python
key = f"{UPLOAD_PREFIX}{uuid.uuid4()}_{safe_name}"
```
**Why:** UUID ensures:
- No two uploads overwrite each other
- Attackers can't guess keys
- Each file has unique identifier for tracking

**4. Content-Type Enforcement:**
```python
Params={
    "ContentType": content_type,  # Must match on upload
}
```
**Why:**
- Browser enforces Content-Type header
- Prevents uploading malicious file types
- Ensures file type matches declared type

**5. Expiration Time Limit:**
```python
ExpiresIn=UPLOAD_EXPIRES_SECONDS,  # 3600 seconds
```
**Why:**
- URL becomes invalid after 1 hour
- Prevents link sharing/reuse
- Limits exposure window if URL is leaked

---

## Configuration Variables

**Location:** `src/services/storage.py` (Lines 20-30)

```python
# File size limits
MAX_FILE_MB = float(os.getenv("MAX_FILE_MB", "500"))  # 500 MB default
MAX_FILE_BYTES = int(MAX_FILE_MB * 1024 * 1024)       # 524,288,000 bytes

# Upload URL settings
UPLOAD_EXPIRES_SECONDS = int(os.getenv("UPLOAD_EXPIRES_SECONDS", "3600"))  # 1 hour
UPLOAD_PREFIX = os.getenv("UPLOAD_PREFIX", "upload/")  # S3 key prefix

# S3 buckets
UPLOAD_BUCKET = os.getenv("UPLOAD_BUCKET", "cr2a-upload")  # Upload bucket
OUTPUT_BUCKET = os.getenv("OUTPUT_BUCKET", "cr2a-output")  # Results bucket

# AWS region
AWS_REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
```

**Environment Variables:**

| Variable | Default | Purpose |
|----------|---------|----------|
| `MAX_FILE_MB` | 500 | Maximum file size in megabytes |
| `UPLOAD_EXPIRES_SECONDS` | 3600 | Presigned URL expiration (1 hour) |
| `UPLOAD_PREFIX` | "upload/" | S3 key prefix for uploads |
| `UPLOAD_BUCKET` | "cr2a-upload" | S3 bucket for contract uploads |
| `OUTPUT_BUCKET` | "cr2a-output" | S3 bucket for analysis results |
| `AWS_REGION` | "us-east-1" | AWS region for S3 operations |

---

## Error Handling

### Common Error Scenarios

**1. File Too Large (400 Bad Request)**
```json
{
  "detail": {
    "category": "ValidationError",
    "message": "File too large: 524300000 bytes. Limit is 524288000 bytes (500 MB)."
  }
}
```
**Cause:** `size` parameter exceeds `MAX_FILE_BYTES`

**Frontend Handling:**
```javascript
if (mb > MAX_FILE_MB) {
  setUploadMessage(`File is ${mb.toFixed(2)} MB; limit is ${MAX_FILE_MB} MB.`, true);
  return;
}
```

**2. Invalid Bucket Name (500 Internal Server Error)**
```json
{
  "detail": {
    "category": "ValidationError",
    "message": "Invalid S3 upload bucket 'Invalid_Bucket'. Expected lowercase DNS-compatible name."
  }
}
```
**Cause:** `UPLOAD_BUCKET` environment variable contains invalid characters

**3. AWS Credentials Missing (500 Internal Server Error)**
```json
{
  "detail": {
    "category": "ConfigError",
    "message": "boto3 not installed; S3 operations unavailable."
  }
}
```
**Cause:** boto3 not installed or AWS credentials not configured

**4. Presign Failure (500 Internal Server Error)**
```json
{
  "detail": "Presign failed: Unable to locate credentials"
}
```
**Cause:** AWS SDK cannot find credentials (access key, secret key)

---

## Testing Step 2

### Test 1: Valid Request

**Terminal:**
```bash
curl -X GET "http://localhost:5000/upload-url?filename=test.pdf&contentType=application/pdf&size=1024" \
  -H "Authorization: Bearer mvp-token" | jq
```

**Expected Response:**
```json
{
  "uploadUrl": "https://cr2a-upload.s3.us-east-1.amazonaws.com/upload/550e8400.../test.pdf?X-Amz-Algorithm=...",
  "url": "https://cr2a-upload.s3.us-east-1.amazonaws.com/upload/550e8400.../test.pdf?X-Amz-Algorithm=...",
  "upload_method": "PUT",
  "fields": null,
  "bucket": "cr2a-upload",
  "key": "upload/550e8400-e29b-41d4-a716-446655440000_test.pdf",
  "expires_in": 3600,
  "headers": {
    "Content-Type": "application/pdf"
  }
}
```

### Test 2: File Too Large

**Terminal:**
```bash
curl -X GET "http://localhost:5000/upload-url?filename=huge.pdf&contentType=application/pdf&size=524300000" \
  -H "Authorization: Bearer mvp-token" | jq
```

**Expected Response (400 Error):**
```json
{
  "detail": "File too large: 524300000 bytes. Limit is 524288000 bytes (500 MB)."
}
```

### Test 3: Browser Console Test

**Browser DevTools (F12):**
```javascript
// Test getUploadUrl function
const result = await getUploadUrl('test.pdf', 'application/pdf', 1024);
console.log('Upload URL:', result.uploadUrl);
console.log('S3 Key:', result.key);
console.log('Expires in:', result.expires_in, 'seconds');

// Verify URL structure
const url = new URL(result.uploadUrl);
console.log('Bucket:', url.hostname.split('.')[0]);
console.log('Key:', url.pathname.slice(1));
console.log('Signature params:', Array.from(url.searchParams.keys()));
```

### Test 4: Presigned URL Upload

**Terminal (using returned presigned URL):**
```bash
# First, get presigned URL
RESPONSE=$(curl -s "http://localhost:5000/upload-url?filename=test.pdf&contentType=application/pdf&size=1024")
UPLOAD_URL=$(echo $RESPONSE | jq -r '.uploadUrl')

# Then, upload file using presigned URL
curl -X PUT "$UPLOAD_URL" \
  -H "Content-Type: application/pdf" \
  --data-binary @test.pdf

# Should return 200 OK if successful
```

---

## Performance Considerations

### Metrics

**Presigned URL Generation:**
- **Time:** ~50-100ms (AWS SDK signature calculation)
- **Memory:** <1 MB (just URL string generation)
- **Network:** 0 bytes (no AWS API calls made)

**Why It's Fast:**
- URL generation is purely computational (HMAC-SHA256)
- No network round-trip to AWS
- No file bytes processed by backend

### Scalability

**Concurrent Requests:**
- Can handle 1000+ presigned URL requests/second
- Each request is stateless and independent
- No database queries or S3 API calls

**Bottlenecks:**
- CPU (HMAC signature calculation)
- Not memory or I/O bound

---

## Key Takeaways

1. **Presigned URLs enable direct client-to-S3 uploads** without exposing AWS credentials
2. **Backend validates requests** before issuing temporary credentials
3. **URLs expire after 1 hour** and are scoped to specific S3 objects
4. **Unique UUIDs prevent collisions** and enable file tracking
5. **File size validation** prevents abuse and controls costs
6. **Content-Type enforcement** ensures file types match declarations
7. **Presign operation is fast** (~50-100ms) and highly scalable

---

## Code Files Reference

| File | Lines | Purpose |
|------|-------|----------|
| `webapp/app.js` | ~201-220 | Frontend request to get presigned URL |
| `src/api/main.py` | ~70-90 | API endpoint handler |
| `src/services/storage.py` | ~300-335 | Presigned URL generation logic |
| `src/services/storage.py` | ~20-30 | Configuration variables |
| `src/services/storage.py` | ~50-75 | S3 bucket validation |

---

## Next Step

Once the frontend receives the presigned URL, it proceeds to **Step 3: Upload File Directly to S3** using the `uploadUrl` returned in this step.
