# CR2A
Clause Risk, Compliance & Redlining Analysis
## Public API Contract (v1)

### Scope
This contract defines the two endpoints the CR2A web client calls in production.

### Endpoints
- **POST `/api/chatkit/session`** — Initializes a ChatKit session and returns a client secret.
- **POST `/api/export-pdf`** — Generates a PDF from provided text and returns it as a download.

### Methods
Only **POST** is supported for both endpoints. Non-POST requests return **405** and include `Allow: POST`.

### Client Request Headers
`Content-Type: application/json` (both endpoints)

### Request Payloads

- **/api/chatkit/session**
  - **Body (client → server):** `{ }` (client sends nothing)
  - **Server behavior:** constructs `{ "workflow": "<OPENAI_WORKFLOW_ID>" }` for the OpenAI Sessions API.

- **/api/export-pdf**
  - **Fields:**
    - `content` (string, required, non-empty)
    - `title` (string, optional)
    - `filename` (string, optional)
  - **Example:**
    ```json
    {
      "content": "Final answer text to export",
      "title": "CR2A Results",
      "filename": "CR2A"
    }
    ```

### Responses

- **/api/chatkit/session**
  - **200**
    ```json
    { "client_secret": { "value": "<string>" } }
    ```
    > Note: The server normalizes OpenAI’s response so the widget always receives `client_secret.value`.
  - **<OpenAI non-OK status>** (forwarded)
    ```json
    { "error": "OpenAI session create failed", "detail": "<raw text from OpenAI>" }
    ```
  - **500**
    ```json
    { "error": "Server error creating ChatKit session", "detail": "<message>" }
    ```

- **/api/export-pdf**
  - **200** — PDF binary
    - **Headers**
      - `Content-Type: application/pdf`
      - `Content-Disposition: attachment; filename="<sanitized>.pdf"`
      - `Cache-Control: no-store`
  - **400** — plain text
    - `"Invalid JSON body"` **or** `"Missing required field: content"`
  - **405** — plain text
    - `"Method Not Allowed"`
    - Header: `Allow: POST`
  - **500** — plain text
    - `"Failed to generate PDF"`


### Status Codes

| Endpoint               | 200 | 400                                 | 405 (Allow: POST) | OpenAI non-OK (forwarded) | 500 |
|------------------------|:---:|:-------------------------------------|:------------------:|:--------------------------:|:---:|
| `/api/chatkit/session` |  ✓  | —                                   |         ✓          |             ✓              |  ✓  |
| `/api/export-pdf`      |  ✓  | Invalid JSON / missing `content`     |         ✓          |             —              |  ✓  |

### Timeouts

- **Client:** `/api/export-pdf` uses a hard **20s** timeout (AbortController) in the button flow.  
- **Server SLOs (non-blocking targets):** Session < **3s** typical; PDF < **5s** typical.

### Environment Variables

**Frontend (build-time)**
- `VITE_CHATKIT_WORKFLOW_ID` — required in production.
- `VITE_CHATKIT_CREATE_SESSION_ENDPOINT` — optional override; default: `/api/chatkit/session`.

**Server (runtime)**
- `OPENAI_API_KEY` — required.
- `OPENAI_WORKFLOW_ID` — required.
- `OPENAI_SESSIONS_URL` — optional; default: `https://api.openai.com/v1/chat/sessions`.

### Change Control

Any change to **URLs**, **methods**, **payloads**, **response shapes**, or **status codes** requires:
1. Bumping this section to **Public API Contract (vX+1)**.
2. Updating affected clients.
3. Reviewer sign-off from app and platform owners.

#### cURL Examples

> Replace `http://localhost:3000` with your dev/staging base URL.

```bash
# Session (expects 200 with { client_secret: { value } })
curl -sS -X POST http://localhost:3000/api/chatkit/session \
  -H 'Content-Type: application/json'

# Export PDF (expects 200 application/pdf; saves CR2A.pdf)
curl -sS -X POST http://localhost:3000/api/export-pdf \
  -H 'Content-Type: application/json' \
  -d '{ "content": "Hello world", "title": "CR2A Results", "filename": "CR2A" }' \
  -o CR2A.pdf