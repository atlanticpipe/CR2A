import os
import sys
import json
from typing import Dict
from pathlib import Path
from openai import OpenAI
from openai._exceptions import OpenAIError


def get_api_key() -> str:
    """
    Get OpenAI API key from environment variable or config file.
    
    Priority:
    1. OPENAI_API_KEY environment variable
    2. config.txt file next to the executable
    3. Raise error if neither is found
    
    Returns:
        str: The API key
        
    Raises:
        OpenAIError: If no API key is found
    """
    # First, try environment variable
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key.strip()
    
    # Second, try config.txt file next to the executable
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        exe_dir = os.path.dirname(sys.executable)
    else:
        # Running as script
        exe_dir = os.path.dirname(os.path.abspath(__file__))
    
    config_file = os.path.join(exe_dir, 'config.txt')
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                # Read first non-empty line as API key
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        return line
        except Exception as e:
            raise OpenAIError(f"Error reading config.txt: {str(e)}")
    
    # No API key found
    raise OpenAIError(
        "OpenAI API key not found.\n\n"
        "Option 1: Set environment variable\n"
        "  Windows PowerShell:\n"
        "    [System.Environment]::SetEnvironmentVariable(\"OPENAI_API_KEY\", \"sk-your-key\", \"User\")\n"
        "  Windows CMD:\n"
        "    setx OPENAI_API_KEY \"sk-your-key\"\n\n"
        "Option 2: Create config.txt file\n"
        f"  Create a file named 'config.txt' in: {exe_dir}\n"
        "  Put your API key on the first line: sk-your-key-here\n\n"
        "Get your API key from: https://platform.openai.com/api-keys"
    )


def analyze_contract(contract_text: str, schema_content: str, rules_content: str) -> Dict:
    # Get API key from environment variable or config file
    api_key = get_api_key()
    
    # Validate API key format
    if not api_key.startswith('sk-'):
        raise OpenAIError(
            "Invalid OpenAI API key format. API keys should start with 'sk-'\n\n"
            "Please check your OPENAI_API_KEY environment variable."
        )

    # Initialize OpenAI client with API key
    try:
        client = OpenAI(api_key=api_key)
    except Exception as e:
        raise OpenAIError(f"Failed to initialize OpenAI client: {str(e)}")

    # Define system message for contract analysis
    system_message = """You are a Contract Analysis Engine. Output only a single JSON object that conforms exactly to the provided JSON Schema (2020-12). Do not include explanations or extra keys. If a required data point is not present in the contract, use "" for strings or [] for arrays. For each ClauseBlock, include at least one Redline Recommendations item with an action of insert, replace, or delete."""

    # Format user message with schema, rules, and contract text
    user_message = f"""SCHEMA (do not echo): <<<JSON_SCHEMA_START
{schema_content}
JSON_SCHEMA_END>>>

COMPANY RULES (do not echo; you must comply): <<<RULES_START
{rules_content}
RULES_END>>>

CRITICAL INSTRUCTIONS - YOU MUST FOLLOW THESE EXACTLY:

1. Use ONLY the predefined subsection names listed below - DO NOT create custom names
2. Only include subsections that:
   - Appear in the contract AND
   - Have at least moderate risk (Risk Triggers, Harmful Language, or Redline Recommendations)
3. If a subsection doesn't appear in the contract or has no moderate risk, OMIT it entirely
4. Use the exact subsection names as keys in the JSON - do not modify them

SECTION I - CONTRACT OVERVIEW (always include all 8 fields):
- Project Title
- Solicitation No.
- Owner
- Contractor
- Scope
- General Risk Level
- Bid Model
- Notes

SECTION II - ADMINISTRATIVE & COMMERCIAL TERMS (use these exact names as keys):
- Contract Term, Renewal & Extensions
- Bonding, Surety, & Insurance Obligations
- Retainage, Progress Payments & Final Payment Terms
- Pay-When-Paid, Pay-If-Paid, or Owner Payment Contingencies
- Price Escalation Clauses (Labor, Materials, Fuel, Inflation Adjustments)
- Fuel Price Adjustment / Fuel Cost Caps
- Change Orders, Scope Adjustments & Modifications
- Termination for Convenience (Owner/Agency Right to Terminate Without Cause)
- Termination for Cause / Default by Contractor
- Bid Protest Procedures & Claims of Improper Award
- Bid Tabulation, Competition & Award Process Requirements
- Contractor Qualification, Licensing & Certification Requirements
- Release Orders, Task Orders & Work Authorization Protocols
- Assignment & Novation Restrictions (Transfer of Contract Rights)
- Audit Rights, Recordkeeping & Document Retention Obligations
- Notice Requirements & Claim Timeframes (Notice to Cure, Delay Notices, Termination Notices, etc.)

SECTION III - TECHNICAL & PERFORMANCE TERMS (use these exact names as keys):
- Scope of Work (Work Inclusions, Exclusions & Defined Deliverables)
- Performance Schedule, Time for Completion & Critical Path Obligations
- Delays of Any Kind (Force Majeure, Acts of God, Weather, Owner-Caused, Unforeseen Events)
- Suspension of Work, Work Stoppages & Agency Directives
- Submittals, Documentation & Approval Requirements
- Emergency & Contingency Work Obligations
- Permits, Licensing & Regulatory Approvals for Work
- Warranty, Guarantee & Defects Liability Periods
- Use of APS Tools, Equipment, Materials or Supplies
- Owner-Supplied Support, Utilities & Site Access Provisions
- Field Ticket, Daily Work Log & Documentation Requirements
- Mobilization & Demobilization Provisions
- Utility Coordination, Locate Risk & Conflict Avoidance
- Delivery Deadlines, Milestone Dates, Substantial & Final Completion Standards
- Punch List, Closeout Procedures & Acceptance of Work
- Worksite Coordination, Access Restrictions & Sequencing Obligations
- Deliverables, Digital Submissions & Documentation Standards

SECTION IV - LEGAL RISK & ENFORCEMENT (use these exact names as keys):
- Indemnification, Defense & Hold Harmless Provisions
- Duty to Defend vs. Indemnify Scope Clarifications
- Limitations of Liability, Damage Caps & Waivers of Consequential Damages
- Insurance Coverage, Additional Insured & Waiver of Subrogation Clauses
- Dispute Resolution (Mediation, Arbitration, Litigation)
- Flow-Down Clauses (Prime-to-Subcontract Risk Pass-Through)
- Subcontracting Restrictions, Approval & Substitution Requirements
- Background Screening, Security Clearance & Worker Eligibility Requirements
- Safety Standards, OSHA Compliance & Site-Specific Safety Obligations
- Site Conditions, Differing Site Conditions & Changed Circumstances Clauses
- Environmental Hazards, Waste Disposal & Hazardous Materials Provisions
- Conflicting Documents / Order of Precedence Clauses
- Setoff & Withholding Rights (Owner's Right to Deduct or Withhold Payment)

SECTION V - REGULATORY & COMPLIANCE TERMS (use these exact names as keys):
- Certified Payroll, Recordkeeping & Reporting Obligations
- Prevailing Wage, Davis-Bacon & Federal/State Wage Compliance
- EEO, Non-Discrimination, MWBE/DBE Participation Requirements
- Anti-Lobbying / Cone of Silence Provisions
- Apprenticeship, Training & Workforce Development Requirements
- Immigration / E-Verify Compliance Obligations
- Worker Classification & Independent Contractor Restrictions
- Drug-Free Workplace Programs & Substance Testing Requirements

SECTION VI - DATA, TECHNOLOGY & DELIVERABLES (use these exact names as keys):
- Data Ownership, Access & Rights to Digital Deliverables
- AI / Technology Use Restrictions (Automation, Digital Tools, Proprietary Systems)
- Digital Surveillance, GIS-Tagged Deliverables & Monitoring Requirements
- GIS, Digital Workflow Integration & Electronic Submittals
- Confidentiality, Data Security & Records Retention Obligations
- Intellectual Property, Licensing & Ownership of Work Product
- Cybersecurity Standards, Breach Notification & IT System Use Policies

SECTION VII - SUPPLEMENTAL OPERATIONAL RISKS:
- Use this section for any significant risks that don't fit in sections II-VI
- Each risk should be a separate object in the array

CONTRACT TEXT:
<<<CONTRACT_START
{contract_text}
CONTRACT_END>>>

Produce ONLY the JSON object that conforms to the schema above. No comments, no markdown, no prose."""

    try:
        # Make API call with JSON schema response formatting
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Use cost-effective model
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.0,  # Deterministic output for consistent analysis
            max_tokens=4000,  # Sufficient for detailed contract analysis
            response_format={"type": "json_object"}  # Request JSON response
        )

        # Extract and parse JSON response
        response_text = response.choices[0].message.content
        if not response_text:
            raise OpenAIError("Empty response from OpenAI API")

        # Parse JSON response
        result = json.loads(response_text)
        return result

    except json.JSONDecodeError as e:
        # Handle non-JSON response from API
        raise OpenAIError(f"Invalid JSON response from API: {e}")
    except OpenAIError as e:
        # Re-raise OpenAI errors with clear message
        raise
    except Exception as e:
        # Handle unexpected errors
        error_msg = str(e)
        if "authentication" in error_msg.lower() or "api key" in error_msg.lower():
            raise OpenAIError(
                f"Authentication failed: {error_msg}\n\n"
                "Please verify your API key is correct and has not expired."
            )
        elif "rate limit" in error_msg.lower():
            raise OpenAIError(
                f"Rate limit exceeded: {error_msg}\n\n"
                "Please wait a moment and try again."
            )
        elif "insufficient" in error_msg.lower() or "quota" in error_msg.lower():
            raise OpenAIError(
                f"Insufficient credits: {error_msg}\n\n"
                "Please check your OpenAI account balance."
            )
        else:
            raise OpenAIError(f"Unexpected error during API call: {str(e)}")