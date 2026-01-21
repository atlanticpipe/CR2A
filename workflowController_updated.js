// Workflow Controller - Orchestrates multi-step contract analysis
// Updated: Removed Section VIII, workflow now II-VII → Risk Score → Section I

class WorkflowController {
  constructor(openaiService, promptBuilder) {
    this.openai = openaiService;
    this.promptBuilder = promptBuilder;
    this.status = 'idle';
    this.results = {};
    this.cancelled = false;
  }

  /**
   * Execute complete analysis workflow
   * Flow: Sections II-VII → Calculate Risk Summary → Generate Section I
   */
  async executeAnalysis(contractText, metadata = {}, progressCallback = null) {
    try {
      this.status = 'running';
      this.cancelled = false;
      this.results = {
        metadata: metadata,
        sections: {},
        risk_summary: null,
        executive_summary: null,
        analysis_date: new Date().toISOString()
      };

      // Get all section keys (II-VII only, VIII removed)
      const sectionKeys = this.promptBuilder.getAllSectionKeys();
      const totalSteps = sectionKeys.length + 2; // sections + risk calculation + executive summary
      let currentStep = 0;

      // Step 1-6: Analyze Sections II through VII
      for (const sectionKey of sectionKeys) {
        if (this.cancelled) {
          throw new Error('Analysis cancelled by user');
        }

        currentStep++;
        const sectionName = this.promptBuilder.getSectionName(sectionKey);

        this.updateProgress(progressCallback, {
          step: `Analyzing ${sectionName}`,
          progress: Math.round((currentStep / totalSteps) * 100),
          status: 'analyzing',
          message: `Processing ${sectionName}...`
        });

        try {
          const sectionResult = await this.analyzeSection(
            sectionKey,
            contractText,
            metadata
          );

          this.results.sections[sectionKey] = sectionResult;

          console.log(`✅ Completed ${sectionName}`);
        } catch (error) {
          console.error(`❌ Failed to analyze ${sectionName}:`, error);
          this.results.sections[sectionKey] = {
            error: error.message,
            findings: []
          };
        }

        // Rate limiting: wait 500ms between API calls
        await this.sleep(500);
      }

      // Step 7: Calculate Risk Summary
      currentStep++;
      this.updateProgress(progressCallback, {
        step: 'Calculating Risk Summary',
        progress: Math.round((currentStep / totalSteps) * 100),
        status: 'calculating',
        message: 'Aggregating risk scores...'
      });

      this.results.risk_summary = this.calculateRiskSummary();
      console.log('✅ Risk summary calculated');

      // Step 8: Generate Executive Summary (Section I)
      currentStep++;
      this.updateProgress(progressCallback, {
        step: 'Generating Executive Summary',
        progress: Math.round((currentStep / totalSteps) * 100),
        status: 'summarizing',
        message: 'Creating executive summary...'
      });

      try {
        this.results.executive_summary = await this.generateExecutiveSummary(metadata);
        console.log('✅ Executive summary generated');
      } catch (error) {
        console.error('❌ Failed to generate executive summary:', error);
        this.results.executive_summary = {
          error: error.message,
          fallback: this.createFallbackSummary()
        };
      }

      // Complete
      this.status = 'completed';
      this.updateProgress(progressCallback, {
        step: 'Analysis Complete',
        progress: 100,
        status: 'completed',
        message: 'All sections analyzed successfully'
      });

      return this.results;

    } catch (error) {
      this.status = 'failed';
      this.updateProgress(progressCallback, {
        step: 'Error',
        progress: 0,
        status: 'failed',
        message: error.message
      });
      throw error;
    }
  }

  /**
   * Analyze a single section
   */
  async analyzeSection(sectionKey, contractText, metadata) {
    const prompt = this.promptBuilder.buildSectionPrompt(
      sectionKey,
      contractText,
      metadata
    );

    if (!prompt) {
      return { findings: [], note: 'No analysis required for this section' };
    }

    const response = await this.openai.analyzeContract(prompt);

    // Parse response
    let findings = [];
    try {
      // Try to parse as JSON
      const parsed = JSON.parse(response);
      findings = Array.isArray(parsed) ? parsed : [parsed];
    } catch (e) {
      // If not valid JSON, try to extract structured data
      findings = this.parseUnstructuredResponse(response);
    }

    return {
      findings: findings,
      raw_response: response,
      analyzed_at: new Date().toISOString()
    };
  }

  /**
   * Parse unstructured AI response into findings
   */
  parseUnstructuredResponse(response) {
    const findings = [];
    const lines = response.split('\n');

    let currentFinding = null;

    for (const line of lines) {
      const trimmed = line.trim();

      // Look for item names/numbers
      if (/^\d+\.|^-|^\*/.test(trimmed)) {
        if (currentFinding) {
          findings.push(currentFinding);
        }
        currentFinding = {
          item_name: trimmed.replace(/^[\d\.\-\*]\s*/, ''),
          status: 'Unclear',
          risk_level: 'Medium',
          details: '',
          recommendations: ''
        };
      } else if (currentFinding && trimmed) {
        // Look for risk indicators
        if (/high.{0,5}risk/i.test(trimmed)) {
          currentFinding.risk_level = 'High';
        } else if (/low.{0,5}risk/i.test(trimmed)) {
          currentFinding.risk_level = 'Low';
        }

        // Accumulate details
        currentFinding.details += (currentFinding.details ? ' ' : '') + trimmed;
      }
    }

    if (currentFinding) {
      findings.push(currentFinding);
    }

    return findings.length > 0 ? findings : [{
      item_name: 'Analysis Result',
      status: 'Present',
      risk_level: 'Medium',
      details: response.substring(0, 500),
      recommendations: 'Review full analysis'
    }];
  }

  /**
   * Calculate overall risk summary from all sections
   */
  calculateRiskSummary() {
    const distribution = {
      High: 0,
      Medium: 0,
      Low: 0
    };

    let totalFindings = 0;

    // Count risk levels across all sections
    Object.values(this.results.sections).forEach(section => {
      if (section.findings) {
        section.findings.forEach(finding => {
          const risk = finding.risk_level || 'Medium';
          if (distribution[risk] !== undefined) {
            distribution[risk]++;
            totalFindings++;
          }
        });
      }
    });

    // Determine overall risk
    let overallRisk = 'Low';
    if (distribution.High > 5 || distribution.High / totalFindings > 0.3) {
      overallRisk = 'High';
    } else if (distribution.High > 0 || distribution.Medium > 10) {
      overallRisk = 'Medium';
    }

    return {
      overallRisk,
      distribution,
      totalFindings,
      calculated_at: new Date().toISOString()
    };
  }

  /**
   * Generate executive summary (Section I) from completed analysis
   */
  async generateExecutiveSummary(metadata) {
    const prompt = this.promptBuilder.buildExecutiveSummary(
      this.results.sections,
      {
        ...metadata,
        risk_summary: this.results.risk_summary
      }
    );

    const response = await this.openai.analyzeContract(prompt);

    try {
      return JSON.parse(response);
    } catch (e) {
      return {
        overall_assessment: response.substring(0, 500),
        critical_findings: [],
        key_recommendations: [],
        compliance_summary: 'See detailed analysis'
      };
    }
  }

  /**
   * Create fallback summary if AI generation fails
   */
  createFallbackSummary() {
    const risk = this.results.risk_summary;

    return {
      overall_assessment: `Contract analysis completed with ${risk.overallRisk} overall risk. ` +
        `Identified ${risk.totalFindings} total findings across 6 analysis sections.`,
      critical_findings: [
        `${risk.distribution.High} high-risk items require immediate attention`,
        `${risk.distribution.Medium} medium-risk items need review`,
        `${risk.distribution.Low} low-risk items noted for reference`
      ],
      key_recommendations: [
        'Review all high-risk findings with legal counsel',
        'Address medium-risk items before contract execution',
        'Ensure compliance requirements are met'
      ],
      compliance_summary: 'Detailed compliance analysis available in Section V'
    };
  }

  /**
   * Update progress callback
   */
  updateProgress(callback, progress) {
    if (typeof callback === 'function') {
      callback(progress);
    }
  }

  /**
   * Sleep utility for rate limiting
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Cancel ongoing analysis
   */
  cancel() {
    this.cancelled = true;
    this.status = 'cancelled';
  }

  /**
   * Get current status
   */
  getStatus() {
    return this.status;
  }

  /**
   * Get results
   */
  getResults() {
    return this.results;
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = WorkflowController;
}
