// ==UserScript==
// @name         RedGifs URL Extractor + Download
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Extract all /watch/ URLs from RedGifs with GUI and download buttons on videos
// @author       Claude
// @match        https://*.redgifs.com/*
// @grant        GM_setClipboard
// @grant        GM_addStyle
// @grant        GM.getValue
// @grant        GM.setValue
// @run-at       document-start
// @noframes
// ==/UserScript==

(function() {
    'use strict';

    const APPID = 'rgext';

    // =================================================================================
    // SECTION: Styles
    // =================================================================================

    const styles = `
        /* URL Extractor Panel */
        #${APPID}-extractor-panel {
            position: fixed;
            top: 10px;
            right: 10px;
            width: 240px;
            max-height: 65vh;
            min-width: 210px;
            min-height: 220px;
            max-width: 90vw;
            max-height: 90vh;
            background: #1a1a1a;
            border: 1px solid #363636;
            border-radius: 8px;
            z-index: 999999;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            display: flex;
            flex-direction: column;
            resize: both;
            overflow: hidden;
            box-sizing: border-box;
        }

        #${APPID}-extractor-panel.minimized {
            max-height: none;
            height: auto;
        }

        #${APPID}-extractor-panel.minimized .panel-content {
            display: none;
        }

        .${APPID}-panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 6px 8px;
            background: #262626;
            border-radius: 12px 12px 0 0;
            cursor: move;
        }

        #${APPID}-extractor-panel.minimized .${APPID}-panel-header {
            border-radius: 8px;
        }

        .${APPID}-panel-header h3 {
            margin: 0;
            color: #fff;
            font-size: 12px;
            font-weight: 600;
        }

        .${APPID}-header-buttons {
            display: flex;
            gap: 8px;
        }

        .${APPID}-header-btn {
            background: none;
            border: none;
            color: #a8a8a8;
            cursor: pointer;
            font-size: 13px;
            padding: 2px 4px;
            border-radius: 3px;
            transition: all 0.2s;
        }

        .${APPID}-header-btn:hover {
            background: #363636;
            color: #fff;
        }

        .${APPID}-panel-content {
            padding: 8px;
            display: flex;
            flex-direction: column;
            gap: 6px;
            overflow: auto;
            flex: 1 1 auto;
            min-height: 0;
        }

        .${APPID}-stats-row {
            display: flex;
            justify-content: space-between;
            color: #a8a8a8;
            font-size: 10px;
        }

        .${APPID}-toggle-row {
            display: flex;
            flex-direction: column;
            gap: 4px;
            font-size: 10px;
            color: #a8a8a8;
        }

        .${APPID}-toggle {
            display: flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
            user-select: none;
        }

        .${APPID}-toggle input {
            width: 12px;
            height: 12px;
            accent-color: #ff4444;
        }

        .${APPID}-stats-row span {
            color: #ff4444;
            font-weight: 600;
        }

        .${APPID}-btn-row {
            display: flex;
            gap: 5px;
        }

        .${APPID}-ext-btn {
            flex: 1;
            padding: 6px 6px;
            border: none;
            border-radius: 5px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            min-width: 0;
            line-height: 1.1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .${APPID}-btn-primary {
            background: #ff4444;
            color: #fff;
        }

        .${APPID}-btn-primary:hover {
            background: #ff6666;
        }

        .${APPID}-btn-secondary {
            background: #363636;
            color: #fff;
        }

        .${APPID}-btn-secondary:hover {
            background: #464646;
        }

        .${APPID}-btn-danger {
            background: #ed4956;
            color: #fff;
        }

        .${APPID}-btn-danger:hover {
            background: #ff5c69;
        }

        .${APPID}-btn-success {
            background: #2ecc71;
            color: #fff;
        }

        .${APPID}-btn-success:hover {
            background: #3ddb80;
        }

        .${APPID}-btn-purple {
            background: #8e44ad;
            color: #fff;
        }

        .${APPID}-btn-purple:hover {
            background: #9b59b6;
        }

        .${APPID}-btn-warning {
            background: #f39c12;
            color: #fff;
        }

        .${APPID}-btn-warning:hover {
            background: #f5ab35;
        }

        .${APPID}-ext-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        #${APPID}-url-textarea {
            width: 100%;
            height: 90px;
            min-height: 70px;
            background: #121212;
            border: 1px solid #363636;
            border-radius: 5px;
            color: #fff;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 10px;
            padding: 6px;
            resize: vertical;
            box-sizing: border-box;
            flex: 1 1 auto;
        }

        #${APPID}-url-textarea:focus {
            outline: none;
            border-color: #ff4444;
        }

        .${APPID}-auto-status {
            background: #262626;
            border-radius: 5px;
            padding: 6px;
            font-size: 10px;
            color: #a8a8a8;
        }

        .${APPID}-auto-status.active {
            border: 1px solid #ff4444;
        }

        .${APPID}-status-line {
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
        }

        .${APPID}-status-line:last-child {
            margin-bottom: 0;
        }

        .${APPID}-status-value {
            color: #fff;
        }

        .${APPID}-progress-bar {
            height: 3px;
            background: #363636;
            border-radius: 2px;
            margin-top: 6px;
            overflow: hidden;
        }

        .${APPID}-progress-fill {
            height: 100%;
            background: #ff4444;
            border-radius: 2px;
            transition: width 0.3s;
        }

        .${APPID}-copy-feedback {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(255, 68, 68, 0.95);
            color: #fff;
            padding: 15px 30px;
            border-radius: 8px;
            font-weight: 600;
            z-index: 9999999;
            animation: ${APPID}-fadeInOut 1.5s ease-in-out;
        }

        @keyframes ${APPID}-fadeInOut {
            0% { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
            15% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
            85% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
            100% { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
        }

        /* Download Button Styles */
        .tileItem, .GifPreview {
            position: relative;
        }

        .${APPID}-download-btn {
            position: absolute;
            top: 8px;
            right: 8px;
            z-index: 10;
            width: 32px;
            height: 32px;
            padding: 0;
            border-radius: 6px;
            background-color: #ff4444;
            border: none;
            cursor: pointer;
            display: grid;
            place-items: center;
            opacity: 0;
            transition: opacity 0.2s, background-color 0.2s;
        }

        .tileItem:hover .${APPID}-download-btn,
        .GifPreview:hover .${APPID}-download-btn {
            opacity: 1;
        }

        .${APPID}-download-btn:hover {
            background-color: #ff6666;
        }

        .${APPID}-download-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .${APPID}-download-btn svg {
            width: 20px;
            height: 20px;
            fill: #fff;
        }

        /* Spinner animation */
        .${APPID}-spinner {
            animation: ${APPID}-spin 1s linear infinite;
        }

        @keyframes ${APPID}-spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        /* Toast notifications */
        .${APPID}-toast-container {
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 9999999;
            display: flex;
            flex-direction: column;
            gap: 10px;
            pointer-events: none;
        }

        .${APPID}-toast {
            padding: 12px 20px;
            border-radius: 8px;
            color: white;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 14px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            animation: ${APPID}-toast-in 0.3s ease-out;
            pointer-events: auto;
        }

        .${APPID}-toast.exiting {
            animation: ${APPID}-toast-out 0.3s ease-in forwards;
        }

        .${APPID}-toast-success { background-color: #2ecc71; }
        .${APPID}-toast-error { background-color: #e74c3c; }
        .${APPID}-toast-info { background-color: #3498db; }

        @keyframes ${APPID}-toast-in {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes ${APPID}-toast-out {
            from { opacity: 1; transform: translateY(0); }
            to { opacity: 0; transform: translateY(-20px); }
        }
    `;

    // =================================================================================
    // SECTION: Icons
    // =================================================================================

    const ICONS = {
        DOWNLOAD: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>`,
        SPINNER: `<svg class="${APPID}-spinner" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path opacity="0.3" d="M12,2A10,10,0,1,0,22,12,10,10,0,0,0,12,2Zm0,18A8,8,0,1,1,20,12,8,8,0,0,1,12,20Z"/><path d="M12,2A10,10,0,0,1,22,12h-2A8,8,0,0,0,12,4Z"/></svg>`,
        SUCCESS: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z"/></svg>`,
        ERROR: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"/></svg>`,
    };

    // =================================================================================
    // SECTION: Settings
    // =================================================================================

    const SETTINGS_KEYS = {
        AUTO_SCAN: `${APPID}_auto_scan`,
        CLEAR_ON_NAV: `${APPID}_clear_on_nav`,
        BLOCK_MEDIA: `${APPID}_block_media`,
    };

    const settings = {
        autoScan: false,
        clearOnNav: false,
        blockMedia: false,
    };

    async function getStoredValue(key, defaultValue) {
        try {
            if (typeof GM !== 'undefined' && typeof GM.getValue === 'function') {
                return await GM.getValue(key, defaultValue);
            }
        } catch (e) {}

        try {
            const raw = localStorage.getItem(key);
            if (raw === null) return defaultValue;
            return JSON.parse(raw);
        } catch (e) {
            return defaultValue;
        }
    }

    async function setStoredValue(key, value) {
        try {
            if (typeof GM !== 'undefined' && typeof GM.setValue === 'function') {
                await GM.setValue(key, value);
                return;
            }
        } catch (e) {}

        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (e) {}
    }

    async function loadSettings() {
        settings.autoScan = Boolean(await getStoredValue(SETTINGS_KEYS.AUTO_SCAN, false));
        settings.clearOnNav = Boolean(await getStoredValue(SETTINGS_KEYS.CLEAR_ON_NAV, false));
        settings.blockMedia = Boolean(await getStoredValue(SETTINGS_KEYS.BLOCK_MEDIA, false));
    }

    // =================================================================================
    // SECTION: Video Cache (via JSON.parse interception)
    // =================================================================================

    const videoCache = new Map();

    function injectPageScript() {
        if (!document.documentElement) return;

        const script = document.createElement('script');
        script.textContent = `
            (function() {
                'use strict';
                const originalParse = JSON.parse;
                JSON.parse = function(text, reviver) {
                    const result = originalParse.call(this, text, reviver);
                    try {
                        if (result && typeof result === 'object') {
                            if (Array.isArray(result.gifs) || (result.gif && typeof result.gif === 'object')) {
                                window.postMessage({
                                    type: 'RGEXT_API_DATA',
                                    data: result
                                }, '*');
                            }
                        }
                    } catch (e) {}
                    return result;
                };
            })();
        `;
        (document.head || document.documentElement).appendChild(script);
        script.remove();
    }

    function listenForApiData() {
        window.addEventListener('message', (event) => {
            if (event.source !== window) return;
            if (event.data.type === 'RGEXT_API_DATA') {
                processApiData(event.data.data);
            }
        });
    }

    function processApiData(data) {
        try {
            const gifs = [];
            if (data && Array.isArray(data.gifs)) gifs.push(...data.gifs);
            if (data && data.gif && typeof data.gif === 'object') gifs.push(data.gif);

            for (const gif of gifs) {
                const id = gif?.id;
                const hdUrl = gif?.urls?.hd;
                if (id && hdUrl) {
                    const normalizedId = id.toLowerCase();
                    if (!videoCache.has(normalizedId)) {
                        videoCache.set(normalizedId, {
                            hdUrl,
                            userName: gif?.userName,
                            createDate: gif?.createDate
                        });
                    }
                }
            }
        } catch (e) {
            console.error('[RGEXT] Error processing API data:', e);
        }
    }

    // =================================================================================
    // SECTION: Toast Notifications
    // =================================================================================

    let toastContainer = null;

    function createToastContainer() {
        if (toastContainer) return;
        if (!document.body) return;
        toastContainer = document.createElement('div');
        toastContainer.className = `${APPID}-toast-container`;
        document.body.appendChild(toastContainer);
    }

    function showToast(message, type = 'info') {
        if (!toastContainer) createToastContainer();

        const toast = document.createElement('div');
        toast.className = `${APPID}-toast ${APPID}-toast-${type}`;
        toast.textContent = message;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('exiting');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // =================================================================================
    // SECTION: Download Functionality
    // =================================================================================

    function formatTimestamp(timestamp) {
        const date = new Date(timestamp * 1000);
        const Y = date.getFullYear();
        const M = String(date.getMonth() + 1).padStart(2, '0');
        const D = String(date.getDate()).padStart(2, '0');
        const h = String(date.getHours()).padStart(2, '0');
        const m = String(date.getMinutes()).padStart(2, '0');
        const s = String(date.getSeconds()).padStart(2, '0');
        return `${Y}${M}${D}_${h}${m}${s}`;
    }

    async function downloadVideo(videoId, button) {
        const info = videoCache.get(videoId.toLowerCase());

        if (!info) {
            showToast('Video not in cache. Try scrolling to load it first.', 'error');
            return;
        }

        // Update button to spinner
        button.innerHTML = ICONS.SPINNER;
        button.disabled = true;

        try {
            const response = await fetch(info.hdUrl);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const blob = await response.blob();
            const objectUrl = URL.createObjectURL(blob);

            // Build filename
            const dateStr = info.createDate ? formatTimestamp(info.createDate) : '';
            const parts = [info.userName, dateStr, videoId].filter(Boolean);
            const filename = `${parts.join('_')}.mp4`;

            // Trigger download
            const a = document.createElement('a');
            a.href = objectUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);

            setTimeout(() => URL.revokeObjectURL(objectUrl), 150);

            button.innerHTML = ICONS.SUCCESS;
            showToast('Download complete!', 'success');
        } catch (e) {
            console.error('[RGEXT] Download failed:', e);
            button.innerHTML = ICONS.ERROR;
            showToast('Download failed: ' + e.message, 'error');
        }

        // Reset button after delay
        setTimeout(() => {
            button.innerHTML = ICONS.DOWNLOAD;
            button.disabled = false;
        }, 2000);
    }

    function addDownloadButton(element, videoId) {
        if (element.querySelector(`.${APPID}-download-btn`)) return;

        const btn = document.createElement('button');
        btn.className = `${APPID}-download-btn`;
        btn.title = 'Download HD Video';
        btn.innerHTML = ICONS.DOWNLOAD;

        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            e.preventDefault();
            downloadVideo(videoId, btn);
        });

        element.appendChild(btn);
    }

    // =================================================================================
    // SECTION: URL Extractor Panel
    // =================================================================================

    let collectedUrls = new Set();
    let isAutomatedMode = false;
    let autoScrollInterval = null;
    let autoScanInterval = null;
    let lastScrollHeight = 0;
    let noNewContentCount = 0;
    let bounceAttempts = 0;
    let totalScrolls = 0;
    const MAX_BOUNCE_ATTEMPTS = 3;
    const MAX_NO_CONTENT_COUNT = 5;

    function createPanel() {
        const panel = document.createElement('div');
        panel.id = `${APPID}-extractor-panel`;
        panel.innerHTML = `
            <div class="${APPID}-panel-header">
                <h3>RedGifs Extractor</h3>
                <div class="${APPID}-header-buttons">
                    <button class="${APPID}-header-btn" id="${APPID}-minimize-btn" title="Minimize">-</button>
                    <button class="${APPID}-header-btn" id="${APPID}-close-btn" title="Close">x</button>
                </div>
            </div>
            <div class="${APPID}-panel-content panel-content">
                <div class="${APPID}-stats-row">
                    <div>URLs Found: <span id="${APPID}-url-count">0</span></div>
                    <div>Page Scrolls: <span id="${APPID}-scroll-count">0</span></div>
                </div>

                <div class="${APPID}-stats-row">
                    <div>Current User: <span id="${APPID}-user-id">-</span></div>
                </div>

                <div class="${APPID}-toggle-row">
                    <label class="${APPID}-toggle">
                        <input type="checkbox" id="${APPID}-auto-scan-toggle">
                        <span>Auto-scan (1s)</span>
                    </label>
                    <label class="${APPID}-toggle">
                        <input type="checkbox" id="${APPID}-clear-nav-toggle">
                        <span>Clear on nav</span>
                    </label>
                    <label class="${APPID}-toggle">
                        <input type="checkbox" id="${APPID}-block-media-toggle">
                        <span>Block media</span>
                    </label>
                </div>

                <div class="${APPID}-btn-row">
                    <button class="${APPID}-ext-btn ${APPID}-btn-primary" id="${APPID}-scan-btn">Scan</button>
                    <button class="${APPID}-ext-btn ${APPID}-btn-secondary" id="${APPID}-clear-btn">Clear</button>
                    <button class="${APPID}-ext-btn ${APPID}-btn-warning" id="${APPID}-auto-btn">Auto</button>
                </div>

                <div class="${APPID}-auto-status" id="${APPID}-auto-status">
                    <div class="${APPID}-status-line">
                        <span>Status:</span>
                        <span class="${APPID}-status-value" id="${APPID}-status-text">Idle</span>
                    </div>
                    <div class="${APPID}-status-line">
                        <span>Bounce Attempts:</span>
                        <span class="${APPID}-status-value"><span id="${APPID}-bounce-count">0</span>/${MAX_BOUNCE_ATTEMPTS}</span>
                    </div>
                    <div class="${APPID}-progress-bar">
                        <div class="${APPID}-progress-fill" id="${APPID}-progress-fill" style="width: 0%"></div>
                    </div>
                </div>

                <textarea id="${APPID}-url-textarea" placeholder="Extracted RedGifs URLs will appear here..."></textarea>

                <div class="${APPID}-btn-row">
                    <button class="${APPID}-ext-btn ${APPID}-btn-success" id="${APPID}-copy-btn">Copy</button>
                    <button class="${APPID}-ext-btn ${APPID}-btn-purple" id="${APPID}-download-btn">Save .txt</button>
                </div>
            </div>
        `;

        document.body.appendChild(panel);
        setupPanelEventListeners();
        makeDraggable(panel);
    }

    function extractWatchUrls() {
        const links = document.querySelectorAll('a[href*="/watch/"]');
        let newCount = 0;

        links.forEach(link => {
            const href = link.getAttribute('href');
            if (href) {
                const match = href.match(/\/watch\/([^\/\?#]+)/);
                if (match) {
                    const fullUrl = `https://www.redgifs.com/watch/${match[1]}`;
                    if (!collectedUrls.has(fullUrl)) {
                        collectedUrls.add(fullUrl);
                        newCount++;
                    }
                }
            }
        });

        const tileItems = document.querySelectorAll('.tileItem[data-feed-item-id]');
        tileItems.forEach(tile => {
            const feedId = tile.dataset.feedItemId;
            if (feedId && !feedId.startsWith('feed-module-')) {
                const fullUrl = `https://www.redgifs.com/watch/${feedId}`;
                if (!collectedUrls.has(fullUrl)) {
                    collectedUrls.add(fullUrl);
                    newCount++;
                }
            }
        });

        const gifPreviews = document.querySelectorAll('.GifPreview[id]');
        gifPreviews.forEach(preview => {
            const id = preview.id;
            if (id && id.startsWith('gif_')) {
                const videoId = id.replace('gif_', '');
                const fullUrl = `https://www.redgifs.com/watch/${videoId}`;
                if (!collectedUrls.has(fullUrl)) {
                    collectedUrls.add(fullUrl);
                    newCount++;
                }
            }
        });

        updateDisplay();
        return newCount;
    }

    function startAutoScan() {
        if (autoScanInterval) return;
        autoScanInterval = setInterval(() => {
            extractWatchUrls();
        }, 1000);
    }

    function stopAutoScan() {
        if (!autoScanInterval) return;
        clearInterval(autoScanInterval);
        autoScanInterval = null;
    }

    function setAutoScanEnabled(enabled) {
        settings.autoScan = enabled;
        if (enabled) {
            startAutoScan();
        } else {
            stopAutoScan();
        }
    }

    function setClearOnNavEnabled(enabled) {
        settings.clearOnNav = enabled;
    }

    const MEDIA_PLACEHOLDER = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==';
    let mediaBlockObserver = null;

    function shouldSkipMediaElement(el) {
        if (!el || !(el instanceof Element)) return true;
        return Boolean(
            el.closest(`#${APPID}-extractor-panel`) ||
            el.closest(`.${APPID}-toast-container`) ||
            el.closest(`.${APPID}-download-btn`)
        );
    }

    function isMediaElementBlocked(el) {
        const tag = el.tagName;
        if (tag === 'IMG') {
            const src = el.getAttribute('src') || '';
            const srcset = el.getAttribute('srcset') || '';
            return src === MEDIA_PLACEHOLDER && srcset === '';
        }
        if (tag === 'VIDEO') {
            const src = el.getAttribute('src') || '';
            const poster = el.getAttribute('poster') || '';
            const preload = el.getAttribute('preload') || '';
            return src === '' && poster === '' && preload === 'none';
        }
        if (tag === 'SOURCE') {
            return !(el.getAttribute('src'));
        }
        const bgImage = el.style ? el.style.backgroundImage : '';
        const bg = el.style ? el.style.background : '';
        const hasBgUrl = bgImage.includes('url(') || bg.includes('url(');
        return !hasBgUrl && el.dataset.rgextBlocked === '1';
    }

    function blockMediaElement(el) {
        if (!(el instanceof Element)) return;
        if (el.dataset.rgextBlocking === '1') return;
        if (shouldSkipMediaElement(el)) return;
        if (el.dataset.rgextBlocked === '1' && isMediaElementBlocked(el)) return;

        el.dataset.rgextBlocking = '1';

        let didBlock = false;
        const tag = el.tagName;

        if (tag === 'IMG') {
            const img = el;
            const currentSrc = img.getAttribute('src') || '';
            if (currentSrc && currentSrc !== MEDIA_PLACEHOLDER) {
                img.dataset.rgextSrc = currentSrc;
            }
            const currentSrcset = img.getAttribute('srcset') || '';
            if (currentSrcset) {
                img.dataset.rgextSrcset = currentSrcset;
            }
            const currentLoading = img.getAttribute('loading') || '';
            if (currentLoading) {
                img.dataset.rgextLoading = currentLoading;
            }
            img.setAttribute('src', MEDIA_PLACEHOLDER);
            img.setAttribute('srcset', '');
            img.setAttribute('loading', 'lazy');
            didBlock = true;
        } else if (tag === 'VIDEO') {
            const video = el;
            const currentSrc = video.getAttribute('src') || '';
            if (currentSrc) {
                video.dataset.rgextSrc = currentSrc;
            }
            const currentPoster = video.getAttribute('poster') || '';
            if (currentPoster) {
                video.dataset.rgextPoster = currentPoster;
            }
            const currentPreload = video.getAttribute('preload') || '';
            if (currentPreload) {
                video.dataset.rgextPreload = currentPreload;
            }
            video.pause();
            video.removeAttribute('src');
            video.removeAttribute('poster');
            video.setAttribute('preload', 'none');
            video.querySelectorAll('source').forEach(blockMediaElement);
            video.load();
            didBlock = true;
        } else if (tag === 'SOURCE') {
            const source = el;
            const currentSrc = source.getAttribute('src') || '';
            if (currentSrc) {
                source.dataset.rgextSrc = currentSrc;
            }
            source.removeAttribute('src');
            didBlock = true;
        }

        const bgImage = el.style ? el.style.backgroundImage : '';
        if (bgImage && bgImage.includes('url(')) {
            el.dataset.rgextBgImage = bgImage;
            el.style.backgroundImage = 'none';
            didBlock = true;
        }

        const bg = el.style ? el.style.background : '';
        if (bg && bg.includes('url(') && !bgImage) {
            el.dataset.rgextBg = bg;
            el.style.background = 'none';
            didBlock = true;
        }

        if (didBlock) {
            el.dataset.rgextBlocked = '1';
        }

        delete el.dataset.rgextBlocking;
    }

    function blockMediaInNode(node) {
        if (!(node instanceof Element)) return;

        if (node.matches('img, video, source')) {
            blockMediaElement(node);
        }

        if (node.hasAttribute('style')) {
            blockMediaElement(node);
        }

        node.querySelectorAll('img, video, source, [style]').forEach(blockMediaElement);
    }

    function restoreMediaElement(el) {
        if (!(el instanceof Element)) return;
        if (el.dataset.rgextBlocked !== '1') return;

        const tag = el.tagName;

        if (tag === 'IMG') {
            if (el.dataset.rgextSrc) {
                el.setAttribute('src', el.dataset.rgextSrc);
            } else {
                el.removeAttribute('src');
            }
            if (el.dataset.rgextSrcset) {
                el.setAttribute('srcset', el.dataset.rgextSrcset);
            } else {
                el.removeAttribute('srcset');
            }
            if (el.dataset.rgextLoading) {
                el.setAttribute('loading', el.dataset.rgextLoading);
            } else {
                el.removeAttribute('loading');
            }
        } else if (tag === 'VIDEO') {
            if (el.dataset.rgextSrc) {
                el.setAttribute('src', el.dataset.rgextSrc);
            }
            if (el.dataset.rgextPoster) {
                el.setAttribute('poster', el.dataset.rgextPoster);
            }
            if (el.dataset.rgextPreload) {
                el.setAttribute('preload', el.dataset.rgextPreload);
            } else {
                el.removeAttribute('preload');
            }
            el.load();
        } else if (tag === 'SOURCE') {
            if (el.dataset.rgextSrc) {
                el.setAttribute('src', el.dataset.rgextSrc);
            }
        }

        if (el.dataset.rgextBgImage) {
            el.style.backgroundImage = el.dataset.rgextBgImage;
        }
        if (el.dataset.rgextBg) {
            el.style.background = el.dataset.rgextBg;
        }

        delete el.dataset.rgextBlocked;
        delete el.dataset.rgextSrc;
        delete el.dataset.rgextSrcset;
        delete el.dataset.rgextLoading;
        delete el.dataset.rgextPoster;
        delete el.dataset.rgextPreload;
        delete el.dataset.rgextBgImage;
        delete el.dataset.rgextBg;
    }

    function restoreMedia() {
        document.querySelectorAll('[data-rgext-blocked="1"]').forEach(restoreMediaElement);
    }

    function enableMediaBlock() {
        if (mediaBlockObserver) return;

        blockMediaInNode(document.documentElement);

        mediaBlockObserver = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                if (mutation.type === 'attributes') {
                    blockMediaElement(mutation.target);
                    continue;
                }
                for (const node of mutation.addedNodes) {
                    blockMediaInNode(node);
                }
            }
        });

        mediaBlockObserver.observe(document.documentElement, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['src', 'srcset', 'poster', 'style', 'data-src', 'data-srcset', 'data-original', 'data-poster', 'data-bg', 'data-background'],
        });
    }

    function disableMediaBlock() {
        if (mediaBlockObserver) {
            mediaBlockObserver.disconnect();
            mediaBlockObserver = null;
        }
        restoreMedia();
    }

    function setBlockMediaEnabled(enabled) {
        settings.blockMedia = enabled;
        if (enabled) {
            enableMediaBlock();
        } else {
            disableMediaBlock();
        }
    }

    function updateDisplay() {
        const textarea = document.getElementById(`${APPID}-url-textarea`);
        const countEl = document.getElementById(`${APPID}-url-count`);
        const scrollCountEl = document.getElementById(`${APPID}-scroll-count`);

        if (textarea) textarea.value = Array.from(collectedUrls).join('\n');
        if (countEl) countEl.textContent = collectedUrls.size;
        if (scrollCountEl) scrollCountEl.textContent = totalScrolls;
    }

    function updateAutoStatus(status, bounces = bounceAttempts) {
        const statusText = document.getElementById(`${APPID}-status-text`);
        const bounceCount = document.getElementById(`${APPID}-bounce-count`);
        const progressFill = document.getElementById(`${APPID}-progress-fill`);
        const autoStatus = document.getElementById(`${APPID}-auto-status`);

        if (statusText) statusText.textContent = status;
        if (bounceCount) bounceCount.textContent = bounces;
        if (progressFill) progressFill.style.width = `${(bounces / MAX_BOUNCE_ATTEMPTS) * 100}%`;
        if (autoStatus) autoStatus.classList.toggle('active', isAutomatedMode);
    }

    function startAutoMode() {
        if (isAutomatedMode) return;

        isAutomatedMode = true;
        bounceAttempts = 0;
        noNewContentCount = 0;
        lastScrollHeight = document.documentElement.scrollHeight;

        const autoBtn = document.getElementById(`${APPID}-auto-btn`);
        autoBtn.textContent = 'Stop';
        autoBtn.classList.remove(`${APPID}-btn-warning`);
        autoBtn.classList.add(`${APPID}-btn-danger`);

        updateAutoStatus('Scrolling...');

        autoScrollInterval = setInterval(() => {
            const currentHeight = document.documentElement.scrollHeight;
            const currentScroll = window.scrollY + window.innerHeight;
            const previousUrlCount = collectedUrls.size;

            extractWatchUrls();
            totalScrolls++;
            updateDisplay();

            if (currentScroll >= currentHeight - 500) {
                if (collectedUrls.size > previousUrlCount || currentHeight > lastScrollHeight) {
                    noNewContentCount = 0;
                    lastScrollHeight = currentHeight;
                    updateAutoStatus('Found new content, continuing...');
                } else {
                    noNewContentCount++;

                    if (noNewContentCount >= MAX_NO_CONTENT_COUNT) {
                        bounceAttempts++;
                        noNewContentCount = 0;

                        if (bounceAttempts >= MAX_BOUNCE_ATTEMPTS) {
                            stopAutoMode();
                            updateAutoStatus('Complete! Reached end.');
                            return;
                        }

                        updateAutoStatus(`Bounce attempt ${bounceAttempts}/${MAX_BOUNCE_ATTEMPTS}...`, bounceAttempts);
                        window.scrollBy(0, -800);
                        setTimeout(() => window.scrollTo(0, document.documentElement.scrollHeight), 500);
                        return;
                    }
                }
            }

            window.scrollBy(0, 600);
            lastScrollHeight = currentHeight;
        }, 800);
    }

    function stopAutoMode() {
        isAutomatedMode = false;
        if (autoScrollInterval) {
            clearInterval(autoScrollInterval);
            autoScrollInterval = null;
        }

        const autoBtn = document.getElementById(`${APPID}-auto-btn`);
        if (autoBtn) {
            autoBtn.textContent = 'Auto';
            autoBtn.classList.remove(`${APPID}-btn-danger`);
            autoBtn.classList.add(`${APPID}-btn-warning`);
        }

        if (bounceAttempts < MAX_BOUNCE_ATTEMPTS) updateAutoStatus('Stopped');
    }

    function copyUrls() {
        const textarea = document.getElementById(`${APPID}-url-textarea`);
        const text = textarea.value;

        if (!text) {
            showFeedback('No URLs to copy!');
            return;
        }

        if (typeof GM_setClipboard !== 'undefined') {
            GM_setClipboard(text);
        } else {
            textarea.select();
            document.execCommand('copy');
        }
        showFeedback(`Copied ${collectedUrls.size} URLs!`);
    }

    function getUserId() {
        const match = window.location.pathname.match(/^\/users\/([^\/]+)/);
        return match ? match[1] : null;
    }

    function getCollectionName() {
        const isUsableName = (value) => {
            if (!value) return false;
            const normalized = value.replace(/\s+/g, ' ').trim();
            if (!normalized) return false;
            const lowered = normalized.toLowerCase();
            if (lowered === 'an unnamed collection') return false;
            if (lowered === 'unnamed collection') return false;
            if (lowered === 'collection') return false;
            return true;
        };

        const normalizeTitle = (value) => {
            if (!value) return '';
            return value
                .replace(/\s*\|\s*redgifs.*$/i, '')
                .replace(/\s*-\s*redgifs.*$/i, '')
                .replace(/\s*redgifs.*$/i, '')
                .trim();
        };

        const header = document.querySelector('.collectionHeader');
        if (header) {
            const candidates = header.querySelectorAll(
                'h1, h2, h3, [data-testid*="title"], [data-testid*="name"], [class*="title"], [class*="name"]'
            );
            for (const el of candidates) {
                const text = el.textContent ? el.textContent.trim() : '';
                if (isUsableName(text)) return text;
            }

            const fallback = header.querySelector('h2:nth-child(2)');
            if (fallback) {
                const text = fallback.textContent ? fallback.textContent.trim() : '';
                if (isUsableName(text)) return text;
            }
        }

        const metaSelectors = [
            'meta[property="og:title"]',
            'meta[name="twitter:title"]',
            'meta[name="title"]',
        ];
        for (const selector of metaSelectors) {
            const meta = document.querySelector(selector);
            if (meta) {
                const content = meta.getAttribute('content');
                const normalized = normalizeTitle(content || '');
                if (isUsableName(normalized)) return normalized;
            }
        }

        const titleText = normalizeTitle(document.title || '');
        if (isUsableName(titleText)) return titleText;

        return null;
    }

    function sanitizeFilename(name) {
        if (!name) return '';
        return name.replace(/[<>:"/\\|?*]/g, '').trim();
    }

    let updateDisplayTimer = null;

    function updateUserIdDisplay() {
        const userIdEl = document.getElementById(`${APPID}-user-id`);
        const downloadBtn = document.getElementById(`${APPID}-download-btn`);
        const userId = getUserId();
        const collectionName = getCollectionName();
        if (userIdEl) userIdEl.textContent = userId || '-';
        if (downloadBtn) downloadBtn.textContent = `Save ${collectionName || userId || 'redgifs'}.txt`;
        return userId;
    }

    function scheduleUpdateUserIdDisplay() {
        if (updateDisplayTimer) {
            clearTimeout(updateDisplayTimer);
        }
        updateDisplayTimer = setTimeout(() => {
            updateUserIdDisplay();
            updateDisplayTimer = null;
        }, 2000);
    }

    function downloadAsTxt() {
        if (collectedUrls.size === 0) {
            showFeedback('No URLs to download!');
            return;
        }

        const collectionName = getCollectionName();
        const userId = getUserId();
        const baseName = sanitizeFilename(collectionName || userId || 'redgifs') || 'redgifs';
        const filename = `${baseName}.txt`;
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

    function showFeedback(message) {
        const existing = document.querySelector(`.${APPID}-copy-feedback`);
        if (existing) existing.remove();

        const feedback = document.createElement('div');
        feedback.className = `${APPID}-copy-feedback`;
        feedback.textContent = message;
        document.body.appendChild(feedback);

        setTimeout(() => feedback.remove(), 1500);
    }

    function clearUrls() {
        collectedUrls.clear();
        totalScrolls = 0;
        bounceAttempts = 0;
        noNewContentCount = 0;
        updateDisplay();
        updateAutoStatus('Idle', 0);
    }

    function makeDraggable(panel) {
        const header = panel.querySelector(`.${APPID}-panel-header`);
        let isDragging = false;
        let offsetX, offsetY;

        header.addEventListener('mousedown', (e) => {
            if (e.target.classList.contains(`${APPID}-header-btn`)) return;
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

    function setupPanelEventListeners() {
        const autoScanToggle = document.getElementById(`${APPID}-auto-scan-toggle`);
        const clearNavToggle = document.getElementById(`${APPID}-clear-nav-toggle`);
        const blockMediaToggle = document.getElementById(`${APPID}-block-media-toggle`);

        if (autoScanToggle) {
            autoScanToggle.addEventListener('change', () => {
                setAutoScanEnabled(autoScanToggle.checked);
                setStoredValue(SETTINGS_KEYS.AUTO_SCAN, settings.autoScan);
            });
        }

        if (clearNavToggle) {
            clearNavToggle.addEventListener('change', () => {
                setClearOnNavEnabled(clearNavToggle.checked);
                setStoredValue(SETTINGS_KEYS.CLEAR_ON_NAV, settings.clearOnNav);
            });
        }

        if (blockMediaToggle) {
            blockMediaToggle.addEventListener('change', () => {
                setBlockMediaEnabled(blockMediaToggle.checked);
                setStoredValue(SETTINGS_KEYS.BLOCK_MEDIA, settings.blockMedia);
            });
        }

        document.getElementById(`${APPID}-scan-btn`).addEventListener('click', () => {
            const newCount = extractWatchUrls();
            showFeedback(`Found ${newCount} new URLs (${collectedUrls.size} total)`);
        });

        document.getElementById(`${APPID}-clear-btn`).addEventListener('click', clearUrls);

        document.getElementById(`${APPID}-auto-btn`).addEventListener('click', () => {
            if (isAutomatedMode) stopAutoMode();
            else startAutoMode();
        });

        document.getElementById(`${APPID}-copy-btn`).addEventListener('click', copyUrls);
        document.getElementById(`${APPID}-download-btn`).addEventListener('click', downloadAsTxt);

        document.getElementById(`${APPID}-minimize-btn`).addEventListener('click', () => {
            const panel = document.getElementById(`${APPID}-extractor-panel`);
            const btn = document.getElementById(`${APPID}-minimize-btn`);
            panel.classList.toggle('minimized');
            btn.textContent = panel.classList.contains('minimized') ? '+' : '-';
        });

        document.getElementById(`${APPID}-close-btn`).addEventListener('click', () => {
            stopAutoMode();
            document.getElementById(`${APPID}-extractor-panel`).remove();
        });
    }

    function applySettingsToPanel() {
        const autoScanToggle = document.getElementById(`${APPID}-auto-scan-toggle`);
        const clearNavToggle = document.getElementById(`${APPID}-clear-nav-toggle`);
        const blockMediaToggle = document.getElementById(`${APPID}-block-media-toggle`);

        if (autoScanToggle) autoScanToggle.checked = settings.autoScan;
        if (clearNavToggle) clearNavToggle.checked = settings.clearOnNav;
        if (blockMediaToggle) blockMediaToggle.checked = settings.blockMedia;

        setAutoScanEnabled(settings.autoScan);
        setClearOnNavEnabled(settings.clearOnNav);
        setBlockMediaEnabled(settings.blockMedia);
    }

    // =================================================================================
    // SECTION: DOM Observer for Download Buttons
    // =================================================================================

    function getVideoIdFromElement(el) {
        // From data-feed-item-id
        const feedId = el.dataset?.feedItemId;
        if (feedId && !feedId.startsWith('feed-module-')) {
            return feedId.toLowerCase();
        }

        // From element ID (gif_xxxxx)
        if (el.id && el.id.startsWith('gif_')) {
            return el.id.split('_')[1]?.toLowerCase();
        }

        // From child link
        const link = el.querySelector('a[href*="/watch/"]');
        if (link) {
            const match = link.href.match(/\/watch\/([^\/\?#]+)/);
            if (match) return match[1].toLowerCase();
        }

        return null;
    }

    function processElement(element) {
        const videoId = getVideoIdFromElement(element);
        if (videoId) {
            addDownloadButton(element, videoId);
        }
    }

    function observeDOM() {
        // Process existing elements
        document.querySelectorAll('.tileItem, .GifPreview').forEach(processElement);

        // Observe for new elements
        const observer = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                for (const node of mutation.addedNodes) {
                    if (node.nodeType !== Node.ELEMENT_NODE) continue;

                    if (node.matches?.('.tileItem, .GifPreview')) {
                        processElement(node);
                    }

                    node.querySelectorAll?.('.tileItem, .GifPreview').forEach(processElement);
                }
            }
        });

        observer.observe(document.body, { childList: true, subtree: true });
    }

    // =================================================================================
    // SECTION: Annoyance Blocker
    // =================================================================================

    class AnnoyanceManager {
        static STYLES = `
                /* --- RGEXT Annoyance Removal --- */

                /* Header: Link button to external site (Desktop) */
                .topNav .aTab {
                    display: none !important;
                }

                /* Information Bar (Top Banner) */
                .InformationBar {
                    display: none !important;
                }

                /* Ad Containers (:has() dependent) */
                .sideBarItem:has(.liveAdButton) {
                    display: none !important;
                }

                /* Feed Injections (Trending Niches/Creators, Ads, etc.) */
                .injection {
                    display: none !important;
                }

                /* Feed Modules */
                .FeedModule:has(.nicheListWidget.trendingNiches),
                .FeedModule:has(.seeMoreBlock.suggestedCreators),
                .FeedModule:has(.seeMoreBlock.trendingCreators),
                .FeedModule:has(.OnlyFansCreatorsModule),
                .FeedModule:has(.nicheExplorer),
                .FeedModule[data-feed-module-type="trending-niches"],
                .FeedModule[data-feed-module-type="suggested-niches"],
                .FeedModule[data-feed-module-type="trending-creators"],
                .FeedModule[data-feed-module-type="suggested-creators"],
                .FeedModule[data-feed-module-type="only-fans"],
                .FeedModule[data-feed-module-type="live-cam"],
                .FeedModule[data-feed-module-type="boost"] {
                    display: none !important;
                }

                /* Sidebar: OnlyFans Creators (Desktop) */
                .OnlyFansCreatorsSidebar {
                    visibility: hidden !important;
                }
            `;

        static POPUP_TEXT_RULES = [
            ['saved', 'collection'],
            ['added', 'collection'],
            ['saved', 'to', 'collections'],
        ];

        static POPUP_CLASS_HINTS = [
            'toast', 'snackbar', 'notification', 'notifier',
            'message', 'alert', 'modal', 'dialog',
            'backdrop', 'overlay', 'sheet',
        ];

        static POPUP_CANDIDATE_SELECTORS = [
            '[role="dialog"]',
            '[role="alert"]',
            '[aria-live]',
            '[class*="toast"]',
            '[class*="snackbar"]',
            '[class*="notification"]',
            '[class*="modal"]',
            '[class*="overlay"]',
            '[id*="toast"]',
            '[id*="snackbar"]',
            '[id*="notification"]',
            '[id*="modal"]',
            '[id*="overlay"]',
        ];

        static MIN_POPUP_Z_INDEX = 1000;

        _elementLooksLikePopup(el) {
            if (!(el instanceof HTMLElement)) return false;
            if (el.dataset.rgextPopupBlocked === '1') return false;

            const cls = (el.className || '').toString();
            const id = el.id || '';
            if (cls.includes(APPID) || id.includes(APPID)) return false;

            const rect = el.getBoundingClientRect();
            if (rect.width < 80 || rect.height < 30) return false;

            const style = getComputedStyle(el);
            const isOverlayish = style.position === 'fixed' || style.position === 'sticky';
            if (!isOverlayish) return false;

            const z = Number.parseInt(style.zIndex, 10);
            const highZ = Number.isFinite(z) ? z >= AnnoyanceManager.MIN_POPUP_Z_INDEX : false;

            const idLower = id.toLowerCase();
            const clsLower = cls.toLowerCase();
            const hinted = AnnoyanceManager.POPUP_CLASS_HINTS.some(h => idLower.includes(h) || clsLower.includes(h));

            const text = (el.innerText || '').replace(/\s+/g, ' ').trim().toLowerCase();
            const matchesTextRule = AnnoyanceManager.POPUP_TEXT_RULES.some(parts =>
                parts.every(p => text.includes(p))
            );

            if (matchesTextRule) return true;
            return highZ && hinted;
        }

        _hidePopupElement(el) {
            if (!(el instanceof HTMLElement)) return;
            if (el.dataset.rgextPopupBlocked === '1') return;

            el.dataset.rgextPopupBlocked = '1';
            el.style.setProperty('display', 'none', 'important');
            el.style.setProperty('visibility', 'hidden', 'important');
            el.style.setProperty('pointer-events', 'none', 'important');

            document.documentElement.style.removeProperty('overflow');
            document.body.style.removeProperty('overflow');
        }

        _scanForPopups(root) {
            if (!(root instanceof HTMLElement)) return;

            if (this._elementLooksLikePopup(root)) {
                this._hidePopupElement(root);
            }

            const selector = AnnoyanceManager.POPUP_CANDIDATE_SELECTORS.join(',');
            const candidates = root.querySelectorAll(selector);

            for (const el of candidates) {
                if (this._elementLooksLikePopup(el)) {
                    this._hidePopupElement(el);
                }
            }
        }

        startPopupBlocker() {
            const observer = new MutationObserver((mutations) => {
                for (const mutation of mutations) {
                    for (const node of mutation.addedNodes) {
                        if (node instanceof HTMLElement) {
                            this._scanForPopups(node);
                        }
                    }
                }
            });

            observer.observe(document.documentElement, {
                childList: true,
                subtree: true,
            });

            const initialScan = () => {
                this._scanForPopups(document.body || document.documentElement);
            };

            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', initialScan, { once: true });
            } else {
                initialScan();
            }
        }

        injectStyles() {
            const styleElement = document.createElement('style');
            styleElement.type = 'text/css';
            styleElement.textContent = AnnoyanceManager.STYLES;
            (document.head || document.documentElement).appendChild(styleElement);
        }

        removeElements(sentinel) {
            const adHider = (adElement) => {
                const adContainer = adElement.closest('.GifPreview.VisibleOnly');
                if (adContainer) {
                    adContainer.style.setProperty('display', 'none', 'important');
                }
            };

            sentinel.on('.StreamateCameraDispatcher', adHider);

            sentinel.on('.metaInfo_isBoosted', (infoElement) => {
                const container = infoElement.closest('.GifPreview');
                if (container) {
                    container.style.setProperty('display', 'none', 'important');
                }
            });
        }
    }

    class Sentinel {
        constructor(prefix) {
            if (!prefix) {
                throw new Error('[Sentinel] "prefix" argument is required to avoid CSS conflicts.');
            }

            const globalScope = window;
            globalScope.__global_sentinel_instances__ = globalScope.__global_sentinel_instances__ || {};
            if (globalScope.__global_sentinel_instances__[prefix]) {
                return globalScope.__global_sentinel_instances__[prefix];
            }

            this.animationName = `${prefix}-global-sentinel-animation`;
            this.styleId = `${prefix}-sentinel-global-rules`;
            this.listeners = new Map();
            this.rules = new Set();
            this.styleElement = null;
            this.sheet = null;
            this.pendingRules = [];
            this.ruleSelectors = new WeakMap();

            this._injectStyleElement();
            document.addEventListener('animationstart', this._handleAnimationStart.bind(this), true);

            globalScope.__global_sentinel_instances__[prefix] = this;
        }

        _injectStyleElement() {
            this.styleElement = document.getElementById(this.styleId);

            if (this.styleElement instanceof HTMLStyleElement) {
                this.sheet = this.styleElement.sheet;
                return;
            }

            this.styleElement = document.createElement('style');
            this.styleElement.id = this.styleId;

            const target = document.head || document.documentElement;

            const initSheet = () => {
                if (this.styleElement instanceof HTMLStyleElement) {
                    this.sheet = this.styleElement.sheet;
                    try {
                        const keyframes = `@keyframes ${this.animationName} { from { transform: none; } to { transform: none; } }`;
                        this.sheet.insertRule(keyframes, 0);
                    } catch (e) {}
                    this._flushPendingRules();
                }
            };

            if (target) {
                target.appendChild(this.styleElement);
                initSheet();
            } else {
                const observer = new MutationObserver(() => {
                    const retryTarget = document.head || document.documentElement;
                    if (retryTarget) {
                        observer.disconnect();
                        retryTarget.appendChild(this.styleElement);
                        initSheet();
                    }
                });
                observer.observe(document, { childList: true });
            }
        }

        _flushPendingRules() {
            if (!this.sheet || this.pendingRules.length === 0) return;

            const rulesToInsert = [...this.pendingRules];
            this.pendingRules = [];

            rulesToInsert.forEach((selector) => {
                this._insertRule(selector);
            });
        }

        _insertRule(selector) {
            try {
                const index = this.sheet.cssRules.length;
                const ruleText = `${selector} { animation-duration: 0.001s; animation-name: ${this.animationName}; }`;
                this.sheet.insertRule(ruleText, index);

                const insertedRule = this.sheet.cssRules[index];
                if (insertedRule) {
                    this.ruleSelectors.set(insertedRule, selector);
                }
            } catch (e) {}
        }

        _handleAnimationStart(event) {
            if (event.animationName !== this.animationName) return;

            const target = event.target;
            if (!(target instanceof Element)) {
                return;
            }

            for (const [selector, callbacks] of this.listeners.entries()) {
                if (target.matches(selector)) {
                    [...callbacks].forEach((cb) => cb(target));
                }
            }
        }

        on(selector, callback) {
            if (!this.listeners.has(selector)) {
                this.listeners.set(selector, []);
            }
            this.listeners.get(selector).push(callback);

            if (this.rules.has(selector)) return;

            this.rules.add(selector);

            if (this.sheet) {
                this._insertRule(selector);
            } else {
                this.pendingRules.push(selector);
            }
        }
    }

    // =================================================================================
    // SECTION: Initialize
    // =================================================================================

    function init() {
        // Add styles
        if (typeof GM_addStyle !== 'undefined') {
            GM_addStyle(styles);
        } else {
            const styleEl = document.createElement('style');
            styleEl.textContent = styles;
            document.head.appendChild(styleEl);
        }

        // Inject page script for API interception
        injectPageScript();
        listenForApiData();

        const annoyanceManager = new AnnoyanceManager();
        const sentinel = new Sentinel(APPID);

        // Wait for DOM
        const setup = async () => {
            await loadSettings();
            createToastContainer();
            createPanel();
            applySettingsToPanel();
            observeDOM();
            annoyanceManager.injectStyles();
            annoyanceManager.startPopupBlocker();
            annoyanceManager.removeElements(sentinel);
            scheduleUpdateUserIdDisplay();

            // Watch for URL changes
            let lastUrl = location.href;
            const urlObserver = new MutationObserver(() => {
                if (location.href !== lastUrl) {
                    lastUrl = location.href;
                    if (settings.clearOnNav) {
                        clearUrls();
                    }
                    if (settings.blockMedia) {
                        enableMediaBlock();
                    }
                    scheduleUpdateUserIdDisplay();
                }
            });
            urlObserver.observe(document.body, { childList: true, subtree: true });

            window.addEventListener('popstate', () => {
                if (settings.clearOnNav) {
                    clearUrls();
                }
                if (settings.blockMedia) {
                    enableMediaBlock();
                }
                scheduleUpdateUserIdDisplay();
            });

            // Auto-scan on manual scroll
            let scrollTimeout;
            window.addEventListener('scroll', () => {
                if (isAutomatedMode) return;
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(extractWatchUrls, 300);
            });
        };

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                setup().catch((e) => console.error('[RGEXT] Setup failed:', e));
            });
        } else {
            setup().catch((e) => console.error('[RGEXT] Setup failed:', e));
        }
    }

    init();
})();