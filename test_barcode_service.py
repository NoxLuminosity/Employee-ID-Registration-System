"""
Test Suite for Barcode Service Integration
Tests the BarcodeAPI.org integration for employee ID card barcode generation.

Run with: python -m pytest test_barcode_service.py -v
Or run directly: python test_barcode_service.py
"""
import unittest
import sys
import os

# Add the app directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.barcode_service import (
    get_barcode_url,
    get_barcode_image,
    validate_barcode_data,
    get_barcode_url_safe,
    BarcodeType,
    BARCODE_API_BASE_URL
)


class TestBarcodeUrlGeneration(unittest.TestCase):
    """Test barcode URL generation functionality."""
    
    def test_basic_url_generation(self):
        """Test basic barcode URL generation with default settings."""
        url = get_barcode_url("EMP-12345")
        
        self.assertIn(BARCODE_API_BASE_URL, url)
        self.assertIn("/128/", url)  # Default is CODE128
        self.assertIn("EMP-12345", url)
        print(f"[OK] Basic URL: {url}")
    
    def test_url_with_code128(self):
        """Test CODE128 barcode URL generation."""
        url = get_barcode_url("EMP-12345", BarcodeType.CODE128)
        
        self.assertIn("/128/", url)
        print(f"[OK] CODE128 URL: {url}")
    
    def test_url_with_qr(self):
        """Test QR code URL generation."""
        url = get_barcode_url("EMP-12345", BarcodeType.QR)
        
        self.assertIn("/qr/", url)
        print(f"[OK] QR Code URL: {url}")
    
    def test_url_with_code39(self):
        """Test CODE39 barcode URL generation."""
        url = get_barcode_url("EMP12345", BarcodeType.CODE39)
        
        self.assertIn("/39/", url)
        print(f"[OK] CODE39 URL: {url}")
    
    def test_url_with_custom_height(self):
        """Test barcode URL with custom height parameter."""
        url = get_barcode_url("EMP-12345", BarcodeType.CODE128, {"height": 60})
        
        self.assertIn("height=60", url)
        print(f"[OK] Custom height URL: {url}")
    
    def test_url_encoding_special_characters(self):
        """Test URL encoding for special characters in ID."""
        url = get_barcode_url("EMP/001 Test")
        
        # Special characters should be URL-encoded
        self.assertIn("EMP%2F001%20Test", url)
        print(f"[OK] URL-encoded: {url}")
    
    def test_empty_data_returns_empty_string(self):
        """Test that empty data returns empty string."""
        url = get_barcode_url("")
        self.assertEqual(url, "")
        
        url = get_barcode_url(None)
        self.assertEqual(url, "")
        print("[OK] Empty data handled correctly")


class TestBarcodeValidation(unittest.TestCase):
    """Test barcode data validation."""
    
    def test_valid_code128_data(self):
        """Test validation of valid CODE128 data."""
        is_valid, error = validate_barcode_data("EMP-12345", BarcodeType.CODE128)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        print("[OK] Valid CODE128 data accepted")
    
    def test_empty_data_rejected(self):
        """Test that empty data is rejected."""
        is_valid, error = validate_barcode_data("", BarcodeType.CODE128)
        
        self.assertFalse(is_valid)
        self.assertIn("empty", error.lower())
        print("[OK] Empty data rejected")
    
    def test_too_long_data_rejected(self):
        """Test that overly long data is rejected."""
        long_data = "A" * 100
        is_valid, error = validate_barcode_data(long_data, BarcodeType.CODE128)
        
        self.assertFalse(is_valid)
        self.assertIn("long", error.lower())
        print("[OK] Long data rejected")
    
    def test_ean13_numeric_only(self):
        """Test that EAN-13 requires numeric data only."""
        # Valid 12-digit numeric
        is_valid, error = validate_barcode_data("123456789012", BarcodeType.EAN13)
        self.assertTrue(is_valid)
        
        # Invalid - contains letters
        is_valid, error = validate_barcode_data("12345678901A", BarcodeType.EAN13)
        self.assertFalse(is_valid)
        print("[OK] EAN-13 numeric validation working")


class TestBarcodeImageFetch(unittest.TestCase):
    """Test barcode image fetching from API."""
    
    def test_fetch_code128_image(self):
        """Test fetching a CODE128 barcode image."""
        image_data, error = get_barcode_image("TEST123")
        
        if error:
            # Network error is acceptable in test environment
            print(f"[WARN] Network error (expected in some environments): {error}")
            self.skipTest("Network unavailable")
        else:
            self.assertIsNotNone(image_data)
            self.assertIsInstance(image_data, bytes)
            self.assertGreater(len(image_data), 100)  # PNG should be > 100 bytes
            
            # Check PNG magic bytes
            self.assertEqual(image_data[:4], b'\x89PNG')
            print(f"[OK] Fetched CODE128 image: {len(image_data)} bytes")
    
    def test_fetch_qr_code_image(self):
        """Test fetching a QR code image."""
        image_data, error = get_barcode_image("TEST123", BarcodeType.QR)
        
        if error:
            print(f"[WARN] Network error: {error}")
            self.skipTest("Network unavailable")
        else:
            self.assertIsNotNone(image_data)
            self.assertEqual(image_data[:4], b'\x89PNG')
            print(f"[OK] Fetched QR code image: {len(image_data)} bytes")
    
    def test_invalid_barcode_returns_error(self):
        """Test that invalid barcode data returns appropriate error."""
        # Empty string should return error
        image_data, error = get_barcode_image("")
        
        self.assertIsNone(image_data)
        self.assertIsNotNone(error)
        print(f"[OK] Invalid data error: {error}")


class TestBarcodeUrlSafe(unittest.TestCase):
    """Test safe barcode URL generation with fallback."""
    
    def test_safe_url_for_valid_data(self):
        """Test safe URL generation for valid data."""
        url = get_barcode_url_safe("EMP-12345")
        
        self.assertIn(BARCODE_API_BASE_URL, url)
        self.assertIn("EMP-12345", url)
        print(f"[OK] Safe URL: {url}")
    
    def test_safe_url_empty_on_invalid_without_fallback(self):
        """Test that invalid data returns empty without fallback."""
        # Very long string should fail validation
        long_id = "X" * 100
        url = get_barcode_url_safe(long_id, BarcodeType.CODE128, fallback_text=False)
        
        self.assertEqual(url, "")
        print("[OK] Empty URL returned without fallback")


class TestAPIEndpointExamples(unittest.TestCase):
    """
    Example requests and responses for the barcode API endpoints.
    These tests document the expected API behavior.
    """
    
    def test_example_get_barcode_url_endpoint(self):
        """
        Example: GET /api/barcode/{id_number}
        
        Request:
            GET /api/barcode/EMP-12345
            GET /api/barcode/EMP-12345?barcode_type=qr
            GET /api/barcode/EMP-12345?height=60
        
        Response (200 OK):
            {
                "success": true,
                "barcode_url": "https://barcodeapi.org/api/128/EMP-12345?height=40",
                "id_number": "EMP-12345",
                "barcode_type": "128"
            }
        
        Response (400 Bad Request - Invalid data):
            {
                "success": false,
                "error": "Data too long (max 80 characters for CODE128)",
                "id_number": "VERY_LONG_ID..."
            }
        """
        # Generate expected URL
        expected_url = get_barcode_url("EMP-12345", BarcodeType.CODE128, {"height": 40})
        
        # Expected response structure
        expected_response = {
            "success": True,
            "barcode_url": expected_url,
            "id_number": "EMP-12345",
            "barcode_type": "128"
        }
        
        print("\n[EXAMPLE] API Response:")
        print(f"   GET /api/barcode/EMP-12345")
        print(f"   Response: {expected_response}")
        
        self.assertIn("barcodeapi.org", expected_url)
    
    def test_example_get_barcode_image_endpoint(self):
        """
        Example: GET /api/barcode/{id_number}/image
        
        Request:
            GET /api/barcode/EMP-12345/image
            GET /api/barcode/EMP-12345/image?barcode_type=qr
        
        Response (200 OK):
            Content-Type: image/png
            Cache-Control: public, max-age=86400
            X-Barcode-Content: EMP-12345
            X-Barcode-Type: 128
            [binary PNG data]
        
        Response (502 Bad Gateway - API error):
            {
                "success": false,
                "error": "Rate limited. Please try again later.",
                "id_number": "EMP-12345"
            }
        """
        print("\n[EXAMPLE] Image API Response:")
        print("   GET /api/barcode/EMP-12345/image")
        print("   Response: [PNG binary data]")
        print("   Headers: Content-Type: image/png, Cache-Control: public, max-age=86400")
    
    def test_example_html_usage(self):
        """
        Example: Using barcode URL in HTML
        
        <!-- Direct embedding in HTML -->
        <img src="https://barcodeapi.org/api/128/EMP-12345?height=40" 
             alt="Barcode for EMP-12345"
             class="id-barcode-image"
             onerror="this.style.display='none';this.nextElementSibling.style.display='block';">
        <span class="barcode-fallback" style="display:none;">EMP-12345</span>
        
        <!-- Using the internal API proxy -->
        <img src="/api/barcode/EMP-12345/image" 
             alt="Barcode for EMP-12345">
        """
        url = get_barcode_url("EMP-12345")
        html_example = '<img src="' + url + '" alt="Barcode for EMP-12345" class="id-barcode-image">'
        
        print("\n[EXAMPLE] HTML Usage:")
        print(html_example)
        
        self.assertIn("barcodeapi.org", html_example)


def run_examples():
    """Run example barcode generation and display results."""
    print("\n" + "="*60)
    print("BARCODE SERVICE - EXAMPLE USAGE")
    print("="*60)
    
    # Example employee IDs
    employee_ids = [
        "EMP-12345",
        "FO-2024-001",
        "INT-001-A",
        "SPM-LEGAL-42"
    ]
    
    print("\n[INFO] Generated Barcode URLs:")
    print("-"*60)
    
    for emp_id in employee_ids:
        # CODE128 (default)
        url_128 = get_barcode_url(emp_id)
        print("\n" + emp_id + ":")
        print("  CODE128: " + url_128)
        
        # QR Code
        url_qr = get_barcode_url(emp_id, BarcodeType.QR)
        print("  QR Code: " + url_qr)
    
    print("\n" + "="*60)
    print("API ENDPOINTS")
    print("="*60)
    
    print("""
[ENDPOINT] GET /api/barcode/{id_number}
   Returns JSON with barcode URL for embedding in HTML.
   
   Query Parameters:
   - barcode_type: "128" (default), "qr", "39", "auto", "dm"
   - height: Pixel height for 1D barcodes (default: 40)
   
   Example: GET /api/barcode/EMP-12345?barcode_type=qr

[ENDPOINT] GET /api/barcode/{id_number}/image
   Returns the actual barcode PNG image.
   
   Use this when you need to proxy the request through your server
   or cache the barcode images.
   
   Example: <img src="/api/barcode/EMP-12345/image">
""")
    
    print("="*60)
    print("FRONTEND INTEGRATION")
    print("="*60)
    
    print("""
[CODE] Direct BarcodeAPI URL (gallery.js, dashboard.js):
   
   function getBarcodeUrl(idNumber, options) {
     options = options || {};
     var type = options.type || '128';
     var height = options.height || 40;
     var encodedId = encodeURIComponent(idNumber);
     var url = 'https://barcodeapi.org/api/' + type + '/' + encodedId;
     if (type !== 'qr' && type !== 'dm') {
       url += '?height=' + height;
     }
     return url;
   }

[HTML] Template with Fallback:
   
   <div class="id-barcode-container">
     <img src="[barcode-url]" 
          alt="Barcode" 
          class="id-barcode-image"
          onerror="this.style.display='none';this.nextElementSibling.style.display='block';">
     <span class="id-barcode-fallback" style="display:none;">
       [emp.id_number]
     </span>
   </div>
""")


if __name__ == "__main__":
    # Run examples first
    run_examples()
    
    # Then run unit tests
    print("\n" + "="*60)
    print("RUNNING UNIT TESTS")
    print("="*60 + "\n")
    
    unittest.main(verbosity=2)
