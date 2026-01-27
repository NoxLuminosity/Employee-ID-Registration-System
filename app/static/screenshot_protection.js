/**
 * ============================================
 * Screenshot Protection Module v2.0
 * ============================================
 * 
 * Web-safe client-side protection that discourages screenshots and screen capture
 * by obscuring content when the user is not actively viewing the page.
 * Works on both localhost and Vercel production environments.
 * 
 * Features:
 * - Full-screen black overlay when tab loses visibility (Page Visibility API)
 * - Full-screen overlay when browser window loses focus
 * - Dynamic watermark with user identifier and timestamp
 * - Keyboard shortcut detection for screenshot attempts
 * - Server-side event logging for audit trail
 * - Graceful degradation for older browsers
 * 
 * NOTE: This does NOT prevent OS-level screenshots. It only obscures content
 * when the user is not actively engaged with the page.
 */

const ScreenshotProtection = (function() {
    'use strict';
    
    // Configuration
    const config = {
        logToServer: true,
        serverEndpoint: '/api/security/log-attempt',
        showWarningOnKeyboard: true,
        watermarkEnabled: true,
        watermarkText: 'CONFIDENTIAL',
        detectionDebounceMs: 100,
        overlayEnabled: true, // Enable/disable the visibility overlay
        overlayMessage: 'Content hidden for security',
    };
    
    // State tracking
    const state = {
        initialized: false,
        overlayActive: false,
        lastKeyboardAttempt: 0,
        userIdentifier: null,
        watermarkElement: null,
        overlayElement: null,
    };
    
    // ============================================
    // Initialization
    // ============================================
    
    function init(options = {}) {
        // Merge user config with defaults
        Object.assign(config, options);
        
        if (state.initialized) {
            console.log('[ScreenshotProtection] Already initialized');
            return;
        }
        
        console.log('[ScreenshotProtection] Initializing protection module v2.0');
        
        // Store user identifier from options or extract from page
        state.userIdentifier = options.userIdentifier || extractUserIdentifier();
        
        // Create DOM elements for overlay and watermark
        createOverlayElement();
        createWatermarkElement();
        
        // Setup event listeners
        setupVisibilityDetection();
        setupFocusDetection();
        setupKeyboardDetection();
        
        // Start watermark timestamp updates
        startWatermarkUpdates();
        
        state.initialized = true;
        console.log('[ScreenshotProtection] Initialization complete');
        console.log('[ScreenshotProtection] User identifier:', state.userIdentifier);
    }
    
    // ============================================
    // User Identifier Extraction
    // ============================================
    
    function extractUserIdentifier() {
        // Try to get from data attribute on body
        const bodyIdentifier = document.body.dataset.userIdentifier;
        if (bodyIdentifier) return bodyIdentifier;
        
        // Try to get from meta tag
        const metaUser = document.querySelector('meta[name="user-identifier"]');
        if (metaUser) return metaUser.content;
        
        // Try to extract from visible user info on page
        const userNameEl = document.querySelector('.user-name, .username, [data-username]');
        if (userNameEl) return userNameEl.textContent.trim() || userNameEl.dataset.username;
        
        // Try to get from cookie
        const sessionId = getSessionIdFromCookie();
        if (sessionId) return `Session: ${sessionId.substring(0, 8).toUpperCase()}`;
        
        // Fallback to anonymous with random ID
        return `User-${Math.random().toString(36).substring(2, 8).toUpperCase()}`;
    }
    
    function getSessionIdFromCookie() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'hr_session' || name === 'employee_session') {
                return value;
            }
        }
        return null;
    }
    
    // ============================================
    // Overlay Element (Black Screen)
    // ============================================
    
    function createOverlayElement() {
        if (state.overlayElement) return;
        
        const overlay = document.createElement('div');
        overlay.id = 'screenshot-protection-overlay';
        overlay.innerHTML = `
            <div class="spo-content">
                <svg class="spo-icon" width="64" height="64" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 15a3 3 0 100-6 3 3 0 000 6z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <line x1="2" y1="2" x2="22" y2="22" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
                <h2 class="spo-title">${config.overlayMessage}</h2>
                <p class="spo-subtitle">Return to this window to continue viewing</p>
            </div>
        `;
        
        // Apply styles directly to ensure they work
        const style = document.createElement('style');
        style.id = 'screenshot-protection-styles';
        style.textContent = `
            #screenshot-protection-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                width: 100vw;
                height: 100vh;
                background: #000000;
                z-index: 999999;
                display: none;
                align-items: center;
                justify-content: center;
                opacity: 0;
                transition: opacity 0.15s ease;
                pointer-events: all;
            }
            
            #screenshot-protection-overlay.active {
                display: flex;
                opacity: 1;
            }
            
            #screenshot-protection-overlay .spo-content {
                text-align: center;
                color: #ffffff;
                padding: 2rem;
                max-width: 400px;
            }
            
            #screenshot-protection-overlay .spo-icon {
                color: #666666;
                margin-bottom: 1.5rem;
            }
            
            #screenshot-protection-overlay .spo-title {
                font-size: 1.5rem;
                font-weight: 600;
                margin: 0 0 0.5rem 0;
                color: #ffffff;
            }
            
            #screenshot-protection-overlay .spo-subtitle {
                font-size: 0.95rem;
                color: #888888;
                margin: 0;
            }
            
            /* Dynamic Watermark Styles */
            #screenshot-protection-watermark {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                width: 100vw;
                height: 100vh;
                pointer-events: none;
                z-index: 999990;
                overflow: hidden;
                opacity: 0.08;
            }
            
            #screenshot-protection-watermark .watermark-pattern {
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                display: flex;
                flex-wrap: wrap;
                align-content: flex-start;
                transform: rotate(-30deg);
            }
            
            #screenshot-protection-watermark .watermark-item {
                padding: 60px 80px;
                font-size: 14px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-weight: 500;
                color: #000000;
                white-space: nowrap;
                user-select: none;
            }
            
            /* Keyboard shortcut warning modal */
            #screenshot-keyboard-warning {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%) scale(0.9);
                background: #1a1a1a;
                color: #ffffff;
                padding: 2rem 2.5rem;
                border-radius: 12px;
                z-index: 999998;
                text-align: center;
                opacity: 0;
                visibility: hidden;
                transition: all 0.2s ease;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            }
            
            #screenshot-keyboard-warning.active {
                opacity: 1;
                visibility: visible;
                transform: translate(-50%, -50%) scale(1);
            }
            
            #screenshot-keyboard-warning .warning-icon {
                color: #f59e0b;
                margin-bottom: 1rem;
            }
            
            #screenshot-keyboard-warning .warning-title {
                font-size: 1.25rem;
                font-weight: 600;
                margin: 0 0 0.5rem 0;
            }
            
            #screenshot-keyboard-warning .warning-text {
                font-size: 0.9rem;
                color: #888888;
                margin: 0;
            }
        `;
        
        document.head.appendChild(style);
        document.body.appendChild(overlay);
        state.overlayElement = overlay;
        
        console.log('[ScreenshotProtection] Overlay element created');
    }
    
    // ============================================
    // Watermark Element (Semi-transparent overlay with user info)
    // ============================================
    
    function createWatermarkElement() {
        if (!config.watermarkEnabled) return;
        if (state.watermarkElement) return;
        
        const watermark = document.createElement('div');
        watermark.id = 'screenshot-protection-watermark';
        watermark.innerHTML = '<div class="watermark-pattern"></div>';
        
        document.body.appendChild(watermark);
        state.watermarkElement = watermark;
        
        // Initial watermark render
        updateWatermarkContent();
        
        console.log('[ScreenshotProtection] Watermark element created');
    }
    
    function updateWatermarkContent() {
        if (!state.watermarkElement) return;
        
        const pattern = state.watermarkElement.querySelector('.watermark-pattern');
        if (!pattern) return;
        
        const timestamp = new Date().toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
        
        const watermarkText = `${config.watermarkText} • ${state.userIdentifier} • ${timestamp}`;
        
        // Create enough items to cover the rotated area
        let items = '';
        for (let i = 0; i < 100; i++) {
            items += `<span class="watermark-item">${watermarkText}</span>`;
        }
        
        pattern.innerHTML = items;
    }
    
    function startWatermarkUpdates() {
        if (!config.watermarkEnabled) return;
        
        // Update watermark every 30 seconds to keep timestamp current
        setInterval(() => {
            updateWatermarkContent();
        }, 30000);
    }
    
    // ============================================
    // Keyboard Shortcut Detection
    // ============================================
    
    function setupKeyboardDetection() {
        document.addEventListener('keydown', handleKeyboardEvent, true);
    }
    
    function handleKeyboardEvent(e) {
        let detected = false;
        let eventType = null;
        
        // Windows/Linux: Print Screen (key code 44)
        if (e.key === 'PrintScreen' || e.keyCode === 44) {
            detected = true;
            eventType = 'printscreen_key';
        }
        
        // Ctrl+Shift+S (Windows Screenshot Tool)
        else if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 's' || e.key === 'S')) {
            detected = true;
            eventType = 'ctrl_shift_s';
        }
        
        // Cmd+Shift+3 (Mac Full Screenshot)
        else if (e.metaKey && e.shiftKey && e.key === '3') {
            detected = true;
            eventType = 'mac_cmd_shift_3';
        }
        
        // Cmd+Shift+4 (Mac Region Screenshot)
        else if (e.metaKey && e.shiftKey && e.key === '4') {
            detected = true;
            eventType = 'mac_cmd_shift_4';
        }
        
        // Cmd+Shift+5 (Mac Screenshot UI - newer Macs)
        else if (e.metaKey && e.shiftKey && e.key === '5') {
            detected = true;
            eventType = 'mac_cmd_shift_5';
        }
        
        // Windows+Print Screen (Windows 10+ Screenshot tool)
        else if (e.metaKey && e.key === 'PrintScreen') {
            detected = true;
            eventType = 'windows_printscreen';
        }
        
        if (detected) {
            handleKeyboardDetection(eventType);
            e.preventDefault();
            e.stopPropagation();
        }
    }
    
    // ============================================
    // Page Visibility Detection (Tab visibility)
    // ============================================
    
    function setupVisibilityDetection() {
        document.addEventListener('visibilitychange', handleVisibilityChange);
        console.log('[ScreenshotProtection] Page Visibility API detection enabled');
    }
    
    function handleVisibilityChange() {
        if (document.visibilityState === 'hidden') {
            // Tab is hidden (user switched tabs or minimized)
            showOverlay('visibility');
            logEvent('tab_hidden', 'visibility_change');
            console.log('[ScreenshotProtection] Tab hidden - overlay activated');
        } else if (document.visibilityState === 'visible') {
            // Tab is visible again
            hideOverlay('visibility');
            console.log('[ScreenshotProtection] Tab visible - overlay deactivated');
        }
    }
    
    // ============================================
    // Window Focus Detection
    // ============================================
    
    function setupFocusDetection() {
        window.addEventListener('blur', handleWindowBlur);
        window.addEventListener('focus', handleWindowFocus);
        console.log('[ScreenshotProtection] Window focus detection enabled');
    }
    
    function handleWindowBlur() {
        // Window lost focus (user clicked outside browser)
        showOverlay('blur');
        logEvent('window_blur', 'focus_change');
        console.log('[ScreenshotProtection] Window blur - overlay activated');
    }
    
    function handleWindowFocus() {
        // Window regained focus
        hideOverlay('focus');
        console.log('[ScreenshotProtection] Window focus - overlay deactivated');
    }
    
    // ============================================
    // Overlay Control
    // ============================================
    
    function showOverlay(reason) {
        if (!config.overlayEnabled) return;
        if (!state.overlayElement) return;
        
        state.overlayActive = true;
        state.overlayElement.classList.add('active');
        
        // Update watermark when overlay shows
        updateWatermarkContent();
    }
    
    function hideOverlay(reason) {
        if (!state.overlayElement) return;
        
        // Only hide if tab is visible AND window has focus
        // This prevents flicker when both events fire
        if (document.visibilityState === 'visible' && document.hasFocus()) {
            state.overlayActive = false;
            state.overlayElement.classList.remove('active');
        }
    }
    
    // ============================================
    // Keyboard Detection Handler
    // ============================================
    
    function handleKeyboardDetection(eventType) {
        const now = Date.now();
        
        // Debounce
        if (now - state.lastKeyboardAttempt < config.detectionDebounceMs) {
            return;
        }
        state.lastKeyboardAttempt = now;
        
        console.warn(`[ScreenshotProtection] Keyboard shortcut detected: ${eventType}`);
        
        // Log the event
        logEvent(eventType, 'keyboard_shortcut');
        
        // Show keyboard warning (brief, non-blocking)
        if (config.showWarningOnKeyboard) {
            showKeyboardWarning();
        }
    }
    
    function showKeyboardWarning() {
        // Create warning element if it doesn't exist
        let warning = document.getElementById('screenshot-keyboard-warning');
        if (!warning) {
            warning = document.createElement('div');
            warning.id = 'screenshot-keyboard-warning';
            warning.innerHTML = `
                <svg class="warning-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 9v4M12 17h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <h3 class="warning-title">Screenshot Shortcut Detected</h3>
                <p class="warning-text">This action has been logged for security purposes</p>
            `;
            document.body.appendChild(warning);
        }
        
        // Show warning
        warning.classList.add('active');
        
        // Hide after 3 seconds
        setTimeout(() => {
            warning.classList.remove('active');
        }, 3000);
    }
    
    // ============================================
    // Server-Side Event Logging
    // ============================================
    
    function logEvent(eventType, details = '') {
        const payload = {
            event_type: eventType,
            details: details,
            timestamp: new Date().toISOString(),
            url: window.location.href,
            user_agent: navigator.userAgent,
            screen_resolution: `${window.screen.width}x${window.screen.height}`,
            user_identifier: state.userIdentifier,
        };
        
        if (!config.logToServer) {
            console.log('[ScreenshotProtection] Event logged locally:', payload);
            return;
        }
        
        // Use fetch with keepalive to ensure delivery even if page unloads
        fetch(config.serverEndpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            keepalive: true,
        }).catch(err => {
            // Silently fail - don't break the page for logging errors
            console.log('[ScreenshotProtection] Event logging failed:', err);
        });
    }
    
    // ============================================
    // Public API
    // ============================================
    
    return {
        init: init,
        logEvent: logEvent,
        showOverlay: () => showOverlay('manual'),
        hideOverlay: () => hideOverlay('manual'),
        updateWatermark: updateWatermarkContent,
        getState: () => ({ ...state }),
        getConfig: () => ({ ...config }),
        setUserIdentifier: (identifier) => {
            state.userIdentifier = identifier;
            updateWatermarkContent();
        },
    };
})();

// Auto-initialize when DOM is ready if data attribute is present
document.addEventListener('DOMContentLoaded', () => {
    // Check for auto-init attribute
    const autoInit = document.body.getAttribute('data-screenshot-protection');
    if (autoInit === 'true' || autoInit === 'auto') {
        // Get user identifier from body attribute if present
        const userIdentifier = document.body.dataset.userIdentifier || null;
        ScreenshotProtection.init({ userIdentifier });
    }
});

// Export for module systems (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ScreenshotProtection;
}
