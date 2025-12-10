# Error source notes (500/403) and Amplify deploy blockers

## Backend 500s during upload presign
- `/upload-url` depends on boto3 and AWS credentials to presign to the hard-coded bucket `cr2a-uploads`. If boto3 is missing or credentials are not available, `_s3_client()` raises a 500 before presigning. Any presign failure bubbles as a 500 (`Presign failed: ...`). Relevant code lives in `src/api/main.py` near the boto3 import + `_s3_client()` helper and the `/upload-url` handler.

## 403s when uploading to S3
- The presign target bucket is fixed to `cr2a-uploads` and the client always attempts a PUT with that presigned URL. If the bucket does not exist or the deploy environment lacks IAM permission to that bucket, S3 returns `AccessDenied` (HTTP 403) during the actual upload even though the presign call succeeded. The presign path is in `src/api/main.py` (`/upload-url` handler) and the browser upload flow uses it via `UPLOAD_ENDPOINT` in `webapp/app.js` (see top constants and the `uploadFile` helper).

## Amplify deploy considerations
- `amplify.yml` publishes the raw `webapp/` folder with no build steps. Amplify jobs must treat `webapp` as the artifact root; if the app is configured to build from a different directory (e.g., the repo root) the job will fail because no build output is produced outside `webapp`. See `amplify.yml` and the static asset entrypoint in `webapp/app.js` (top-level constants).
