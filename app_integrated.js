document.addEventListener("DOMContentLoaded", async () => {
  "use strict";

  // ===== CONFIGURATION =====
  const MAX_FILE_MB = 500;
  const APP_VERSION = "2.0.0-github-pages";

  console.log(`🚀 CR2A v${APP_VERSION} - GitHub Pages Edition`);

  // ===== INITIALIZE SERVICES =====
  let services = null;

  try {
    // Check if API key exists
    if (!ConfigManager.hasApiKey()) {
      showApiKeyWarning();
    }

    // Initialize services
    services = await initializeServices();
    console.log("✅ Services initialized successfully");
  } catch (error) {
    console.error("❌ Service initialization failed:", error);
    showNotification(`Initialization error: ${error.message}`, 'error');
  }

  // ===== DOM ELEMENTS =====
  const form = document.querySelector("#submission-form");
  const dropzone = document.querySelector("#dropzone");
  const fileInput = document.querySelector("#file-input");
  const contractIdInput = document.querySelector("#contract-id");
  const projectTitleInput = document.querySelector("#project-title");
  const ownerInput = document.querySelector("#owner");
  const llmToggle = document.querySelector("#llm_toggle");
  const fileName = document.querySelector("#file-name");
  const timelineEl = document.querySelector("#timeline");
  const validationStatus = document.querySelector("#validation-status");
  const riskLevel = document.querySelector("#risk-level");
  const findingsCount = document.querySelector("#findings-count");
  const exportStatus = document.querySelector("#export-status");
  const downloadReportBtn = document.querySelector("#download-report");
  const runDemoBtn = document.querySelector("#run-demo");
  const submitBtn = document.querySelector("#submit-btn");

  // ===== SERVICE INITIALIZATION =====
  async function initializeServices() {
    const apiKey = ConfigManager.getApiKey();
    const model = ConfigManager.getModel();

    const openai = new OpenAIService(apiKey || 'placeholder');
    const fileParser = new FileParser();
    const promptBuilder = new PromptBuilder();
    const workflow = new WorkflowController(openai, promptBuilder);

    // Load prompt data
    await promptBuilder.loadPromptData('./data/promptScript.json');

    return {
      openai,
      fileParser,
      promptBuilder,
      workflow
    };
  }

  // ===== API KEY MANAGEMENT =====
  function showApiKeyWarning() {
    showNotification(
      '⚙️ OpenAI API key required. Click Settings to configure.',
      'warning'
    );
  }

  function checkApiKey() {
    if (!ConfigManager.hasApiKey()) {
      showNotification('Please configure your OpenAI API key in Settings', 'error');
      // Open settings modal
      document.getElementById('settings-modal').style.display = 'flex';
      return false;
    }
    return true;
  }

  // ===== FILE HANDLING =====
  const handleFileSelect = (file) => {
    if (!file) return;

    const mb = file.size / (1024 * 1024);
    if (mb > MAX_FILE_MB) {
      fileInput.value = "";
      fileName.textContent = "No file selected";
      showNotification(
        `File too large: ${mb.toFixed(2)} MB (max: ${MAX_FILE_MB} MB)`,
        'error'
      );
      return;
    }

    fileName.textContent = `${file.name} (${mb.toFixed(2)} MB)`;
    fileName.style.color = 'var(--success)';
  };

  // Drag and drop handlers
  dropzone?.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragging");
  });

  dropzone?.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragging");
  });

  dropzone?.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragging");
    const file = e.dataTransfer.files?.[0];
    if (file) {
      fileInput.files = e.dataTransfer.files;
      handleFileSelect(file);
    }
  });

  fileInput?.addEventListener("change", (e) => {
    const file = e.target.files?.[0];
    handleFileSelect(file);
  });

  // ===== TIMELINE RENDERING =====
  const renderTimeline = (steps) => {
    if (!timelineEl) return;

    timelineEl.innerHTML = "";
    steps.forEach((step) => {
      const row = document.createElement("div");
      row.className = "timeline-row";

      const dot = document.createElement("div");
      dot.className = `dot ${step.active ? "active" : ""}`;

      const copy = document.createElement("div");
      const title = document.createElement("p");
      title.className = "title";
      title.textContent = step.title;

      const meta = document.createElement("p");
      meta.className = "meta";
      meta.textContent = step.meta;

      copy.appendChild(title);
      copy.appendChild(meta);
      row.appendChild(dot);
      row.appendChild(copy);
      timelineEl.appendChild(row);
    });
  };

  // ===== OUTPUT DISPLAY =====
  const updateOutputs = (data) => {
    if (validationStatus) {
      validationStatus.textContent = data.status || 'Processing';
    }

    if (riskLevel && data.riskLevel) {
      riskLevel.textContent = data.riskLevel;
      riskLevel.className = `output-value pill ${data.riskLevel.toLowerCase()}`;
    }

    if (findingsCount && data.findingsCount !== undefined) {
      findingsCount.textContent = data.findingsCount;
    }

    if (exportStatus) {
      exportStatus.textContent = data.exportStatus || 'Pending';
    }

    // Enable download if results available
    if (downloadReportBtn && data.results) {
      downloadReportBtn.setAttribute('aria-disabled', 'false');
      downloadReportBtn.classList.remove('disabled');
      downloadReportBtn.onclick = () => exportResults(data.results);
    }
  };

  // ===== PROGRESS HANDLING =====
  const handleProgress = (progress) => {
    console.log(`Progress: ${progress.step} (${progress.progress}%)`);

    // Update timeline with current step
    const steps = [
      { 
        title: progress.step || 'Processing', 
        meta: progress.message || `${progress.progress}% complete`,
        active: true 
      }
    ];

    renderTimeline(steps);

    // Update status display
    updateOutputs({
      status: progress.status || 'Processing',
      exportStatus: progress.message || `${progress.progress}% complete`
    });
  };

  // ===== EXPORT RESULTS =====
  const exportResults = async (results) => {
    try {
      showNotification('Generating PDF report...', 'info');

      // Create simple JSON export for now
      // TODO: Implement PDF generation with jsPDF
      const jsonData = JSON.stringify(results, null, 2);
      const blob = new Blob([jsonData], { type: 'application/json' });

      // Use FileSaver.js if available, fallback to manual download
      if (typeof saveAs === 'function') {
        saveAs(blob, `cr2a-analysis-${Date.now()}.json`);
      } else {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `cr2a-analysis-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
      }

      showNotification('Report downloaded successfully!', 'success');

      // Save to storage
      StorageManager.set('last_analysis', results);

    } catch (error) {
      console.error('Export failed:', error);
      showNotification(`Export failed: ${error.message}`, 'error');
    }
  };

  // ===== DEMO MODE =====
  const runDemo = () => {
    showNotification('Running demo analysis...', 'info');

    const steps = [
      { title: "Queued", meta: "Demo mode - simulated workflow", active: true },
      { title: "Document Analysis", meta: "Parsing contract text...", active: false },
      { title: "Section II Analysis", meta: "Administrative & Commercial...", active: false },
      { title: "Section III Analysis", meta: "Technical & Performance...", active: false },
      { title: "Risk Assessment", meta: "Calculating risk scores...", active: false },
      { title: "Export Ready", meta: "Report generated", active: false },
    ];

    renderTimeline(steps);
    updateOutputs({
      status: 'Processing',
      exportStatus: 'Running demo...'
    });

    let currentStep = 0;
    const interval = setInterval(() => {
      if (currentStep < steps.length) {
        steps[currentStep].active = true;
        renderTimeline(steps);
        currentStep++;

        // Update progress
        const progress = Math.round((currentStep / steps.length) * 100);
        updateOutputs({
          status: currentStep === steps.length ? 'Completed' : 'Processing',
          exportStatus: `${progress}% complete`
        });
      } else {
        clearInterval(interval);

        // Show demo results
        updateOutputs({
          status: 'Completed (Demo)',
          riskLevel: 'Medium',
          findingsCount: 12,
          exportStatus: 'Demo Complete',
          results: {
            demo: true,
            message: 'This is a demo analysis',
            sections: {}
          }
        });

        showNotification('Demo completed successfully!', 'success');
      }
    }, 800);
  };

  // ===== FORM SUBMISSION =====
  form?.addEventListener("submit", async (e) => {
    e.preventDefault();

    // Check API key
    if (!checkApiKey()) return;

    // Reinitialize services with current API key
    try {
      services = await initializeServices();
    } catch (error) {
      showNotification(`Service initialization failed: ${error.message}`, 'error');
      return;
    }

    const file = fileInput?.files?.[0];
    const contractId = contractIdInput?.value?.trim() || "";
    const projectTitle = projectTitleInput?.value?.trim() || "";
    const owner = ownerInput?.value?.trim() || "";
    const llmEnabled = llmToggle ? !!llmToggle.checked : true;

    // Validation
    if (!contractId) {
      showNotification("Please provide a contract ID", 'error');
      return;
    }

    if (!file) {
      showNotification("Please attach a contract file", 'error');
      return;
    }

    // Disable form during processing
    submitBtn.disabled = true;
    submitBtn.classList.add('loading');

    try {
      showNotification('Starting analysis...', 'info');

      // Step 1: Parse file
      renderTimeline([
        { title: "Parsing document", meta: `Extracting text from ${file.name}...`, active: true }
      ]);

      const parsed = await services.fileParser.parseFile(file);
      console.log(`✅ Parsed ${parsed.wordCount} words from ${file.name}`);

      showNotification(`Document parsed: ${parsed.wordCount} words`, 'success');

      // Step 2: Prepare metadata
      const metadata = {
        contract_id: contractId,
        project_title: projectTitle,
        owner: owner,
        filename: file.name,
        file_size: parsed.metadata.size,
        word_count: parsed.wordCount,
        llm_enabled: llmEnabled,
        analysis_date: new Date().toISOString()
      };

      // Step 3: Run workflow
      if (!llmEnabled) {
        showNotification('LLM analysis disabled - using rule-based analysis only', 'info');
      }

      const results = await services.workflow.executeAnalysis(
        parsed.content,
        metadata,
        handleProgress
      );

      // Step 4: Display results
      console.log('✅ Analysis complete:', results);

      // Calculate summary stats
      const riskSummary = results.risk_summary || { overallRisk: 'Unknown', distribution: {} };
      const totalFindings = Object.values(riskSummary.distribution || {})
        .reduce((sum, val) => sum + val, 0);

      updateOutputs({
        status: 'Completed',
        riskLevel: riskSummary.overallRisk,
        findingsCount: totalFindings,
        exportStatus: 'Ready for download',
        results: results
      });

      // Final timeline
      renderTimeline([
        { title: "Analysis Complete", meta: "All sections analyzed successfully", active: true },
        { title: "Report Ready", meta: "Click 'Get Report' to download", active: true }
      ]);

      showNotification('✅ Analysis completed successfully!', 'success');

    } catch (error) {
      console.error('❌ Analysis failed:', error);

      renderTimeline([
        { title: "Error", meta: error.message, active: true }
      ]);

      updateOutputs({
        status: 'Failed',
        exportStatus: `Error: ${error.message}`
      });

      showNotification(`Analysis failed: ${error.message}`, 'error');
    } finally {
      // Re-enable form
      submitBtn.disabled = false;
      submitBtn.classList.remove('loading');
    }
  });

  // ===== DEMO BUTTON =====
  runDemoBtn?.addEventListener("click", runDemo);

  // ===== INITIAL STATE =====
  renderTimeline([
    { 
      title: "Awaiting submission", 
      meta: "Upload a contract and provide details to start analysis", 
      active: true 
    }
  ]);

  updateOutputs({
    status: 'Pending',
    exportStatus: 'Pending'
  });

  // Check API key status on load
  if (ConfigManager.hasApiKey()) {
    console.log('✅ API key configured');
  } else {
    console.warn('⚠️ No API key configured');
  }
});
