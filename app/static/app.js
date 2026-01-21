/**
 * Employee ID Registration System
 * One-Page Form with Signature Pad
 */

// ============================================
// State Management
// ============================================
const state = {
  signaturePad: null,
  isDrawing: false,
  aiGenerationController: null  // AbortController for AI generation
};

// ============================================
// DOM Elements (initialized after DOM is ready)
// ============================================
let elements = {};

// ============================================
// Initialization
// ============================================
document.addEventListener('DOMContentLoaded', () => {
  // Initialize elements after DOM is ready
  elements = {
    form: document.getElementById('registrationForm'),
    btnSubmit: document.getElementById('btnSubmit'),
    btnCancel: document.getElementById('btnCancel'),
    messageContainer: document.getElementById('messageContainer'),
    photoInput: document.getElementById('photo'),
    photoPreview: document.getElementById('photoPreview'),
    photoPreviewImg: document.getElementById('photoPreviewImg'),
    photoComparison: document.getElementById('photoComparison'),
    aiPreviewImg: document.getElementById('aiPreviewImg'),
    aiLoading: document.getElementById('aiLoading'),
    aiError: document.getElementById('aiError'),
    signatureCanvas: document.getElementById('signaturePad'),
    signatureData: document.getElementById('signature_data'),
    clearSignature: document.getElementById('clearSignature')
  };

  initPhotoUpload();
  initSignaturePad();
  initFormSubmission();
  initCancelButton();
  updateReviewSection(); // Update on load
  updateIdCardPreview(); // Update ID card preview on load
  
  // Auto-update review and ID card preview when form changes
  document.querySelectorAll('input, select, textarea').forEach(el => {
    el.addEventListener('change', () => { updateReviewSection(); updateIdCardPreview(); });
    el.addEventListener('input', () => { updateReviewSection(); updateIdCardPreview(); });
    el.addEventListener('blur', () => { updateReviewSection(); updateIdCardPreview(); });
  });
});

// ============================================
// Photo Upload with AI Generation
// ============================================
function initPhotoUpload() {
  elements.photoInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        showMessage('Photo size must be less than 5MB.', 'error');
        if (elements.photoInput) elements.photoInput.value = '';
        return;
      }

      const reader = new FileReader();
      reader.onload = async (event) => {
        const imageData = event.target.result;
        
        // Show the comparison container
        elements.photoComparison.style.display = 'grid';
        elements.photoPreview.classList.add('active');
        
        // Display original photo
        elements.photoPreviewImg.src = imageData;
        
        // Reset AI preview state
        elements.aiPreviewImg.style.display = 'none';
        elements.aiError.style.display = 'none';
        elements.aiLoading.style.display = 'flex';
        
        // Update review section
        updateReviewSection();
        
        // Update ID card preview (will show original photo until AI completes)
        updateIdCardPreview();
        
        // Generate AI headshot
        await generateAIHeadshot(imageData);
      };
      reader.readAsDataURL(file);
    }
  });
}

// ============================================
// AI Headshot Generation (with server-side background removal)
// ============================================
async function generateAIHeadshot(imageBase64) {
  const loadingText = document.getElementById('aiLoadingText');
  
  try {
    // Cancel any previous generation request
    if (state.aiGenerationController) {
      state.aiGenerationController.abort();
    }
    state.aiGenerationController = new AbortController();
    
    // Update loading text - server handles AI generation + background removal
    if (loadingText) loadingText.textContent = 'Generating AI headshot...';
    
    const response = await fetch('/generate-headshot', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ image: imageBase64 }),
      signal: state.aiGenerationController.signal
    });
    
    // Safely parse response
    const responseText = await response.text();
    let result;
    try {
      result = JSON.parse(responseText);
    } catch (parseError) {
      console.error('Non-JSON response from AI endpoint:', responseText);
      throw new Error('Server returned invalid response');
    }
    
    if (response.ok && result.success && result.generated_image) {
      // Server returns pre-processed image (already transparent if bg removal succeeded)
      const processedImageUrl = result.generated_image;
      const isTransparent = result.transparent === true;
      
      console.log(`AI headshot received: transparent=${isTransparent}, url=${processedImageUrl.substring(0, 80)}...`);
      
      // Display the image (already has transparent background from server)
      elements.aiPreviewImg.src = processedImageUrl;
      
      // Add class for proper styling if transparent
      if (isTransparent) {
        elements.aiPreviewImg.classList.add('transparent-bg');
      } else {
        elements.aiPreviewImg.classList.remove('transparent-bg');
      }
      
      elements.aiPreviewImg.style.display = 'block';
      elements.aiLoading.style.display = 'none';
      elements.aiError.style.display = 'none';
      
      // Store transparency state for ID card preview
      elements.aiPreviewImg.dataset.transparent = isTransparent ? 'true' : 'false';
      
      // Update ID card preview with the processed image
      updateIdCardPreview();
      
      if (result.message) {
        console.log('Server message:', result.message);
      }
    } else {
      throw new Error(result.error || 'Failed to generate headshot');
    }
    
  } catch (error) {
    if (error.name === 'AbortError') {
      console.log('AI generation aborted');
      return;
    }
    
    console.error('AI headshot generation error:', error);
    
    // Show error state
    elements.aiLoading.style.display = 'none';
    elements.aiPreviewImg.style.display = 'none';
    elements.aiError.style.display = 'block';
    elements.aiError.textContent = 'AI preview unavailable';
  }
}

// ============================================
// Background Removal
// ============================================
async function removeBackground(imageData, isUrl = true) {
  try {
    console.log(`Removing background from ${isUrl ? 'URL' : 'base64'}...`);
    
    const response = await fetch('/remove-background', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ 
        image: imageData,
        is_url: isUrl 
      })
    });
    
    const result = await response.json();
    
    if (response.ok && result.success && result.processed_image) {
      console.log('Background removed successfully');
      return result.processed_image;
    } else {
      console.warn('Background removal failed:', result.error || 'Unknown error');
      return null;
    }
    
  } catch (error) {
    console.error('Background removal error:', error);
    return null;
  }
}

// ============================================
// Signature Pad with Transparent Background
// ============================================
function initSignaturePad() {
  const canvas = elements.signatureCanvas;
  const ctx = canvas.getContext('2d');

  // Set canvas size explicitly
  function resizeCanvas() {
    const wrapper = canvas.parentElement;
    const rect = wrapper.getBoundingClientRect();

    // Store existing drawing
    const imageData = canvas.width > 0 ? ctx.getImageData(0, 0, canvas.width, canvas.height) : null;

    // Set actual canvas dimensions (not CSS)
    canvas.width = rect.width || 600;
    canvas.height = 200;

    // Set drawing styles
    ctx.strokeStyle = '#212529';
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    // Clear canvas with transparent background (don't fill with white)
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Restore drawing if exists
    if (imageData) {
      ctx.putImageData(imageData, 0, 0);
    }
  }

  // Initial setup with delay to ensure DOM is ready
  setTimeout(resizeCanvas, 100);
  window.addEventListener('resize', resizeCanvas);

  // Drawing state
  let lastX = 0;
  let lastY = 0;
  let isCurrentlyDrawing = false;

  function getPos(e) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    let clientX, clientY;
    if (e.touches && e.touches.length > 0) {
      clientX = e.touches[0].clientX;
      clientY = e.touches[0].clientY;
    } else {
      clientX = e.clientX;
      clientY = e.clientY;
    }

    return {
      x: (clientX - rect.left) * scaleX,
      y: (clientY - rect.top) * scaleY
    };
  }

  function startDrawing(e) {
    e.preventDefault();
    isCurrentlyDrawing = true;
    state.isDrawing = true;
    const pos = getPos(e);
    lastX = pos.x;
    lastY = pos.y;

    // Draw a dot for single clicks
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, 1, 0, Math.PI * 2);
    ctx.fill();
  }

  function draw(e) {
    if (!isCurrentlyDrawing) return;
    e.preventDefault();

    const pos = getPos(e);
    ctx.beginPath();
    ctx.moveTo(lastX, lastY);
    ctx.lineTo(pos.x, pos.y);
    ctx.stroke();

    lastX = pos.x;
    lastY = pos.y;
  }

  function stopDrawing(e) {
    if (isCurrentlyDrawing) {
      isCurrentlyDrawing = false;
      state.isDrawing = false;
      // Save signature data with transparent background (PNG format preserves transparency)
      if (elements.signatureData) elements.signatureData.value = canvas.toDataURL('image/png');
      // Update review section to show signature
      updateReviewSection();
      // Update ID card preview to show signature
      updateIdCardPreview();
    }
  }

  // Mouse events
  canvas.addEventListener('mousedown', startDrawing);
  canvas.addEventListener('mousemove', draw);
  canvas.addEventListener('mouseup', stopDrawing);
  canvas.addEventListener('mouseleave', stopDrawing);

  // Touch events - use passive: false to allow preventDefault
  canvas.addEventListener('touchstart', startDrawing, { passive: false });
  canvas.addEventListener('touchmove', draw, { passive: false });
  canvas.addEventListener('touchend', stopDrawing);
  canvas.addEventListener('touchcancel', stopDrawing);

  // Clear button
  elements.clearSignature.addEventListener('click', () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (elements.signatureData) elements.signatureData.value = '';
    updateReviewSection();
    updateIdCardPreview();
  });
}

// ============================================
// ID Card Preview - Live Data Binding
// ============================================
function updateIdCardPreview() {
  // Helper function to safely get element value
  const getValue = (id) => {
    const el = document.getElementById(id);
    if (!el) return '';
    return el.value.trim();
  };

  // Update Nickname (vertical text on blue sidebar)
  const nickname = getValue('id_nickname');
  const nicknameEl = document.getElementById('id_preview_nickname');
  if (nicknameEl) {
    nicknameEl.textContent = nickname || 'Nickname';
  }

  // Update Full Name
  const fullname = getValue('employee_name');
  const fullnameEl = document.getElementById('id_preview_fullname');
  if (fullnameEl) {
    fullnameEl.textContent = fullname || 'Employee Fullname';
  }

  // Update Department
  const department = getValue('department');
  const departmentEl = document.getElementById('id_preview_department');
  if (departmentEl) {
    departmentEl.textContent = department || 'Department';
  }

  // Update Position
  const position = getValue('position');
  const positionEl = document.getElementById('id_preview_position');
  if (positionEl) {
    positionEl.textContent = position || 'Position';
  }

  // Update ID Number
  const idNumber = getValue('id_number');
  const idNumberEl = document.getElementById('id_preview_idnumber');
  if (idNumberEl) {
    idNumberEl.textContent = idNumber || 'ID Number';
  }

  // Update Photo - prefer AI generated (with transparent bg), fallback to original
  const aiPreviewImg = document.getElementById('aiPreviewImg');
  const photoPreviewImg = document.getElementById('photoPreviewImg');
  const idPhotoEl = document.getElementById('id_preview_photo');
  const idPhotoPlaceholder = document.getElementById('id_preview_photo_placeholder');
  
  let photoSrc = '';
  let hasTransparentBg = false;
  
  // Check AI generated photo first (if visible and has src)
  if (aiPreviewImg && aiPreviewImg.style.display !== 'none' && aiPreviewImg.src && 
      (aiPreviewImg.src.startsWith('data:') || aiPreviewImg.src.startsWith('http') || aiPreviewImg.src.startsWith('blob:'))) {
    photoSrc = aiPreviewImg.src;
    // Check transparency from data attribute (set by server response) or class
    hasTransparentBg = aiPreviewImg.dataset.transparent === 'true' || aiPreviewImg.classList.contains('transparent-bg');
  }
  // Fallback to original photo (no transparency)
  else if (photoPreviewImg && photoPreviewImg.src && 
           (photoPreviewImg.src.startsWith('data:') || photoPreviewImg.src.startsWith('blob:'))) {
    photoSrc = photoPreviewImg.src;
    hasTransparentBg = false;
  }
  
  if (idPhotoEl && idPhotoPlaceholder) {
    if (photoSrc) {
      idPhotoEl.src = photoSrc;
      idPhotoEl.style.display = 'block';
      idPhotoPlaceholder.style.display = 'none';
      
      // Add has-image class to container to hide background pattern
      const photoContainer = idPhotoEl.closest('.id-photo-container');
      if (photoContainer) {
        photoContainer.classList.add('has-image');
      }
      
      // Apply transparent-bg class for styling hints (both use cover now)
      if (hasTransparentBg) {
        idPhotoEl.classList.add('transparent-bg');
      } else {
        idPhotoEl.classList.remove('transparent-bg');
      }
    } else {
      idPhotoEl.style.display = 'none';
      idPhotoEl.removeAttribute('src');
      idPhotoEl.classList.remove('transparent-bg');
      idPhotoPlaceholder.style.display = 'block';
      
      // Remove has-image class to show background pattern
      const photoContainer = idPhotoEl.closest('.id-photo-container');
      if (photoContainer) {
        photoContainer.classList.remove('has-image');
      }
    }
  }

  // Update Signature
  const signatureData = document.getElementById('signature_data');
  const idSignatureEl = document.getElementById('id_preview_signature');
  const idSignaturePlaceholder = document.getElementById('id_preview_signature_placeholder');
  
  const signatureSrc = signatureData ? signatureData.value : '';
  const hasSignature = signatureSrc && signatureSrc.startsWith('data:');
  
  if (idSignatureEl && idSignaturePlaceholder) {
    if (hasSignature) {
      idSignatureEl.src = signatureSrc;
      idSignatureEl.style.display = 'block';
      idSignaturePlaceholder.style.display = 'none';
      
      // Add has-image class to container to hide background pattern
      const signatureContainer = idSignatureEl.closest('.id-signature-area');
      if (signatureContainer) {
        signatureContainer.classList.add('has-image');
      }
    } else {
      idSignatureEl.style.display = 'none';
      idSignatureEl.removeAttribute('src');
      idSignaturePlaceholder.style.display = 'block';
      
      // Remove has-image class to show background pattern
      const signatureContainer = idSignatureEl.closest('.id-signature-area');
      if (signatureContainer) {
        signatureContainer.classList.remove('has-image');
      }
    }
  }
}

// ============================================
// Review Section
// ============================================
function updateReviewSection() {
  // Helper function to safely get element value
  const getValue = (id) => {
    const el = document.getElementById(id);
    if (!el) return '-';
    const val = el.value;
    return (val && val.trim() !== '') ? val : '-';
  };

  // Helper function to safely set text content
  const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) {
      el.textContent = value;
    }
  };

  // Update text fields - Personal Details
  setText('review_employee_name', getValue('employee_name'));
  setText('review_id_nickname', getValue('id_nickname'));
  setText('review_id_number', getValue('id_number'));

  // Update text fields - Work Details
  setText('review_position', getValue('position'));
  setText('review_department', getValue('department'));

  // Update text fields - Contact Information
  setText('review_email', getValue('email'));
  setText('review_personal_number', getValue('personal_number'));

  // Photo preview
  const photoPreviewImg = document.getElementById('photoPreviewImg');
  const reviewPhoto = document.getElementById('review_photo');
  const reviewPhotoPlaceholder = document.getElementById('review_photo_placeholder');
  
  // Check if photo has been uploaded - must have a valid data: or blob: URL
  // Also check the file preview is active (means a file was selected)
  const photoPreview = document.getElementById('photoPreview');
  const isPhotoActive = photoPreview && photoPreview.classList.contains('active');
  const photoSrc = photoPreviewImg ? photoPreviewImg.getAttribute('src') : '';
  const hasPhoto = isPhotoActive && photoSrc && (photoSrc.startsWith('data:') || photoSrc.startsWith('blob:'));
  
  if (reviewPhoto && reviewPhotoPlaceholder) {
    if (hasPhoto) {
      reviewPhoto.src = photoSrc;
      reviewPhoto.style.display = 'block';
      reviewPhotoPlaceholder.style.display = 'none';
    } else {
      reviewPhoto.style.display = 'none';
      reviewPhoto.removeAttribute('src');
      reviewPhotoPlaceholder.style.display = 'block';
    }
  }

  // Signature preview
  const signatureData = document.getElementById('signature_data');
  const reviewSignature = document.getElementById('review_signature');
  const reviewSignaturePlaceholder = document.getElementById('review_signature_placeholder');
  
  // Check if signature exists (value will be base64 data)
  const signatureSrc = signatureData ? signatureData?.value : '';
  const hasSignature = signatureSrc && signatureSrc.startsWith('data:');
  
  if (reviewSignature && reviewSignaturePlaceholder) {
    if (hasSignature) {
      reviewSignature.src = signatureSrc;
      reviewSignature.style.display = 'block';
      reviewSignaturePlaceholder.style.display = 'none';
    } else {
      reviewSignature.style.display = 'none';
      reviewSignature.removeAttribute('src');
      reviewSignaturePlaceholder.style.display = 'block';
    }
  }
}

// ============================================
// Form Submission
// ============================================
function initFormSubmission() {
  elements.form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Validate all required fields
    const requiredInputs = elements.form.querySelectorAll('[required]');
    let isValid = true;

    requiredInputs.forEach(input => {
      if (!input.value.trim()) {
        isValid = false;
        input.style.borderColor = 'var(--color-danger)';
        input.addEventListener('input', function handler() {
          this.style.borderColor = '';
          this.removeEventListener('input', handler);
        }, { once: true });
      }
    });

    if (!isValid) {
      showMessage('Please fill in all required fields.', 'error');
      return;
    }

    // Validate signature
    if (!elements.signatureData.value) {
      showMessage('Please provide your signature before submitting.', 'error');
      elements.signatureCanvas.style.borderColor = 'var(--color-danger)';
      setTimeout(() => {
        elements.signatureCanvas.style.borderColor = '';
      }, 3000);
      return;
    }

    // Disable submit button and show loading
    elements.btnSubmit.disabled = true;
    elements.btnSubmit.classList.add('loading');
    elements.btnSubmit.textContent = 'Submitting...';

    try {
      const formData = new FormData(elements.form);
      
      // Include AI-generated headshot URL if available
      // Now returns URL from Seedream instead of base64
      const aiHeadshotImg = document.getElementById('aiPreviewImg');
      if (aiHeadshotImg && aiHeadshotImg.src && aiHeadshotImg.style.display !== 'none') {
        // Send the URL (or base64 if legacy) to the backend
        formData.append('ai_headshot_data', aiHeadshotImg.src);
      }

      const response = await fetch('/submit', {
        method: 'POST',
        body: formData
      });

      // Safely parse response - handle non-JSON responses
      const responseText = await response.text();
      let result;
      try {
        result = JSON.parse(responseText);
      } catch (parseError) {
        console.error('Non-JSON response from server:', responseText);
        throw new Error(`Server error: ${responseText.substring(0, 100)}`);
      }

      if (response.ok && (result.success !== false)) {
        showMessage('Registration submitted successfully! Your ID will be processed shortly.', 'success');

        // Disable all inputs
        elements.form.querySelectorAll('input, select, button').forEach(el => {
          el.disabled = true;
        });

        // Show success state
        elements.btnSubmit.textContent = '✓ Submitted';
        elements.btnSubmit.classList.remove('loading');
        elements.btnCancel.style.display = 'none';
      } else {
        throw new Error(result.detail || result.error || 'Submission failed');
      }
    } catch (error) {
      console.error('Submission error:', error);
      showMessage(`Error: ${error.message}. Please try again.`, 'error');

      // Re-enable submit button
      elements.btnSubmit.disabled = false;
      elements.btnSubmit.classList.remove('loading');
      elements.btnSubmit.textContent = 'Submit';
    }
  });
}

// ============================================
// Cancel Button
// ============================================
function initCancelButton() {
  elements.btnCancel.addEventListener('click', () => {
    if (confirm('Are you sure you want to cancel? All entered data will be lost.')) {
      location.reload();
    }
  });
}

// ============================================
// Messages
// ============================================
function showMessage(message, type = 'success') {
  elements.messageContainer.innerHTML = `
    <div class="message message-${type}">
      ${message}
    </div>
  `;

  // Auto-hide error messages after 5 seconds
  if (type !== 'success') {
    setTimeout(() => {
      elements.messageContainer.innerHTML = '';
    }, 5000);
  }

  // Scroll to message
  elements.messageContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
