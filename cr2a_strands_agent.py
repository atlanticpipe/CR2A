"""
CR2A Contract Analysis Agent using Strands SDK
Integrates with existing CR2A infrastructure while providing enhanced AI capabilities
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import calculator

# Import existing CR2A components
from src.core.analyzer import analyze_to_json, AnalyzerError
from src.schemas.template_spec import CR2A_TEMPLATE_SPEC, canonical_template_items
from src.core.validator import validate_filled_template

logger = logging.getLogger(__name__)

@tool
def extract_contract_text(file_path: str, ocr_mode: str = "auto") -> Dict[str, Any]:
    """Extract and analyze contract text using CR2A's existing analyzer.
    
    Args:
        file_path: Path to contract file (PDF, DOCX, TXT)
        ocr_mode: OCR mode for PDFs ("auto", "textract", "tesseract", "none")
    
    Returns:
        Dictionary containing extracted contract sections and metadata
    """
    try:
        repo_root = Path(__file__).resolve().parents[1]  # Adjust path as needed
        result = analyze_to_json(file_path, repo_root, ocr=ocr_mode)
        return {
            "success": True,
            "data": result,
            "sections_found": list(result.keys()),
            "contract_text_length": len(result.get("_contract_text", "")),
        }
    except AnalyzerError as e:
        return {
            "success": False,
            "error": {"category": e.category, "message": str(e)},
            "data": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": {"category": "UnknownError", "message": str(e)},
            "data": None
        }

@tool
def validate_contract_analysis(analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate contract analysis against CR2A template requirements.
    
    Args:
        analysis_data: Contract analysis data from extract_contract_text
    
    Returns:
        Validation results with any issues found
    """
    try:
        validation_result = validate_filled_template(analysis_data)
        return {
            "valid": True,
            "validation_result": validation_result,
            "issues": []
        }
    except Exception as e:
        return {
            "valid": False,
            "validation_result": None,
            "issues": [str(e)]
        }

@tool
def analyze_contract_risks(contract_sections: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze contract sections for specific risk patterns and compliance issues.
    
    Args:
        contract_sections: Extracted contract sections from CR2A analyzer
    
    Returns:
        Risk analysis with categorized findings
    """
    risks = {
        "high_risk": [],
        "medium_risk": [],
        "low_risk": [],
        "compliance_issues": [],
        "recommendations": []
    }
    
    # Analyze Section V (Risk Allocation) for high-risk patterns
    section_v = contract_sections.get("SECTION_V", [])
    for item in section_v:
        clauses = item.get("clauses", [])
        for clause in clauses:
            clause_text = clause.get("clause_language", "").lower()
            
            # High-risk patterns
            if any(pattern in clause_text for pattern in [
                "unlimited liability", "consequential damages", "punitive damages"
            ]):
                risks["high_risk"].append({
                    "section": "V",
                    "item": item.get("item_title", ""),
                    "risk": "Unlimited liability exposure",
                    "clause": clause_text[:200] + "..." if len(clause_text) > 200 else clause_text
                })
            
            # Medium-risk patterns
            elif any(pattern in clause_text for pattern in [
                "indemnification", "hold harmless", "defend"
            ]):
                risks["medium_risk"].append({
                    "section": "V", 
                    "item": item.get("item_title", ""),
                    "risk": "Indemnification obligations",
                    "clause": clause_text[:200] + "..." if len(clause_text) > 200 else clause_text
                })
    
    # Analyze Section IV (Payment Terms) for compliance
    section_iv = contract_sections.get("SECTION_IV", [])
    for item in section_iv:
        clauses = item.get("clauses", [])
        for clause in clauses:
            clause_text = clause.get("clause_language", "").lower()
            
            if "net 90" in clause_text or "90 days" in clause_text:
                risks["compliance_issues"].append({
                    "section": "IV",
                    "item": item.get("item_title", ""),
                    "issue": "Extended payment terms may impact cash flow",
                    "clause": clause_text[:200] + "..." if len(clause_text) > 200 else clause_text
                })
    
    # Generate recommendations based on findings
    if risks["high_risk"]:
        risks["recommendations"].append("Review high-risk liability clauses with legal counsel")
    if risks["medium_risk"]:
        risks["recommendations"].append("Consider liability caps and insurance requirements")
    if risks["compliance_issues"]:
        risks["recommendations"].append("Negotiate more favorable payment terms")
    
    return risks

def create_cr2a_agent() -> Agent:
    """Create a specialized CR2A contract analysis agent."""
    
    # Use Amazon Nova Pro for cost-effective analysis
    model = BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        region_name="us-east-1",
        temperature=0.1,  # Low temperature for consistent legal analysis
        max_tokens=4096,
    )
    
    agent = Agent(
        model=model,
        tools=[extract_contract_text, validate_contract_analysis, analyze_contract_risks, calculator],
        system_prompt="""You are a specialized contract risk and compliance analyzer for the CR2A system.

Your expertise includes:
- Contract clause extraction and categorization
- Risk assessment and compliance validation
- Legal language analysis and interpretation
- Recommendation generation for contract improvements

When analyzing contracts:
1. Use extract_contract_text to process the contract file
2. Use validate_contract_analysis to ensure compliance with CR2A templates
3. Use analyze_contract_risks to identify specific risk patterns
4. Provide clear, actionable recommendations

Always be thorough but concise in your analysis. Focus on practical risks and compliance issues that matter for procurement and service contracts."""
    )
    
    return agent

def analyze_contract_with_strands(file_path: str, contract_id: str) -> Dict[str, Any]:
    """Complete contract analysis using Strands agent."""
    
    agent = create_cr2a_agent()
    
    try:
        # Analyze the contract
        response = agent(f"""
        Please analyze the contract at: {file_path}
        Contract ID: {contract_id}
        
        Perform a complete CR2A analysis including:
        1. Extract all contract sections and clauses
        2. Validate against CR2A template requirements  
        3. Identify risks and compliance issues
        4. Provide specific recommendations
        
        Return a comprehensive analysis report.
        """)
        
        return {
            "success": True,
            "contract_id": contract_id,
            "analysis": response,
            "agent_model": "Amazon Nova Pro via Strands"
        }
        
    except Exception as e:
        logger.error(f"Contract analysis failed: {e}")
        return {
            "success": False,
            "contract_id": contract_id,
            "error": str(e),
            "agent_model": "Amazon Nova Pro via Strands"
        }

if __name__ == "__main__":
    # Test the agent
    print("🔍 Testing CR2A Strands Agent...")
    
    # Create agent
    agent = create_cr2a_agent()
    
    # Test basic functionality
    test_response = agent("Explain how you would analyze a contract for risk and compliance issues.")
    print(f"Agent Response: {test_response}")
    
    print("\n✅ CR2A Strands Agent is ready!")
    print("Use analyze_contract_with_strands(file_path, contract_id) to analyze contracts.")