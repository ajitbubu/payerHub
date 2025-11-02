// PayerHub UI JavaScript

const API_BASE_URL = 'http://localhost:8001';
let selectedFile = null;
let authToken = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    checkAPIStatus();
    setupEventListeners();
    loadRecentUploads();
});

// Check API status
async function checkAPIStatus() {
    const statusBadge = document.getElementById('apiStatus');
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        
        if (data.api === 'healthy') {
            statusBadge.classList.add('online');
            statusBadge.innerHTML = '<span class="status-dot"></span><span>API Online</span>';
        } else {
            throw new Error('API unhealthy');
        }
    } catch (error) {
        statusBadge.classList.add('offline');
        statusBadge.innerHTML = '<span class="status-dot"></span><span>API Offline</span>';
        console.error('API status check failed:', error);
    }
}

// Setup event listeners
function setupEventListeners() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');

    // Click to upload
    uploadArea.addEventListener('click', (e) => {
        if (e.target.id !== 'uploadArea' && !e.target.closest('.upload-content')) return;
        fileInput.click();
    });

    // File input change
    fileInput.addEventListener('change', (e) => {
        handleFileSelect(e.target.files[0]);
    });

    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('drag-over');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('drag-over');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        handleFileSelect(file);
    });
}

// Handle file selection
function handleFileSelect(file) {
    if (!file) return;

    // Validate file type
    const validTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png', 'image/tiff', 'text/plain'];
    if (!validTypes.includes(file.type)) {
        alert('Invalid file type. Please upload PDF, JPG, PNG, TIFF, or TXT files.');
        return;
    }

    // Validate file size (50MB max)
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
        alert('File too large. Maximum size is 50MB.');
        return;
    }

    selectedFile = file;

    // Show file preview
    document.querySelector('.upload-content').style.display = 'none';
    document.getElementById('filePreview').style.display = 'flex';
    document.getElementById('fileName').textContent = file.name;
    document.getElementById('fileSize').textContent = formatFileSize(file.size);
    document.getElementById('uploadButton').disabled = false;
}

// Remove selected file
function removeFile() {
    selectedFile = null;
    document.querySelector('.upload-content').style.display = 'block';
    document.getElementById('filePreview').style.display = 'none';
    document.getElementById('fileInput').value = '';
    document.getElementById('uploadButton').disabled = true;
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Get authentication token
async function getAuthToken() {
    if (authToken) return authToken;

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/auth/token?user_id=USER001&organization_id=ORG789`, {
            method: 'POST'
        });
        const data = await response.json();
        authToken = data.data.token;
        return authToken;
    } catch (error) {
        console.error('Failed to get auth token:', error);
        throw error;
    }
}

// Upload document
async function uploadDocument() {
    if (!selectedFile) return;

    const uploadButton = document.getElementById('uploadButton');
    const uploadButtonText = document.getElementById('uploadButtonText');
    
    // Disable button and show loading
    uploadButton.disabled = true;
    uploadButtonText.textContent = 'Uploading...';

    try {
        // Get auth token
        const token = await getAuthToken();

        // Prepare form data
        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('document_type', document.getElementById('documentType').value);
        formData.append('patient_id', document.getElementById('patientId').value);
        formData.append('organization_id', document.getElementById('organizationId').value);

        // Show results section
        document.getElementById('resultsSection').style.display = 'block';
        document.getElementById('progressContainer').style.display = 'block';
        document.getElementById('resultsCard').style.display = 'none';
        document.getElementById('errorCard').style.display = 'none';

        // Scroll to results
        document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });

        // Simulate progress
        animateProgress();

        // Upload file
        const response = await fetch(`${API_BASE_URL}/api/v1/documents/upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        const result = await response.json();

        if (response.ok && result.success) {
            displayResults(result.data);
            saveToRecentUploads(result.data);
        } else {
            throw new Error(result.error || 'Upload failed');
        }

    } catch (error) {
        console.error('Upload error:', error);
        displayError(error.message);
    } finally {
        uploadButton.disabled = false;
        uploadButtonText.textContent = 'Upload & Process';
    }
}

// Animate progress bar
function animateProgress() {
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    const steps = [
        { width: 20, text: 'Uploading document...' },
        { width: 40, text: 'Running OCR extraction...' },
        { width: 60, text: 'Extracting entities...' },
        { width: 80, text: 'Validating data quality...' },
        { width: 100, text: 'Processing complete!' }
    ];

    let currentStep = 0;
    const interval = setInterval(() => {
        if (currentStep < steps.length) {
            progressFill.style.width = steps[currentStep].width + '%';
            progressText.textContent = steps[currentStep].text;
            currentStep++;
        } else {
            clearInterval(interval);
        }
    }, 1000);
}

// Display results
function displayResults(data) {
    document.getElementById('progressContainer').style.display = 'none';
    document.getElementById('resultsCard').style.display = 'block';

    // Status
    const statusEl = document.getElementById('resultStatus');
    statusEl.textContent = data.status.toUpperCase();
    statusEl.className = 'result-status ' + (data.status === 'completed' ? 'success' : 
                                             data.status === 'processing' ? 'processing' : 'error');

    // Document ID
    document.getElementById('resultId').textContent = `ID: ${data.document_id}`;

    // Pipeline steps
    displayPipelineSteps(data.steps);

    // Extracted data (if available)
    if (data.steps && data.steps.entity_extraction) {
        displayExtractedData(data.steps.entity_extraction);
    }

    // Raw response
    document.getElementById('rawResponse').textContent = JSON.stringify(data, null, 2);
}

// Display pipeline steps
function displayPipelineSteps(steps) {
    const container = document.getElementById('pipelineSteps');
    container.innerHTML = '<h4 style="margin-bottom: 1rem; font-weight: 600;">Processing Pipeline</h4>';

    const stepNames = {
        ocr: 'OCR Processing',
        entity_extraction: 'Entity Extraction',
        anomaly_detection: 'Anomaly Detection',
        fhir_conversion: 'FHIR Conversion',
        privacy_check: 'Privacy Check',
        hub_update: 'Hub Integration'
    };

    for (const [key, name] of Object.entries(stepNames)) {
        const step = steps[key];
        const stepEl = document.createElement('div');
        stepEl.className = 'pipeline-step';

        const status = step ? step.status : 'pending';
        const icon = status === 'completed' ? '✓' : status === 'processing' ? '⟳' : '○';

        stepEl.innerHTML = `
            <div class="step-icon ${status}">
                ${icon}
            </div>
            <div class="step-content">
                <div class="step-title">${name}</div>
                <div class="step-details">
                    ${step ? getStepDetails(key, step) : 'Pending'}
                </div>
            </div>
        `;

        container.appendChild(stepEl);
    }
}

// Get step details
function getStepDetails(stepName, stepData) {
    switch (stepName) {
        case 'ocr':
            return `Confidence: ${(stepData.confidence * 100).toFixed(1)}% | Type: ${stepData.document_type}`;
        case 'entity_extraction':
            return `Extracted ${stepData.entities_count} entities`;
        case 'anomaly_detection':
            return stepData.is_anomaly ? `⚠️ Anomaly detected: ${stepData.anomaly_type}` : '✓ No anomalies detected';
        case 'fhir_conversion':
            return `Resource: ${stepData.resource_type} | Status: ${stepData.validation_status}`;
        case 'privacy_check':
            return stepData.access_allowed ? `✓ Access granted (${stepData.access_level})` : '✗ Access denied';
        case 'hub_update':
            return `Record ID: ${stepData.hub_record_id}`;
        default:
            return 'Completed';
    }
}

// Display extracted data
function displayExtractedData(entityData) {
    const container = document.getElementById('extractedData');
    container.innerHTML = '<h4 style="margin-bottom: 1rem; font-weight: 600;">Extracted Information</h4>';

    const sections = [
        { title: 'Patient Information', data: entityData.patient_info },
        { title: 'Insurance Information', data: entityData.insurance_info }
    ];

    sections.forEach(section => {
        if (section.data && Object.keys(section.data).length > 0) {
            const sectionEl = document.createElement('div');
            sectionEl.className = 'data-section';
            sectionEl.innerHTML = `<h4>${section.title}</h4>`;

            const gridEl = document.createElement('div');
            gridEl.className = 'data-grid';

            for (const [key, value] of Object.entries(section.data)) {
                if (value) {
                    const itemEl = document.createElement('div');
                    itemEl.className = 'data-item';
                    itemEl.innerHTML = `
                        <div class="data-label">${key.replace(/_/g, ' ')}</div>
                        <div class="data-value">${value}</div>
                    `;
                    gridEl.appendChild(itemEl);
                }
            }

            sectionEl.appendChild(gridEl);
            container.appendChild(sectionEl);
        }
    });
}

// Display error
function displayError(message) {
    document.getElementById('progressContainer').style.display = 'none';
    document.getElementById('errorCard').style.display = 'block';
    document.getElementById('errorMessage').textContent = message;
}

// Reset form
function resetForm() {
    removeFile();
    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('uploadSection').scrollIntoView({ behavior: 'smooth' });
}

// Save to recent uploads
function saveToRecentUploads(data) {
    const uploads = JSON.parse(localStorage.getItem('recentUploads') || '[]');
    uploads.unshift({
        id: data.document_id,
        fileName: selectedFile.name,
        documentType: document.getElementById('documentType').value,
        status: data.status,
        timestamp: new Date().toISOString()
    });
    
    // Keep only last 10
    if (uploads.length > 10) uploads.pop();
    
    localStorage.setItem('recentUploads', JSON.stringify(uploads));
    loadRecentUploads();
}

// Load recent uploads
function loadRecentUploads() {
    const uploads = JSON.parse(localStorage.getItem('recentUploads') || '[]');
    
    if (uploads.length === 0) return;

    const container = document.getElementById('recentUploads');
    const list = document.getElementById('uploadsList');
    
    container.style.display = 'block';
    list.innerHTML = '';

    uploads.forEach(upload => {
        const item = document.createElement('div');
        item.className = 'upload-item';
        
        const date = new Date(upload.timestamp);
        const timeAgo = getTimeAgo(date);

        item.innerHTML = `
            <div>
                <div style="font-weight: 600; color: var(--gray-900);">${upload.fileName}</div>
                <div style="font-size: 0.875rem; color: var(--gray-600);">
                    ${upload.documentType} • ${timeAgo}
                </div>
            </div>
            <div class="result-status ${upload.status === 'completed' ? 'success' : 'processing'}" 
                 style="padding: 0.25rem 0.75rem; font-size: 0.75rem;">
                ${upload.status}
            </div>
        `;

        list.appendChild(item);
    });
}

// Get time ago
function getTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return Math.floor(seconds / 60) + ' minutes ago';
    if (seconds < 86400) return Math.floor(seconds / 3600) + ' hours ago';
    return Math.floor(seconds / 86400) + ' days ago';
}
