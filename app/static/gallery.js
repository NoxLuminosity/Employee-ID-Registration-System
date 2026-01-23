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
  lastFetchTime: null
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
    departmentFilter: document.getElementById('departmentFilter'),
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
  if (elements.departmentFilter) {
    elements.departmentFilter.addEventListener('change', filterGallery);
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
        <div class="id-card-image-wrapper" onclick="previewID(${emp.id})">
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
            <span>${escapeHtml(emp.department)}</span>
          </div>
          <div class="id-card-actions">
            <button class="btn-preview" onclick="previewID(${emp.id})">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                <path d="M8 3C4.5 3 1.7 5.5 1 8c.7 2.5 3.5 5 7 5s6.3-2.5 7-5c-.7-2.5-3.5-5-7-5z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                <circle cx="8" cy="8" r="2" stroke="currentColor" stroke-width="1.5"/>
              </svg>
              Preview
            </button>
            <button class="btn-download" onclick="downloadSinglePdf(${emp.id})">
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
          <p class="id-website-url">www.spmadrid.com</p>
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
  
  // Emergency contact details
  const emergencyName = emp.emergency_name || 'Not provided';
  const emergencyContact = emp.emergency_contact || 'Not provided';
  const emergencyAddress = emp.emergency_address || 'Not provided';

  return `
    <div class="id-card id-card-back gallery-id-card-back">
      <!-- Top Section - QR Code Area with Geometric Background -->
      <div class="id-back-top">
        <!-- Geometric Background Pattern -->
        <div class="id-back-pattern"></div>
        
        <!-- QR Code Content -->
        <div class="id-back-qr-content">
          <!-- QR Code Placeholder -->
          <div class="id-qr-code">
            <svg viewBox="0 0 100 100" width="180" height="180">
              <rect fill="#ffffff" width="100" height="100" rx="8"/>
              <text x="50" y="50" text-anchor="middle" fill="#9ca3af" font-size="10" dy=".3em">QR Code</text>
            </svg>
          </div>
          
          <!-- VCARD Label -->
          <h1 class="id-vcard-label">VCARD</h1>
          
          <!-- Website URL -->
          <p class="id-vcard-url">www.spmadrid.com/${escapeHtml(username)}</p>
        </div>
      </div>

      <!-- Bottom Section - Logo and Emergency Contact -->
      <div class="id-back-bottom">
        <!-- SPM Logo -->
        <div class="id-back-logo">
          <img src="/static/images/SPM%20Logo%201.png" alt="SPM Logo" class="id-back-logo-image" crossorigin="anonymous">
        </div>

        <!-- Emergency Contact Info -->
        <div class="id-emergency-section">
          <h2 class="id-emergency-title">In case of emergency, please notify:</h2>
          
          <div class="id-emergency-info">
            <div class="id-emergency-row">
              <span class="id-emergency-label">Name:</span>
              <span class="id-emergency-value">${escapeHtml(emergencyName)}</span>
            </div>
            
            <div class="id-emergency-row">
              <span class="id-emergency-label">Contact #:</span>
              <span class="id-emergency-value">${escapeHtml(emergencyContact)}</span>
            </div>
            
            <div class="id-emergency-row">
              <span class="id-emergency-label">Address:</span>
              <span class="id-emergency-value">${escapeHtml(emergencyAddress)}</span>
            </div>
          </div>
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
  const deptFilter = elements.departmentFilter ? elements.departmentFilter.value : '';

  galleryState.filteredEmployees = galleryState.employees.filter(emp => {
    const matchesSearch = !searchTerm || 
      emp.employee_name.toLowerCase().includes(searchTerm) ||
      emp.id_number.toLowerCase().includes(searchTerm);

    const matchesDept = !deptFilter || emp.department === deptFilter;

    return matchesSearch && matchesDept;
  });

  renderGallery();
}

// ============================================
// Preview & Download
// ============================================
function previewID(id) {
  const emp = galleryState.employees.find(e => e.id === id);
  if (!emp) return;

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
          <span class="label">Department</span>
          <span class="value">${escapeHtml(emp.department)}</span>
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

// Make showPreviewSide available globally
window.showPreviewSide = showPreviewSide;

function closePreviewModal() {
  if (elements.previewModal) {
    elements.previewModal.classList.remove('active');
  }
  galleryState.currentEmployee = null;
}

// Download single ID as PDF
function downloadSinglePdf(id) {
  const emp = galleryState.employees.find(e => e.id === id);
  if (!emp) return;
  downloadIDPdf(emp);
}

// Download ID card as PDF using jsPDF and html2canvas - includes both front and back
// Captures FULL card content - no cropping
async function downloadIDPdf(emp) {
  showToast('Generating PDF...', 'success');

  try {
    // Create a temporary container - position off-screen but rendered
    const tempContainer = document.createElement('div');
    tempContainer.style.position = 'absolute';
    tempContainer.style.left = '-9999px';
    tempContainer.style.top = '0';
    tempContainer.style.width = '450px';  // Slightly wider to ensure no clipping
    tempContainer.style.background = '#ffffff';
    document.body.appendChild(tempContainer);
    
    // Render front side
    tempContainer.innerHTML = `
      <div class="pdf-id-card-wrapper" style="width: 420px; padding: 0; background: white; display: inline-block;">
        ${generateIDCardHtml(emp)}
      </div>
    `;

    // Force the card to have exact width, let height be natural
    const frontCardEl = tempContainer.querySelector('.id-card');
    frontCardEl.style.width = '420px';
    frontCardEl.style.minHeight = '620px';
    frontCardEl.style.height = 'auto';
    frontCardEl.style.transform = 'none';
    frontCardEl.style.margin = '0';
    frontCardEl.style.overflow = 'visible';

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
    
    // Get ACTUAL dimensions after render
    const frontHeight = Math.max(620, frontCardEl.scrollHeight, frontCardEl.offsetHeight);
    console.log('PDF Front card height:', frontHeight);
    
    // Capture front side - use ACTUAL height to prevent cropping
    const frontCanvas = await html2canvas(frontCardEl, {
      scale: 3,
      useCORS: true,
      allowTaint: true,
      backgroundColor: '#ffffff',
      width: 420,
      height: frontHeight,
      scrollY: 0,
      scrollX: 0,
      logging: false
    });

    // Render back side
    tempContainer.innerHTML = `
      <div class="pdf-id-card-wrapper" style="width: 420px; padding: 0; background: white; display: inline-block;">
        ${generateIDCardBackHtml(emp)}
      </div>
    `;
    
    const backCardEl = tempContainer.querySelector('.id-card');
    backCardEl.style.width = '420px';
    backCardEl.style.minHeight = '620px';
    backCardEl.style.height = 'auto';
    backCardEl.style.transform = 'none';
    backCardEl.style.margin = '0';
    backCardEl.style.overflow = 'visible';
    
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
    
    // Get ACTUAL back side height
    const backHeight = Math.max(620, backCardEl.scrollHeight, backCardEl.offsetHeight);
    console.log('PDF Back card height:', backHeight);
    
    // Capture back side - use ACTUAL height
    const backCanvas = await html2canvas(backCardEl, {
      scale: 3,
      useCORS: true,
      allowTaint: true,
      backgroundColor: '#ffffff',
      width: 420,
      height: backHeight,
      scrollY: 0,
      scrollX: 0,
      logging: false
    });

    // Use the taller of the two for consistent PDF page size
    const maxHeight = Math.max(frontHeight, backHeight);
    
    // Convert px to mm at 96 DPI: px * (25.4 / 96)
    const pdfWidthMm = 420 * (25.4 / 96);   // ~111.125mm
    const pdfHeightMm = maxHeight * (25.4 / 96);
    
    console.log('PDF dimensions (mm):', pdfWidthMm, 'x', pdfHeightMm);

    // Create PDF with calculated dimensions
    const { jsPDF } = window.jspdf;
    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: [pdfWidthMm, pdfHeightMm]
    });

    // Add front side - scale to fit page
    const frontImgData = frontCanvas.toDataURL('image/png', 1.0);
    const frontPdfHeight = frontHeight * (25.4 / 96);
    pdf.addImage(frontImgData, 'PNG', 0, 0, pdfWidthMm, frontPdfHeight);
    
    // Add back side on new page
    pdf.addPage([pdfWidthMm, pdfHeightMm], 'portrait');
    const backImgData = backCanvas.toDataURL('image/png', 1.0);
    const backPdfHeight = backHeight * (25.4 / 96);
    pdf.addImage(backImgData, 'PNG', 0, 0, pdfWidthMm, backPdfHeight);
    
    // Download the PDF
    pdf.save(`ID_${emp.id_number}_${emp.employee_name.replace(/\\s+/g, '_')}.pdf`);

    // Cleanup
    document.body.removeChild(tempContainer);
    
    // Mark as completed if approved
    if (emp.status === 'Approved') {
      await markAsCompleted(emp.id);
    }

    showToast('PDF downloaded successfully (Front + Back)', 'success');
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

  showToast(`Generating ${employees.length} PDFs... This may take a moment.`, 'success');
  elements.downloadAllBtn.disabled = true;
  elements.downloadAllBtn.innerHTML = `
    <svg class="spin" width="16" height="16" viewBox="0 0 16 16" fill="none">
      <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="2" stroke-dasharray="31.4" stroke-dashoffset="10"/>
    </svg>
    Downloading...
  `;

  try {
    // Create a temporary container
    const tempContainer = document.createElement('div');
    tempContainer.style.position = 'absolute';
    tempContainer.style.left = '-9999px';
    tempContainer.style.top = '0';
    tempContainer.style.width = '450px';
    tempContainer.style.background = '#ffffff';
    document.body.appendChild(tempContainer);

    const { jsPDF } = window.jspdf;

    for (let i = 0; i < employees.length; i++) {
      const emp = employees[i];
      
      // Render front side
      tempContainer.innerHTML = `
        <div class="pdf-id-card-wrapper" style="width: 420px; padding: 0; background: white; display: inline-block;">
          ${generateIDCardHtml(emp)}
        </div>
      `;
      
      const frontCardEl = tempContainer.querySelector('.id-card');
      frontCardEl.style.width = '420px';
      frontCardEl.style.minHeight = '620px';
      frontCardEl.style.height = 'auto';
      frontCardEl.style.transform = 'none';
      frontCardEl.style.overflow = 'visible';
      
      await new Promise(resolve => setTimeout(resolve, 800));
      
      const frontImages = tempContainer.querySelectorAll('img');
      await Promise.all(Array.from(frontImages).map(img => {
        if (img.complete) return Promise.resolve();
        return new Promise(resolve => {
          img.onload = resolve;
          img.onerror = resolve;
        });
      }));
      
      // Get actual height
      const frontHeight = Math.max(620, frontCardEl.scrollHeight, frontCardEl.offsetHeight);
      
      const frontCanvas = await html2canvas(frontCardEl, {
        scale: 2,
        useCORS: true,
        allowTaint: true,
        backgroundColor: '#ffffff',
        width: 420,
        height: frontHeight
      });
      
      // Render back side
      tempContainer.innerHTML = `
        <div class="pdf-id-card-wrapper" style="width: 420px; padding: 0; background: white; display: inline-block;">
          ${generateIDCardBackHtml(emp)}
        </div>
      `;
      
      const backCardEl = tempContainer.querySelector('.id-card');
      backCardEl.style.width = '420px';
      backCardEl.style.minHeight = '620px';
      backCardEl.style.height = 'auto';
      backCardEl.style.transform = 'none';
      backCardEl.style.overflow = 'visible';
      
      await new Promise(resolve => setTimeout(resolve, 500));
      
      const backImages = tempContainer.querySelectorAll('img');
      await Promise.all(Array.from(backImages).map(img => {
        if (img.complete) return Promise.resolve();
        return new Promise(resolve => {
          img.onload = resolve;
          img.onerror = resolve;
        });
      }));
      
      // Get actual height
      const backHeight = Math.max(620, backCardEl.scrollHeight, backCardEl.offsetHeight);
      
      const backCanvas = await html2canvas(backCardEl, {
        scale: 2,
        useCORS: true,
        allowTaint: true,
        backgroundColor: '#ffffff',
        width: 420,
        height: backHeight
      });

      // Calculate PDF dimensions from actual content
      const maxHeight = Math.max(frontHeight, backHeight);
      const pdfWidthMm = 420 * (25.4 / 96);
      const pdfHeightMm = maxHeight * (25.4 / 96);

      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: [pdfWidthMm, pdfHeightMm]
      });

      // Add front side
      const frontImgData = frontCanvas.toDataURL('image/png', 1.0);
      pdf.addImage(frontImgData, 'PNG', 0, 0, pdfWidthMm, frontHeight * (25.4 / 96));
      
      // Add back side
      pdf.addPage([pdfWidthMm, pdfHeightMm], 'portrait');
      const backImgData = backCanvas.toDataURL('image/png', 1.0);
      pdf.addImage(backImgData, 'PNG', 0, 0, pdfWidthMm, backHeight * (25.4 / 96));
      
      pdf.save(`ID_${emp.id_number}_${emp.employee_name.replace(/\s+/g, '_')}.pdf`);

      await new Promise(resolve => setTimeout(resolve, 300));
    }

    document.body.removeChild(tempContainer);
    showToast(`Successfully downloaded ${employees.length} PDFs (Front + Back)`, 'success');
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
