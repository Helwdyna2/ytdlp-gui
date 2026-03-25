// ==UserScript==
// @name         Instagram Reel URL Extractor
// @namespace    http://tampermonkey.net/
// @version      1.2
// @description  Extract all /reel/ URLs from Instagram with manual and automated scrolling modes
// @author       Claude
// @match        https://www.instagram.com/*
// @match        https://instagram.com/*
// @grant        GM_setClipboard
// @grant        GM_addStyle
// ==/UserScript==

(function() {
    'use strict';

    // Styles
    const styles = `
        #reel-extractor-panel {
            position: fixed;
            top: 10px;
            right: 10px;
            width: 350px;
            max-height: 80vh;
            background: #1a1a1a;
            border: 1px solid #363636;
            border-radius: 12px;
            z-index: 999999;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            display: flex;
            flex-direction: column;
        }

        #reel-extractor-panel.minimized {
            max-height: none;
            height: auto;
        }

        #reel-extractor-panel.minimized .panel-content {
            display: none;
        }

        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 15px;
            background: #262626;
            border-radius: 12px 12px 0 0;
            cursor: move;
        }

        #reel-extractor-panel.minimized .panel-header {
            border-radius: 12px;
        }

        .panel-header h3 {
            margin: 0;
            color: #fff;
            font-size: 14px;
            font-weight: 600;
        }

        .header-buttons {
            display: flex;
            gap: 8px;
        }

        .header-btn {
            background: none;
            border: none;
            color: #a8a8a8;
            cursor: pointer;
            font-size: 16px;
            padding: 2px 6px;
            border-radius: 4px;
            transition: all 0.2s;
        }

        .header-btn:hover {
            background: #363636;
            color: #fff;
        }

        .panel-content {
            padding: 15px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            overflow: hidden;
        }

        .stats-row {
            display: flex;
            justify-content: space-between;
            color: #a8a8a8;
            font-size: 12px;
        }

        .stats-row span {
            color: #0095f6;
            font-weight: 600;
        }

        .btn-row {
            display: flex;
            gap: 8px;
        }

        .ext-btn {
            flex: 1;
            padding: 10px 12px;
            border: none;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-primary {
            background: #0095f6;
            color: #fff;
        }

        .btn-primary:hover {
            background: #1aa3ff;
        }

        .btn-secondary {
            background: #363636;
            color: #fff;
        }

        .btn-secondary:hover {
            background: #464646;
        }

        .btn-danger {
            background: #ed4956;
            color: #fff;
        }

        .btn-danger:hover {
            background: #ff5c69;
        }

        .btn-success {
            background: #2ecc71;
            color: #fff;
        }

        .btn-success:hover {
            background: #3ddb80;
        }

        .btn-purple {
            background: #8e44ad;
            color: #fff;
        }

        .btn-purple:hover {
            background: #9b59b6;
        }

        .btn-warning {
            background: #f39c12;
            color: #fff;
        }

        .btn-warning:hover {
            background: #f5ab35;
        }

        .ext-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        #url-textarea {
            width: 100%;
            height: 200px;
            background: #121212;
            border: 1px solid #363636;
            border-radius: 8px;
            color: #fff;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 11px;
            padding: 10px;
            resize: vertical;
            box-sizing: border-box;
        }

        #url-textarea:focus {
            outline: none;
            border-color: #0095f6;
        }

        .auto-status {
            background: #262626;
            border-radius: 8px;
            padding: 10px;
            font-size: 12px;
            color: #a8a8a8;
        }

        .auto-status.active {
            border: 1px solid #0095f6;
        }

        .status-line {
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
        }

        .status-line:last-child {
            margin-bottom: 0;
        }

        .status-value {
            color: #fff;
        }

        .progress-bar {
            height: 4px;
            background: #363636;
            border-radius: 2px;
            margin-top: 8px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: #0095f6;
            border-radius: 2px;
            transition: width 0.3s;
        }

        .copy-feedback {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 149, 246, 0.95);
            color: #fff;
            padding: 15px 30px;
            border-radius: 8px;
            font-weight: 600;
            z-index: 9999999;
            animation: fadeInOut 1.5s ease-in-out;
        }

        @keyframes fadeInOut {
            0% { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
            15% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
            85% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
            100% { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
        }
    `;

    // Add styles
    if (typeof GM_addStyle !== 'undefined') {
        GM_addStyle(styles);
    } else {
        const styleEl = document.createElement('style');
        styleEl.textContent = styles;
        document.head.appendChild(styleEl);
    }

    // State
    let collectedUrls = new Set();
    let isAutomatedMode = false;
    let autoScrollInterval = null;
    let lastScrollHeight = 0;
    let noNewContentCount = 0;
    let bounceAttempts = 0;
    let totalScrolls = 0;
    const MAX_BOUNCE_ATTEMPTS = 3;
    const MAX_NO_CONTENT_COUNT = 5;

    // Create panel
    function createPanel() {
        const panel = document.createElement('div');
        panel.id = 'reel-extractor-panel';
        panel.innerHTML = `
            <div class="panel-header">
                <h3>🎬 Reel Extractor</h3>
                <div class="header-buttons">
                    <button class="header-btn" id="minimize-btn" title="Minimize">−</button>
                    <button class="header-btn" id="close-btn" title="Close">×</button>
                </div>
            </div>
            <div class="panel-content">
                <div class="stats-row">
                    <div>URLs Found: <span id="url-count">0</span></div>
                    <div>Page Scrolls: <span id="scroll-count">0</span></div>
                </div>

                <div class="stats-row">
                    <div>User ID: <span id="user-id">—</span></div>
                </div>

                <div class="btn-row">
                    <button class="ext-btn btn-primary" id="scan-btn">🔍 Scan Page</button>
                    <button class="ext-btn btn-secondary" id="clear-btn">🗑️ Clear</button>
                </div>

                <div class="btn-row">
                    <button class="ext-btn btn-warning" id="auto-btn">🤖 Start Auto Mode</button>
                </div>

                <div class="auto-status" id="auto-status">
                    <div class="status-line">
                        <span>Status:</span>
                        <span class="status-value" id="status-text">Idle</span>
                    </div>
                    <div class="status-line">
                        <span>Bounce Attempts:</span>
                        <span class="status-value"><span id="bounce-count">0</span>/${MAX_BOUNCE_ATTEMPTS}</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="progress-fill" style="width: 0%"></div>
                    </div>
                </div>

                <textarea id="url-textarea" placeholder="Extracted reel URLs will appear here..."></textarea>

                <div class="btn-row">
                    <button class="ext-btn btn-success" id="copy-btn">📋 Copy All URLs</button>
                </div>

                <div class="btn-row">
                    <button class="ext-btn btn-purple" id="download-btn">📁 Download .txt</button>
                </div>
            </div>
        `;

        document.body.appendChild(panel);
        setupEventListeners();
        makeDraggable(panel);
    }

    // Extract reel URLs from page
    function extractReelUrls() {
        const links = document.querySelectorAll('a[href*="/reel/"]');
        let newCount = 0;

        links.forEach(link => {
            const href = link.getAttribute('href');
            if (href) {
                // Extract just the reel path and construct full URL
                const match = href.match(/\/reel\/([^\/\?]+)/);
                if (match) {
                    const fullUrl = `https://www.instagram.com/reel/${match[1]}/`;
                    if (!collectedUrls.has(fullUrl)) {
                        collectedUrls.add(fullUrl);
                        newCount++;
                    }
                }
            }
        });

        updateDisplay();
        return newCount;
    }

    // Update the display
    function updateDisplay() {
        const textarea = document.getElementById('url-textarea');
        const countEl = document.getElementById('url-count');
        const scrollCountEl = document.getElementById('scroll-count');

        if (textarea) {
            textarea.value = Array.from(collectedUrls).join('\n');
        }
        if (countEl) {
            countEl.textContent = collectedUrls.size;
        }
        if (scrollCountEl) {
            scrollCountEl.textContent = totalScrolls;
        }
    }

    // Update auto status
    function updateAutoStatus(status, bounces = bounceAttempts) {
        const statusText = document.getElementById('status-text');
        const bounceCount = document.getElementById('bounce-count');
        const progressFill = document.getElementById('progress-fill');
        const autoStatus = document.getElementById('auto-status');

        if (statusText) statusText.textContent = status;
        if (bounceCount) bounceCount.textContent = bounces;
        if (progressFill) {
            const progress = (bounces / MAX_BOUNCE_ATTEMPTS) * 100;
            progressFill.style.width = `${progress}%`;
        }
        if (autoStatus) {
            autoStatus.classList.toggle('active', isAutomatedMode);
        }
    }

    // Automated scrolling
    function startAutoMode() {
        if (isAutomatedMode) return;

        isAutomatedMode = true;
        bounceAttempts = 0;
        noNewContentCount = 0;
        lastScrollHeight = document.documentElement.scrollHeight;

        const autoBtn = document.getElementById('auto-btn');
        autoBtn.textContent = '⏹️ Stop Auto Mode';
        autoBtn.classList.remove('btn-warning');
        autoBtn.classList.add('btn-danger');

        updateAutoStatus('Scrolling...');

        autoScrollInterval = setInterval(() => {
            const currentHeight = document.documentElement.scrollHeight;
            const currentScroll = window.scrollY + window.innerHeight;
            const previousUrlCount = collectedUrls.size;

            // Scan for new URLs
            extractReelUrls();
            totalScrolls++;
            updateDisplay();

            // Check if we're near the bottom
            if (currentScroll >= currentHeight - 500) {
                // Check if we found new content
                if (collectedUrls.size > previousUrlCount || currentHeight > lastScrollHeight) {
                    // Found new content, reset counters
                    noNewContentCount = 0;
                    lastScrollHeight = currentHeight;
                    updateAutoStatus('Found new content, continuing...');
                } else {
                    noNewContentCount++;

                    if (noNewContentCount >= MAX_NO_CONTENT_COUNT) {
                        // Time to bounce
                        bounceAttempts++;
                        noNewContentCount = 0;

                        if (bounceAttempts >= MAX_BOUNCE_ATTEMPTS) {
                            // We're done
                            stopAutoMode();
                            updateAutoStatus('Complete! Reached end.');
                            return;
                        }

                        // Scroll up then back down
                        updateAutoStatus(`Bounce attempt ${bounceAttempts}/${MAX_BOUNCE_ATTEMPTS}...`, bounceAttempts);
                        window.scrollBy(0, -800);

                        setTimeout(() => {
                            window.scrollTo(0, document.documentElement.scrollHeight);
                        }, 500);

                        return;
                    }
                }
            }

            // Continue scrolling down
            window.scrollBy(0, 600);
            lastScrollHeight = currentHeight;

        }, 800);
    }

    // Stop automated mode
    function stopAutoMode() {
        isAutomatedMode = false;

        if (autoScrollInterval) {
            clearInterval(autoScrollInterval);
            autoScrollInterval = null;
        }

        const autoBtn = document.getElementById('auto-btn');
        if (autoBtn) {
            autoBtn.textContent = '🤖 Start Auto Mode';
            autoBtn.classList.remove('btn-danger');
            autoBtn.classList.add('btn-warning');
        }

        if (bounceAttempts < MAX_BOUNCE_ATTEMPTS) {
            updateAutoStatus('Stopped');
        }
    }

    // Copy to clipboard
    function copyUrls() {
        const textarea = document.getElementById('url-textarea');
        const text = textarea.value;

        if (!text) {
            showFeedback('No URLs to copy!');
            return;
        }

        if (typeof GM_setClipboard !== 'undefined') {
            GM_setClipboard(text);
            showFeedback(`Copied ${collectedUrls.size} URLs!`);
        } else {
            textarea.select();
            document.execCommand('copy');
            showFeedback(`Copied ${collectedUrls.size} URLs!`);
        }
    }

    // Get user ID from URL
    function getUserId() {
        const path = window.location.pathname;
        // Match patterns like /username/ or /username/reels/ etc.
        const match = path.match(/^\/([^\/]+)/);
        if (match && match[1] && !['explore', 'reels', 'stories', 'direct', 'accounts', 'p', 'reel'].includes(match[1])) {
            return match[1];
        }
        return null;
    }

    // Update user ID display
    function updateUserIdDisplay() {
        const userIdEl = document.getElementById('user-id');
        const downloadBtn = document.getElementById('download-btn');
        const userId = getUserId();
        if (userIdEl) {
            userIdEl.textContent = userId || '—';
        }
        if (downloadBtn) {
            downloadBtn.textContent = `📁 Download ${userId || 'reels'}.txt`;
        }
        return userId;
    }

    // Download as txt file
    function downloadAsTxt() {
        if (collectedUrls.size === 0) {
            showFeedback('No URLs to download!');
            return;
        }

        const userId = getUserId() || 'instagram_reels';
        const filename = `${userId}.txt`;
        const content = Array.from(collectedUrls).join('\n');

        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        showFeedback(`Downloaded ${filename} (${collectedUrls.size} URLs)`);
    }

    // Show feedback
    function showFeedback(message) {
        const existing = document.querySelector('.copy-feedback');
        if (existing) existing.remove();

        const feedback = document.createElement('div');
        feedback.className = 'copy-feedback';
        feedback.textContent = message;
        document.body.appendChild(feedback);

        setTimeout(() => feedback.remove(), 1500);
    }

    // Clear collected URLs
    function clearUrls() {
        collectedUrls.clear();
        totalScrolls = 0;
        bounceAttempts = 0;
        noNewContentCount = 0;
        updateDisplay();
        updateAutoStatus('Idle', 0);
    }

    // Make panel draggable
    function makeDraggable(panel) {
        const header = panel.querySelector('.panel-header');
        let isDragging = false;
        let offsetX, offsetY;

        header.addEventListener('mousedown', (e) => {
            if (e.target.classList.contains('header-btn')) return;
            isDragging = true;
            offsetX = e.clientX - panel.offsetLeft;
            offsetY = e.clientY - panel.offsetTop;
            header.style.cursor = 'grabbing';
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            panel.style.left = (e.clientX - offsetX) + 'px';
            panel.style.top = (e.clientY - offsetY) + 'px';
            panel.style.right = 'auto';
        });

        document.addEventListener('mouseup', () => {
            isDragging = false;
            header.style.cursor = 'move';
        });
    }

    // Setup event listeners
    function setupEventListeners() {
        document.getElementById('scan-btn').addEventListener('click', () => {
            const newCount = extractReelUrls();
            showFeedback(`Found ${newCount} new URLs (${collectedUrls.size} total)`);
        });

        document.getElementById('clear-btn').addEventListener('click', clearUrls);

        document.getElementById('auto-btn').addEventListener('click', () => {
            if (isAutomatedMode) {
                stopAutoMode();
            } else {
                startAutoMode();
            }
        });

        document.getElementById('copy-btn').addEventListener('click', copyUrls);

        document.getElementById('download-btn').addEventListener('click', downloadAsTxt);

        document.getElementById('minimize-btn').addEventListener('click', () => {
            const panel = document.getElementById('reel-extractor-panel');
            const btn = document.getElementById('minimize-btn');
            panel.classList.toggle('minimized');
            btn.textContent = panel.classList.contains('minimized') ? '+' : '−';
        });

        document.getElementById('close-btn').addEventListener('click', () => {
            stopAutoMode();
            document.getElementById('reel-extractor-panel').remove();
        });
    }

    // Initialize
    function init() {
        // Wait for page to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', createPanel);
        } else {
            createPanel();
        }

        // Update user ID display initially and on URL changes
        setTimeout(updateUserIdDisplay, 500);

        // Watch for URL changes (Instagram is a SPA)
        let lastUrl = location.href;
        const urlObserver = new MutationObserver(() => {
            if (location.href !== lastUrl) {
                lastUrl = location.href;
                updateUserIdDisplay();
            }
        });
        urlObserver.observe(document.body, { childList: true, subtree: true });

        // Also check on popstate (back/forward navigation)
        window.addEventListener('popstate', updateUserIdDisplay);

        // Auto-scan periodically when scrolling manually
        let scrollTimeout;
        window.addEventListener('scroll', () => {
            if (isAutomatedMode) return;
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(extractReelUrls, 300);
        });
    }

    init();
})();