/**
 * ID Gallery JavaScript
 * Handles gallery display and ID card downloads
 * Shows only IDs generated from the ID Preview on Employee portal
 */

// ============================================
// State Management
// ============================================
const galleryState = {
  employees: [],
  filteredEmployees: [],
  isLoading: true,
  currentEmployee: null,
  lastFetchTime: null,
  autoDownloadId: null,
  autoDownloadAttempted: false
};

// If navigated from Dashboard "Download ID", auto-trigger a download once data loads.
try {
  const params = new URLSearchParams(window.location.search);
  const downloadParam = params.get('download');
  if (downloadParam) {
    const parsed = Number(downloadParam);
    if (Number.isFinite(parsed)) {
      galleryState.autoDownloadId = parsed;
    }
  }
} catch (e) {
  // no-op
}

function maybeAutoDownloadFromQuery() {
  if (galleryState.autoDownloadAttempted) return;
  if (!galleryState.autoDownloadId) return;
  galleryState.autoDownloadAttempted = true;

  // Ensure libraries exist
  if (typeof window.html2canvas === 'undefined' || !window.jspdf) {
    showToast('PDF tools not loaded. Please refresh and try again.', 'error');
    return;
  }

  const emp = galleryState.employees.find(e => e.id === galleryState.autoDownloadId);
  if (!emp) {
    showToast('Employee not found in gallery yet.', 'error');
    return;
  }

  // Remove the query param so refresh doesn't re-download
  try {
    const url = new URL(window.location.href);
    url.searchParams.delete('download');
    window.history.replaceState({}, document.title, url.pathname + url.search);
  } catch (e) {
    // no-op
  }

  downloadIDPdf(emp);
}

// ============================================
// PDF Export Configuration - ID Card Dimensions
// ============================================
// Preview Dimensions: 512px × 800px (97% scale display)
// Final PDF: 2.13" width × 3.33" height at 300 DPI
// Aspect Ratio: 2.13:3.33 (locked)
const PDF_CONFIG = {
  // Preview canvas dimensions (pixels)
  PREVIEW_WIDTH_PX: 512,
  PREVIEW_HEIGHT_PX: 800,
  DISPLAY_SCALE: 0.97,  // 97% scale factor
  
  // Final dimensions in inches
  WIDTH_INCHES: 2.13,
  HEIGHT_INCHES: 3.33,  // 3.43" × 0.97 = 3.3271" ≈ 3.33"
  
  // Original design reference
  ORIGINAL_HEIGHT_INCHES: 3.43,
  SCALE_FACTOR: 0.97,
  
  // Print quality DPI
  PRINT_DPI: 300,
  SCREEN_DPI: 96,
  
  // Calculated dimensions in mm (for jsPDF)
  get WIDTH_MM() { return this.WIDTH_INCHES * 25.4; },  // 54.102mm
  get HEIGHT_MM() { return this.HEIGHT_INCHES * 25.4; }, // 84.582mm
  
  // Pixel dimensions at 300 DPI for rendering
  get RENDER_WIDTH_PX() { return Math.round(this.WIDTH_INCHES * this.PRINT_DPI); },  // 639px
  get RENDER_HEIGHT_PX() { return Math.round(this.HEIGHT_INCHES * this.PRINT_DPI); }, // 999px
  
  // html2canvas scale factor (DPI ratio)
  get CANVAS_SCALE() { return this.PRINT_DPI / this.SCREEN_DPI; }  // ~3.125
};

// Cache settings - MUST match dashboard.js for shared cache
// VERCEL FIX: Use shared cache key with dashboard so both pages see the same data
const GALLERY_CACHE_KEY = 'hrEmployeeDataCache';  // Shared with dashboard.js
const GALLERY_CACHE_DURATION_MS = 300000; // 5 minutes - matches dashboard
const GALLERY_CACHE_MAX_AGE_MS = 3600000; // 1 hour - matches dashboard

// Load cached employee data from sessionStorage
function loadGalleryCachedData() {
  try {
    const cached = sessionStorage.getItem(GALLERY_CACHE_KEY);
    if (cached) {
      const { employees, timestamp } = JSON.parse(cached);
      const age = Date.now() - timestamp;
      
      // Use cache if within normal duration
      if (age < GALLERY_CACHE_DURATION_MS && employees && employees.length > 0) {
        console.log('Gallery: Using cached data, age:', Math.round(age/1000), 'seconds');
        return employees;
      }
      
      // VERCEL FIX: For stale but not expired cache, still return it for immediate display
      if (age < GALLERY_CACHE_MAX_AGE_MS && employees && employees.length > 0) {
        console.log('Gallery: Using stale cached data for immediate display, age:', Math.round(age/1000), 'seconds');
        return employees;
      }
    }
  } catch (e) {
    console.warn('Gallery: Cache read error', e);
  }
  return null;
}

// Save employee data to sessionStorage cache
function saveGalleryCachedData(employees) {
  try {
    sessionStorage.setItem(GALLERY_CACHE_KEY, JSON.stringify({
      employees,
      timestamp: Date.now()
    }));
  } catch (e) {
    console.warn('Gallery: Cache write error', e);
  }
}

// ============================================
// DOM Elements (initialized after DOM loads)
// ============================================
let elements = {};

// ============================================
// Initialization
// ============================================
document.addEventListener('DOMContentLoaded', () => {
  // Initialize elements after DOM is fully loaded
  elements = {
    loadingState: document.getElementById('loadingState'),
    gallerySection: document.getElementById('gallerySection'),
    galleryGrid: document.getElementById('galleryGrid'),
    emptyState: document.getElementById('emptyState'),
    searchInput: document.getElementById('searchInput'),
    positionFilter: document.getElementById('positionFilter'),
    totalApproved: document.getElementById('totalApproved'),
    totalCompleted: document.getElementById('totalCompleted'),
    previewModal: document.getElementById('previewModal'),
    modalBody: document.getElementById('modalBody'),
    closeModal: document.getElementById('closeModal'),
    downloadBtn: document.getElementById('downloadBtn'),
    downloadAllBtn: document.getElementById('downloadAllBtn'),
    toast: document.getElementById('toast'),
    toastMessage: document.getElementById('toastMessage')
  };
  
  console.log('Gallery DOM elements initialized:', Object.keys(elements).filter(k => elements[k] !== null));
  
  initEventListeners();
  fetchGalleryData();
});

function initEventListeners() {
  // Search and filter - add null checks
  if (elements.searchInput) {
    elements.searchInput.addEventListener('input', debounce(filterGallery, 300));
  }
  if (elements.positionFilter) {
    elements.positionFilter.addEventListener('change', filterGallery);
  }

  // Modal - add null checks
  if (elements.closeModal) {
    elements.closeModal.addEventListener('click', closePreviewModal);
  }
  if (elements.previewModal) {
    elements.previewModal.addEventListener('click', (e) => {
      if (e.target === elements.previewModal) closePreviewModal();
    });
  }

  if (elements.downloadBtn) {
    elements.downloadBtn.addEventListener('click', () => {
      if (galleryState.currentEmployee) {
        downloadIDPdf(galleryState.currentEmployee);
      }
    });
  }

  // Download All button
  if (elements.downloadAllBtn) {
    elements.downloadAllBtn.addEventListener('click', downloadAllPdfs);
  }

  // Escape key to close modal
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closePreviewModal();
  });
}

// ============================================
// Data Fetching
// ============================================
async function fetchGalleryData(forceRefresh = false, retryCount = 0) {
  const MAX_RETRIES = 2;  // VERCEL FIX: Retry on cold start timeouts
  
  console.log('fetchGalleryData: Starting data fetch... (attempt', retryCount + 1, ')');
  console.log('fetchGalleryData: Current URL:', window.location.href);
  
  // VERCEL FIX: Try to use cached data first to prevent data loss on navigation
  if (!forceRefresh) {
    const cachedData = loadGalleryCachedData();
    if (cachedData) {
      // Filter only approved and completed IDs from cache
      galleryState.employees = cachedData.filter(
        emp => emp.status === 'Approved' || emp.status === 'Completed'
      );
      galleryState.filteredEmployees = [...galleryState.employees];
      galleryState.lastFetchTime = Date.now();
      updateStats();
      renderGallery();
      maybeAutoDownloadFromQuery();
      showLoading(false);
      
      // Show/hide Download All button based on whether there are IDs
      if (elements.downloadAllBtn) {
        elements.downloadAllBtn.style.display = galleryState.employees.length > 0 ? 'flex' : 'none';
      }
      
      // Still fetch fresh data in background to keep cache updated
      fetchGalleryDataBackground();
      return;
    }
  }
  
  showLoading(true);

  // VERCEL FIX: Longer timeout for cold starts, shorter for retries
  const timeoutMs = retryCount === 0 ? 20000 : 15000;  // 20s first attempt, 15s retries
  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    console.log('fetchGalleryData: Request timeout - aborting');
    controller.abort();
  }, timeoutMs);

  try {
    // VERCEL FIX: Include credentials to ensure JWT cookie is sent with request
    // Without this, serverless functions may not receive the authentication cookie
    const apiUrl = '/hr/api/employees';
    console.log('fetchGalleryData: Fetching from', apiUrl);
    
    const response = await fetch(apiUrl, {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
        'Cache-Control': 'no-cache'
      },
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    console.log('fetchGalleryData: Response status:', response.status);
    console.log('fetchGalleryData: Response headers:', Object.fromEntries(response.headers.entries()));
    
    // Handle unauthorized - redirect to login
    if (response.status === 401) {
      console.log('fetchGalleryData: Unauthorized, redirecting to login');
      window.location.href = '/hr/login';
      return;
    }
    
    // Handle other error status codes
    if (!response.ok) {
      const errorText = await response.text();
      console.error('fetchGalleryData: HTTP error', response.status, errorText);
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    
    const data = await response.json();
    console.log('fetchGalleryData: Response data:', data);
    console.log('fetchGalleryData: Success:', data.success);
    console.log('fetchGalleryData: Employee array length:', data.employees?.length);

    if (data.success) {
      // Filter only approved and completed IDs
      const allEmployees = data.employees || [];
      console.log('fetchGalleryData: Total employees:', allEmployees.length);
      
      // VERCEL FIX: Cache all employees data
      saveGalleryCachedData(allEmployees);
      galleryState.lastFetchTime = Date.now();
      
      galleryState.employees = allEmployees.filter(
        emp => emp.status === 'Approved' || emp.status === 'Completed'
      );
      console.log('fetchGalleryData: Filtered employees (Approved/Completed):', galleryState.employees.length);
      
      galleryState.filteredEmployees = [...galleryState.employees];
      updateStats();
      renderGallery();
      maybeAutoDownloadFromQuery();
      
      // Show/hide Download All button based on whether there are IDs
      if (elements.downloadAllBtn) {
        elements.downloadAllBtn.style.display = galleryState.employees.length > 0 ? 'flex' : 'none';
      }
    } else {
      console.error('fetchGalleryData: API returned error:', data.error);
      throw new Error(data.error || 'Failed to fetch data');
    }
  } catch (error) {
    clearTimeout(timeoutId);
    console.error('fetchGalleryData: Error occurred:', error);
    
    // VERCEL FIX: Retry on timeout (cold start recovery)
    if (error.name === 'AbortError' && retryCount < MAX_RETRIES) {
      console.log('fetchGalleryData: Timeout, retrying... (attempt', retryCount + 2, ')');
      showToast('Loading... please wait (server warming up)', 'info');
      // Small delay before retry
      await new Promise(resolve => setTimeout(resolve, 1000));
      return fetchGalleryData(forceRefresh, retryCount + 1);
    }
    
    // VERCEL FIX: Handle abort/timeout gracefully
    if (error.name === 'AbortError') {
      showToast('Request timed out. Please refresh the page.', 'error');
    } else {
      showToast('Failed to load gallery data: ' + error.message, 'error');
    }
    
    // VERCEL FIX: Try to use cached data on error instead of showing empty state
    const cachedData = loadGalleryCachedData();
    if (cachedData && cachedData.length > 0) {
      console.log('Gallery: Using cached data after fetch error');
      galleryState.employees = cachedData.filter(
        emp => emp.status === 'Approved' || emp.status === 'Completed'
      );
      galleryState.filteredEmployees = [...galleryState.employees];
      updateStats();
      renderGallery();
      showToast('Showing cached data. Pull to refresh.', 'warning');
    } else {
      // Only set empty state if no cache available
      galleryState.employees = [];
      galleryState.filteredEmployees = [];
      updateStats();
      renderGallery();
    }
  } finally {
    console.log('fetchGalleryData: Hiding loading state');
    // VERCEL FIX: Always hide loading state, even on error
    showLoading(false);
  }
}

// Background fetch to update cache without blocking UI
async function fetchGalleryDataBackground() {
  try {
    const response = await fetch('/hr/api/employees', {
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
        'Cache-Control': 'no-cache'
      }
    });
    
    if (response.status === 401) return;
    if (!response.ok) return;
    
    const data = await response.json();
    if (data.success && data.employees) {
      const allEmployees = data.employees;
      const filteredNew = allEmployees.filter(
        emp => emp.status === 'Approved' || emp.status === 'Completed'
      );
      
      // Only update if data changed
      if (JSON.stringify(filteredNew) !== JSON.stringify(galleryState.employees)) {
        console.log('Gallery: Background fetch found updated data');
        saveGalleryCachedData(allEmployees);
        galleryState.employees = filteredNew;
        galleryState.filteredEmployees = [...filteredNew];
        galleryState.lastFetchTime = Date.now();
        updateStats();
        renderGallery();
        
        if (elements.downloadAllBtn) {
          elements.downloadAllBtn.style.display = filteredNew.length > 0 ? 'flex' : 'none';
        }
      }
    }
  } catch (e) {
    console.log('Gallery: Background fetch error (non-blocking)', e);
  }
}

// ============================================
// UI Updates
// ============================================
function showLoading(show) {
  console.log('showLoading:', show);
  galleryState.isLoading = show;
  
  // VERCEL FIX: Use try-catch to prevent any DOM errors from blocking UI updates
  try {
    if (elements.loadingState) {
      elements.loadingState.style.display = show ? 'flex' : 'none';
      console.log('showLoading: loadingState display =', elements.loadingState.style.display);
    } else {
      console.warn('showLoading: loadingState element not found');
    }
    
    if (elements.gallerySection) {
      elements.gallerySection.style.display = show ? 'none' : 'block';
      console.log('showLoading: gallerySection display =', elements.gallerySection.style.display);
    } else {
      console.warn('showLoading: gallerySection element not found');
    }
  } catch (e) {
    console.error('showLoading: Error updating UI', e);
  }
}

function updateStats() {
  const approved = galleryState.employees.filter(e => e.status === 'Approved').length;
  const completed = galleryState.employees.filter(e => e.status === 'Completed').length;
  
  if (elements.totalApproved) {
    elements.totalApproved.textContent = approved;
  }
  if (elements.totalCompleted) {
    elements.totalCompleted.textContent = completed;
  }
}

function renderGallery() {
  console.log('renderGallery: Starting render...');
  const employees = galleryState.filteredEmployees;
  console.log('renderGallery: Employee count:', employees.length);

  if (employees.length === 0) {
    console.log('renderGallery: No employees, showing empty state');
    if (elements.galleryGrid) elements.galleryGrid.innerHTML = '';
    if (elements.emptyState) {
      elements.emptyState.style.display = 'flex';
      console.log('renderGallery: emptyState display = flex');
    }
    return;
  }

  if (elements.emptyState) {
    elements.emptyState.style.display = 'none';
    console.log('renderGallery: emptyState display = none');
  }

  const cards = employees.map(emp => {
    const statusClass = emp.status.toLowerCase();

    return `
      <div class="id-gallery-card" data-id="${emp.id}">
        <div class="id-card-image-wrapper" onclick="window.previewID(${emp.id})">
          ${generateIDCardHtml(emp)}
        </div>
        <div class="id-gallery-card-footer">
          <div class="id-card-info-row">
            <span class="id-card-emp-name">${escapeHtml(emp.employee_name)}</span>
            <span class="status-badge ${statusClass}">${emp.status}</span>
          </div>
          <div class="id-card-meta">
            <span>${escapeHtml(emp.id_number)}</span>
            <span>•</span>
            <span>${escapeHtml(emp.location_branch || '-')}</span>
          </div>
          <div class="id-card-actions">
            <button class="btn-preview" onclick="window.previewID(${emp.id})">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                <path d="M8 3C4.5 3 1.7 5.5 1 8c.7 2.5 3.5 5 7 5s6.3-2.5 7-5c-.7-2.5-3.5-5-7-5z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                <circle cx="8" cy="8" r="2" stroke="currentColor" stroke-width="1.5"/>
              </svg>
              Preview
            </button>
            <button class="btn-download" onclick="window.downloadSinglePdf(${emp.id})">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                <path d="M8 2v8M4 6l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 12v2h12v-2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              PDF
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');

  if (elements.galleryGrid) {
    elements.galleryGrid.innerHTML = cards;
  }
}

// Generate the ID card HTML for display - matches the exact design from form.html id-preview-section
function generateIDCardHtml(emp) {
  const idPhotoUrl = emp.nobg_photo_url || emp.new_photo_url || emp.photo_url;
  const photoHasImage = idPhotoUrl ? 'has-image' : '';
  const photoHtml = idPhotoUrl 
    ? `<img src="${idPhotoUrl}" alt="${escapeHtml(emp.employee_name)}" crossorigin="anonymous">`
    : `<span class="id-photo-placeholder">AI Image</span>`;

  const signatureHasImage = emp.signature_url ? 'has-image' : '';
  const signatureHtml = emp.signature_url 
    ? `<img src="${emp.signature_url}" alt="Signature" crossorigin="anonymous">`
    : `<span class="id-signature-placeholder">Signature</span>`;

  // Calculate expiration date (2 years from now)
  const expDate = new Date();
  expDate.setFullYear(expDate.getFullYear() + 2);
  const expDateStr = expDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

  // Get nickname or use first name
  const nickname = emp.id_nickname || emp.employee_name.split(' ')[0];
  
  // Get first name for dynamic back-side URL (lowercase)
  const firstName = emp.employee_name.split(' ')[0] || '';
  const firstNameLower = firstName.toLowerCase();
  const backDynamicUrl = `www.okpo.com/spm/${firstNameLower}`;
  const frontStaticUrl = 'www.spmadrid.com';

  return `
    <div class="id-card gallery-id-card">
      <!-- Photo Section with Blue Sidebar -->
      <div class="id-card-top">
        <!-- Blue vertical sidebar -->
        <div class="id-sidebar">
          <span class="id-nickname-vertical">${escapeHtml(nickname)}</span>
        </div>

        <!-- Photo area -->
        <div class="id-photo-section">
          <!-- Header with Logo -->
          <div class="id-header">
            <img src="/static/images/SPM%20Logo%201.png" alt="SPM Logo" class="id-logo-image" crossorigin="anonymous">
          </div>
          
          <!-- Photo placeholder with geometric background -->
          <div class="id-photo-container ${photoHasImage}">
            ${photoHtml}
          </div>
        </div>
      </div>

      <!-- Bottom Info Section -->
      <div class="id-card-bottom">
        <div class="id-info-container">
          <!-- Left side - Name, Title, Barcode -->
          <div class="id-info-left">
            <h1 class="id-fullname">${escapeHtml(emp.employee_name)}</h1>
            
            <div class="id-position-dept">
              <span>${escapeHtml(emp.position)}</span>
            </div>

            <!-- Barcode area -->
            <div class="id-barcode-area">
              <div class="id-barcode-placeholder">
                <span>Barcode</span>
              </div>
              <p class="id-number-text">${escapeHtml(emp.id_number)}</p>
            </div>
          </div>

          <!-- Right side - Signature -->
          <div class="id-signature-area ${signatureHasImage}">
            ${signatureHtml}
          </div>
        </div>

        <!-- Website icon and URL -->
        <div class="id-website-strip">
          <p class="id-website-url">${escapeHtml(frontStaticUrl)}</p>
          <svg class="id-globe-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="2" y1="12" x2="22" y2="12"></line>
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
          </svg>
        </div>

        <!-- Expiration Date -->
        <div class="id-expiration">
          <span class="id-exp-label">Expiration Date:</span>
          <span class="id-exp-date">${expDateStr}</span>
        </div>
      </div>
    </div>
  `;
}

// Generate ID Card Backside HTML
function generateIDCardBackHtml(emp) {
  // Get username from nickname or first name
  const nickname = emp.id_nickname || emp.employee_name.split(' ')[0];
  const username = nickname.toLowerCase().replace(/\s+/g, '');
  
  // Get first name for dynamic URL and contact label
  const firstName = emp.employee_name.split(' ')[0] || '';
  const firstNameLower = firstName.toLowerCase();
  const dynamicUrl = `www.okpo.com/spm/${firstNameLower}`;
  const contactLabel = `${firstName}'s Contact`;
  
  // Emergency contact details
  const emergencyName = emp.emergency_name || 'Not provided';
  const emergencyContact = emp.emergency_contact || 'Not provided';
  const emergencyAddress = emp.emergency_address || 'Not provided';

  return `
    <div class="id-card id-card-back gallery-id-card-back">
      <!-- Overlay Pattern -->
      <div class="id-back-overlay"></div>
      
      <!-- Header Section - Logo and Address -->
      <div class="id-back-header">
        <div class="id-back-header-content">
          <div class="id-back-logo-row">
            <img src="/static/images/Logo.png" alt="SPM Logo" class="id-back-spm-logo" crossorigin="anonymous">
          </div>
          <div class="id-back-address">
            17th Floor Chatham House Valero, Cor V.A. Rufino<br>
            St. Lgry, Makati City Metro Manila
          </div>
        </div>
      </div>

      <!-- QR Code Section -->
      <div class="id-back-qr-section">
        <div class="id-back-qr-code">
          <span>QR Code Here</span>
        </div>
        <div class="id-back-vcard-row">
          <div class="id-back-vcard-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
              <circle cx="12" cy="7" r="4"></circle>
            </svg>
          </div>
          <span class="id-back-vcard-label">${escapeHtml(contactLabel)}</span>
        </div>
      </div>

      <!-- Emergency Contact Card -->
      <div class="id-back-emergency-card">
        <div class="id-back-emergency-title">In case of emergency:</div>
        <div class="id-back-emergency-list">
          <!-- Person Name -->
          <div class="id-back-emergency-row">
            <div class="id-back-emergency-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </svg>
            </div>
            <span class="id-back-emergency-value">${escapeHtml(emergencyName)}</span>
          </div>
          <!-- Phone -->
          <div class="id-back-emergency-row">
            <div class="id-back-emergency-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path>
              </svg>
            </div>
            <span class="id-back-emergency-value">${escapeHtml(emergencyContact)}</span>
          </div>
          <!-- Address -->
          <div class="id-back-emergency-row address-row">
            <div class="id-back-emergency-icon address-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
                <polyline points="9 22 9 12 15 12 15 22"></polyline>
              </svg>
            </div>
            <span class="id-back-emergency-value">${escapeHtml(emergencyAddress)}</span>
          </div>
        </div>
      </div>

      <!-- Bottom QR and Website -->
      <div class="id-back-bottom">
        <div class="id-back-bottom-qr">
          <span>QR Code Here</span>
        </div>
        <div class="id-back-website-row">
          <div class="id-back-website-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="2" y1="12" x2="22" y2="12"></line>
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
            </svg>
          </div>
          <span class="id-back-website-url">${escapeHtml(dynamicUrl)}</span>
        </div>
      </div>
    </div>
  `;
}

// ============================================
// Filtering
// ============================================
function filterGallery() {
  const searchTerm = elements.searchInput ? elements.searchInput.value.toLowerCase().trim() : '';
  const positionFilter = elements.positionFilter ? elements.positionFilter.value : '';

  galleryState.filteredEmployees = galleryState.employees.filter(emp => {
    const matchesSearch = !searchTerm || 
      emp.employee_name.toLowerCase().includes(searchTerm) ||
      emp.id_number.toLowerCase().includes(searchTerm) ||
      (emp.location_branch || '').toLowerCase().includes(searchTerm);

    const matchesPosition = !positionFilter || emp.position === positionFilter;

    return matchesSearch && matchesPosition;
  });

  renderGallery();
}

// ============================================
// Preview & Download
// ============================================
function previewID(id) {
  const emp = galleryState.employees.find(e => e.id == id);
  
  if (!emp) {
    showToast('Employee not found', 'error');
    return;
  }

  galleryState.currentEmployee = emp;

  if (!elements.modalBody) {
    console.error('Modal body element not found');
    return;
  }

  elements.modalBody.innerHTML = `
    <!-- Flip Toggle Buttons -->
    <div class="id-flip-toggle">
      <button type="button" class="flip-btn active" data-side="front" onclick="showPreviewSide('front')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <circle cx="9" cy="10" r="2"/>
          <path d="M15 8h2M15 12h2M7 16h10"/>
        </svg>
        Front
      </button>
      <button type="button" class="flip-btn" data-side="back" onclick="showPreviewSide('back')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <path d="M7 7h10v10H7z"/>
          <path d="M12 11v4M12 7v1"/>
        </svg>
        Back
      </button>
    </div>
    
    <div class="id-preview-wrapper">
      <div id="previewFront">
        ${generateIDCardHtml(emp)}
      </div>
      <div id="previewBack" style="display: none;">
        ${generateIDCardBackHtml(emp)}
      </div>
    </div>
    <div class="id-preview-details">
      <h3>Employee Information</h3>
      <div class="preview-info-grid">
        <div class="preview-info-item">
          <span class="label">Full Name</span>
          <span class="value">${escapeHtml(emp.employee_name)}</span>
        </div>
        <div class="preview-info-item">
          <span class="label">ID Number</span>
          <span class="value">${escapeHtml(emp.id_number)}</span>
        </div>
        <div class="preview-info-item">
          <span class="label">Position</span>
          <span class="value">${escapeHtml(emp.position)}</span>
        </div>
        <div class="preview-info-item">
          <span class="label">Branch/Location</span>
          <span class="value">${escapeHtml(emp.location_branch || '-')}</span>
        </div>
        <div class="preview-info-item">
          <span class="label">Email</span>
          <span class="value">${escapeHtml(emp.email)}</span>
        </div>
        <div class="preview-info-item">
          <span class="label">Phone</span>
          <span class="value">${escapeHtml(emp.personal_number)}</span>
        </div>
        <div class="preview-info-item">
          <span class="label">Emergency Contact</span>
          <span class="value">${escapeHtml(emp.emergency_name || 'Not provided')}</span>
        </div>
        <div class="preview-info-item">
          <span class="label">Status</span>
          <span class="value"><span class="status-badge ${emp.status.toLowerCase()}">${emp.status}</span></span>
        </div>
      </div>
    </div>
  `;

  if (elements.previewModal) {
    elements.previewModal.classList.add('active');
  }
}

// Toggle between front and back preview in modal
function showPreviewSide(side) {
  const frontPreview = document.getElementById('previewFront');
  const backPreview = document.getElementById('previewBack');
  const flipBtns = document.querySelectorAll('.id-flip-toggle .flip-btn');
  
  // Update button states
  flipBtns.forEach(btn => {
    if (btn.dataset.side === side) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
  
  // Show/hide cards
  if (side === 'front') {
    if (frontPreview) frontPreview.style.display = 'block';
    if (backPreview) backPreview.style.display = 'none';
  } else {
    if (frontPreview) frontPreview.style.display = 'none';
    if (backPreview) backPreview.style.display = 'block';
  }
}

function closePreviewModal() {
  if (elements.previewModal) {
    elements.previewModal.classList.remove('active');
  }
  galleryState.currentEmployee = null;
}

// Download single ID as PDF
function downloadSinglePdf(id) {
  const emp = galleryState.employees.find(e => e.id == id);
  
  if (!emp) {
    showToast('Employee not found', 'error');
    return;
  }
  downloadIDPdf(emp);
}

// Download ID card as PDF using jsPDF and html2canvas - includes both front and back
// PDF Dimensions: 2.13" × 3.33" (97% of 3.43" original) at 300 DPI
async function downloadIDPdf(emp) {
  showToast('Generating print-quality PDF (2.13" × 3.33" at 300 DPI)...', 'success');

  try {
    // Log PDF configuration for debugging
    console.log('PDF Config:', {
      dimensions: `${PDF_CONFIG.WIDTH_INCHES}" × ${PDF_CONFIG.HEIGHT_INCHES}"`,
      dimensionsMm: `${PDF_CONFIG.WIDTH_MM.toFixed(2)}mm × ${PDF_CONFIG.HEIGHT_MM.toFixed(2)}mm`,
      renderPx: `${PDF_CONFIG.RENDER_WIDTH_PX}px × ${PDF_CONFIG.RENDER_HEIGHT_PX}px`,
      dpi: PDF_CONFIG.PRINT_DPI,
      scale: PDF_CONFIG.CANVAS_SCALE.toFixed(3)
    });

    // Create a temporary container - position off-screen but rendered
    const tempContainer = document.createElement('div');
    tempContainer.style.position = 'absolute';
    tempContainer.style.left = '-9999px';
    tempContainer.style.top = '0';
    tempContainer.style.width = `${PDF_CONFIG.RENDER_WIDTH_PX + 20}px`;
    tempContainer.style.background = '#ffffff';
    document.body.appendChild(tempContainer);
    
    // Use actual ID card dimensions (512×800) - matches preview exactly
    const designWidth = PDF_CONFIG.PREVIEW_WIDTH_PX;   // 512px
    const designHeight = PDF_CONFIG.PREVIEW_HEIGHT_PX; // 800px
    const scaleToFit = PDF_CONFIG.CANVAS_SCALE;        // ~3.125 for 300 DPI
    
    // Render front side at actual size for 300 DPI output
    tempContainer.innerHTML = `
      <div class="pdf-id-card-wrapper" style="width: ${designWidth}px; padding: 0; margin: 0; background: white; display: inline-block;">
        ${generateIDCardHtml(emp)}
      </div>
    `;

    // Ensure the card renders at exact 512×800 dimensions - NO scaling transforms
    const frontCardEl = tempContainer.querySelector('.id-card');
    frontCardEl.style.width = `${designWidth}px`;
    frontCardEl.style.height = `${designHeight}px`;
    frontCardEl.style.minWidth = `${designWidth}px`;
    frontCardEl.style.minHeight = `${designHeight}px`;
    frontCardEl.style.transform = 'none';  // Remove any CSS transforms
    frontCardEl.style.transformOrigin = 'top left';
    frontCardEl.style.margin = '0';
    frontCardEl.style.overflow = 'hidden';

    // Wait for images to fully load
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Preload all images in the container
    const images = tempContainer.querySelectorAll('img');
    await Promise.all(Array.from(images).map(img => {
      if (img.complete) return Promise.resolve();
      return new Promise(resolve => {
        img.onload = resolve;
        img.onerror = resolve;
      });
    }));
    
    // Use fixed height for consistent output
    const actualDesignHeight = designHeight;  // Always 800px
    console.log('PDF Front - Design dimensions:', designWidth, '×', actualDesignHeight);
    
    // Capture front side at high resolution for print quality (300 DPI)
    const frontCanvas = await html2canvas(frontCardEl, {
      scale: scaleToFit,  // Scale up for 300 DPI print quality
      useCORS: true,
      // Avoid tainted-canvas export failures (SecurityError on toDataURL)
      allowTaint: false,
      backgroundColor: '#ffffff',
      width: designWidth,
      height: actualDesignHeight,
      scrollY: 0,
      scrollX: 0,
      logging: false
    });

    // Render back side with same exact dimensions
    tempContainer.innerHTML = `
      <div class="pdf-id-card-wrapper" style="width: ${designWidth}px; padding: 0; margin: 0; background: white; display: inline-block;">
        ${generateIDCardBackHtml(emp)}
      </div>
    `;
    
    const backCardEl = tempContainer.querySelector('.id-card');
    backCardEl.style.width = `${designWidth}px`;
    backCardEl.style.height = `${designHeight}px`;
    backCardEl.style.minWidth = `${designWidth}px`;
    backCardEl.style.minHeight = `${designHeight}px`;
    backCardEl.style.transform = 'none';  // Remove any CSS transforms
    backCardEl.style.transformOrigin = 'top left';
    backCardEl.style.margin = '0';
    backCardEl.style.overflow = 'hidden';
    
    // Wait for back side images
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const backImages = tempContainer.querySelectorAll('img');
    await Promise.all(Array.from(backImages).map(img => {
      if (img.complete) return Promise.resolve();
      return new Promise(resolve => {
        img.onload = resolve;
        img.onerror = resolve;
      });
    }));
    
    // Use fixed height for back card
    const actualBackHeight = designHeight;  // Always 800px
    console.log('PDF Back - Design dimensions:', designWidth, '×', actualBackHeight);
    
    // Capture back side at high resolution (300 DPI)
    const backCanvas = await html2canvas(backCardEl, {
      scale: scaleToFit,
      useCORS: true,
      allowTaint: false,
      backgroundColor: '#ffffff',
      width: designWidth,
      height: actualBackHeight,
      scrollY: 0,
      scrollX: 0,
      logging: false
    });

    // Use exact PDF dimensions from config (2.13" × 3.33")
    const pdfWidthMm = PDF_CONFIG.WIDTH_MM;
    const pdfHeightMm = PDF_CONFIG.HEIGHT_MM;
    
    console.log('PDF Output:', {
      dimensions: `${pdfWidthMm.toFixed(2)}mm × ${pdfHeightMm.toFixed(2)}mm`,
      inches: `${PDF_CONFIG.WIDTH_INCHES}" × ${PDF_CONFIG.HEIGHT_INCHES}"`,
      scaleFactor: `${PDF_CONFIG.SCALE_FACTOR * 100}% of ${PDF_CONFIG.ORIGINAL_HEIGHT_INCHES}"`
    });

    // Create PDF with exact ID card dimensions
    const { jsPDF } = window.jspdf;
    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: [pdfWidthMm, pdfHeightMm],
      compress: true
    });

    // Add front side - fit to exact page dimensions
    const frontImgData = frontCanvas.toDataURL('image/png', 1.0);
    pdf.addImage(frontImgData, 'PNG', 0, 0, pdfWidthMm, pdfHeightMm, undefined, 'FAST');
    
    // Add back side on new page with same dimensions
    pdf.addPage([pdfWidthMm, pdfHeightMm], 'portrait');
    const backImgData = backCanvas.toDataURL('image/png', 1.0);
    pdf.addImage(backImgData, 'PNG', 0, 0, pdfWidthMm, pdfHeightMm, undefined, 'FAST');
    
    // Download the PDF with descriptive filename
    pdf.save(`ID_${emp.id_number}_${emp.employee_name.replace(/\\s+/g, '_')}_2.13x3.33in.pdf`);

    // Cleanup
    document.body.removeChild(tempContainer);
    
    // Mark as completed if approved
    if (emp.status === 'Approved') {
      await markAsCompleted(emp.id);
    }

    showToast(`PDF downloaded (${PDF_CONFIG.WIDTH_INCHES}" × ${PDF_CONFIG.HEIGHT_INCHES}" at ${PDF_CONFIG.PRINT_DPI} DPI)`, 'success');
  } catch (error) {
    console.error('Error generating PDF:', error);
    showToast('Failed to generate PDF. Please try again.', 'error');
  }
}

// Download all IDs as PDFs (front and back) - captures full content
async function downloadAllPdfs() {
  const employees = galleryState.filteredEmployees;
  
  if (employees.length === 0) {
    showToast('No IDs to download', 'error');
    return;
  }

  showToast(`Generating ${employees.length} print-quality PDFs (2.13" × 3.33")...`, 'success');
  elements.downloadAllBtn.disabled = true;
  elements.downloadAllBtn.innerHTML = `
    <svg class="spin" width="16" height="16" viewBox="0 0 16 16" fill="none">
      <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="2" stroke-dasharray="31.4" stroke-dashoffset="10"/>
    </svg>
    Downloading...
  `;

  try {
    // Use actual ID card dimensions (512×800) - matches preview exactly
    const designWidth = PDF_CONFIG.PREVIEW_WIDTH_PX;   // 512px
    const designHeight = PDF_CONFIG.PREVIEW_HEIGHT_PX; // 800px
    const scaleToFit = PDF_CONFIG.CANVAS_SCALE;        // ~3.125 for 300 DPI
    
    // Create a temporary container
    const tempContainer = document.createElement('div');
    tempContainer.style.position = 'absolute';
    tempContainer.style.left = '-9999px';
    tempContainer.style.top = '0';
    tempContainer.style.width = `${PDF_CONFIG.RENDER_WIDTH_PX + 20}px`;
    tempContainer.style.background = '#ffffff';
    document.body.appendChild(tempContainer);

    const { jsPDF } = window.jspdf;

    for (let i = 0; i < employees.length; i++) {
      const emp = employees[i];
      
      // Render front side at actual 512×800 dimensions
      tempContainer.innerHTML = `
        <div class="pdf-id-card-wrapper" style="width: ${designWidth}px; padding: 0; margin: 0; background: white; display: inline-block;">
          ${generateIDCardHtml(emp)}
        </div>
      `;
      
      const frontCardEl = tempContainer.querySelector('.id-card');
      frontCardEl.style.width = `${designWidth}px`;
      frontCardEl.style.height = `${designHeight}px`;
      frontCardEl.style.minWidth = `${designWidth}px`;
      frontCardEl.style.minHeight = `${designHeight}px`;
      frontCardEl.style.transform = 'none';  // No transform - actual size
      frontCardEl.style.transformOrigin = 'top left';
      frontCardEl.style.margin = '0';
      frontCardEl.style.overflow = 'hidden';
      
      await new Promise(resolve => setTimeout(resolve, 800));
      
      const frontImages = tempContainer.querySelectorAll('img');
      await Promise.all(Array.from(frontImages).map(img => {
        if (img.complete) return Promise.resolve();
        return new Promise(resolve => {
          img.onload = resolve;
          img.onerror = resolve;
        });
      }));
      
      // Use fixed 800px height
      const frontHeight = designHeight;
      
      const frontCanvas = await html2canvas(frontCardEl, {
        scale: scaleToFit,
        useCORS: true,
        allowTaint: false,
        backgroundColor: '#ffffff',
        width: designWidth,
        height: frontHeight
      });
      
      // Render back side at actual 512×800 dimensions
      tempContainer.innerHTML = `
        <div class="pdf-id-card-wrapper" style="width: ${designWidth}px; padding: 0; margin: 0; background: white; display: inline-block;">
          ${generateIDCardBackHtml(emp)}
        </div>
      `;
      
      const backCardEl = tempContainer.querySelector('.id-card');
      backCardEl.style.width = `${designWidth}px`;
      backCardEl.style.height = `${designHeight}px`;
      backCardEl.style.minWidth = `${designWidth}px`;
      backCardEl.style.minHeight = `${designHeight}px`;
      backCardEl.style.transform = 'none';  // No transform - actual size
      backCardEl.style.transformOrigin = 'top left';
      backCardEl.style.margin = '0';
      backCardEl.style.overflow = 'hidden';
      
      await new Promise(resolve => setTimeout(resolve, 500));
      
      const backImages = tempContainer.querySelectorAll('img');
      await Promise.all(Array.from(backImages).map(img => {
        if (img.complete) return Promise.resolve();
        return new Promise(resolve => {
          img.onload = resolve;
          img.onerror = resolve;
        });
      }));
      
      // Use fixed 800px height
      const backHeight = designHeight;
      
      const backCanvas = await html2canvas(backCardEl, {
        scale: scaleToFit,
        useCORS: true,
        allowTaint: false,
        backgroundColor: '#ffffff',
        width: designWidth,
        height: backHeight
      });

      // Use exact PDF dimensions (2.13" × 3.33")
      const pdfWidthMm = PDF_CONFIG.WIDTH_MM;
      const pdfHeightMm = PDF_CONFIG.HEIGHT_MM;

      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: [pdfWidthMm, pdfHeightMm],
        compress: true
      });

      // Add front side - fit to exact dimensions
      const frontImgData = frontCanvas.toDataURL('image/png', 1.0);
      pdf.addImage(frontImgData, 'PNG', 0, 0, pdfWidthMm, pdfHeightMm, undefined, 'FAST');
      
      // Add back side - fit to exact dimensions
      pdf.addPage([pdfWidthMm, pdfHeightMm], 'portrait');
      const backImgData = backCanvas.toDataURL('image/png', 1.0);
      pdf.addImage(backImgData, 'PNG', 0, 0, pdfWidthMm, pdfHeightMm, undefined, 'FAST');
      
      pdf.save(`ID_${emp.id_number}_${emp.employee_name.replace(/\s+/g, '_')}_2.13x3.33in.pdf`);

      await new Promise(resolve => setTimeout(resolve, 300));
    }

    document.body.removeChild(tempContainer);
    showToast(`Downloaded ${employees.length} PDFs (${PDF_CONFIG.WIDTH_INCHES}" × ${PDF_CONFIG.HEIGHT_INCHES}" at ${PDF_CONFIG.PRINT_DPI} DPI)`, 'success');
  } catch (error) {
    console.error('Error downloading PDFs:', error);
    showToast('Failed to download some PDFs. Please try again.', 'error');
  } finally {
    elements.downloadAllBtn.disabled = false;
    elements.downloadAllBtn.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M8 2v8M4 6l4 4 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M2 12v2h12v-2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      Download All PDFs
    `;
  }
}

async function markAsCompleted(id) {
  try {
    const response = await fetch(`/hr/api/employees/${id}/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });

    if (response.ok) {
      const emp = galleryState.employees.find(e => e.id === id);
      if (emp) emp.status = 'Completed';
      updateStats();
      renderGallery();
    }
  } catch (error) {
    console.error('Error marking as completed:', error);
  }
}

// ============================================
// Utilities
// ============================================
function showToast(message, type = 'success') {
  if (!elements.toastMessage || !elements.toast) {
    console.log('Toast:', type, message);
    return;
  }
  elements.toastMessage.textContent = message;
  elements.toast.className = `toast show ${type}`;

  setTimeout(() => {
    elements.toast.classList.remove('show');
  }, 3000);
}

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// ============================================
// Global Window Exports for onclick handlers
// Must be at the END after all functions are defined
// ============================================
window.showPreviewSide = showPreviewSide;
window.previewID = previewID;
window.closePreviewModal = closePreviewModal;
window.downloadSinglePdf = downloadSinglePdf;
window.downloadAllPdfs = downloadAllPdfs;
