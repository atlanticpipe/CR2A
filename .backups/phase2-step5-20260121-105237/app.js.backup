document.addEventListener("DOMContentLoaded", () => {
  "use strict";

  // ===== CONFIGURATION =====
  const MAX_FILE_MB = 500;
  const APP_VERSION = "2.0.0-github-pages";

  // ===== DOM ELEMENTS =====
  const form = document.querySelector("#submission-form");
  const dropzone = document.querySelector("#dropzone");
  const fileInput = document.querySelector("#file-input");
  const contractIdInput = document.querySelector('input[name="contract_id"]');
  const llmToggle = document.querySelector("#llm_toggle");
  const fileName = document.querySelector("#file-name");
  const timelineEl = document.querySelector("#timeline");
  const validationStatus = document.querySelector("#validation-status");
  const exportStatus = document.querySelector("#export-status");
  const downloadReportBtn = document.querySelector("#download-report");
  const runDemoBtn = document.querySelector("#run-demo");

  // ===== API KEY MANAGEMENT =====
  const checkApiKey = () => {
    const apiKey = localStorage.getItem('openai_api_key');
    if (!apiKey) {
      showApiKeyPrompt();
      return false;
    }
    return true;
  };

  const showApiKeyPrompt = () => {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay active';
    modal.innerHTML = `
      <div class="modal">
        <h3>OpenAI API Key Required</h3>
        <p>This app uses OpenAI's API to analyze contracts. Please enter your API key:</p>
        <div class="field">
          <label>API Key:</label>
          <input type="password" id="api-key-input" placeholder="sk-...">
          <p class="field-help">Your API key is stored locally and never sent to any server except OpenAI.</p>
        </div>
        <div class="modal-actions">
          <button class="btn" onclick="window.open('https://platform.openai.com/api-keys', '_blank')">Get API Key</button>
          <button class="btn primary" id="save-api-key">Save & Continue</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    document.getElementById('save-api-key').addEventListener('click', () => {
      const key = document.getElementById('api-key-input').value.trim();
      if (key) {
        localStorage.setItem('openai_api_key', key);
        modal.remove();
        location.reload();
      } else {
        alert('Please enter a valid API key');
      }
    });
  };

  // ===== FILE HANDLING =====
  const handleFileSelect = (file) => {
    if (!file) return;
    const mb = file.size / 1024 / 1024;
    if (mb > MAX_FILE_MB) {
      fileInput.value = "";
      fileName.textContent = "No file selected";
      showNotification(`File is ${mb.toFixed(2)} MB; limit is ${MAX_FILE_MB} MB.`, 'error');
      return;
    }
    fileName.textContent = `${file.name} (${mb.toFixed(2)} MB)`;
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

  // ===== NOTIFICATIONS =====
  const showNotification = (message, type = 'info') => {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 5000);
  };

  // ===== OUTPUT DISPLAY =====
  const setOutputs = ({ validation, exportStatusText }) => {
    validationStatus.textContent = validation;
    exportStatus.textContent = exportStatusText;
  };

  // ===== DEMO MODE =====
  const runDemo = () => {
    const steps = [
      { title: "Queued", meta: "Demo mode - simulated workflow", active: true },
      { title: "Document Analysis", meta: "Parsing contract text...", active: false },
      { title: "Policy Validation", meta: "Running compliance checks...", active: false },
      { title: "LLM Analysis", meta: "Analyzing with OpenAI...", active: false },
      { title: "Export Ready", meta: "Report generated", active: false },
    ];

    renderTimeline(steps);
    setOutputs({ validation: "Pending", exportStatusText: "Processing..." });

    let currentStep = 0;
    const interval = setInterval(() => {
      if (currentStep < steps.length) {
        steps[currentStep].active = true;
        renderTimeline(steps);
        currentStep++;
      } else {
        clearInterval(interval);
        setOutputs({ validation: "Passed", exportStatusText: "Demo Complete" });
        showNotification('Demo completed successfully!', 'success');
      }
    }, 1000);
  };

  // ===== FORM SUBMISSION =====
  form?.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (!checkApiKey()) return;

    const file = fileInput?.files?.[0];
    const contractId = contractIdInput?.value?.trim() || "";
    const llmEnabled = llmToggle ? !!llmToggle.checked : true;

    if (!contractId) {
      showNotification("Please provide a contract ID", 'error');
      return;
    }

    if (!file) {
      showNotification("Please attach a contract file", 'error');
      return;
    }

    try {
      // TODO: Implement OpenAI-based analysis workflow
      showNotification('Analysis starting... (Implementation in progress)', 'info');

      renderTimeline([
        { title: "Parsing document", meta: "Extracting text from file...", active: true }
      ]);

      setOutputs({ 
        validation: "Processing", 
        exportStatusText: "Analysis workflow will be implemented in Phase 2, Step 4" 
      });

    } catch (error) {
      showNotification(`Error: ${error.message}`, 'error');
      setOutputs({ validation: "Failed", exportStatusText: error.message });
    }
  });

  // ===== DEMO BUTTON =====
  runDemoBtn?.addEventListener("click", runDemo);

  // ===== INITIAL STATE =====
  renderTimeline([
    { title: "Awaiting submission", meta: "Provide contract details to start.", active: true },
  ]);
  setOutputs({ validation: "Pending", exportStatusText: "Pending" });

  // Check for API key on load
  if (!localStorage.getItem('openai_api_key')) {
    showNotification('OpenAI API key required. Click to configure.', 'warning');
  }

  console.log(`CR2A v${APP_VERSION} - GitHub Pages Edition`);
});
