const API_BASE_URL = ""; // Set to your API URL (e.g., https://api.example.com)
const POLICY_DOC_URL = ""; // Optional link to your policy/rulebook docs
const MAX_FILE_MB = 500; // client-side guard; matches CLI default
const UPLOAD_ENDPOINT = "/upload-url"; // expected presign endpoint relative to API_BASE_URL

const fdotToggle = document.querySelector("#fdot_toggle");
const fdotYearField = document.querySelector("#fdot_year_field");
const form = document.querySelector("#submission-form");
const dropzone = document.querySelector("#dropzone");
const fileInput = document.querySelector("#file-input");
const fileName = document.querySelector("#file-name");
const timelineEl = document.querySelector("#timeline");
const validationStatus = document.querySelector("#validation-status");
const exportStatus = document.querySelector("#export-status");
const analysisJson = document.querySelector("#analysis-json");
const insights = document.querySelector("#insights");
const runDemoBtn = document.querySelector("#run-demo");
const docLinkBtn = document.querySelector("#doc-link");
const uploadProgress = document.querySelector("#upload-progress");
const uploadProgressBar = document.querySelector("#upload-progress-bar");
const uploadProgressText = document.querySelector("#upload-progress-text");
const uploadMessage = document.querySelector("#upload-message");

const sampleResult = {
  run_id: "run_demo_123",
  status: "completed",
  completed_at: new Date().toISOString(),
  manifest: {
    contract_id: "FDOT-Bridge-2024-18",
    fdot_contract: true,
    assume_fdot_year: "2024",
    policy_version: "schemas@v1.0",
    validation: { ok: true, findings: 0 },
    export: { pdf: "cr2a_export.pdf", backend: "docx" },
    ocr_mode: "auto",
    llm_refinement: "off",
  },
};

fdotToggle?.addEventListener("change", () => {
  fdotYearField.hidden = !fdotToggle.checked;
});

const handleFileSelect = (file) => {
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

const setOutputs = ({ validation, exportStatusText, payload }) => {
  validationStatus.textContent = validation;
  exportStatus.textContent = exportStatusText;
  analysisJson.textContent = JSON.stringify(payload, null, 2);
};

const setUploadProgress = (pct) => {
  if (!uploadProgress) return;
  uploadProgress.hidden = false;
  uploadProgressBar.style.setProperty("--pct", `${pct}%`);
  uploadProgressText.textContent = `${Math.min(100, Math.max(0, pct)).toFixed(0)}%`;
};

const setUploadMessage = (msg, isError = false) => {
  if (!uploadMessage) return;
  uploadMessage.textContent = msg;
  uploadMessage.style.color = isError ? "var(--danger)" : "var(--muted)";
  if (!msg) uploadMessage.textContent = "";
};

const resetUploadUi = () => {
  if (uploadProgress) uploadProgress.hidden = true;
  if (uploadProgressBar) uploadProgressBar.style.setProperty("--pct", "0%");
  if (uploadProgressText) uploadProgressText.textContent = "0%";
  setUploadMessage("");
};

const runMock = (payload) => {
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
    advance(3, payload.llm === "on" ? "LLM refinement applied." : "LLM skipped (off).");
  }, 1500);
  setTimeout(() => {
    advance(4, "Export finished.");
    setOutputs({
      validation: "Passed",
      exportStatusText: "Completed",
      payload: { ...payload, status: "completed", completed_at: new Date().toISOString() },
    });
    insights.innerHTML = `
      <li>Validation passed with no critical findings.</li>
      <li>Export available via docx backend.</li>
      <li>LLM refinement ${payload.llm === "on" ? "enabled" : "was disabled"}.</li>
    `;
  }, 2000);
};

const submitToApi = async (payload) => {
  renderTimeline([
    { title: "Queued", meta: "Submitting to API…", active: true },
    { title: "Processing", meta: "Waiting for backend response…", active: false },
  ]);
  try {
    const resp = await fetch(`${API_BASE_URL}/analysis`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
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

const presignUpload = async (file) => {
  const params = new URLSearchParams({
    filename: file.name,
    contentType: file.type || "application/octet-stream",
    size: file.size.toString(),
  });
  const resp = await fetch(`${API_BASE_URL}${UPLOAD_ENDPOINT}?${params.toString()}`, {
    method: "GET",
  });
  if (!resp.ok) throw new Error(`Presign failed: HTTP ${resp.status}`);
  return resp.json(); // expected: { url: "...", fields?: {...}, upload_method?: "PUT"|"POST" }
};

const uploadFile = async (file) => {
  resetUploadUi();
  setUploadProgress(1);
  const presign = await presignUpload(file);
  const method = (presign.upload_method || "PUT").toUpperCase();

  if (method === "POST" && presign.fields) {
    const formData = new FormData();
    Object.entries(presign.fields).forEach(([k, v]) => formData.append(k, v));
    formData.append("file", file);
    const resp = await fetch(presign.url, {
      method: "POST",
      body: formData,
    });
    if (!resp.ok) throw new Error(`Upload failed: HTTP ${resp.status}`);
    setUploadProgress(100);
    return { location: presign.fields.key || presign.url };
  }

  // Default: PUT pre-signed URL
  const resp = await fetch(presign.url, {
    method: "PUT",
    headers: {
      "Content-Type": file.type || "application/octet-stream",
    },
    body: file,
  });

  if (!resp.ok) throw new Error(`Upload failed: HTTP ${resp.status}`);
  setUploadProgress(100);
  return { location: presign.url.split("?")[0] };
};

form?.addEventListener("submit", (e) => {
  e.preventDefault();
  const formData = new FormData(form);
  const file = fileInput?.files?.[0] || null;
  const mb = file ? file.size / 1024 / 1024 : 0;

  if (file && mb > MAX_FILE_MB) {
    setUploadMessage(`File is ${(mb).toFixed(2)} MB; limit is ${MAX_FILE_MB} MB.`, true);
    return;
  }

  const payload = {
    contract_id: formData.get("contract_id") || "",
    contract_uri: formData.get("contract_uri") || null,
    fdot_contract: formData.get("fdot_contract") === "on",
    assume_fdot_year: formData.get("assume_fdot_year") || null,
    policy_version: formData.get("policy_version") || null,
    notes: formData.get("notes") || null,
    llm: "off",
  };

  const doSubmit = async () => {
    if (API_BASE_URL) {
      try {
        if (file) {
          setUploadMessage("Uploading…");
          const res = await uploadFile(file);
          setUploadMessage("Upload complete.");
          payload.contract_uri = res.location;
        }
        submitToApi(payload);
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
    } else {
      runMock({ ...sampleResult, ...payload });
    }
  };

  doSubmit();
});

runDemoBtn?.addEventListener("click", () => {
  runMock(sampleResult);
});

docLinkBtn?.addEventListener("click", () => {
  if (POLICY_DOC_URL) {
    window.open(POLICY_DOC_URL, "_blank");
  } else {
    alert("Set POLICY_DOC_URL in app.js to link to your policy bundle.");
  }
});

// Initial render
renderTimeline([
  { title: "Awaiting submission", meta: "Provide contract details to start.", active: true },
]);
setOutputs({
  validation: "Pending",
  exportStatusText: "Pending",
  payload: sampleResult,
});
