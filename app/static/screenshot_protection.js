/**
 * ============================================
 * Screenshot Protection Module
 * ============================================
 * 
 * Comprehensive client-side protection against screenshots and screen recording.
 * Works on both localhost and Vercel production environments.
 * 
 * Features:
 * - Keyboard shortcut detection (Print Screen, Ctrl+Shift+S, Cmd+Shift+3/4)
 * - Screen recording heuristics (visibility changes, focus loss patterns)
 * - Content blur/overlay on detection
 * - Server-side event logging for audit trail
 * - Per-user and session-based watermarking
 * - Graceful degradation for older browsers
 */

const ScreenshotProtection = (function() {
    'use strict';
    
    // Configuration
    const config = {
        logToServer: true,
        serverEndpoint: '/api/security/log-attempt',
        blurOnDetection: true,
        showWarningModal: true,
        watermarkEnabled: true,
        watermarkText: 'CONFIDENTIAL',
        detectionDebounceMs: 100,
        recordingThreshold: 3, // Number of rapid events before considering it recording
    };
    
    // State tracking
    const state = {
        initialized: false,
        shortcutAttemptsInWindow: 0,
        lastShortcutAttempt: 0,
        recordingLikelihood: 0,
        blurActive: false,
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
        
        console.log('[ScreenshotProtection] Initializing protection module');
        
        setupKeyboardDetection();
        setupRecordingDetection();
        setupDataProtection();
        setupWatermarking();
        
        state.initialized = true;
        console.log('[ScreenshotProtection] Initialization complete');
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
            handleDetection(eventType, 'keyboard');
            e.preventDefault();
            e.stopPropagation();
        }
    }
    
    // ============================================
    // Screen Recording Heuristics
    // ============================================
    
    function setupRecordingDetection() {
        // Monitor visibility changes (tab visibility)
        document.addEventListener('visibilitychange', handleVisibilityChange);
        
        // Monitor window focus/blur
        window.addEventListener('blur', handleWindowBlur);
        window.addEventListener('focus', handleWindowFocus);
        
        // Monitor frame rate drops (CPU load heuristic for recording)
        startFrameRateMonitoring();
    }
    
    let visibilityChangeEvents = [];
    function handleVisibilityChange() {
        const now = Date.now();
        visibilityChangeEvents.push(now);
        
        // Keep only last 10 events within 5 second window
        visibilityChangeEvents = visibilityChangeEvents.filter(t => now - t < 5000);
        
        // If more than 5 visibility changes in 5 seconds, likely recording
        if (visibilityChangeEvents.length > 5) {
            handleDetection('visibility_spam', 'recording_heuristic');
            visibilityChangeEvents = [];
        }
    }
    
    let focusLossEvents = [];
    function handleWindowBlur() {
        const now = Date.now();
        focusLossEvents.push(now);
        
        // Keep only events within last 3 seconds
        focusLossEvents = focusLossEvents.filter(t => now - t < 3000);
        
        // More than 3 rapid focus losses suggest recording
        if (focusLossEvents.length > 3) {
            handleDetection('focus_loss_spam', 'recording_heuristic');
            focusLossEvents = [];
        }
    }
    
    function handleWindowFocus() {
        // Reset counters on focus regain
        focusLossEvents = [];
    }
    
    // Frame rate monitoring (CPU load heuristic)
    function startFrameRateMonitoring() {
        let frameCount = 0;
        let lastTime = Date.now();
        let lowFrameRateCount = 0;
        
        function countFrames() {
            const now = Date.now();
            const elapsed = now - lastTime;
            
            if (elapsed > 1000) {
                // FPS calculation
                const fps = Math.round((frameCount / elapsed) * 1000);
                
                // If FPS drops below 20, likely recording
                if (fps < 20 && fps > 0) {
                    lowFrameRateCount++;
                    if (lowFrameRateCount > 5) {
                        // Only log once to avoid spam
                        console.log('[ScreenshotProtection] Low FPS detected:', fps);
                        logEvent('low_frame_rate', `FPS: ${fps}`);
                    }
                } else {
                    lowFrameRateCount = Math.max(0, lowFrameRateCount - 1);
                }
                
                frameCount = 0;
                lastTime = now;
            }
            frameCount++;
            requestAnimationFrame(countFrames);
        }
        
        requestAnimationFrame(countFrames);
    }
    
    // ============================================
    // Data Protection (Copy/Paste/Select)
    // ============================================
    
    function setupDataProtection() {
        // Prevent copy on sensitive elements
        document.addEventListener('copy', handleCopyEvent);
        
        // Prevent paste on restricted elements
        document.addEventListener('paste', handlePasteEvent);
        
        // Prevent text selection on sensitive elements
        document.addEventListener('selectstart', handleSelectEvent);
        
        // Prevent drag operations
        document.addEventListener('dragstart', handleDragEvent);
    }
    
    function handleCopyEvent(e) {
        const target = e.target.closest('.sensitive-data, [data-protect="copy"]');
        if (target) {
            e.preventDefault();
            e.clipboardData.setData('text/plain', '[REDACTED - SENSITIVE INFORMATION]');
            logEvent('copy_attempted', target.id || 'unknown');
        }
    }
    
    function handlePasteEvent(e) {
        const target = e.target.closest('[data-protect="paste"]');
        if (target) {
            e.preventDefault();
            logEvent('paste_attempted', target.id || 'unknown');
        }
    }
    
    function handleSelectEvent(e) {
        const target = e.target.closest('.sensitive-data, [data-protect="select"]');
        if (target) {
            e.preventDefault();
            logEvent('select_attempted', target.id || 'unknown');
        }
    }
    
    function handleDragEvent(e) {
        const target = e.target.closest('.sensitive-data, [data-protect="drag"]');
        if (target) {
            e.preventDefault();
            logEvent('drag_attempted', target.id || 'unknown');
        }
    }
    
    // ============================================
    // Watermarking System
    // ============================================
    
    function setupWatermarking() {
        if (!config.watermarkEnabled) return;
        
        // Get session/user identifier
        const sessionId = getSessionId();
        const watermarkText = `${config.watermarkText} • Session: ${sessionId} • ${new Date().toLocaleTimeString()}`;
        
        // Add watermark to sensitive elements
        addWatermarksToElements(watermarkText);
        
        // Re-apply watermark if DOM changes (MutationObserver)
        observeDOM(watermarkText);
    }
    
    function getSessionId() {
        // Try to extract from JWT cookie
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            if (cookie.includes('hr_session') || cookie.includes('employee_session')) {
                return cookie.split('=')[1].substring(0, 8).toUpperCase();
            }
        }
        return Math.random().toString(36).substring(2, 8).toUpperCase();
    }
    
    function addWatermarksToElements(watermarkText) {
        const sensitiveElements = document.querySelectorAll(
            '.id-card-preview, .sensitive-data, [data-watermark="true"], .employee-data'
        );
        
        sensitiveElements.forEach(element => {
            if (!element.hasAttribute('data-watermarked')) {
                element.setAttribute('data-watermark-text', watermarkText);
                element.setAttribute('data-watermarked', 'true');
                element.style.position = 'relative';
            }
        });
    }
    
    function observeDOM(watermarkText) {
        const observer = new MutationObserver((mutations) => {
            // Re-apply watermarks to new sensitive elements
            addWatermarksToElements(watermarkText);
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: false,
            characterData: false,
        });
    }
    
    // ============================================
    // Detection Handler (Main Trigger)
    // ============================================
    
    function handleDetection(detectionType, source = 'unknown') {
        const now = Date.now();
        
        console.warn(`[ScreenshotProtection] DETECTION: ${detectionType} from ${source}`);
        
        // Debounce multiple rapid detections
        if (now - state.lastShortcutAttempt < config.detectionDebounceMs) {
            return;
        }
        state.lastShortcutAttempt = now;
        
        // Log the event
        logEvent(detectionType, source);
        
        // Show warning modal
        if (config.showWarningModal) {
            showWarningModal(detectionType);
        }
        
        // Blur sensitive content
        if (config.blurOnDetection) {
            blurSensitiveContent();
        }
        
        // Increment recording likelihood
        state.recordingLikelihood++;
        
        // Auto-clear blur after 5 seconds if no further detections
        setTimeout(() => {
            state.recordingLikelihood = Math.max(0, state.recordingLikelihood - 1);
            if (state.recordingLikelihood === 0 && state.blurActive) {
                unblurSensitiveContent();
            }
        }, 5000);
    }
    
    // ============================================
    // Visual Response to Detection
    // ============================================
    
    function blurSensitiveContent() {
        if (state.blurActive) return;
        state.blurActive = true;
        
        const sensitiveElements = document.querySelectorAll(
            '.id-card-preview, .sensitive-data, [data-protect="blur"], .employee-data'
        );
        
        sensitiveElements.forEach(el => {
            el.style.filter = 'blur(8px)';
            el.style.opacity = '0.5';
            el.style.pointerEvents = 'none';
            el.classList.add('recording-detected');
        });
        
        // Darken entire page
        document.body.style.backgroundColor = '#f0f0f0';
        
        console.log('[ScreenshotProtection] Content blurred due to detection');
    }
    
    function unblurSensitiveContent() {
        state.blurActive = false;
        
        const sensitiveElements = document.querySelectorAll('.recording-detected');
        sensitiveElements.forEach(el => {
            el.style.filter = 'none';
            el.style.opacity = '1';
            el.style.pointerEvents = 'auto';
            el.classList.remove('recording-detected');
        });
        
        console.log('[ScreenshotProtection] Content unblurred');
    }
    
    function showWarningModal(detectionType) {
        const overlay = document.getElementById('screenshotOverlay');
        if (overlay) {
            overlay.classList.add('active');
            console.log('[ScreenshotProtection] Warning modal shown');
            
            // Auto-hide after 10 seconds
            setTimeout(() => {
                overlay.classList.remove('active');
            }, 10000);
        }
    }
    
    // ============================================
    // Server-Side Event Logging
    // ============================================
    
    function logEvent(eventType, details = '') {
        if (!config.logToServer) {
            console.log('[ScreenshotProtection] Event logged locally:', eventType, details);
            return;
        }
        
        const payload = {
            event_type: eventType,
            details: details,
            timestamp: new Date().toISOString(),
            url: window.location.href,
            user_agent: navigator.userAgent,
            screen_resolution: `${window.screen.width}x${window.screen.height}`,
        };
        
        // Use fetch with keepalive to ensure delivery even if page unloads
        fetch(config.serverEndpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            keepalive: true, // Ensures request completes even on page close
        }).catch(err => {
            console.log('[ScreenshotProtection] Event logging failed:', err);
        });
    }
    
    // ============================================
    // Public API
    // ============================================
    
    return {
        init: init,
        logEvent: logEvent,
        blur: blurSensitiveContent,
        unblur: unblurSensitiveContent,
        getState: () => ({ ...state }),
        getConfig: () => ({ ...config }),
    };
})();

// Auto-initialize if data attribute present on body
if (document.body.getAttribute('data-screenshot-protection') === 'true') {
    document.addEventListener('DOMContentLoaded', () => {
        ScreenshotProtection.init();
    });
}
