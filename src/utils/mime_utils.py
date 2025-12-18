"""Utility helpers for reliable MIME and extension detection."""
from __future__ import annotations

import importlib
import mimetypes
import zipfile
from pathlib import Path
from typing import Optional

magic = importlib.import_module("magic") if importlib.util.find_spec("magic") else None

def _detect_signature(path: Path) -> Optional[str]:
    """Inspect file signatures to classify PDFs and DOCX without extensions."""
    head = path.read_bytes()[:8192]
    # PDFs always start with the %PDF- marker; short read is enough to confirm.
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    # DOCX packages are ZIPs; look for expected entries to avoid extension reliance.
    if head.startswith(b"PK"):
        try:
            with zipfile.ZipFile(path) as zf:
                names = set(zf.namelist())
                if "word/document.xml" in names or "[Content_Types].xml" in names:
                    return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        except zipfile.BadZipFile:
            return None
    return None

def infer_mime_type(file_path: str | Path) -> str:
    """Return a best-effort MIME type for the given file path."""
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"File not found for MIME detection: {path}")

    # Prefer signature sniffing to stay accurate even when renamed.
    signature_mime = _detect_signature(path)
    if signature_mime:
        return signature_mime

    # magic provides reliable detection for arbitrary binary payloads.
    if magic is not None:  # pragma: no cover - depends on native libmagic
        mime = magic.from_file(str(path), mime=True)
        if mime and mime != "application/octet-stream":
            return str(mime)

    # Fallback to extension-based guess when nothing else works.
    mime_guess, _ = mimetypes.guess_type(str(path))
    if mime_guess:
        return mime_guess

    raise ValueError("Unable to determine MIME type from content or extension")

def infer_extension_from_content_type_or_magic(file_path: str | Path) -> str:
    """Infer a safe extension from MIME type or raise if unsupported."""
    mime = infer_mime_type(file_path)
    if mime == "application/pdf":
        return ".pdf"
    if mime in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    }:
        return ".docx"
    raise ValueError(f"Unsupported MIME type detected: {mime}")