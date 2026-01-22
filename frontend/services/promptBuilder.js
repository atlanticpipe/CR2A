// Prompt Builder - Constructs section-specific prompts
// Uses CR2A template instructions for each analysis section

class PromptBuilder {
  constructor() {
    this.promptData = null;
  }

  /**
   * Load prompt data from external JSON file
   */
  async loadPromptData(url = './data/promptScript.json') {
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to load prompt data: ${response.statusText}`);
      }
      this.promptData = await response.json();
      return true;
    } catch (error) {
      console.error('Failed to load prompt data:', error);
      // Fallback to embedded prompts
      this.promptData = this.getDefaultPrompts();
      return false;
    }
  }

  /**
   * Get prompt for a specific section
   * @param {string} sectionId - Section identifier (e.g., 'section_ii')
   * @returns {string} Formatted prompt for OpenAI
   */
  getSectionPrompt(sectionId) {
    if (!this.promptData) {
      this.promptData = this.getDefaultPrompts();
    }

    const section = this.promptData[sectionId];
    if (!section) {
      throw new Error(`No prompt found for section: ${sectionId}`);
    }

    return this.formatPrompt(section);
  }

  /**
   * Format prompt with instructions and structure
   */
  formatPrompt(section) {
    let prompt = `# ${section.name}\n\n`;

    if (section.description) {
      prompt += `${section.description}\n\n`;
    }

    prompt += `## Instructions:\n`;
    prompt += `${section.instructions}\n\n`;

    if (section.items && section.items.length > 0) {
      prompt += `## Items to Analyze:\n\n`;
      section.items.forEach((item, index) => {
        prompt += `${index + 1}. **${item.name}**\n`;
        if (item.description) {
          prompt += `   ${item.description}\n`;
        }
        prompt += `\n`;
      });
    }

    if (section.output_format) {
      prompt += `## Required Output Format:\n`;
      prompt += `${section.output_format}\n\n`;
    }

    return prompt;
  }

  /**
   * Default prompts if external file not loaded
   */
  getDefaultPrompts() {
    return {
      section_ii: {
        name: 'Section II - Administrative & Commercial Requirements',
        description: 'Analyze administrative and commercial aspects of the contract.',
        instructions: 'Review the contract for the following administrative and commercial requirements. For each item, identify if it is present, missing, or unclear. Note any risks or concerns.',
        items: [
          { name: 'Contract Type', description: 'Identify the contract type (FFP, T&M, Cost-Plus, etc.)' },
          { name: 'Payment Terms', description: 'Review payment schedule, milestones, and conditions' },
          { name: 'Invoicing Requirements', description: 'Check invoicing procedures and documentation' },
          { name: 'Progress Reporting', description: 'Identify reporting frequency and requirements' },
          { name: 'Key Personnel', description: 'Review key personnel requirements and approval process' },
          { name: 'Subcontracting', description: 'Check subcontracting permissions and requirements' },
          { name: 'Change Orders', description: 'Review change order process and approval authority' },
          { name: 'Price Escalation', description: 'Check for price adjustment clauses' },
          { name: 'Retainage', description: 'Identify any retainage provisions' },
          { name: 'Bonds/Insurance', description: 'Review bonding and insurance requirements' },
          { name: 'Liquidated Damages', description: 'Check for delay penalties' },
          { name: 'Warranty Period', description: 'Identify warranty terms and duration' },
          { name: 'Closeout Requirements', description: 'Review contract closeout procedures' },
          { name: 'Records Retention', description: 'Check document retention requirements' },
          { name: 'Audit Rights', description: 'Review audit and inspection provisions' },
          { name: 'Dispute Resolution', description: 'Identify dispute resolution mechanisms' }
        ],
        output_format: 'For each item, provide: Status (Present/Missing/Unclear), Details, Risk Level (High/Medium/Low), and Recommendations.'
      },
      section_iii: {
        name: 'Section III - Technical & Performance Requirements',
        description: 'Analyze technical specifications and performance requirements.',
        instructions: 'Evaluate technical and performance aspects. Identify any unclear specifications or unrealistic requirements.',
        items: [
          { name: 'Scope of Work', description: 'Review completeness of work scope' },
          { name: 'Technical Specifications', description: 'Check clarity of technical requirements' },
          { name: 'Performance Standards', description: 'Review acceptance criteria' },
          { name: 'Materials & Equipment', description: 'Check material specifications' },
          { name: 'Testing Requirements', description: 'Review testing and QA/QC procedures' },
          { name: 'Delivery Schedule', description: 'Evaluate timeline feasibility' },
          { name: 'Site Conditions', description: 'Check site access and conditions' },
          { name: 'Safety Requirements', description: 'Review safety standards' },
          { name: 'Environmental Compliance', description: 'Check environmental requirements' },
          { name: 'Quality Assurance', description: 'Review QA/QC program requirements' },
          { name: 'Submittals', description: 'Check submittal requirements and schedule' },
          { name: 'Standards & Codes', description: 'Identify applicable codes and standards' },
          { name: 'Coordination Requirements', description: 'Review coordination with other parties' },
          { name: 'As-Built Documentation', description: 'Check documentation requirements' },
          { name: 'Training Requirements', description: 'Review training obligations' },
          { name: 'Commissioning', description: 'Check commissioning requirements' },
          { name: 'Performance Guarantees', description: 'Review any performance guarantees' }
        ],
        output_format: 'For each item, provide: Status, Technical Risk Assessment, Feasibility Analysis, and Recommendations.'
      },
      section_iv: {
        name: 'Section IV - Legal Risk & Enforcement',
        description: 'Analyze legal terms, liabilities, and enforcement provisions.',
        instructions: 'Review legal terms for unfavorable provisions, unclear terms, and enforcement risks.',
        items: [
          { name: 'Indemnification', description: 'Review indemnity obligations' },
          { name: 'Limitation of Liability', description: 'Check liability caps and exclusions' },
          { name: 'Force Majeure', description: 'Review force majeure provisions' },
          { name: 'Termination Clauses', description: 'Check termination rights and obligations' },
          { name: 'Default Provisions', description: 'Review default and cure provisions' },
          { name: 'Intellectual Property', description: 'Check IP ownership and licensing' },
          { name: 'Confidentiality', description: 'Review confidentiality obligations' },
          { name: 'Governing Law', description: 'Identify applicable law and jurisdiction' },
          { name: 'Assignment Rights', description: 'Check assignment and delegation provisions' },
          { name: 'Third-Party Rights', description: 'Review third-party beneficiary provisions' },
          { name: 'Waiver of Rights', description: 'Check for rights waivers' },
          { name: 'Severability', description: 'Review severability clause' },
          { name: 'Notice Requirements', description: 'Check notice procedures' }
        ],
        output_format: 'For each item, provide: Status, Legal Risk Level, Potential Impact, and Mitigation Strategies.'
      },
      section_v: {
        name: 'Section V - Regulatory & Compliance Requirements',
        description: 'Analyze regulatory compliance and statutory requirements.',
        instructions: 'Identify all regulatory and compliance obligations. Flag any high-risk or unclear requirements.',
        items: [
          { name: 'Federal Regulations', description: 'Check FAR/DFAR compliance if applicable' },
          { name: 'State/Local Requirements', description: 'Review state and local regulations' },
          { name: 'Licensing Requirements', description: 'Check required licenses and certifications' },
          { name: 'Labor Compliance', description: 'Review wage and labor requirements (Davis-Bacon, etc.)' },
          { name: 'Minority/Small Business', description: 'Check DBE/MBE/WBE requirements' },
          { name: 'Environmental Permits', description: 'Review environmental compliance' },
          { name: 'Equal Opportunity', description: 'Check EEO requirements' },
          { name: 'Buy American', description: 'Review domestic preference requirements' }
        ],
        output_format: 'For each item, provide: Status, Compliance Risk, Required Actions, and Documentation Needs.'
      },
      section_vi: {
        name: 'Section VI - Data, Technology & Deliverables',
        description: 'Analyze data handling, technology requirements, and deliverables.',
        instructions: 'Review data management, technology requirements, and deliverable specifications.',
        items: [
          { name: 'Data Ownership', description: 'Check data ownership and usage rights' },
          { name: 'Data Security', description: 'Review cybersecurity requirements' },
          { name: 'Data Privacy', description: 'Check privacy compliance (GDPR, CCPA, etc.)' },
          { name: 'Technology Requirements', description: 'Review software/hardware requirements' },
          { name: 'System Integration', description: 'Check integration requirements' },
          { name: 'Deliverables Schedule', description: 'Review deliverable timing and format' },
          { name: 'Acceptance Criteria', description: 'Check deliverable acceptance procedures' }
        ],
        output_format: 'For each item, provide: Status, Technical Feasibility, Resource Requirements, and Risks.'
      },
      section_vii: {
        name: 'Section VII - Supplemental Risk Assessment',
        description: 'Additional risk factors not covered in previous sections.',
        instructions: 'Identify any additional risks, unusual provisions, or concerns not covered in previous sections.',
        items: [
          { name: 'Market Conditions', description: 'Consider current market factors' },
          { name: 'Resource Availability', description: 'Assess availability of required resources' },
          { name: 'Schedule Risks', description: 'Evaluate timeline feasibility' },
          { name: 'Financial Risks', description: 'Assess financial exposure' },
          { name: 'Reputation Risks', description: 'Consider reputation impact' }
        ],
        output_format: 'For each risk, provide: Description, Likelihood, Impact, and Mitigation Strategy.'
      },
      section_viii: {
        name: 'Section VIII - Final Analysis & Recommendations',
        description: 'Comprehensive analysis summary and strategic recommendations.',
        instructions: 'Synthesize all findings into actionable recommendations. Provide go/no-go assessment.',
        items: [
          { name: 'Overall Risk Assessment', description: 'Comprehensive risk evaluation' },
          { name: 'Key Concerns', description: 'Top 3-5 most critical issues' },
          { name: 'Mitigation Strategies', description: 'Recommended risk mitigation approaches' },
          { name: 'Bid/No-Bid Recommendation', description: 'Strategic recommendation with justification' }
        ],
        output_format: 'Provide: Executive Summary, Critical Issues, Risk Matrix, Strategic Recommendations, and Final Recommendation (Bid/No-Bid with rationale).'
      }
    };
  }

  /**
   * Get all section IDs
   */
  getSectionIds() {
    const data = this.promptData || this.getDefaultPrompts();
    return Object.keys(data);
  }

  /**
   * Get section metadata
   */
  getSectionMetadata(sectionId) {
    const data = this.promptData || this.getDefaultPrompts();
    const section = data[sectionId];

    if (!section) return null;

    return {
      id: sectionId,
      name: section.name,
      itemCount: section.items ? section.items.length : 0,
      hasDescription: !!section.description
    };
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = PromptBuilder;
}
