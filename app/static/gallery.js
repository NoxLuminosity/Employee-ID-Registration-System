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

// Landscape PDF Config for Field Officer templates
// PDF Dimensions: 3.33" width × 2.13" height (landscape orientation)
// Card Preview: 512px × 319px (matches .id-card-field-office)
const PDF_CONFIG_LANDSCAPE = {
  // Landscape dimensions (credit card aspect ratio)
  WIDTH_INCHES: 3.33,
  HEIGHT_INCHES: 2.13,  // Exact 3.33:2.13 ratio as requested
  
  // Preview canvas dimensions for landscape (pixels) - MUST match CSS
  PREVIEW_WIDTH_PX: 512,
  PREVIEW_HEIGHT_PX: 319,
  
  // Print quality DPI
  PRINT_DPI: 300,
  SCREEN_DPI: 96,
  
  // Calculated dimensions in mm (for jsPDF)
  get WIDTH_MM() { return this.WIDTH_INCHES * 25.4; },  // 84.582mm
  get HEIGHT_MM() { return this.HEIGHT_INCHES * 25.4; }, // 54.102mm
  
  // Pixel dimensions at 300 DPI for rendering
  get RENDER_WIDTH_PX() { return Math.round(this.WIDTH_INCHES * this.PRINT_DPI); },  // 999px
  get RENDER_HEIGHT_PX() { return Math.round(this.HEIGHT_INCHES * this.PRINT_DPI); }, // 639px
  
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
    const isFieldOfficer = emp.position === 'Field Officer';
    
    // Dual template badge for ALL Field Officers
    const dualBadge = isFieldOfficer 
      ? '<span class="dual-template-badge" title="This employee has 2 ID templates (Portrait + Landscape)">2 Templates</span>' 
      : '';
    
    // Determine wrapper class for proper scaling
    // Show portrait template in gallery grid for all Field Officers
    const wrapperClass = 'id-card-image-wrapper';

    return `
      <div class="id-gallery-card${isFieldOfficer ? ' field-officer-card' : ''}" data-id="${emp.id}">
        <div class="${wrapperClass}" onclick="window.previewID(${emp.id})">
          ${generateIDCardHtml(emp)}
        </div>
        <div class="id-gallery-card-footer">
          <div class="id-card-info-row">
            <span class="id-card-emp-name">${escapeHtml(emp.employee_name)}</span>
            <div class="id-card-badges">
              ${dualBadge}
              <span class="status-badge ${statusClass}">${emp.status}</span>
            </div>
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
              PDF${isFieldOfficer ? ' (4 pages)' : ''}
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
// Now supports different templates based on position and field_officer_type
// Template selection source-of-truth:
// - Freelancer, Intern, Others: Portrait template (512x800)
// - Field Officer (Others): Landscape Field Office template (512x319)
// - Field Officer (Reprocessor): DUAL templates (Portrait + Landscape) - shown in grid as portrait
function generateIDCardHtml(emp) {
  // Check if this is a Field Officer - Reprocessor (needs dual templates)
  const isFieldOfficer = emp.position === 'Field Officer';
  const isReprocessor = isFieldOfficer && emp.field_officer_type === 'Reprocessor';
  
  // For Reprocessor: In gallery grid, show portrait template (original) as primary card
  // The dual preview is shown in modal and PDF will include both
  if (isReprocessor) {
    return generateRegularIDCardHtml(emp);
  }
  
  // For Field Officers (Others only), use the Field Office template (landscape)
  if (isFieldOfficer) {
    return generateFieldOfficeIDCardHtml(emp);
  }
  
  // For non-Field Officers, use the regular template
  return generateRegularIDCardHtml(emp);
}

// Generate Regular ID Card HTML (for Freelancer, Intern, Others)
// Image source rule: Uses AI-generated photo (nobg_photo_url preferred)
// For Reprocessor Portrait Template: Uses AI photo
function generateRegularIDCardHtml(emp) {
  // Use AI-generated photo (nobg_photo_url or new_photo_url) for portrait template
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
            <!-- Signature overlay at lower-right of photo -->
            <div class="id-signature-area ${signatureHasImage}">
              ${signatureHtml}
            </div>
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

// Generate Field Office ID Card HTML (for Field Officers)
// Image source rule: Uses ORIGINAL uploaded photo (NOT AI-generated)
// - Field Officer (Others): Uses original photo only
// - Field Officer (Reprocessor) Landscape Template: Uses original photo
function generateFieldOfficeIDCardHtml(emp) {
  // Use original uploaded photo only (NOT AI photo)
  const idPhotoUrl = emp.photo_url;
  const photoHasImage = idPhotoUrl ? 'has-image' : '';
  const photoHtml = idPhotoUrl 
    ? `<img src="${idPhotoUrl}" alt="${escapeHtml(emp.employee_name)}" crossorigin="anonymous">`
    : `<span class="id-fo-photo-placeholder">Photo</span>`;

  const signatureHtml = emp.signature_url 
    ? `<img src="${emp.signature_url}" alt="Signature" crossorigin="anonymous">`
    : `<span class="id-fo-signature-placeholder"></span>`;

  // Parse name for multi-line display
  const nameParts = emp.employee_name.split(' ');
  const firstName = nameParts[0] || '';
  const lastName = nameParts.slice(1).join(' ') || '';
  const displayName = firstName && lastName ? `${firstName}<br>${lastName}` : emp.employee_name;
  
  // Position display - ALWAYS show "LEGAL OFFICER" regardless of field_officer_type
  // The placeholder label should never change to "REPROCESSOR"
  const positionDisplay = 'LEGAL OFFICER';
  
  // Field clearance (default to Level 5)
  const clearanceLevel = emp.field_clearance || 'Level 5';

  return `
    <div class="id-card-field-office gallery-id-card-field-office">
      <div class="id-field-office-content">
        <!-- Photo Section with border -->
        <div class="id-fo-photo-section">
          <div class="id-fo-photo-container ${photoHasImage}">
            ${photoHtml}
          </div>
        </div>

        <!-- Signature Section -->
        <div class="id-fo-signature-section">
          <div class="id-fo-signature-container ${emp.signature_url ? 'has-image' : ''}">
            ${signatureHtml}
          </div>
        </div>

        <!-- Employee Name -->
        <div class="id-fo-name-section">
          <h1 class="id-fo-name">${displayName}</h1>
        </div>

        <!-- Position -->
        <div class="id-fo-position-section">
          <span class="id-fo-position">${escapeHtml(positionDisplay)}</span>
        </div>

        <!-- Field Clearance Level -->
        <div class="id-fo-clearance-section">
          <span class="id-fo-clearance-label">FIELD CLEARANCE:</span>
          <span class="id-fo-clearance-level">${escapeHtml(clearanceLevel)}</span>
        </div>

        <!-- Barcode - Above ID Number -->
        <div class="id-fo-barcode-section">
          <div class="id-fo-barcode-placeholder">
            <span>Barcode</span>
          </div>
        </div>

        <!-- ID Number - Below Barcode -->
        <div class="id-fo-idnumber-section">
          <span class="id-fo-idnumber">${escapeHtml(emp.id_number)}</span>
        </div>
      </div>
    </div>
  `;
}

// Generate Field Office ID Card Back HTML
function generateFieldOfficeIDCardBackHtml(emp) {
  return `
    <div class="id-card-field-office-back gallery-id-card-field-office-back">
      <!-- Back side uses 4.png as background - no editable content -->
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

// Generate appropriate back HTML based on employee type
function getBackHtml(emp) {
  const isFieldOfficer = emp.position === 'Field Officer';
  if (isFieldOfficer) {
    return generateFieldOfficeIDCardBackHtml(emp);
  }
  return generateIDCardBackHtml(emp);
}

// Generate single template preview HTML (for Others/non-Field Officers)
function generateSingleTemplatePreviewHtml(emp, isFieldOfficer) {
  return `
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
        ${getBackHtml(emp)}
      </div>
    </div>
  `;
}

// Generate dual template preview HTML (for Reprocessor - shows both SPMC and Field Office templates)
function generateDualTemplatePreviewHtml(emp) {
  return `
    <div class="dual-template-grid gallery-dual-template-grid">
      <!-- SPMC Template (Portrait) -->
      <div class="dual-template-card">
        <h3 class="dual-template-title">SPMC ID Card</h3>
        <div class="id-flip-toggle dual-flip-toggle">
          <button type="button" class="flip-btn active" data-side="front" data-template="original" onclick="showDualPreviewSide('original', 'front')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <circle cx="9" cy="10" r="2"/>
              <path d="M15 8h2M15 12h2M7 16h10"/>
            </svg>
            Front
          </button>
          <button type="button" class="flip-btn" data-side="back" data-template="original" onclick="showDualPreviewSide('original', 'back')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <path d="M7 7h10v10H7z"/>
              <path d="M12 11v4M12 7v1"/>
            </svg>
            Back
          </button>
        </div>
        <div class="id-preview-wrapper dual-preview-wrapper">
          <div id="dualOriginalFront">
            ${generateRegularIDCardHtml(emp)}
          </div>
          <div id="dualOriginalBack" style="display: none;">
            ${generateIDCardBackHtml(emp)}
          </div>
        </div>
      </div>
      
      <!-- Field Office Template (Landscape) -->
      <div class="dual-template-card">
        <h3 class="dual-template-title">Field Office ID Card</h3>
        <div class="id-flip-toggle dual-flip-toggle">
          <button type="button" class="flip-btn active" data-side="front" data-template="reprocessor" onclick="showDualPreviewSide('reprocessor', 'front')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <circle cx="9" cy="10" r="2"/>
              <path d="M15 8h2M15 12h2M7 16h10"/>
            </svg>
            Front
          </button>
          <button type="button" class="flip-btn" data-side="back" data-template="reprocessor" onclick="showDualPreviewSide('reprocessor', 'back')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <path d="M7 7h10v10H7z"/>
              <path d="M12 11v4M12 7v1"/>
            </svg>
            Back
          </button>
        </div>
        <div class="id-preview-wrapper dual-preview-wrapper">
          <div id="dualReprocessorFront">
            ${generateFieldOfficeIDCardHtml(emp)}
          </div>
          <div id="dualReprocessorBack" style="display: none;">
            ${generateFieldOfficeIDCardBackHtml(emp)}
          </div>
        </div>
      </div>
    </div>
  `;
}

// Generate employee information HTML for preview modal
// Shows all employee data including Field Officer fields for HR visibility
function generateEmployeeInfoHtml(emp) {
  // Determine if employee is Field Officer (for conditional display text)
  const isFieldOfficer = emp.position === 'Field Officer';
  
  // Build the FO-specific fields section - show for ALL employees to allow HR to see source-of-truth data
  // Display hyphen (-) when values are empty or not applicable
  const foFieldsHtml = `
        <div class="preview-info-item">
          <span class="label">Field Clearance</span>
          <span class="value">${escapeHtml(emp.field_clearance || '-')}</span>
        </div>
        <div class="preview-info-item">
          <span class="label">Division</span>
          <span class="value">${escapeHtml(emp.fo_division || '-')}</span>
        </div>
        <div class="preview-info-item">
          <span class="label">Department</span>
          <span class="value">${escapeHtml(emp.fo_department || '-')}</span>
        </div>
        <div class="preview-info-item">
          <span class="label">Campaign</span>
          <span class="value">${escapeHtml(emp.fo_campaign || '-')}</span>
        </div>
        ${isFieldOfficer ? `
        <div class="preview-info-item">
          <span class="label">FO Type</span>
          <span class="value">${escapeHtml(emp.field_officer_type || '-')}</span>
        </div>` : ''}
  `;
  
  return `
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
          <span class="value">${escapeHtml(emp.position)}${emp.field_officer_type ? ' - ' + escapeHtml(emp.field_officer_type) : ''}</span>
        </div>
        <div class="preview-info-item">
          <span class="label">Branch/Location</span>
          <span class="value">${escapeHtml(emp.location_branch || '-')}</span>
        </div>
        ${foFieldsHtml}
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
}

// Show/hide sides in dual template preview mode (for gallery modal)
function showDualPreviewSide(template, side) {
  const templatePrefix = template === 'original' ? 'dualOriginal' : 'dualReprocessor';
  const frontCard = document.getElementById(`${templatePrefix}Front`);
  const backCard = document.getElementById(`${templatePrefix}Back`);
  
  // Update button states for this template only
  const templateCards = document.querySelectorAll('.dual-template-card');
  const templateCard = template === 'original' ? templateCards[0] : templateCards[1];
  
  if (templateCard) {
    const flipBtns = templateCard.querySelectorAll('.flip-btn');
    flipBtns.forEach(btn => {
      if (btn.dataset.side === side) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
  }
  
  // Show/hide cards
  if (side === 'front') {
    if (frontCard) frontCard.style.display = 'block';
    if (backCard) backCard.style.display = 'none';
  } else {
    if (frontCard) frontCard.style.display = 'none';
    if (backCard) backCard.style.display = 'block';
  }
}

// Make showDualPreviewSide available globally
window.showDualPreviewSide = showDualPreviewSide;

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

  // Check if this is a Field Officer (needs dual template display - both portrait and landscape)
  const isFieldOfficer = emp.position === 'Field Officer';
  
  // Generate the appropriate preview HTML
  let previewHtml = '';
  
  if (isFieldOfficer) {
    // Dual template preview for ALL Field Officers (shows both SPMC portrait + Field Office landscape)
    previewHtml = generateDualTemplatePreviewHtml(emp);
  } else {
    // Single template preview for non-Field Officers (Freelancer, Intern, Others)
    previewHtml = generateSingleTemplatePreviewHtml(emp, isFieldOfficer);
  }
  
  elements.modalBody.innerHTML = previewHtml + generateEmployeeInfoHtml(emp);

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

// Helper function to capture a card canvas for PDF generation
async function captureCardCanvas(tempContainer, cardHtml, designWidth, designHeight, scaleToFit, waitTime = 1000) {
  tempContainer.innerHTML = `
    <div class="pdf-id-card-wrapper" style="width: ${designWidth}px; padding: 0; margin: 0; background: white; display: inline-block;">
      ${cardHtml}
    </div>
  `;

  // Try to find the card element - could be .id-card or .id-card-field-office or .id-card-back
  let cardEl = tempContainer.querySelector('.id-card');
  if (!cardEl) {
    cardEl = tempContainer.querySelector('.id-card-field-office');
  }
  if (!cardEl) {
    cardEl = tempContainer.querySelector('.id-card-field-office-back');
  }
  if (!cardEl) {
    cardEl = tempContainer.querySelector('[class*="id-card"]');
  }
  
  // Guard against null element
  if (!cardEl) {
    console.error('captureCardCanvas: No card element found in HTML');
    throw new Error('Card element not found for PDF capture');
  }

  cardEl.style.width = `${designWidth}px`;
  cardEl.style.height = `${designHeight}px`;
  cardEl.style.minWidth = `${designWidth}px`;
  cardEl.style.minHeight = `${designHeight}px`;
  cardEl.style.transform = 'none';
  cardEl.style.transformOrigin = 'top left';
  cardEl.style.margin = '0';
  cardEl.style.overflow = 'hidden';

  await new Promise(resolve => setTimeout(resolve, waitTime));
  
  const images = tempContainer.querySelectorAll('img');
  await Promise.all(Array.from(images).map(img => {
    if (img.complete) return Promise.resolve();
    return new Promise(resolve => {
      img.onload = resolve;
      img.onerror = resolve;
    });
  }));

  return await html2canvas(cardEl, {
    scale: scaleToFit,
    useCORS: true,
    allowTaint: false,
    backgroundColor: '#ffffff',
    width: designWidth,
    height: designHeight,
    scrollY: 0,
    scrollX: 0,
    logging: false
  });
}

// Download ID card as PDF using jsPDF and html2canvas - includes both front and back
// PDF Dimensions: 2.13" × 3.33" (97% of 3.43" original) at 300 DPI
// For ALL Field Officers: generates 4-page PDF (Portrait SPMC + Landscape Field Office templates)
async function downloadIDPdf(emp) {
  const isFieldOfficer = emp.position === 'Field Officer';
  const pageCount = isFieldOfficer ? 4 : 2;
  
  showToast(`Generating ${pageCount}-page print-quality PDF (2.13" × 3.33" at 300 DPI)...`, 'success');

  try {
    // Log PDF configuration for debugging
    console.log('PDF Config:', {
      dimensions: `${PDF_CONFIG.WIDTH_INCHES}" × ${PDF_CONFIG.HEIGHT_INCHES}"`,
      dimensionsMm: `${PDF_CONFIG.WIDTH_MM.toFixed(2)}mm × ${PDF_CONFIG.HEIGHT_MM.toFixed(2)}mm`,
      renderPx: `${PDF_CONFIG.RENDER_WIDTH_PX}px × ${PDF_CONFIG.RENDER_HEIGHT_PX}px`,
      dpi: PDF_CONFIG.PRINT_DPI,
      scale: PDF_CONFIG.CANVAS_SCALE.toFixed(3),
      isFieldOfficer: isFieldOfficer,
      pageCount: pageCount
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
    
    // Use exact PDF dimensions from config (2.13" × 3.33")
    const pdfWidthMm = PDF_CONFIG.WIDTH_MM;
    const pdfHeightMm = PDF_CONFIG.HEIGHT_MM;
    
    // Create PDF with exact ID card dimensions
    const { jsPDF } = window.jspdf;
    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: [pdfWidthMm, pdfHeightMm],
      compress: true
    });

    if (isFieldOfficer) {
      // 4-page PDF for ALL Field Officers: Original Portrait (front/back) + Field Office Landscape (front/back)
      console.log('Generating 4-page PDF for Field Officer...');
      
      // Page 1: Original template front
      console.log('Capturing Original template front...');
      const originalFrontCanvas = await captureCardCanvas(
        tempContainer, 
        generateRegularIDCardHtml(emp), 
        designWidth, 
        designHeight, 
        scaleToFit, 
        1500
      );
      const originalFrontImgData = originalFrontCanvas.toDataURL('image/png', 1.0);
      pdf.addImage(originalFrontImgData, 'PNG', 0, 0, pdfWidthMm, pdfHeightMm, undefined, 'FAST');
      
      // Page 2: Original template back
      console.log('Capturing Original template back...');
      pdf.addPage([pdfWidthMm, pdfHeightMm], 'portrait');
      const originalBackCanvas = await captureCardCanvas(
        tempContainer, 
        generateIDCardBackHtml(emp), 
        designWidth, 
        designHeight, 
        scaleToFit, 
        1000
      );
      const originalBackImgData = originalBackCanvas.toDataURL('image/png', 1.0);
      pdf.addImage(originalBackImgData, 'PNG', 0, 0, pdfWidthMm, pdfHeightMm, undefined, 'FAST');
      
      // Page 3: Field Officer template front (landscape - 3.33" x 2.13")
      console.log('Capturing Field Officer template front (landscape)...');
      const landscapeWidthMm = PDF_CONFIG_LANDSCAPE.WIDTH_MM;  // 3.33" = 84.582mm
      const landscapeHeightMm = PDF_CONFIG_LANDSCAPE.HEIGHT_MM; // 2.13" = 54.102mm
      const landscapeDesignWidth = PDF_CONFIG_LANDSCAPE.PREVIEW_WIDTH_PX;  // 512px
      const landscapeDesignHeight = PDF_CONFIG_LANDSCAPE.PREVIEW_HEIGHT_PX; // 319px
      const landscapeScale = PDF_CONFIG_LANDSCAPE.CANVAS_SCALE;
      
      // Add page with LANDSCAPE orientation - width > height
      pdf.addPage([landscapeWidthMm, landscapeHeightMm], 'landscape');
      const foFrontCanvas = await captureCardCanvas(
        tempContainer, 
        generateFieldOfficeIDCardHtml(emp), 
        landscapeDesignWidth, 
        landscapeDesignHeight, 
        landscapeScale, 
        1000
      );
      const foFrontImgData = foFrontCanvas.toDataURL('image/png', 1.0);
      pdf.addImage(foFrontImgData, 'PNG', 0, 0, landscapeWidthMm, landscapeHeightMm, undefined, 'FAST');
      
      // Page 4: Field Officer template back (landscape - 3.33" x 2.13" - MUST match front)
      console.log('Capturing Field Officer template back (landscape)...');
      // CRITICAL: Back side MUST use same landscape dimensions as front
      pdf.addPage([landscapeWidthMm, landscapeHeightMm], 'landscape');
      const foBackCanvas = await captureCardCanvas(
        tempContainer, 
        generateFieldOfficeIDCardBackHtml(emp), 
        landscapeDesignWidth, 
        landscapeDesignHeight, 
        landscapeScale, 
        1000
      );
      const foBackImgData = foBackCanvas.toDataURL('image/png', 1.0);
      pdf.addImage(foBackImgData, 'PNG', 0, 0, landscapeWidthMm, landscapeHeightMm, undefined, 'FAST');
      
    } else {
      // Standard 2-page PDF for non-Field Officer employees (Freelancer, Intern, Others)
      // Uses portrait template only
      console.log('Generating 2-page PDF (portrait)...');
      
      // Non-Field Officer - Use portrait dimensions
      // Page 1: Front side (uses position-aware template)
      console.log('Capturing front side...');
      const frontCanvas = await captureCardCanvas(
        tempContainer, 
        generateIDCardHtml(emp), 
        designWidth, 
        designHeight, 
        scaleToFit, 
        1500
      );
      const frontImgData = frontCanvas.toDataURL('image/png', 1.0);
      pdf.addImage(frontImgData, 'PNG', 0, 0, pdfWidthMm, pdfHeightMm, undefined, 'FAST');
      
      // Page 2: Back side (uses position-aware template)
      console.log('Capturing back side...');
      pdf.addPage([pdfWidthMm, pdfHeightMm], 'portrait');
      const backCanvas = await captureCardCanvas(
        tempContainer, 
        getBackHtml(emp), 
        designWidth, 
        designHeight, 
        scaleToFit, 
        1000
      );
      const backImgData = backCanvas.toDataURL('image/png', 1.0);
      pdf.addImage(backImgData, 'PNG', 0, 0, pdfWidthMm, pdfHeightMm, undefined, 'FAST');
    }
    
    console.log('PDF Output:', {
      dimensions: `${pdfWidthMm.toFixed(2)}mm × ${pdfHeightMm.toFixed(2)}mm`,
      inches: `${PDF_CONFIG.WIDTH_INCHES}" × ${PDF_CONFIG.HEIGHT_INCHES}"`,
      scaleFactor: `${PDF_CONFIG.SCALE_FACTOR * 100}% of ${PDF_CONFIG.ORIGINAL_HEIGHT_INCHES}"`,
      pages: pageCount
    });
    
    // Download the PDF with descriptive filename
    const suffix = isFieldOfficer ? '_dual_templates' : '';
    pdf.save(`ID_${emp.id_number}_${emp.employee_name.replace(/\s+/g, '_')}${suffix}.pdf`);

    // Cleanup
    document.body.removeChild(tempContainer);
    
    // Mark as completed if approved
    if (emp.status === 'Approved') {
      await markAsCompleted(emp.id);
    }

    const message = isFieldOfficer 
      ? `4-page PDF downloaded (Portrait + Landscape templates at ${PDF_CONFIG.PRINT_DPI} DPI)`
      : `PDF downloaded (${PDF_CONFIG.WIDTH_INCHES}" × ${PDF_CONFIG.HEIGHT_INCHES}" at ${PDF_CONFIG.PRINT_DPI} DPI)`;
    showToast(message, 'success');
  } catch (error) {
    console.error('Error generating PDF:', error);
    showToast('Failed to generate PDF. Please try again.', 'error');
  }
}

// Download all IDs as PDFs (front and back) - captures full content
// For ALL Field Officer employees: generates 4-page PDFs (Portrait + Landscape templates)
async function downloadAllPdfs() {
  const employees = galleryState.filteredEmployees;
  
  if (employees.length === 0) {
    showToast('No IDs to download', 'error');
    return;
  }

  // Count Field Officer employees for accurate messaging
  const fieldOfficerCount = employees.filter(emp => 
    emp.position === 'Field Officer'
  ).length;
  const regularCount = employees.length - fieldOfficerCount;
  
  let message = `Generating ${employees.length} print-quality PDFs`;
  if (fieldOfficerCount > 0) {
    message += ` (${fieldOfficerCount} dual-template, ${regularCount} standard)`;
  }
  showToast(message + '...', 'success');
  
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
    
    // Use exact PDF dimensions (2.13" × 3.33")
    const pdfWidthMm = PDF_CONFIG.WIDTH_MM;
    const pdfHeightMm = PDF_CONFIG.HEIGHT_MM;

    for (let i = 0; i < employees.length; i++) {
      const emp = employees[i];
      const isFieldOfficer = emp.position === 'Field Officer';

      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: [pdfWidthMm, pdfHeightMm],
        compress: true
      });
      
      // Landscape config for Field Officer templates
      const landscapeWidthMm = PDF_CONFIG_LANDSCAPE.WIDTH_MM;  // 3.33" = 84.582mm
      const landscapeHeightMm = PDF_CONFIG_LANDSCAPE.HEIGHT_MM; // 2.13" = 54.102mm
      const landscapeDesignWidth = PDF_CONFIG_LANDSCAPE.PREVIEW_WIDTH_PX;  // 512px
      const landscapeDesignHeight = PDF_CONFIG_LANDSCAPE.PREVIEW_HEIGHT_PX; // 319px
      const landscapeScale = PDF_CONFIG_LANDSCAPE.CANVAS_SCALE;
      
      if (isFieldOfficer) {
        // 4-page PDF for ALL Field Officers: Portrait (front/back) + Landscape (front/back)
        
        // Page 1: Original template front (portrait 2.13" x 3.33")
        const originalFrontCanvas = await captureCardCanvas(
          tempContainer, 
          generateRegularIDCardHtml(emp), 
          designWidth, 
          designHeight, 
          scaleToFit, 
          800
        );
        pdf.addImage(originalFrontCanvas.toDataURL('image/png', 1.0), 'PNG', 0, 0, pdfWidthMm, pdfHeightMm, undefined, 'FAST');
        
        // Page 2: Original template back (portrait 2.13" x 3.33")
        pdf.addPage([pdfWidthMm, pdfHeightMm], 'portrait');
        const originalBackCanvas = await captureCardCanvas(
          tempContainer, 
          generateIDCardBackHtml(emp), 
          designWidth, 
          designHeight, 
          scaleToFit, 
          500
        );
        pdf.addImage(originalBackCanvas.toDataURL('image/png', 1.0), 'PNG', 0, 0, pdfWidthMm, pdfHeightMm, undefined, 'FAST');
        
        // Page 3: Field Officer template front (landscape 3.33" x 2.13")
        pdf.addPage([landscapeWidthMm, landscapeHeightMm], 'landscape');
        const foFrontCanvas = await captureCardCanvas(
          tempContainer, 
          generateFieldOfficeIDCardHtml(emp), 
          landscapeDesignWidth, 
          landscapeDesignHeight, 
          landscapeScale, 
          500
        );
        pdf.addImage(foFrontCanvas.toDataURL('image/png', 1.0), 'PNG', 0, 0, landscapeWidthMm, landscapeHeightMm, undefined, 'FAST');
        
        // Page 4: Field Officer template back (landscape 3.33" x 2.13")
        pdf.addPage([landscapeWidthMm, landscapeHeightMm], 'landscape');
        const foBackCanvas = await captureCardCanvas(
          tempContainer, 
          generateFieldOfficeIDCardBackHtml(emp), 
          landscapeDesignWidth, 
          landscapeDesignHeight, 
          landscapeScale, 
          500
        );
        pdf.addImage(foBackCanvas.toDataURL('image/png', 1.0), 'PNG', 0, 0, landscapeWidthMm, landscapeHeightMm, undefined, 'FAST');
        
        pdf.save(`ID_${emp.id_number}_${emp.employee_name.replace(/\s+/g, '_')}_dual_templates.pdf`);
        
      } else {
        // Standard 2-page PORTRAIT PDF for Freelancer/Intern/Others - 2.13" x 3.33"
        
        // Page 1: Front side (uses position-aware template)
        const frontCanvas = await captureCardCanvas(
          tempContainer, 
          generateIDCardHtml(emp), 
          designWidth, 
          designHeight, 
          scaleToFit, 
          800
        );
        pdf.addImage(frontCanvas.toDataURL('image/png', 1.0), 'PNG', 0, 0, pdfWidthMm, pdfHeightMm, undefined, 'FAST');
        
        // Page 2: Back side (uses position-aware template)
        pdf.addPage([pdfWidthMm, pdfHeightMm], 'portrait');
        const backCanvas = await captureCardCanvas(
          tempContainer, 
          getBackHtml(emp), 
          designWidth, 
          designHeight, 
          scaleToFit, 
          500
        );
        pdf.addImage(backCanvas.toDataURL('image/png', 1.0), 'PNG', 0, 0, pdfWidthMm, pdfHeightMm, undefined, 'FAST');
        
        pdf.save(`ID_${emp.id_number}_${emp.employee_name.replace(/\s+/g, '_')}_2.13x3.33in.pdf`);
      }

      await new Promise(resolve => setTimeout(resolve, 300));
    }

    document.body.removeChild(tempContainer);
    
    let successMessage = `Downloaded ${employees.length} PDFs`;
    if (fieldOfficerCount > 0) {
      successMessage += ` (${fieldOfficerCount} with dual templates)`;
    }
    showToast(successMessage, 'success');
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
