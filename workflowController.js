// Workflow Controller - Client-side state machine
// Replaces AWS Step Functions orchestration

class WorkflowController {
  constructor(openaiService, promptBuilder) {
    this.openai = openaiService;
    this.promptBuilder = promptBuilder;
    this.currentStep = null;
    this.progress = 0;
    this.results = {};
    this.status = 'idle'; // idle, running, completed, failed
    this.startTime = null;
    this.endTime = null;
  }

  /**
   * Execute full contract analysis workflow
   * @param {string} contractText - Parsed contract text
   * @param {object} metadata - Contract metadata from form
   * @param {function} onProgress - Progress callback
   * @returns {Promise<object>} Complete analysis results
   */
  async executeAnalysis(contractText, metadata, onProgress) {
    this.status = 'running';
    this.startTime = Date.now();
    this.results = {};
    this.progress = 0;

    try {
      // Define workflow steps
      const steps = [
        { id: 'section_ii', name: 'Section II - Administrative & Commercial', weight: 16 },
        { id: 'section_iii', name: 'Section III - Technical & Performance', weight: 17 },
        { id: 'section_iv', name: 'Section IV - Legal Risk & Enforcement', weight: 13 },
        { id: 'section_v', name: 'Section V - Regulatory & Compliance', weight: 8 },
        { id: 'section_vi', name: 'Section VI - Data & Technology', weight: 7 },
        { id: 'section_vii', name: 'Section VII - Supplemental Risks', weight: 5 },
        { id: 'section_viii', name: 'Section VIII - Final Analysis', weight: 4 }
      ];

      const totalWeight = steps.reduce((sum, step) => sum + step.weight, 0);
      let completedWeight = 0;

      // Process each section
      for (const step of steps) {
        this.currentStep = step.name;

        // Report progress
        onProgress({
          step: step.name,
          stepId: step.id,
          progress: Math.round((completedWeight / totalWeight) * 100),
          status: 'processing',
          message: `Analyzing ${step.name}...`
        });

        // Get prompt for this section
        const prompt = this.promptBuilder.getSectionPrompt(step.id);

        // Analyze with OpenAI
        const analysis = await this.openai.analyzeSection(
          contractText,
          prompt,
          metadata
        );

        // Store result
        this.results[step.id] = {
          name: step.name,
          analysis: analysis,
          completedAt: new Date().toISOString()
        };

        // Update progress
        completedWeight += step.weight;
        this.progress = Math.round((completedWeight / totalWeight) * 100);

        // Rate limit protection (500ms between calls)
        await this.delay(500);
      }

      // Generate Section I (Overview) based on all results
      onProgress({
        step: 'Section I - Overview',
        stepId: 'section_i',
        progress: 95,
        status: 'processing',
        message: 'Generating executive summary...'
      });

      this.results.section_i = await this.generateOverview(metadata);

      // Final progress
      this.progress = 100;
      this.status = 'completed';
      this.endTime = Date.now();

      onProgress({
        step: 'Complete',
        progress: 100,
        status: 'completed',
        message: 'Analysis complete',
        results: this.results
      });

      return this.getFormattedResults();

    } catch (error) {
      this.status = 'failed';
      this.endTime = Date.now();

      onProgress({
        step: this.currentStep || 'Unknown',
        progress: this.progress,
        status: 'failed',
        error: error.message
      });

      throw error;
    }
  }

  /**
   * Generate Section I overview based on accumulated results
   */
  async generateOverview(metadata) {
    const riskSummary = this.calculateRiskSummary();

    return {
      name: 'Section I - Overview',
      project_title: metadata.project_title || '',
      solicitation_no: metadata.solicitation_no || '',
      owner: metadata.owner || '',
      contractor: metadata.contractor || '',
      scope: metadata.scope || '',
      contract_id: metadata.contract_id || '',
      general_risk_level: riskSummary.overallRisk,
      risk_distribution: riskSummary.distribution,
      bid_model: metadata.bid_model || '',
      notes: metadata.notes || '',
      analysis_date: new Date().toISOString(),
      completedAt: new Date().toISOString()
    };
  }

  /**
   * Calculate risk summary from all sections
   */
  calculateRiskSummary() {
    const risks = {
      high: 0,
      medium: 0,
      low: 0
    };

    // Parse results to count risk levels
    // This is a simplified version - actual implementation would parse
    // the structured analysis from each section
    Object.values(this.results).forEach(result => {
      if (result.analysis) {
        const text = result.analysis.toLowerCase();
        // Simple keyword matching - improve with structured parsing
        if (text.includes('high risk')) risks.high++;
        if (text.includes('medium risk')) risks.medium++;
        if (text.includes('low risk')) risks.low++;
      }
    });

    // Determine overall risk level
    let overallRisk = 'Low';
    if (risks.high > 3) overallRisk = 'High';
    else if (risks.high > 0 || risks.medium > 5) overallRisk = 'Medium';

    return {
      overallRisk,
      distribution: risks,
      totalFlags: risks.high + risks.medium + risks.low
    };
  }

  /**
   * Format results for export
   */
  getFormattedResults() {
    return {
      metadata: {
        analysis_id: this.generateAnalysisId(),
        status: this.status,
        started_at: new Date(this.startTime).toISOString(),
        completed_at: new Date(this.endTime).toISOString(),
        duration_ms: this.endTime - this.startTime,
        version: '2.0.0-github-pages'
      },
      sections: this.results,
      summary: this.results.section_i || {},
      risk_summary: this.calculateRiskSummary()
    };
  }

  /**
   * Generate unique analysis ID
   */
  generateAnalysisId() {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 9);
    return `cr2a_${timestamp}_${random}`;
  }

  /**
   * Delay helper for rate limiting
   */
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Get current workflow status
   */
  getStatus() {
    return {
      status: this.status,
      currentStep: this.currentStep,
      progress: this.progress,
      startTime: this.startTime,
      endTime: this.endTime
    };
  }

  /**
   * Cancel running analysis
   */
  cancel() {
    if (this.status === 'running') {
      this.status = 'cancelled';
      this.endTime = Date.now();
    }
  }

  /**
   * Reset workflow state
   */
  reset() {
    this.status = 'idle';
    this.currentStep = null;
    this.progress = 0;
    this.results = {};
    this.startTime = null;
    this.endTime = null;
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = WorkflowController;
}
