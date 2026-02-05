"""
Test script to verify id_card column connection and PDF upload functionality.

This script tests:
1. LarkBase connection and authentication
2. id_card field existence and accessibility
3. PDF upload to Cloudinary
4. LarkBase id_card field update with attachment format
5. End-to-end PDF upload workflow

Usage:
    python test_id_card_upload.py

Environment variables required:
    - LARK_APP_ID
    - LARK_APP_SECRET
    - LARK_BITABLE_ID
    - LARK_TABLE_ID
    - CLOUDINARY_CLOUD_NAME
    - CLOUDINARY_API_KEY
    - CLOUDINARY_API_SECRET
"""

import os
import sys
import json
import logging
from datetime import datetime

# Load environment variables FIRST before importing services
from dotenv import load_dotenv
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import services (after loading env vars)
from app.services import lark_service, cloudinary_service

def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def test_lark_connection():
    """Test 1: Verify LarkBase connection."""
    print_section("TEST 1: LarkBase Connection")
    
    try:
        token = lark_service.get_tenant_access_token()
        if token:
            logger.info(f"✅ Successfully obtained access token: {token[:20]}...")
            return True
        else:
            logger.error("❌ Failed to obtain access token")
            return False
    except Exception as e:
        logger.error(f"❌ Exception during authentication: {str(e)}")
        return False

def test_lark_credentials():
    """Test 2: Check if all required LarkBase credentials are configured."""
    print_section("TEST 2: LarkBase Credentials")
    
    required_vars = {
        'LARK_APP_ID': lark_service.LARK_APP_ID,
        'LARK_APP_SECRET': lark_service.LARK_APP_SECRET,
        'LARK_BITABLE_ID': lark_service.LARK_BITABLE_ID,
        'LARK_TABLE_ID': lark_service.LARK_TABLE_ID
    }
    
    all_configured = True
    for var_name, var_value in required_vars.items():
        if var_value:
            logger.info(f"✅ {var_name}: {var_value[:10]}...{var_value[-4:]}")
        else:
            logger.error(f"❌ {var_name}: NOT CONFIGURED")
            all_configured = False
    
    return all_configured

def test_cloudinary_connection():
    """Test 3: Verify Cloudinary connection."""
    print_section("TEST 3: Cloudinary Connection")
    
    try:
        configured = cloudinary_service.configure_cloudinary()
        if configured:
            logger.info("✅ Cloudinary configured successfully")
            
            # Check for required credentials
            cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
            api_key = os.environ.get('CLOUDINARY_API_KEY')
            api_secret = os.environ.get('CLOUDINARY_API_SECRET')
            
            if cloud_name and api_key and api_secret:
                logger.info(f"✅ Cloud Name: {cloud_name}")
                logger.info(f"✅ API Key: {api_key[:10]}...")
                return True
            else:
                logger.error("❌ Cloudinary credentials incomplete")
                return False
        else:
            logger.error("❌ Failed to configure Cloudinary")
            return False
    except Exception as e:
        logger.error(f"❌ Exception during Cloudinary setup: {str(e)}")
        return False

def test_get_bitable_records():
    """Test 4: Retrieve records from LarkBase table."""
    print_section("TEST 4: Retrieve LarkBase Records")
    
    try:
        app_token = lark_service.LARK_BITABLE_ID
        table_id = lark_service.LARK_TABLE_ID
        
        if not app_token or not table_id:
            logger.error("❌ Missing app_token or table_id")
            return False
        
        # Get records from LarkBase
        records = lark_service.get_bitable_records(app_token, table_id)
        
        if records:
            logger.info(f"✅ Successfully retrieved {len(records)} records")
            
            # Check if any record has id_number field
            for i, record in enumerate(records[:3]):
                fields = record.get("fields", {})
                id_number = fields.get("id_number", "N/A")
                employee_name = fields.get("employee_name", "N/A")
                status = fields.get("status", "N/A")
                id_card = fields.get("id_card", None)
                
                logger.info(f"  Record {i+1}:")
                logger.info(f"    ID Number: {id_number}")
                logger.info(f"    Name: {employee_name}")
                logger.info(f"    Status: {status}")
                logger.info(f"    id_card: {type(id_card).__name__} - {id_card if id_card else 'Empty'}")
            
            return True
        else:
            logger.warning("⚠️ No records found or failed to retrieve")
            return False
            
    except Exception as e:
        logger.error(f"❌ Exception retrieving records: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_id_card_field_structure():
    """Test 5: Check id_card field structure in existing records."""
    print_section("TEST 5: id_card Field Structure Analysis")
    
    try:
        app_token = lark_service.LARK_BITABLE_ID
        table_id = lark_service.LARK_TABLE_ID
        
        # Find records with id_card populated
        records = lark_service.get_bitable_records(app_token, table_id)
        
        if not records:
            logger.warning("⚠️ No records found")
            return False
        
        populated_count = 0
        empty_count = 0
        
        for record in records:
            fields = record.get("fields", {})
            id_card = fields.get("id_card")
            
            if id_card:
                populated_count += 1
                if populated_count <= 3:  # Show first 3 examples
                    logger.info(f"✅ Record with id_card:")
                    logger.info(f"   ID: {fields.get('id_number', 'N/A')}")
                    logger.info(f"   id_card type: {type(id_card).__name__}")
                    logger.info(f"   id_card value: {json.dumps(id_card)[:200]}")
            else:
                empty_count += 1
        
        logger.info(f"\n📊 Summary:")
        logger.info(f"   Total records: {len(records)}")
        logger.info(f"   With id_card: {populated_count}")
        logger.info(f"   Without id_card: {empty_count}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Exception analyzing id_card field: {str(e)}")
        return False

def test_pdf_generation_mock():
    """Test 6: Generate a mock PDF for testing."""
    print_section("TEST 6: Mock PDF Generation")
    
    try:
        # Create a minimal valid PDF (smallest possible PDF)
        # PDF header and minimal structure
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000317 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
410
%%EOF
"""
        logger.info(f"✅ Generated mock PDF: {len(pdf_content)} bytes")
        return pdf_content
        
    except Exception as e:
        logger.error(f"❌ Failed to generate mock PDF: {str(e)}")
        return None

def test_cloudinary_pdf_upload(pdf_bytes):
    """Test 7: Upload PDF to Cloudinary."""
    print_section("TEST 7: Cloudinary PDF Upload")
    
    if not pdf_bytes:
        logger.error("❌ No PDF bytes provided")
        return None
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        public_id = f"TEST_ID_CARD_{timestamp}"
        
        logger.info(f"📤 Uploading test PDF to Cloudinary...")
        pdf_url = cloudinary_service.upload_pdf_to_cloudinary(
            pdf_bytes, 
            public_id, 
            folder="test_id_cards"
        )
        
        if pdf_url:
            logger.info(f"✅ PDF uploaded successfully")
            logger.info(f"   URL: {pdf_url}")
            return pdf_url
        else:
            logger.error("❌ PDF upload failed (no URL returned)")
            return None
            
    except Exception as e:
        logger.error(f"❌ Exception during PDF upload: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def test_find_test_employee():
    """Test 8: Find a test employee to update."""
    print_section("TEST 8: Find Test Employee")
    
    try:
        app_token = lark_service.LARK_BITABLE_ID
        table_id = lark_service.LARK_TABLE_ID
        
        # Get records with Approved or Completed status
        records = lark_service.get_bitable_records(app_token, table_id)
        
        if not records:
            logger.error("❌ No records found")
            return None
        
        # Look for a suitable test record (Approved or Completed)
        for record in records:
            fields = record.get("fields", {})
            status = fields.get("status", "")
            id_number = fields.get("id_number", "")
            
            if status in ["Approved", "Completed"] and id_number:
                logger.info(f"✅ Found test employee:")
                logger.info(f"   ID Number: {id_number}")
                logger.info(f"   Name: {fields.get('employee_name', 'N/A')}")
                logger.info(f"   Status: {status}")
                logger.info(f"   Current id_card: {fields.get('id_card', 'Empty')}")
                return id_number
        
        logger.warning("⚠️ No suitable test employee found (need Approved/Completed status)")
        return None
        
    except Exception as e:
        logger.error(f"❌ Exception finding test employee: {str(e)}")
        return None

def test_update_id_card_field(id_number, pdf_url):
    """Test 9: Update id_card field with test PDF URL."""
    print_section("TEST 9: Update id_card Field")
    
    if not id_number or not pdf_url:
        logger.error("❌ Missing id_number or pdf_url")
        return False
    
    try:
        logger.info(f"📝 Updating id_card field for employee: {id_number}")
        logger.info(f"   PDF URL: {pdf_url}")
        
        success = lark_service.update_employee_id_card(
            id_number=id_number,
            pdf_url=pdf_url,
            source="Test Script"
        )
        
        if success:
            logger.info("✅ id_card field updated successfully")
            
            # Verify the update
            logger.info("\n🔍 Verifying update...")
            app_token = lark_service.LARK_BITABLE_ID
            table_id = lark_service.LARK_TABLE_ID
            filter_formula = f'CurrentValue.[id_number]="{id_number}"'
            records = lark_service.get_bitable_records(app_token, table_id, filter_formula=filter_formula)
            
            if records:
                fields = records[0].get("fields", {})
                id_card = fields.get("id_card")
                logger.info(f"✅ Verified id_card value: {json.dumps(id_card)}")
                return True
            else:
                logger.warning("⚠️ Could not verify update (record not found)")
                return False
        else:
            logger.error("❌ id_card field update failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Exception updating id_card field: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def run_all_tests():
    """Run all tests in sequence."""
    print("\n" + "🚀" * 40)
    print("  ID CARD UPLOAD SYSTEM TEST SUITE")
    print("🚀" * 40)
    
    results = {}
    
    # Test 1: LarkBase Connection
    results['lark_connection'] = test_lark_connection()
    
    # Test 2: LarkBase Credentials
    results['lark_credentials'] = test_lark_credentials()
    
    # Test 3: Cloudinary Connection
    results['cloudinary_connection'] = test_cloudinary_connection()
    
    # Test 4: Get Records
    results['get_records'] = test_get_bitable_records()
    
    # Test 5: id_card Field Structure
    results['id_card_structure'] = test_id_card_field_structure()
    
    # Test 6: Generate Mock PDF
    pdf_bytes = test_pdf_generation_mock()
    results['pdf_generation'] = pdf_bytes is not None
    
    # Test 7: Upload PDF to Cloudinary
    pdf_url = None
    if pdf_bytes:
        pdf_url = test_cloudinary_pdf_upload(pdf_bytes)
        results['cloudinary_upload'] = pdf_url is not None
    else:
        results['cloudinary_upload'] = False
    
    # Test 8: Find Test Employee
    test_id_number = test_find_test_employee()
    results['find_employee'] = test_id_number is not None
    
    # Test 9: Update id_card Field
    if test_id_number and pdf_url:
        results['update_id_card'] = test_update_id_card_field(test_id_number, pdf_url)
    else:
        results['update_id_card'] = False
        logger.warning("⚠️ Skipping id_card update test (missing prerequisites)")
    
    # Print final results
    print_section("FINAL RESULTS")
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    failed_tests = total_tests - passed_tests
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name:25s} : {status}")
    
    print("\n" + "-" * 80)
    print(f"  Total Tests: {total_tests}")
    print(f"  Passed: {passed_tests}")
    print(f"  Failed: {failed_tests}")
    print(f"  Success Rate: {(passed_tests/total_tests*100):.1f}%")
    print("-" * 80)
    
    if failed_tests == 0:
        print("\n🎉 All tests passed! The id_card upload system is working correctly.")
        return True
    else:
        print(f"\n⚠️ {failed_tests} test(s) failed. Please review the errors above.")
        return False

if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Test suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
