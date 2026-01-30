"""
Test Lark Bitable Connection for SPMA Table
Run this to verify your SPMA Lark table credentials are working
SPMA Table: tblajlHwJ6qFRlVa

SPMA Table Fields:
- employee_name (text)
- middle_initial (text)  
- last_name (text)
- suffix (text)
- id_number (text)
- division (text)
- department (text)
- field_clearance (text)
- branch_location (text)
- photo_preview (URL/Link)
- signature (URL/Link)
- email (text)
- personal_number (number)
"""
import os
import sys
import io
import json
import time
import urllib.request
import urllib.error
from datetime import datetime



# Fix encoding for Windows PowerShell
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================
# Configuration
# ============================================
LARK_APP_ID = os.getenv('LARK_APP_ID')
LARK_APP_SECRET = os.getenv('LARK_APP_SECRET')
LARK_BITABLE_ID = os.getenv('LARK_BITABLE_ID')

# SPMA-specific config (different Base)
LARK_APP_ID_SPMA = os.getenv('LARK_APP_ID_SPMA', os.getenv('LARK_APP_ID'))
LARK_APP_SECRET_SPMA = os.getenv('LARK_APP_SECRET_SPMA', os.getenv('LARK_APP_SECRET'))
LARK_BITABLE_ID_SPMA = os.getenv('LARK_BITABLE_ID_SPMA', os.getenv('LARK_BITABLE_ID'))
LARK_TABLE_ID_SPMA = os.getenv('LARK_TABLE_ID_SPMA', 'tblajlHwJ6qFRlVa')

# Lark API endpoints
LARK_TOKEN_URL = "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal"
LARK_BITABLE_BASE_URL = "https://open.larksuite.com/open-apis/bitable/v1/apps"


def _make_request(url: str, method: str = "GET", headers: dict = None, data: dict = None) -> dict:
    """Make HTTP request to Lark API using urllib."""
    if headers is None:
        headers = {}
    
    headers["Content-Type"] = "application/json; charset=utf-8"
    
    request_data = None
    if data:
        request_data = json.dumps(data).encode('utf-8')
    
    req = urllib.request.Request(url, data=request_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        print(f"HTTP error {e.code}: {error_body}")
        try:
            return json.loads(error_body)
        except:
            return {"code": e.code, "error": error_body}
    except Exception as e:
        print(f"Request error: {str(e)}")
        return {"code": -1, "error": str(e)}


def get_tenant_access_token() -> str:
    """Get Lark tenant access token."""
    if not LARK_APP_ID or not LARK_APP_SECRET:
        print("❌ Missing LARK_APP_ID or LARK_APP_SECRET")
        return None
    
    response = _make_request(LARK_TOKEN_URL, method="POST", data={
        "app_id": LARK_APP_ID,
        "app_secret": LARK_APP_SECRET
    })
    
    if response.get("code") != 0:
        print(f"❌ Token error: {response.get('msg')}")
        return None
    
    return response.get("tenant_access_token")


def get_tables(app_token: str, token: str) -> list:
    """List all tables in a Bitable app (debug helper)."""
    url = f"{LARK_BITABLE_BASE_URL}/{app_token}/tables"
    
    response = _make_request(url, method="GET", headers={"Authorization": f"Bearer {token}"})
    
    if response.get("code") != 0:
        print(f"❌ Failed to list tables: {response.get('msg')}")
        return []
    
    return response.get("data", {}).get("items", [])


def get_table_fields(app_token: str, table_id: str, token: str) -> list:
    """Get all fields/columns from a Bitable table."""
    url = f"{LARK_BITABLE_BASE_URL}/{app_token}/tables/{table_id}/fields"
    
    response = _make_request(url, method="GET", headers={"Authorization": f"Bearer {token}"})
    
    if response.get("code") != 0:
        print(f"❌ Failed to get fields: {response.get('msg')}")
        return []
    
    return response.get("data", {}).get("items", [])


def append_spma_record(
    token: str,
    employee_name: str,
    middle_initial: str = "",
    last_name: str = "",
    suffix: str = "",
    id_number: str = "",
    division: str = "",
    department: str = "",
    field_clearance: str = "",
    branch_location: str = "",
    photo_preview: str = None,
    signature: str = None,
    email: str = "",
    personal_number: str = ""
) -> bool:
    """Append a record to the SPMA Lark Bitable table."""
    
    # Parse personal_number to integer for Number field
    phone_number = 0
    if personal_number:
        phone_digits = ''.join(c for c in str(personal_number) if c.isdigit())
        phone_number = int(phone_digits) if phone_digits else 0
    
    # Build fields matching SPMA table structure
    fields = {
        "employee_name": employee_name,
        "middle_initial": middle_initial,
        "last_name": last_name,
        "suffix": suffix,
        "id_number": id_number,
        "division": division,
        "department": department,
        "field_clearance": field_clearance,
        "branch_location": branch_location,
        "email": email,
        "personal_number": phone_number,  # Number field
    }
    
    # Add URL fields if provided (Lark URL field format)
    if photo_preview:
        fields["photo_preview"] = {"link": photo_preview, "text": "Photo"}
    
    if signature:
        fields["signature"] = {"link": signature, "text": "Signature"}
    
    # Make the API request using SPMA Bitable ID
    url = f"{LARK_BITABLE_BASE_URL}/{LARK_BITABLE_ID_SPMA}/tables/{LARK_TABLE_ID_SPMA}/records"
    
    print(f"\n📡 POST URL: {url}")
    print(f"📦 Payload fields: {list(fields.keys())}")
    
    response = _make_request(
        url, 
        method="POST", 
        headers={"Authorization": f"Bearer {token}"},
        data={"fields": fields}
    )
    
    if response.get("code") != 0:
        print(f"❌ Lark API error (code {response.get('code')}): {response.get('msg')}")
        return False
    
    record_id = response.get("data", {}).get("record", {}).get("record_id")
    print(f"✅ Record created with ID: {record_id}")
    return True


def test_spma_connection():
    """Test SPMA Lark Bitable connection."""
    print("=" * 60)
    print("Testing SPMA Lark Bitable Connection")
    print(f"Table: {LARK_TABLE_ID_SPMA}")
    print("=" * 60)
    
    # Check SPMA-specific credentials
    print(f"\n1. Environment Variables (SPMA):")
    print(f"   LARK_APP_ID_SPMA: {LARK_APP_ID_SPMA[:10]}...{LARK_APP_ID_SPMA[-4:] if LARK_APP_ID_SPMA else 'MISSING'}")
    print(f"   LARK_APP_SECRET_SPMA: {'*' * 20 if LARK_APP_SECRET_SPMA else 'MISSING'}")
    print(f"   LARK_BITABLE_ID_SPMA: {LARK_BITABLE_ID_SPMA if LARK_BITABLE_ID_SPMA else 'MISSING'}")
    print(f"   LARK_TABLE_ID_SPMA: {LARK_TABLE_ID_SPMA if LARK_TABLE_ID_SPMA else 'MISSING'}")
    
    if not all([LARK_APP_ID_SPMA, LARK_APP_SECRET_SPMA, LARK_BITABLE_ID_SPMA, LARK_TABLE_ID_SPMA]):
        print("\n❌ ERROR: Missing required SPMA environment variables!")
        return False
    
    # Get SPMA-specific access token
    print(f"\n2. Testing SPMA Tenant Access Token...")
    response = _make_request(LARK_TOKEN_URL, method="POST", data={
        "app_id": LARK_APP_ID_SPMA,
        "app_secret": LARK_APP_SECRET_SPMA
    })
    
    if response.get("code") != 0:
        print(f"❌ SPMA Token error: {response.get('msg')}")
        return False
    
    token = response.get("tenant_access_token")
    if not token:
        return False
    print(f"   ✅ Token obtained: {token[:10]}...{token[-4:]}")
    
    # DEBUG: List tables in the SPMA app_token to verify table presence
    print(f"\n2.5. Listing tables for SPMA app_token (LARK_BITABLE_ID_SPMA): {LARK_BITABLE_ID_SPMA}")
    tables = get_tables(LARK_BITABLE_ID_SPMA, token)
    if tables:
        print(f"   ✅ Found {len(tables)} tables. Scanning for target table id...")
        found = False
        for t in tables:
            tid = t.get("table_id") or t.get("tableId") or t.get("id")
            name = t.get("name") or t.get("table_name") or t.get("tableName")
            print(f"      - {tid}  {name}")
            if tid == LARK_TABLE_ID_SPMA:
                found = True
                print(f"         ✅ FOUND TARGET TABLE!")
        if not found:
            print("\n⚠️  TARGET TABLE ID NOT FOUND under the provided LARK_BITABLE_ID_SPMA.")
            print("   This means the table may not exist or app lacks permissions.")

            print("\n   Or, your app may lack permission to read this Base.")
            print("   Solution: Share the Base with the app or update LARK_BITABLE_ID if using wrong Base.")
    else:
        print("   ⚠️ Could not retrieve tables. This may be a permissions issue.")
    
    # Get table fields to verify structure
    print(f"\n3. Fetching SPMA Table Fields...")
    fields = get_table_fields(LARK_BITABLE_ID_SPMA, LARK_TABLE_ID_SPMA, token)
    
    if fields:
        print(f"   ✅ Found {len(fields)} fields in SPMA table:")
        for field in fields:
            field_name = field.get("field_name", "Unknown")
            field_type = field.get("type", "Unknown")
            type_names = {
                1: "Text", 2: "Number", 3: "Single Select", 4: "Multi Select",
                5: "Date", 7: "Checkbox", 11: "Person", 13: "Phone",
                15: "URL/Link", 17: "Attachment", 18: "Single Link", 19: "Lookup",
                20: "Formula", 21: "Double Link", 22: "Created Time", 23: "Modified Time",
                1001: "Created By", 1002: "Modified By"
            }
            type_name = type_names.get(field_type, f"Type {field_type}")
            print(f"      - {field_name} ({type_name})")
    else:
        print(f"   ⚠️  Could not fetch table fields (permissions may be limited)")
    
    # Test appending a record
    print(f"\n4. Testing Record Append...")
    success = append_spma_record(
        token=token,
        employee_name="TEST SPMA USER - DELETE ME",
        middle_initial="T",
        last_name="User",
        suffix="",
        id_number="TEST-SPMA-001",
        division="Test Division",
        department="Test Department",
        field_clearance="Test Clearance",
        branch_location="Test Branch",
        photo_preview="https://example.com/test-photo.jpg",
        signature="https://example.com/test-signature.png",
        email="test.spma@example.com",
        personal_number="09123456789"
    )
    
    return success


def test_field_mapping():
    """Test that our field names match the Lark table exactly."""
    print("\n" + "=" * 60)
    print("Field Mapping Verification")
    print("=" * 60)
    
    # Expected SPMA fields based on user's description
    expected_fields = [
        ("employee_name", "Text"),
        ("middle_initial", "Text"),
        ("last_name", "Text"),
        ("suffix", "Text"),
        ("id_number", "Text"),
        ("division", "Text"),
        ("department", "Text"),
        ("field_clearance", "Text"),
        ("branch_location", "Text"),
        ("photo_preview", "URL/Link"),
        ("signature", "URL/Link"),
        ("email", "Text"),
        ("personal_number", "Number"),
    ]
    
    print("\nExpected SPMA Table Fields (based on your requirements):")
    for field_name, field_type in expected_fields:
        print(f"   ✓ {field_name} ({field_type})")
    
    print("\n⚠️  Note: Field names in Lark must match EXACTLY (case-sensitive)")
    print("   If you see 'Field name not found' errors, check the spelling in Lark.")
    
    return True


def print_permission_fix():
    """Print instructions to fix Lark table permissions."""
    print("\n" + "=" * 60)
    print("🔧 HOW TO FIX LARK TABLE PERMISSIONS")
    print("=" * 60)
    print("""
The SPMA table exists but your Lark app doesn't have access.

To fix this:

1. Open your Lark Base in browser:
   https://spmadridlaw.sg.larksuite.com/wiki/JSE6wQzR5iDll1kbyR1lYIZxg9e
   
2. Click on the SPMA table (tblajlHwJ6qFRlVa)

3. In the table view, click the "..." menu or Share button

4. Look for "Advanced Permissions" or "API Permissions"

5. Find your app (cli_a866185f1638502f) and grant it:
   - Read access
   - Write access (to create records)

ALTERNATIVE METHOD (via Lark Developer Console):

1. Go to: https://open.larksuite.com/app
2. Select your app (cli_a866185f1638502f)
3. Go to "Permissions & Scopes"
4. Ensure these scopes are enabled:
   - bitable:app
   - bitable:record:read
   - bitable:record:create
   
5. Go to "Version Management" and publish a new version

CRITICAL: After adding permissions, you may need to:
- Share the Base with the app (add as a collaborator)
- Grant the app access to both tables in the Base
""")


if __name__ == "__main__":
    try:
        # First verify field mapping
        test_field_mapping()
        
        # Then test connection
        success = test_spma_connection()
        
        print("\n" + "=" * 60)
        if success:
            print("✅ SPMA Lark Bitable connection test PASSED")
            print(f"   Table ID: {LARK_TABLE_ID_SPMA}")
            print("   Check your Lark Base for 'TEST SPMA USER - DELETE ME'")
        else:
            print("❌ SPMA Lark Bitable connection test FAILED")
            print_permission_fix()
        print("=" * 60)
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
