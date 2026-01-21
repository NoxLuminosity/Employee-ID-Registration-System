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
// DOM Elements
// ============================================
const elements = {
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

// ============================================
// Initialization
// ============================================
document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  fetchGalleryData();
});

function initEventListeners() {
  // Search and filter
  elements.searchInput.addEventListener('input', debounce(filterGallery, 300));
  elements.departmentFilter.addEventListener('change', filterGallery);

  // Modal
  elements.closeModal.addEventListener('click', closePreviewModal);
  elements.previewModal.addEventListener('click', (e) => {
    if (e.target === elements.previewModal) closePreviewModal();
  });

  elements.downloadBtn.addEventListener('click', () => {
    if (galleryState.currentEmployee) {
      downloadIDPdf(galleryState.currentEmployee);
    }
  });

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
  showLoading(true);

  try {
    // VERCEL FIX: Include credentials to ensure JWT cookie is sent with request
    // Without this, serverless functions may not receive the authentication cookie
    const response = await fetch('/hr/api/employees', {
      credentials: 'include'
    });
    const data = await response.json();

    if (data.success) {
      // Filter only approved and completed IDs
      const allEmployees = data.employees || [];
      galleryState.employees = allEmployees.filter(
        emp => emp.status === 'Approved' || emp.status === 'Completed'
      );
      galleryState.filteredEmployees = [...galleryState.employees];
      updateStats();
      renderGallery();
      
      // Show/hide Download All button based on whether there are IDs
      if (elements.downloadAllBtn) {
        elements.downloadAllBtn.style.display = galleryState.employees.length > 0 ? 'flex' : 'none';
      }
    } else {
      throw new Error(data.error || 'Failed to fetch data');
    }
  } catch (error) {
    console.error('Error fetching gallery data:', error);
    showToast('Failed to load gallery data', 'error');
    galleryState.employees = [];
    galleryState.filteredEmployees = [];
    updateStats();
    renderGallery();
  } finally {
    showLoading(false);
  }
}

// ============================================
// UI Updates
// ============================================
function showLoading(show) {
  galleryState.isLoading = show;
  elements.loadingState.style.display = show ? 'flex' : 'none';
  elements.gallerySection.style.display = show ? 'none' : 'block';
}

function updateStats() {
  const approved = galleryState.employees.filter(e => e.status === 'Approved').length;
  const completed = galleryState.employees.filter(e => e.status === 'Completed').length;
  
  elements.totalApproved.textContent = approved;
  elements.totalCompleted.textContent = completed;
}

function renderGallery() {
  const employees = galleryState.filteredEmployees;

  if (employees.length === 0) {
    elements.galleryGrid.innerHTML = '';
    elements.emptyState.style.display = 'flex';
    return;
  }

  elements.emptyState.style.display = 'none';

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

  elements.galleryGrid.innerHTML = cards;
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
            <div class="id-logo-group">
              <span class="id-logo-spm">SPM</span>
              <span class="id-logo-divider">|</span>
            </div>
            <span class="id-logo-text">S.P. MADRID</span>
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

// ============================================
// Filtering
// ============================================
function filterGallery() {
  const searchTerm = elements.searchInput.value.toLowerCase().trim();
  const deptFilter = elements.departmentFilter.value;

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

  elements.modalBody.innerHTML = `
    <div class="id-preview-wrapper">
      ${generateIDCardHtml(emp)}
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
          <span class="label">Status</span>
          <span class="value"><span class="status-badge ${emp.status.toLowerCase()}">${emp.status}</span></span>
        </div>
      </div>
    </div>
  `;

  elements.previewModal.classList.add('active');
}

function closePreviewModal() {
  elements.previewModal.classList.remove('active');
  galleryState.currentEmployee = null;
}

// Download single ID as PDF
function downloadSinglePdf(id) {
  const emp = galleryState.employees.find(e => e.id === id);
  if (!emp) return;
  downloadIDPdf(emp);
}

// Download ID card as PDF using jsPDF and html2canvas
async function downloadIDPdf(emp) {
  showToast('Generating PDF...', 'success');

  try {
    // Create a temporary container for the ID card
    const tempContainer = document.createElement('div');
    tempContainer.style.position = 'absolute';
    tempContainer.style.left = '-9999px';
    tempContainer.style.top = '0';
    tempContainer.innerHTML = `<div class="pdf-id-card-wrapper">${generateIDCardHtml(emp)}</div>`;
    document.body.appendChild(tempContainer);

    // Wait a bit for images to load
    await new Promise(resolve => setTimeout(resolve, 800));

    const idCardEl = tempContainer.querySelector('.id-card');
    
    // Use html2canvas to capture the ID card
    const canvas = await html2canvas(idCardEl, {
      scale: 2,
      useCORS: true,
      allowTaint: true,
      backgroundColor: '#ffffff'
    });

    // Create PDF with jsPDF - using the actual ID card dimensions ratio
    const { jsPDF } = window.jspdf;
    // ID card is 420px wide x ~620px tall (including both sections)
    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: [85.6, 125] // Proportional to ID card design
    });

    const imgData = canvas.toDataURL('image/png');
    pdf.addImage(imgData, 'PNG', 0, 0, 85.6, 125);
    
    // Download the PDF
    pdf.save(`ID_${emp.id_number}_${emp.employee_name.replace(/\s+/g, '_')}.pdf`);

    // Cleanup
    document.body.removeChild(tempContainer);
    
    // Mark as completed if approved
    if (emp.status === 'Approved') {
      await markAsCompleted(emp.id);
    }

    showToast('PDF downloaded successfully', 'success');
  } catch (error) {
    console.error('Error generating PDF:', error);
    showToast('Failed to generate PDF. Please try again.', 'error');
  }
}

// Download all IDs as PDFs
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
    // Create a temporary container for rendering
    const tempContainer = document.createElement('div');
    tempContainer.style.position = 'absolute';
    tempContainer.style.left = '-9999px';
    tempContainer.style.top = '0';
    document.body.appendChild(tempContainer);

    const { jsPDF } = window.jspdf;

    for (let i = 0; i < employees.length; i++) {
      const emp = employees[i];
      
      // Render the ID card
      tempContainer.innerHTML = `<div class="pdf-id-card-wrapper">${generateIDCardHtml(emp)}</div>`;
      
      // Wait for images to load
      await new Promise(resolve => setTimeout(resolve, 600));

      const idCardEl = tempContainer.querySelector('.id-card');
      
      // Capture with html2canvas
      const canvas = await html2canvas(idCardEl, {
        scale: 2,
        useCORS: true,
        allowTaint: true,
        backgroundColor: '#ffffff'
      });

      // Create PDF (portrait format to match full ID card design)
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: [85.6, 125]
      });

      const imgData = canvas.toDataURL('image/png');
      pdf.addImage(imgData, 'PNG', 0, 0, 85.6, 125);
      
      // Download
      pdf.save(`ID_${emp.id_number}_${emp.employee_name.replace(/\s+/g, '_')}.pdf`);

      // Small delay between downloads to prevent browser blocking
      await new Promise(resolve => setTimeout(resolve, 200));
    }

    // Cleanup
    document.body.removeChild(tempContainer);

    showToast(`Successfully downloaded ${employees.length} PDFs`, 'success');
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
