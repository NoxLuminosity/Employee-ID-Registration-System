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
from typing import Optional, Dict, Any
import urllib.request
import urllib.error

# Configure logging
logger = logging.getLogger(__name__)

# Lark API endpoints
LARK_TOKEN_URL = "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal"
LARK_BITABLE_RECORD_URL = "https://open.larksuite.com/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"

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
        raise


def get_tenant_access_token() -> Optional[str]:
    """Get Lark tenant access token. Cached and auto-refreshed."""
    global _cached_token, _token_expiry
    
    if _cached_token and time.time() < (_token_expiry - 300):
        return _cached_token
    
    app_id = os.environ.get('LARK_APP_ID')
    app_secret = os.environ.get('LARK_APP_SECRET')
    
    if not app_id:
        logger.error("LARK_APP_ID environment variable not set")
        return None
    if not app_secret:
        logger.error("LARK_APP_SECRET environment variable not set")
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
    render_url: str = ''
) -> bool:
    """Append employee submission to Lark Bitable."""
    app_token = os.environ.get('LARK_BITABLE_APP_TOKEN')
    table_id = os.environ.get('LARK_BITABLE_TABLE_ID')
    
    if not app_token:
        logger.warning("LARK_BITABLE_APP_TOKEN not set. Skipping Lark append.")
        return False
    if not table_id:
        logger.warning("LARK_BITABLE_TABLE_ID not set. Skipping Lark append.")
        return False
    
    from datetime import datetime
    if date_last_modified is None:
        date_last_modified = datetime.now().isoformat()
    
    # Field names must match your Lark Bitable columns EXACTLY
    fields = {
        "employee_name": employee_name,
        "id_nickname": id_nickname or "",
        "id_number": id_number,
        "position": position,
        "department": department,
        "email": email,
        "personal number": personal_number,
        "photo_preview": "",  # Empty - not backend-managed
        "photo_url": photo_url or "",
        "ai_headshot_url": ai_headshot_url or "",  # AI-generated professional headshot
        "new_photo": "",  # Empty - not backend-managed
        "signature_preview": "",  # Empty - not backend-managed
        "signature": signature_url or "",
        "status": status,
        "date last modified": date_last_modified,
        "id_generated": "",  # Empty - not backend-managed
        "render_url": render_url or ""
    }
    
    return append_record_to_bitable(app_token, table_id, fields)
