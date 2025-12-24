"""
CR2A Frontend Application
Handles file submission, progress tracking, and results display.
"""

// Configuration
const API_BASE_URL = window.env?.API_BASE_URL || 'http://localhost:5000';
const UPLOAD_CHUNK_SIZE = 1024 * 1024; // 1MB chunks

// State management
let currentAnalysisId = null;
let currentContractId = null;
let analysisInProgress = false;

// DOM Elements
const fileInput = document.getElementById('file-input');
const contractIdInput = document.getElementById('contract-id');
const submitBtn = document.getElementById('submit-btn');
const progressContainer = document.getElementById('progress-container');
const resultsContainer = document.getElementById('results-container');
const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');
const stageIndicator = document.getElementById('stage-indicator');

// Event listeners
submitBtn?.addEventListener('click', handleSubmit);
fileInput?.addEventListener('change', handleFileSelect);

/**
 * Handle file selection
 */
function handleFileSelect(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['pdf', 'docx', 'txt'].includes(ext)) {
        showError('Invalid file type. Please upload PDF, DOCX, or TXT.');
        return;
    }

    // Validate file size (500MB)
    const maxSize = 500 * 1024 * 1024;
    if (file.size > maxSize) {
        showError('File too large. Maximum size is 500 MB.');
        return;
    }

    // Show file info
    const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
    document.getElementById('file-info').textContent = `${file.name} (${sizeMB} MB)`;
}

/**
 * Handle form submission
 */
async function handleSubmit() {
    if (analysisInProgress) {
        showError('Analysis already in progress');
        return;
    }

    const file = fileInput?.files?.[0];
    if (!file) {
        showError('Please select a file');
        return;
    }

    const contractId = contractIdInput?.value || `CONTRACT-${Date.now()}`;

    try {
        // Submit file for analysis
        const formData = new FormData();
        formData.append('file', file);
        formData.append('contract_id', contractId);

        submitBtn.disabled = true;
        submitBtn.textContent = 'Submitting...';
        showProgress();

        const response = await fetch(`${API_BASE_URL}/analyze`, {
            method: 'POST',
            body: formData,
        });

        if (response.status !== 202) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to submit analysis');
        }

        const data = await response.json();
        currentAnalysisId = data.analysis_id;
        currentContractId = data.contract_id;

        console.log(`Analysis submitted: ${currentAnalysisId}`);
        updateProgress(`Submitted for analysis`, 5);

        // Start streaming results
        await streamAnalysis(currentAnalysisId);

    } catch (error) {
        showError(error.message);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Analyze Contract';
    }
}

/**
 * Stream analysis progress and results
 */
async function streamAnalysis(analysisId) {
    analysisInProgress = true;
    const eventSource = new EventSource(`${API_BASE_URL}/analyze/${analysisId}/stream`);

    eventSource.addEventListener('open', () => {
        console.log('Connected to analysis stream');
    });

    eventSource.addEventListener('message', (event) => {
        try {
            const message = JSON.parse(event.data);

            if (message.type === 'progress') {
                handleProgressUpdate(message.data);
            } else if (message.type === 'result') {
                handleAnalysisResult(message.data);
            } else if (message.type === 'complete') {
                handleAnalysisComplete();
                eventSource.close();
            } else if (message.type === 'error') {
                showError(message.message);
                eventSource.close();
            }
        } catch (error) {
            console.error('Error parsing stream message:', error);
        }
    });

    eventSource.addEventListener('error', (error) => {
        console.error('Stream error:', error);
        if (eventSource.readyState === EventSource.CLOSED) {
            console.log('Stream closed');
        } else {
            showError('Connection lost during analysis');
        }
        eventSource.close();
        analysisInProgress = false;
    });
}

/**
 * Handle progress update from stream
 */
function handleProgressUpdate(progress) {
    console.log(`Progress: ${progress.stage} - ${progress.percentage}%`);
    updateProgress(progress.message, progress.percentage);
    updateStage(progress.stage);
}

/**
 * Handle analysis result
 */
function handleAnalysisResult(result) {
    console.log('Analysis result received:', result);
    displayResults(result);
}

/**
 * Handle analysis completion
 */
function handleAnalysisComplete() {
    console.log('Analysis complete');
    analysisInProgress = false;
}

/**
 * Update progress bar and text
 */
function updateProgress(message, percentage) {
    if (progressBar) progressBar.style.width = `${percentage}%`;
    if (progressText) progressText.textContent = `${message} (${percentage}%)`;
}

/**
 * Update stage indicator
 */
function updateStage(stage) {
    const stageNames = {
        'initialization': 'Initializing',
        'text_extraction': 'Extracting Text',
        'clause_extraction': 'Finding Clauses',
        'risk_assessment': 'Assessing Risks',
        'compliance_check': 'Checking Compliance',
        'summary_generation': 'Generating Summary',
        'report_generation': 'Building Report',
        'complete': 'Complete',
    };

    if (stageIndicator) {
        stageIndicator.textContent = stageNames[stage] || stage;
    }
}

/**
 * Display analysis results
 */
function displayResults(result) {
    if (!resultsContainer) return;

    const riskColor = {
        'HIGH': '#ef4444',
        'MEDIUM': '#f59e0b',
        'LOW': '#10b981',
    }[result.risk_level] || '#6b7280';

    resultsContainer.innerHTML = `
        <div class="results-header">
            <h2>Analysis Results</h2>
            <div class="contract-info">
                <p><strong>Contract ID:</strong> ${escapeHtml(result.contract_id)}</p>
                <p><strong>Analysis ID:</strong> ${escapeHtml(result.analysis_id)}</p>
            </div>
        </div>

        <div class="risk-summary">
            <div class="risk-badge" style="background-color: ${riskColor}">
                <div class="risk-level">${result.risk_level}</div>
                <div class="risk-score">Score: ${result.overall_score.toFixed(1)}/100</div>
            </div>
        </div>

        <div class="executive-summary">
            <h3>Executive Summary</h3>
            <p>${escapeHtml(result.executive_summary)}</p>
        </div>

        <div class="findings">
            <h3>Key Findings (${result.findings.length})</h3>
            <div class="findings-list">
                ${result.findings.map(finding => `
                    <div class="finding-card" data-risk="${finding.risk_level}">
                        <div class="finding-header">
                            <span class="clause-type">${escapeHtml(finding.clause_type)}</span>
                            <span class="risk-badge-small">${finding.risk_level}</span>
                        </div>
                        <div class="finding-body">
                            <p><strong>Concern:</strong> ${escapeHtml(finding.concern)}</p>
                            <p><strong>Recommendation:</strong> ${escapeHtml(finding.recommendation)}</p>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>

        <div class="recommendations">
            <h3>Recommendations</h3>
            <ul>
                ${result.recommendations.map(rec => `<li>${escapeHtml(rec)}</li>`).join('')}
            </ul>
        </div>

        <div class="compliance-issues">
            <h3>Compliance Issues</h3>
            ${result.compliance_issues.length > 0 ? `
                <ul>
                    ${result.compliance_issues.map(issue => `<li>${escapeHtml(issue)}</li>`).join('')}
                </ul>
            ` : `<p>No compliance issues identified.</p>`}
        </div>

        <div class="results-actions">
            <button onclick="downloadReport('${result.analysis_id}')">Download Report (PDF)</button>
            <button onclick="resetForm()">Analyze Another</button>
        </div>
    `;
}

/**
 * Show progress container
 */
function showProgress() {
    if (progressContainer) {
        progressContainer.style.display = 'block';
    }
    if (resultsContainer) {
        resultsContainer.style.display = 'none';
    }
}

/**
 * Show error message
 */
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    document.body.insertBefore(errorDiv, document.body.firstChild);

    setTimeout(() => errorDiv.remove(), 5000);
}

/**
 * Download report as PDF
 */
async function downloadReport(analysisId) {
    try {
        const response = await fetch(`${API_BASE_URL}/download/${analysisId}`);
        if (!response.ok) throw new Error('Failed to download report');

        // For now, download as JSON
        const data = await response.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], {
            type: 'application/json'
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `CR2A-Report-${analysisId}.json`;
        a.click();
        URL.revokeObjectURL(url);
    } catch (error) {
        showError(error.message);
    }
}

/**
 * Reset form for new analysis
 */
function resetForm() {
    if (fileInput) fileInput.value = '';
    if (contractIdInput) contractIdInput.value = '';
    if (progressContainer) progressContainer.style.display = 'none';
    if (resultsContainer) resultsContainer.style.display = 'none';
    if (progressBar) progressBar.style.width = '0%';
    if (progressText) progressText.textContent = '';
    currentAnalysisId = null;
    currentContractId = null;
    analysisInProgress = false;
}

/**
 * Escape HTML entities
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;',
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('CR2A Frontend initialized');
});
