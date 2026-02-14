/**
 * Employee ID Registration System
 * One-Page Form with Signature Pad
 */

// ============================================
// Barcode Generation Helper
// ============================================

/**
 * Generate a barcode image URL for the given employee ID number.
 * Uses QuickChart.io Barcode API to generate Code 128 barcodes.
 * API Documentation: https://quickchart.io/documentation/barcode-api/
 * 
 * @param {string} idNumber - The employee ID number to encode
 * @param {Object} options - Optional configuration
 * @param {number} options.width - Width in pixels (default: 500)
 * @param {number} options.height - Height in pixels (default: 50)
 * @returns {string} URL to the barcode image, or empty string if no ID
 */
function getBarcodeUrl(idNumber, options = {}) {
  if (!idNumber || idNumber.trim() === '') return '';
  
  // Default dimensions - width=500 for high quality, height=50 for scan reliability
  const width = options.width || 500;
  const height = options.height || 150;
  
  // URL-encode the ID number to handle special characters
  const encodedId = encodeURIComponent(idNumber.trim());
  
  // QuickChart Barcode API URL
  // type=code128: Code 128 barcode (alphanumeric)
  // Note: Omitting includeText parameter = no human-readable text (BWIPP default behavior)
  // format=png: PNG output format
  const url = `https://quickchart.io/barcode?type=code128&text=${encodedId}&width=${width}&height=${height}&format=png`;
  
  return url;
}

/**
 * Update a barcode image element with the given ID number.
 * Shows the barcode image if ID is valid, otherwise shows fallback text.
 * 
 * @param {string} idNumber - The employee ID number to encode
 * @param {HTMLImageElement} imgEl - The barcode img element
 * @param {HTMLElement} fallbackEl - The fallback text element
 * @param {Object} options - Barcode generation options
 */
function updateBarcodeDisplay(idNumber, imgEl, fallbackEl, options = {}) {
  console.log('[Barcode] updateBarcodeDisplay called:', { idNumber, imgEl: !!imgEl, fallbackEl: !!fallbackEl });
  
  if (!imgEl || !fallbackEl) {
    console.warn('[Barcode] Missing elements:', { imgEl: !!imgEl, fallbackEl: !!fallbackEl });
    return;
  }
  
  const barcodeUrl = getBarcodeUrl(idNumber, options);
  console.log('[Barcode] Generated URL:', barcodeUrl);
  
  if (barcodeUrl) {
    imgEl.src = barcodeUrl;
    imgEl.alt = `Barcode for ${idNumber}`;
    imgEl.style.display = 'block';
    fallbackEl.style.display = 'none';
    
    // Handle successful load
    imgEl.onload = function() {
      console.log('[Barcode] Image loaded successfully');
      // BarcodeAPI returns error images with small dimensions or specific sizes
      // A valid barcode should have reasonable dimensions
      if (this.naturalWidth < 20 || this.naturalHeight < 5) {
        console.warn('[Barcode] Image too small, likely an error response');
        this.style.display = 'none';
        fallbackEl.style.display = 'none'; // Hide fallback too - show nothing on error
      }
    };
    
    // Handle load error - hide everything (no text, no fallback)
    imgEl.onerror = function() {
      console.error('[Barcode] Image failed to load');
      this.style.display = 'none';
      fallbackEl.style.display = 'none'; // Show nothing on error
    };
  } else {
    console.log('[Barcode] No URL generated, hiding barcode area');
    imgEl.style.display = 'none';
    imgEl.removeAttribute('src');
    fallbackEl.style.display = 'none'; // Show nothing when no ID
  }
}

// ============================================
// State Management
// ============================================
const state = {
  signaturePad: null,
  isDrawing: false,
  aiGenerationController: null,  // AbortController for AI generation
  aiGenerationComplete: false,   // Track if AI generation has successfully completed
  aiGenerationInProgress: false, // Track if AI generation is currently in progress
  isSubmitting: false            // Prevent double-submit
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
    clearSignature: document.getElementById('clearSignature'),
    suffixDropdown: document.getElementById('suffix'),
    suffixCustomGroup: document.getElementById('suffix_custom_group'),
    suffixCustomInput: document.getElementById('suffix_custom')
  };

  initPhotoUpload();
  initSignaturePad();
  initFormSubmission();
  initCancelButton();
  initNameAutoPopulation(); // Auto-populate id_nickname from first_name
  initPositionRadioButtons(); // Handle position radio button changes
  initPrefilledFields(); // Handle prefilled fields from Lark
  initInputValidation(); // Initialize character restrictions on input fields
  initSuffixField(); // Initialize suffix dropdown and custom input
  updateReviewSection(); // Update on load
  updateIdCardPreview(); // Update ID card preview on load
  updateIdCardBackside(); // Update ID card backside on load
  updateFieldOfficePreview(); // Update Field Office ID preview on load
  updateSubmitButtonState(); // Initialize submit button state
  
  // Auto-update review and ID card preview when form changes
  document.querySelectorAll('input, select, textarea').forEach(el => {
    el.addEventListener('change', () => { updateReviewSection(); updateIdCardPreview(); updateIdCardBackside(); updateFieldOfficePreview(); });
    el.addEventListener('input', () => { updateReviewSection(); updateIdCardPreview(); updateIdCardBackside(); updateFieldOfficePreview(); });
    el.addEventListener('blur', () => { updateReviewSection(); updateIdCardPreview(); updateIdCardBackside(); updateFieldOfficePreview(); });
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
      // Auto-populate id_nickname with only the first word of first name
      // e.g., "Sean Raphael" -> "Sean" for the ID card nickname
      const fullFirstName = firstNameInput.value.trim();
      const firstWord = fullFirstName.split(' ')[0] || '';
      idNicknameInput.value = firstWord;
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
  
  // If first_name is prefilled, auto-populate id_nickname with only first word
  if (firstNameInput && idNicknameInput && firstNameInput.value) {
    const fullFirstName = firstNameInput.value.trim();
    const firstWord = fullFirstName.split(' ')[0] || '';
    idNicknameInput.value = firstWord;
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
// QA-Grade Input Validation
// ============================================

// Validation error display helper
function showFieldError(fieldId, message) {
  const field = document.getElementById(fieldId);
  if (!field) return;
  
  field.classList.add('validation-error');
  field.style.borderColor = '#ef4444';
  
  // Remove any existing error message
  const existingError = field.parentElement.querySelector('.field-error-message');
  if (existingError) existingError.remove();
  
  // Add error message
  if (message) {
    const errorEl = document.createElement('span');
    errorEl.className = 'field-error-message';
    errorEl.style.cssText = 'color: #ef4444; font-size: 0.75rem; display: block; margin-top: 0.25rem;';
    errorEl.textContent = message;
    field.parentElement.appendChild(errorEl);
  }
}

function clearFieldError(fieldId) {
  const field = document.getElementById(fieldId);
  if (!field) return;
  
  field.classList.remove('validation-error');
  field.style.borderColor = '';
  
  // Remove error message
  const existingError = field.parentElement.querySelector('.field-error-message');
  if (existingError) existingError.remove();
}

// Phone number validation: 11 digits, starts with 09, no all-same digits
function validatePhoneNumber(value, fieldName) {
  if (!value) return { valid: false, message: `${fieldName} is required` };
  
  // Extract digits only
  const digits = value.replace(/\D/g, '');
  
  if (digits.length !== 11) {
    return { valid: false, message: `${fieldName} must be exactly 11 digits (got ${digits.length})` };
  }
  
  if (!digits.startsWith('09')) {
    return { valid: false, message: `${fieldName} must start with 09` };
  }
  
  // Check for all identical digits
  if (new Set(digits).size === 1) {
    return { valid: false, message: `${fieldName} cannot be all identical digits` };
  }
  
  // Check for common invalid patterns
  const invalidPatterns = ['09000000000', '09111111111', '09999999999', '09123456789', '09876543210'];
  if (invalidPatterns.includes(digits)) {
    return { valid: false, message: `${fieldName} appears to be an invalid test number` };
  }
  
  return { valid: true, message: '', cleaned: digits };
}

// Name validation: letters, spaces, hyphens, apostrophes only
function validateName(value, fieldName, minLength = 2, maxLength = 50) {
  if (!value || !value.trim()) {
    return { valid: false, message: `${fieldName} is required` };
  }
  
  const trimmed = value.trim().replace(/\s+/g, ' ');
  
  // Check for invalid characters
  if (!/^[A-Za-zÀ-ÿ\s\-'''.]+$/.test(trimmed)) {
    // Check if contains numbers
    if (/\d/.test(trimmed)) {
      return { valid: false, message: `${fieldName} cannot contain numbers` };
    }
    return { valid: false, message: `${fieldName} contains invalid characters` };
  }
  
  if (trimmed.length < minLength) {
    return { valid: false, message: `${fieldName} must be at least ${minLength} characters` };
  }
  
  if (trimmed.length > maxLength) {
    return { valid: false, message: `${fieldName} cannot exceed ${maxLength} characters` };
  }
  
  return { valid: true, message: '', cleaned: trimmed };
}

// Email validation
function validateEmail(value) {
  if (!value || !value.trim()) {
    return { valid: false, message: 'Email is required' };
  }
  
  const trimmed = value.trim().toLowerCase();
  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  
  if (!emailRegex.test(trimmed)) {
    return { valid: false, message: 'Please enter a valid email address' };
  }
  
  // Check for common typos
  const typos = {
    '@gmial.com': '@gmail.com',
    '@gmal.com': '@gmail.com',
    '@gmail.con': '@gmail.com',
    '@yahooo.com': '@yahoo.com'
  };
  
  for (const [typo, correct] of Object.entries(typos)) {
    if (trimmed.endsWith(typo)) {
      return { valid: false, message: `Did you mean ${trimmed.replace(typo, correct)}?` };
    }
  }
  
  return { valid: true, message: '', cleaned: trimmed };
}

function initInputValidation() {
  // ========================================
  // Phone Number Fields - Strict 11-digit, starts with 09
  // ========================================
  const phoneFields = [
    { id: 'personal_number', name: 'Personal Number', required: true },
    { id: 'emergency_contact', name: 'Emergency Contact', required: false }
  ];
  
  phoneFields.forEach(({ id, name, required }) => {
    const field = document.getElementById(id);
    if (!field) return;
    
    // Real-time: digits only input restriction
    field.addEventListener('input', function(e) {
      // Remove all non-digit characters while typing
      const digits = this.value.replace(/\D/g, '');
      this.value = digits;
      
      // Real-time length feedback
      if (digits.length > 0 && digits.length !== 11) {
        this.style.borderColor = '#f59e0b'; // Warning orange
      } else if (digits.length === 11) {
        const result = validatePhoneNumber(digits, name);
        if (result.valid) {
          clearFieldError(id);
          this.style.borderColor = '#10b981'; // Success green
        } else {
          showFieldError(id, result.message);
        }
      }
    });
    
    // On blur: full validation
    field.addEventListener('blur', function(e) {
      if (!this.value && !required) {
        clearFieldError(id);
        return;
      }
      
      const result = validatePhoneNumber(this.value, name);
      if (!result.valid) {
        showFieldError(id, result.message);
      } else {
        clearFieldError(id);
        this.style.borderColor = '';
      }
    });
    
    // Block paste of non-digits
    field.addEventListener('paste', function(e) {
      e.preventDefault();
      const pastedText = (e.clipboardData || window.clipboardData).getData('text');
      const digits = pastedText.replace(/\D/g, '');
      document.execCommand('insertText', false, digits);
    });
  });

  // ========================================
  // Name Fields - Letters, spaces, hyphens, apostrophes only
  // ========================================
  const nameFields = [
    { id: 'first_name', name: 'First Name', minLength: 2, maxLength: 50 },
    { id: 'last_name', name: 'Last Name', minLength: 2, maxLength: 50 },
    { id: 'emergency_name', name: 'Emergency Contact Name', minLength: 2, maxLength: 100 },
    { id: 'suffix_custom', name: 'Custom Suffix', minLength: 1, maxLength: 10 }
  ];
  
  nameFields.forEach(({ id, name, minLength, maxLength }) => {
    const field = document.getElementById(id);
    if (!field) return;
    
    field.addEventListener('input', function(e) {
      // Allow letters, spaces, hyphens, apostrophes, periods
      this.value = this.value.replace(/[^a-zA-ZÀ-ÿ\s\-'''.]/g, '');
      // Collapse multiple spaces
      this.value = this.value.replace(/\s+/g, ' ');
    });
    
    field.addEventListener('blur', function(e) {
      if (!this.value.trim()) {
        if (id !== 'emergency_name' && id !== 'suffix_custom') {
          showFieldError(id, `${name} is required`);
        }
        return;
      }
      
      const result = validateName(this.value, name, minLength, maxLength);
      if (!result.valid) {
        showFieldError(id, result.message);
      } else {
        clearFieldError(id);
      }
    });
    
    field.addEventListener('paste', function(e) {
      e.preventDefault();
      const pastedText = (e.clipboardData || window.clipboardData).getData('text');
      const cleaned = pastedText.replace(/[^a-zA-ZÀ-ÿ\s\-'''.]/g, '').replace(/\s+/g, ' ');
      document.execCommand('insertText', false, cleaned);
    });
  });

  // ========================================
  // Middle Initial - Single letter only
  // ========================================
  const middleInitialField = document.getElementById('middle_initial');
  if (middleInitialField) {
    middleInitialField.addEventListener('input', function(e) {
      // Allow only letters and one period
      let value = this.value.replace(/[^a-zA-Z.]/g, '');
      // Limit to 2 characters (letter + optional period)
      value = value.substring(0, 2);
      this.value = value.toUpperCase();
    });
    
    middleInitialField.addEventListener('blur', function(e) {
      let value = this.value.trim();
      // Remove trailing period (system adds it)
      value = value.replace(/\.$/, '');
      if (value.length > 1) {
        value = value[0];
      }
      this.value = value.toUpperCase();
      clearFieldError('middle_initial');
    });
    
    middleInitialField.addEventListener('paste', function(e) {
      e.preventDefault();
      const pastedText = (e.clipboardData || window.clipboardData).getData('text');
      const letter = pastedText.replace(/[^a-zA-Z]/g, '')[0] || '';
      document.execCommand('insertText', false, letter.toUpperCase());
    });
  }

  // ========================================
  // ID Number - Alphanumeric and hyphens, uppercase
  // ========================================
  const idNumberField = document.getElementById('id_number');
  if (idNumberField) {
    idNumberField.addEventListener('input', function(e) {
      // Allow letters, numbers, and hyphens only
      this.value = this.value.replace(/[^a-zA-Z0-9\-]/g, '').toUpperCase();
    });
    
    idNumberField.addEventListener('blur', function(e) {
      const value = this.value.trim();
      if (!value) {
        showFieldError('id_number', 'ID Number is required');
        return;
      }
      if (value.length < 3) {
        showFieldError('id_number', 'ID Number must be at least 3 characters');
        return;
      }
      clearFieldError('id_number');
    });
    
    idNumberField.addEventListener('paste', function(e) {
      e.preventDefault();
      const pastedText = (e.clipboardData || window.clipboardData).getData('text');
      const cleaned = pastedText.replace(/[^a-zA-Z0-9\-]/g, '').toUpperCase();
      document.execCommand('insertText', false, cleaned);
    });
  }

  // ========================================
  // Email - Validate format, auto-lowercase
  // ========================================
  const emailField = document.getElementById('email');
  if (emailField) {
    emailField.addEventListener('input', function(e) {
      // Remove spaces while typing
      this.value = this.value.replace(/\s/g, '');
    });
    
    emailField.addEventListener('blur', function(e) {
      const result = validateEmail(this.value);
      if (!result.valid) {
        showFieldError('email', result.message);
      } else {
        clearFieldError('email');
        // Auto-lowercase
        this.value = result.cleaned;
      }
    });
    
    emailField.addEventListener('paste', function(e) {
      e.preventDefault();
      const pastedText = (e.clipboardData || window.clipboardData).getData('text');
      const cleaned = pastedText.trim().replace(/\s/g, '').toLowerCase();
      document.execCommand('insertText', false, cleaned);
    });
  }
  
  // ========================================
  // Emergency Address - Min length, block placeholders
  // ========================================
  const emergencyAddress = document.getElementById('emergency_address');
  if (emergencyAddress) {
    emergencyAddress.addEventListener('blur', function(e) {
      const value = this.value.trim();
      if (!value) return; // Optional field
      
      const placeholders = ['na', 'n/a', '-', '.', 'none', 'nil', 'x', 'xx', 'xxx'];
      if (placeholders.includes(value.toLowerCase())) {
        showFieldError('emergency_address', 'Please enter a valid address or leave empty');
        return;
      }
      
      if (value.length < 10) {
        showFieldError('emergency_address', 'Address must be at least 10 characters');
        return;
      }
      
      clearFieldError('emergency_address');
    });
  }
}

// ============================================
// Comprehensive Form Validation Before Submit
// ============================================
function validateFormBeforeSubmit() {
  const errors = [];
  
  // --- Phone Number Validation ---
  const personalNumber = document.getElementById('personal_number');
  if (personalNumber) {
    const result = validatePhoneNumber(personalNumber.value, 'Personal Number');
    if (!result.valid) {
      errors.push(result.message);
      showFieldError('personal_number', result.message);
    }
  }
  
  const emergencyContact = document.getElementById('emergency_contact');
  if (emergencyContact && emergencyContact.value.trim()) {
    const result = validatePhoneNumber(emergencyContact.value, 'Emergency Contact');
    if (!result.valid) {
      errors.push(result.message);
      showFieldError('emergency_contact', result.message);
    }
  }
  
  // --- Name Validation ---
  const firstName = document.getElementById('first_name');
  if (firstName) {
    const result = validateName(firstName.value, 'First Name', 2, 50);
    if (!result.valid) {
      errors.push(result.message);
      showFieldError('first_name', result.message);
    }
  }
  
  const lastName = document.getElementById('last_name');
  if (lastName) {
    const result = validateName(lastName.value, 'Last Name', 2, 50);
    if (!result.valid) {
      errors.push(result.message);
      showFieldError('last_name', result.message);
    }
  }
  
  // --- ID Number Validation ---
  const idNumber = document.getElementById('id_number');
  if (idNumber) {
    const value = idNumber.value.trim();
    if (!value) {
      errors.push('ID Number is required');
      showFieldError('id_number', 'ID Number is required');
    } else if (!/^[A-Za-z0-9\-]+$/.test(value)) {
      errors.push('ID Number can only contain letters, numbers, and hyphens');
      showFieldError('id_number', 'ID Number can only contain letters, numbers, and hyphens');
    } else if (value.length < 3) {
      errors.push('ID Number must be at least 3 characters');
      showFieldError('id_number', 'ID Number must be at least 3 characters');
    }
  }
  
  // --- Email Validation ---
  const emailField = document.getElementById('email');
  if (emailField) {
    const result = validateEmail(emailField.value);
    if (!result.valid) {
      errors.push(result.message);
      showFieldError('email', result.message);
    }
  }
  
  // --- Required Dropdown Validation ---
  const position = document.getElementById('position');
  if (position && (!position.value || position.value === '')) {
    errors.push('Please select a Position');
    position.style.borderColor = '#ef4444';
  }
  
  const department = document.getElementById('department');
  if (department && (!department.value || department.value === '')) {
    errors.push('Please select a Department');
    department.style.borderColor = '#ef4444';
  }
  
  const branchField = document.getElementById('branch') || document.getElementById('branch_search');
  if (branchField) {
    const branchValue = document.getElementById('branch')?.value || '';
    if (!branchValue) {
      errors.push('Please select a Branch');
      branchField.style.borderColor = '#ef4444';
    }
  }
  
  // --- Date Validation ---
  const hireDateField = document.getElementById('hire_date');
  if (hireDateField && hireDateField.value) {
    const hireDate = new Date(hireDateField.value);
    const today = new Date();
    const oneYearAgo = new Date(today);
    oneYearAgo.setFullYear(today.getFullYear() - 1);
    
    if (hireDate > today) {
      errors.push('Hire date cannot be in the future');
      showFieldError('hire_date', 'Hire date cannot be in the future');
    }
    if (hireDate < oneYearAgo) {
      errors.push('Hire date cannot be more than 1 year in the past');
      showFieldError('hire_date', 'Hire date cannot be more than 1 year in the past');
    }
  }
  
  const birthdateField = document.getElementById('birthdate');
  if (birthdateField && birthdateField.value) {
    const birthdate = new Date(birthdateField.value);
    const today = new Date();
    
    // Calculate age
    let age = today.getFullYear() - birthdate.getFullYear();
    const monthDiff = today.getMonth() - birthdate.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthdate.getDate())) {
      age--;
    }
    
    if (age < 18) {
      errors.push('Employee must be at least 18 years old');
      showFieldError('birthdate', 'Employee must be at least 18 years old');
    }
    if (age > 100) {
      errors.push('Please verify birthdate - age exceeds 100 years');
      showFieldError('birthdate', 'Please verify birthdate');
    }
  }
  
  // --- Address Length Validation ---
  const emergencyAddress = document.getElementById('emergency_address');
  if (emergencyAddress && emergencyAddress.value.trim()) {
    const value = emergencyAddress.value.trim();
    const placeholders = ['na', 'n/a', '-', '.', 'none', 'nil', 'x', 'xx', 'xxx'];
    if (placeholders.includes(value.toLowerCase())) {
      errors.push('Please enter a valid emergency address or leave empty');
      showFieldError('emergency_address', 'Please enter a valid address or leave empty');
    } else if (value.length < 10) {
      errors.push('Emergency address must be at least 10 characters');
      showFieldError('emergency_address', 'Address must be at least 10 characters');
    }
  }
  
  return errors;
}

// ============================================
// Suffix Field Management
// ============================================
function initSuffixField() {
  const suffixDropdown = elements.suffixDropdown;
  const suffixCustomGroup = elements.suffixCustomGroup;
  const suffixCustomInput = elements.suffixCustomInput;
  
  console.log('Initializing suffix field:', {
    dropdown: suffixDropdown,
    customGroup: suffixCustomGroup,
    customInput: suffixCustomInput
  });
  
  if (suffixDropdown && suffixCustomGroup && suffixCustomInput) {
    // Handle dropdown changes
    suffixDropdown.addEventListener('change', () => {
      console.log('Suffix dropdown changed to:', suffixDropdown.value);
      if (suffixDropdown.value === 'Other') {
        suffixCustomGroup.style.display = 'block';
        console.log('Showing custom suffix input');
      } else {
        suffixCustomGroup.style.display = 'none';
        suffixCustomInput.value = ''; // Clear custom input when not "Other"
        console.log('Hiding custom suffix input');
      }
      // Trigger update events
      updateReviewSection();
      updateIdCardPreview();
      updateIdCardBackside();
    });
    
    // Check initial state on page load
    if (suffixDropdown.value === 'Other') {
      suffixCustomGroup.style.display = 'block';
      console.log('Initial state: Other selected, showing custom input');
    }
  } else {
    console.error('Suffix field elements not found:', {
      dropdown: !!suffixDropdown,
      customGroup: !!suffixCustomGroup,
      customInput: !!suffixCustomInput
    });
  }
}

// Helper function to get the actual suffix value
function getSuffixValue() {
  const suffixDropdown = elements.suffixDropdown;
  const suffixCustomInput = elements.suffixCustomInput;
  
  if (!suffixDropdown) return '';
  
  const dropdownValue = suffixDropdown.value;
  
  if (dropdownValue === 'Other' && suffixCustomInput) {
    return suffixCustomInput.value.trim();
  } else if (dropdownValue && dropdownValue !== '') {
    return dropdownValue;
  }
  
  return '';
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
  const fieldOfficerSubtypeGroup = document.getElementById('field_officer_subtype_group');
  const fieldOfficerDetails = document.getElementById('field_officer_details');
  const foTypeRadios = document.querySelectorAll('input[name="field_officer_type"]');
  
  // Handle Field Officer Type selection (Reprocessor/Shared/Others)
  // Note: "Shared" behaves exactly the same as "Reprocessor" (dual template mode)
  foTypeRadios.forEach(radio => {
    radio.addEventListener('change', () => {
      const selectedType = radio.value;
      
      // Show details section for Reprocessor or Shared (both use dual template mode)
      if (selectedType === 'Reprocessor' || selectedType === 'Shared') {
        if (fieldOfficerDetails) fieldOfficerDetails.style.display = 'block';
        setFieldOfficerFieldsRequired(true);
        // Show dual template preview for Reprocessor/Shared
        showDualTemplateMode(true);
      } else {
        // Hide for Others or any other value
        if (fieldOfficerDetails) fieldOfficerDetails.style.display = 'none';
        setFieldOfficerFieldsRequired(false);
        // Show single template preview for Others (Field Office template only)
        showDualTemplateMode(false);
      }
      
      updateIdCardPreview();
      updateReviewSection();
      updateFieldOfficePreview();
      updateDualTemplatePreview();
    });
  });
  
  positionRadios.forEach(radio => {
    radio.addEventListener('change', () => {
      const selectedPosition = radio.value;
      
      // Show/hide Field Officer specific fields
      if (selectedPosition === 'Field Officer') {
        if (fieldOfficerSubtypeGroup) fieldOfficerSubtypeGroup.style.display = 'block';
        // Don't show details yet - wait for Reprocessor selection
        if (fieldOfficerDetails) fieldOfficerDetails.style.display = 'none';
        setFieldOfficerFieldsRequired(false);
        // Reset to single template mode until subtype is selected
        showDualTemplateMode(false);
      } else {
        if (fieldOfficerSubtypeGroup) fieldOfficerSubtypeGroup.style.display = 'none';
        if (fieldOfficerDetails) fieldOfficerDetails.style.display = 'none';
        
        // Remove required from Field Officer fields
        setFieldOfficerFieldsRequired(false);
        
        // Clear Field Officer type selection
        foTypeRadios.forEach(r => r.checked = false);
        
        // Always show single template mode for non-Field Officers
        showDualTemplateMode(false);
      }
      
      updateIdCardPreview();
      updateReviewSection();
      updateFieldOfficePreview(); // Switch templates based on position
    });
  });
  
  // Initialize searchable dropdowns
  initSearchableDropdowns();
  
  // Initialize multi-select dropdowns (Campaign field)
  initMultiSelectDropdown();
}

// ============================================
// Dual Template Mode Handling
// ============================================
function showDualTemplateMode(isDualMode) {
  const singleContainer = document.getElementById('singleTemplateContainer');
  const dualContainer = document.getElementById('dualTemplateContainer');
  
  if (isDualMode) {
    // Show dual template container for Reprocessor
    if (singleContainer) singleContainer.style.display = 'none';
    if (dualContainer) dualContainer.style.display = 'block';
    // Update dual template previews
    updateDualTemplatePreview();
  } else {
    // Show single template container for Others/non-Field Officer
    if (singleContainer) singleContainer.style.display = 'block';
    if (dualContainer) dualContainer.style.display = 'none';
  }
}

// Show/hide sides in dual template mode
function showDualCardSide(template, side) {
  const templatePrefix = template === 'original' ? 'dualOriginal' : 'dualReprocessor';
  const frontCard = document.getElementById(`${templatePrefix}Front`);
  const backCard = document.getElementById(`${templatePrefix}Back`);
  
  // Update button states for this template only
  const templateCard = (template === 'original') 
    ? document.querySelector('.dual-template-card:first-child')
    : document.querySelector('.dual-template-card:last-child');
  
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

// Make showDualCardSide available globally
window.showDualCardSide = showDualCardSide;

// Update dual template previews with form data
// Image source rules:
// - Original Template (Portrait): Uses AI-generated photo
// - Reprocessor Template (Landscape): Uses original uploaded photo
function updateDualTemplatePreview() {
  const dualContainer = document.getElementById('dualTemplateContainer');
  if (!dualContainer || dualContainer.style.display === 'none') return;
  
  // Helper function to safely get element value
  const getValue = (id) => {
    const el = document.getElementById(id);
    if (!el) return '';
    return el.value.trim();
  };
  
  // Get suffix value
  const getSuffixValue = () => {
    const suffixSelect = document.getElementById('suffix');
    if (!suffixSelect) return '';
    const val = suffixSelect.value;
    return (val && val !== 'None' && val !== '') ? val : '';
  };
  
  // Get form values
  const firstName = getValue('first_name');
  const lastName = getValue('last_name');
  const middleInitial = getValue('middle_initial');
  const suffix = getSuffixValue();
  const nickname = getValue('id_nickname') || firstName;
  const idNumber = getValue('id_number');
  const emergencyName = getValue('emergency_name');
  const emergencyContact = getValue('emergency_contact');
  const emergencyAddress = getValue('emergency_address');
  
  // Build full name
  let fullName = '';
  if (firstName) fullName += firstName;
  if (middleInitial) fullName += ' ' + middleInitial + '.';
  if (lastName) fullName += ' ' + lastName;
  if (suffix) fullName += ' ' + suffix;
  fullName = fullName.trim() || 'Bonifacio M. Aguinaldo';
  
  // Get photo sources - separate AI and original
  const aiPreviewImg = document.getElementById('aiPreviewImg');
  const photoPreviewImg = document.getElementById('photoPreviewImg');
  const signatureData = document.getElementById('signature_data');
  
  // AI photo source (for Original Template - Portrait)
  let aiPhotoSrc = '';
  if (aiPreviewImg && aiPreviewImg.style.display !== 'none' && aiPreviewImg.src && 
      (aiPreviewImg.src.startsWith('data:') || aiPreviewImg.src.startsWith('http') || aiPreviewImg.src.startsWith('blob:'))) {
    aiPhotoSrc = aiPreviewImg.src;
  }
  
  // Original uploaded photo source (for Reprocessor Template - Landscape)
  let originalPhotoSrc = '';
  if (photoPreviewImg && photoPreviewImg.src && 
      (photoPreviewImg.src.startsWith('data:') || photoPreviewImg.src.startsWith('blob:'))) {
    originalPhotoSrc = photoPreviewImg.src;
  }
  
  const signatureSrc = signatureData ? signatureData.value : '';
  const hasSignature = signatureSrc && signatureSrc.startsWith('data:');
  
  // === Update Original Template (uses AI photo) ===
  // Nickname
  const origNickname = document.getElementById('dual_original_nickname');
  if (origNickname) origNickname.textContent = nickname || 'Ian';
  
  // Full name
  const origFullname = document.getElementById('dual_original_fullname');
  if (origFullname) origFullname.textContent = fullName;
  
  // Position - Show "Legal Officer" for SPMC card (same as single template behavior)
  const origPosition = document.getElementById('dual_original_position');
  if (origPosition) origPosition.textContent = 'Legal Officer';
  
  // ID Number
  const origIdNumber = document.getElementById('dual_original_idnumber');
  if (origIdNumber) origIdNumber.textContent = idNumber || '012402-081';
  
  // Barcode - Original Template
  const origBarcodeImg = document.getElementById('dual_original_barcode');
  const origBarcodeFallback = document.getElementById('dual_original_barcode_fallback');
  updateBarcodeDisplay(idNumber, origBarcodeImg, origBarcodeFallback, { width: 500, height: 50 });
  
  // Photo - Original Template uses AI photo
  const origPhoto = document.getElementById('dual_original_photo');
  const origPhotoPlaceholder = document.getElementById('dual_original_photo_placeholder');
  if (origPhoto && origPhotoPlaceholder) {
    if (aiPhotoSrc) {
      origPhoto.src = aiPhotoSrc;
      origPhoto.style.display = 'block';
      origPhotoPlaceholder.style.display = 'none';
    } else {
      origPhoto.style.display = 'none';
      origPhotoPlaceholder.style.display = 'block';
      origPhotoPlaceholder.textContent = 'AI Image';
    }
  }
  
  // Signature
  const origSignature = document.getElementById('dual_original_signature');
  const origSignaturePlaceholder = document.getElementById('dual_original_signature_placeholder');
  if (origSignature && origSignaturePlaceholder) {
    if (hasSignature) {
      origSignature.src = signatureSrc;
      origSignature.style.display = 'block';
      origSignaturePlaceholder.style.display = 'none';
    } else {
      origSignature.style.display = 'none';
      origSignaturePlaceholder.style.display = 'block';
    }
  }
  
  // Emergency contact for back side
  const origContactLabel = document.getElementById('dual_original_contact_label');
  if (origContactLabel) origContactLabel.textContent = `${firstName || 'Employee'}'s Contact`;
  
  const origEmergencyName = document.getElementById('dual_original_emergency_name');
  if (origEmergencyName) origEmergencyName.textContent = emergencyName || 'Emergency Contact Name';
  
  const origEmergencyContact = document.getElementById('dual_original_emergency_contact');
  if (origEmergencyContact) origEmergencyContact.textContent = emergencyContact || '09XXXXXXXXX';
  
  const origEmergencyAddress = document.getElementById('dual_original_emergency_address');
  if (origEmergencyAddress) origEmergencyAddress.textContent = emergencyAddress || 'Contact Address';
  
  // Update SPMC back website URL with correct format: www.okpo.com/spm/firstnamelastinitialmiddleinitial
  const origBackWebsiteUrl = document.getElementById('dual_original_back_website_url');
  if (origBackWebsiteUrl) {
    const firstNameLower = firstName ? firstName.toLowerCase().replace(/\s+/g, '') : '';
    const lastNameInitialLower = lastName ? lastName.charAt(0).toLowerCase() : '';
    const middleInitialLower = middleInitial ? middleInitial.charAt(0).toLowerCase() : '';
    const backDynamicUrl = `www.okpo.com/spm/${firstNameLower}${lastNameInitialLower}${middleInitialLower}`;
    origBackWebsiteUrl.textContent = firstNameLower ? backDynamicUrl : 'www.okpo.com/spm/';
  }
  
  // Generate vCard QR code for SPMC backside using QuickChart API
  const vcardQrImg = document.getElementById('dual_original_vcard_qr');
  const vcardQrPlaceholder = document.getElementById('dual_original_vcard_qr_placeholder');
  if (vcardQrImg && vcardQrPlaceholder) {
    // Get additional employee data for vCard
    const email = getValue('email');
    const phone = getValue('personal_number');
    
    // Build vCard 3.0 string
    // N: Last;First;Middle;;
    // FN: First M. Last
    let vcardFn = firstName || '';
    if (middleInitial) {
      vcardFn += ' ' + middleInitial.charAt(0).toUpperCase() + '.';
    }
    if (lastName) vcardFn += ' ' + lastName;
    if (suffix) vcardFn += ' ' + suffix;
    vcardFn = vcardFn.trim();
    
    const vcardN = `${lastName || ''};${firstName || ''};${middleInitial ? middleInitial.charAt(0) : ''};;${suffix || ''}`;
    
    // Build complete vCard
    let vcard = 'BEGIN:VCARD\n';
    vcard += 'VERSION:3.0\n';
    vcard += `N:${vcardN}\n`;
    vcard += `FN:${vcardFn || 'Employee'}\n`;
    vcard += 'ORG:S.P. Madrid & Associates\n';
    vcard += 'TITLE:Field Officer\n';
    if (phone) vcard += `TEL:${phone}\n`;
    if (email) vcard += `EMAIL:${email}\n`;
    vcard += 'END:VCARD';
    
    // Generate QuickChart QR URL
    const encodedVcard = encodeURIComponent(vcard);
    const qrUrl = `https://quickchart.io/qr?text=${encodedVcard}&size=200&ecLevel=Q&format=png&margin=1`;
    
    // Update QR image
    if (firstName || lastName) {
      vcardQrImg.src = qrUrl;
      vcardQrImg.style.display = 'block';
      vcardQrPlaceholder.style.display = 'none';
    } else {
      vcardQrImg.style.display = 'none';
      vcardQrPlaceholder.style.display = 'block';
    }
  }
  
  // Generate URL QR code for bottom of SPMC backside with embedded OKPO logo
  const urlQrImg = document.getElementById('dual_original_url_qr');
  const urlQrPlaceholder = document.getElementById('dual_original_url_qr_placeholder');
  if (urlQrImg && urlQrPlaceholder) {
    // Build URL using same format as the displayed URL text
    const firstNameLower = firstName ? firstName.toLowerCase().replace(/\s+/g, '') : '';
    const lastNameInitialLower = lastName ? lastName.charAt(0).toLowerCase() : '';
    const middleInitialLower = middleInitial ? middleInitial.charAt(0).toLowerCase() : '';
    const employeeUrl = `https://www.okpo.com/spm/${firstNameLower}${lastNameInitialLower}${middleInitialLower}`;
    
    if (firstNameLower) {
      // OKPO logo URL (must be URL-encoded)
      const logoUrl = 'https://239dc453931a663c0cfa3bb867f1aaae.cdn.bubble.io/cdn-cgi/image/w=,h=,f=auto,dpr=1,fit=contain/f1727917655428x617042099316169600/okpologo.jpg';
      const encodedLogoUrl = encodeURIComponent(logoUrl);
      const encodedEmployeeUrl = encodeURIComponent(employeeUrl);
      
      // Generate QuickChart QR URL with embedded logo using centerImageUrl parameter
      const urlQrCode = `https://quickchart.io/qr?text=${encodedEmployeeUrl}&size=200&ecLevel=H&format=png&margin=1&centerImageUrl=${encodedLogoUrl}&centerImageSizeRatio=0.25`;
      urlQrImg.src = urlQrCode;
      urlQrImg.style.display = 'block';
      urlQrPlaceholder.style.display = 'none';
    } else {
      urlQrImg.style.display = 'none';
      urlQrPlaceholder.style.display = 'block';
    }
  }
  
  // === Update Reprocessor Template (uses ORIGINAL uploaded photo, NOT AI) ===
  // Name (with line break) - Include middle initial with dot
  const reprocessorName = document.getElementById('dual_reprocessor_name');
  if (reprocessorName) {
    let displayName = '';
    if (firstName && lastName) {
      // Format: FirstName M.<br>LastName Suffix
      displayName = firstName;
      if (middleInitial) {
        // Use first character of middle initial field, uppercase, with dot
        displayName += ' ' + middleInitial.charAt(0).toUpperCase() + '.';
      }
      displayName += '<br>' + lastName;
      if (suffix) displayName += ' ' + suffix;
    } else {
      displayName = 'Name<br>Placeholder';
    }
    reprocessorName.innerHTML = displayName;
  }
  
  // Position - ALWAYS show "LEGAL OFFICER" regardless of field_officer_type
  // The placeholder label should never change to "REPROCESSOR"
  const reprocessorPosition = document.getElementById('dual_reprocessor_position');
  if (reprocessorPosition) reprocessorPosition.textContent = 'LEGAL OFFICER';
  
  // Clearance
  const reprocessorClearance = document.getElementById('dual_reprocessor_clearance');
  if (reprocessorClearance) reprocessorClearance.textContent = 'Level 5';
  
  // ID Number
  const reprocessorIdNumber = document.getElementById('dual_reprocessor_idnumber');
  if (reprocessorIdNumber) reprocessorIdNumber.textContent = idNumber || 'ID Number Placeholder';
  
  // Barcode - Reprocessor Template (SPMA card in dual mode)
  // Container is 180x40, so with width=500 we need height≈111 to maintain aspect ratio and fill the container
  const reprocessorBarcodeImg = document.getElementById('dual_reprocessor_barcode');
  const reprocessorBarcodeFallback = document.getElementById('dual_reprocessor_barcode_fallback');
  updateBarcodeDisplay(idNumber, reprocessorBarcodeImg, reprocessorBarcodeFallback, { width: 500, height: 111 });
  
  // Photo - Reprocessor Template uses ORIGINAL uploaded photo (NOT AI)
  const reprocessorPhoto = document.getElementById('dual_reprocessor_photo');
  const reprocessorPhotoPlaceholder = document.getElementById('dual_reprocessor_photo_placeholder');
  if (reprocessorPhoto && reprocessorPhotoPlaceholder) {
    if (originalPhotoSrc) {
      reprocessorPhoto.src = originalPhotoSrc;
      reprocessorPhoto.style.display = 'block';
      reprocessorPhotoPlaceholder.style.display = 'none';
    } else {
      reprocessorPhoto.style.display = 'none';
      reprocessorPhotoPlaceholder.style.display = 'block';
      reprocessorPhotoPlaceholder.textContent = 'Original Photo';
    }
  }
  
  // Signature
  const reprocessorSignature = document.getElementById('dual_reprocessor_signature');
  const reprocessorSignaturePlaceholder = document.getElementById('dual_reprocessor_signature_placeholder');
  if (reprocessorSignature && reprocessorSignaturePlaceholder) {
    if (hasSignature) {
      reprocessorSignature.src = signatureSrc;
      reprocessorSignature.style.display = 'block';
      reprocessorSignaturePlaceholder.style.display = 'none';
    } else {
      reprocessorSignature.style.display = 'none';
      reprocessorSignaturePlaceholder.style.display = 'block';
    }
  }
}

// Make updateDualTemplatePreview available globally
window.updateDualTemplatePreview = updateDualTemplatePreview;

// Set Field Officer fields as required or not
function setFieldOfficerFieldsRequired(required) {
  // Division is hidden from UI — no longer required from user
  const foDepartment = document.getElementById('fo_department');
  const foCampaign = document.getElementById('fo_campaign');
  const foTypeRadios = document.querySelectorAll('input[name="field_officer_type"]');
  
  if (foDepartment) foDepartment.required = required;
  if (foCampaign) foCampaign.required = required;
  
  // Set first radio as required to ensure one is selected
  if (foTypeRadios.length > 0) {
    foTypeRadios[0].required = required;
  }
}

// ============================================
// Searchable Dropdown Functionality
// ============================================
function initSearchableDropdowns() {
  const dropdowns = document.querySelectorAll('.searchable-dropdown');
  
  dropdowns.forEach(dropdown => {
    const searchInput = dropdown.querySelector('.dropdown-search');
    const hiddenInput = dropdown.querySelector('input[type="hidden"]');
    const optionsContainer = dropdown.querySelector('.dropdown-options');
    const options = dropdown.querySelectorAll('.dropdown-option');
    
    if (!searchInput || !optionsContainer || !options.length) return;
    
    // Show dropdown on focus
    searchInput.addEventListener('focus', () => {
      dropdown.classList.add('active');
    });
    
    // Filter options on input
    searchInput.addEventListener('input', () => {
      const searchTerm = searchInput.value.toLowerCase();
      let hasVisibleOptions = false;
      
      options.forEach(option => {
        const text = option.textContent.toLowerCase();
        if (text.includes(searchTerm)) {
          option.classList.remove('hidden');
          hasVisibleOptions = true;
        } else {
          option.classList.add('hidden');
        }
      });
      
      // Show "no results" message if needed
      let noResults = dropdown.querySelector('.no-results');
      if (!hasVisibleOptions) {
        if (!noResults) {
          noResults = document.createElement('div');
          noResults.className = 'no-results';
          noResults.textContent = 'No matching options';
          optionsContainer.appendChild(noResults);
        }
        noResults.style.display = 'block';
      } else if (noResults) {
        noResults.style.display = 'none';
      }
      
      dropdown.classList.add('active');
    });
    
    // Handle option selection
    options.forEach(option => {
      option.addEventListener('click', () => {
        const value = option.dataset.value;
        searchInput.value = value;
        searchInput.classList.add('has-value');
        if (hiddenInput) hiddenInput.value = value;
        
        // Remove selected class from all options
        options.forEach(o => o.classList.remove('selected'));
        option.classList.add('selected');
        
        dropdown.classList.remove('active');
        
        // Trigger change events for review section update
        updateReviewSection();
        updateIdCardPreview();
      });
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
      if (!dropdown.contains(e.target)) {
        dropdown.classList.remove('active');
      }
    });
    
    // Handle keyboard navigation
    searchInput.addEventListener('keydown', (e) => {
      const visibleOptions = Array.from(options).filter(o => !o.classList.contains('hidden'));
      const currentIndex = visibleOptions.findIndex(o => o.classList.contains('selected'));
      
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        dropdown.classList.add('active');
        const nextIndex = currentIndex < visibleOptions.length - 1 ? currentIndex + 1 : 0;
        visibleOptions.forEach((o, i) => o.classList.toggle('selected', i === nextIndex));
        visibleOptions[nextIndex]?.scrollIntoView({ block: 'nearest' });
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        const prevIndex = currentIndex > 0 ? currentIndex - 1 : visibleOptions.length - 1;
        visibleOptions.forEach((o, i) => o.classList.toggle('selected', i === prevIndex));
        visibleOptions[prevIndex]?.scrollIntoView({ block: 'nearest' });
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const selectedOption = visibleOptions.find(o => o.classList.contains('selected'));
        if (selectedOption) {
          selectedOption.click();
        }
      } else if (e.key === 'Escape') {
        dropdown.classList.remove('active');
      }
    });
  });
}

// ============================================
// Multi-Select Dropdown Functionality (Campaign field)
// ============================================
function initMultiSelectDropdown() {
  const dropdown = document.getElementById('fo_campaign_dropdown');
  if (!dropdown || !dropdown.classList.contains('multi-select-dropdown')) return;
  
  const searchInput = dropdown.querySelector('.dropdown-search');
  const hiddenInput = dropdown.querySelector('input[type="hidden"]');
  const optionsContainer = dropdown.querySelector('.dropdown-options');
  const options = dropdown.querySelectorAll('.dropdown-option');
  const tagsContainer = dropdown.querySelector('.selected-tags');
  const multiSelectContainer = dropdown.querySelector('.multi-select-container');
  
  if (!searchInput || !optionsContainer || !options.length || !tagsContainer) return;
  
  let selectedValues = [];
  
  // Function to update hidden input and tags display
  function updateSelection() {
    // Store as comma-separated values
    hiddenInput.value = selectedValues.join(',');
    
    // Update tags display
    tagsContainer.innerHTML = '';
    selectedValues.forEach(value => {
      const tag = document.createElement('span');
      tag.className = 'selected-tag';
      tag.innerHTML = `
        ${value}
        <span class="remove-tag" data-value="${value}">&times;</span>
      `;
      tagsContainer.appendChild(tag);
    });
    
    // Update container styling
    if (selectedValues.length > 0) {
      multiSelectContainer.classList.add('has-value');
    } else {
      multiSelectContainer.classList.remove('has-value');
    }
    
    // Update option selected state
    options.forEach(option => {
      if (selectedValues.includes(option.dataset.value)) {
        option.classList.add('selected-option');
      } else {
        option.classList.remove('selected-option');
      }
    });
    
    // Trigger updates
    updateReviewSection();
    updateIdCardPreview();
  }
  
  // Show dropdown on focus or click on container
  multiSelectContainer.addEventListener('click', () => {
    searchInput.focus();
    dropdown.classList.add('active');
  });
  
  searchInput.addEventListener('focus', () => {
    dropdown.classList.add('active');
  });
  
  // Filter options on input
  searchInput.addEventListener('input', () => {
    const searchTerm = searchInput.value.toLowerCase();
    let hasVisibleOptions = false;
    
    options.forEach(option => {
      const text = option.textContent.toLowerCase();
      if (text.includes(searchTerm)) {
        option.classList.remove('hidden');
        hasVisibleOptions = true;
      } else {
        option.classList.add('hidden');
      }
    });
    
    // Show "no results" message if needed
    let noResults = dropdown.querySelector('.no-results');
    if (!hasVisibleOptions) {
      if (!noResults) {
        noResults = document.createElement('div');
        noResults.className = 'no-results';
        noResults.textContent = 'No matching campaigns';
        optionsContainer.appendChild(noResults);
      }
      noResults.style.display = 'block';
    } else if (noResults) {
      noResults.style.display = 'none';
    }
    
    dropdown.classList.add('active');
  });
  
  // Handle option click (toggle selection)
  options.forEach(option => {
    option.addEventListener('click', (e) => {
      e.stopPropagation();
      const value = option.dataset.value;
      
      if (selectedValues.includes(value)) {
        // Remove from selection
        selectedValues = selectedValues.filter(v => v !== value);
      } else {
        // Add to selection
        selectedValues.push(value);
      }
      
      updateSelection();
      
      // Clear search input and keep dropdown open for more selections
      searchInput.value = '';
      searchInput.focus();
      
      // Show all options again
      options.forEach(o => o.classList.remove('hidden'));
    });
  });
  
  // Handle remove tag click
  tagsContainer.addEventListener('click', (e) => {
    if (e.target.classList.contains('remove-tag')) {
      e.stopPropagation();
      const value = e.target.dataset.value;
      selectedValues = selectedValues.filter(v => v !== value);
      updateSelection();
    }
  });
  
  // Close dropdown when clicking outside
  document.addEventListener('click', (e) => {
    if (!dropdown.contains(e.target)) {
      dropdown.classList.remove('active');
    }
  });
  
  // Handle keyboard navigation
  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      dropdown.classList.remove('active');
    } else if (e.key === 'Backspace' && searchInput.value === '' && selectedValues.length > 0) {
      // Remove last tag on backspace if search is empty
      selectedValues.pop();
      updateSelection();
    }
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
    window.aiGenerationController = state.aiGenerationController; // Make accessible globally
    
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

// Regenerate with outfit selection from dropdown
async function regenerateWithOutfit() {
  const outfitSelect = document.getElementById('outfitSelect');
  const selectedOutfit = outfitSelect ? outfitSelect.value : 'male_1';
  console.log('=== regenerateWithOutfit called ===');
  console.log('Selected outfit:', selectedOutfit);
  await regenerateAIImage(selectedOutfit);
}

// Make functions globally accessible for inline onclick
window.regenerateAIImage = regenerateAIImage;
window.simpleRegenerateAI = simpleRegenerateAI;
window.regenerateWithOutfit = regenerateWithOutfit;
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
  console.log('[Preview] updateIdCardPreview called');
  
  // Helper function to safely get element value
  const getValue = (id) => {
    const el = document.getElementById(id);
    if (!el) return '';
    return el.value.trim();
  };

  // Update Nickname (vertical text on blue sidebar)
  // Use only first word of the nickname for the ID card display
  const nickname = getValue('id_nickname');
  const nicknameEl = document.getElementById('id_preview_nickname');
  if (nicknameEl) {
    const firstWord = nickname ? nickname.trim().split(' ')[0] : 'Nickname';
    nicknameEl.textContent = firstWord;
  }

  // Update Full Name (constructed from first_name, middle_initial, last_name)
  const firstName = getValue('first_name');
  const middleInitial = getValue('middle_initial');
  const lastName = getValue('last_name');
  
  // Build full name with line break for long names:
  // Format: "FirstName SecondName M.I. <br> LastName Suffix"
  // Get suffix value
  const suffix = getSuffixValue();
  
  let fullNameLine1 = '';
  let fullNameLine2 = '';
  if (firstName) {
    fullNameLine1 = firstName;
    if (middleInitial) {
      fullNameLine1 += ' ' + middleInitial + (middleInitial.endsWith('.') ? '' : '.');
    }
    if (lastName) {
      fullNameLine2 = lastName;
    }
    if (suffix) {
      fullNameLine2 += (fullNameLine2 ? ' ' : '') + suffix;
    }
  } else if (lastName) {
    fullNameLine1 = lastName;
    if (suffix) {
      fullNameLine1 += ' ' + suffix;
    }
  }
  
  const fullnameEl = document.getElementById('id_preview_fullname');
  if (fullnameEl) {
    if (fullNameLine1 && fullNameLine2) {
      fullnameEl.innerHTML = fullNameLine1 + '<br>' + fullNameLine2;
    } else {
      fullnameEl.textContent = fullNameLine1 || 'Employee Fullname';
    }
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
  console.log('[Preview] ID Number:', idNumber);

  // Update Barcode - generates CODE128 barcode from ID number
  const barcodeImg = document.getElementById('id_preview_barcode');
  const barcodeFallback = document.getElementById('id_barcode_fallback');
  console.log('[Preview] Barcode elements found:', { barcodeImg: !!barcodeImg, barcodeFallback: !!barcodeFallback });
  updateBarcodeDisplay(idNumber, barcodeImg, barcodeFallback, { width: 500, height: 55 });

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

  // Update dynamic website URLs
  // Back-side URL format: www.okpo.com/spm/(FirstName + LastNameInitial + MiddleInitial)
  // All lowercase, no spaces, no separators
  // Example: Miguel Manuel Lacaden → www.okpo.com/spm/miguelml
  const firstNameLower = firstName ? firstName.toLowerCase() : '';
  const lastNameInitialLower = lastName ? lastName.charAt(0).toLowerCase() : '';
  const middleInitialLower = middleInitial ? middleInitial.replace('.', '').charAt(0).toLowerCase() : '';
  const backDynamicUrl = `www.okpo.com/spm/${firstNameLower}${lastNameInitialLower}${middleInitialLower}`;
  
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
  
  // Generate vCard QR code for single template SPMC backside using QuickChart API
  const vcardQrImg = document.getElementById('id_back_vcard_qr');
  const vcardQrPlaceholder = document.getElementById('id_back_vcard_qr_placeholder');
  if (vcardQrImg && vcardQrPlaceholder) {
    // Get additional employee data for vCard
    const email = getValue('email');
    const phone = getValue('personal_number');
    
    // Build vCard 3.0 string
    // N: Last;First;Middle;;
    // FN: First M. Last
    let vcardFn = firstName || '';
    if (middleInitial) {
      const mi = middleInitial.replace('.', '').charAt(0).toUpperCase();
      vcardFn += ' ' + mi + '.';
    }
    if (lastName) vcardFn += ' ' + lastName;
    if (suffix) vcardFn += ' ' + suffix;
    vcardFn = vcardFn.trim();
    
    const vcardMiddle = middleInitial ? middleInitial.replace('.', '').charAt(0) : '';
    const vcardN = `${lastName || ''};${firstName || ''};${vcardMiddle};;${suffix || ''}`;
    
    // Build complete vCard
    let vcard = 'BEGIN:VCARD\n';
    vcard += 'VERSION:3.0\n';
    vcard += `N:${vcardN}\n`;
    vcard += `FN:${vcardFn || 'Employee'}\n`;
    vcard += 'ORG:S.P. Madrid & Associates\n';
    // Use position for TITLE (Freelancer, Intern, Others, or default)
    vcard += `TITLE:${position || 'Employee'}\n`;
    if (phone) vcard += `TEL:${phone}\n`;
    if (email) vcard += `EMAIL:${email}\n`;
    vcard += 'END:VCARD';
    
    // Generate QuickChart QR URL
    const encodedVcard = encodeURIComponent(vcard);
    const qrUrl = `https://quickchart.io/qr?text=${encodedVcard}&size=200&ecLevel=Q&format=png&margin=1`;
    
    // Update QR image
    if (firstName || lastName) {
      vcardQrImg.src = qrUrl;
      vcardQrImg.style.display = 'block';
      vcardQrPlaceholder.style.display = 'none';
    } else {
      vcardQrImg.style.display = 'none';
      vcardQrPlaceholder.style.display = 'block';
    }
  }
  
  // Generate URL QR code for bottom of single template SPMC backside with embedded OKPO logo
  const urlQrImg = document.getElementById('id_back_url_qr');
  const urlQrPlaceholder = document.getElementById('id_back_url_qr_placeholder');
  if (urlQrImg && urlQrPlaceholder) {
    // Reuse the same URL format as the displayed URL text
    const employeeUrl = `https://${backDynamicUrl}`;
    
    if (firstNameLower) {
      // OKPO logo URL (must be URL-encoded)
      const logoUrl = 'https://239dc453931a663c0cfa3bb867f1aaae.cdn.bubble.io/cdn-cgi/image/w=,h=,f=auto,dpr=1,fit=contain/f1727917655428x617042099316169600/okpologo.jpg';
      const encodedLogoUrl = encodeURIComponent(logoUrl);
      const encodedEmployeeUrl = encodeURIComponent(employeeUrl);
      
      // Generate QuickChart QR URL with embedded logo using centerImageUrl parameter
      const urlQrCode = `https://quickchart.io/qr?text=${encodedEmployeeUrl}&size=200&ecLevel=H&format=png&margin=1&centerImageUrl=${encodedLogoUrl}&centerImageSizeRatio=0.25`;
      urlQrImg.src = urlQrCode;
      urlQrImg.style.display = 'block';
      urlQrPlaceholder.style.display = 'none';
    } else {
      urlQrImg.style.display = 'none';
      urlQrPlaceholder.style.display = 'block';
    }
  }
  
  // Also update dual template preview if in Reprocessor mode
  if (typeof updateDualTemplatePreview === 'function') {
    updateDualTemplatePreview();
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
  const suffixValue = getSuffixValue();
  setText('review_suffix', suffixValue || '-');
  setText('review_id_nickname', getValue('id_nickname'));
  setText('review_id_number', getValue('id_number'));

  // Update text fields - Work Details (position from radio buttons)
  const position = getSelectedPosition();
  setText('review_position', position || '-');
  setText('review_location_branch', getValue('location_branch'));

  // Update Field Officer details in review section
  const reviewFieldOfficerDetails = document.getElementById('review_field_officer_details');
  if (position === 'Field Officer') {
    if (reviewFieldOfficerDetails) reviewFieldOfficerDetails.style.display = 'block';
    
    // Get Field Officer type
    const foTypeRadio = document.querySelector('input[name="field_officer_type"]:checked');
    setText('review_fo_type', foTypeRadio ? foTypeRadio.value : '-');
    
    // Get other Field Officer fields
    setText('review_field_clearance', 'Level 5');
    setText('review_fo_division', getValue('fo_division') || '-');
    setText('review_fo_department', getValue('fo_department') || '-');
    setText('review_fo_campaign', getValue('fo_campaign') || '-');
  } else {
    if (reviewFieldOfficerDetails) reviewFieldOfficerDetails.style.display = 'none';
  }

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

    // Prevent double-submit
    if (state.isSubmitting) {
      showMessage('Submission in progress. Please wait...', 'info');
      return;
    }

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

    // Validate Field Officer fields if Field Officer is selected
    const selectedPosition = getSelectedPosition();
    if (selectedPosition === 'Field Officer') {
      // Check Field Officer Type
      const foTypeSelected = document.querySelector('input[name="field_officer_type"]:checked');
      if (!foTypeSelected) {
        isValid = false;
        showMessage('Please select a Field Officer Type (Reprocessor or Others).', 'error');
        return;
      }
      
      // Only require Department, Campaign for Reprocessor/Shared types
      // (Division is hidden from UI — not required from user)
      if (foTypeSelected.value === 'Reprocessor' || foTypeSelected.value === 'Shared') {
        // Check Department - using searchable dropdown (hidden input stores value)
        const foDepartment = document.getElementById('fo_department');
        const foDepartmentSearch = document.getElementById('fo_department_search');
        if (!foDepartment || !foDepartment.value || foDepartment.value === '') {
          isValid = false;
          if (foDepartmentSearch) foDepartmentSearch.style.borderColor = 'var(--color-danger)';
        } else {
          if (foDepartmentSearch) foDepartmentSearch.style.borderColor = '';
        }
        
        // Check Campaign - using searchable dropdown (hidden input stores value)
        const foCampaign = document.getElementById('fo_campaign');
        const foCampaignSearch = document.getElementById('fo_campaign_search');
        if (!foCampaign || !foCampaign.value || foCampaign.value === '') {
          isValid = false;
          if (foCampaignSearch) foCampaignSearch.style.borderColor = 'var(--color-danger)';
        } else {
          if (foCampaignSearch) foCampaignSearch.style.borderColor = '';
        }
      }
    }

    if (!isValid) {
      showMessage('Please fill in all required fields.', 'error');
      return;
    }

    // ========================================
    // QA-Grade Form Validation (mirror backend rules)
    // ========================================
    const formValidationErrors = validateFormBeforeSubmit();
    if (formValidationErrors.length > 0) {
      // Show first error and highlight all fields
      showMessage(formValidationErrors[0], 'error');
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
    state.isSubmitting = true;
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
        // Show success toast first
        showToast('Success!', 'Your ID registration has been submitted successfully. HR will review and process your request shortly.', 'success');

        // Show success modal after brief delay
        setTimeout(() => {
          showSuccessModal();
        }, 1500);
        
        // Reset submit button state
        elements.btnSubmit.classList.remove('loading');
        elements.btnSubmit.textContent = 'Submitted';
      } else {
        throw new Error(result.detail || result.error || 'Submission failed');
      }
    } catch (error) {
      console.error('Submission error:', error);
      showMessage(`Error: ${error.message}. Please try again.`, 'error');

      // Re-enable submit button
      state.isSubmitting = false;
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

// ============================================
// Toast Notifications
// ============================================
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

// Remove photo function
function removePhoto() {
  const photoInput = document.getElementById('photo');
  const photoComparison = document.getElementById('photoComparison');
  const photoUploadArea = document.getElementById('photoUploadArea');
  const photoPreviewImg = document.getElementById('photoPreviewImg');
  const aiPreviewImg = document.getElementById('aiPreviewImg');
  
  // Cancel any ongoing AI generation
  if (window.aiGenerationController) {
    window.aiGenerationController.abort();
    window.aiGenerationController = null;
  }
  
  if (photoInput) {
    photoInput.value = '';
  }
  if (photoPreviewImg) {
    photoPreviewImg.src = '';
  }
  if (aiPreviewImg) {
    aiPreviewImg.src = '';
    aiPreviewImg.style.display = 'none';
  }
  if (photoComparison) {
    photoComparison.style.display = 'none';
  }
  if (photoUploadArea) {
    photoUploadArea.style.display = 'flex';
  }
  
  // Reset AI preview states
  const aiLoading = document.getElementById('aiLoading');
  const aiError = document.getElementById('aiError');
  const aiActions = document.getElementById('aiActions');
  const aiPreviewContainer = document.getElementById('aiPreviewContainer');
  if (aiLoading) aiLoading.style.display = 'none';
  if (aiError) aiError.style.display = 'none';
  if (aiActions) aiActions.style.display = 'none';
  if (aiPreviewContainer) aiPreviewContainer.classList.remove('loading');
  
  // Update ID preview and review section
  updateIdCardPreview();
  updateReviewSection();
}
window.removePhoto = removePhoto;

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
  const fieldOfficeFront = document.getElementById('idCardFieldOfficeFront');
  const fieldOfficeBack = document.getElementById('idCardFieldOfficeBack');
  const flipBtns = document.querySelectorAll('.flip-btn');
  
  // Get selected position to determine which template to show
  const position = getSelectedPosition();
  const isFieldOfficer = position === 'Field Officer';
  
  // Update button states
  flipBtns.forEach(btn => {
    if (btn.dataset.side === side) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
  
  // Hide all cards first
  if (frontCard) frontCard.style.display = 'none';
  if (backCard) backCard.style.display = 'none';
  if (fieldOfficeFront) fieldOfficeFront.style.display = 'none';
  if (fieldOfficeBack) fieldOfficeBack.style.display = 'none';
  
  // Show appropriate card based on position and side
  if (isFieldOfficer) {
    // Show Field Office template
    if (side === 'front') {
      if (fieldOfficeFront) fieldOfficeFront.style.display = 'block';
    } else {
      if (fieldOfficeBack) fieldOfficeBack.style.display = 'block';
    }
  } else {
    // Show regular template
    if (side === 'front') {
      if (frontCard) frontCard.style.display = 'block';
    } else {
      if (backCard) backCard.style.display = 'block';
    }
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
    emergencyContactEl.textContent = contact || '09XXXXXXXXX';
  }
  
  // Update Emergency Address
  const emergencyAddressEl = document.getElementById('id_back_emergency_address');
  if (emergencyAddressEl) {
    const address = getValue('emergency_address');
    emergencyAddressEl.textContent = address || 'Contact Address';
  }
}

// ============================================
// Field Office ID Card Preview Update
// ============================================
function updateFieldOfficePreview() {
  // Helper function to safely get element value
  const getValue = (id) => {
    const el = document.getElementById(id);
    if (!el) return '';
    return el.value.trim();
  };

  // Get selected position
  const position = getSelectedPosition();
  const isFieldOfficer = position === 'Field Officer';
  
  // Get the currently active side (front or back)
  const activeFrontBtn = document.querySelector('.flip-btn[data-side="front"].active');
  const currentSide = activeFrontBtn ? 'front' : 'back';
  
  // Get all ID card elements
  const frontCard = document.getElementById('idCardFront');
  const backCard = document.getElementById('idCardBack');
  const fieldOfficeFront = document.getElementById('idCardFieldOfficeFront');
  const fieldOfficeBack = document.getElementById('idCardFieldOfficeBack');
  
  // Show/hide appropriate templates based on position
  if (isFieldOfficer) {
    // Hide regular templates, show Field Office templates
    if (frontCard) frontCard.style.display = 'none';
    if (backCard) backCard.style.display = 'none';
    
    if (currentSide === 'front') {
      if (fieldOfficeFront) fieldOfficeFront.style.display = 'block';
      if (fieldOfficeBack) fieldOfficeBack.style.display = 'none';
    } else {
      if (fieldOfficeFront) fieldOfficeFront.style.display = 'none';
      if (fieldOfficeBack) fieldOfficeBack.style.display = 'block';
    }
  } else {
    // Hide Field Office templates, show regular templates
    if (fieldOfficeFront) fieldOfficeFront.style.display = 'none';
    if (fieldOfficeBack) fieldOfficeBack.style.display = 'none';
    
    if (currentSide === 'front') {
      if (frontCard) frontCard.style.display = 'block';
      if (backCard) backCard.style.display = 'none';
    } else {
      if (frontCard) frontCard.style.display = 'none';
      if (backCard) backCard.style.display = 'block';
    }
  }
  
  // Only update Field Office placeholders if Field Officer is selected
  if (!isFieldOfficer) return;
  
  // Update Employee Name (First M. + Last Name format for ID) - Include middle initial with dot
  const firstName = getValue('first_name');
  const middleInitial = getValue('middle_initial');
  const lastName = getValue('last_name');
  const suffix = getSuffixValue();
  
  let displayName = '';
  if (firstName && lastName) {
    // Format: FirstName M.<br>LastName Suffix
    displayName = firstName;
    if (middleInitial) {
      // Use first character of middle initial field, uppercase, with dot
      displayName += ' ' + middleInitial.charAt(0).toUpperCase() + '.';
    }
    displayName += '\n' + lastName;
    if (suffix) {
      displayName += ' ' + suffix;
    }
  } else if (firstName) {
    displayName = firstName;
  } else if (lastName) {
    displayName = lastName;
  } else {
    displayName = 'Name\nPlaceholder';
  }
  
  const nameEl = document.getElementById('id_fo_preview_name');
  if (nameEl) {
    nameEl.innerHTML = displayName.replace('\n', '<br>');
  }
  
  // Update Position (always "LEGAL OFFICER" for Field Officer)
  const positionEl = document.getElementById('id_fo_preview_position');
  if (positionEl) {
    positionEl.textContent = 'LEGAL OFFICER';
  }
  
  // Update Field Clearance Level (based on location/branch or default)
  // For now, display a default level - can be customized later
  const clearanceEl = document.getElementById('id_fo_preview_clearance');
  if (clearanceEl) {
    clearanceEl.textContent = 'Level 5';
  }
  
  // Update ID Number
  const idNumber = getValue('id_number');
  const idNumberEl = document.getElementById('id_fo_preview_idnumber');
  if (idNumberEl) {
    idNumberEl.textContent = idNumber || 'ID Number Placeholder';
  }

  // Update Barcode - generates CODE128 barcode from ID number
  // Container is 180x40, so with width=500 we need height≈111 to maintain aspect ratio and fill the container
  const foBarcodeImg = document.getElementById('id_fo_preview_barcode');
  const foBarcodeFallback = document.getElementById('id_fo_barcode_fallback');
  updateBarcodeDisplay(idNumber, foBarcodeImg, foBarcodeFallback, { width: 500, height: 111 });
  
  // Update Photo - prefer AI generated, fallback to original
  const aiPreviewImg = document.getElementById('aiPreviewImg');
  const photoPreviewImg = document.getElementById('photoPreviewImg');
  const foPhotoEl = document.getElementById('id_fo_preview_photo');
  const foPhotoPlaceholder = document.getElementById('id_fo_photo_placeholder');
  const foPhotoContainer = document.getElementById('id_fo_photo_container');
  
  let photoSrc = '';
  
  // Check AI generated photo first
  if (aiPreviewImg && aiPreviewImg.style.display !== 'none' && aiPreviewImg.src && 
      (aiPreviewImg.src.startsWith('data:') || aiPreviewImg.src.startsWith('http') || aiPreviewImg.src.startsWith('blob:'))) {
    photoSrc = aiPreviewImg.src;
  }
  // Fallback to original photo
  else if (photoPreviewImg && photoPreviewImg.src && 
           (photoPreviewImg.src.startsWith('data:') || photoPreviewImg.src.startsWith('blob:'))) {
    photoSrc = photoPreviewImg.src;
  }
  
  if (foPhotoEl && foPhotoPlaceholder) {
    if (photoSrc) {
      foPhotoEl.src = photoSrc;
      foPhotoEl.style.display = 'block';
      foPhotoPlaceholder.style.display = 'none';
      if (foPhotoContainer) foPhotoContainer.classList.add('has-image');
    } else {
      foPhotoEl.style.display = 'none';
      foPhotoEl.removeAttribute('src');
      foPhotoPlaceholder.style.display = 'block';
      if (foPhotoContainer) foPhotoContainer.classList.remove('has-image');
    }
  }
  
  // Update Signature
  const signatureData = document.getElementById('signature_data');
  const foSignatureEl = document.getElementById('id_fo_preview_signature');
  const foSignaturePlaceholder = document.getElementById('id_fo_signature_placeholder');
  const foSignatureContainer = document.getElementById('id_fo_signature_container');
  
  const signatureSrc = signatureData ? signatureData.value : '';
  const hasSignature = signatureSrc && signatureSrc.startsWith('data:');
  
  if (foSignatureEl && foSignaturePlaceholder) {
    if (hasSignature) {
      foSignatureEl.src = signatureSrc;
      foSignatureEl.style.display = 'block';
      foSignaturePlaceholder.style.display = 'none';
      if (foSignatureContainer) foSignatureContainer.classList.add('has-image');
    } else {
      foSignatureEl.style.display = 'none';
      foSignatureEl.removeAttribute('src');
      foSignaturePlaceholder.style.display = 'block';
      if (foSignatureContainer) foSignatureContainer.classList.remove('has-image');
    }
  }
}

// Make updateFieldOfficePreview available globally
window.updateFieldOfficePreview = updateFieldOfficePreview;

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
