"""
OpenAI Client for Contract Analysis

Tiny wrapper that makes exactly one API call to ChatGPT for contract analysis.
Uses official OpenAI client library and reads API key from environment variables only.
"""

import os
import json
from typing import Dict
from openai import OpenAI
from openai._exceptions import OpenAIError


def analyze_contract(contract_text: str, schema_content: str, rules_content: str) -> Dict:
    """
    Analyze contract text using OpenAI's ChatGPT API with structured JSON response.

    Args:
        contract_text: The extracted contract text to analyze
        schema_content: JSON schema string defining the expected response structure
        rules_content: Validation rules string for compliance checking

    Returns:
        Dict: Parsed JSON response from the API

    Raises:
        OpenAIError: If API key is missing or API call fails
    """
    # Read API key from environment variable only
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise OpenAIError(
            "OPENAI_API_KEY environment variable is not set.\n\n"
            "To set it:\n"
            "  Windows: setx OPENAI_API_KEY \"sk-your-key-here\"\n"
            "  Linux/Mac: export OPENAI_API_KEY=\"sk-your-key-here\"\n\n"
            "Get your API key from: https://platform.openai.com/api-keys"
        )
    
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

TEMPLATE HEADINGS (for your reference only; do not echo):
I. Contract Overview
II. Administrative & Commercial Terms
III. Technical & Performance Terms
IV. Legal Risk & Enforcement
V. Regulatory & Compliance Terms
VI. Data, Technology & Deliverables
VII. Supplemental Operational Risks
VIII. Final Analysis

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