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
  currentEmployee: null
};

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
async function fetchGalleryData() {
  console.log('fetchGalleryData: Starting data fetch...');
  console.log('fetchGalleryData: Current URL:', window.location.href);
  showLoading(true);

  // VERCEL FIX: Add timeout to prevent infinite loading on serverless cold starts
  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    console.log('fetchGalleryData: Request timeout - aborting');
    controller.abort();
  }, 15000); // 15 second timeout

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
    
    // VERCEL FIX: Handle abort/timeout gracefully
    if (error.name === 'AbortError') {
      showToast('Request timed out. Please refresh the page.', 'error');
    } else {
      showToast('Failed to load gallery data: ' + error.message, 'error');
    }
    
    // VERCEL FIX: Always set empty state on error to prevent infinite loading
    galleryState.employees = [];
    galleryState.filteredEmployees = [];
    updateStats();
    renderGallery();
  } finally {
    console.log('fetchGalleryData: Hiding loading state');
    // VERCEL FIX: Always hide loading state, even on error
    showLoading(false);
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
              <span>${escapeHtml(emp.department)}</span>
              <span class="id-dash">-</span>
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
// CRITICAL: Captures ACTUAL rendered dimensions to prevent cropping
async function downloadIDPdf(emp) {
  showToast('Generating PDF...', 'success');

  try {
    // Create a temporary container - VISIBLE position for accurate rendering
    const tempContainer = document.createElement('div');
    tempContainer.style.position = 'fixed';
    tempContainer.style.left = '0';
    tempContainer.style.top = '0';
    tempContainer.style.zIndex = '99999';
    tempContainer.style.background = '#ffffff';
    tempContainer.style.opacity = '0.01';  // Nearly invisible but still rendered
    tempContainer.style.pointerEvents = 'none';
    
    // Render front side - DO NOT constrain dimensions, let card render naturally
    tempContainer.innerHTML = `
      <div class="pdf-id-card-wrapper" style="display: inline-block; background: white; padding: 0;">
        ${generateIDCardHtml(emp)}
      </div>
    `;
    document.body.appendChild(tempContainer);

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

    const frontCardEl = tempContainer.querySelector('.id-card');
    
    // Get ACTUAL rendered dimensions - DO NOT hardcode
    const frontRect = frontCardEl.getBoundingClientRect();
    const frontWidth = Math.ceil(frontRect.width);
    const frontHeight = Math.ceil(frontRect.height);
    console.log('PDF: Front card actual dimensions:', frontWidth, 'x', frontHeight);
    
    // Capture front side - use ACTUAL dimensions, no cropping
    const frontCanvas = await html2canvas(frontCardEl, {
      scale: 3,
      useCORS: true,
      allowTaint: true,
      backgroundColor: '#ffffff',
      width: frontWidth,
      height: frontHeight,
      windowWidth: frontWidth,
      windowHeight: frontHeight,
      logging: false,
      onclone: (clonedDoc, element) => {
        // Ensure cloned element has no transforms that could affect size
        element.style.transform = 'none';
        element.style.margin = '0';
      }
    });

    // Render back side
    tempContainer.innerHTML = `
      <div class="pdf-id-card-wrapper" style="display: inline-block; background: white; padding: 0;">
        ${generateIDCardBackHtml(emp)}
      </div>
    `;
    
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
    
    const backCardEl = tempContainer.querySelector('.id-card');
    
    // Get ACTUAL back side dimensions
    const backRect = backCardEl.getBoundingClientRect();
    const backWidth = Math.ceil(backRect.width);
    const backHeight = Math.ceil(backRect.height);
    console.log('PDF: Back card actual dimensions:', backWidth, 'x', backHeight);
    
    // Capture back side with ACTUAL dimensions
    const backCanvas = await html2canvas(backCardEl, {
      scale: 3,
      useCORS: true,
      allowTaint: true,
      backgroundColor: '#ffffff',
      width: backWidth,
      height: backHeight,
      windowWidth: backWidth,
      windowHeight: backHeight,
      logging: false,
      onclone: (clonedDoc, element) => {
        element.style.transform = 'none';
        element.style.margin = '0';
      }
    });

    // Calculate PDF page size from canvas dimensions (maintain exact aspect ratio)
    // Use larger of front/back for consistent page size
    const maxWidth = Math.max(frontCanvas.width, backCanvas.width);
    const maxHeight = Math.max(frontCanvas.height, backCanvas.height);
    
    // Convert to mm (assuming 96 DPI screen, scale 3x = 288 DPI effective)
    // 1 inch = 25.4mm, 288 pixels per inch
    const pdfWidthMm = (maxWidth / 3) * (25.4 / 96);
    const pdfHeightMm = (maxHeight / 3) * (25.4 / 96);
    
    console.log('PDF: Page size (mm):', pdfWidthMm.toFixed(2), 'x', pdfHeightMm.toFixed(2));

    // Create PDF with EXACT dimensions from captured canvas
    const { jsPDF } = window.jspdf;
    const pdf = new jsPDF({
      orientation: pdfHeightMm > pdfWidthMm ? 'portrait' : 'landscape',
      unit: 'mm',
      format: [pdfWidthMm, pdfHeightMm]
    });

    // Add front side - fill entire page
    const frontImgData = frontCanvas.toDataURL('image/png', 1.0);
    pdf.addImage(frontImgData, 'PNG', 0, 0, pdfWidthMm, pdfHeightMm);
    
    // Add back side on new page with same size
    pdf.addPage([pdfWidthMm, pdfHeightMm], pdfHeightMm > pdfWidthMm ? 'portrait' : 'landscape');
    const backImgData = backCanvas.toDataURL('image/png', 1.0);
    pdf.addImage(backImgData, 'PNG', 0, 0, pdfWidthMm, pdfHeightMm);
    
    // Download the PDF
    pdf.save(`ID_${emp.id_number}_${emp.employee_name.replace(/\s+/g, '_')}.pdf`);

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

// Download all IDs as PDFs (front and back) - uses ACTUAL rendered dimensions
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
    // Create a temporary container - nearly invisible but rendered
    const tempContainer = document.createElement('div');
    tempContainer.style.position = 'fixed';
    tempContainer.style.left = '0';
    tempContainer.style.top = '0';
    tempContainer.style.zIndex = '99999';
    tempContainer.style.background = '#ffffff';
    tempContainer.style.opacity = '0.01';
    tempContainer.style.pointerEvents = 'none';
    document.body.appendChild(tempContainer);

    const { jsPDF } = window.jspdf;

    for (let i = 0; i < employees.length; i++) {
      const emp = employees[i];
      
      // Render front side
      tempContainer.innerHTML = `
        <div class="pdf-id-card-wrapper" style="display: inline-block; background: white; padding: 0;">
          ${generateIDCardHtml(emp)}
        </div>
      `;
      
      // Wait for images to load
      await new Promise(resolve => setTimeout(resolve, 800));
      
      const frontImages = tempContainer.querySelectorAll('img');
      await Promise.all(Array.from(frontImages).map(img => {
        if (img.complete) return Promise.resolve();
        return new Promise(resolve => {
          img.onload = resolve;
          img.onerror = resolve;
        });
      }));

      const frontCardEl = tempContainer.querySelector('.id-card');
      const frontRect = frontCardEl.getBoundingClientRect();
      
      // Capture front with ACTUAL dimensions
      const frontCanvas = await html2canvas(frontCardEl, {
        scale: 2,
        useCORS: true,
        allowTaint: true,
        backgroundColor: '#ffffff',
        width: Math.ceil(frontRect.width),
        height: Math.ceil(frontRect.height),
        windowWidth: Math.ceil(frontRect.width),
        windowHeight: Math.ceil(frontRect.height)
      });
      
      // Render back side
      tempContainer.innerHTML = `
        <div class="pdf-id-card-wrapper" style="display: inline-block; background: white; padding: 0;">
          ${generateIDCardBackHtml(emp)}
        </div>
      `;
      
      await new Promise(resolve => setTimeout(resolve, 500));
      
      const backImages = tempContainer.querySelectorAll('img');
      await Promise.all(Array.from(backImages).map(img => {
        if (img.complete) return Promise.resolve();
        return new Promise(resolve => {
          img.onload = resolve;
          img.onerror = resolve;
        });
      }));
      
      const backCardEl = tempContainer.querySelector('.id-card');
      const backRect = backCardEl.getBoundingClientRect();
      
      // Capture back with ACTUAL dimensions
      const backCanvas = await html2canvas(backCardEl, {
        scale: 2,
        useCORS: true,
        allowTaint: true,
        backgroundColor: '#ffffff',
        width: Math.ceil(backRect.width),
        height: Math.ceil(backRect.height),
        windowWidth: Math.ceil(backRect.width),
        windowHeight: Math.ceil(backRect.height)
      });

      // Calculate PDF size from canvas
      const maxWidth = Math.max(frontCanvas.width, backCanvas.width);
      const maxHeight = Math.max(frontCanvas.height, backCanvas.height);
      const pdfWidthMm = (maxWidth / 2) * (25.4 / 96);
      const pdfHeightMm = (maxHeight / 2) * (25.4 / 96);

      // Create PDF with exact dimensions
      const pdf = new jsPDF({
        orientation: pdfHeightMm > pdfWidthMm ? 'portrait' : 'landscape',
        unit: 'mm',
        format: [pdfWidthMm, pdfHeightMm]
      });

      // Add front side
      const frontImgData = frontCanvas.toDataURL('image/png', 1.0);
      pdf.addImage(frontImgData, 'PNG', 0, 0, pdfWidthMm, pdfHeightMm);
      
      // Add back side on new page
      pdf.addPage([pdfWidthMm, pdfHeightMm], pdfHeightMm > pdfWidthMm ? 'portrait' : 'landscape');
      const backImgData = backCanvas.toDataURL('image/png', 1.0);
      pdf.addImage(backImgData, 'PNG', 0, 0, pdfWidthMm, pdfHeightMm);
      
      // Download
      pdf.save(`ID_${emp.id_number}_${emp.employee_name.replace(/\s+/g, '_')}.pdf`);

      // Small delay between downloads
      await new Promise(resolve => setTimeout(resolve, 300));
    }

    // Cleanup
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
