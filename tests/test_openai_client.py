from __future__ import annotations

import copy
from typing import Any, Dict, List

import pytest

from src.schemas.template_spec import canonical_template_items
from src.services import openai_client
from src.services.openai_client import (
    DEFAULT_PLACEHOLDER_TEXT,
    OpenAIClientError,
    _canonicalize_llm_sections,
    _is_generic_clause,
    refine_cr2a,
)


def _scaffold_with_text(clause_text: str, rationale: str) -> Dict[str, Any]:
    # Build a minimal response that mirrors the template so canonicalization passes.
    response: Dict[str, List[Dict[str, Any]]] = {}
    for sec_key in ["SECTION_II", "SECTION_III", "SECTION_IV", "SECTION_V", "SECTION_VI"]:
        _, template_items = canonical_template_items(sec_key)
        response[sec_key] = []
        for item in template_items:
            response[sec_key].append(
                {
                    "item_number": item["item_number"],
                    "item_title": item["item_title"],
                    "clauses": [
                        {
                            "clause_language": clause_text,
                            "clause_summary": clause_text,
                            "risk_triggers": clause_text,
                            "flow_down_obligations": clause_text,
                            "redline_recommendations": clause_text,
                            "harmful_language_conflicts": clause_text,
                            "search_rationale": rationale,
                            "provenance": {"source": "seed", "page": 1, "span": "seed span"},
                        }
                    ],
                }
            )
    return response


def test_is_generic_clause_detects_placeholders():
    # Ensure placeholder text is flagged while substantive text is not.
    generic_block = {
        "clause_language": "Not present in contract.",
        "clause_summary": "Not present in contract.",
        "risk_triggers": "Not present in contract.",
        "flow_down_obligations": "Not present in contract.",
        "redline_recommendations": "Not present in contract.",
        "harmful_language_conflicts": "Not present in contract.",
    }
    assert _is_generic_clause(generic_block) is True

    real_block = copy.deepcopy(generic_block)
    real_block["clause_language"] = "Actual clause text"
    assert _is_generic_clause(real_block) is False


def test_canonicalize_preserves_multi_clause_blocks():
    # Seed all sections so validation passes, then attach multiple clauses to one item.
    response = _scaffold_with_text("Initial clause", "first sweep")
    response["SECTION_II"][0]["clauses"] = [
        {
            "clause_language": "Clause A",
            "clause_summary": "Summary A",
            "risk_triggers": "Risk A",
            "flow_down_obligations": "Flow A",
            "redline_recommendations": "Redline A",
            "harmful_language_conflicts": "Conflict A",
            "search_rationale": "Trace A",
            "provenance": {"source": "seed", "page": 1, "span": "A"},
        },
        {
            "clause_language": "Clause B",
            "clause_summary": "Summary B",
            "risk_triggers": "Risk B",
            "flow_down_obligations": "Flow B",
            "redline_recommendations": "Redline B",
            "harmful_language_conflicts": "Conflict B",
            "search_rationale": "Trace B",
            "provenance": {"source": "seed", "page": 2, "span": "B"},
        },
    ]

    normalized = _canonicalize_llm_sections(response, DEFAULT_PLACEHOLDER_TEXT)
    multi_clause = normalized["SECTION_II"][0]["clauses"]
    assert len(multi_clause) == 2
    assert {block["clause_language"] for block in multi_clause} == {"Clause A", "Clause B"}


def test_canonicalize_rejects_missing_items():
    # Drop a required item to confirm validation failure is surfaced.
    response = _scaffold_with_text("Initial clause", "first sweep")
    response["SECTION_III"] = response["SECTION_III"][:-1]
    with pytest.raises(OpenAIClientError) as excinfo:
        _canonicalize_llm_sections(response, DEFAULT_PLACEHOLDER_TEXT)
    assert "missing item" in str(excinfo.value)


def test_refine_merges_retry_results(monkeypatch):
    # Mock API key resolution so refine_cr2a executes without real secrets.
    monkeypatch.setattr(openai_client, "_get_api_key", lambda: "test-key")

    # Build an initial response where one item is generic to trigger a retry.
    base_response = _scaffold_with_text(DEFAULT_PLACEHOLDER_TEXT, "initial search")
    for sec_key, items in base_response.items():
        for idx, item in enumerate(items):
            for field_block in item.get("clauses", []):
                # Seed non-target items with substantive text so they are not retried.
                if not (sec_key == "SECTION_II" and idx == 0):
                    for key in [
                        "clause_language",
                        "clause_summary",
                        "risk_triggers",
                        "flow_down_obligations",
                        "redline_recommendations",
                        "harmful_language_conflicts",
                    ]:
                        field_block[key] = "Specific content"
                    field_block["search_rationale"] = "kept rationale"
                    field_block["provenance"] = {"source": "initial", "page": 1, "span": "init"}

    base_response["SECTION_II"][0]["clauses"][0]["search_rationale"] = "initial rationale"
    base_response["SECTION_II"][0]["clauses"][0]["provenance"] = {"source": "initial", "page": 1, "span": "init"}

    retry_response = copy.deepcopy(base_response)
    retry_clause = retry_response["SECTION_II"][0]["clauses"][0]
    retry_clause.update(
        {
            "clause_language": "Focused clause",
            "clause_summary": "Focused summary",
            "risk_triggers": "Focused risk",
            "flow_down_obligations": "Focused flow",
            "redline_recommendations": "Focused redline",
            "harmful_language_conflicts": "Focused conflict",
            "search_rationale": "focused rationale",
            "provenance": {"source": "retry", "page": 2, "span": "focus"},
        }
    )

    # Provide deterministic OpenAI responses: initial then retry.
    calls = iter([base_response, retry_response])
    monkeypatch.setattr(openai_client, "_call_openai", lambda *args, **kwargs: next(calls))

    # Build payload with focused spans so retry targets are discovered.
    payload: Dict[str, Any] = {
        "SECTION_I": {"Project Title:": "Test"},
        "_contract_text": "sample contract",
        "_section_text": {sec: f"{sec} section text" for sec in ["II", "III", "IV", "V", "VI"]},
        "_item_spans": {},
    }
    for sec_key in ["SECTION_II", "SECTION_III", "SECTION_IV", "SECTION_V", "SECTION_VI"]:
        _, template_items = canonical_template_items(sec_key)
        label = sec_key.split("_")[-1]
        payload.setdefault(sec_key, [])
        for item in template_items:
            span_key = f"SECTION_{label}:{item['item_number']}"
            payload["_item_spans"][span_key] = f"{span_key} focus span"

    refined = refine_cr2a(payload)
    updated_item = refined["SECTION_II"][0]
    clause = updated_item["clauses"][0]

    # The retry clause should override the placeholder and carry rationale/provenance.
    assert clause["clause_language"] == "Focused clause"
    assert clause["search_rationale"] == "focused rationale"
    assert clause["provenance"]["source"] == "retry"

    # Non-retried items should preserve their original clause details.
    preserved_clause = refined["SECTION_II"][1]["clauses"][0]
    assert preserved_clause["clause_language"] == "Specific content"
    assert preserved_clause["provenance"]["source"] == "initial"
