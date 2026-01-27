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
  aiGenerationController: null,  // AbortController for AI generation
  aiGenerationComplete: false,   // Track if AI generation has successfully completed
  aiGenerationInProgress: false  // Track if AI generation is currently in progress
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
    aiActions: document.getElementById('aiActions'),
    regenerateBtn: document.getElementById('regenerateBtn'),
    signatureCanvas: document.getElementById('signaturePad'),
    signatureData: document.getElementById('signature_data'),
    clearSignature: document.getElementById('clearSignature')
  };

  initPhotoUpload();
  initSignaturePad();
  initFormSubmission();
  initCancelButton();
  initNameAutoPopulation(); // Auto-populate id_nickname from first_name
  initPositionRadioButtons(); // Handle position radio button changes
  initPrefilledFields(); // Handle prefilled fields from Lark
  initInputValidation(); // Initialize character restrictions on input fields
  updateReviewSection(); // Update on load
  updateIdCardPreview(); // Update ID card preview on load
  updateIdCardBackside(); // Update ID card backside on load
  updateSubmitButtonState(); // Initialize submit button state
  
  // Auto-update review and ID card preview when form changes
  document.querySelectorAll('input, select, textarea').forEach(el => {
    el.addEventListener('change', () => { updateReviewSection(); updateIdCardPreview(); updateIdCardBackside(); });
    el.addEventListener('input', () => { updateReviewSection(); updateIdCardPreview(); updateIdCardBackside(); });
    el.addEventListener('blur', () => { updateReviewSection(); updateIdCardPreview(); updateIdCardBackside(); });
  });
});

// ============================================
// Name Auto-Population (id_nickname from first_name)
// ============================================
function initNameAutoPopulation() {
  const firstNameInput = document.getElementById('first_name');
  const idNicknameInput = document.getElementById('id_nickname');
  
  if (firstNameInput && idNicknameInput) {
    firstNameInput.addEventListener('input', () => {
      // Auto-populate id_nickname with first name value
      idNicknameInput.value = firstNameInput.value;
      // Trigger change event to update previews
      idNicknameInput.dispatchEvent(new Event('change'));
    });
  }
}

// ============================================
// Handle Prefilled Fields from Lark
// ============================================
function initPrefilledFields() {
  const firstNameInput = document.getElementById('first_name');
  const idNicknameInput = document.getElementById('id_nickname');
  
  // If first_name is prefilled, auto-populate id_nickname
  if (firstNameInput && idNicknameInput && firstNameInput.value) {
    idNicknameInput.value = firstNameInput.value;
    // Trigger change event to update previews
    idNicknameInput.dispatchEvent(new Event('change'));
  }
  
  // Remove prefilled styling when user edits the field
  document.querySelectorAll('input.prefilled').forEach(input => {
    input.addEventListener('input', function() {
      this.classList.remove('prefilled');
    });
  });
}

// ============================================
// Input Field Character Restrictions
// ============================================
function initInputValidation() {
  // Contact Number fields - digits only (and + for country code)
  const phoneFields = ['personal_number', 'emergency_contact'];
  phoneFields.forEach(fieldId => {
    const field = document.getElementById(fieldId);
    if (field) {
      field.addEventListener('input', function(e) {
        // Allow digits, +, spaces, and hyphens for phone formatting
        this.value = this.value.replace(/[^0-9+\-\s]/g, '');
      });
      field.addEventListener('paste', function(e) {
        e.preventDefault();
        const pastedText = (e.clipboardData || window.clipboardData).getData('text');
        const cleanedText = pastedText.replace(/[^0-9+\-\s]/g, '');
        document.execCommand('insertText', false, cleanedText);
      });
    }
  });

  // Contact Name fields - alphanumeric + spaces only
  const nameFields = ['first_name', 'last_name', 'emergency_name'];
  nameFields.forEach(fieldId => {
    const field = document.getElementById(fieldId);
    if (field) {
      field.addEventListener('input', function(e) {
        // Allow letters, numbers, spaces, and common name characters (hyphen, apostrophe, period)
        this.value = this.value.replace(/[^a-zA-Z0-9\s\-'.]/g, '');
      });
      field.addEventListener('paste', function(e) {
        e.preventDefault();
        const pastedText = (e.clipboardData || window.clipboardData).getData('text');
        const cleanedText = pastedText.replace(/[^a-zA-Z0-9\s\-'.]/g, '');
        document.execCommand('insertText', false, cleanedText);
      });
    }
  });

  // Middle Initial - single letter only
  const middleInitialField = document.getElementById('middle_initial');
  if (middleInitialField) {
    middleInitialField.addEventListener('input', function(e) {
      // Allow only letters and period
      this.value = this.value.replace(/[^a-zA-Z.]/g, '').substring(0, 2);
    });
    middleInitialField.addEventListener('paste', function(e) {
      e.preventDefault();
      const pastedText = (e.clipboardData || window.clipboardData).getData('text');
      const cleanedText = pastedText.replace(/[^a-zA-Z.]/g, '').substring(0, 2);
      document.execCommand('insertText', false, cleanedText);
    });
  }

  // ID Number / Employee Number - alphanumeric and hyphens only
  const idNumberField = document.getElementById('id_number');
  if (idNumberField) {
    idNumberField.addEventListener('input', function(e) {
      // Allow letters, numbers, and hyphens (common in employee IDs like EMP-001)
      this.value = this.value.replace(/[^a-zA-Z0-9\-]/g, '');
    });
    idNumberField.addEventListener('paste', function(e) {
      e.preventDefault();
      const pastedText = (e.clipboardData || window.clipboardData).getData('text');
      const cleanedText = pastedText.replace(/[^a-zA-Z0-9\-]/g, '');
      document.execCommand('insertText', false, cleanedText);
    });
  }

  // Email - validate format on blur
  const emailField = document.getElementById('email');
  if (emailField) {
    emailField.addEventListener('blur', function(e) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (this.value && !emailRegex.test(this.value)) {
        this.style.borderColor = 'var(--color-danger)';
        showMessage('Please enter a valid email address.', 'error');
      } else {
        this.style.borderColor = '';
      }
    });
  }
}

// ============================================
// Submit Button State Management
// ============================================
function updateSubmitButtonState() {
  const submitBtn = elements.btnSubmit;
  if (!submitBtn) return;

  // Check if AI generation is required (photo has been uploaded)
  const photoInput = elements.photoInput;
  const hasPhoto = photoInput && photoInput.files && photoInput.files.length > 0;

  if (hasPhoto) {
    // If photo is uploaded, require AI generation to complete
    if (state.aiGenerationInProgress) {
      submitBtn.disabled = true;
      submitBtn.title = 'Please wait for AI photo generation to complete';
      submitBtn.classList.add('disabled-ai');
    } else if (!state.aiGenerationComplete) {
      submitBtn.disabled = true;
      submitBtn.title = 'AI photo generation required';
      submitBtn.classList.add('disabled-ai');
    } else {
      submitBtn.disabled = false;
      submitBtn.title = '';
      submitBtn.classList.remove('disabled-ai');
    }
  } else {
    // No photo uploaded yet - button can be enabled (form validation will catch missing photo)
    submitBtn.disabled = false;
    submitBtn.title = '';
    submitBtn.classList.remove('disabled-ai');
  }
}

// ============================================
// Position Radio Button Handling
// ============================================
function initPositionRadioButtons() {
  const positionRadios = document.querySelectorAll('input[name="position"]');
  
  positionRadios.forEach(radio => {
    radio.addEventListener('change', () => {
      updateIdCardPreview();
      updateReviewSection();
    });
  });
}

// Get selected position value
function getSelectedPosition() {
  const selectedRadio = document.querySelector('input[name="position"]:checked');
  return selectedRadio ? selectedRadio.value : '';
}

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
async function generateAIHeadshot(imageBase64, promptType = 'male_1') {
  console.log('=== generateAIHeadshot called ===');
  console.log('promptType received:', promptType);
  const loadingText = document.getElementById('aiLoadingText');
  
  // Reset AI generation state
  state.aiGenerationComplete = false;
  state.aiGenerationInProgress = true;
  updateSubmitButtonState();
  
  try {
    // Cancel any previous generation request
    if (state.aiGenerationController) {
      state.aiGenerationController.abort();
    }
    state.aiGenerationController = new AbortController();
    
    // Update loading text - server handles AI generation + background removal
    if (loadingText) loadingText.textContent = 'Generating AI headshot...';
    
    const requestBody = { image: imageBase64, prompt_type: promptType };
    console.log('=== Sending to /generate-headshot ===');
    console.log('Request body prompt_type:', requestBody.prompt_type);
    
    const response = await fetch('/generate-headshot', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      credentials: 'include',
      body: JSON.stringify(requestBody),
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
      
      // Always show Remove Background button when AI image is ready
      // Users can use it to remove/re-process background at any time
      if (elements.aiActions) {
        elements.aiActions.style.display = 'flex';
        console.log('AI Actions button shown - Remove Background available');
      }
      
      // Note: updateRemoveBgButtonState removed since background removal is disabled on Employee side
      
      // Store transparency state for ID card preview
      elements.aiPreviewImg.dataset.transparent = isTransparent ? 'true' : 'false';
      
      // Update ID card preview with the processed image
      updateIdCardPreview();
      
      if (result.message) {
        console.log('Server message:', result.message);
      }
      
      // Mark AI generation as complete and successful
      state.aiGenerationComplete = true;
      state.aiGenerationInProgress = false;
      updateSubmitButtonState();
      
    } else {
      throw new Error(result.error || 'Failed to generate headshot');
    }
    
  } catch (error) {
    if (error.name === 'AbortError') {
      console.log('AI generation aborted');
      state.aiGenerationInProgress = false;
      updateSubmitButtonState();
      return;
    }
    
    console.error('AI headshot generation error:', error);
    
    // Show error state
    elements.aiLoading.style.display = 'none';
    elements.aiPreviewImg.style.display = 'none';
    elements.aiError.style.display = 'block';
    elements.aiError.textContent = 'AI preview unavailable';
    
    // Mark AI generation as failed
    state.aiGenerationComplete = false;
    state.aiGenerationInProgress = false;
    updateSubmitButtonState();
    
    // Still show Remove Background button - user can try after uploading new photo
    if (elements.aiActions) {
      elements.aiActions.style.display = 'none';  // Hide when no image
    }
  }
}

// ============================================
// Background Removal
// ============================================

// REMOVED: Background removal functions (disabled on Employee side)
// The background removal feature is not available on the Employee portal

// Regenerate AI image with selected prompt style (called from dropdown)
async function regenerateAIImage(promptType = 'male_1') {
  console.log('=== regenerateAIImage called ===');
  console.log('promptType parameter:', promptType);
  console.log('typeof promptType:', typeof promptType);
  
  // Store the selected prompt type for the regenerate button
  state.lastSelectedPromptType = promptType;
  
  // Close the dropdown menu
  closeRegenerateDropdown();
  
  const photoInput = elements.photoInput;
  
  // Check if original photo exists
  if (!photoInput || !photoInput.files || !photoInput.files[0]) {
    showMessage('Please upload a photo first', 'error');
    return;
  }
  
  // Convert file to base64 before regeneration
  const file = photoInput.files[0];
  const reader = new FileReader();
  
  reader.onload = async (event) => {
    const imageData = event.target.result;
    
    // Reset AI preview state (show loading spinner)
    elements.aiPreviewImg.style.display = 'none';
    elements.aiError.style.display = 'none';
    elements.aiLoading.style.display = 'flex';
    
    // Re-trigger AI generation with the base64 data and selected prompt type
    await generateAIHeadshot(imageData, promptType);
  };
  
  reader.readAsDataURL(file);
}

// Simple regenerate button - uses last selected prompt type
async function simpleRegenerateAI() {
  console.log('=== simpleRegenerateAI called ===');
  console.log('Using last selected prompt type:', state.lastSelectedPromptType);
  
  const photoInput = elements.photoInput;
  
  // Check if original photo exists
  if (!photoInput || !photoInput.files || !photoInput.files[0]) {
    showMessage('Please upload a photo first', 'error');
    return;
  }
  
  // Convert file to base64 before regeneration
  const file = photoInput.files[0];
  const reader = new FileReader();
  
  reader.onload = async (event) => {
    const imageData = event.target.result;
    
    // Reset AI preview state (show loading spinner)
    elements.aiPreviewImg.style.display = 'none';
    elements.aiError.style.display = 'none';
    elements.aiLoading.style.display = 'flex';
    
    // Re-trigger AI generation with the last selected prompt type
    await generateAIHeadshot(imageData, state.lastSelectedPromptType);
  };
  
  reader.readAsDataURL(file);
}

// Toggle regenerate dropdown menu
function toggleRegenerateDropdown(event) {
  if (event) event.stopPropagation();
  
  const menu = document.getElementById('regenerateDropdownMenu');
  const dropdown = document.getElementById('regenerateDropdown');
  
  if (menu && dropdown) {
    const isOpen = menu.classList.contains('show');
    
    if (isOpen) {
      menu.classList.remove('show');
      dropdown.classList.remove('open');
    } else {
      menu.classList.add('show');
      dropdown.classList.add('open');
    }
  }
}

// Close regenerate dropdown menu
function closeRegenerateDropdown() {
  const menu = document.getElementById('regenerateDropdownMenu');
  const dropdown = document.getElementById('regenerateDropdown');
  
  if (menu) menu.classList.remove('show');
  if (dropdown) dropdown.classList.remove('open');
}

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
  const dropdown = document.getElementById('regenerateDropdown');
  if (dropdown && !dropdown.contains(event.target)) {
    closeRegenerateDropdown();
  }
});

// Make functions globally accessible for inline onclick
window.regenerateAIImage = regenerateAIImage;
window.simpleRegenerateAI = simpleRegenerateAI;
window.toggleRegenerateDropdown = toggleRegenerateDropdown;
window.closeRegenerateDropdown = closeRegenerateDropdown;

// REMOVED: Background removal functionality is fully disabled on Employee side
// The following functions are no longer used:
// - removeBackgroundFromAI()
// - removeBackground()
// - updateRemoveBgButtonState()

// Legacy placeholder for removeBackgroundFromAI (if still referenced)
async function removeBackgroundFromAI() {
  console.log('removeBackgroundFromAI: Feature disabled on Employee side');
  showMessage('Background removal is not available', 'error');
  return;
}

// Legacy function kept for compatibility but disabled
async function removeBackground(imageData, isUrl = true) {
  console.warn('removeBackground: Feature disabled on Employee side');
  return null;
}

// Old implementation removed below this line
// ============================================
// DISABLED: Background Removal (Employee Side)
// ============================================
/*
async function removeBackgroundFromAI_DISABLED() {
  console.log('removeBackgroundFromAI: Starting background removal...');
  
  const aiPreviewImg = elements.aiPreviewImg;
  const btnText = document.getElementById('regenerateBtnText');
  
  // This implementation was removed - legacy disabled code
}
*/

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

  // Update Full Name (constructed from first_name, middle_initial, last_name)
  const firstName = getValue('first_name');
  const middleInitial = getValue('middle_initial');
  const lastName = getValue('last_name');
  
  // Build full name: "FirstName M.I. LastName" or "FirstName LastName" if no MI
  let fullName = '';
  if (firstName) {
    fullName = firstName;
    if (middleInitial) {
      fullName += ' ' + middleInitial + (middleInitial.endsWith('.') ? '' : '.');
    }
    if (lastName) {
      fullName += ' ' + lastName;
    }
  } else if (lastName) {
    fullName = lastName;
  }
  
  const fullnameEl = document.getElementById('id_preview_fullname');
  if (fullnameEl) {
    fullnameEl.textContent = fullName || 'Employee Fullname';
  }

  // Update Position (with conditional display and transformation)
  const position = getSelectedPosition();
  const positionEl = document.getElementById('id_preview_position');
  const positionContainer = document.getElementById('id_position_container');
  
  if (positionEl && positionContainer) {
    // Position display rules:
    // - Field Officer -> Display "Legal Officer"
    // - Freelancer, Intern -> Display as-is
    // - Others -> Hide position entirely
    if (position === 'Others' || !position) {
      positionContainer.style.display = 'none';
    } else {
      positionContainer.style.display = 'block';
      if (position === 'Field Officer') {
        positionEl.textContent = 'Legal Officer';
      } else {
        positionEl.textContent = position;
      }
    }
  }

  // Update Expiration Date (conditional - only for Freelancer/Intern)
  const expirationContainer = document.getElementById('id_expiration_container');
  const expirationDateEl = document.getElementById('id_preview_expiration');
  
  if (expirationContainer) {
    // Expiration date rules:
    // - Show only for Freelancer or Intern
    // - Hide for Field Officer and Others
    if (position === 'Freelancer' || position === 'Intern') {
      expirationContainer.style.display = 'flex';
      // Calculate expiration date (1 year from now for preview)
      if (expirationDateEl) {
        const expirationDate = new Date();
        expirationDate.setFullYear(expirationDate.getFullYear() + 1);
        const formattedDate = expirationDate.toLocaleDateString('en-US', {
          month: 'long',
          day: 'numeric',
          year: 'numeric'
        });
        expirationDateEl.textContent = formattedDate;
      }
    } else {
      expirationContainer.style.display = 'none';
    }
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

  // Update dynamic website URLs with first name
  const firstNameLower = firstName ? firstName.toLowerCase() : '';
  const backDynamicUrl = `www.okpo.com/spm/${firstNameLower}`;
  
  // Front-side website URL (always static)
  const frontWebsiteEl = document.getElementById('id_front_website_url');
  if (frontWebsiteEl) {
    frontWebsiteEl.textContent = 'www.spmadrid.com';
  }
  
  // Back-side website URL (dynamic with first name)
  const backWebsiteEl = document.getElementById('id_back_website_url');
  if (backWebsiteEl) {
    backWebsiteEl.textContent = firstNameLower ? backDynamicUrl : 'www.okpo.com/spm/';
  }
  
  // Back-side contact label ("{First name}'s Contact")
  const backContactLabel = document.getElementById('id_back_contact_label');
  if (backContactLabel) {
    backContactLabel.textContent = firstName ? `${firstName}'s Contact` : "'s Contact";
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

  // Update text fields - Personal Details (new name fields)
  setText('review_first_name', getValue('first_name'));
  setText('review_middle_initial', getValue('middle_initial'));
  setText('review_last_name', getValue('last_name'));
  setText('review_id_nickname', getValue('id_nickname'));
  setText('review_id_number', getValue('id_number'));

  // Update text fields - Work Details (position from radio buttons)
  const position = getSelectedPosition();
  setText('review_position', position || '-');

  // Update text fields - Contact Information
  setText('review_email', getValue('email'));
  setText('review_personal_number', getValue('personal_number'));

  // Update text fields - Emergency Contact
  setText('review_emergency_name', getValue('emergency_name'));
  setText('review_emergency_contact', getValue('emergency_contact'));
  setText('review_emergency_address', getValue('emergency_address'));

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

    // Check if AI generation is in progress or failed (photo uploaded but not generated)
    const photoInput = elements.photoInput;
    const hasPhoto = photoInput && photoInput.files && photoInput.files.length > 0;
    
    if (hasPhoto && state.aiGenerationInProgress) {
      showMessage('Please wait for AI photo generation to complete before submitting.', 'error');
      return;
    }
    
    if (hasPhoto && !state.aiGenerationComplete) {
      showMessage('AI photo generation failed. Please upload a new photo and try again.', 'error');
      return;
    }

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

    // Validate email format
    const emailField = document.getElementById('email');
    if (emailField && emailField.value) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(emailField.value)) {
        showMessage('Please enter a valid email address.', 'error');
        emailField.style.borderColor = 'var(--color-danger)';
        return;
      }
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
        body: formData,
        credentials: 'same-origin'  // Include cookies for authentication
      });

      // Handle authentication error - redirect to login
      if (response.status === 401) {
        showMessage('Your session has expired. Redirecting to login...', 'error');
        setTimeout(() => {
          window.location.href = '/auth/login';
        }, 1500);
        return;
      }

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

        // Show success modal with options
        showSuccessModal();
        
        // Reset submit button state
        elements.btnSubmit.classList.remove('loading');
        elements.btnSubmit.textContent = 'Submit';
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
// Success Modal
// ============================================
function showSuccessModal() {
  const modal = document.getElementById('successModal');
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function hideSuccessModal() {
  const modal = document.getElementById('successModal');
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

function submitAnotherForm() {
  hideSuccessModal();
  // Reset the form completely
  elements.form.reset();
  
  // Clear signature canvas
  const canvas = elements.signatureCanvas;
  if (canvas) {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }
  if (elements.signatureData) elements.signatureData.value = '';
  
  // Reset photo previews
  const photoComparison = document.getElementById('photoComparison');
  const photoUploadArea = document.getElementById('photoUploadArea');
  const aiPreviewImg = document.getElementById('aiPreviewImg');
  const aiLoading = document.getElementById('aiLoading');
  const aiError = document.getElementById('aiError');
  
  if (photoComparison) photoComparison.style.display = 'none';
  if (photoUploadArea) photoUploadArea.style.display = 'flex';
  if (aiPreviewImg) {
    aiPreviewImg.style.display = 'none';
    aiPreviewImg.src = '';
  }
  if (aiLoading) aiLoading.style.display = 'none';
  if (aiError) aiError.style.display = 'none';
  
  // Reset review section
  const reviewSection = document.getElementById('reviewSection');
  if (reviewSection) {
    reviewSection.style.display = 'none';
  }
  
  // Clear messages
  elements.messageContainer.innerHTML = '';
  
  // Scroll to top
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Make submitAnotherForm available globally for onclick
window.submitAnotherForm = submitAnotherForm;

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
// ID Card Flip Toggle
// ============================================
function showCardSide(side) {
  const frontCard = document.getElementById('idCardFront');
  const backCard = document.getElementById('idCardBack');
  const flipBtns = document.querySelectorAll('.flip-btn');
  
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
    if (frontCard) frontCard.style.display = 'block';
    if (backCard) backCard.style.display = 'none';
  } else {
    if (frontCard) frontCard.style.display = 'none';
    if (backCard) backCard.style.display = 'block';
  }
}

// Make showCardSide available globally for onclick
window.showCardSide = showCardSide;

// ============================================
// ID Card Backside Preview Update
// ============================================
function updateIdCardBackside() {
  // Helper function to safely get element value
  const getValue = (id) => {
    const el = document.getElementById(id);
    if (!el) return '';
    return el.value || '';
  };
  
  // Update username (derived from first_name or id_nickname)
  const idBackUsername = document.getElementById('id_back_username');
  if (idBackUsername) {
    const nickname = getValue('id_nickname');
    const firstName = getValue('first_name');
    // Use nickname if available, otherwise use first name
    if (nickname) {
      idBackUsername.textContent = nickname.toLowerCase().replace(/\s+/g, '');
    } else if (firstName) {
      idBackUsername.textContent = firstName.toLowerCase().replace(/\s+/g, '');
    } else {
      idBackUsername.textContent = 'username';
    }
  }
  
  // Update Emergency Contact Name
  const emergencyNameEl = document.getElementById('id_back_emergency_name');
  if (emergencyNameEl) {
    const name = getValue('emergency_name');
    emergencyNameEl.textContent = name || 'Emergency Contact Name';
  }
  
  // Update Emergency Contact Number
  const emergencyContactEl = document.getElementById('id_back_emergency_contact');
  if (emergencyContactEl) {
    const contact = getValue('emergency_contact');
    emergencyContactEl.textContent = contact || '+63 XXX XXX XXXX';
  }
  
  // Update Emergency Address
  const emergencyAddressEl = document.getElementById('id_back_emergency_address');
  if (emergencyAddressEl) {
    const address = getValue('emergency_address');
    emergencyAddressEl.textContent = address || 'Contact Address';
  }
}

// ============================================
// Messages
// ============================================
// ============================================
// Back Button Navigation
// ============================================
function goBack() {
  // Check if there's history to go back to
  if (window.history.length > 1 && document.referrer) {
    window.history.back();
  } else {
    // No history - navigate to landing page
    window.location.href = '/';
  }
}

// Make goBack available globally for onclick
window.goBack = goBack;

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
