/**
 * SPMA Form JavaScript
 * Handles the SPMA-specific form functionality
 */

document.addEventListener('DOMContentLoaded', function() {
  // Initialize SPMA form
  initSpmaForm();
});

function initSpmaForm() {
  // Initialize suffix dropdown
  initSuffixDropdown();
  
  // Initialize photo upload
  initPhotoUpload();
  
  // Initialize signature pad
  initSignaturePad();
  
  // Initialize form submission
  initFormSubmission();
  
  // Initialize cancel button
  initCancelButton();
  
  // Initialize live preview updates
  initLivePreview();
  
  // Initialize ID card flip
  initIdCardFlip();
}

// Suffix dropdown handler
function initSuffixDropdown() {
  const suffixSelect = document.getElementById('suffix');
  const customGroup = document.getElementById('suffix_custom_group');
  
  if (suffixSelect && customGroup) {
    suffixSelect.addEventListener('change', function() {
      if (this.value === 'Other') {
        customGroup.style.display = 'block';
      } else {
        customGroup.style.display = 'none';
      }
      updateReviewSection();
    });
  }
}

// Photo upload handler
function initPhotoUpload() {
  const photoInput = document.getElementById('photo');
  const uploadArea = document.getElementById('photoUploadArea');
  const photoComparison = document.getElementById('photoComparison');
  const photoPreviewImg = document.getElementById('photoPreviewImg');
  
  if (photoInput && uploadArea) {
    uploadArea.addEventListener('click', () => photoInput.click());
    
    uploadArea.addEventListener('dragover', (e) => {
      e.preventDefault();
      uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
      uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
      e.preventDefault();
      uploadArea.classList.remove('dragover');
      if (e.dataTransfer.files.length > 0) {
        photoInput.files = e.dataTransfer.files;
        handlePhotoChange(photoInput.files[0]);
      }
    });
    
    photoInput.addEventListener('change', function() {
      if (this.files && this.files[0]) {
        handlePhotoChange(this.files[0]);
      }
    });
  }
}

function handlePhotoChange(file) {
  const photoComparison = document.getElementById('photoComparison');
  const photoPreviewImg = document.getElementById('photoPreviewImg');
  const uploadArea = document.getElementById('photoUploadArea');
  const photoPreview = document.getElementById('photoPreview');
  
  if (file && photoPreviewImg) {
    const reader = new FileReader();
    reader.onload = function(e) {
      photoPreviewImg.src = e.target.result;
      if (photoPreview) {
        photoPreview.style.display = 'block';
      }
      if (uploadArea) {
        uploadArea.style.display = 'none';
      }
      
      // Update ID preview
      updateIdCardPreview();
      updateReviewSection();
    };
    reader.readAsDataURL(file);
  }
}

// Signature pad
let signaturePad = null;

function initSignaturePad() {
  const canvas = document.getElementById('signaturePad');
  const clearBtn = document.getElementById('clearSignature');
  const signatureData = document.getElementById('signature_data');
  
  if (!canvas) return;
  
  const ctx = canvas.getContext('2d');
  let isDrawing = false;
  let lastX = 0;
  let lastY = 0;
  
  // Set canvas size
  function resizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
    ctx.strokeStyle = '#000';
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
  }
  
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);
  
  function getCoordinates(e) {
    const rect = canvas.getBoundingClientRect();
    if (e.touches) {
      return {
        x: e.touches[0].clientX - rect.left,
        y: e.touches[0].clientY - rect.top
      };
    }
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    };
  }
  
  function startDrawing(e) {
    isDrawing = true;
    const coords = getCoordinates(e);
    lastX = coords.x;
    lastY = coords.y;
  }
  
  function draw(e) {
    if (!isDrawing) return;
    e.preventDefault();
    
    const coords = getCoordinates(e);
    ctx.beginPath();
    ctx.moveTo(lastX, lastY);
    ctx.lineTo(coords.x, coords.y);
    ctx.stroke();
    
    lastX = coords.x;
    lastY = coords.y;
  }
  
  function stopDrawing() {
    if (isDrawing) {
      isDrawing = false;
      saveSignature();
    }
  }
  
  function saveSignature() {
    if (signatureData) {
      signatureData.value = canvas.toDataURL('image/png');
      updateIdCardPreview();
      updateReviewSection();
    }
  }
  
  // Mouse events
  canvas.addEventListener('mousedown', startDrawing);
  canvas.addEventListener('mousemove', draw);
  canvas.addEventListener('mouseup', stopDrawing);
  canvas.addEventListener('mouseout', stopDrawing);
  
  // Touch events
  canvas.addEventListener('touchstart', startDrawing, { passive: false });
  canvas.addEventListener('touchmove', draw, { passive: false });
  canvas.addEventListener('touchend', stopDrawing);
  
  // Clear button
  if (clearBtn) {
    clearBtn.addEventListener('click', function() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (signatureData) {
        signatureData.value = '';
      }
      updateIdCardPreview();
      updateReviewSection();
    });
  }
}

// Live preview updates
function initLivePreview() {
  const inputs = document.querySelectorAll('#spmaRegistrationForm input, #spmaRegistrationForm select');
  inputs.forEach(input => {
    input.addEventListener('input', () => {
      updateIdCardPreview();
      updateReviewSection();
    });
    input.addEventListener('change', () => {
      updateIdCardPreview();
      updateReviewSection();
    });
  });
  
  // Initial update
  updateIdCardPreview();
  updateReviewSection();
}

function updateIdCardPreview() {
  // Get form values
  const firstName = document.getElementById('first_name')?.value || '';
  const middleInitial = document.getElementById('middle_initial')?.value || '';
  const lastName = document.getElementById('last_name')?.value || '';
  const suffix = document.getElementById('suffix')?.value || '';
  const idNumber = document.getElementById('id_number')?.value || '';
  
  // Build full name
  let fullName = firstName;
  if (middleInitial) fullName += ' ' + middleInitial;
  if (lastName) fullName += ' ' + lastName;
  if (suffix && suffix !== 'Other') fullName += ' ' + suffix;
  
  // Update ID card elements
  const nicknameEl = document.getElementById('id_preview_nickname');
  const fullnameEl = document.getElementById('id_preview_fullname');
  const idnumberEl = document.getElementById('id_preview_idnumber');
  const positionEl = document.getElementById('id_preview_position');
  const photoEl = document.getElementById('id_preview_photo');
  const photoPlaceholder = document.getElementById('id_preview_photo_placeholder');
  const signatureEl = document.getElementById('id_preview_signature');
  const signaturePlaceholder = document.getElementById('id_preview_signature_placeholder');
  
  if (nicknameEl) nicknameEl.textContent = firstName.split(' ')[0] || 'SPMA';
  if (fullnameEl) fullnameEl.textContent = fullName || 'Full Name';
  if (idnumberEl) idnumberEl.textContent = idNumber || 'LO-001';
  if (positionEl) positionEl.textContent = 'Legal Officer';
  
  // Update photo
  const photoPreview = document.getElementById('photoPreviewImg');
  if (photoEl && photoPreview && photoPreview.src) {
    photoEl.src = photoPreview.src;
    photoEl.style.display = 'block';
    if (photoPlaceholder) photoPlaceholder.style.display = 'none';
  }
  
  // Update signature
  const signatureData = document.getElementById('signature_data')?.value;
  if (signatureEl && signatureData) {
    signatureEl.src = signatureData;
    signatureEl.style.display = 'block';
    if (signaturePlaceholder) signaturePlaceholder.style.display = 'none';
  }
  
  // Update back contact label
  const contactLabel = document.getElementById('id_back_contact_label');
  if (contactLabel) {
    contactLabel.textContent = firstName ? `${firstName.split(' ')[0]}'s Contact` : "'s Contact";
  }
}

function updateReviewSection() {
  // Update review fields
  const fields = [
    { id: 'first_name', reviewId: 'review_first_name' },
    { id: 'middle_initial', reviewId: 'review_middle_initial' },
    { id: 'last_name', reviewId: 'review_last_name' },
    { id: 'suffix', reviewId: 'review_suffix' },
    { id: 'field_clearance', reviewId: 'review_field_clearance' },
    { id: 'id_number', reviewId: 'review_id_number' },
    { id: 'location_branch', reviewId: 'review_location_branch' },
    { id: 'division', reviewId: 'review_division' },
    { id: 'department', reviewId: 'review_department' },
    { id: 'email', reviewId: 'review_email' },
    { id: 'personal_number', reviewId: 'review_personal_number' }
  ];
  
  fields.forEach(field => {
    const input = document.getElementById(field.id);
    const review = document.getElementById(field.reviewId);
    if (input && review) {
      review.textContent = input.value || '-';
    }
  });
  
  // Update photo preview
  const photoPreview = document.getElementById('photoPreviewImg');
  const reviewPhoto = document.getElementById('review_photo');
  const reviewPhotoPlaceholder = document.getElementById('review_photo_placeholder');
  
  if (photoPreview && photoPreview.src && reviewPhoto) {
    reviewPhoto.src = photoPreview.src;
    reviewPhoto.style.display = 'block';
    if (reviewPhotoPlaceholder) reviewPhotoPlaceholder.style.display = 'none';
  }
  
  // Update signature preview
  const signatureData = document.getElementById('signature_data')?.value;
  const reviewSignature = document.getElementById('review_signature');
  const reviewSignaturePlaceholder = document.getElementById('review_signature_placeholder');
  
  if (signatureData && reviewSignature) {
    reviewSignature.src = signatureData;
    reviewSignature.style.display = 'block';
    if (reviewSignaturePlaceholder) reviewSignaturePlaceholder.style.display = 'none';
  }
}

// ID Card flip
function initIdCardFlip() {
  // Expose to global scope
  window.showCardSide = showCardSide;
}

function showCardSide(side) {
  const frontCard = document.getElementById('idCardFront');
  const backCard = document.getElementById('idCardBack');
  const buttons = document.querySelectorAll('.flip-btn');
  
  buttons.forEach(btn => {
    btn.classList.toggle('active', btn.dataset.side === side);
  });
  
  if (side === 'front') {
    if (frontCard) frontCard.style.display = 'block';
    if (backCard) backCard.style.display = 'none';
  } else {
    if (frontCard) frontCard.style.display = 'none';
    if (backCard) backCard.style.display = 'block';
  }
}

// Form submission
function initFormSubmission() {
  const form = document.getElementById('spmaRegistrationForm');
  
  if (form) {
    form.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const submitBtn = document.getElementById('btnSubmit');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Submitting...';
      }
      
      try {
        const formData = new FormData(form);
        
        // Add form type
        formData.set('form_type', 'SPMA');
        
        const response = await fetch('/submit', {
          method: 'POST',
          body: formData
        });
        
        const result = await response.json();
        
        if (response.ok && result.success === true) {
          // Show success toast
          showToast('Success!', 'Your SPMA ID registration has been submitted successfully. HR will review and process your request shortly.', 'success');
          
          // Show success modal after brief delay
          setTimeout(() => {
            showSuccessModal();
          }, 1500);
          
          // Reset button text but keep it disabled
          if (submitBtn) {
            submitBtn.textContent = 'Submitted';
          }
        } else {
          showMessage(result.message || result.error || 'Submission failed', 'error');
          
          // Re-enable button on error
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit SPMA Application';
          }
        }
      } catch (error) {
        console.error('Submission error:', error);
        showMessage('An error occurred. Please try again.', 'error');
        
        // Re-enable button on error
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Submit SPMA Application';
        }
      }
    });
  }
}

// Cancel button
function initCancelButton() {
  const cancelBtn = document.getElementById('btnCancel');
  
  if (cancelBtn) {
    cancelBtn.addEventListener('click', function() {
      if (confirm('Are you sure you want to cancel? All entered data will be lost.')) {
        window.location.href = '/choose-form';
      }
    });
  }
}

// Message display
function showMessage(message, type) {
  const container = document.getElementById('messageContainer');
  if (container) {
    container.innerHTML = `<div class="message ${type}">${message}</div>`;
    container.scrollIntoView({ behavior: 'smooth' });
    
    if (type !== 'success') {
      setTimeout(() => {
        container.innerHTML = '';
      }, 5000);
    }
  }
}

// Go back function
function goBack() {
  window.location.href = '/choose-form';
}
window.goBack = goBack;

// Show success modal
function showSuccessModal() {
  const modal = document.getElementById('successModal');
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

// Hide success modal
function hideSuccessModal() {
  const modal = document.getElementById('successModal');
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

// Submit another form
function submitAnotherForm() {
  hideSuccessModal();
  // Reset the form completely
  const form = document.getElementById('spmaRegistrationForm');
  if (form) form.reset();
  
  // Clear signature canvas
  const canvas = document.getElementById('signaturePad');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }
  const signatureData = document.getElementById('signature_data');
  if (signatureData) signatureData.value = '';
  
  // Reset photo preview
  const photoPreview = document.getElementById('photoPreview');
  const photoUploadArea = document.getElementById('photoUploadArea');
  const photoPreviewImg = document.getElementById('photoPreviewImg');
  
  if (photoPreview) photoPreview.style.display = 'none';
  if (photoUploadArea) photoUploadArea.style.display = 'flex';
  if (photoPreviewImg) photoPreviewImg.src = '';
  
  // Update previews
  updateIdCardPreview();
  updateReviewSection();
  
  // Scroll to top
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
window.submitAnotherForm = submitAnotherForm;

// Remove photo function
function removePhoto() {
  const photoInput = document.getElementById('photo');
  const photoPreview = document.getElementById('photoPreview');
  const photoUploadArea = document.getElementById('photoUploadArea');
  const photoPreviewImg = document.getElementById('photoPreviewImg');
  
  if (photoInput) {
    photoInput.value = '';
  }
  if (photoPreviewImg) {
    photoPreviewImg.src = '';
  }
  if (photoPreview) {
    photoPreview.style.display = 'none';
  }
  if (photoUploadArea) {
    photoUploadArea.style.display = 'flex';
  }
  
  // Update ID preview and review section
  updateIdCardPreview();
  updateReviewSection();
}
window.removePhoto = removePhoto;

// Toast notification function
function showToast(title, message, type = 'success') {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  
  const icon = type === 'success' 
    ? '<svg class="toast-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>'
    : '<svg class="toast-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>';
  
  toast.innerHTML = `
    ${icon}
    <div class="toast-content">
      <div class="toast-title">${title}</div>
      <div class="toast-message">${message}</div>
    </div>
    <button class="toast-close" onclick="this.parentElement.remove()">
      <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
      </svg>
    </button>
  `;
  
  container.appendChild(toast);
  
  // Trigger animation
  setTimeout(() => toast.classList.add('show'), 10);
  
  // Auto-remove after 5 seconds
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 5000);
}
window.showToast = showToast;
