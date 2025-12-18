import os
import json
from typing import Any, Dict, Optional

from openai import OpenAI  # pip install --upgrade openai

# Environment configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "120"))

client = OpenAI(api_key=OPENAI_API_KEY)  # uses env var by default [web:2]

class OpenAIClientError(Exception):
    pass

def _call_openai_responses(
    instructions: str,
    input_payload: Dict[str, Any],
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Helper to call the Responses API and return parsed JSON.
    Expects the model to return ONLY a JSON object as text. [web:2][web:20]
    """
    use_model = model or OPENAI_MODEL
    try:
        response = client.responses.create(
            model=use_model,
            instructions=instructions,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(input_payload),
                        }
                    ],
                }
            ],
            timeout=OPENAI_TIMEOUT,
        )
    except Exception as exc:
        raise OpenAIClientError(f"OpenAI API call failed: {exc}") from exc

    # Extract text output from Responses API [web:2]
    try:
        text_chunks = []
        for item in response.output:
            if getattr(item, "type", None) == "message":
                for c in item.content:
                    if getattr(c, "type", None) == "output_text":
                        text_chunks.append(c.text)
        output_text = "".join(text_chunks).strip()
        if not output_text:
            raise ValueError("Empty response text from OpenAI")
        return json.loads(output_text)
    except Exception as exc:
        raise OpenAIClientError(f"Failed to parse JSON from OpenAI: {exc}") from exc

def refine_cr2a(
    *,
    contract_text: str,
    cr2a_skeleton: Dict[str, Any],
    template_spec: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Take raw contract text + a sparse CR2A skeleton (SECTION_I–VI) and
    return a fully-populated CR2A JSON object that matches output_schemas.json.

    Inputs:
      - contract_text: full contract text (or relevant sections)
      - cr2a_skeleton: current SECTION_I–VI structure from the heuristic analyzer
      - template_spec: optional description of all CR2A items / headings; if not
        provided, the model infers items from the skeleton keys.
    """
    if not OPENAI_API_KEY:
        # If no key, just return the skeleton unmodified so pipeline still runs
        return cr2a_skeleton

    # This payload is what the model sees
    payload = {
        "contract_text": contract_text,
        "current_cr2a": cr2a_skeleton,
        "template_spec": template_spec,
    }

    instructions = """
You are a contracts attorney and risk analyst generating a Clause Risk & Compliance Analyzer (CR2A) report.

Goal:
Return a SINGLE JSON object that fully populates a CR2A report for this contract.

You are given:
- "contract_text": the full contract (or large portions of it).
- "current_cr2a": a sparse JSON skeleton with SECTION_I–SECTION_VI.
- Optionally "template_spec": a description of all CR2A items and subsections.

Requirements for the output:
1. Shape:
   - Return a JSON object with top-level keys:
     "SECTION_I", "SECTION_II", "SECTION_III", "SECTION_IV", "SECTION_V", "SECTION_VI".
   - The structure MUST match and be compatible with the current_cr2a keys so that
     a downstream normalizer and PDF exporter can consume it without errors.
   - Do NOT invent new top-level section names.

2. Items and clauses:
   - For SECTIONS II–VI, enumerate ALL material items and sub-items that a
     diligent CR2A reviewer would include, based on the contract_text and template_spec.
   - Each item must contain one or more "clauses" objects.

3. Per-clause detail:
   For EVERY clause you include, populate ALL of the following fields:
   - "clause_language": the most relevant excerpt(s) from the contract, quoted or closely paraphrased.
   - "clause_summary": a concise, business-readable summary of what the clause does.
   - "risk_triggers": specific conditions or events that would create risk or liability.
   - "flow_down_obligations": obligations that must be imposed on subcontractors or third parties.
   - "redline_recommendations": concrete, actionable redline or negotiation suggestions.
   - "harmful_language_conflicts": any conflicts with standard terms, policies, or existing agreements.

4. Use of the skeleton:
   - You MAY reuse and refine any existing items in current_cr2a.
   - You MUST expand beyond the skeleton where warranted by the contract_text
     so that the report is comprehensive, not minimal.

5. Style and content:
   - Be specific and practical. Avoid generic statements.
   - Where the contract is silent, state that clearly in summaries and risks,
     and explain why that is a concern.

6. Output format:
   - Return ONLY valid JSON.
   - Do NOT include markdown, backticks, explanations, or commentary.
   - Ensure the JSON is directly parseable by standard JSON parsers.
"""

    refined = _call_openai_responses(
        instructions=instructions,
        input_payload=payload,
        model=OPENAI_MODEL,
    )

    # Basic guard: ensure the main sections exist so downstream code never crashes
    for section_key in [
        "SECTION_I",
        "SECTION_II",
        "SECTION_III",
        "SECTION_IV",
        "SECTION_V",
        "SECTION_VI",
    ]:
        if section_key not in refined and section_key in cr2a_skeleton:
            refined[section_key] = cr2a_skeleton[section_key]

    return refined

def health_check() -> Dict[str, Any]:
    """
    Lightweight check to ensure OpenAI is reachable and the key is set.
    """
    status = {"openai_configured": bool(OPENAI_API_KEY)}
    if not OPENAI_API_KEY:
        status["error"] = "OPENAI_API_KEY not set"
        return status

    try:
        # extremely cheap call to verify credentials [web:2][web:20]
        _ = client.models.list()
        status["reachable"] = True
    except Exception as exc:
        status["reachable"] = False
        status["error"] = str(exc)
    return status