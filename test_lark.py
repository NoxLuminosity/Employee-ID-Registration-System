"""
Test Lark Bitable Connection
Run this to verify your Lark credentials are working
"""
import os
import sys
import io

# Fix encoding for Windows PowerShell
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Lark service
sys.path.insert(0, os.path.dirname(__file__))
from app.services.lark_service import get_tenant_access_token, append_employee_submission

def test_lark_connection():
    """Test Lark Bitable connection"""
    print("=" * 60)
    print("Testing Lark Bitable Connection")
    print("=" * 60)
    
    # Check credentials
    app_id = os.getenv('LARK_APP_ID')
    app_secret = os.getenv('LARK_APP_SECRET')
    bitable_id = os.getenv('LARK_BITABLE_ID')
    table_id = os.getenv('LARK_TABLE_ID')
    
    print(f"\n1. Environment Variables:")
    print(f"   LARK_APP_ID: {app_id[:10]}...{app_id[-4:] if app_id else 'MISSING'}")
    print(f"   LARK_APP_SECRET: {'*' * 20 if app_secret else 'MISSING'}")
    print(f"   LARK_BITABLE_ID: {bitable_id if bitable_id else 'MISSING'}")
    print(f"   LARK_TABLE_ID: {table_id if table_id else 'MISSING'}")
    
    if not all([app_id, app_secret, bitable_id, table_id]):
        print("\n❌ ERROR: Missing required environment variables!")
        print("   Please check your .env file")
        return False
    
    # Test getting access token
    print(f"\n2. Testing Tenant Access Token...")
    token = get_tenant_access_token()
    if token:
        print(f"   ✅ Token obtained: {token[:10]}...{token[-4:]}")
    else:
        print(f"   ❌ Failed to get access token")
        print(f"   Check your LARK_APP_ID and LARK_APP_SECRET")
        return False
    
    # Test appending a simple record using append_employee_submission
    print(f"\n3. Testing Bitable Record Append...")
    success = append_employee_submission(
        employee_name="TEST USER - DELETE ME",
        id_nickname="Test",
        id_number="TEST-001",
        position="Test Position",
        department="Test Dept",
        email="test@example.com",
        personal_number="1234567890",
        status="Reviewing",
        date_last_modified="2026/01/30",  # Simple date format
        first_name="Test",
        middle_initial="T",
        last_name="User"
    )
    
    if success:
        print(f"   ✅ Successfully appended test record!")
        print(f"   Check your Lark Base for 'TEST USER - DELETE ME'")
        return True
    else:
        print(f"   ❌ Failed to append record")
        print(f"   Check the error logs above")
        return False

if __name__ == "__main__":
    try:
        success = test_lark_connection()
        print("\n" + "=" * 60)
        if success:
            print("✅ Lark Bitable connection test PASSED")
            print("Your credentials are working correctly!")
        else:
            print("❌ Lark Bitable connection test FAILED")
            print("Please check the errors above")
        print("=" * 60)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
