"""
Lark (Feishu) Bitable Integration Service
Handles appending employee submissions to Lark Bitable (spreadsheet-like database).

Authentication: Uses LARK_APP_ID and LARK_APP_SECRET environment variables.
This is production-safe for Vercel serverless functions.

Direct Cloudinary URL Strategy:
- Files are uploaded to Cloudinary (primary storage with CDN)
- Cloudinary URLs are used directly in Bitable attachment fields
- No Lark Drive upload required (avoids permission issues)
- Attachment fields receive: [{"url": "cloudinary_url", "name": "filename"}]
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
LARK_TABLE_ID_SPMA = os.environ.get('LARK_TABLE_ID_SPMA', 'tblajlHwJ6qFRlVa')

# SPMA Lark app credentials (may be different if table is in different Base)
LARK_APP_ID_SPMA = os.environ.get('LARK_APP_ID_SPMA', os.environ.get('LARK_APP_ID'))
LARK_APP_SECRET_SPMA = os.environ.get('LARK_APP_SECRET_SPMA', os.environ.get('LARK_APP_SECRET'))
LARK_BITABLE_ID_SPMA = os.environ.get('LARK_BITABLE_ID_SPMA', os.environ.get('LARK_BITABLE_ID'))

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


def build_attachment_from_url(url: str, filename: str = None) -> Optional[List[Dict[str, str]]]:
    """
    Build attachment field value from a Cloudinary URL.
    
    Lark Base attachment fields accept this format for URL-based attachments:
    [{"url": "https://example.com/image.jpg", "name": "image.jpg"}]
    
    This avoids the need for Lark Drive permissions.
    
    Args:
        url: The Cloudinary URL to the image
        filename: Optional filename to display in Lark Base
        
    Returns:
        List containing attachment dict, or None if URL is invalid
    """
    if not url:
        return None
    
    # Extract filename from URL if not provided
    if not filename:
        try:
            filename = url.split('/')[-1].split('?')[0]
            if not filename or len(filename) < 3:
                filename = "attachment.jpg"
        except:
            filename = "attachment.jpg"
    
    return [{"url": url, "name": filename}]


# ============================================
# Bitable Operations
# ============================================


def update_record_in_bitable(app_token: str, table_id: str, record_id: str, fields: Dict[str, Any], token: Optional[str] = None) -> bool:
    """Update a record in Lark Bitable table.
    
    Args:
        app_token: Lark Bitable app token (base ID)
        table_id: Table ID within the app
        record_id: The record ID to update
        fields: Dictionary of field values to update
        token: Optional pre-obtained access token (if None, will get default token)
    """
    logger.info(f"🔵 Updating record in Lark Bitable...")
    logger.info(f"   App Token: {app_token[:10]}...{app_token[-4:]}")
    logger.info(f"   Table ID: {table_id}")
    logger.info(f"   Record ID: {record_id}")
    logger.info(f"   Fields count: {len(fields)}")
    
    # Use provided token or get default
    if token is None:
        token = get_tenant_access_token()
        if not token:
            logger.error("❌ Failed to get tenant access token")
            return False
    
    logger.info(f"✅ Got tenant access token: {token[:10]}...")
    
    try:
        url = f"{LARK_BITABLE_RECORD_URL.format(app_token=app_token, table_id=table_id)}/{record_id}"
        logger.info(f"📡 PUT URL: {url}")
        
        payload = {"fields": fields}
        logger.info(f"📦 Payload field names: {list(fields.keys())}")
        
        response = _make_request(url, method="PUT", 
            headers={"Authorization": f"Bearer {token}"},
            data=payload
        )
        
        logger.info(f"📥 Lark API Response: {json.dumps(response)[:500]}")
        
        if response.get("code") != 0:
            error_msg = response.get('msg') or response.get('message') or 'Unknown error'
            logger.error(f"❌ Lark Bitable update error (code {response.get('code')}): {error_msg}")
            return False
        
        logger.info(f"✅ Successfully updated Lark Bitable record (record_id: {record_id})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Exception in update_record_in_bitable: {str(e)}", exc_info=True)
        return False


def log_status_transition(id_number: str, old_status: str, new_status: str, source: str = "HR System") -> None:
    """Log status transition with timestamp for traceability.
    
    Args:
        id_number: Employee ID number
        old_status: Previous status value
        new_status: New status value
        source: Source of the status change (e.g., "HR System", "PDF Download")
    """
    from datetime import datetime
    timestamp = datetime.now().isoformat()
    logger.info("=" * 60)
    logger.info(f"📊 STATUS TRANSITION LOG")
    logger.info(f"   Timestamp: {timestamp}")
    logger.info(f"   Employee ID: {id_number}")
    logger.info(f"   Transition: {old_status} → {new_status}")
    logger.info(f"   Source: {source}")
    logger.info("=" * 60)


# Valid status values for Lark Bitable dropdown field
# NOTE: These must match EXACTLY with the dropdown options in Lark Base
# Order: Reviewing -> Rendered -> Approved -> Completed
VALID_STATUS_VALUES = ["Reviewing", "Rendered", "Approved", "Completed"]

# Maximum retry attempts for handling race conditions
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 0.5


def validate_status_value(status: str) -> Tuple[bool, str]:
    """Validate that a status value is a valid dropdown option.
    
    Args:
        status: The status value to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not status:
        return False, "Status value cannot be empty"
    
    # Normalize status for comparison (handle case differences)
    normalized_status = status.strip()
    
    # Check exact match against valid values
    if normalized_status not in VALID_STATUS_VALUES:
        return False, f"Invalid status '{status}'. Must be one of: {', '.join(VALID_STATUS_VALUES)}"
    
    return True, ""


def find_and_update_employee_status(id_number: str, new_status: str, old_status: str = None, source: str = "HR System") -> bool:
    """Find an employee by ID number and update their status in Lark Bitable.
    
    Uses precise record matching by id_number to ensure only the correct employee
    record is updated. Includes validation for dropdown status values and
    retry logic to handle race conditions.
    
    Args:
        id_number: The employee's ID number to search for (unique identifier)
        new_status: The new status value (must be "Reviewing", "Approved", or "Completed")
        old_status: Previous status for logging (optional)
        source: Source of the status change for logging
    
    Returns:
        True if update was successful, False otherwise
    """
    logger.info(f"🔍 Finding employee {id_number} in Lark Bitable to update status to '{new_status}'")
    
    # Step 1: Validate the new status value against allowed dropdown options
    is_valid, error_msg = validate_status_value(new_status)
    if not is_valid:
        logger.error(f"❌ Status validation failed: {error_msg}")
        return False
    
    # Log the status transition
    log_status_transition(id_number, old_status or "Unknown", new_status, source)
    
    app_token = LARK_BITABLE_ID or os.environ.get('LARK_BITABLE_APP_TOKEN')
    table_id = LARK_TABLE_ID or os.environ.get('LARK_BITABLE_TABLE_ID')
    
    if not app_token or not table_id:
        logger.error("❌ Lark Bitable credentials not configured")
        return False
    
    # Step 2: Find the exact record by id_number with filter
    # Use precise filter to ensure we get only the matching record
    filter_formula = f'CurrentValue.[id_number]="{id_number}"'
    records = get_bitable_records(app_token, table_id, filter_formula=filter_formula)
    
    if not records:
        logger.warning(f"⚠️ Employee {id_number} not found in Lark Bitable using filter: {filter_formula}")
        return False
    
    # Step 3: Verify we found exactly the right record (prevent updating wrong record)
    matching_record = None
    for record in records:
        fields = record.get("fields", {})
        record_id_number = fields.get("id_number", "").strip()
        
        # Exact match verification (case-sensitive)
        if record_id_number == id_number.strip():
            matching_record = record
            logger.info(f"✅ Found exact match for id_number: {id_number}")
            break
    
    if not matching_record:
        logger.error(f"❌ No exact match found for id_number '{id_number}' in {len(records)} returned records")
        return False
    
    record_id = matching_record.get("record_id")
    if not record_id:
        logger.error(f"❌ No record_id found for employee {id_number}")
        return False
    
    logger.info(f"📍 Targeting Lark Bitable record_id: {record_id} for employee {id_number}")
    
    # Step 4: Update the status with retry logic for race conditions
    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            success = update_record_in_bitable(app_token, table_id, record_id, {"status": new_status})
            
            if success:
                logger.info(f"✅ Larkbase status synced: {id_number} → {new_status} (record_id: {record_id})")
                return True
            else:
                logger.warning(f"⚠️ Update attempt {attempt + 1}/{MAX_RETRY_ATTEMPTS} failed for {id_number}")
                
        except Exception as e:
            logger.warning(f"⚠️ Update attempt {attempt + 1}/{MAX_RETRY_ATTEMPTS} raised exception: {str(e)}")
        
        # Wait before retry (except on last attempt)
        if attempt < MAX_RETRY_ATTEMPTS - 1:
            time.sleep(RETRY_DELAY_SECONDS)
    
    logger.error(f"❌ Failed to sync Larkbase status for {id_number} after {MAX_RETRY_ATTEMPTS} attempts")
    return False


def update_employee_id_card(id_number: str, pdf_url: str, source: str = "HR PDF Download") -> bool:
    """Update the id_card field for an employee in Lark Bitable.
    
    Uses precise record matching by id_number to ensure only the correct employee
    record is updated. The id_card field is a URL field in LarkBase.
    
    For LarkBase URL fields, we use the format:
    {"link": "https://...", "text": "display text"}
    
    Args:
        id_number: The employee's ID number to search for (unique identifier)
        pdf_url: The Cloudinary URL of the uploaded PDF
        source: Source of the update for logging
    
    Returns:
        True if update was successful, False otherwise
    """
    logger.info(f"📄 Updating id_card for employee {id_number}")
    logger.info(f"   PDF URL: {pdf_url[:80]}..." if len(pdf_url) > 80 else f"   PDF URL: {pdf_url}")
    
    if not pdf_url:
        logger.error("❌ PDF URL cannot be empty")
        return False
    
    app_token = LARK_BITABLE_ID or os.environ.get('LARK_BITABLE_APP_TOKEN')
    table_id = LARK_TABLE_ID or os.environ.get('LARK_BITABLE_TABLE_ID')
    
    if not app_token or not table_id:
        logger.error("❌ Lark Bitable credentials not configured")
        return False
    
    # Find the exact record by id_number with filter
    filter_formula = f'CurrentValue.[id_number]="{id_number}"'
    records = get_bitable_records(app_token, table_id, filter_formula=filter_formula)
    
    if not records:
        logger.warning(f"⚠️ Employee {id_number} not found in Lark Bitable")
        return False
    
    # Verify we found exactly the right record
    matching_record = None
    for record in records:
        fields = record.get("fields", {})
        record_id_number = fields.get("id_number", "").strip()
        
        if record_id_number == id_number.strip():
            matching_record = record
            logger.info(f"✅ Found exact match for id_number: {id_number}")
            break
    
    if not matching_record:
        logger.error(f"❌ No exact match found for id_number '{id_number}'")
        return False
    
    record_id = matching_record.get("record_id")
    if not record_id:
        logger.error(f"❌ No record_id found for employee {id_number}")
        return False
    
    logger.info(f"📍 Targeting Lark Bitable record_id: {record_id} for employee {id_number}")
    
    # Build proper URL field value for LarkBase
    # URL fields accept: {"link": "https://...", "text": "display text"}
    # Extract filename from URL for display text
    try:
        filename = pdf_url.split('/')[-1].split('?')[0]
        if not filename or len(filename) < 3:
            filename = f"ID_Card_{id_number}.pdf"
    except:
        filename = f"ID_Card_{id_number}.pdf"
    
    # Use URL field format (object with link and text)
    id_card_url_field = {"link": pdf_url, "text": filename}
    logger.info(f"📎 URL field value: {json.dumps(id_card_url_field)}")
    
    # Update with retry logic
    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            success = update_record_in_bitable(app_token, table_id, record_id, {"id_card": id_card_url_field})
            
            if success:
                logger.info(f"✅ Larkbase id_card updated for {id_number} (record_id: {record_id})")
                return True
            else:
                logger.warning(f"⚠️ Update attempt {attempt + 1}/{MAX_RETRY_ATTEMPTS} failed for {id_number}")
                
        except Exception as e:
            logger.warning(f"⚠️ Update attempt {attempt + 1}/{MAX_RETRY_ATTEMPTS} raised exception: {str(e)}")
        
        if attempt < MAX_RETRY_ATTEMPTS - 1:
            time.sleep(RETRY_DELAY_SECONDS)
    
    logger.error(f"❌ Failed to update id_card for {id_number} after {MAX_RETRY_ATTEMPTS} attempts")
    return False


def update_employee_status(id_number: str, new_status: str) -> bool:
    """Update the status field for an employee in Lark Bitable.
    
    Wrapper around find_and_update_employee_status for simplified testing.
    Uses precise record matching by id_number to ensure only the correct employee
    record is updated. The status field is a dropdown field in LarkBase.
    
    Args:
        id_number: The employee's ID number to search for (unique identifier)
        new_status: The new status value (must be "Reviewing", "Approved", or "Completed")
    
    Returns:
        True if update was successful, False otherwise
    """
    logger.info(f"📝 Updating status for employee {id_number} to '{new_status}'")
    
    # Call the main function with default source
    return find_and_update_employee_status(id_number, new_status, source="API Call")


def append_record_to_bitable(app_token: str, table_id: str, fields: Dict[str, Any], token: Optional[str] = None) -> bool:
    """Append a record to Lark Bitable table.
    
    Args:
        app_token: Lark Bitable app token (base ID)
        table_id: Table ID within the app
        fields: Dictionary of field values
        token: Optional pre-obtained access token (if None, will get default token)
    """
    logger.info(f"🔵 Appending record to Lark Bitable...")
    logger.info(f"   App Token: {app_token[:10]}...{app_token[-4:]}")
    logger.info(f"   Table ID: {table_id}")
    logger.info(f"   Fields count: {len(fields)}")
    
    # Use provided token or get default
    if token is None:
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
    personal_number: str,
    location_branch: Optional[str] = None,
    department: str = '',
    email: str = '',
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
    last_name: Optional[str] = None,
    suffix: Optional[str] = None,
    table_id: Optional[str] = None,
    # Field Officer specific fields
    field_officer_type: Optional[str] = None,
    field_clearance: Optional[str] = None,
    fo_division: Optional[str] = None,
    fo_campaign: Optional[str] = None
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
    target_table_id = table_id or LARK_TABLE_ID or os.environ.get('LARK_BITABLE_TABLE_ID')
    
    logger.info(f"[CONFIG] Lark BITABLE_ID: {app_token[:20] if app_token else 'MISSING'}...")
    logger.info(f"[CONFIG] Lark TABLE_ID: {target_table_id[:20] if target_table_id else 'MISSING'}...")
    
    if not app_token:
        logger.error("[ERROR] LARK_BITABLE_ID not configured. Skipping Lark append.")
        return False
    if not target_table_id:
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
        "suffix": suffix or "",
        "id_nickname": id_nickname or "",
        "id_number": id_number,
        "position": position,
        "location_branch": location_branch or "",
        "email": email,
        "personal_number": phone_number,  # Number field - send as int
        "status": status,
        # Field Officer specific fields - use column names matching Larkbase table
        "field_officer_type": field_officer_type or "",
        "field_clearance": field_clearance or "",
        "division": fo_division or "",  # Maps to 'division' column in Larkbase
        "department": department or "",  # Maps to 'department' column in Larkbase
        "campaign": fo_campaign or "",   # Maps to 'campaign' column in Larkbase
    }
    
    print(f"\\n[DEBUG] Fields being sent to Lark:")
    for key, val in fields.items():
        print(f"  {key}: {repr(val)} (type: {type(val).__name__})")
    
    # =========================================
    # Step 2: Add URL fields for photo/signature/headshot
    # Columns are URL/Link type - use Lark URL format: {"link": "url", "text": "display"}
    # =========================================
    
    # Safe ID for logging
    safe_id = id_number.replace(' ', '_').replace('/', '-').replace('\\', '-') if id_number else 'unknown'
    
    logger.info("=" * 60)
    logger.info("🔗 PROCESSING IMAGE URLS (Lark URL Field Format)")
    logger.info(f"  Photo URL: {photo_url[:80] + '...' if photo_url and len(photo_url) > 80 else photo_url}")
    logger.info(f"  AI Headshot URL: {ai_headshot_url[:80] + '...' if ai_headshot_url and len(ai_headshot_url) > 80 else ai_headshot_url}")
    logger.info(f"  Signature URL: {signature_url[:80] + '...' if signature_url and len(signature_url) > 80 else signature_url}")
    logger.info("=" * 60)
    
    # Photo URL (photo_preview column) - Lark URL field format
    if photo_url:
        fields["photo_preview"] = {"link": photo_url, "text": "Photo"}
        logger.info(f"✅ Photo URL added for {safe_id}")
    else:
        logger.info(f"ℹ️ No photo URL provided for {safe_id}")
    
    # AI Headshot URL (new_photo column) - Lark URL field format
    if ai_headshot_url:
        fields["new_photo"] = {"link": ai_headshot_url, "text": "AI Headshot"}
        logger.info(f"✅ AI headshot URL added for {safe_id}")
    else:
        logger.info(f"ℹ️ No AI headshot URL provided for {safe_id}")
    
    # Signature URL (signature_preview column) - Lark URL field format
    if signature_url:
        fields["signature_preview"] = {"link": signature_url, "text": "Signature"}
        logger.info(f"✅ Signature URL added for {safe_id}")
    else:
        logger.info(f"ℹ️ No signature URL provided for {safe_id}")
    
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
    
    return append_record_to_bitable(app_token, target_table_id, fields)


def append_spma_employee_submission(
    employee_name: str,
    middle_initial: str = '',
    last_name: str = '',
    suffix: str = '',
    id_number: str = '',
    division: str = '',
    department: str = '',
    field_clearance: str = '',
    branch_location: str = '',
    email: str = '',
    personal_number: str = '',
    photo_url: Optional[str] = None,
    signature_url: Optional[str] = None
) -> bool:
    """
    Append SPMA (Legal Officer) employee submission to Lark Bitable.
    
    This uses the SPMA table (tblajlHwJ6qFRlVa) with different field structure:
    - employee_name, middle_initial, last_name, suffix
    - id_number, division, department, field_clearance
    - branch_location, email, personal_number
    - photo_preview (URL), signature (URL)
    
    NOTE: SPMA table may be in a different Lark Base, uses separate credentials.
    """
    logger.info(f"[START] Starting SPMA Lark Bitable submission for employee: {id_number}")
    
    # Use SPMA-specific Lark credentials (may be different Base)
    app_token = LARK_BITABLE_ID_SPMA
    target_table_id = LARK_TABLE_ID_SPMA
    spma_app_id = LARK_APP_ID_SPMA
    spma_app_secret = LARK_APP_SECRET_SPMA
    
    logger.info(f"[CONFIG] SPMA - Lark BITABLE_ID: {app_token[:20] if app_token else 'MISSING'}...")
    logger.info(f"[CONFIG] SPMA - Lark TABLE_ID: {target_table_id if target_table_id else 'MISSING'}...")
    logger.info(f"[CONFIG] SPMA - Using separate app credentials: {spma_app_id[:10]}...")
    
    if not app_token:
        logger.error("[ERROR] LARK_BITABLE_ID_SPMA not configured. Skipping SPMA Lark append.")
        return False
    if not target_table_id:
        logger.error("[ERROR] LARK_TABLE_ID_SPMA not configured. Skipping SPMA Lark append.")
        return False
    
    # Get SPMA-specific access token using SPMA app credentials
    logger.info("Getting SPMA-specific tenant access token...")
    spma_token = None
    if spma_app_id and spma_app_secret:
        try:
            response = _make_request(LARK_TOKEN_URL, method="POST", data={
                "app_id": spma_app_id,
                "app_secret": spma_app_secret
            })
            if response.get("code") == 0:
                spma_token = response.get("tenant_access_token")
                logger.info(f"✅ SPMA access token obtained: {spma_token[:10]}...")
            else:
                logger.error(f"❌ Failed to get SPMA access token: {response.get('msg')}")
        except Exception as e:
            logger.error(f"❌ Error getting SPMA token: {str(e)}")
    
    if not spma_token:
        logger.error("[ERROR] Could not obtain SPMA access token. Check LARK_APP_ID_SPMA and LARK_APP_SECRET_SPMA")
        return False
    
    # Parse personal_number to integer for Number field
    phone_number = 0
    if personal_number:
        phone_digits = ''.join(c for c in str(personal_number) if c.isdigit())
        phone_number = int(phone_digits) if phone_digits else 0
    
    # Build fields matching SPMA table structure
    fields = {
        "employee_name": employee_name,
        "middle_initial": middle_initial or "",
        "last_name": last_name or "",
        "suffix": suffix or "",
        "id_number": id_number,
        "division": division or "",
        "department": department or "",
        "field_clearance": field_clearance or "",
        "branch_location": branch_location or "",
        "email": email or "",
        "personal_number": phone_number,  # Number field
    }
    
    # Safe ID for logging
    safe_id = id_number.replace(' ', '_').replace('/', '-').replace('\\', '-') if id_number else 'unknown'
    
    logger.info("=" * 60)
    logger.info("🔗 SPMA - PROCESSING IMAGE URLS")
    logger.info(f"  Photo URL: {photo_url[:80] + '...' if photo_url and len(photo_url) > 80 else photo_url}")
    logger.info(f"  Signature URL: {signature_url[:80] + '...' if signature_url and len(signature_url) > 80 else signature_url}")
    logger.info("=" * 60)
    
    # Photo URL (photo_preview column) - Lark URL field format
    if photo_url:
        fields["photo_preview"] = {"link": photo_url, "text": "Photo"}
        logger.info(f"✅ SPMA Photo URL added for {safe_id}")
    
    # Signature URL (signature column) - Lark URL field format
    if signature_url:
        fields["signature"] = {"link": signature_url, "text": "Signature"}
        logger.info(f"✅ SPMA Signature URL added for {safe_id}")
    
    # Log final payload
    logger.info(f"SPMA Bitable payload fields: {list(fields.keys())}")
    
    print(f"\n[DEBUG SPMA] Fields being sent to Lark:")
    for key, val in fields.items():
        print(f"  {key}: {repr(val)[:50]} (type: {type(val).__name__})")
    
    # Use SPMA-specific token for append
    return append_record_to_bitable(app_token, target_table_id, fields, token=spma_token)
