from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from src.schemas.normalizer import normalize_to_schema
from src.schemas.template_spec import canonical_template_items
from src.services.pdf_export import export_pdf_from_filled_json


def test_normalize_and_export_preserves_multiple_clauses(tmp_path: Path):
    # Prepare a sample analyzer-like payload with two clauses on the same item.
    section_closing, template_items = canonical_template_items("SECTION_II")
    raw = {
        "SECTION_I": {
            "Project Title:": "Sample Project",
            "Solicitation No.:": "RFP-123",
        },
        "SECTION_II": [
            {
                "item_number": template_items[0]["item_number"],
                "item_title": template_items[0]["item_title"],
                "clauses": [
                    {
                        "clause_language": "Clause language alpha",
                        "clause_summary": "Summary alpha",
                        "risk_triggers": "Risk alpha",
                        "flow_down_obligations": "Flow alpha",
                        "redline_recommendations": "Redline alpha",
                        "harmful_language_conflicts": "Conflict alpha",
                    },
                    {
                        "clause_language": "Clause language beta",
                        "clause_summary": "Summary beta",
                        "risk_triggers": "Risk beta",
                        "flow_down_obligations": "Flow beta",
                        "redline_recommendations": "Redline beta",
                        "harmful_language_conflicts": "Conflict beta",
                    },
                ],
                "closing_line": section_closing,
            }
        ],
    }

    # Normalize to schema to mimic pipeline output and preserve both clauses.
    normalized = normalize_to_schema(raw, section_closing, policy_version="test-policy")
    assert len(normalized["SECTION_II"][0]["clauses"]) == 2

    # Export the normalized payload to PDF so downstream rendering keeps both blocks.
    output_pdf = tmp_path / "report.pdf"
    pdf_path = export_pdf_from_filled_json(normalized, output_pdf, backend="reportlab")
    assert pdf_path.exists()

    # Confirm both clause texts are present in the rendered PDF content.
    reader = PdfReader(str(pdf_path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Clause language alpha" in text
    assert "Clause language beta" in text
