# CR2A Frontend + Orchestrator

This repo now includes a lightweight static frontend (in `webapp/`) to drive the CR2A workflow:

- Collect contract metadata (ID, URI, FDOT toggle/year, policy version, notes).
- Drag-and-drop contract file UI (client-side only; no upload wired yet).
- Mocked execution timeline and output preview while the backend endpoint is not connected.

## Deploying to Amplify Hosting

Amplify is configured for static hosting via `amplify.yml`:

- Artifact path: `webapp`
- Build commands: none (pure HTML/CSS/JS)

Once connected, Amplify will serve `webapp/index.html` at your domain.

## Wiring the API

Set `API_BASE_URL` (and optionally `POLICY_DOC_URL`) in `webapp/app.js`. When `API_BASE_URL` is non-empty:

- File uploads up to 500 MB: the UI requests a presigned URL from `${API_BASE_URL}/upload-url?filename=...&contentType=...&size=...` and performs the upload (PUT by default, POST if `upload_method: "POST"` with `fields` is returned). The resulting URL is passed as `contract_uri` to the submit payload.
- Analysis submit: the form POSTs JSON to `${API_BASE_URL}/analysis` with the collected fields.

If `API_BASE_URL` is empty, the UI runs the built-in mock flow for demo purposes.

## Backend stub (FastAPI)

- Location: `src/api/main.py`
- Endpoints:
  - `GET /health` – basic health check
  - `GET /upload-url` – returns an S3 presigned PUT URL (requires `S3_UPLOAD_BUCKET` env and AWS creds). Enforces 500 MB limit by default (`MAX_FILE_MB` env overrides).
  - `POST /analysis` – stub response echoing the submission with a generated `run_id`.
- Run locally: `uvicorn src.api.main:app --host 0.0.0.0 --port 8000`
- Required env:
  - `S3_UPLOAD_BUCKET` (preferred, lowercase only; e.g., `cr2a-uploads`; `UPLOAD_BUCKET` remains as a fallback)
  - `AWS_REGION` (default `us-east-1`)
  - Optional: `CORS_ALLOW_ORIGINS` (comma-separated, default `*`), `MAX_FILE_MB`, `UPLOAD_PREFIX`, `UPLOAD_EXPIRES_SECONDS`

Front-end config: set `API_BASE_URL` in `webapp/app.js` to your deployed API base URL so the browser can call `/upload-url` and `/analysis`.
