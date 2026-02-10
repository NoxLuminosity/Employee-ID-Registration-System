"""
QA-Grade Input Validation Module
================================
Centralized validation rules for all form inputs.
Used by both create and update operations.

All validation rules are enforced at the backend level.
Frontend validation is for UX only - never trust it.
"""
import re
import logging
from typing import Tuple, Optional, List, Dict, Any
from datetime import datetime, date

logger = logging.getLogger(__name__)

# ============================================
# Phone Number Validation
# ============================================
# Rules:
# - Exactly 11 digits
# - Digits only (no spaces, +63, dashes, parentheses)
# - Must start with 09
# - Must not be all identical digits

def validate_phone_number(phone: str, field_name: str = "Phone Number") -> Tuple[bool, str, str]:
    """
    Validate Philippine mobile phone number.
    
    Args:
        phone: The phone number to validate
        field_name: Name of the field for error messages
        
    Returns:
        Tuple of (is_valid, error_message, cleaned_value)
    """
    if not phone:
        return False, f"{field_name} is required", ""
    
    # Remove all whitespace
    cleaned = phone.strip()
    
    # Remove any non-digit characters for validation
    digits_only = re.sub(r'\D', '', cleaned)
    
    # Check if exactly 11 digits
    if len(digits_only) != 11:
        return False, f"{field_name} must be exactly 11 digits (got {len(digits_only)})", digits_only
    
    # Must start with 09
    if not digits_only.startswith('09'):
        return False, f"{field_name} must start with 09", digits_only
    
    # Check for all identical digits (e.g., 00000000000, 11111111111)
    if len(set(digits_only)) == 1:
        return False, f"{field_name} cannot be all identical digits", digits_only
    
    # Additional check for common invalid patterns
    invalid_patterns = [
        '09000000000',
        '09111111111',
        '09999999999',
        '09123456789',
        '09876543210',
    ]
    if digits_only in invalid_patterns:
        return False, f"{field_name} appears to be an invalid test number", digits_only
    
    return True, "", digits_only


# ============================================
# ID Number Validation
# ============================================
# Rules:
# - Digits only (after trimming)
# - Enforce exact length if format is fixed
# - Must be unique in DB (checked separately)

def validate_id_number(id_number: str, expected_length: Optional[int] = None) -> Tuple[bool, str, str]:
    """
    Validate employee ID number.
    
    Args:
        id_number: The ID number to validate
        expected_length: Optional exact length requirement
        
    Returns:
        Tuple of (is_valid, error_message, cleaned_value)
    """
    if not id_number:
        return False, "ID Number is required", ""
    
    # Trim whitespace
    cleaned = id_number.strip()
    
    # Check for empty after trim
    if not cleaned:
        return False, "ID Number cannot be empty", ""
    
    # Allow alphanumeric and hyphens (e.g., EMP-001, FO-2024-001)
    # Remove spaces and validate
    cleaned = re.sub(r'\s+', '', cleaned)
    
    # Validate character set: alphanumeric and hyphens only
    if not re.match(r'^[A-Za-z0-9\-]+$', cleaned):
        return False, "ID Number can only contain letters, numbers, and hyphens", cleaned
    
    # Check length if specified
    if expected_length and len(cleaned) != expected_length:
        return False, f"ID Number must be exactly {expected_length} characters", cleaned
    
    # Check minimum length
    if len(cleaned) < 3:
        return False, "ID Number must be at least 3 characters", cleaned
    
    # Check maximum length
    if len(cleaned) > 50:
        return False, "ID Number cannot exceed 50 characters", cleaned
    
    return True, "", cleaned.upper()


# ============================================
# Name Validation
# ============================================
# Rules:
# - Letters, space, hyphen (-), apostrophe (' or ')
# - No numbers
# - No emoji / symbol spam
# - Auto-trim spaces
# - Collapse double spaces
# - First/Last: 2-50 chars
# - Middle Initial: exactly 1 letter, allow A or A., dot added by system

def validate_name(name: str, field_name: str, min_length: int = 2, max_length: int = 50) -> Tuple[bool, str, str]:
    """
    Validate name field (first name, last name, emergency name, etc).
    
    Args:
        name: The name to validate
        field_name: Name of the field for error messages
        min_length: Minimum required length
        max_length: Maximum allowed length
        
    Returns:
        Tuple of (is_valid, error_message, cleaned_value)
    """
    if not name:
        return False, f"{field_name} is required", ""
    
    # Trim whitespace
    cleaned = name.strip()
    
    # Collapse multiple spaces to single space
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Check for empty after trim
    if not cleaned:
        return False, f"{field_name} cannot be empty", ""
    
    # Validate character set: letters, spaces, hyphens, apostrophes, periods
    # Allow both straight and curly apostrophes
    if not re.match(r"^[A-Za-zÀ-ÿ\s\-'''.]+$", cleaned):
        # Check what invalid characters are present
        invalid_chars = re.findall(r"[^A-Za-zÀ-ÿ\s\-'''.]+", cleaned)
        if any(char.isdigit() for char in ''.join(invalid_chars)):
            return False, f"{field_name} cannot contain numbers", cleaned
        return False, f"{field_name} contains invalid characters: {''.join(set(''.join(invalid_chars)))}", cleaned
    
    # Check length
    if len(cleaned) < min_length:
        return False, f"{field_name} must be at least {min_length} characters", cleaned
    
    if len(cleaned) > max_length:
        return False, f"{field_name} cannot exceed {max_length} characters", cleaned
    
    # Title case the name for proper formatting
    # Handle hyphenated and apostrophe names properly
    formatted = format_name(cleaned)
    
    return True, "", formatted


def format_name(name: str) -> str:
    """
    Format a name with proper capitalization.
    Handles hyphenated names (Mary-Jane) and apostrophe names (O'Brien).
    """
    parts = name.split(' ')
    formatted_parts = []
    
    for part in parts:
        # Handle hyphenated names
        if '-' in part:
            formatted_parts.append('-'.join(word.capitalize() for word in part.split('-')))
        # Handle apostrophe names (O'Brien, D'Angelo)
        elif "'" in part or "'" in part:
            # Split on apostrophe
            for sep in ["'", "'"]:
                if sep in part:
                    sub_parts = part.split(sep)
                    formatted_parts.append(sep.join(word.capitalize() for word in sub_parts))
                    break
        else:
            formatted_parts.append(part.capitalize())
    
    return ' '.join(formatted_parts)


def validate_middle_initial(mi: str) -> Tuple[bool, str, str]:
    """
    Validate middle initial.
    
    Rules:
    - Exactly 1 letter
    - Allow A or A.
    - Dot added by system, not user
    
    Args:
        mi: The middle initial to validate
        
    Returns:
        Tuple of (is_valid, error_message, cleaned_value)
    """
    # Middle initial is optional
    if not mi:
        return True, "", ""
    
    # Trim whitespace
    cleaned = mi.strip()
    
    if not cleaned:
        return True, "", ""
    
    # Remove any trailing period (we add it ourselves)
    cleaned = cleaned.rstrip('.')
    
    # Should be exactly 1 letter after removing period
    if len(cleaned) != 1:
        return False, "Middle Initial must be exactly 1 letter", cleaned
    
    if not cleaned.isalpha():
        return False, "Middle Initial must be a letter", cleaned
    
    # Return uppercase with period
    return True, "", cleaned.upper() + "."


# ============================================
# Email Validation
# ============================================
# Rules:
# - Must be valid format
# - Auto-lowercase
# - Trim spaces

def validate_email(email: str, required: bool = True) -> Tuple[bool, str, str]:
    """
    Validate email address.
    
    Args:
        email: The email to validate
        required: Whether the field is required
        
    Returns:
        Tuple of (is_valid, error_message, cleaned_value)
    """
    if not email:
        if required:
            return False, "Email is required", ""
        return True, "", ""
    
    # Trim whitespace
    cleaned = email.strip()
    
    if not cleaned:
        if required:
            return False, "Email cannot be empty", ""
        return True, "", ""
    
    # Lowercase
    cleaned = cleaned.lower()
    
    # Basic email format regex
    # More permissive than RFC 5322 but catches most invalid formats
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, cleaned):
        return False, "Invalid email format", cleaned
    
    # Check for common typos
    common_typos = {
        '@gmial.com': '@gmail.com',
        '@gmal.com': '@gmail.com',
        '@gmail.con': '@gmail.com',
        '@yahooo.com': '@yahoo.com',
        '@yahoo.con': '@yahoo.com',
    }
    
    for typo, correct in common_typos.items():
        if cleaned.endswith(typo):
            suggested = cleaned.replace(typo, correct)
            return False, f"Did you mean {suggested}?", cleaned
    
    return True, "", cleaned


# ============================================
# Address Validation
# ============================================
# Rules:
# - Minimum length (block NA, -, .)
# - Allow letters, numbers, commas, hyphens, periods, spaces
# - Block emojis / symbol spam

def validate_address(address: str, field_name: str = "Address", min_length: int = 10) -> Tuple[bool, str, str]:
    """
    Validate address field.
    
    Args:
        address: The address to validate
        field_name: Name of the field for error messages
        min_length: Minimum required length
        
    Returns:
        Tuple of (is_valid, error_message, cleaned_value)
    """
    if not address:
        return True, "", ""  # Address fields are typically optional
    
    # Trim whitespace
    cleaned = address.strip()
    
    if not cleaned:
        return True, "", ""
    
    # Collapse multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Check for placeholder values
    placeholders = ['na', 'n/a', '-', '.', 'none', 'nil', 'x', 'xx', 'xxx']
    if cleaned.lower() in placeholders:
        return False, f"{field_name} cannot be a placeholder value", cleaned
    
    # Check minimum length
    if len(cleaned) < min_length:
        return False, f"{field_name} must be at least {min_length} characters", cleaned
    
    # Check for emoji/special character spam
    # Allow: letters, numbers, spaces, commas, periods, hyphens, apostrophes, slashes, #
    if not re.match(r"^[A-Za-z0-9\s,.\-'#/()]+$", cleaned):
        # Find invalid characters
        invalid_chars = re.findall(r"[^A-Za-z0-9\s,.\-'#/()]+", cleaned)
        return False, f"{field_name} contains invalid characters", cleaned
    
    return True, "", cleaned


# ============================================
# Date Validation
# ============================================
# Rules:
# - Birthdate: Not in the future, age within policy (15-80)
# - Hire Date: Not before birthdate + minimum working age

def validate_birthdate(birthdate_str: str, min_age: int = 15, max_age: int = 80) -> Tuple[bool, str, Optional[date]]:
    """
    Validate birthdate.
    
    Args:
        birthdate_str: The birthdate string to validate (various formats accepted)
        min_age: Minimum required age
        max_age: Maximum allowed age
        
    Returns:
        Tuple of (is_valid, error_message, parsed_date)
    """
    if not birthdate_str:
        return True, "", None  # Often optional
    
    cleaned = birthdate_str.strip()
    if not cleaned:
        return True, "", None
    
    # Try to parse various date formats
    parsed_date = None
    formats_to_try = [
        '%Y-%m-%d',      # ISO format
        '%m/%d/%Y',      # US format
        '%d/%m/%Y',      # EU format
        '%Y/%m/%d',      # Alternative ISO
        '%m-%d-%Y',      # US with dashes
        '%d-%m-%Y',      # EU with dashes
    ]
    
    for fmt in formats_to_try:
        try:
            parsed_date = datetime.strptime(cleaned, fmt).date()
            break
        except ValueError:
            continue
    
    if not parsed_date:
        return False, "Invalid date format. Use YYYY-MM-DD or MM/DD/YYYY", None
    
    # Check not in the future
    today = date.today()
    if parsed_date > today:
        return False, "Birthdate cannot be in the future", parsed_date
    
    # Calculate age
    age = today.year - parsed_date.year - ((today.month, today.day) < (parsed_date.month, parsed_date.day))
    
    if age < min_age:
        return False, f"Minimum age is {min_age} years", parsed_date
    
    if age > max_age:
        return False, f"Maximum age is {max_age} years", parsed_date
    
    return True, "", parsed_date


def validate_hire_date(hire_date_str: str, birthdate: Optional[date] = None, min_working_age: int = 15) -> Tuple[bool, str, Optional[date]]:
    """
    Validate hire date.
    
    Args:
        hire_date_str: The hire date string to validate
        birthdate: Optional birthdate for age check
        min_working_age: Minimum age allowed for hiring
        
    Returns:
        Tuple of (is_valid, error_message, parsed_date)
    """
    if not hire_date_str:
        return True, "", None
    
    cleaned = hire_date_str.strip()
    if not cleaned:
        return True, "", None
    
    # Try to parse date
    parsed_date = None
    formats_to_try = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']
    
    for fmt in formats_to_try:
        try:
            parsed_date = datetime.strptime(cleaned, fmt).date()
            break
        except ValueError:
            continue
    
    if not parsed_date:
        return False, "Invalid date format. Use YYYY-MM-DD", None
    
    # Check against birthdate if provided
    if birthdate:
        min_hire_date = date(birthdate.year + min_working_age, birthdate.month, birthdate.day)
        if parsed_date < min_hire_date:
            return False, f"Hire date must be after employee turned {min_working_age}", parsed_date
    
    # Check not too far in the future (allow up to 1 year for pre-hires)
    today = date.today()
    max_future = date(today.year + 1, today.month, today.day)
    if parsed_date > max_future:
        return False, "Hire date cannot be more than 1 year in the future", parsed_date
    
    return True, "", parsed_date


# ============================================
# Required Field Validation
# ============================================

def validate_required(value: Any, field_name: str) -> Tuple[bool, str]:
    """
    Validate that a required field is not empty.
    
    Args:
        value: The value to check
        field_name: Name of the field for error messages
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if value is None:
        return False, f"{field_name} is required"
    
    if isinstance(value, str):
        if not value.strip():
            return False, f"{field_name} cannot be empty or whitespace"
    
    return True, ""


def validate_dropdown_selection(value: str, field_name: str, valid_options: List[str]) -> Tuple[bool, str, str]:
    """
    Validate dropdown selection is not a placeholder.
    
    Args:
        value: The selected value
        field_name: Name of the field for error messages
        valid_options: List of valid option values
        
    Returns:
        Tuple of (is_valid, error_message, cleaned_value)
    """
    if not value:
        return False, f"Please select a {field_name}", ""
    
    cleaned = value.strip()
    
    # Check for placeholder values
    placeholders = ['', 'select', 'select...', 'choose', 'choose...', 'placeholder']
    if cleaned.lower() in placeholders:
        return False, f"Please select a valid {field_name}", cleaned
    
    # Check against valid options if provided
    if valid_options and cleaned not in valid_options:
        return False, f"Invalid {field_name} selection", cleaned
    
    return True, "", cleaned


# ============================================
# Suffix Validation
# ============================================

VALID_SUFFIXES = ['', 'Jr.', 'Sr.', 'II', 'III', 'IV', 'V', 'Other']

def validate_suffix(suffix: str, custom_suffix: str = None) -> Tuple[bool, str, str]:
    """
    Validate suffix field.
    
    Args:
        suffix: The selected suffix value
        custom_suffix: Custom suffix if 'Other' was selected
        
    Returns:
        Tuple of (is_valid, error_message, final_suffix_value)
    """
    if not suffix:
        return True, "", ""
    
    cleaned = suffix.strip()
    
    # If 'Other' selected, validate custom suffix
    if cleaned == 'Other':
        if not custom_suffix:
            return False, "Please enter a custom suffix", ""
        
        custom_cleaned = custom_suffix.strip()
        if not custom_cleaned:
            return False, "Custom suffix cannot be empty", ""
        
        # Validate custom suffix (letters and periods only)
        if not re.match(r'^[A-Za-z.]+$', custom_cleaned):
            return False, "Suffix can only contain letters and periods", custom_cleaned
        
        if len(custom_cleaned) > 10:
            return False, "Custom suffix cannot exceed 10 characters", custom_cleaned
        
        return True, "", custom_cleaned
    
    # Check against valid options
    if cleaned not in VALID_SUFFIXES:
        return False, f"Invalid suffix selection", cleaned
    
    return True, "", cleaned


# ============================================
# Position Validation
# ============================================

VALID_POSITIONS = ['Field Officer', 'Freelancer', 'Intern', 'Others']
VALID_FIELD_OFFICER_TYPES = ['Reprocessor', 'Shared', 'Others']

def validate_position(position: str, field_officer_type: str = None) -> Tuple[bool, str, str]:
    """
    Validate position field.
    
    Args:
        position: The selected position
        field_officer_type: Sub-type if position is Field Officer
        
    Returns:
        Tuple of (is_valid, error_message, cleaned_value)
    """
    if not position:
        return False, "Position is required", ""
    
    cleaned = position.strip()
    
    if cleaned not in VALID_POSITIONS:
        return False, f"Invalid position selection", cleaned
    
    # If Field Officer, validate sub-type
    if cleaned == 'Field Officer':
        if not field_officer_type:
            return False, "Field Officer Type is required for Field Officers", cleaned
        
        fo_type_cleaned = field_officer_type.strip()
        if fo_type_cleaned not in VALID_FIELD_OFFICER_TYPES:
            return False, f"Invalid Field Officer Type selection", cleaned
    
    return True, "", cleaned


# ============================================
# Branch Validation
# ============================================

VALID_BRANCHES = [
    'Bacolod', 'Batangas', 'Bulacan', 'Cagayan De Oro', 'Cavite', 
    'Cebu', 'Davao', 'General Santos', 'Iloilo', 'Laguna', 
    'Makati', 'Pampanga', 'Pangasinan', 'Paranaque', 'Pagadian',
    'Quezon City', 'Tagum', 'Zamboanga'
]

def validate_branch(branch: str) -> Tuple[bool, str, str]:
    """
    Validate branch/location field.
    
    Args:
        branch: The selected branch
        
    Returns:
        Tuple of (is_valid, error_message, cleaned_value)
    """
    if not branch:
        return False, "Location/Branch is required", ""
    
    cleaned = branch.strip()
    
    if cleaned not in VALID_BRANCHES:
        return False, f"Invalid branch selection: {cleaned}", cleaned
    
    return True, "", cleaned


# ============================================
# Comprehensive Form Validation
# ============================================

def validate_employee_form(data: Dict[str, Any]) -> Tuple[bool, Dict[str, str], Dict[str, Any]]:
    """
    Validate all employee form fields.
    
    Args:
        data: Dictionary of form field values
        
    Returns:
        Tuple of (is_valid, errors_dict, cleaned_data_dict)
    """
    errors = {}
    cleaned = {}
    
    # First Name (required)
    is_valid, error, value = validate_name(data.get('first_name', ''), "First Name", min_length=2, max_length=50)
    if not is_valid:
        errors['first_name'] = error
    cleaned['first_name'] = value
    
    # Middle Initial (optional)
    is_valid, error, value = validate_middle_initial(data.get('middle_initial', ''))
    if not is_valid:
        errors['middle_initial'] = error
    cleaned['middle_initial'] = value
    
    # Last Name (required)
    is_valid, error, value = validate_name(data.get('last_name', ''), "Last Name", min_length=2, max_length=50)
    if not is_valid:
        errors['last_name'] = error
    cleaned['last_name'] = value
    
    # Suffix (optional)
    is_valid, error, value = validate_suffix(data.get('suffix', ''), data.get('suffix_custom', ''))
    if not is_valid:
        errors['suffix'] = error
    cleaned['suffix'] = value
    
    # ID Number (required, unique check done separately)
    is_valid, error, value = validate_id_number(data.get('id_number', ''))
    if not is_valid:
        errors['id_number'] = error
    cleaned['id_number'] = value
    
    # Position (required)
    is_valid, error, value = validate_position(data.get('position', ''), data.get('field_officer_type', ''))
    if not is_valid:
        errors['position'] = error
    cleaned['position'] = value
    
    # Branch/Location (required)
    is_valid, error, value = validate_branch(data.get('location_branch', ''))
    if not is_valid:
        errors['location_branch'] = error
    cleaned['location_branch'] = value
    
    # Email (required)
    is_valid, error, value = validate_email(data.get('email', ''), required=True)
    if not is_valid:
        errors['email'] = error
    cleaned['email'] = value
    
    # Personal Number (required)
    is_valid, error, value = validate_phone_number(data.get('personal_number', ''), "Personal Number")
    if not is_valid:
        errors['personal_number'] = error
    cleaned['personal_number'] = value
    
    # Emergency Contact (optional but validate format if provided)
    emergency_contact = data.get('emergency_contact', '')
    if emergency_contact and emergency_contact.strip():
        is_valid, error, value = validate_phone_number(emergency_contact, "Emergency Contact")
        if not is_valid:
            errors['emergency_contact'] = error
        cleaned['emergency_contact'] = value
    else:
        cleaned['emergency_contact'] = ''
    
    # Emergency Name (optional)
    emergency_name = data.get('emergency_name', '')
    if emergency_name and emergency_name.strip():
        is_valid, error, value = validate_name(emergency_name, "Emergency Contact Name", min_length=2, max_length=100)
        if not is_valid:
            errors['emergency_name'] = error
        cleaned['emergency_name'] = value
    else:
        cleaned['emergency_name'] = ''
    
    # Emergency Address (optional)
    emergency_address = data.get('emergency_address', '')
    if emergency_address and emergency_address.strip():
        is_valid, error, value = validate_address(emergency_address, "Emergency Address", min_length=10)
        if not is_valid:
            errors['emergency_address'] = error
        cleaned['emergency_address'] = value
    else:
        cleaned['emergency_address'] = ''
    
    # Determine overall validity
    overall_valid = len(errors) == 0
    
    if not overall_valid:
        logger.warning(f"Form validation failed with {len(errors)} errors: {errors}")
    
    return overall_valid, errors, cleaned


def check_id_number_unique(id_number: str, exclude_id: Optional[int] = None) -> bool:
    """
    Check if an ID number is unique in the database.
    
    Args:
        id_number: The ID number to check
        exclude_id: Optional employee ID to exclude (for updates)
        
    Returns:
        True if unique, False if duplicate exists
    """
    from app.database import get_employee_by_id_number
    
    existing = get_employee_by_id_number(id_number)
    
    if not existing:
        return True
    
    # If updating, check if it's the same record
    if exclude_id and existing.get('id') == exclude_id:
        return True
    
    return False
