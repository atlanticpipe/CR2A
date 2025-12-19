from __future__ import annotations
import json
import os
import re
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
from src.core.config import get_secret_env_or_aws
from src.schemas.template_spec import (
    CR2A_TEMPLATE_SPEC,
    build_template_scaffold,
    canonical_template_items,
)

class OpenAIClientError(RuntimeError):
    """Typed error that carries an error category for HTTP mapping."""

    def __init__(self, category: str, message: str):
        super().__init__(message)
        self.category = category

OPENAI_BASE = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")
OPENAI_MODEL_DEFAULT = os.getenv("OPENAI_MODEL", "gpt-5.2")
DEFAULT_PLACEHOLDER_TEXT = "Not present in contract."

def _get_api_key() -> Optional[str]:
    # Resolve key from env or AWS Secrets Manager; keep secrets out of logs.
    key = get_secret_env_or_aws("OPENAI_API_KEY", "OPENAI_SECRET_ARN")
    return key

def _extract_text(data: Dict[str, Any]) -> str:
    # Prefer Responses API shape; fall back to chat-style messages if present.
    if isinstance(data, dict):
        output = data.get("output") or []
        for block in output:
            for item in block.get("content", []):
                item_type = item.get("type")
                text_value = item.get("text")
                # Accept both legacy output_text and new text content markers.
                if item_type in {"output_text", "text"} and text_value:
                    return str(text_value)
        choices = data.get("choices") or []
        if choices:
            msg = choices[0].get("message", {})
            content = msg.get("content")
            if isinstance(content, str):
                return content
    raise RuntimeError("OpenAI response missing text content")

def _parse_json_payload(raw_text: str) -> Dict[str, Any]:
    try:
        # Fast path when the model returned clean JSON.
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        # Log the actual error for debugging
        print(f"JSON parsing failed at line {e.lineno}, column {e.colno}: {e.msg}")
        print(f"Problematic text near error: {raw_text[max(0, e.pos-100):e.pos+100]}")
        
        # Best-effort salvage: slice the outermost object
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(raw_text[start : end + 1])
            except json.JSONDecodeError:
                # Try to fix common JSON issues
                cleaned = raw_text[start : end + 1]
                # Remove trailing commas before closing braces/brackets
                cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
                return json.loads(cleaned)
        raise OpenAIClientError("ProcessingError", f"Cannot parse OpenAI JSON response: {e.msg}")

def _load_clause_keywords() -> Dict[str, List[str]]:
    # Load clause classification synonyms to guide section-level search prompts.
    try:
        root = Path(__file__).resolve().parents[2]
        data = json.loads((root / "schemas" / "clause_classification.json").read_text(encoding="utf-8"))
        section_fit = data.get("section_fit") or {}
        return {k: [str(x) for x in v] for k, v in section_fit.items() if isinstance(v, list)}
    except Exception:
        return {}

def _derive_item_keywords(template_spec: Dict[str, Any], clause_keywords: Dict[str, List[str]]) -> Dict[str, List[str]]:
    # Combine template headings with synonym lists so the LLM searches relevant terms per item.
    derived: Dict[str, List[str]] = {}
    all_synonyms: List[str] = sorted(
        {phrase.lower() for phrases in clause_keywords.values() for phrase in phrases}
    )
    for sec_key, sec in (template_spec or {}).items():
        items = sec.get("items") or []
        sec_label = sec_key.rsplit("_", 1)[-1]
        for item in items:
            title = item.get("item_title", "")
            base_key = f"{sec_label}:{item.get('item_number', '')}"
            tokens = [tok.lower() for tok in re.findall(r"[A-Za-z][A-Za-z']+", title)]
            matches: List[str] = []
            for heading, phrases in clause_keywords.items():
                heading_tokens = [t.lower() for t in re.findall(r"[A-Za-z][A-Za-z']+", heading)]
                if heading.lower() in title.lower() or any(tok in heading_tokens for tok in tokens):
                    matches.extend([p.lower() for p in phrases])
            # Always return at least one synonym set so LLM searches stay guided.
            synonyms = matches or all_synonyms
            combined = sorted({*synonyms, *(t for t in tokens if t)}, key=lambda x: x)
            derived[base_key] = combined
    return derived

def _is_generic_clause(block: Dict[str, Any]) -> bool:
    # Detect placeholder-only clauses that should trigger a targeted re-run.
    generic_markers = {"", "n/a", "na", "not present", "not present in contract.", "not provided"}
    fields = [
        block.get("clause_language", ""),
        block.get("clause_summary", ""),
        block.get("risk_triggers", ""),
        block.get("flow_down_obligations", ""),
        block.get("redline_recommendations", ""),
        block.get("harmful_language_conflicts", ""),
    ]
    normalized = [str(f or "").strip().lower() for f in fields]
    return all(f in generic_markers for f in normalized)

def _validate_search_rationale(refined: Dict[str, Any]) -> None:
    # Enforce that any "Not present" language is backed by search_rationale.
    for sec_key in ["SECTION_II", "SECTION_III", "SECTION_IV", "SECTION_V", "SECTION_VI"]:
        for item in refined.get(sec_key, []) or []:
            for block in item.get("clauses", []) or []:
                rationale = str(block.get("search_rationale", "")).strip()
                any_not_present = any(
                    "not present" in str(block.get(field, "")).lower()
                    for field in [
                        "clause_language",
                        "clause_summary",
                        "risk_triggers",
                        "flow_down_obligations",
                        "redline_recommendations",
                        "harmful_language_conflicts",
                    ]
                )
                if any_not_present and not rationale:
                    raise OpenAIClientError(
                        "ValidationError",
                        f"Clause in {sec_key} is marked 'Not present' but missing search_rationale.",
                    )

def _call_openai(body: Dict[str, Any], headers: Dict[str, str], timeout: float) -> Dict[str, Any]:
    # Execute the OpenAI request with consistent error handling.
    with httpx.Client(timeout=timeout) as client:
        try:
            resp = client.post(f"{OPENAI_BASE}/v1/responses", headers=headers, json=body)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Surface actionable error details when the API rejects the request.
            detail = exc.response.text
            raise OpenAIClientError(
                "ProcessingError",
                f"OpenAI request failed ({exc.response.status_code}): {detail}",
            ) from exc
        data = resp.json()
    content = _extract_text(data)
    return _parse_json_payload(content)


def _seed_current_cr2a(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a LLM-friendly payload that already contains every template item with empty clauses.
    This ensures the model fills clauses instead of inventing or renaming items.
    """
    scaffold = build_template_scaffold(empty_clauses=True)
    seeded = {
        "SECTION_I": deepcopy(payload.get("SECTION_I", {})),  # Preserve overview fields verbatim.
        **scaffold,
    }
    # Preserve other optional sections without letting them overwrite the canonical scaffold.
    for optional_key in ["SECTION_VII", "SECTION_VIII", "OMISSION_CHECK", "doc_meta", "PROVENANCE"]:
        if optional_key in payload:
            seeded[optional_key] = deepcopy(payload[optional_key])
    return seeded


def _default_placeholder_clause(text: str) -> Dict[str, Any]:
    """
    Build a clause object using the required six fields so schema validation always passes.
    """
    return {
        "clause_language": text,
        "clause_summary": text,
        "risk_triggers": text,
        "flow_down_obligations": text,
        "redline_recommendations": text,
        "harmful_language_conflicts": text,
        "search_rationale": text,
        "provenance": {"source": "system", "page": 0, "span": ""},
    }


def _canonicalize_llm_sections(refined: Dict[str, Any], default_text: str) -> Dict[str, Any]:
    """
    Force SECTION_II–SECTION_VI to match the template spec exactly; reject renamed or missing items.
    """
    issues: List[str] = []
    canonical_sections: Dict[str, List[Dict[str, Any]]] = {}

    for sec_key in ["SECTION_II", "SECTION_III", "SECTION_IV", "SECTION_V", "SECTION_VI"]:
        closing_line, template_items = canonical_template_items(sec_key)
        incoming_items = refined.get(sec_key) or []
        matched: List[bool] = [False] * len(incoming_items)
        normalized_items: List[Dict[str, Any]] = []

        for tmpl in template_items:
            match_idx = next(
                (
                    idx
                    for idx, itm in enumerate(incoming_items)
                    if itm.get("item_number") == tmpl.get("item_number")
                    and itm.get("item_title") == tmpl.get("item_title")
                ),
                None,
            )

            if match_idx is not None:
                matched[match_idx] = True
                item = deepcopy(incoming_items[match_idx])
            else:
                issues.append(
                    f"{sec_key} missing item {tmpl.get('item_number')}: {tmpl.get('item_title')} — add the template item or accept the default placeholder."
                )
                item = {}

            item["item_number"] = tmpl.get("item_number")
            item["item_title"] = tmpl.get("item_title")
            item["closing_line"] = closing_line

            clauses = item.get("clauses") or []
            if not clauses:
                clauses = [_default_placeholder_clause(default_text)]
            item["clauses"] = clauses
            normalized_items.append(item)

        extras = [
            incoming_items[i]
            for i, found in enumerate(matched)
            if not found
        ]
        if extras:
            extras_desc = ", ".join(
                f"{ex.get('item_number', '?')}: {ex.get('item_title', 'Unnamed')}" for ex in extras
            )
            issues.append(
                f"{sec_key} has unexpected items not in template: {extras_desc} — remove these items to match the canonical template."
            )

        canonical_sections[sec_key] = normalized_items

    refined.update(canonical_sections)
    if issues:
        raise OpenAIClientError("ValidationError", "; ".join(issues))
    return refined


def _ensure_clause_rationale(refined: Dict[str, Any]) -> None:
    """
    Fail fast when any clause is missing search_rationale; downstream validators assume it exists.
    """
    for sec_key in ["SECTION_II", "SECTION_III", "SECTION_IV", "SECTION_V", "SECTION_VI"]:
        for item in refined.get(sec_key, []) or []:
            for block in item.get("clauses", []) or []:
                rationale = str(block.get("search_rationale", "")).strip()
                if not rationale:
                    raise OpenAIClientError(
                        "ValidationError",
                        f"{sec_key} item {item.get('item_number', '')} is missing search_rationale for a clause; supply a brief search trace.",
                    )


def _merge_item_update(
    refined: Dict[str, Any],
    sec_key: str,
    new_item: Dict[str, Any],
    default_prov: Dict[str, Any],
) -> None:
    # Merge refreshed clauses for a single item without dropping existing sections.
    items = refined.get(sec_key) or []
    merged: List[Dict[str, Any]] = []
    updated = False

    for item in items:
        if item.get("item_number") == new_item.get("item_number") and item.get("item_title") == new_item.get("item_title"):
            replacement = deepcopy(item)
            clauses = new_item.get("clauses") or []
            if clauses:
                replacement["clauses"] = clauses
            replacement["closing_line"] = new_item.get("closing_line", item.get("closing_line", ""))
            for block in replacement.get("clauses", []):
                block.setdefault("search_rationale", "")
                block.setdefault("provenance", default_prov.copy())
            merged.append(replacement)
            updated = True
        else:
            merged.append(item)

    if not updated and new_item:
        fallback = deepcopy(new_item)
        fallback.setdefault("item_title", "")
        fallback.setdefault("item_number", "")
        fallback.setdefault("clauses", [])
        for block in fallback.get("clauses", []):
            block.setdefault("search_rationale", "")
            block.setdefault("provenance", default_prov.copy())
        merged.append(fallback)

    refined[sec_key] = merged


def refine_cr2a(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Best-effort JSON refinement with OpenAI. If no key is present, raises.
    Keeps token usage low by prompting for structured JSON only.
    """
    api_key = _get_api_key()
    if not api_key:
        # Fail fast when no credentials are available so callers can skip refinement.
        raise OpenAIClientError("ValidationError", "Set OPENAI_API_KEY or OPENAI_SECRET_ARN to enable LLM refinement.")

    model = os.getenv("OPENAI_MODEL", OPENAI_MODEL_DEFAULT)
    timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0"))

    clause_keywords = _load_clause_keywords()
    derived_keywords = _derive_item_keywords(CR2A_TEMPLATE_SPEC, clause_keywords)

    system_text = (
        "You are a contracts attorney and risk analyst generating a Clause Risk & "
        "Compliance Analysis (CR2A) report.\n\n"
        "Return ONLY valid JSON; no commentary or markdown."
    )

    seeded_current = _seed_current_cr2a(payload)
    payload_for_llm = {
        "current_cr2a": seeded_current,
        "template_spec": CR2A_TEMPLATE_SPEC,
        "contract_text": payload.get("_contract_text", ""),
        "section_text": payload.get("_section_text", {}),
        "item_spans": payload.get("_item_spans", {}),
        "search_keywords": derived_keywords,
    }

    user_text = (
        "You are given a JSON object with two keys:\n"
        "- 'current_cr2a': a partial CR2A analysis of a contract.\n"
        "- 'template_spec': the complete list of required SectionItem templates "
        "for SECTION_II through SECTION_VI.\n\n"
        "Your task is to produce a FINAL CR2A JSON object that:\n"
        "1) Preserves SECTION_I from current_cr2a, enriching fields only where the "
        "contract clearly provides information.\n"
        "2) For EACH SectionItem listed in template_spec for SECTION_II–SECTION_VI, "
        "creates an element in that section's array with:\n"
        "   - item_number and item_title exactly as in template_spec.\n"
        "   - closing_line copied from template_spec for that section.\n"
        "   - clauses: an array containing one or more ClauseBlock objects.\n"
        "3) For EVERY ClauseBlock you create, you MUST fill all six fields:\n"
        "   clause_language, clause_summary, risk_triggers, "
        "flow_down_obligations, redline_recommendations, "
        "harmful_language_conflicts, plus a search_rationale string explaining where you looked.\n\n"
        "Rules:\n"
        "- Do NOT invent new SectionItem records or change item_title text.\n"
        "- Do NOT omit any items that appear in template_spec; every item "
        "must appear in the final JSON.\n"
        "- If the contract is silent for an item, you MUST still create a single "
        "ClauseBlock for that item and set all six fields to a clear statement "
        "such as 'Not present in contract.' plus a brief risk explanation AND a search_rationale that lists searched phrases and sections.\n"
        "- You may add more than one ClauseBlock for an item if the contract "
        "has multiple distinct clauses affecting that risk area.\n"
        "- Per item: search the most relevant section_text using synonyms and the provided search_keywords; prefer matches in the provided section_text span before scanning the full contract_text.\n"
        "- Only return the final CR2A JSON object. No explanations.\n\n"
        "Output format requirements:\n"
        "- Every clause block must include: clause_language, clause_summary, risk_triggers, flow_down_obligations, redline_recommendations, harmful_language_conflicts, search_rationale.\n"
        "- search_rationale must cite the phrases and section_text keys inspected; 'Not present' is only allowed when no relevant phrases were found in any section_text.\n\n"
        f"{json.dumps(payload_for_llm, ensure_ascii=False)}"
    )

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    org_id = os.getenv("OPENAI_ORG_ID")
    if org_id:
        headers["OpenAI-Organization"] = org_id
    base_body = {
        # Responses API payload requesting strict JSON output via the new text.format field.
        "model": model,
        "input": user_text,
        "instructions": system_text,
        "temperature": temperature,
        "max_tokens": 250000,
        "text": {"format": {"type": "json_object"}},  # text.format must be a structured object.
    }

    try:
        # Call the Responses API with a strict JSON-only contract to keep structure intact.
        refined = _call_openai(base_body, headers, timeout)
        refined = _canonicalize_llm_sections(refined, DEFAULT_PLACEHOLDER_TEXT)

        logging.info(f"OpenAI response type: {type(refined)}")
        logging.info(f"OpenAI response keys: {refined.keys() if isinstance(refined, dict) else 'Not a dict'}")

        default_prov = {"source": "LLM", "page": 0, "span": ""}

        for sec_key in ["SECTION_II", "SECTION_III", "SECTION_IV", "SECTION_V", "SECTION_VI"]:
            for item in refined.get(sec_key, []) or []:
                for block in item.get("clauses", []) or []:
                    block.setdefault("search_rationale", "")
                    block.setdefault("provenance", default_prov.copy())

        _validate_search_rationale(refined)
        _ensure_clause_rationale(refined)

        # Preserve source metadata and SECTION_I verbatim for downstream validators/exporters.
        refined["SECTION_I"] = deepcopy(payload.get("SECTION_I", {}))
        for meta_key in ["_contract_text", "_section_text", "_item_spans"]:
            if meta_key in payload:
                refined[meta_key] = payload[meta_key]

        retry_targets: List[Dict[str, Any]] = []
        item_spans = payload.get("_item_spans", {}) or {}
        section_text = payload.get("_section_text", {}) or {}

        for sec_key in ["SECTION_II", "SECTION_III", "SECTION_IV", "SECTION_V", "SECTION_VI"]:
            sec_label = sec_key.split("_")[-1]
            for item in refined.get(sec_key, []) or []:
                item_number = item.get("item_number", "")
                span_key = f"SECTION_{sec_label}:{item_number}"
                focus_span = item_spans.get(span_key) or section_text.get(sec_label, "")
                clauses = item.get("clauses") or []
                needs_retry = (not clauses) or any(_is_generic_clause(block) for block in clauses)
                if needs_retry and focus_span:
                    retry_targets.append(
                        {
                            "section": sec_key,
                            "item_number": item_number,
                            "item_title": item.get("item_title", ""),
                            "focus_span": focus_span,
                        }
                    )

        for idx, target in enumerate(retry_targets, start=1):
            logging.info("Retrying item %s %s (attempt %d)", target["section"], target["item_number"], idx)
            narrowed_body = json.loads(json.dumps(base_body))
            narrowed_body["input"] = (
                f"{user_text}\n\n"
                f"Retry ONLY for item {target['item_number']} ({target['item_title']}) in {target['section']}. "
                "Use the provided focus_span as the primary evidence. "
                f"focus_span:\n{target['focus_span']}\n\n"
                "Return JSON with only the updated section and item, keeping field names exact. "
                "Fill all clause fields with specific language from focus_span where possible and include search_rationale."
            )
            try:
                retry_refined = _call_openai(narrowed_body, headers, timeout)
                retry_scaffolded = {**build_template_scaffold(empty_clauses=True), **retry_refined}
                retry_refined = _canonicalize_llm_sections(retry_scaffolded, DEFAULT_PLACEHOLDER_TEXT)
            except httpx.TimeoutException as exc:
                raise OpenAIClientError("TimeoutError", f"OpenAI retry timed out for {target['section']} {target['item_number']}: {exc}") from exc
            except httpx.RequestError as exc:
                raise OpenAIClientError("NetworkError", f"OpenAI retry failed for {target['section']} {target['item_number']}: {exc}") from exc

            for item in retry_refined.get(target["section"], []) or []:
                for block in item.get("clauses", []) or []:
                    block.setdefault("search_rationale", "")
                    block.setdefault("provenance", default_prov.copy())
                _merge_item_update(refined, target["section"], item, default_prov)

            _validate_search_rationale(refined)

        refined = _canonicalize_llm_sections(refined, DEFAULT_PLACEHOLDER_TEXT)

        # Preserve source text hints for downstream processors.
        refined["SECTION_I"] = deepcopy(payload.get("SECTION_I", {}))
        for meta_key in ["_contract_text", "_section_text", "_item_spans"]:
            if meta_key in payload:
                refined[meta_key] = payload[meta_key]

        for sec_key in ["SECTION_II", "SECTION_III", "SECTION_IV", "SECTION_V", "SECTION_VI"]:
            for item in refined.get(sec_key, []) or []:
                for block in item.get("clauses", []) or []:
                    block.setdefault("search_rationale", "")
                    block.setdefault("provenance", default_prov.copy())

        _validate_search_rationale(refined)
        _ensure_clause_rationale(refined)

        return refined
    except httpx.TimeoutException as exc:
        # Bubble up a concise timeout message so the caller can retry or bypass refinement.
        raise OpenAIClientError("TimeoutError", f"OpenAI request timed out: {exc}")
    except httpx.RequestError as exc:
        # Network failures should not be silent; expose enough detail without leaking secrets.
        raise OpenAIClientError("NetworkError", f"OpenAI request failed: {exc}")
    except OpenAIClientError:
        # Propagate typed errors unchanged for upstream mapping.
        raise
    except Exception as exc:
        # Catch-all to avoid surfacing raw tracebacks to the API surface.
        raise OpenAIClientError("ProcessingError", f"OpenAI refinement failed: {exc}")
