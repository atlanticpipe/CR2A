# CR2A Frontend + Orchestrator

This repo now includes a lightweight static frontend (in `webapp/`) to drive the CR2A workflow:

- Collect contract metadata (ID, URI, FDOT toggle/year, policy version, notes).
- Drag-and-drop contract file UI (client-side only; no upload wired yet).
- Mocked execution timeline and output preview while the backend endpoint is not connected.

## Hosting on GitHub Pages + AWS Lambda/S3 backend

This repo is now wired to serve the static UI from GitHub Pages and call a Lambda-backed REST API for uploads/analysis:

- Static hosting: the GitHub Actions workflow in `.github/workflows/deploy-pages.yml` publishes `webapp/` directly to GitHub Pages on pushes to `main` (or manual runs).
- API base URL: set `window._env.API_BASE_URL` in `webapp/env.js` (or inject `window.CR2A_API_BASE` in a separate script) to your API Gateway/Lambda base path (e.g., `https://abc123.execute-api.us-east-1.amazonaws.com/prod`). The app refuses uploads when the API base is blank.
- Uploads: `/upload-url` must return an S3 presign to an uploads bucket you control. `/analysis` should process the uploaded file and write outputs to your downloads bucket.

### Deployment steps

1. **Frontend:** push to `main` with `webapp/env.js` updated to your API base. GitHub Actions will publish `webapp/` to GitHub Pages automatically.
2. **Backend:** package and deploy `amplify/functions/cr2a-api` (or `src/api/main.py` via your preferred adapter) to AWS Lambda behind API Gateway. Configure env vars: `UPLOAD_BUCKET`, `OUTPUT_BUCKET`, `AWS_REGION`, `MAX_FILE_MB`, `UPLOAD_EXPIRES_SECONDS`, `MAX_ANALYSIS_SECONDS`.
3. **S3 buckets:** create two buckets (uploads + outputs) matching the env vars. Ensure the Lambda IAM role can `s3:PutObject`, `s3:GetObject`, and `s3:PutObjectAcl` where needed for presigns and exports.
4. **Wire presigns:** confirm `/upload-url` uses your upload bucket and that presigned URLs accept PUT or POST uploads from browsers.
5. **Test:** load the GitHub Pages site, confirm the footer shows the GitHub Pages + Lambda banner, and run a demo upload/analysis against your API base URL.

## Backend stub (FastAPI)

- Python 3.11+ is required for the orchestrator and API utilities.

- Location: `src/api/main.py`
- Endpoints:
  - `GET /health` – basic health check
  - `GET /upload-url` – returns an S3 presigned PUT URL against the `cr2a-uploads` bucket (requires AWS creds). Enforces 500 MB limit by default (`MAX_FILE_MB` env overrides).
  - `POST /analysis` – stub response echoing the submission with a generated `run_id`.
- Run locally: `uvicorn src.api.main:app --host 0.0.0.0 --port 8000`
- Required env:
  - `AWS_REGION` (default `us-east-1`)
  - Optional: `CORS_ALLOW_ORIGINS` (comma-separated, default `*`), `MAX_FILE_MB`, `UPLOAD_PREFIX`, `UPLOAD_EXPIRES_SECONDS`

Front-end config: set `API_BASE_URL` in `webapp/env.js` (or define `window.CR2A_API_BASE` before loading `app.js`) to your deployed API base URL so the browser can call `/upload-url` and `/analysis`.
