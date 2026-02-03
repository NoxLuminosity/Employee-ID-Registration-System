"""
Barcode Service - BarcodeAPI.org Integration
Generates barcode images for employee ID numbers using the BarcodeAPI.org service.

API Documentation: https://barcodeapi.org/api.html

Features:
- CODE128 barcode generation (default, suitable for alphanumeric IDs)
- QR code generation (alternative format)
- Automatic URL encoding for special characters
- Error handling and fallback behavior
- Rate limit awareness

Usage:
    from app.services.barcode_service import get_barcode_url, get_barcode_image

    # Get a direct URL to embed in HTML
    url = get_barcode_url("EMP-12345")
    
    # Get the barcode image bytes
    image_data, error = get_barcode_image("EMP-12345")
"""
import logging
import urllib.parse
import urllib.request
import urllib.error
from typing import Optional, Tuple
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)

# BarcodeAPI.org base URL
BARCODE_API_BASE_URL = "https://barcodeapi.org/api"


class BarcodeType(str, Enum):
    """
    Supported barcode types from BarcodeAPI.org.
    See https://barcodeapi.org/types.html for full list.
    """
    AUTO = "auto"          # Automatic type detection
    CODE128 = "128"        # CODE128 - Alphanumeric, compact (RECOMMENDED for employee IDs)
    CODE39 = "39"          # CODE39 - Alphanumeric, widely used
    QR = "qr"              # QR Code - 2D barcode
    DATAMATRIX = "dm"      # DataMatrix - 2D barcode
    EAN13 = "ean13"        # EAN-13 - Numeric only, 13 digits
    UPC = "upca"           # UPC-A - Numeric only, 12 digits


# Default barcode configuration
DEFAULT_BARCODE_TYPE = BarcodeType.CODE128
DEFAULT_BARCODE_OPTIONS = {
    "height": 40,          # Height in pixels (for 1D barcodes)
    # "fg": "000000",      # Foreground color (black) - optional
    # "bg": "ffffff",      # Background color (white) - optional
}


def get_barcode_url(
    data: str,
    barcode_type: BarcodeType = DEFAULT_BARCODE_TYPE,
    options: Optional[dict] = None
) -> str:
    """
    Generate a URL to fetch a barcode image from BarcodeAPI.org.
    
    This URL can be used directly in HTML <img> tags for client-side rendering.
    The API returns PNG images by default.
    
    Args:
        data: The data to encode in the barcode (e.g., employee ID number)
        barcode_type: The type of barcode to generate (default: CODE128)
        options: Optional customization options (height, fg, bg, etc.)
    
    Returns:
        Full URL to the barcode image
    
    Example:
        >>> get_barcode_url("EMP-12345")
        'https://barcodeapi.org/api/128/EMP-12345'
        
        >>> get_barcode_url("EMP-12345", options={"height": 50})
        'https://barcodeapi.org/api/128/EMP-12345?height=50'
    """
    if not data:
        logger.warning("get_barcode_url called with empty data")
        return ""
    
    # URL-encode the data to handle special characters
    encoded_data = urllib.parse.quote(str(data), safe='')
    
    # Build base URL
    url = f"{BARCODE_API_BASE_URL}/{barcode_type.value}/{encoded_data}"
    
    # Add options as query parameters if provided
    if options:
        query_params = urllib.parse.urlencode(options)
        url = f"{url}?{query_params}"
    
    logger.debug(f"Generated barcode URL: {url}")
    return url


def get_barcode_image(
    data: str,
    barcode_type: BarcodeType = DEFAULT_BARCODE_TYPE,
    options: Optional[dict] = None,
    timeout: int = 10
) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Fetch the barcode image bytes from BarcodeAPI.org.
    
    This can be used for server-side processing or caching the barcode images.
    
    Args:
        data: The data to encode in the barcode
        barcode_type: The type of barcode to generate
        options: Optional customization options
        timeout: Request timeout in seconds
    
    Returns:
        Tuple of (image_bytes, error_message)
        - On success: (bytes, None)
        - On failure: (None, error_string)
    
    Example:
        >>> image_data, error = get_barcode_image("EMP-12345")
        >>> if error:
        ...     print(f"Error: {error}")
        >>> else:
        ...     with open("barcode.png", "wb") as f:
        ...         f.write(image_data)
    """
    if not data:
        return None, "No data provided for barcode generation"
    
    url = get_barcode_url(data, barcode_type, options)
    
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "EmployeeIDSystem/1.0",
                "Accept": "image/png"
            }
        )
        
        with urllib.request.urlopen(request, timeout=timeout) as response:
            # Check for rate limiting
            remaining_tokens = response.headers.get("X-RateLimit-Tokens")
            if remaining_tokens:
                tokens = float(remaining_tokens)
                if tokens < 100:
                    logger.warning(f"BarcodeAPI rate limit low: {tokens} tokens remaining")
            
            # Read image data
            image_data = response.read()
            
            # Log successful generation
            barcode_content = response.headers.get("X-Barcode-Content", data)
            barcode_type_header = response.headers.get("X-Barcode-Type", "unknown")
            logger.info(f"Barcode generated: type={barcode_type_header}, content={barcode_content}")
            
            return image_data, None
            
    except urllib.error.HTTPError as e:
        error_msg = e.headers.get("X-Error-Message", str(e))
        
        # Handle specific error codes
        if e.code == 400:
            error = f"Invalid barcode data: {error_msg}"
        elif e.code == 409:
            error = f"Checksum error: {error_msg}"
        elif e.code == 429:
            error = "Rate limited. Please try again later."
        elif e.code == 500:
            error = f"Barcode generation failed: {error_msg}"
        elif e.code == 503:
            error = "BarcodeAPI service is busy. Please try again."
        else:
            error = f"HTTP error {e.code}: {error_msg}"
        
        logger.error(f"BarcodeAPI error for '{data}': {error}")
        return None, error
        
    except urllib.error.URLError as e:
        error = f"Network error: {e.reason}"
        logger.error(f"BarcodeAPI network error: {error}")
        return None, error
        
    except TimeoutError:
        error = "Request timed out"
        logger.error(f"BarcodeAPI timeout for '{data}'")
        return None, error
        
    except Exception as e:
        error = f"Unexpected error: {str(e)}"
        logger.error(f"BarcodeAPI unexpected error: {error}")
        return None, error


def validate_barcode_data(data: str, barcode_type: BarcodeType = DEFAULT_BARCODE_TYPE) -> Tuple[bool, Optional[str]]:
    """
    Validate that the data can be encoded in the specified barcode type.
    
    Args:
        data: The data to validate
        barcode_type: The target barcode type
    
    Returns:
        Tuple of (is_valid, error_message)
    
    Example:
        >>> is_valid, error = validate_barcode_data("EMP-12345")
        >>> print(is_valid)  # True
    """
    if not data:
        return False, "Data cannot be empty"
    
    if len(data) > 80:
        return False, "Data too long (max 80 characters for CODE128)"
    
    # CODE128 supports ASCII 0-127
    if barcode_type == BarcodeType.CODE128:
        for char in data:
            if ord(char) > 127:
                return False, f"Invalid character '{char}' for CODE128 (ASCII only)"
    
    # CODE39 supports limited character set
    elif barcode_type == BarcodeType.CODE39:
        valid_chars = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-. $/+%")
        for char in data.upper():
            if char not in valid_chars:
                return False, f"Invalid character '{char}' for CODE39"
    
    # EAN-13 requires exactly 12 or 13 digits
    elif barcode_type == BarcodeType.EAN13:
        if not data.isdigit():
            return False, "EAN-13 requires numeric data only"
        if len(data) not in [12, 13]:
            return False, "EAN-13 requires 12 or 13 digits"
    
    return True, None


def get_barcode_url_safe(
    data: str,
    barcode_type: BarcodeType = DEFAULT_BARCODE_TYPE,
    fallback_text: bool = True
) -> str:
    """
    Get a barcode URL with validation and optional fallback.
    
    If the data is invalid for the barcode type, returns an empty string
    or falls back to a text placeholder URL.
    
    Args:
        data: The data to encode
        barcode_type: The barcode type to generate
        fallback_text: If True, return a placeholder URL on validation failure
    
    Returns:
        Barcode URL or empty string on failure
    """
    is_valid, error = validate_barcode_data(data, barcode_type)
    
    if not is_valid:
        logger.warning(f"Invalid barcode data '{data}': {error}")
        if fallback_text:
            # Return a placeholder text image (using the auto type which handles most data)
            return get_barcode_url(data, BarcodeType.AUTO)
        return ""
    
    return get_barcode_url(data, barcode_type)
