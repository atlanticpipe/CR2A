# Debugging `/analysis` 500 errors caused by file-type misclassification

The backend is rejecting uploaded contracts with `ProcessingError` messages such as `Unsupported input type: .bin`. Schema validation already passed, so the failure occurs during the backend's file-type inspection (likely MIME or byte-level detection) and not due to field names like `tdot_contract` or `fdot_contract`.

## Goals
- Confirm whether the file itself is unsupported or being misclassified.
- Check if the ingestion path (local `file://` vs. S3 `https://`) alters detection outcomes.
- Keep tests client-side only; resolving the root cause ultimately requires backend code/config changes.

## Black-box test matrix
1. **Known-good plaintext**: Upload a tiny `.txt` file (e.g., "hello world") to `/analysis`. Expect success; failure indicates ingestion path or detector issue.
2. **Known-good docx**: Upload a minimal `.docx` (freshly saved from Word) to verify the detector accepts supported Office files.
3. **PDF vs. binary misclass**:
   - Use the same sample PDF via two URIs:
     - `file:///tmp/sample.pdf` (or another local path readable by the backend).
     - `https://<bucket>.s3.<region>.amazonaws.com/sample.pdf`.
   - Compare results. If local succeeds but S3 fails (or vice versa), the ingestion path affects type detection.
4. **Content sanity**: Re-export the PDF from a PDF printer to ensure it is a valid PDF container, then retry. If still reported as `.bin`, the detector is misclassifying a valid file.
5. **Small binary control**: Intentionally send a non-supported binary (e.g., a small `.bin`) to confirm the backend reliably produces the same `ProcessingError`; this checks consistency of error handling.

## What to observe
- Whether any test returns a non-`.bin` type; this indicates the detector can succeed and the failing file is anomalous.
- Whether only S3-hosted files misclassify; this suggests the download/streaming path may alter headers or content before detection.
- Consistency of errors across retries; intermittent results could imply race conditions or partial downloads.

## Additional notes
- Swagger alone cannot resolve this; you need actual file uploads through the API or frontend to reproduce.
- Long-term fixes require backend changes: adjust MIME/sniffing logic to trust validated PDF signatures, or whitelist `.pdf` when byte patterns match expected headers.
