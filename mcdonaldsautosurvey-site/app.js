/**
 * McDVOICE Auto Survey — Frontend App Logic (Netlify Static Build)
 * QR scanning, API calls, progress polling, history management
 */

// =========================================================================
// CONFIGURATION: POINT THIS TO YOUR PYTHON BACKEND URL
// E.g., "https://my-survey-backend.onrender.com"
// Do NOT include a trailing slash.
// =========================================================================
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? 'http://localhost:5000' 
    : 'https://YOUR_BACKEND_URL_HERE'; 

// ---- State ----
let currentMode = 'receipt';
let currentJobId = null;
let pollInterval = null;
let qrScanner = null;
let qrActive = false;

// ---- DOM refs ----
const $ = (id) => document.getElementById(id);
const inputCard   = $('input-card');
const progressCard = $('progress-card');
const resultCard   = $('result-card');
const historyCard  = $('history-card');
const btnSubmit    = $('btn-submit');
const btnText      = $('btn-text');
const progressBar  = $('progress-bar');
const progressMsg  = $('progress-message');
const progressPct  = $('progress-percent');
const stepLog      = $('step-log');
const configNotice = $('config-notice');

// Show the config notice if the URL is not configured
if (API_BASE_URL.includes('YOUR_BACKEND_URL_HERE') && !window.location.hostname.includes('localhost')) {
    configNotice.style.display = 'block';
}

// ---- Mode Tabs ----
document.querySelectorAll('.mode-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.mode-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        currentMode = tab.dataset.mode;

        $('mode-receipt').style.display = currentMode === 'receipt' ? 'block' : 'none';
        $('mode-store').style.display   = currentMode === 'store'  ? 'block' : 'none';
    });
});

// ---- Auto-tab code fields ----
const codeFields = ['cn1', 'cn2', 'cn3', 'cn4', 'cn5', 'cn6'];
codeFields.forEach((id, idx) => {
    const field = $(id);
    field.addEventListener('input', () => {
        // Only allow digits
        field.value = field.value.replace(/[^0-9]/g, '');
        const max = parseInt(field.maxLength);
        if (field.value.length >= max && idx < codeFields.length - 1) {
            $(codeFields[idx + 1]).focus();
        }
    });

    field.addEventListener('keydown', (e) => {
        // Backspace to previous field
        if (e.key === 'Backspace' && field.value === '' && idx > 0) {
            $(codeFields[idx - 1]).focus();
        }
    });

    // Handle paste on any field
    field.addEventListener('paste', (e) => {
        e.preventDefault();
        const pasted = (e.clipboardData || window.clipboardData).getData('text').trim();
        parseAndFillCode(pasted);
    });
});

function parseAndFillCode(text) {
    // Clean the text - extract digits
    let clean = text.replace(/[^0-9\-]/g, '');

    let parts;
    if (clean.includes('-')) {
        parts = clean.split('-');
    } else {
        // Raw digits
        const digits = clean.replace(/\D/g, '');
        if (digits.length >= 26) {
            parts = [
                digits.slice(0, 5),
                digits.slice(5, 10),
                digits.slice(10, 15),
                digits.slice(15, 20),
                digits.slice(20, 25),
                digits.slice(25, 26),
            ];
        } else {
            // Try to fill as much as we can
            parts = [digits];
        }
    }

    codeFields.forEach((id, idx) => {
        if (parts[idx]) {
            $(id).value = parts[idx];
        }
    });
}

function getReceiptCode() {
    return codeFields.map(id => $(id).value.trim()).join('-');
}

function validateReceiptCode() {
    const parts = codeFields.map(id => $(id).value.trim());
    for (let i = 0; i < 5; i++) {
        if (parts[i].length !== 5) return false;
    }
    if (parts[5].length < 1) return false;
    return true;
}

// ---- QR Scanner ----
$('qr-toggle').addEventListener('click', () => {
    if (qrActive) {
        stopQR();
    } else {
        startQR();
    }
});

function startQR() {
    const readerDiv = $('qr-reader');
    readerDiv.style.display = 'block';
    $('qr-btn-text').textContent = 'Close Camera';
    qrActive = true;

    qrScanner = new Html5Qrcode("qr-reader");
    qrScanner.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 250, height: 100 } },
        (decodedText) => {
            // Successfully scanned
            parseAndFillCode(decodedText);
            stopQR();
        },
        () => { /* ignore scan errors */ }
    ).catch(err => {
        console.error('QR Scanner error:', err);
        readerDiv.style.display = 'none';
        $('qr-btn-text').textContent = 'Camera unavailable';
        qrActive = false;
    });
}

function stopQR() {
    if (qrScanner) {
        qrScanner.stop().then(() => {
            qrScanner.clear();
        }).catch(() => {});
    }
    $('qr-reader').style.display = 'none';
    $('qr-btn-text').textContent = 'Open Camera';
    qrActive = false;
}

// ---- Submit ----
btnSubmit.addEventListener('click', startSurvey);

async function startSurvey() {
    if (API_BASE_URL.includes('YOUR_BACKEND_URL_HERE') && !window.location.hostname.includes('localhost')) {
        showError('You must configure the API_BASE_URL in app.js before starting a survey.');
        return;
    }

    let payload;

    if (currentMode === 'receipt') {
        if (!validateReceiptCode()) {
            shakeButton();
            return;
        }
        payload = {
            mode: 'receipt_code',
            code: getReceiptCode(),
        };
    } else {
        const store = $('store-number').value.trim();
        if (!store) {
            shakeButton();
            return;
        }
        payload = {
            mode: 'store_info',
            store_number: store,
            ks_number: $('ks-number').value.trim() || '01',
        };
    }

    // Disable button
    btnSubmit.disabled = true;
    btnText.innerHTML = '<span class="spinner"></span> Starting...';

    // Show progress
    progressCard.classList.add('active');
    resultCard.classList.remove('active');
    stepLog.innerHTML = '';
    updateProgress(0, 'Connecting to backend server...');

    try {
        const resp = await fetch(`${API_BASE_URL}/api/survey`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await resp.json();

        if (data.error) {
            showError(data.error);
            resetButton();
            return;
        }

        currentJobId = data.job_id;
        startPolling();

    } catch (err) {
        console.error("Fetch error:", err);
        showError('Could not connect to the backend server. Make sure it is running and CORS is enabled.');
        resetButton();
    }
}

function shakeButton() {
    btnSubmit.style.animation = 'none';
    btnSubmit.offsetHeight; // trigger reflow
    btnSubmit.style.animation = 'shake 0.4s ease';
    setTimeout(() => { btnSubmit.style.animation = 'none'; }, 400);
}

// Add shake animation via JS
const shakeStyle = document.createElement('style');
shakeStyle.textContent = `
@keyframes shake {
    0%, 100% { transform: translateX(0); }
    20% { transform: translateX(-8px); }
    40% { transform: translateX(8px); }
    60% { transform: translateX(-6px); }
    80% { transform: translateX(6px); }
}`;
document.head.appendChild(shakeStyle);

// ---- Polling ----
function startPolling() {
    pollInterval = setInterval(pollStatus, 1500); // Polling every 1.5s
}

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

async function pollStatus() {
    if (!currentJobId) return;

    try {
        const resp = await fetch(`${API_BASE_URL}/api/status/${currentJobId}`);
        const data = await resp.json();

        updateProgress(data.progress || 0, data.message || 'Working...');

        // Add new log entries
        if (data.updates && data.updates.length > 0) {
            const lastShown = stepLog.children.length;
            for (let i = lastShown; i < data.updates.length; i++) {
                addStepEntry(data.updates[i].message);
            }
        }

        if (data.status === 'completed') {
            stopPolling();
            showSuccess(data.validation_code);
            resetButton();
            loadHistory();
        } else if (data.status === 'failed') {
            stopPolling();
            showError(data.error || 'Survey failed');
            resetButton();
        }
    } catch (err) {
        // Ignore transient network errors during polling
        console.warn("Polling error:", err);
    }
}

// ---- UI Updates ----
function updateProgress(pct, msg) {
    progressBar.style.width = pct + '%';
    progressMsg.textContent = msg;
    progressPct.textContent = pct + '%';
}

function addStepEntry(msg) {
    const entry = document.createElement('div');
    entry.className = 'step-entry';
    entry.innerHTML = `<span class="step-dot"></span><span>${escapeHtml(msg)}</span>`;
    stepLog.appendChild(entry);
    stepLog.scrollTop = stepLog.scrollHeight;
}

function showSuccess(code) {
    progressCard.classList.remove('active');
    resultCard.classList.add('active');
    resultCard.innerHTML = `
        <div class="result-success">
            <div class="result-icon">🎉</div>
            <div class="result-label">Your Validation Code</div>
            <div class="result-code" id="validation-code">${escapeHtml(code)}</div>
            <br>
            <button class="copy-btn" id="copy-btn" onclick="copyCode()">
                📋 Copy Code
            </button>
            <div style="margin-top: 20px;">
                <button class="btn-retry" onclick="resetAll()" style="border-color: rgba(255,199,44,0.2); color: var(--mcd-yellow); background: rgba(255,199,44,0.08);">
                    🔄 New Survey
                </button>
            </div>
        </div>
    `;
    // Save to local history
    saveToLocalHistory(code);
}

function showError(msg) {
    progressCard.classList.remove('active');
    resultCard.classList.add('active');
    resultCard.innerHTML = `
        <div class="result-error">
            <div class="error-icon">❌</div>
            <div class="error-message">${escapeHtml(msg)}</div>
            <button class="btn-retry" onclick="resetAll()">
                🔄 Try Again
            </button>
        </div>
    `;
}

function resetButton() {
    btnSubmit.disabled = false;
    btnText.innerHTML = '🚀 Start Survey';
}

function resetAll() {
    resultCard.classList.remove('active');
    progressCard.classList.remove('active');
    resetButton();
    currentJobId = null;
}

// ---- Copy to clipboard ----
function copyCode() {
    const code = document.getElementById('validation-code')?.textContent;
    if (!code) return;

    navigator.clipboard.writeText(code).then(() => {
        const btn = document.getElementById('copy-btn');
        btn.innerHTML = '✅ Copied!';
        btn.classList.add('copied');
        setTimeout(() => {
            btn.innerHTML = '📋 Copy Code';
            btn.classList.remove('copied');
        }, 2000);
    });
}

// ---- Local History ----
function saveToLocalHistory(code) {
    const history = JSON.parse(localStorage.getItem('mcd_history') || '[]');
    history.unshift({
        code: code,
        timestamp: new Date().toISOString(),
        mode: currentMode,
    });
    // Keep last 20
    if (history.length > 20) history.length = 20;
    localStorage.setItem('mcd_history', JSON.stringify(history));
}

function loadHistory() {
    const history = JSON.parse(localStorage.getItem('mcd_history') || '[]');
    const list = document.getElementById('history-list');

    if (history.length === 0) {
        list.innerHTML = '<div class="history-empty">No surveys completed yet</div>';
        return;
    }

    list.innerHTML = history.map(h => {
        const date = new Date(h.timestamp);
        const timeStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        return `
            <div class="history-item">
                <span class="history-code">${escapeHtml(h.code)}</span>
                <span class="history-meta">
                    <span class="history-time">${timeStr}</span>
                </span>
            </div>
        `;
    }).join('');
}

// Also try loading from server
async function loadServerHistory() {
    try {
        const resp = await fetch(`${API_BASE_URL}/api/history`);
        const data = await resp.json();
        if (Array.isArray(data) && data.length > 0) {
            data.forEach(item => {
                if (item.validation_code) {
                    saveToLocalHistory(item.validation_code);
                }
            });
        }
    } catch (e) {
        // Server might not be running
    }
    loadHistory();
}

// ---- Helpers ----
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}

// ---- Init ----
document.addEventListener('DOMContentLoaded', () => {
    loadHistory();
    // Focus first code field
    $('cn1').focus();
});
