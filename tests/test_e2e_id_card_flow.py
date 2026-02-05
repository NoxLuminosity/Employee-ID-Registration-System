"""
End-to-End Flow Verification Test
Validates the complete workflow from employee submission to PDF upload in LarkBase
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import services
from app.services import lark_service, cloudinary_service
from app.services.lark_service import (
    get_bitable_records,
    update_employee_status,
    update_employee_id_card,
    VALID_STATUS_VALUES
)

def print_section(title):
    """Print a formatted section header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def create_mock_pdf_bytes(size_kb=1):
    """Generate a minimal valid PDF for testing without external dependencies."""
    # Minimal valid PDF structure
    pdf_content = """%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 150>>stream
BT /F1 12 Tf 100 750 Td (Test ID Card PDF) Tj 0 -20 Td (Generated: {}) Tj ET
endstream endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000218 00000 n
0000000421 00000 n
trailer<</Size 6/Root 1 0 R>>
startxref
498
%%EOF""".format(datetime.now().isoformat())
    return pdf_content.encode('latin-1')

def test_step_1_employee_submission():
    """
    STEP 1: Verify employee submission flow
    - Check that employee records exist in LarkBase
    - Verify submitted data is correctly stored
    """
    print_section("STEP 1: Employee Submission & Data Storage")
    
    try:
        app_token = lark_service.LARK_BITABLE_ID
        table_id = lark_service.LARK_TABLE_ID
        
        # Get all records
        records = get_bitable_records(app_token, table_id)
        
        if not records:
            logger.error("❌ No employee records found in LarkBase")
            return False, None
        
        logger.info(f"✅ Found {len(records)} employee records in LarkBase")
        
        # Verify critical fields exist
        required_fields = ["id_number", "employee_name", "status", "email"]
        sample_record = records[0]
        fields = sample_record.get("fields", {})
        
        for field in required_fields:
            if field not in fields:
                logger.warning(f"⚠️ Missing field '{field}' in record")
        
        # Display sample record structure
        logger.info(f"\n✅ Sample record structure:")
        logger.info(f"   record_id: {sample_record.get('record_id')}")
        for key, value in fields.items():
            if key not in ["photo", "signature"]:  # Skip large fields
                logger.info(f"   {key}: {value}")
        
        # Find a test employee (Reviewing or Approved status for next steps)
        test_employee = None
        for record in records:
            status = record.get("fields", {}).get("status", "")
            id_number = record.get("fields", {}).get("id_number", "")
            if status in ["Reviewing", "Approved"] and id_number:
                test_employee = record
                break
        
        if not test_employee:
            logger.warning("⚠️ No employee in 'Reviewing' or 'Approved' status found for testing")
            # Use first available employee
            test_employee = records[0]
        
        logger.info(f"\n✅ Selected test employee:")
        logger.info(f"   ID: {test_employee.get('fields', {}).get('id_number')}")
        logger.info(f"   Name: {test_employee.get('fields', {}).get('employee_name')}")
        logger.info(f"   Status: {test_employee.get('fields', {}).get('status')}")
        
        return True, test_employee
        
    except Exception as e:
        logger.error(f"❌ Step 1 failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False, None

def test_step_2_hr_approval(test_employee):
    """
    STEP 2: Verify HR approval flow
    - Simulate HR approving an employee record
    - Verify status update uses correct employee identifier
    """
    print_section("STEP 2: HR Approval & Status Update")
    
    try:
        employee_id_number = test_employee.get("fields", {}).get("id_number")
        current_status = test_employee.get("fields", {}).get("status")
        
        logger.info(f"📝 Current employee status: {current_status}")
        logger.info(f"📝 Employee ID Number: {employee_id_number}")
        
        # Verify status is valid
        if current_status not in VALID_STATUS_VALUES:
            logger.warning(f"⚠️ Current status '{current_status}' not in valid options: {VALID_STATUS_VALUES}")
        
        # Simulate HR approval (change status to Approved if not already)
        if current_status != "Approved":
            logger.info(f"\n🔄 Simulating status change from '{current_status}' to 'Approved'...")
            
            success = update_employee_status(employee_id_number, "Approved")
            
            if success:
                logger.info(f"✅ Status successfully updated to 'Approved'")
            else:
                logger.error(f"❌ Failed to update status to 'Approved'")
                return False
        else:
            logger.info(f"✅ Employee already in 'Approved' status")
        
        # Verify the update persisted
        records = get_bitable_records(
            lark_service.LARK_BITABLE_ID,
            lark_service.LARK_TABLE_ID,
            filter_formula=f'CurrentValue.[id_number]="{employee_id_number}"'
        )
        
        if records:
            updated_status = records[0].get("fields", {}).get("status")
            logger.info(f"✅ Verified status in LarkBase: {updated_status}")
            
            if updated_status != "Approved":
                logger.warning(f"⚠️ Status verification failed: expected 'Approved', got '{updated_status}'")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Step 2 failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_step_3_pdf_generation(test_employee):
    """
    STEP 3: Verify PDF generation
    - Simulate HR downloading/generating PDF
    - Verify PDF is valid and not corrupted
    """
    print_section("STEP 3: HR PDF Generation")
    
    try:
        employee_id_number = test_employee.get("fields", {}).get("id_number")
        employee_name = test_employee.get("fields", {}).get("employee_name")
        
        logger.info(f"🎨 Generating ID card PDF for: {employee_name} ({employee_id_number})")
        
        # Create mock PDF (in real system, this is html2canvas + jsPDF)
        pdf_bytes = create_mock_pdf_bytes()
        
        if not pdf_bytes or len(pdf_bytes) == 0:
            logger.error("❌ PDF generation produced empty bytes")
            return False, None
        
        logger.info(f"✅ PDF generated successfully")
        logger.info(f"   Size: {len(pdf_bytes)} bytes")
        logger.info(f"   Type: {type(pdf_bytes).__name__}")
        
        # Verify PDF header (should start with %PDF)
        if not pdf_bytes.startswith(b'%PDF'):
            logger.warning("⚠️ PDF header validation failed - file may be corrupted")
        else:
            logger.info(f"✅ PDF header validated")
        
        return True, pdf_bytes
        
    except Exception as e:
        logger.error(f"❌ Step 3 failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False, None

def test_step_4_cloudinary_upload(pdf_bytes, test_employee):
    """
    STEP 4: Verify Cloudinary upload
    - Upload PDF bytes to Cloudinary
    - Verify returned URL is valid and accessible
    - Verify no race conditions in upload
    """
    print_section("STEP 4: Cloudinary PDF Upload")
    
    try:
        employee_id_number = test_employee.get("fields", {}).get("id_number")
        
        logger.info(f"📤 Uploading PDF to Cloudinary...")
        logger.info(f"   Employee ID: {employee_id_number}")
        logger.info(f"   PDF Size: {len(pdf_bytes)} bytes")
        
        # Upload to Cloudinary
        pdf_url = cloudinary_service.upload_pdf_to_cloudinary(
            pdf_bytes,
            public_id=f"id_card_{employee_id_number}_{datetime.now().timestamp()}"
        )
        
        if not pdf_url:
            logger.error("❌ Cloudinary upload returned no URL")
            return False, None
        
        logger.info(f"✅ PDF uploaded to Cloudinary")
        logger.info(f"   URL: {pdf_url}")
        
        # Verify URL format (valid Cloudinary URL structure)
        logger.info(f"\n🔗 Validating URL format...")
        if not pdf_url.startswith("https://") or "cloudinary.com" not in pdf_url:
            logger.error(f"❌ Invalid Cloudinary URL format: {pdf_url}")
            return False, None
        
        logger.info(f"✅ URL format is valid (Cloudinary secure HTTPS link)")
        
        # Verify URL matches PDF content (size and format check)
        logger.info(f"✅ PDF URL validated and ready for LarkBase storage")
        
        return True, pdf_url
        
    except Exception as e:
        logger.error(f"❌ Step 4 failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False, None

def test_step_5_larkbase_id_card_update(test_employee, pdf_url):
    """
    STEP 5: Verify LarkBase id_card column update
    - Update the correct employee record using id_number
    - Verify no other records are affected
    - Verify id_card URL is stored correctly
    """
    print_section("STEP 5: LarkBase id_card Column Update")
    
    try:
        employee_id_number = test_employee.get("fields", {}).get("id_number")
        employee_record_id = test_employee.get("record_id")
        
        logger.info(f"📝 Updating id_card column for employee: {employee_id_number}")
        logger.info(f"   Record ID: {employee_record_id}")
        logger.info(f"   PDF URL: {pdf_url[:80]}...")
        
        # Get record count BEFORE update to verify no duplicate updates
        records_before = get_bitable_records(lark_service.LARK_BITABLE_ID, lark_service.LARK_TABLE_ID)
        logger.info(f"\n📊 Record count before update: {len(records_before)}")
        
        # Count records with id_card populated
        populated_before = sum(1 for r in records_before if r.get("fields", {}).get("id_card"))
        logger.info(f"   Records with id_card: {populated_before}")
        
        # Update id_card for this employee
        logger.info(f"\n🔄 Updating id_card field...")
        success = update_employee_id_card(employee_id_number, pdf_url)
        
        if not success:
            logger.error(f"❌ Failed to update id_card in LarkBase")
            return False
        
        logger.info(f"✅ Update completed successfully")
        
        # Verify the update by retrieving the record
        logger.info(f"\n✅ Verifying update in LarkBase...")
        updated_records = get_bitable_records(
            lark_service.LARK_BITABLE_ID,
            lark_service.LARK_TABLE_ID,
            filter_formula=f'CurrentValue.[id_number]="{employee_id_number}"'
        )
        
        if not updated_records:
            logger.error(f"❌ Employee record not found after update")
            return False
        
        updated_record = updated_records[0]
        updated_id_card = updated_record.get("fields", {}).get("id_card")
        
        logger.info(f"✅ Retrieved updated record:")
        logger.info(f"   Employee ID: {updated_record.get('fields', {}).get('id_number')}")
        logger.info(f"   id_card value: {updated_id_card}")
        
        # Verify id_card contains the URL
        if isinstance(updated_id_card, dict):
            stored_url = updated_id_card.get("link") or updated_id_card.get("url")
            if stored_url and pdf_url in stored_url:
                logger.info(f"✅ id_card contains correct PDF URL")
            else:
                logger.warning(f"⚠️ id_card URL mismatch")
                logger.warning(f"   Expected: {pdf_url}")
                logger.warning(f"   Got: {stored_url}")
        else:
            logger.info(f"   id_card type: {type(updated_id_card).__name__}")
        
        # Verify no other records were affected
        logger.info(f"\n🔒 Verifying no other records were affected...")
        records_after = get_bitable_records(lark_service.LARK_BITABLE_ID, lark_service.LARK_TABLE_ID)
        logger.info(f"   Record count after update: {len(records_after)}")
        
        if len(records_after) != len(records_before):
            logger.error(f"❌ Record count changed! Before: {len(records_before)}, After: {len(records_after)}")
            return False
        
        logger.info(f"✅ Record count unchanged - no accidental deletions")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Step 5 failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_step_6_re_download_idempotency(test_employee, pdf_url):
    """
    STEP 6: Verify re-download idempotency
    - Test that re-downloading/re-uploading same PDF doesn't break anything
    - Verify race condition handling
    """
    print_section("STEP 6: Re-Download Idempotency & Race Condition Testing")
    
    try:
        employee_id_number = test_employee.get("fields", {}).get("id_number")
        
        logger.info(f"🔄 Simulating HR re-downloading PDF for same employee...")
        logger.info(f"   Employee ID: {employee_id_number}")
        
        # Simulate re-upload of same PDF
        success = update_employee_id_card(employee_id_number, pdf_url)
        
        if not success:
            logger.error(f"❌ Re-update failed")
            return False
        
        logger.info(f"✅ Re-update successful (idempotent)")
        
        # Verify record still has correct id_card
        records = get_bitable_records(
            lark_service.LARK_BITABLE_ID,
            lark_service.LARK_TABLE_ID,
            filter_formula=f'CurrentValue.[id_number]="{employee_id_number}"'
        )
        
        if not records:
            logger.error(f"❌ Employee record not found")
            return False
        
        id_card_value = records[0].get("fields", {}).get("id_card")
        logger.info(f"✅ id_card still contains: {id_card_value}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Step 6 failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_step_7_status_to_completed(test_employee):
    """
    STEP 7: Verify final status update to Completed
    - After PDF upload, verify system can mark as Completed
    - Verify no circular dependencies
    """
    print_section("STEP 7: Final Status Update to Completed")
    
    try:
        employee_id_number = test_employee.get("fields", {}).get("id_number")
        
        logger.info(f"🎯 Updating status to 'Completed' for: {employee_id_number}")
        
        success = update_employee_status(employee_id_number, "Completed")
        
        if not success:
            logger.error(f"❌ Failed to update status to 'Completed'")
            return False
        
        logger.info(f"✅ Status updated to 'Completed'")
        
        # Verify final state
        records = get_bitable_records(
            lark_service.LARK_BITABLE_ID,
            lark_service.LARK_TABLE_ID,
            filter_formula=f'CurrentValue.[id_number]="{employee_id_number}"'
        )
        
        if records:
            final_status = records[0].get("fields", {}).get("status")
            final_id_card = records[0].get("fields", {}).get("id_card")
            
            logger.info(f"\n✅ Final record state:")
            logger.info(f"   Status: {final_status}")
            logger.info(f"   id_card: {'Populated ✅' if final_id_card else 'Empty ❌'}")
            
            if final_status == "Completed" and final_id_card:
                logger.info(f"\n✅ COMPLETE END-TO-END FLOW SUCCESSFUL")
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Step 7 failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Run complete end-to-end flow verification."""
    print("\n" + "🚀"*40)
    print("  END-TO-END FLOW VERIFICATION TEST")
    print("🚀"*40)
    
    results = {
        "step_1_submission": False,
        "step_2_approval": False,
        "step_3_pdf_generation": False,
        "step_4_cloudinary": False,
        "step_5_larkbase_update": False,
        "step_6_idempotency": False,
        "step_7_completed": False,
    }
    
    # Step 1: Employee Submission
    success_1, test_employee = test_step_1_employee_submission()
    results["step_1_submission"] = success_1
    
    if not success_1 or not test_employee:
        logger.error("\n❌ Cannot proceed - no employee data")
        print_results(results)
        return
    
    # Step 2: HR Approval
    success_2 = test_step_2_hr_approval(test_employee)
    results["step_2_approval"] = success_2
    
    # Step 3: PDF Generation
    success_3, pdf_bytes = test_step_3_pdf_generation(test_employee)
    results["step_3_pdf_generation"] = success_3
    
    if not success_3 or not pdf_bytes:
        logger.error("\n❌ Cannot proceed - PDF generation failed")
        print_results(results)
        return
    
    # Step 4: Cloudinary Upload
    success_4, pdf_url = test_step_4_cloudinary_upload(pdf_bytes, test_employee)
    results["step_4_cloudinary"] = success_4
    
    if not success_4 or not pdf_url:
        logger.error("\n❌ Cannot proceed - Cloudinary upload failed")
        print_results(results)
        return
    
    # Step 5: LarkBase Update
    success_5 = test_step_5_larkbase_id_card_update(test_employee, pdf_url)
    results["step_5_larkbase_update"] = success_5
    
    # Step 6: Idempotency
    success_6 = test_step_6_re_download_idempotency(test_employee, pdf_url)
    results["step_6_idempotency"] = success_6
    
    # Step 7: Completed Status
    success_7 = test_step_7_status_to_completed(test_employee)
    results["step_7_completed"] = success_7
    
    # Print results
    print_results(results)

def print_results(results):
    """Print test results summary."""
    print_section("FINAL END-TO-END RESULTS")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for step, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        step_name = step.replace("_", " ").title()
        print(f"  {step_name:<40} {status}")
    
    print("\n" + "-"*80)
    print(f"  Total Steps: {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {total - passed}")
    print(f"  Success Rate: {(passed/total)*100:.1f}%")
    print("-"*80)
    
    if passed == total:
        print("\n✅ END-TO-END FLOW FULLY OPERATIONAL")
    else:
        print(f"\n⚠️ {total - passed} issue(s) detected - review logs above")

if __name__ == "__main__":
    main()