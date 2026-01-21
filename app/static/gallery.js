/**
 * ID Gallery JavaScript
 * Handles gallery display and ID card downloads
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
      downloadID(galleryState.currentEmployee.id);
    }
  });

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
    const response = await fetch('/hr/api/employees');
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
    // Priority for ID card photo: 1) nobg (background removed), 2) AI photo, 3) original
    const idPhotoUrl = emp.nobg_photo_url || emp.new_photo_url || emp.photo_url;
    const isEnhanced = emp.nobg_photo_url || emp.new_photo_url;
    const photoHtml = idPhotoUrl 
      ? `<img src="${idPhotoUrl}" alt="${emp.employee_name}"${isEnhanced ? ' class="ai-enhanced"' : ''}>`
      : `<div class="id-card-photo-placeholder">👤</div>`;

    const statusClass = emp.status.toLowerCase();

    return `
      <div class="id-card" data-id="${emp.id}">
        <div class="id-card-header">
          <span class="id-card-company">Company ID Card</span>
          <span class="id-card-badge">${emp.department}</span>
        </div>
        <div class="id-card-body">
          <div class="id-card-photo">
            ${photoHtml}
          </div>
          <div class="id-card-info">
            <div class="id-card-name">${escapeHtml(emp.employee_name)}</div>
            <div class="id-card-position">${escapeHtml(emp.position)}</div>
            <div class="id-card-department">${escapeHtml(emp.department)} Department</div>
            <div class="id-card-id">ID: ${escapeHtml(emp.id_number)}</div>
          </div>
        </div>
        <div class="id-card-footer">
          <div class="id-card-status">
            <span class="status-badge ${statusClass}">${emp.status}</span>
          </div>
          <div class="id-card-actions">
            <button class="btn-preview" onclick="previewID(${emp.id})">Preview</button>
            <button class="btn-download" onclick="downloadID(${emp.id})">Download</button>
          </div>
        </div>
      </div>
    `;
  }).join('');

  elements.galleryGrid.innerHTML = cards;
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

  // Priority for ID card photo: 1) nobg (background removed), 2) AI photo, 3) original
  const idPhotoUrl = emp.nobg_photo_url || emp.new_photo_url || emp.photo_url;
  const isEnhanced = emp.nobg_photo_url || emp.new_photo_url;
  const photoHtml = idPhotoUrl 
    ? `<img src="${idPhotoUrl}" alt="${emp.employee_name}" class="id-preview-photo${isEnhanced ? ' ai-enhanced' : ''}">`
    : '<div class="id-card-photo-placeholder" style="width:120px;height:150px;">👤</div>';

  const signatureHtml = emp.signature_url 
    ? `<img src="${emp.signature_url}" alt="Signature" class="id-preview-signature">`
    : '<span style="color: var(--color-text-muted); font-size: 0.8rem;">No signature</span>';

  elements.modalBody.innerHTML = `
    <div class="id-preview-content">
      <div class="id-preview-card">
        <div class="id-preview-header">
          <h3>Employee ID Card</h3>
          <p>Official Identification</p>
        </div>
        <div class="id-preview-body">
          ${photoHtml}
          <div class="id-preview-details">
            <div class="id-preview-name">${escapeHtml(emp.employee_name)}</div>
            <div class="id-preview-position">${escapeHtml(emp.position)}</div>
            <div class="id-preview-department">${escapeHtml(emp.department)} Department</div>
            <div class="id-preview-info">
              <div class="id-preview-info-item">
                <span>ID Number</span>
                <span>${escapeHtml(emp.id_number)}</span>
              </div>
              <div class="id-preview-info-item">
                <span>Email</span>
                <span>${escapeHtml(emp.email)}</span>
              </div>
              <div class="id-preview-info-item">
                <span>Phone</span>
                <span>${escapeHtml(emp.personal_number)}</span>
              </div>
              <div class="id-preview-info-item">
                <span>Status</span>
                <span>${emp.status}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="id-preview-footer">
          ${signatureHtml}
          <div class="id-preview-qr">QR Code</div>
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

async function downloadID(id) {
  const emp = galleryState.employees.find(e => e.id === id);
  if (!emp) return;

  showToast('Generating ID card PDF...', 'success');

  try {
    const response = await fetch(`/hr/api/employees/${id}/download-id`);
    
    if (response.ok) {
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ID_${emp.id_number}_${emp.employee_name.replace(/\s+/g, '_')}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
      
      // Mark as completed if it was approved
      if (emp.status === 'Approved') {
        await markAsCompleted(id);
      }
      
      showToast('ID card downloaded successfully', 'success');
    } else {
      const data = await response.json();
      throw new Error(data.error || 'Download failed');
    }
  } catch (error) {
    console.error('Error downloading ID:', error);
    showToast('ID template is being finalized. Download will be available soon.', 'error');
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
