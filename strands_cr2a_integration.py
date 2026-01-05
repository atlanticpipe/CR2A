"""
Strands-Enhanced CR2A Contract Analyzer
Replaces OpenAI client with Strands multi-provider agent
"""
from strands import Agent, tool
from strands.models import BedrockModel
from typing import Dict, Any
import json

@tool
def analyze_contract_clause(clause_text: str, clause_type: str) -> Dict[str, Any]:
    """Analyze a specific contract clause for risks and compliance.
    
    Args:
        clause_text: The contract clause text to analyze
        clause_type: Type of clause (liability, payment, indemnification, etc.)
    
    Returns:
        Analysis results with risks and recommendations
    """
    # Risk patterns by clause type
    risk_patterns = {
        "liability": ["unlimited", "consequential", "punitive", "indirect"],
        "payment": ["net 90", "net 60", "upon completion"],
        "indemnification": ["hold harmless", "defend", "indemnify"],
        "termination": ["immediate", "without cause", "no notice"]
    }
    
    analysis = {
        "clause_type": clause_type,
        "risks_found": [],
        "risk_level": "LOW",
        "recommendations": []
    }
    
    # Check for risk patterns
    clause_lower = clause_text.lower()
    patterns = risk_patterns.get(clause_type, [])
    
    for pattern in patterns:
        if pattern in clause_lower:
            analysis["risks_found"].append(pattern)
    
    # Determine risk level
    if len(analysis["risks_found"]) >= 2:
        analysis["risk_level"] = "HIGH"
    elif len(analysis["risks_found"]) == 1:
        analysis["risk_level"] = "MEDIUM"
    
    # Generate recommendations
    if analysis["risks_found"]:
        analysis["recommendations"].append(f"Review {clause_type} clause for risk mitigation")
        analysis["recommendations"].append("Consider adding liability caps or limitations")
    
    return analysis

def create_strands_cr2a_agent():
    """Create enhanced CR2A agent using Strands."""
    model = BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        region_name="us-east-1",
        temperature=0.1,
        max_tokens=4096,
    )
    
    return Agent(
        model=model,
        tools=[analyze_contract_clause],
        system_prompt="""You are an expert contract risk analyzer for the CR2A system.
        
        Analyze contracts for:
        - Risk allocation and liability issues
        - Payment terms and cash flow impact
        - Indemnification and insurance requirements
        - Compliance with company policies
        - Termination and dispute resolution clauses
        
        Provide specific, actionable recommendations for risk mitigation."""
    )

# Integration with existing CR2A
def enhance_cr2a_with_strands(contract_data: Dict[str, Any]) -> Dict[str, Any]:
    """Enhance CR2A analysis using Strands agent."""
    agent = create_strands_cr2a_agent()
    
    enhanced_data = contract_data.copy()
    
    # Process each section with Strands
    for section_key in ["SECTION_II", "SECTION_III", "SECTION_IV", "SECTION_V", "SECTION_VI"]:
        if section_key in contract_data:
            items = contract_data[section_key]
            for item in items:
                clauses = item.get("clauses", [])
                for clause in clauses:
                    clause_text = clause.get("clause_language", "")
                    if clause_text and clause_text != "Not present in contract.":
                        # Use Strands agent for enhanced analysis
                        response = agent(f"Analyze this contract clause: {clause_text}")
                        clause["strands_analysis"] = response
    
    return enhanced_data
