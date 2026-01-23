"""
Lark (Feishu) Bitable Integration Service
Handles appending employee submissions to Lark Bitable (spreadsheet-like database).

Authentication: Uses LARK_APP_ID and LARK_APP_SECRET environment variables.
This is production-safe for Vercel serverless functions.

Note: Image uploads are handled by Cloudinary (see cloudinary_service.py).
"""
import os
import json
import logging
import time
from typing import Optional, Dict, Any, List
import urllib.request
import urllib.error

# Configure logging
logger = logging.getLogger(__name__)

# Lark Configuration - use provided credentials as defaults
LARK_APP_ID = os.environ.get('LARK_APP_ID', 'cli_a866185f1638502f')
LARK_APP_SECRET = os.environ.get('LARK_APP_SECRET', 'zaduPnvOLTxcb7W8XHYIaggtYgzOUOI6')
LARK_BITABLE_ID = os.environ.get('LARK_BITABLE_ID', 'WxvXbLMt8aoPzzszjR3lIXhlgNc')
LARK_TABLE_ID = os.environ.get('LARK_TABLE_ID', 'tbl3Jm6881dJMF6E')

# Lark API endpoints
LARK_TOKEN_URL = "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal"
LARK_BITABLE_BASE_URL = "https://open.larksuite.com/open-apis/bitable/v1/apps"
LARK_BITABLE_RECORD_URL = f"{LARK_BITABLE_BASE_URL}/{{app_token}}/tables/{{table_id}}/records"

# Cache for access token
_cached_token: Optional[str] = None
_token_expiry: float = 0


def _make_request(url: str, method: str = "GET", headers: Dict = None, data: Dict = None) -> Dict[str, Any]:
    """Make HTTP request to Lark API using urllib (no external dependencies)."""
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
        logger.error(f"Lark API HTTP error {e.code}: {error_body}")
        try:
            return json.loads(error_body)
        except:
            return {"code": e.code, "error": error_body}
    except Exception as e:
        logger.error(f"Lark API request error: {str(e)}")
        return {"code": -1, "error": str(e)}


def get_tenant_access_token() -> Optional[str]:
    """Get Lark tenant access token. Cached and auto-refreshed."""
    global _cached_token, _token_expiry
    
    if _cached_token and time.time() < (_token_expiry - 300):
        return _cached_token
    
    # Use configured credentials
    app_id = LARK_APP_ID
    app_secret = LARK_APP_SECRET
    
    if not app_id:
        logger.error("LARK_APP_ID not configured")
        return None
    if not app_secret:
        logger.error("LARK_APP_SECRET not configured")
        return None
    
    try:
        response = _make_request(LARK_TOKEN_URL, method="POST", data={
            "app_id": app_id,
            "app_secret": app_secret
        })
        
        if response.get("code") != 0:
            logger.error(f"Lark token error: {response.get('msg')}")
            return None
        
        _cached_token = response.get("tenant_access_token")
        _token_expiry = time.time() + response.get("expire", 7200)
        
        logger.info("Lark tenant access token obtained successfully")
        return _cached_token
        
    except Exception as e:
        logger.error(f"Failed to get Lark access token: {str(e)}")
        return None


def append_record_to_bitable(app_token: str, table_id: str, fields: Dict[str, Any]) -> bool:
    """Append a record to Lark Bitable table."""
    token = get_tenant_access_token()
    if not token:
        return False
    
    try:
        url = LARK_BITABLE_RECORD_URL.format(app_token=app_token, table_id=table_id)
        
        response = _make_request(url, method="POST", 
            headers={"Authorization": f"Bearer {token}"},
            data={"fields": fields}
        )
        
        if response.get("code") != 0:
            logger.error(f"Lark Bitable error: {response.get('msg')}")
            return False
        
        record_id = response.get("data", {}).get("record", {}).get("record_id")
        logger.info(f"Successfully appended to Lark Bitable (record_id: {record_id})")
        return True
        
    except Exception as e:
        logger.error(f"Failed to append to Lark Bitable: {str(e)}")
        return False


def get_bitable_records(app_token: str = None, table_id: str = None, filter_formula: str = None) -> list:
    """
    Get records from Lark Bitable table.
    
    Args:
        app_token: Bitable app token (uses default if not provided)
        table_id: Table ID (uses default if not provided)
        filter_formula: Optional filter formula for querying specific records
    
    Returns:
        List of records or empty list on failure
    """
    token = get_tenant_access_token()
    if not token:
        return []
    
    # Use defaults if not provided
    app_token = app_token or LARK_BITABLE_ID
    table_id = table_id or LARK_TABLE_ID
    
    if not app_token or not table_id:
        logger.warning("Bitable credentials not configured")
        return []
    
    try:
        url = f"{LARK_BITABLE_BASE_URL}/{app_token}/tables/{table_id}/records"
        
        # Add filter if provided
        if filter_formula:
            from urllib.parse import quote
            url += f"?filter={quote(filter_formula)}"
        
        response = _make_request(url, method="GET", 
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.get("code") != 0:
            logger.error(f"Lark Bitable read error: {response.get('msg')}")
            return []
        
        items = response.get("data", {}).get("items", [])
        logger.info(f"Retrieved {len(items)} records from Bitable")
        return items
        
    except Exception as e:
        logger.error(f"Failed to read from Lark Bitable: {str(e)}")
        return []


def check_user_in_bitable(email: str = None, employee_no: str = None) -> Dict[str, Any]:
    """
    Check if a user exists in the Lark Bitable employee records.
    Used for validating HR Portal access.
    
    Args:
        email: User's email address
        employee_no: User's employee number
    
    Returns:
        Dict with 'found' boolean and 'record' data if found
    """
    if not email and not employee_no:
        return {"found": False, "error": "No email or employee_no provided"}
    
    # Get all records and search (Bitable filter syntax can be limited)
    records = get_bitable_records()
    
    for record in records:
        fields = record.get("fields", {})
        record_email = fields.get("email", "").lower().strip()
        record_emp_no = fields.get("id_number", "").strip()
        
        # Match by email or employee number
        if email and record_email == email.lower().strip():
            logger.info(f"User found in Bitable by email: {email}")
            return {"found": True, "record": fields}
        
        if employee_no and record_emp_no == employee_no.strip():
            logger.info(f"User found in Bitable by employee_no: {employee_no}")
            return {"found": True, "record": fields}
    
    logger.info(f"User not found in Bitable (email={email}, employee_no={employee_no})")
    return {"found": False}


def append_employee_submission(
    employee_name: str,
    id_nickname: str,
    id_number: str,
    position: str,
    department: str,
    email: str,
    personal_number: str,
    photo_path: str = None,
    signature_path: str = None,
    status: str = 'Reviewing',
    date_last_modified: str = None,
    photo_url: Optional[str] = None,
    signature_url: Optional[str] = None,
    ai_headshot_url: Optional[str] = None,
    render_url: str = '',
    first_name: Optional[str] = None,
    middle_initial: Optional[str] = None,
    last_name: Optional[str] = None
) -> bool:
    """Append employee submission to Lark Bitable."""
    # Use configured Bitable credentials (fall back to env vars for backwards compatibility)
    app_token = LARK_BITABLE_ID or os.environ.get('LARK_BITABLE_APP_TOKEN')
    table_id = LARK_TABLE_ID or os.environ.get('LARK_BITABLE_TABLE_ID')
    
    if not app_token:
        logger.warning("LARK_BITABLE_ID not configured. Skipping Lark append.")
        return False
    if not table_id:
        logger.warning("LARK_TABLE_ID not configured. Skipping Lark append.")
        return False
    
    from datetime import datetime
    if date_last_modified is None:
        date_last_modified = datetime.now().isoformat()
    
    # FIX for AttachFieldConvFail:
    # Bitable attachment-type fields CANNOT receive empty strings ("").
    # Sending "" to an attachment field causes Lark to attempt conversion, which fails.
    # Solution: Only include text-type fields. Omit attachment fields entirely.
    #
    # Known attachment-type fields in this Bitable (must be OMITTED if empty):
    # - photo_preview (attachment)
    # - new_photo (attachment)  
    # - signature_preview (attachment)
    # - id_generated (attachment or checkbox)
    #
    # These fields should be managed through Lark Bitable UI, not via API.
    
    # Field names must match your Lark Bitable columns EXACTLY
    # Only include TEXT-type fields that accept string values
    fields = {
        "employee_name": employee_name,
        "first_name": first_name or "",
        "middle_initial": middle_initial or "",
        "last_name": last_name or "",
        "id_nickname": id_nickname or "",
        "id_number": id_number,
        "position": position,
        "department": department or "",  # Deprecated but kept for compatibility
        "email": email,
        "personal number": personal_number,
        # NOTE: photo_preview OMITTED - it's an attachment field, not text
        "photo_url": photo_url or "",  # Text field containing Cloudinary URL
        "ai_headshot_url": ai_headshot_url or "",  # Text field containing AI headshot URL
        # NOTE: new_photo OMITTED - it's an attachment field, not text
        # NOTE: signature_preview OMITTED - it's an attachment field, not text
        "signature": signature_url or "",  # Text field containing signature URL
        "status": status,
        "date last modified": date_last_modified,
        # NOTE: id_generated OMITTED - may be attachment or checkbox field
        "render_url": render_url or ""
    }
    
    logger.debug(f"Bitable payload fields: {list(fields.keys())}")
    
    return append_record_to_bitable(app_token, table_id, fields)
