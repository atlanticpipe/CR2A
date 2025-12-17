document.addEventListener("DOMContentLoaded", () => {
  "use strict";

  // Backend URL comes from env.js or a global override; GitHub Pages keeps this static.
  const configuredApiBase =
    (typeof window !== "undefined" &&
      (window._env?.API_BASE_URL || window.CR2A_API_BASE)) ||
    "";
  const configuredAuthToken =
    (typeof window !== "undefined" &&
      (window._env?.API_AUTH_TOKEN || window.CR2A_API_TOKEN)) ||
    "";
  const API_BASE_URL = configuredApiBase.replace(/\/+$/, "");
  const AUTHORIZATION = configuredAuthToken.trim();
  const requireApiBase = () => {
    // Fail fast if the API base is missing so uploads never target the wrong host.
    if (!API_BASE_URL) {
      throw new Error(
        "API base URL is not set. Edit webapp/env.js or set window.CR2A_API_BASE to your API Gateway base path.",
      );
    }
    return API_BASE_URL;
  };
  const requireAuthHeader = () => {
    // Lambda authorizer guard: ensure Authorization header is always sent.
    if (!AUTHORIZATION) {
      throw new Error(
        "Authorization token is not set. Edit webapp/env.js or set window.CR2A_API_TOKEN to the required value.",
      );
    }
    return { Authorization: AUTHORIZATION };
  };
  const POLICY_DOC_URL = ""; // Optional link to your policy/rulebook docs
  const MAX_FILE_MB = 500; // client-side guard; matches CLI default
  const UPLOAD_ENDPOINT = "/upload-url"; // expected presign endpoint relative to API_BASE_URL
  const getUploadUrl = async (filename, contentType, size) => {
    // Request a presigned URL for the given file with explicit params.
    const apiBase = requireApiBase();
    const params = new URLSearchParams({
      filename,
      contentType,
      size: String(size),
    });

    const res = await fetch(`${apiBase}${UPLOAD_ENDPOINT}?${params.toString()}`, {
      headers: requireAuthHeader(), // Propagate caller auth for Lambda authorizer.
    });
    if (!res.ok) {
      throw new Error("Failed to get upload URL");
    }
    return res.json(); // { uploadUrl, key }
  };

  // Cache DOM nodes once after load to avoid repeated lookups.
  const form = document.querySelector("#submission-form");
  const dropzone = document.querySelector("#dropzone");
  const fileInput = document.querySelector("#file-input");
  const contractIdInput = document.querySelector('input[name="contract_id"]');
  const llmToggle = document.querySelector("#llm_toggle");
  const fileName = document.querySelector("#file-name");
  const timelineEl = document.querySelector("#timeline");
  const validationStatus = document.querySelector("#validation-status");
  const exportStatus = document.querySelector("#export-status");
  const analysisJson = document.querySelector("#analysis-json");
  const runDemoBtn = document.querySelector("#run-demo");
  const docLinkBtn = document.querySelector("#doc-link");
  const uploadProgress = document.querySelector("#upload-progress");
  const uploadProgressBar = document.querySelector("#upload-progress-bar");
  const uploadProgressText = document.querySelector("#upload-progress-text");
  const uploadMessage = document.querySelector("#upload-message");

  // Provide demo output for mock mode and initial render.
  const sampleResult = {
    run_id: "run_demo_123",
    status: "completed",
    completed_at: new Date().toISOString(),
    llm_enabled: true,
    manifest: {
      contract_id: "FDOT-Bridge-2024-18",
      validation: { ok: true, findings: 0 },
      export: { pdf: "cr2a_export.pdf", backend: "docx" },
      ocr_mode: "auto",
      llm_refinement: "on",
    },
  };

  const handleFileSelect = (file) => {
    // Enforce local size guard and surface the selected filename.
    if (!file) return;
    const mb = file.size / 1024 / 1024;
    if (mb > MAX_FILE_MB) {
      fileInput.value = "";
      fileName.textContent = "No file selected";
      setUploadMessage(`File is ${(mb).toFixed(2)} MB; limit is ${MAX_FILE_MB} MB.`, true);
      return;
    }
    fileName.textContent = `${file.name} (${mb.toFixed(2)} MB)`;
    setUploadMessage("");
  };

  dropzone?.addEventListener("dragover", (e) => {
    // Highlight dropzone on drag to guide the user.
    e.preventDefault();
    dropzone.classList.add("dragging");
  });

  dropzone?.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragging");
  });

  dropzone?.addEventListener("drop", (e) => {
    // Accept the first dropped file and mirror it into the file input for form submission.
    e.preventDefault();
    dropzone.classList.remove("dragging");
    const file = e.dataTransfer.files?.[0];
    if (file) {
      fileInput.files = e.dataTransfer.files;
      handleFileSelect(file);
    }
  });

  fileInput?.addEventListener("change", (e) => {
    // Keep UI state in sync with manual file picker selection.
    const file = e.target.files?.[0];
    handleFileSelect(file);
  });

  const renderTimeline = (steps) => {
    // Render timeline rows from the current progression state.
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

  const setOutputs = ({ validation, exportStatusText, payload }) => {
    // Surface backend status and payload JSON in the preview panel.
    validationStatus.textContent = validation;
    exportStatus.textContent = exportStatusText;
    analysisJson.textContent = JSON.stringify(payload, null, 2);
  };

  const setUploadProgress = (pct) => {
    // Show a simple percentage bar while uploading to presigned URL.
    if (!uploadProgress) return;
    uploadProgress.hidden = false;
    uploadProgressBar.style.setProperty("--pct", `${pct}%`);
    uploadProgressText.textContent = `${Math.min(100, Math.max(0, pct)).toFixed(0)}%`;
  };

  const setUploadMessage = (msg, isError = false) => {
    // Provide inline feedback next to the upload bar.
    if (!uploadMessage) return;
    uploadMessage.textContent = msg || "";
    uploadMessage.style.color = isError ? "var(--danger)" : "var(--muted)";
  };

  const resetUploadUi = () => {
    // Clear progress and messaging before a fresh upload attempt.
    if (uploadProgress) uploadProgress.hidden = true;
    if (uploadProgressBar) uploadProgressBar.style.setProperty("--pct", "0%");
    if (uploadProgressText) uploadProgressText.textContent = "0%";
    setUploadMessage("");
  };

  const runMock = (payload) => {
    // Simple simulated progression for offline demo mode.
    const steps = [
      { title: "Queued", meta: "Submission accepted and queued.", active: true },
      { title: "OCR / text prep", meta: "Detecting scans, normalizing text.", active: false },
      { title: "Policy validation", meta: "Running CR2A rules + schemas.", active: false },
      { title: "LLM refinement (optional)", meta: "Applying OpenAI refinement if enabled.", active: false },
      { title: "Export ready", meta: "PDF + JSON outputs available.", active: false },
    ];

    renderTimeline(steps);
    setOutputs({
      validation: "Pending",
      exportStatusText: "Pending",
      payload: payload,
    });

    const advance = (index, metaOverride) => {
      steps.forEach((s, i) => (s.active = i <= index));
      if (metaOverride) steps[index].meta = metaOverride;
      renderTimeline(steps);
    };

    setTimeout(() => advance(1, "OCR complete; ready for validation."), 500);
    setTimeout(() => {
      advance(2, "No blocking findings detected.");
      setOutputs({
        validation: "Passed",
        exportStatusText: "Rendering PDF…",
        payload: payload,
      });
    }, 1000);
    setTimeout(() => {
      advance(3, payload.llm_enabled ? "LLM refinement applied." : "LLM skipped (off).");
    }, 1500);
    setTimeout(() => {
      advance(4, "Export finished.");
      setOutputs({
        validation: "Passed",
        exportStatusText: "Completed",
        payload: { ...payload, status: "completed", completed_at: new Date().toISOString() },
      });
    }, 2000);
  };

  const submitToApi = async (key, contractId, llmEnabled) => {
    // Submit uploaded object key plus contract metadata to backend; render minimal two-step timeline.
    renderTimeline([
      { title: "Queued", meta: "Submitting to API…", active: true },
      { title: "Processing", meta: "Waiting for backend response…", active: false },
    ]);
    try {
      const apiBase = requireApiBase();
      const resp = await fetch(`${apiBase}/analyze`, {
        method: "POST",
        headers: { ...requireAuthHeader(), "Content-Type": "application/json" },
        body: JSON.stringify({ key, contract_id: contractId, llm_enabled: llmEnabled }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setOutputs({
        validation: "See response",
        exportStatusText: data.status || "See response",
        payload: data,
      });
      renderTimeline([
        { title: "Queued", meta: "Submitted.", active: true },
        { title: "Processing", meta: "Backend returned response.", active: true },
      ]);
    } catch (err) {
      setOutputs({
        validation: "Failed",
        exportStatusText: "Failed",
        payload: { error: String(err) },
      });
      renderTimeline([
        { title: "Queued", meta: "Submission sent.", active: true },
        { title: "Error", meta: String(err), active: true },
      ]);
    }
  };

  const uploadFile = async (file) => {
    // Upload via pre-signed PUT URL returned by the backend.
    resetUploadUi();
    setUploadProgress(1);
    const { uploadUrl, key } = await getUploadUrl(
      file.name,
      file.type || "application/octet-stream",
      file.size,
    );

    const resp = await fetch(uploadUrl, {
      method: "PUT",
      headers: {
        "Content-Type": file.type || "application/octet-stream",
      },
      body: file,
    });

    if (!resp.ok) throw new Error(`Upload failed: HTTP ${resp.status}`);
    setUploadProgress(100);
    return { key };
  };

  form?.addEventListener("submit", (e) => {
    // Main submit handler driving upload + API submission or mock fallback.
    e.preventDefault();
    const file = fileInput?.files?.[0] || null;
    const contractId = contractIdInput?.value?.trim() || "";
    const llmEnabled = !!llmToggle?.checked;
    const mb = file ? file.size / 1024 / 1024 : 0;

    if (!contractId) {
      setUploadMessage("Provide a contract ID before submitting.", true);
      return;
    }

    if (file && mb > MAX_FILE_MB) {
      setUploadMessage(`File is ${(mb).toFixed(2)} MB; limit is ${MAX_FILE_MB} MB.`, true);
      return;
    }

    if (!file) {
      // Require an upload since manual contract URIs were removed for safety.
      setUploadMessage("Attach a contract file to continue.", true);
      return;
    }

    const doSubmit = async () => {
      try {
        if (file) {
          setUploadMessage("Uploading…");
          const res = await uploadFile(file);
          setUploadMessage("Upload complete.");
          await submitToApi(res.key, contractId, llmEnabled);
        }
      } catch (err) {
        setUploadMessage(String(err), true);
        setOutputs({
          validation: "Failed",
          exportStatusText: "Failed",
          payload: { error: String(err) },
        });
        renderTimeline([
          { title: "Queued", meta: "Submission sent.", active: true },
          { title: "Error", meta: String(err), active: true },
        ]);
      }
    };

    doSubmit();
  });

  runDemoBtn?.addEventListener("click", () => {
    // Force demo mode regardless of backend wiring.
    runMock(sampleResult);
  });

  docLinkBtn?.addEventListener("click", () => {
    // Open policy bundle link when provided.
    if (POLICY_DOC_URL) {
      window.open(POLICY_DOC_URL, "_blank");
    } else {
      alert("Set POLICY_DOC_URL in app.js to link to your policy bundle.");
    }
  });

  // Initial render showing idle state and sample payload.
  renderTimeline([
    { title: "Awaiting submission", meta: "Provide contract details to start.", active: true },
  ]);
  setOutputs({
    validation: "Pending",
    exportStatusText: "Pending",
    payload: sampleResult,
  });
});
