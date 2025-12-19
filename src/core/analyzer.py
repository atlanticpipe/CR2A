from __future__ import annotations

import io
import json
import re
import time
import logging
from typing import Any, Dict, List, Tuple, Union
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None  # type: ignore

try:
    import boto3  # AWS Textract
except Exception:
    boto3 = None  # type: ignore

try:
    import pytesseract
    from PIL import Image
except Exception:
    pytesseract = None  # type: ignore
    Image = None  # type: ignore

from src.utils.mime_utils import infer_mime_type

logger = logging.getLogger(__name__)

def _read_json(path: Union[str, Path]) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def _get_policy_closing_line(root: Union[str, Path]) -> str:
    root = Path(root).expanduser().resolve()
    rules_path = root / "schemas" / "validation_rules.json"
    try:
        rules = _read_json(rules_path)
        val = rules.get("validation", rules)
        return val.get("mandatory_fields", {}).get(
            "section_II_to_VI_closing_line",
            "All applicable clauses for [Item #/Title] have been identified and analyzed.",
        )
    except Exception:
        return "All applicable clauses for [Item #/Title] have been identified and analyzed."


_DOCX_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

def _docx_iter_paragraphs(docx_bytes: bytes) -> List[str]:
    import zipfile
    with io.BytesIO(docx_bytes) as bio:
        with zipfile.ZipFile(bio) as z:
            xml_bytes = z.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    lines: List[str] = []
    for p in root.findall(".//w:p", _DOCX_NS):
        texts = []
        for t in p.findall(".//w:t", _DOCX_NS):
            texts.append(t.text or "")
        line = "".join(texts).strip()
        if line:
            lines.append(line)
    return lines

def _pdf_text_pages_with_pymupdf(pdf_bytes: bytes) -> List[str]:
    if fitz is None:
        return []
    pages: List[str] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            txt = page.get_text("text") or ""
            pages.append(txt.strip())
    return pages

def _pdf_ocr_with_textract(pdf_bytes: bytes) -> List[str]:
    if boto3 is None or fitz is None:
        return []
    pages_text: List[str] = []
    textract = boto3.client("textract")
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            pix = page.get_pixmap(alpha=False)
            img_bytes = pix.tobytes("png")
            resp = textract.detect_document_text(Document={"Bytes": img_bytes})
            lines = [b["Text"] for b in resp.get("Blocks", []) if b.get("BlockType") == "LINE"]
            pages_text.append("\n".join(lines).strip())
    return pages_text

def _pdf_ocr_with_tesseract(pdf_bytes: bytes) -> List[str]:
    if pytesseract is None or Image is None or fitz is None:
        return []
    pages_text: List[str] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            pix = page.get_pixmap(alpha=False)
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))
            txt = pytesseract.image_to_string(img)
            pages_text.append(txt.strip())
    return pages_text

def _pdf_extract_pages(pdf_bytes: bytes, ocr_mode: str = "auto") -> List[str]:
    # 1) Try native text first
    text_pages = _pdf_text_pages_with_pymupdf(pdf_bytes)
    if any(text_pages):
        return text_pages

    # 2) OCR fallback
    mode = (ocr_mode or "auto").lower()
    if mode == "none":
        # No OCR; return blank pages if we can count them
        if fitz is not None:
            with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                return ["" for _ in doc]
        return [""]

    if mode == "textract":
        ocr = _pdf_ocr_with_textract(pdf_bytes)
        if any(ocr):
            return ocr
    elif mode == "tesseract":
        ocr = _pdf_ocr_with_tesseract(pdf_bytes)
        if any(ocr):
            return ocr
    else:  # auto
        ocr = _pdf_ocr_with_textract(pdf_bytes)
        if not any(ocr):
            ocr = _pdf_ocr_with_tesseract(pdf_bytes)
        if any(ocr):
            return ocr

    # 3) Couldn’t extract anything
    if fitz is not None:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            return ["" for _ in doc]
    return [""]

SECTION_I_FIELDS = [
    "Project Title:",
    "Solicitation No.:",
    "Owner:",
    "Contractor:",
    "Scope:",
    "General Risk Level:",
    "Bid Model:",
    "Notes:",
]

_SECTION_HEADER_RX = {
    "I": re.compile(r"^\s*I\.\s*(Contract Overview|Overview)\b", re.I),
    "II": re.compile(r"^\s*II\.\s*(Parties|Parties\s*&\s*Dates|Parties and Dates)\b", re.I),
    "III": re.compile(r"^\s*III\.\s*(Scope|Scope\s*&\s*Deliverables|Scope of Work)\b", re.I),
    "IV": re.compile(r"^\s*IV\.\s*(Payment|Payment Terms)\b", re.I),
    "V": re.compile(r"^\s*V\.\s*(Risk Allocation|Liability|Indemn)", re.I),
    "VI": re.compile(r"^\s*VI\.\s*(Compliance|Legal)\b", re.I),
}

def _locate_sections(lines: List[str]) -> Dict[str, Tuple[int,int]]:
    starts: Dict[str, int] = {}
    for i, ln in enumerate(lines):
        for sec, rx in _SECTION_HEADER_RX.items():
            if sec not in starts and rx.search(ln):
                starts[sec] = i
    ordered = [(k, starts[k]) for k in ["I","II","III","IV","V","VI"] if k in starts]
    spans: Dict[str, Tuple[int,int]] = {}
    for idx, (sec, start) in enumerate(ordered):
        end = len(lines)
        if idx + 1 < len(ordered):
            end = ordered[idx+1][1]
        spans[sec] = (start, end)
    return spans

def _build_section_i(lines: List[str]) -> Dict[str, str]:
    res = {k: "Not present in contract." for k in SECTION_I_FIELDS}
    for i, ln in enumerate(lines):
        for key in SECTION_I_FIELDS:
            if ln.startswith(key):
                val = ln[len(key):].strip()
                if not val and i+1 < len(lines) and not any(lines[i+1].startswith(f) for f in SECTION_I_FIELDS):
                    val = lines[i+1].strip()
                res[key] = val or "Not present in contract."
    return res

def _parse_clause_blocks(region_lines: List[str], span_text: str) -> List[Dict[str, Any]]:
    labels = {
        "clause_language": [r"^Clause Language:\s*(.*)$"],
        "clause_summary": [r"^Clause Summary:\s*(.*)$"],
        "risk_triggers": [r"^Risk Triggers?:\s*(.*)$"],
        "flow_down_obligations": [r"^Flow[- ]?Down Obligations?:\s*(.*)$", r"^Flow[- ]?Down:\s*(.*)$"],
        "redline_recommendations": [r"^Redline Recommendations?:\s*(.*)$", r"^Redlines?:\s*(.*)$"],
        "harmful_language_conflicts": [r"^Harmful Language(?:/| and )Conflicts?:\s*(.*)$", r"^Conflicts?:\s*(.*)$"],
    }
    collected = {k: [] for k in labels.keys()}
    for ln in region_lines:
        for key, patterns in labels.items():
            for pat in patterns:
                m = re.match(pat, ln, re.I)
                if m:
                    val = m.group(1).strip()
                    if val:
                        collected[key].append(val)
                    break
    if not any(collected[k] for k in collected):
        # Fall back to heuristic span capture when no structured labels are found.
        return [{
            "clause_language": " ".join(region_lines[:6])[:2000],
            "clause_summary": "",
            "risk_triggers": "",
            "flow_down_obligations": "",
            "redline_recommendations": "",
            "harmful_language_conflicts": "",
            "provenance": {"source": "document", "method": "heuristic", "span": span_text[:2000]}
        }]
    return [{
        "clause_language": (collected["clause_language"][0] if collected["clause_language"] else ""),
        "clause_summary": (collected["clause_summary"][0] if collected["clause_summary"] else ""),
        "risk_triggers": collected["risk_triggers"][0] if collected["risk_triggers"] else "",
        "flow_down_obligations": (collected["flow_down_obligations"][0] if collected["flow_down_obligations"] else ""),
        "redline_recommendations": (collected["redline_recommendations"][0] if collected["redline_recommendations"] else ""),
        "harmful_language_conflicts": (collected["harmful_language_conflicts"][0] if collected["harmful_language_conflicts"] else ""),
        "provenance": {"source": "document", "method": "labels", "span": span_text[:2000]}
    }]

def _items_from_region(region_lines: List[str], title_fallback: str, closing_line: str, section_label: str) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    # Capture raw text span for downstream LLM targeting and search diagnostics.
    span_text = "\n".join(region_lines).strip()
    title = next((ln for ln in region_lines if ln.strip()), title_fallback)[:200]
    item = {
        "item_number": 1,
        "item_title": title,
        "clauses": _parse_clause_blocks(region_lines, span_text),
        "closing_line": closing_line,
        "source_span": span_text,
        "section_label": section_label,
    }
    return [item], {f"SECTION_{section_label}:1": span_text}

def _build_from_lines(lines: List[str], closing_line: str) -> Dict[str, Any]:
    spans = _locate_sections(lines)
    payload: Dict[str, Any] = {}
    section_text: Dict[str, str] = {}
    item_spans: Dict[str, str] = {}
    if "I" in spans:
        s, e = spans["I"]; payload["SECTION_I"] = _build_section_i(lines[s:e])
    else:
        payload["SECTION_I"] = {k: "Not present in contract." for k in SECTION_I_FIELDS}

    for sec in ["II","III","IV","V","VI"]:
        if sec in spans:
            s, e = spans[sec]
            region = lines[s+1:e]
            section_text[sec] = "\n".join(lines[s:e]).strip()
            items, spans_map = _items_from_region(region, f"{sec} item", closing_line, sec)
            item_spans.update(spans_map)
            payload[f"SECTION_{sec}"] = items
        else:
            payload[f"SECTION_{sec}"] = []

    payload["PROVENANCE"] = {"version": "1.0.0", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
    payload["_contract_text"] = "\n".join(lines).strip()
    payload["_section_text"] = section_text
    payload["_item_spans"] = item_spans
    return payload

def analyze_to_json(input_path: Union[str, Path], repo_root: Union[str, Path], ocr: str = "auto") -> Dict[str, Any]:
    input_path = Path(input_path).expanduser().resolve()
    closing_line = _get_policy_closing_line(repo_root)

    # Resolve MIME from content so renamed binaries are still classified correctly.
    mime_type = infer_mime_type(input_path)
    logger.debug(
        "Analyzing file",
        extra={
            "file_name": input_path.name,
            "mime_type": mime_type,
            "detected_via": "mime-sniff",
        },
    )

    if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or mime_type == "application/msword":
        lines = _docx_iter_paragraphs(input_path.read_bytes())
        return _build_from_lines(lines, closing_line)

    if mime_type == "application/pdf":
        pdf_bytes = input_path.read_bytes()
        pages = _pdf_extract_pages(pdf_bytes, ocr_mode=ocr)
        lines: List[str] = []
        for ptxt in pages:
            for ln in (ptxt or "").splitlines():
                lines.append(ln.strip())
            lines.append("")
        return _build_from_lines(lines, closing_line)

    raise ValueError(f"Unsupported input type: {mime_type}")
