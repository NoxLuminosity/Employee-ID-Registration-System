"""
Google Sheets Integration Service - Service Account Version
Handles appending employee submissions to Google Sheets.

Authentication: Uses GOOGLE_SERVICE_ACCOUNT_JSON environment variable (no files required).
This is production-safe for Vercel serverless functions.

Note: Image uploads are handled by Cloudinary (see cloudinary_service.py).
"""
import os
import json
import logging
from typing import Optional, List, Dict, Any
import gspread
from google.oauth2.service_account import Credentials

# Configure logging
logger = logging.getLogger(__name__)

# Google API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Cache credentials to avoid re-parsing JSON on every request
_cached_credentials: Optional[Credentials] = None


def get_google_credentials() -> Optional[Credentials]:
    """
    Get Google credentials from GOOGLE_SERVICE_ACCOUNT_JSON environment variable.
    Uses Service Account authentication (no user consent required).
    
    Returns None if env var is missing or invalid.
    """
    global _cached_credentials
    
    # Return cached credentials if available and valid
    if _cached_credentials is not None:
        return _cached_credentials
    
    try:
        # Get service account JSON from environment variable
        service_account_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        
        if not service_account_json:
            logger.error(
                "GOOGLE_SERVICE_ACCOUNT_JSON environment variable not set. "
                "Please add your service account JSON to Vercel environment variables."
            )
            return None
        
        # Parse the JSON string
        try:
            service_account_info = json.loads(service_account_json)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON: {str(e)}")
            return None
        
        # Validate required fields
        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        missing_fields = [f for f in required_fields if f not in service_account_info]
        if missing_fields:
            logger.error(f"GOOGLE_SERVICE_ACCOUNT_JSON missing required fields: {missing_fields}")
            return None
        
        if service_account_info.get('type') != 'service_account':
            logger.error("GOOGLE_SERVICE_ACCOUNT_JSON must be a service account credential (type: service_account)")
            return None
        
        # Create credentials from service account info
        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )
        
        # Cache the credentials
        _cached_credentials = creds
        
        logger.info(f"Google Service Account credentials loaded successfully (email: {service_account_info.get('client_email')})")
        return creds
        
    except Exception as e:
        logger.error(f"Failed to load Google credentials: {str(e)}")
        return None


def get_google_sheets_client() -> Optional[gspread.Client]:
    """
    Initialize and return Google Sheets client using Service Account credentials.
    Returns None if credentials are not configured or invalid.
    """
    try:
        creds = get_google_credentials()
        if not creds:
            return None
        
        # Create and return gspread client
        client = gspread.authorize(creds)
        logger.info("Google Sheets client initialized successfully")
        return client
        
    except Exception as e:
        logger.error(f"Failed to initialize Google Sheets client: {str(e)}")
        return None


def append_to_sheet(
    spreadsheet_id: str,
    worksheet_name: str,
    row_data: list,
    use_formulas: bool = False
) -> bool:
    """
    Append a row of data to a Google Sheet.
    
    Args:
        spreadsheet_id: The ID of the Google Spreadsheet
        worksheet_name: Name of the worksheet/tab to append to
        row_data: List of values to append as a row
        use_formulas: If True, treats values starting with '=' as formulas
    
    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_google_sheets_client()
        if not client:
            return False
        
        # Open the spreadsheet
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        # Get or create the worksheet
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            # Create worksheet if it doesn't exist
            worksheet = spreadsheet.add_worksheet(
                title=worksheet_name,
                rows=1000,
                cols=20
            )
            # Add header row matching new schema
            header = [
                'employee_name', 'id_nickname', 'id_number', 'position', 'department',
                'email', 'personal_number', 'photo_preview', 'photo_url', 'new_photo',
                'signature_preview', 'signature', 'status', 'date_last_modified',
                'id_generated', 'render_url'
            ]
            worksheet.append_row(header)
            logger.info(f"Created new worksheet: {worksheet_name}")
        
        # Append the row
        if use_formulas:
            # Get the next empty row
            all_values = worksheet.get_all_values()
            next_row = len(all_values) + 1
            
            # Calculate range
            num_cols = len(row_data)
            if num_cols <= 26:
                end_col = chr(ord('A') + num_cols - 1)
            else:
                end_col = 'A' + chr(ord('A') + (num_cols - 1) % 26)
            
            range_name = f"A{next_row}:{end_col}{next_row}"
            
            # Use update with USER_ENTERED to allow formulas
            worksheet.update(range_name, [row_data], value_input_option='USER_ENTERED')
        else:
            worksheet.append_row(row_data)
        
        logger.info(f"Successfully appended row to Google Sheet: {worksheet_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to append to Google Sheet: {str(e)}")
        return False


def append_employee_submission(
    employee_name: str,
    id_nickname: str,
    id_number: str,
    position: str,
    department: str,
    email: str,
    personal_number: str,
    photo_path: str,
    signature_path: str = None,
    status: str = 'Reviewing',
    date_last_modified: str = None,
    photo_url: Optional[str] = None,
    signature_url: Optional[str] = None,
    render_url: str = ''
) -> bool:
    """
    Append employee submission to Google Sheets with IMAGE() formulas for photo preview.
    
    Args:
        All employee fields
    
    Returns:
        True if successful, False otherwise
    """
    spreadsheet_id = os.environ.get('GOOGLE_SPREADSHEET_ID')
    worksheet_name = os.environ.get('GOOGLE_WORKSHEET_NAME', 'Employee Submissions')
    
    if not spreadsheet_id:
        logger.warning("GOOGLE_SPREADSHEET_ID not set. Skipping Google Sheets append.")
        return False
    
    from datetime import datetime
    if date_last_modified is None:
        date_last_modified = datetime.now().isoformat()
    
    # Create IMAGE() formulas for previews if URLs exist
    photo_preview = f'=IMAGE("{photo_url}")' if photo_url else ''
    signature_preview = f'=IMAGE("{signature_url}")' if signature_url else ''
    
    # Prepare row data with all fields
    row_data = [
        employee_name,
        id_nickname or '',
        id_number,
        position,
        department,
        email,
        personal_number,
        photo_preview,  # IMAGE() formula
        photo_url or '',
        '',  # new_photo - managed manually
        signature_preview,  # IMAGE() formula
        signature_url or '',
        status,
        date_last_modified,
        '',  # id_generated - managed manually
        render_url or ''
    ]
    
    return append_to_sheet(spreadsheet_id, worksheet_name, row_data, use_formulas=True)


def sync_employees_to_sheets(employees: List[Dict[str, Any]]) -> bool:
    """
    Sync all employee records to Google Sheets.
    Clears existing data and writes fresh data.
    
    Args:
        employees: List of employee dictionaries
    
    Returns:
        True if successful, False otherwise
    """
    spreadsheet_id = os.environ.get('GOOGLE_SPREADSHEET_ID')
    worksheet_name = os.environ.get('GOOGLE_WORKSHEET_NAME', 'Employee Submissions')
    
    if not spreadsheet_id:
        logger.warning("GOOGLE_SPREADSHEET_ID not set. Skipping sync.")
        return False
    
    try:
        client = get_google_sheets_client()
        if not client:
            return False
        
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=20)
        
        # Clear existing data
        worksheet.clear()
        
        # Header row
        header = [
            'employee_name', 'id_nickname', 'id_number', 'position', 'department',
            'email', 'personal_number', 'photo_preview', 'photo_url', 'new_photo',
            'signature_preview', 'signature', 'status', 'date_last_modified',
            'id_generated', 'render_url'
        ]
        
        # Prepare all rows
        rows = [header]
        for emp in employees:
            photo_url = emp.get('photo_url', '')
            signature_url = emp.get('signature_url', '')
            
            row = [
                emp.get('employee_name', ''),
                emp.get('id_nickname', ''),
                emp.get('id_number', ''),
                emp.get('position', ''),
                emp.get('department', ''),
                emp.get('email', ''),
                emp.get('personal_number', ''),
                f'=IMAGE("{photo_url}")' if photo_url else '',
                photo_url,
                '',
                f'=IMAGE("{signature_url}")' if signature_url else '',
                signature_url,
                emp.get('status', 'Reviewing'),
                emp.get('date_last_modified', ''),
                '',
                emp.get('render_url', '')
            ]
            rows.append(row)
        
        # Write all data
        worksheet.update('A1', rows, value_input_option='USER_ENTERED')
        
        logger.info(f"Successfully synced {len(employees)} employees to Google Sheets")
        return True
        
    except Exception as e:
        logger.error(f"Failed to sync to Google Sheets: {str(e)}")
        return False
