# CR2A Frontend + Orchestrator

This repo now includes a lightweight static frontend (in `webapp/`) to drive the CR2A workflow:

- Collect contract metadata (ID, URI, FDOT toggle/year, policy version, notes).
- Drag-and-drop contract file UI (client-side only; no upload wired yet).
- Mocked execution timeline and output preview while the backend endpoint is not connected.

## Deploying to Amplify Hosting + Backend

Amplify now drives both hosting and a REST API backend:

- `amplify/backend.ts` defines a REST API (API Gateway) that sends all routes to the Lambda handler at `amplify/functions/cr2a-api/app.py`. The handler exposes `GET /health` and a placeholder `POST /analysis` response so the API surface is wired before orchestrator logic lands.
- Backend env vars (configure in Amplify console): `UPLOAD_BUCKET`, `OUTPUT_BUCKET`, `AWS_REGION`, `MAX_FILE_MB`, `UPLOAD_EXPIRES_SECONDS`, `MAX_ANALYSIS_SECONDS`.
- `amplify.yml` now has two jobs: the `webapp` frontend and a backend build that vendors the Lambda (`pip install -r requirements.txt -t .` then zips to `amplify/artifacts/cr2a-api.zip`).
- Amplify publishes `amplify_outputs.json` after backend deployment. The frontend prebuild writes `webapp/env.js` with `window.CR2A_API_BASE` set to the API Gateway URL so the static app calls the deployed API automatically.

### Deployment steps

1. Connect this repo to Amplify Hosting (monorepo mode) and enable both the `webapp` and `amplify` jobs defined in `amplify.yml`.
2. In the backend environment settings, set the required env vars (`UPLOAD_BUCKET`, `OUTPUT_BUCKET`, `AWS_REGION`, limits). Deploy the backend; Amplify will produce `amplify_outputs.json` that includes `custom.apiGatewayUrl`.
3. On subsequent frontend builds, `webapp/env.js` is rewritten with that API URL, so `webapp/app.js` picks it up at runtime via `window.CR2A_API_BASE`.
4. Once connected, Amplify serves `webapp/index.html` at your domain while the REST API runs behind API Gateway + Lambda.

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

Front-end config: set `API_BASE_URL` in `webapp/app.js` to your deployed API base URL so the browser can call `/upload-url` and `/analysis`.
