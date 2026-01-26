"""
Diagnose Lark Bitable Field Names
This script shows you what fields actually exist in your Lark Base table
"""
import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))
from app.services.lark_service import get_tenant_access_token, _make_request

LARK_BITABLE_BASE_URL = "https://open.larksuite.com/open-apis/bitable/v1/apps"

def get_table_fields():
    """Get all fields in the Bitable table"""
    app_token = os.getenv('LARK_BITABLE_ID')
    table_id = os.getenv('LARK_TABLE_ID')
    
    if not app_token or not table_id:
        print("❌ Missing LARK_BITABLE_ID or LARK_TABLE_ID in .env")
        return
    
    token = get_tenant_access_token()
    if not token:
        print("❌ Failed to get access token")
        return
    
    print("=" * 70)
    print("LARK BITABLE TABLE FIELDS DIAGNOSIS")
    print("=" * 70)
    print(f"\nBitable ID: {app_token}")
    print(f"Table ID: {table_id}")
    
    # Get table metadata with fields
    url = f"{LARK_BITABLE_BASE_URL}/{app_token}/tables/{table_id}/fields"
    
    response = _make_request(url, method="GET", 
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print(f"\nAPI Response Code: {response.get('code')}")
    
    if response.get("code") != 0:
        print(f"❌ Error: {response.get('msg')}")
        print(f"\nFull response: {json.dumps(response, indent=2)}")
        return
    
    fields = response.get("data", {}).get("items", [])
    
    if not fields:
        print("❌ No fields found in table!")
        return
    
    print(f"\n✅ Found {len(fields)} fields in your Lark Base table:\n")
    
    field_mapping = {}
    for field in fields:
        field_name = field.get("field_name")
        field_type = field.get("type")
        field_id = field.get("field_id")
        
        field_mapping[field_name] = field_type
        print(f"  • {field_name:<30} (Type: {field_type}, ID: {field_id})")
    
    print("\n" + "=" * 70)
    print("FIELD NAME MAPPING FOR CODE")
    print("=" * 70)
    print("\nUse these EXACT field names in the code:\n")
    
    for field_name in sorted(field_mapping.keys()):
        print(f'    "{field_name}": value_here,')
    
    print("\n" + "=" * 70)
    print("COMMON FIELD ISSUES TO CHECK:")
    print("=" * 70)
    
    # Check for common issues
    issues = []
    
    # Check if fields with spaces exist
    problematic_fields = [
        ("personal number", "personal_number"),
        ("date last modified", "submitted_date"),
        ("photo_preview", "photo_preview"),
        ("new_photo", "new_photo"),
        ("signature_preview", "signature"),
    ]
    
    for expected, alternate in problematic_fields:
        if expected not in field_mapping:
            if alternate in field_mapping:
                issues.append(f"⚠️  Found '{alternate}' but code expects '{expected}'")
            else:
                issues.append(f"❌ Missing field: '{expected}' (also checked for '{alternate}')")
        else:
            issues.append(f"✅ Found: '{expected}'")
    
    print()
    for issue in issues:
        print(f"  {issue}")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    try:
        get_table_fields()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
