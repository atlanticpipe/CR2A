// Prompt Builder Service - Generates section-specific prompts
// Updated: Removed Section VIII per user request

class PromptBuilder {
  constructor() {
    this.prompts = this.getDefaultPrompts();
    this.customPrompts = null;
  }

  /**
   * Load custom prompt data from external JSON
   */
  async loadPromptData(url) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        this.customPrompts = await response.json();
        console.log('Custom prompts loaded successfully');
        return true;
      }
    } catch (error) {
      console.warn('Failed to load custom prompts, using defaults:', error);
    }
    return false;
  }

  /**
   * Get default prompts for all sections (I-VII only, VIII removed)
   */
  getDefaultPrompts() {
    return {
      section_i: {
        name: "Section I - Executive Summary & Risk Overview",
        description: "High-level summary generated after all analysis sections complete",
        instructions: "This section is generated automatically from the results of Sections II-VII. No separate analysis required.",
        items: [],
        output_format: "Auto-generated summary"
      },
      section_ii: {
        name: "Section II - Administrative & Commercial Requirements",
        description: "Comprehensive analysis of administrative and commercial contract terms",
        instructions: `Analyze each item below. For each, determine:
- Status: Present/Missing/Unclear
- Risk Level: High/Medium/Low
- Details: Quote relevant text or note absence
- Recommendations: Specific actions needed

Return results as JSON array with these exact keys: item_name, status, risk_level, details, recommendations`,
        items: [
          { name: "Contract Type", description: "Identify contract type and payment structure" },
          { name: "Payment Terms", description: "Review payment schedule, retention, and conditions" },
          { name: "Invoicing Requirements", description: "Check invoicing procedures and documentation" },
          { name: "Change Order Process", description: "Evaluate change order procedures and approval requirements" },
          { name: "Dispute Resolution", description: "Review dispute resolution mechanisms and procedures" },
          { name: "Termination Clauses", description: "Analyze termination rights, procedures, and consequences" },
          { name: "Notice Requirements", description: "Identify notice periods and delivery methods" },
          { name: "Subcontracting Terms", description: "Review subcontractor approval and liability terms" },
          { name: "Material Procurement", description: "Check material sourcing and approval requirements" },
          { name: "Schedule Requirements", description: "Analyze project timeline and milestone requirements" },
          { name: "Liquidated Damages", description: "Identify delay penalties and damage provisions" },
          { name: "Force Majeure", description: "Review excusable delay and force majeure provisions" },
          { name: "Warranty Terms", description: "Check warranty periods and requirements" },
          { name: "Acceptance Criteria", description: "Review completion and acceptance procedures" },
          { name: "Records and Reporting", description: "Identify documentation and reporting requirements" },
          { name: "Administrative Controls", description: "Check project management and coordination requirements" }
        ],
        output_format: "JSON array"
      },
      section_iii: {
        name: "Section III - Technical & Performance Requirements",
        description: "Analysis of technical specifications and performance standards",
        instructions: `For each technical requirement, assess:
- Status: Present/Missing/Unclear
- Risk Level: High/Medium/Low
- Details: Specific requirements or gaps
- Recommendations: Technical compliance actions

Return as JSON array with keys: item_name, status, risk_level, details, recommendations`,
        items: [
          { name: "Technical Specifications", description: "Review detailed technical requirements and standards" },
          { name: "Quality Standards", description: "Identify quality control and assurance requirements" },
          { name: "Testing Requirements", description: "Check testing, inspection, and certification needs" },
          { name: "Performance Metrics", description: "Analyze performance standards and measurement criteria" },
          { name: "Materials Standards", description: "Review material specifications and approval processes" },
          { name: "Workmanship Standards", description: "Check craftsmanship and execution requirements" },
          { name: "Equipment Requirements", description: "Identify equipment specifications and qualifications" },
          { name: "Safety Requirements", description: "Review safety standards and compliance needs" },
          { name: "Environmental Standards", description: "Check environmental compliance and protection requirements" },
          { name: "As-Built Documentation", description: "Review documentation and drawing requirements" },
          { name: "Submittals", description: "Identify submittal requirements and approval processes" },
          { name: "Shop Drawings", description: "Check shop drawing requirements and procedures" },
          { name: "Product Data", description: "Review product data submission requirements" },
          { name: "Samples", description: "Identify sample submission and approval requirements" },
          { name: "Coordination Requirements", description: "Check technical coordination needs" },
          { name: "Interface Requirements", description: "Review integration with existing systems" },
          { name: "Closeout Requirements", description: "Check project closeout and final documentation" }
        ],
        output_format: "JSON array"
      },
      section_iv: {
        name: "Section IV - Legal Risk & Enforcement",
        description: "Assessment of legal risks and enforcement mechanisms",
        instructions: `Evaluate legal risks with:
- Status: Present/Missing/Unclear
- Risk Level: High/Medium/Low
- Details: Legal implications and requirements
- Recommendations: Legal compliance actions

Return as JSON array with keys: item_name, status, risk_level, details, recommendations`,
        items: [
          { name: "Indemnification", description: "Review indemnification obligations and scope" },
          { name: "Liability Limits", description: "Check liability caps and exclusions" },
          { name: "Insurance Requirements", description: "Analyze insurance types, limits, and additional insured" },
          { name: "Bonds", description: "Review performance and payment bond requirements" },
          { name: "Applicable Law", description: "Identify governing law and jurisdiction" },
          { name: "Intellectual Property", description: "Check IP ownership and licensing terms" },
          { name: "Confidentiality", description: "Review confidentiality and NDA requirements" },
          { name: "Remedies", description: "Analyze available remedies for breach" },
          { name: "Limitation of Actions", description: "Check statute of limitations provisions" },
          { name: "Assignment Rights", description: "Review assignment and delegation restrictions" },
          { name: "Third-Party Rights", description: "Check third-party beneficiary provisions" },
          { name: "Waivers", description: "Identify waiver of rights provisions" },
          { name: "Severability", description: "Check contract severability terms" }
        ],
        output_format: "JSON array"
      },
      section_v: {
        name: "Section V - Regulatory & Compliance Requirements",
        description: "Review of regulatory compliance obligations",
        instructions: `Assess regulatory compliance with:
- Status: Present/Missing/Unclear
- Risk Level: High/Medium/Low
- Details: Specific regulatory requirements
- Recommendations: Compliance actions needed

Return as JSON array with keys: item_name, status, risk_level, details, recommendations`,
        items: [
          { name: "Permits and Licenses", description: "Identify required permits and licensing" },
          { name: "Prevailing Wage", description: "Check Davis-Bacon or prevailing wage requirements" },
          { name: "DBE/MBE/WBE", description: "Review diversity and small business requirements" },
          { name: "Labor Compliance", description: "Check labor law and employment requirements" },
          { name: "Environmental Permits", description: "Identify environmental regulatory requirements" },
          { name: "OSHA Compliance", description: "Review workplace safety and OSHA requirements" },
          { name: "Federal/State Requirements", description: "Check government-specific compliance needs" },
          { name: "Buy America", description: "Review Buy America or domestic preference requirements" }
        ],
        output_format: "JSON array"
      },
      section_vi: {
        name: "Section VI - Data Security & Technology Requirements",
        description: "Assessment of data, cybersecurity, and technology obligations",
        instructions: `Evaluate technology requirements with:
- Status: Present/Missing/Unclear
- Risk Level: High/Medium/Low
- Details: Specific technology requirements
- Recommendations: Technology compliance actions

Return as JSON array with keys: item_name, status, risk_level, details, recommendations`,
        items: [
          { name: "Data Protection", description: "Review data handling and protection requirements" },
          { name: "Cybersecurity", description: "Check cybersecurity standards and requirements" },
          { name: "System Access", description: "Identify system access and security requirements" },
          { name: "Software/Technology Use", description: "Review technology and software requirements" },
          { name: "Data Retention", description: "Check data retention and destruction requirements" },
          { name: "Privacy Compliance", description: "Review privacy law compliance requirements" },
          { name: "Electronic Records", description: "Check electronic record keeping requirements" }
        ],
        output_format: "JSON array"
      },
      section_vii: {
        name: "Section VII - Supplemental Risk Areas",
        description: "Additional risks and special considerations",
        instructions: `Identify supplemental risks with:
- Status: Present/Missing/Unclear
- Risk Level: High/Medium/Low
- Details: Specific risk factors
- Recommendations: Risk mitigation actions

Return as JSON array with keys: item_name, status, risk_level, details, recommendations`,
        items: [
          { name: "Unfamiliar Clauses", description: "Identify unusual or unfamiliar contract terms" },
          { name: "Ambiguous Language", description: "Flag vague or unclear contract language" },
          { name: "Conflicting Terms", description: "Identify contradictory provisions" },
          { name: "Unrealistic Requirements", description: "Flag potentially unachievable terms" },
          { name: "Hidden Costs", description: "Identify potential cost exposure not clearly stated" }
        ],
        output_format: "JSON array"
      }
    };
  }

  /**
   * Build prompt for a specific section
   */
  buildSectionPrompt(sectionKey, contractText, metadata = {}) {
    const prompts = this.customPrompts || this.prompts;
    const section = prompts[sectionKey];

    if (!section) {
      throw new Error(`Unknown section: ${sectionKey}`);
    }

    // Section I is auto-generated, no prompt needed
    if (sectionKey === 'section_i') {
      return null;
    }

    let prompt = `You are analyzing a contract for risk and compliance.

CONTRACT METADATA:
- Contract ID: ${metadata.contract_id || 'Unknown'}
- Project: ${metadata.project_title || 'Unknown'}
- Owner: ${metadata.owner || 'Unknown'}

ANALYSIS SECTION: ${section.name}
${section.description}

INSTRUCTIONS:
${section.instructions}

`;

    if (section.items && section.items.length > 0) {
      prompt += `ITEMS TO ANALYZE:
`;
      section.items.forEach((item, idx) => {
        prompt += `${idx + 1}. ${item.name}: ${item.description}
`;
      });
      prompt += `
`;
    }

    prompt += `CONTRACT TEXT:
${contractText}

`;
    prompt += `OUTPUT FORMAT: ${section.output_format}
`;
    prompt += `Provide your analysis now:`;

    return prompt;
  }

  /**
   * Get all section keys (excluding Section I and Section VIII)
   */
  getAllSectionKeys() {
    return ['section_ii', 'section_iii', 'section_iv', 'section_v', 'section_vi', 'section_vii'];
  }

  /**
   * Get section name for display
   */
  getSectionName(sectionKey) {
    const prompts = this.customPrompts || this.prompts;
    return prompts[sectionKey]?.name || sectionKey;
  }

  /**
   * Build executive summary prompt (Section I) from completed analysis
   */
  buildExecutiveSummary(analysisResults, metadata = {}) {
    let prompt = `Create an executive summary for this contract risk analysis.

CONTRACT METADATA:
- Contract ID: ${metadata.contract_id || 'Unknown'}
- Project: ${metadata.project_title || 'Unknown'}
- Owner: ${metadata.owner || 'Unknown'}
- Analysis Date: ${metadata.analysis_date || new Date().toISOString()}

COMPLETED ANALYSIS SECTIONS:
`;

    // Add each section's findings
    const sectionKeys = this.getAllSectionKeys();
    sectionKeys.forEach(key => {
      if (analysisResults[key]) {
        prompt += `
${this.getSectionName(key)}:
`;
        const findings = analysisResults[key].findings || [];
        const highRisk = findings.filter(f => f.risk_level === 'High').length;
        const medRisk = findings.filter(f => f.risk_level === 'Medium').length;
        const lowRisk = findings.filter(f => f.risk_level === 'Low').length;
        prompt += `- High Risk: ${highRisk}, Medium Risk: ${medRisk}, Low Risk: ${lowRisk}
`;
      }
    });

    prompt += `
RISK SUMMARY:
- Overall Risk: ${analysisResults.risk_summary?.overallRisk || 'Unknown'}
- Total High Risk Items: ${analysisResults.risk_summary?.distribution?.High || 0}
- Total Medium Risk Items: ${analysisResults.risk_summary?.distribution?.Medium || 0}
- Total Low Risk Items: ${analysisResults.risk_summary?.distribution?.Low || 0}

Create a concise executive summary (200-300 words) that includes:
1. Overall risk assessment
2. Top 3-5 critical findings
3. Key recommendations
4. Summary of compliance requirements

Format as JSON with keys: overall_assessment, critical_findings (array), key_recommendations (array), compliance_summary`;

    return prompt;
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = PromptBuilder;
}
