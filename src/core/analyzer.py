from __future__ import annotations

import io
import json
import re
import time
import logging
from typing import Any, Dict, List, Tuple, Union, Optional
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
from src.schemas.template_spec import CR2A_TEMPLATE_SPEC, canonical_template_items

logger = logging.getLogger(__name__)

class AnalyzerError(RuntimeError):
    """Typed error for analyzer failures so callers can map categories."""

    def __init__(self, category: str, message: str):
        super().__init__(message)
        self.category = category

def _read_json(path: Union[str, Path]) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))

# Load section map patterns so section detection stays deterministic.
try:
    _SECTION_MAP = _read_json(Path(__file__).resolve().parents[2] / "schemas" / "section_map.json")
except Exception:
    _SECTION_MAP = {"patterns": {}, "section_order": ["I", "II", "III", "IV", "V", "VI"]}

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
    # Disable entity expansion to prevent XXE attacks
    root = ET.fromstring(xml_bytes, parser=ET.XMLParser(resolve_entities=False))
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
    MAX_PDF_SIZE = 500 * 1024 * 1024
    if len(pdf_bytes) > MAX_PDF_SIZE:
        raise AnalyzerError("ValidationError", f"PDF file too large: {len(pdf_bytes)} bytes")
    
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

def _locate_sections(lines: List[str]) -> Dict[str, Tuple[int, int]]:
    """
    Locate top-level section spans using regex patterns so downstream slicing stays stable.
    """
    pattern_overrides = _SECTION_MAP.get("patterns") or {}
    order = [sec for sec in _SECTION_MAP.get("section_order", []) if sec in {"I", "II", "III", "IV", "V", "VI"}]
    compiled: Dict[str, re.Pattern[str]] = {}
    for sec, rx in _SECTION_HEADER_RX.items():
        # Prefer data-driven patterns; fall back to static defaults.
        if sec in pattern_overrides:
            compiled[sec] = re.compile(pattern_overrides[sec], re.I)
        else:
            compiled[sec] = rx

    starts: Dict[str, int] = {}
    for i, ln in enumerate(lines):
        for sec, rx in compiled.items():
            if sec not in starts and rx.search(ln):
                starts[sec] = i

    ordered = [(k, starts[k]) for k in order if k in starts]
    spans: Dict[str, Tuple[int, int]] = {}
    for idx, (sec, start) in enumerate(ordered):
        end = len(lines)
        if idx + 1 < len(ordered):
            end = ordered[idx + 1][1]
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

def _find_item_anchor_indices(region_lines: List[str], item_number: int, item_title: str) -> Optional[int]:
    """
    Return the earliest line index matching either the numbered heading or a title fragment.
    """
    # Limit title length to prevent ReDoS attacks
    MAX_TITLE_LENGTH = 500
    item_title = item_title[:MAX_TITLE_LENGTH]
    
    tokens = re.findall(r"[A-Za-z][A-Za-z']+", item_title)
    trimmed = tokens[:6]
    title_pattern = re.compile(r".*".join(re.escape(tok) for tok in trimmed), re.I) if trimmed else None
    candidates: List[int] = []
    number_pat = re.compile(rf"^\s*{item_number}[\.\)]\s*", re.I)
    for idx, line in enumerate(region_lines):
        if number_pat.search(line):
            candidates.append(idx)
            continue
        if title_pattern and title_pattern.search(line):
            candidates.append(idx)
    return min(candidates) if candidates else None


def _focus_span_lines(span_lines: List[str]) -> List[str]:
    """
    Prefer clause headings or numbered list entries; fall back to nearby paragraphs.
    """
    heading_rx = re.compile(r"^(Clause Language|Clause Summary|Risk Trigger|Risk Triggers?|Flow[- ]?Down|Redline|Harmful)", re.I)
    list_rx = re.compile(r"^\s*(\d+\.|\([a-z0-9]+\)|[a-z]\))", re.I)
    for idx, line in enumerate(span_lines):
        if heading_rx.search(line):
            start = max(0, idx - 1)
            end = min(len(span_lines), idx + 8)
            return span_lines[start:end]
    for idx, line in enumerate(span_lines):
        if list_rx.search(line):
            end = min(len(span_lines), idx + 8)
            return span_lines[idx:end]
    cleaned = [ln for ln in span_lines if ln.strip()]
    return cleaned[:8] if cleaned else span_lines[:6]


def _items_from_region(
    region_lines: List[str],
    section_label: str,
    template_items: List[Dict[str, Any]],
    default_closing_line: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Build deterministic items for a section using template ordering and focused spans.
    """
    item_spans: Dict[str, str] = {}
    items: List[Dict[str, Any]] = []
    anchor_map: Dict[int, int] = {}
    for spec in template_items:
        # Cache the earliest anchor so we can build non-overlapping spans.
        idx = _find_item_anchor_indices(region_lines, int(spec.get("item_number", 0) or 0), spec.get("item_title", ""))
        if idx is not None:
            anchor_map[int(spec.get("item_number", 0) or 0)] = idx

    sorted_anchors = sorted(anchor_map.items(), key=lambda kv: kv[1])
    fallback_span = "\n".join(region_lines).strip()

    for pos, spec in enumerate(template_items):
        item_number = int(spec.get("item_number", 0) or 0)
        item_title = spec.get("item_title", "")[:200]
        start = anchor_map.get(item_number)
        if start is None:
            # Evenly distribute a fallback anchor when no heading is present.
            start = int(len(region_lines) * pos / max(len(template_items), 1))
        # End at the next anchor or the end of the region to keep spans non-overlapping.
        later_anchors = [a for _, a in sorted_anchors if a > start]
        end = later_anchors[0] if later_anchors else len(region_lines)
        span_lines = region_lines[start:end] if region_lines else []
        focus_lines = _focus_span_lines(span_lines)
        span_text = "\n".join(focus_lines).strip()
        if not span_text:
            span_text = f"[Fallback] No focused span found for item {item_number} ({item_title}); use section context.\n{fallback_span}"
        span_key = f"SECTION_{section_label}:{item_number}"
        item_spans[span_key] = span_text
        parse_lines = focus_lines or span_text.splitlines()
        clauses = _parse_clause_blocks(parse_lines, span_text)
        closing_line = spec.get("closing_line", "") or default_closing_line
        items.append(
            {
                "item_number": item_number,
                "item_title": item_title,
                "clauses": clauses,
                "closing_line": closing_line,
                "source_span": span_text,
                "section_label": section_label,
            }
        )
    return items, item_spans

def _build_from_lines(lines: List[str], closing_line: str) -> Dict[str, Any]:
    spans = _locate_sections(lines)
    payload: Dict[str, Any] = {}
    section_text: Dict[str, str] = {}
    item_spans: Dict[str, str] = {}
    if "I" in spans:
        s, e = spans["I"]; payload["SECTION_I"] = _build_section_i(lines[s:e])
    else:
        payload["SECTION_I"] = {k: "Not present in contract." for k in SECTION_I_FIELDS}

    for sec in ["II", "III", "IV", "V", "VI"]:
        sec_key = f"SECTION_{sec}"
        section_default = "\n".join(lines[spans[sec][0]:spans[sec][1]]).strip() if sec in spans else ""
        section_text[sec] = section_default or f"[Fallback] Section {sec} not detected; using empty span."
        try:
            template_closing, template_items = canonical_template_items(sec_key)
        except KeyError:
            template_closing = closing_line
            template_items = CR2A_TEMPLATE_SPEC.get(sec_key, {}).get("items", [])
        region = lines[spans[sec][0] + 1:spans[sec][1]] if sec in spans else []
        items, spans_map = _items_from_region(region, sec, template_items, template_closing or closing_line)
        item_spans.update(spans_map)
        payload[sec_key] = items

    payload["PROVENANCE"] = {"version": "1.0.0", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
    payload["_contract_text"] = "\n".join(lines).strip()
    payload["_section_text"] = section_text
    payload["_item_spans"] = item_spans
    return payload

def _validate_item_spans(payload: Dict[str, Any]) -> None:
    """
    Ensure every template item has a focused span or an explicit fallback note.
    """
    spans = payload.get("_item_spans", {}) or {}
    missing: List[str] = []
    for sec_key, spec in CR2A_TEMPLATE_SPEC.items():
        sec_label = sec_key.rsplit("_", 1)[-1]
        for item in spec.get("items", []):
            key = f"SECTION_{sec_label}:{item.get('item_number', '')}"
            span_val = str(spans.get(key, "")).strip()
            if not span_val:
                missing.append(key)
    if missing:
        raise AnalyzerError("ValidationError", f"Missing focused spans for items: {', '.join(missing)}")

def analyze_to_json(input_path: Union[str, Path], repo_root: Union[str, Path], ocr: str = "auto") -> Dict[str, Any]:
    input_path = Path(input_path).expanduser().resolve()
    
    if not input_path.exists():
        raise AnalyzerError("FileNotFoundError", f"Input file not found: {input_path}")
    
    if not input_path.is_file():
        raise AnalyzerError("ValidationError", f"Input path is not a file: {input_path}")
    
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
        try:
            lines = _docx_iter_paragraphs(input_path.read_bytes())
        except Exception as e:
            raise AnalyzerError("FileReadError", f"Failed to read DOCX file: {e}") from e
        try:
            payload = _build_from_lines(lines, closing_line)
            _validate_item_spans(payload)
            return payload
        except AnalyzerError:
            raise
        except Exception as e:
            raise AnalyzerError("ProcessingError", f"Failed to process DOCX content: {e}") from e

    if mime_type == "application/pdf":
        try:
            pdf_bytes = input_path.read_bytes()
        except Exception as e:
            raise AnalyzerError("FileReadError", f"Failed to read PDF file: {e}") from e
        
        try:
            pages = _pdf_extract_pages(pdf_bytes, ocr_mode=ocr)
        except Exception as e:
            raise AnalyzerError("PDFProcessingError", f"Failed to extract PDF pages: {e}") from e
        
        try:
            lines: List[str] = []
            for ptxt in pages:
                for ln in (ptxt or "").splitlines():
                    lines.append(ln.strip())
                lines.append("")
            payload = _build_from_lines(lines, closing_line)
            _validate_item_spans(payload)
            return payload
        except AnalyzerError:
            raise
        except Exception as e:
            raise AnalyzerError("ProcessingError", f"Failed to process PDF content: {e}") from e

    raise AnalyzerError("ValidationError", f"Unsupported input type: {mime_type}")