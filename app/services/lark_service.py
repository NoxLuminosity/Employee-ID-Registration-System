"""
Lark (Feishu) Bitable Integration Service
Handles appending employee submissions to Lark Bitable (spreadsheet-like database).

Authentication: Uses LARK_APP_ID and LARK_APP_SECRET environment variables.
This is production-safe for Vercel serverless functions.

Dual Upload Strategy:
- Files are uploaded to Cloudinary (primary storage, URLs stored in local DB)
- Files are ALSO uploaded to Lark Drive to get file_tokens for Bitable attachments
- Bitable attachment fields receive [{"file_token": "xxx"}] format
"""
import os
import json
import logging
import time
import uuid
from typing import Optional, Dict, Any, List, Tuple
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
LARK_DRIVE_UPLOAD_URL = "https://open.larksuite.com/open-apis/drive/v1/files/upload_all"

# Cache for access token
_cached_token: Optional[str] = None
_token_expiry: float = 0


# ============================================
# HTTP Request Helpers
# ============================================

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


def _make_multipart_request(url: str, headers: Dict, fields: Dict[str, str], file_field: str, file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Make a multipart/form-data request for file uploads.
    Uses urllib to avoid external dependencies.
    """
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex[:16]}"
    
    # Build multipart body
    body_parts = []
    
    # Add text fields
    for key, value in fields.items():
        body_parts.append(f'--{boundary}\r\n'.encode('utf-8'))
        body_parts.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode('utf-8'))
        body_parts.append(f'{value}\r\n'.encode('utf-8'))
    
    # Add file field
    body_parts.append(f'--{boundary}\r\n'.encode('utf-8'))
    body_parts.append(f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode('utf-8'))
    body_parts.append(f'Content-Type: application/octet-stream\r\n\r\n'.encode('utf-8'))
    body_parts.append(file_bytes)
    body_parts.append(f'\r\n--{boundary}--\r\n'.encode('utf-8'))
    
    body = b''.join(body_parts)
    
    # Set headers
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    headers["Content-Length"] = str(len(body))
    
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        logger.error(f"Lark Drive upload HTTP error {e.code}: {error_body}")
        try:
            return json.loads(error_body)
        except:
            return {"code": e.code, "error": error_body}
    except Exception as e:
        logger.error(f"Lark Drive upload error: {str(e)}")
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


# ============================================
# Lark Drive File Upload (for Bitable Attachments)
# ============================================

def download_file_from_url(url: str, timeout: int = 30) -> Optional[bytes]:
    """
    Download file bytes from a URL (e.g., Cloudinary URL).
    
    Args:
        url: The URL to download from
        timeout: Request timeout in seconds
    
    Returns:
        File bytes or None on failure
    """
    if not url:
        return None
    
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; LarkBot/1.0)"
        })
        
        with urllib.request.urlopen(req, timeout=timeout) as response:
            file_bytes = response.read()
            logger.debug(f"Downloaded {len(file_bytes)} bytes from {url[:50]}...")
            return file_bytes
            
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP error downloading file from {url[:50]}...: {e.code}")
        return None
    except Exception as e:
        logger.error(f"Error downloading file from {url[:50]}...: {str(e)}")
        return None


def upload_file_to_lark_drive(file_bytes: bytes, filename: str, parent_type: str = "bitable_file") -> Optional[str]:
    """
    Upload file to Lark Drive and get file_token for Bitable attachments.
    
    Uses the upload_all API for small files (< 20MB).
    API: POST /open-apis/drive/v1/files/upload_all
    
    Args:
        file_bytes: The file content as bytes
        filename: Filename for the uploaded file
        parent_type: Parent type, use "bitable_file" for Bitable attachments
    
    Returns:
        file_token string or None on failure
    """
    if not file_bytes:
        logger.warning("No file bytes provided for Lark Drive upload")
        return None
    
    token = get_tenant_access_token()
    if not token:
        logger.error("Cannot upload to Lark Drive: no access token")
        return None
    
    try:
        # File size check (upload_all supports up to 20MB)
        file_size = len(file_bytes)
        if file_size > 20 * 1024 * 1024:
            logger.error(f"File too large for upload_all API: {file_size} bytes (max 20MB)")
            return None
        
        logger.info(f"Uploading {filename} ({file_size} bytes) to Lark Drive...")
        
        # Prepare multipart form data
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        fields = {
            "file_name": filename,
            "parent_type": parent_type,
            "size": str(file_size)
        }
        
        response = _make_multipart_request(
            url=LARK_DRIVE_UPLOAD_URL,
            headers=headers,
            fields=fields,
            file_field="file",
            file_bytes=file_bytes,
            filename=filename
        )
        
        if response.get("code") != 0:
            logger.error(f"Lark Drive upload failed: {response.get('msg')}")
            return None
        
        file_token = response.get("data", {}).get("file_token")
        
        if file_token:
            logger.info(f"Lark Drive upload successful: file_token={file_token[:20]}...")
            return file_token
        else:
            logger.error("Lark Drive upload response missing file_token")
            return None
            
    except Exception as e:
        logger.error(f"Failed to upload to Lark Drive: {str(e)}")
        return None


def upload_url_to_lark_drive(url: str, filename: str) -> Optional[str]:
    """
    Download file from URL and upload to Lark Drive.
    Combines download_file_from_url and upload_file_to_lark_drive.
    
    Args:
        url: Source URL (e.g., Cloudinary URL)
        filename: Filename for the Lark Drive file
    
    Returns:
        file_token string or None on failure
    """
    if not url:
        return None
    
    # Download from source URL
    file_bytes = download_file_from_url(url)
    if not file_bytes:
        return None
    
    # Upload to Lark Drive
    return upload_file_to_lark_drive(file_bytes, filename)


def build_attachment_field(file_token: Optional[str]) -> Optional[List[Dict[str, str]]]:
    """
    Build a Bitable attachment field value from a file_token.
    
    Bitable attachment fields require format: [{"file_token": "xxx"}]
    
    Args:
        file_token: Lark Drive file token
    
    Returns:
        Attachment field value or None (to omit field)
    """
    if not file_token:
        return None
    
    return [{"file_token": file_token}]


# ============================================
# Bitable Operations
# ============================================


def append_record_to_bitable(app_token: str, table_id: str, fields: Dict[str, Any]) -> bool:
    """Append a record to Lark Bitable table."""
    logger.info(f"🔵 Appending record to Lark Bitable...")
    logger.info(f"   App Token: {app_token[:10]}...{app_token[-4:]}")
    logger.info(f"   Table ID: {table_id}")
    logger.info(f"   Fields count: {len(fields)}")
    
    token = get_tenant_access_token()
    if not token:
        logger.error("❌ Failed to get tenant access token")
        return False
    
    logger.info(f"✅ Got tenant access token: {token[:10]}...")
    
    try:
        url = LARK_BITABLE_RECORD_URL.format(app_token=app_token, table_id=table_id)
        logger.info(f"📡 POST URL: {url}")
        
        payload = {"fields": fields}
        logger.info(f"📦 Payload field names: {list(fields.keys())}")
        
        response = _make_request(url, method="POST", 
            headers={"Authorization": f"Bearer {token}"},
            data=payload
        )
        
        logger.info(f"📥 Lark API Response: {json.dumps(response)[:500]}")
        
        if response.get("code") != 0:
            error_msg = response.get('msg') or response.get('message') or 'Unknown error'
            logger.error(f"❌ Lark Bitable API error (code {response.get('code')}): {error_msg}")
            return False
        
        record_id = response.get("data", {}).get("record", {}).get("record_id")
        logger.info(f"✅ Successfully appended to Lark Bitable (record_id: {record_id})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Exception in append_record_to_bitable: {str(e)}", exc_info=True)
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
    """
    Append employee submission to Lark Bitable.
    
    DUAL UPLOAD STRATEGY:
    - Cloudinary URLs are stored in local database (unchanged)
    - Files are downloaded from Cloudinary and uploaded to Lark Drive
    - Lark Drive file_tokens are used for Bitable attachment fields
    
    Attachment fields receive: [{"file_token": "xxx"}]
    Text fields receive: plain strings
    """
    logger.info(f"[START] Starting Lark Bitable submission for employee: {id_number}")
    
    # Use configured Bitable credentials
    app_token = LARK_BITABLE_ID or os.environ.get('LARK_BITABLE_APP_TOKEN')
    table_id = LARK_TABLE_ID or os.environ.get('LARK_BITABLE_TABLE_ID')
    
    logger.info(f"[CONFIG] Lark BITABLE_ID: {app_token[:20] if app_token else 'MISSING'}...")
    logger.info(f"[CONFIG] Lark TABLE_ID: {table_id[:20] if table_id else 'MISSING'}...")
    
    if not app_token:
        logger.error("[ERROR] LARK_BITABLE_ID not configured. Skipping Lark append.")
        return False
    if not table_id:
        logger.error("[ERROR] LARK_TABLE_ID not configured. Skipping Lark append.")
        return False
    
    from datetime import datetime
    if date_last_modified is None:
        date_last_modified = datetime.now().isoformat()
    
    # =========================================
    # Step 1: Build TEXT fields (always included)
    # =========================================
    from datetime import datetime
    
    # Parse date_last_modified to get millisecond timestamp for Lark Date field (Type 5)
    # Lark Date fields expect millisecond timestamps
    date_value = None
    if date_last_modified:
        try:
            date_str = str(date_last_modified).strip()
            
            # Remove microseconds if present (e.g., "2026-01-24T15:30:37.824118" -> "2026-01-24T15:30:37")
            if '.' in date_str:
                date_str = date_str.split('.')[0]
            
            # Replace slashes with dashes for parsing
            date_str = date_str.replace('/', '-')
            
            # Parse ISO format with time: "2026-01-24T15:30:37" or just date: "2026-01-30"
            if 'T' in date_str:
                dt = datetime.fromisoformat(date_str)
            elif ' ' in date_str:
                dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            else:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            
            # Convert to millisecond timestamp
            timestamp_ms = int(dt.timestamp() * 1000)
            date_value = timestamp_ms
            logger.info(f"   Parsed date '{date_last_modified}' to timestamp: {date_value}")
            
        except Exception as e:
            logger.warning(f"   Failed to parse date '{date_last_modified}': {e}. Using current timestamp.")
            timestamp_ms = int(datetime.now().timestamp() * 1000)
            date_value = timestamp_ms
    else:
        timestamp_ms = int(datetime.now().timestamp() * 1000)
        date_value = timestamp_ms
    
    # Parse personal_number - convert to integer for Number field
    phone_number = 0
    if personal_number:
        # Extract only digits from phone number
        phone_digits = ''.join(c for c in str(personal_number) if c.isdigit())
        # Convert to integer
        phone_number = int(phone_digits) if phone_digits else 0
    
    fields = {
        "employee_name": employee_name,
        "first_name": first_name or "",
        "middle_initial": middle_initial or "",
        "last_name": last_name or "",
        "id_nickname": id_nickname or "",
        "id_number": id_number,
        "position": position,
        "department": department or "",
        "email": email,
        "personal number": phone_number,  # Number field - send as int
        "status": status,
        "date last modified": date_value,  # Date field - millisecond timestamp
    }
    
    print(f"\\n[DEBUG] Fields being sent to Lark:")
    for key, val in fields.items():
        print(f"  {key}: {repr(val)} (type: {type(val).__name__})")
    
    # =========================================
    # Step 2: Upload files to Lark Drive and build ATTACHMENT fields
    # Only add attachment fields if upload succeeds (file_token obtained)
    # =========================================
    
    # Safe ID for filenames
    safe_id = id_number.replace(' ', '_').replace('/', '-').replace('\\', '-') if id_number else 'unknown'
    
    # Photo attachment (original uploaded photo)
    if photo_url:
        logger.info(f"Uploading photo to Lark Drive for {safe_id}...")
        photo_token = upload_url_to_lark_drive(photo_url, f"{safe_id}_photo.jpg")
        photo_attachment = build_attachment_field(photo_token)
        if photo_attachment:
            fields["photo_preview"] = photo_attachment
            logger.info(f"Photo attachment added for {safe_id}")
    
    # AI Headshot attachment
    if ai_headshot_url:
        logger.info(f"Uploading AI headshot to Lark Drive for {safe_id}...")
        ai_token = upload_url_to_lark_drive(ai_headshot_url, f"{safe_id}_ai_headshot.jpg")
        ai_attachment = build_attachment_field(ai_token)
        if ai_attachment:
            fields["new_photo"] = ai_attachment
            logger.info(f"AI headshot attachment added for {safe_id}")
    
    # Signature attachment
    if signature_url:
        logger.info(f"Uploading signature to Lark Drive for {safe_id}...")
        sig_token = upload_url_to_lark_drive(signature_url, f"{safe_id}_signature.png")
        sig_attachment = build_attachment_field(sig_token)
        if sig_attachment:
            fields["signature_preview"] = sig_attachment
            logger.info(f"Signature attachment added for {safe_id}")
    
    # Render URL attachment (if provided)
    if render_url:
        logger.info(f"Uploading render to Lark Drive for {safe_id}...")
        render_token = upload_url_to_lark_drive(render_url, f"{safe_id}_render.png")
        render_attachment = build_attachment_field(render_token)
        if render_attachment:
            fields["render_url"] = render_attachment
            logger.info(f"Render attachment added for {safe_id}")
    
    # =========================================
    # Step 3: Log final payload and append to Bitable
    # =========================================
    text_fields = [k for k, v in fields.items() if not isinstance(v, list)]
    attachment_fields = [k for k, v in fields.items() if isinstance(v, list)]
    logger.info(f"Bitable payload - Text fields: {text_fields}")
    logger.info(f"Bitable payload - Attachment fields: {attachment_fields}")
    
    # Print JSON payload for debugging
    import json
    logger.info(f"Final payload JSON: {json.dumps({k: str(v)[:50] for k, v in fields.items()}, indent=2)}")
    
    return append_record_to_bitable(app_token, table_id, fields)
