document.addEventListener("DOMContentLoaded", () => {
  "use strict";

  // Detect API base from an override or same-origin hosting; empty when running from file://.
  const detectApiBase = () => {
    // Resolve API base from explicit override, meta tag, or same-origin host.
    const meta = document.querySelector('meta[name="cr2a-api-base"]')?.content?.trim();
    const htmlData = document.documentElement?.dataset?.apiBase;
    const overrides = [window.CR2A_API_BASE, meta, htmlData].filter(Boolean);
    if (overrides.length) return String(overrides[0]).replace(/\/$/, "");
    const origin = window.location.origin || "";
    return origin.startsWith("http") ? origin.replace(/\/$/, "") : "/api"; // fallback keeps UI wired
  };

  let API_BASE_URL = detectApiBase();
  const POLICY_DOC_URL = ""; // Optional link to your policy/rulebook docs
  const MAX_FILE_MB = 500; // client-side guard; matches CLI default
  const UPLOAD_ENDPOINT = "/upload-url"; // expected presign endpoint relative to API_BASE_URL

  // Cache DOM nodes once after load to avoid repeated lookups.
  const fdotToggle = document.querySelector("#fdot_toggle");
  const fdotYearField = document.querySelector("#fdot_year_field");
  const form = document.querySelector("#submission-form");
  const dropzone = document.querySelector("#dropzone");
  const fileInput = document.querySelector("#file-input");
  const fileName = document.querySelector("#file-name");
  const backendHelper = document.querySelector("#backend-helper");
  const timelineEl = document.querySelector("#timeline");
  const validationStatus = document.querySelector("#validation-status");
  const exportStatus = document.querySelector("#export-status");
  const analysisJson = document.querySelector("#analysis-json");
  const insights = document.querySelector("#insights");
  const docLinkBtn = document.querySelector("#doc-link");
  const downloadReport = document.querySelector("#download-report");
  const uploadProgress = document.querySelector("#upload-progress");
  const uploadProgressBar = document.querySelector("#upload-progress-bar");
  const uploadProgressText = document.querySelector("#upload-progress-text");
  const uploadMessage = document.querySelector("#upload-message");

  const updateBackendHelper = (base, status) => {
    // Show detected backend base and any probe status for clarity.
    if (!backendHelper) return;
    if (base) {
      backendHelper.textContent = `Backend wired to ${base}/analysis${status ? ` (${status})` : ""}`;
    } else {
      backendHelper.textContent =
        "No backend wired yet — set window.CR2A_API_BASE or host alongside the API.";
    }
  };

  const probeBackend = async () => {
    // Probe /health to find a reachable API; fall back to the first candidate even if /health fails.
    const origin = window.location.origin || "";
    const candidates = new Set();
    if (API_BASE_URL) candidates.add(API_BASE_URL);
    if (origin.startsWith("http")) {
      candidates.add(origin.replace(/\/$/, ""));
      candidates.add(`${origin.replace(/\/$/, "")}/api`);
    }
    candidates.add("/api");

    const ordered = Array.from(candidates);
    let fallback = ordered[0] || "";

    for (const base of ordered) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 3000);
      try {
        const resp = await fetch(`${base}/health`, {
          method: "GET",
          signal: controller.signal,
        });
        if (resp.ok) {
          API_BASE_URL = base.replace(/\/$/, "");
          updateBackendHelper(API_BASE_URL, "health OK");
          return;
        }
      } catch (err) {
        // try next candidate
      } finally {
        clearTimeout(timeout);
      }
    }

    API_BASE_URL = fallback.replace(/\/$/, "");
    updateBackendHelper(API_BASE_URL, fallback ? "health check failed; using fallback" : "not reachable");
  };

  probeBackend();

  fdotToggle?.addEventListener("change", () => {
    // Reveal FDOT year only when the FDOT toggle is on.
    fdotYearField.hidden = !fdotToggle.checked;
  });

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

    // Wire the download link when a server export is available.
    const href = payload.download_url ? `${API_BASE_URL}${payload.download_url}` : null;
    if (downloadReport) {
      if (href) {
        downloadReport.href = href;
        downloadReport.setAttribute("aria-disabled", "false");
        downloadReport.classList.remove("ghost");
      } else {
        downloadReport.href = "#";
        downloadReport.setAttribute("aria-disabled", "true");
        downloadReport.classList.add("ghost");
      }
    }
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

  const submitToApi = async (payload) => {
    // Submit to backend when configured; render minimal two-step timeline.
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
        validation: data.manifest?.validation?.ok ? "Passed" : "See response",
        exportStatusText: data.status || "See response",
        payload: data,
      });
      renderTimeline([
        { title: "Queued", meta: "Submitted.", active: true },
        { title: "Processing", meta: "Backend returned response.", active: true },
      ]);
      if (insights) {
        insights.innerHTML = "";
        const bullets = [
          data.status ? `Status: ${data.status}` : null,
          data.manifest?.validation?.ok === false ? "Validation reported findings." : null,
          data.download_url ? "PDF export available." : null,
        ].filter(Boolean);
        if (bullets.length === 0) bullets.push("Submission accepted; check response for details.");
        bullets.forEach((text) => {
          const li = document.createElement("li");
          li.textContent = text;
          insights.appendChild(li);
        });
      }
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
    // Request presigned URL for the selected file before uploading.
    if (!API_BASE_URL) throw new Error("Backend unavailable; set CR2A_API_BASE or serve with API.");
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
    // Upload via POST (form-data) or PUT (raw) depending on presign response.
    resetUploadUi();
    setUploadProgress(1);
    const presign = await presignUpload(file);
    const method = (presign.upload_method || "PUT").toUpperCase();
    const targetUrl = presign.url?.startsWith("http") ? presign.url : `${API_BASE_URL}${presign.url}`;

    if (method === "POST" && presign.fields) {
      const formData = new FormData();
      Object.entries(presign.fields).forEach(([k, v]) => formData.append(k, v));
      formData.append("file", file);
      const resp = await fetch(targetUrl, {
        method: "POST",
        body: formData,
      });
      if (!resp.ok) throw new Error(`Upload failed: HTTP ${resp.status}`);
      setUploadProgress(100);
      return { location: presign.fields.key || presign.url };
    }

    if (method === "POST") {
      const formData = new FormData();
      formData.append("file", file);
      const resp = await fetch(targetUrl, { method: "POST", body: formData });
      if (!resp.ok) throw new Error(`Upload failed: HTTP ${resp.status}`);
      const data = await resp.json().catch(() => ({}));
      setUploadProgress(100);
      return { location: data.location || presign.url };
    }

    // Default: PUT pre-signed URL
    const resp = await fetch(targetUrl, {
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
    // Main submit handler driving upload + API submission.
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
      if (!API_BASE_URL) {
        setUploadMessage("Backend not detected. Set window.CR2A_API_BASE or host alongside API.", true);
        return;
      }

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
    };

    doSubmit();
  });

  docLinkBtn?.addEventListener("click", () => {
    // Open policy bundle link when available.
    if (!POLICY_DOC_URL) return;
    window.open(POLICY_DOC_URL, "_blank", "noreferrer");
  });
});
