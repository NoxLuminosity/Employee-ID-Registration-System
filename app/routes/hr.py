"""
HR Routes - From Code 2
Handles HR authentication, dashboard, gallery, and employee management.
Includes background removal functionality for AI-generated photos.
Supports both password-based and Lark SSO authentication.
"""
from fastapi import APIRouter, Request, Depends, Cookie, Query
from fastapi.responses import HTMLResponse, JSONResponse, Response, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
from pathlib import Path
from datetime import datetime
import logging
import json

# Database abstraction layer (supports Supabase and SQLite)
from app.database import (
    get_all_employees,
    get_employee_by_id,
    update_employee,
    update_employee_status_rpc,
    delete_employee,
    table_exists,
    get_employee_count,
    get_status_breakdown,
    USE_SUPABASE,
    get_sqlite_connection
)

# Import services for background removal
from app.services.background_removal_service import remove_background_from_url
from app.services.cloudinary_service import upload_bytes_to_cloudinary

# Import POC routing service
from app.services.poc_routing_service import compute_nearest_poc_branch, is_valid_poc_branch

# Import Lark OAuth service
from app.services.lark_auth_service import (
    get_authorization_url,
    complete_oauth_flow,
    validate_hr_portal_access,
    LARK_APP_ID
)

# Import authentication
from app.auth import (
    verify_session, 
    verify_org_access,
    authenticate_user, 
    create_session, 
    delete_session,
    get_session
)

router = APIRouter(prefix="/hr")

# Get the directory where this file is located
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Configure logging
logger = logging.getLogger(__name__)

# Check if running on Vercel (serverless) or locally
# VERCEL env var is "1" when running on Vercel
IS_VERCEL = os.environ.get("VERCEL", "0") == "1" or os.environ.get("VERCEL_ENV") is not None


# ============================================
# Authentication Routes
# ============================================

@router.get("/login", response_class=HTMLResponse)
def hr_login_page(request: Request, hr_session: str = Cookie(None)):
    """HR Login Page - redirect to dashboard if already logged in"""
    if get_session(hr_session):
        return RedirectResponse(url="/hr/dashboard", status_code=302)
    return templates.TemplateResponse("hr_login.html", {"request": request})


@router.post("/login")
async def hr_login(request: Request, response: Response):
    """Process HR login"""
    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "")
    
    if not username or not password:
        return JSONResponse(content={
            "success": False, 
            "error": "Username and password are required"
        })
    
    if not authenticate_user(username, password):
        return JSONResponse(content={
            "success": False, 
            "error": "Invalid username or password"
        })
    
    # Create session (JWT token)
    session_id = create_session(username)
    
    # Create response with cookie
    json_response = JSONResponse(content={
        "success": True, 
        "redirect": "/hr/dashboard"
    })
    
    # VERCEL FIX: Set secure=True for production (HTTPS) environments
    # This ensures the cookie is only sent over secure connections in production
    # but still works for local development over HTTP
    is_production = IS_VERCEL or os.environ.get('VERCEL_ENV') == 'production'
    
    # Set session cookie (8 hours expiry)
    json_response.set_cookie(
        key="hr_session",
        value=session_id,
        httponly=True,
        max_age=28800,  # 8 hours
        samesite="lax",
        secure=is_production,  # Only require HTTPS in production
        path="/"  # Ensure cookie is sent for all paths
    )
    
    logger.info(f"HR user logged in: {username} (secure={is_production})")
    return json_response


@router.get("/logout")
def hr_logout(response: Response, hr_session: str = Cookie(None)):
    """Logout HR user"""
    if hr_session:
        delete_session(hr_session)
    
    response = RedirectResponse(url="/hr/login", status_code=302)
    response.delete_cookie("hr_session")
    return response


# ============================================
# Lark SSO Authentication Routes
# ============================================

@router.get("/lark/login")
def lark_login(request: Request):
    """
    Initiate Lark OAuth login flow for HR Portal.
    Redirects user to Lark authorization page.
    
    IMPORTANT: On Vercel, set LARK_HR_REDIRECT_URI environment variable to:
    https://your-vercel-domain.vercel.app/hr/lark/callback
    
    This URL must be registered in Lark Developer Console -> Security Settings -> Redirect URLs
    """
    # Check for explicit HR redirect URI first (recommended for Vercel)
    env_redirect_uri = os.environ.get('LARK_HR_REDIRECT_URI')
    
    if env_redirect_uri:
        # CRITICAL FIX: Strip whitespace to remove trailing newlines from env vars
        # Vercel dashboard copy/paste can introduce \n which encodes as %0A in URLs
        # causing Lark OAuth error 20029 (redirect_uri mismatch)
        redirect_uri = env_redirect_uri.strip()
        logger.info(f"Using LARK_HR_REDIRECT_URI from environment: {redirect_uri}")
    else:
        # Build redirect URI dynamically from request
        scheme = request.url.scheme
        host = request.headers.get('host', 'localhost:8000')
        
        # Normalize 127.0.0.1 to localhost for Lark compatibility
        if '127.0.0.1' in host:
            host = host.replace('127.0.0.1', 'localhost')
        
        # Use HTTPS in production (Vercel)
        if IS_VERCEL:
            scheme = 'https'
        
        redirect_uri = f"{scheme}://{host}/hr/lark/callback"
        logger.info(f"Built redirect_uri dynamically: {redirect_uri}")
    
    logger.info(f"Initiating HR Lark OAuth with redirect_uri: {redirect_uri}")
    
    # Get authorization URL
    auth_url, state = get_authorization_url(redirect_uri)
    
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/lark/callback")
def lark_callback(
    request: Request,
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    error_description: str = Query(None)
):
    """
    Handle Lark OAuth callback.
    Exchanges authorization code for tokens and creates session.
    Validates organization access (only People Support department allowed).
    """
    # Handle authorization denial
    if error:
        logger.warning(f"Lark OAuth error: {error} - {error_description}")
        return templates.TemplateResponse("hr_login.html", {
            "request": request,
            "error": f"Lark login denied: {error_description or error}"
        })
    
    # Validate required parameters
    if not code:
        logger.error("Lark callback missing authorization code")
        return templates.TemplateResponse("hr_login.html", {
            "request": request,
            "error": "Missing authorization code from Lark"
        })
    
    if not state:
        logger.error("Lark callback missing state parameter")
        return templates.TemplateResponse("hr_login.html", {
            "request": request,
            "error": "Missing state parameter (security check failed)"
        })
    
    # Complete OAuth flow
    result = complete_oauth_flow(code, state)
    
    if not result.get("success"):
        error_msg = result.get("error", "Unknown error during Lark authentication")
        logger.error(f"Lark OAuth flow failed: {error_msg}")
        return templates.TemplateResponse("hr_login.html", {
            "request": request,
            "error": f"Lark login failed: {error_msg}"
        })
    
    # Extract user info
    user = result.get("user", {})
    tokens = result.get("tokens", {})
    
    user_name = user.get("name") or user.get("email") or user.get("user_id")
    user_email = user.get("email")
    open_id = user.get("open_id")
    logger.info(f"Lark OAuth successful for user: {user_name}")
    
    # Validate organization access for HR Portal
    # Uses Lark Contact API (department hierarchy) and Bitable API (employee records)
    if open_id:
        access_result = validate_hr_portal_access(open_id, user_email=user_email)
        if not access_result.get("allowed"):
            logger.warning(f"HR Portal access denied for user {user_name}: {access_result.get('reason')}")
            return templates.TemplateResponse("hr_login.html", {
                "request": request,
                "error": access_result.get("reason", "Access denied. You are not authorized to access the HR Portal.")
            })
        logger.info(f"HR Portal access granted for user {user_name}: {access_result.get('reason')}")
    
    # Create session with Lark data
    session_id = create_session(
        username=user_name,
        hours=8,
        lark_data={
            "user_id": user.get("user_id"),
            "open_id": user.get("open_id"),
            "name": user.get("name"),
            "email": user.get("email"),
            "avatar_url": user.get("avatar_url"),
            "tenant_key": user.get("tenant_key"),
        }
    )
    
    # Create redirect response with session cookie
    response = RedirectResponse(url="/hr/dashboard", status_code=302)
    
    is_production = IS_VERCEL or os.environ.get('VERCEL_ENV') == 'production'
    response.set_cookie(
        key="hr_session",
        value=session_id,
        httponly=True,
        max_age=28800,  # 8 hours
        samesite="lax",
        secure=is_production,
        path="/"
    )
    
    logger.info(f"Lark user logged in: {user_name}")
    return response


# ============================================
# Protected HTML Pages
# ============================================

@router.get("/", response_class=HTMLResponse)
def hr_dashboard_redirect(request: Request, hr_session: str = Cookie(None)):
    """Redirect /hr/ to /hr/dashboard or login"""
    if not get_session(hr_session):
        return RedirectResponse(url="/hr/login", status_code=302)
    return RedirectResponse(url="/hr/dashboard", status_code=302)


@router.get("/dashboard", response_class=HTMLResponse)
def hr_dashboard(request: Request, hr_session: str = Cookie(None)):
    """HR Dashboard page - Protected by auth and org access"""
    session = get_session(hr_session)
    if not session:
        return RedirectResponse(url="/hr/login", status_code=302)
    
    # Verify org access on each request
    from app.services.lark_auth_service import is_descendant_of_people_support
    
    if session.get("auth_type") == "lark":
        open_id = session.get("lark_open_id")
        is_authorized, reason = is_descendant_of_people_support(open_id)
        
        if not is_authorized:
            logger.warning(f"Org access denied for dashboard: {session.get('username')} - {reason}")
            return templates.TemplateResponse("hr_login.html", {
                "request": request,
                "error": f"Access denied. HR Portal access is restricted to People Support department members only."
            })
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "username": session["username"]
    })


@router.get("/gallery", response_class=HTMLResponse)
def id_gallery(request: Request, hr_session: str = Cookie(None)):
    """ID Gallery page - Protected by auth and org access"""
    session = get_session(hr_session)
    if not session:
        return RedirectResponse(url="/hr/login", status_code=302)
    
    # Verify org access on each request
    from app.services.lark_auth_service import is_descendant_of_people_support
    
    if session.get("auth_type") == "lark":
        open_id = session.get("lark_open_id")
        is_authorized, reason = is_descendant_of_people_support(open_id)
        
        if not is_authorized:
            logger.warning(f"Org access denied for gallery: {session.get('username')} - {reason}")
            return templates.TemplateResponse("hr_login.html", {
                "request": request,
                "error": f"Access denied. HR Portal access is restricted to People Support department members only."
            })
    
    return templates.TemplateResponse("gallery.html", {
        "request": request,
        "username": session["username"]
    })


# ============================================
# API Endpoints (Protected)
# ============================================

def verify_api_session(hr_session: str = Cookie(None)):
    """Verify session for API endpoints, return 401 if not authenticated"""
    session = get_session(hr_session)
    if not session:
        return None
    return session["username"]


@router.get("/api/debug")
def api_debug(hr_session: str = Cookie(None)):
    """Debug endpoint to check database and session status"""
    import os
    from app.database import SUPABASE_URL, SUPABASE_KEY, SQLITE_DB
    
    debug_info = {
        "use_supabase": USE_SUPABASE,
        "is_vercel": IS_VERCEL,
        "supabase_url_set": bool(SUPABASE_URL),
        "supabase_key_set": bool(SUPABASE_KEY),
        "sqlite_path": SQLITE_DB if not USE_SUPABASE else "N/A (using Supabase)",
        "session_present": hr_session is not None,
        "session_valid": False,
        "employee_count": 0,
        "table_exists": False,
        "error": None,
        "recommendation": None
    }
    
    # Check session
    session = get_session(hr_session)
    if session:
        debug_info["session_valid"] = True
        debug_info["session_username"] = session.get("username")
    
    # Check database
    try:
        debug_info["table_exists"] = table_exists()
        debug_info["employee_count"] = get_employee_count()
        debug_info["status_breakdown"] = get_status_breakdown()
    except Exception as e:
        debug_info["error"] = str(e)
    
    # Add recommendation if data might be ephemeral
    if IS_VERCEL and not USE_SUPABASE:
        debug_info["recommendation"] = "WARNING: Using SQLite on Vercel (/tmp is ephemeral). Data will be lost on cold starts. Set SUPABASE_URL and SUPABASE_KEY environment variables for persistent storage."
    
    logger.info(f"Debug endpoint: {debug_info}")
    return JSONResponse(content=debug_info)


@router.get("/api/debug/lark")
def api_debug_lark():
    """
    Debug endpoint to check Lark Base configuration and test connection.
    
    This endpoint helps diagnose why Lark Base updates may be failing on Vercel.
    It checks:
    1. Environment variables are set
    2. Access token can be obtained
    3. Records can be fetched from Lark Base
    
    Access: Public (for debugging purposes)
    """
    import os
    from app.services.lark_service import (
        LARK_APP_ID, LARK_APP_SECRET, LARK_BITABLE_ID, LARK_TABLE_ID,
        get_tenant_access_token, get_bitable_records
    )
    
    debug_info = {
        "is_vercel": IS_VERCEL,
        "env_vars": {
            "LARK_APP_ID_set": bool(os.environ.get('LARK_APP_ID')),
            "LARK_APP_ID_value": os.environ.get('LARK_APP_ID', '')[:10] + "..." if os.environ.get('LARK_APP_ID') else "NOT SET",
            "LARK_APP_SECRET_set": bool(os.environ.get('LARK_APP_SECRET')),
            "LARK_BITABLE_ID_set": bool(os.environ.get('LARK_BITABLE_ID')),
            "LARK_BITABLE_ID_value": os.environ.get('LARK_BITABLE_ID', 'NOT SET'),
            "LARK_TABLE_ID_set": bool(os.environ.get('LARK_TABLE_ID')),
            "LARK_TABLE_ID_value": os.environ.get('LARK_TABLE_ID', 'NOT SET'),
        },
        "module_vars": {
            "LARK_APP_ID": LARK_APP_ID[:10] + "..." if LARK_APP_ID else "NOT SET",
            "LARK_APP_SECRET": "***" if LARK_APP_SECRET else "NOT SET",
            "LARK_BITABLE_ID": LARK_BITABLE_ID or "NOT SET",
            "LARK_TABLE_ID": LARK_TABLE_ID or "NOT SET",
        },
        "token_test": {
            "success": False,
            "token_prefix": None,
            "error": None
        },
        "records_test": {
            "success": False,
            "record_count": 0,
            "sample_id_numbers": [],
            "error": None
        }
    }
    
    # Test 1: Can we get an access token?
    try:
        token = get_tenant_access_token()
        if token:
            debug_info["token_test"]["success"] = True
            debug_info["token_test"]["token_prefix"] = token[:10] + "..."
        else:
            debug_info["token_test"]["error"] = "get_tenant_access_token returned None"
    except Exception as e:
        debug_info["token_test"]["error"] = str(e)
    
    # Test 2: Can we fetch records from Lark Base?
    if debug_info["token_test"]["success"]:
        try:
            app_token = LARK_BITABLE_ID
            table_id = LARK_TABLE_ID
            
            if app_token and table_id:
                # Fetch first 5 records to verify connection
                records = get_bitable_records(app_token, table_id, page_size=5)
                
                if records is not None:
                    debug_info["records_test"]["success"] = True
                    debug_info["records_test"]["record_count"] = len(records)
                    
                    # Get sample id_numbers for verification
                    sample_ids = []
                    for record in records[:3]:
                        fields = record.get("fields", {})
                        id_num = fields.get("id_number", "")
                        status = fields.get("status", "")
                        if id_num:
                            sample_ids.append(f"{id_num} ({status})")
                    debug_info["records_test"]["sample_id_numbers"] = sample_ids
                else:
                    debug_info["records_test"]["error"] = "get_bitable_records returned None"
            else:
                debug_info["records_test"]["error"] = f"Missing config: app_token={bool(app_token)}, table_id={bool(table_id)}"
        except Exception as e:
            debug_info["records_test"]["error"] = str(e)
    
    # Add recommendations
    recommendations = []
    
    if not debug_info["env_vars"]["LARK_APP_ID_set"]:
        recommendations.append("Set LARK_APP_ID environment variable in Vercel")
    if not debug_info["env_vars"]["LARK_APP_SECRET_set"]:
        recommendations.append("Set LARK_APP_SECRET environment variable in Vercel")
    if not debug_info["env_vars"]["LARK_BITABLE_ID_set"]:
        recommendations.append("Set LARK_BITABLE_ID environment variable in Vercel")
    if not debug_info["env_vars"]["LARK_TABLE_ID_set"]:
        recommendations.append("Set LARK_TABLE_ID environment variable in Vercel")
    
    if debug_info["token_test"]["success"] and not debug_info["records_test"]["success"]:
        recommendations.append("Token works but records fetch failed - check Bitable permissions")
    
    if not recommendations:
        if debug_info["records_test"]["success"]:
            recommendations.append("✅ All Lark Base configuration looks good!")
        else:
            recommendations.append("Check Vercel function logs for more details")
    
    debug_info["recommendations"] = recommendations
    
    logger.info(f"Lark debug endpoint: token_ok={debug_info['token_test']['success']}, records_ok={debug_info['records_test']['success']}")
    return JSONResponse(content=debug_info)


@router.get("/api/employees")
def api_get_employees(request: Request, hr_session: str = Cookie(None)):
    """Get all employees for the dashboard - Protected by org access
    
    VERCEL FIX: Enhanced logging to debug cookie/session issues in serverless
    """
    logger.info(f"=== API /hr/api/employees ===")
    logger.info(f"Cookie value received: {hr_session[:20] if hr_session else 'None'}...")
    logger.info(f"Request headers: Authorization={request.headers.get('authorization', 'None')}")
    logger.info(f"Environment: USE_SUPABASE={USE_SUPABASE}, IS_VERCEL={IS_VERCEL}")
    logger.info(f"Client: {request.client.host if request.client else 'Unknown'}")
    
    session = get_session(hr_session)
    logger.info(f"Session retrieved: {session is not None}")
    if session:
        logger.info(f"Session username: {session.get('username')}, auth_type: {session.get('auth_type')}")
    
    if not session:
        logger.warning("API /api/employees: Unauthorized - no valid session")
        logger.warning(f"Failed to deserialize session from token (first 20 chars): {hr_session[:20] if hr_session else 'token is None'}")
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    
    # Verify org access on each request
    if session.get("auth_type") == "lark":
        from app.services.lark_auth_service import is_descendant_of_people_support
        open_id = session.get("lark_open_id")
        is_authorized, reason = is_descendant_of_people_support(open_id)
        
        if not is_authorized:
            logger.warning(f"API /api/employees: Org access denied - {reason}")
            return JSONResponse(status_code=403, content={
                "success": False, 
                "error": "Access denied. You are not authorized to access the HR Portal."
            })
    
    logger.info(f"API /api/employees: Authenticated as {session.get('username')}")
    
    try:
        # Check if table exists first
        if not table_exists():
            logger.info("API /api/employees: Table does not exist, returning empty list")
            return JSONResponse(content={"success": True, "employees": []})

        # Get all employees using abstraction layer
        rows = get_all_employees()
        logger.info(f"API /api/employees: Found {len(rows)} total employees")

        employees = []
        for row in rows:
            employees.append({
                "id": row.get("id"),
                "employee_name": row.get("employee_name"),
                "first_name": row.get("first_name"),
                "middle_initial": row.get("middle_initial"),
                "last_name": row.get("last_name"),
                "suffix": row.get("suffix"),
                "id_nickname": row.get("id_nickname"),
                "id_number": row.get("id_number"),
                "position": row.get("position"),
                "location_branch": row.get("location_branch"),  # Current field used in dashboard
                "department": row.get("department"),  # Deprecated - kept for backward compatibility
                "email": row.get("email"),
                "personal_number": row.get("personal_number"),
                "photo_path": row.get("photo_path"),
                "photo_url": row.get("photo_url"),
                "new_photo": bool(row.get("new_photo")),
                "new_photo_url": row.get("new_photo_url"),
                "nobg_photo_url": row.get("nobg_photo_url"),
                "signature_path": row.get("signature_path"),
                "signature_url": row.get("signature_url"),
                "status": row.get("status") or "Reviewing",
                "date_last_modified": row.get("date_last_modified"),
                "id_generated": bool(row.get("id_generated")),
                "render_url": row.get("render_url"),
                "emergency_name": row.get("emergency_name"),
                "emergency_contact": row.get("emergency_contact"),
                "emergency_address": row.get("emergency_address"),
                # Field Officer specific fields
                "field_officer_type": row.get("field_officer_type"),
                "field_clearance": row.get("field_clearance"),
                "fo_division": row.get("fo_division"),
                "fo_department": row.get("fo_department"),
                "fo_campaign": row.get("fo_campaign")
            })

        logger.info(f"API /api/employees: Returning {len(employees)} employees")
        return JSONResponse(content={"success": True, "employees": employees})

    except Exception as e:
        logger.error(f"Error fetching employees: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/api/employees/{employee_id}")
def api_get_employee(employee_id: int, hr_session: str = Cookie(None)):
    """Get a single employee by ID - Protected by org access"""
    session = get_session(hr_session)
    if not session:
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    
    # Verify org access on each request
    if session.get("auth_type") == "lark":
        from app.services.lark_auth_service import is_descendant_of_people_support
        open_id = session.get("lark_open_id")
        is_authorized, reason = is_descendant_of_people_support(open_id)
        
        if not is_authorized:
            logger.warning(f"API /api/employees/{employee_id}: Org access denied - {reason}")
            return JSONResponse(status_code=403, content={
                "success": False, 
                "error": "Access denied. You are not authorized to access the HR Portal."
            })
    try:
        row = get_employee_by_id(employee_id)

        if not row:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Employee not found"}
            )

        employee = {
            "id": row.get("id"),
            "employee_name": row.get("employee_name"),
            "first_name": row.get("first_name"),
            "middle_initial": row.get("middle_initial"),
            "last_name": row.get("last_name"),
            "suffix": row.get("suffix"),
            "id_nickname": row.get("id_nickname"),
            "id_number": row.get("id_number"),
            "position": row.get("position"),
            "department": row.get("department"),
            "location_branch": row.get("location_branch"),
            "email": row.get("email"),
            "personal_number": row.get("personal_number"),
            "photo_path": row.get("photo_path"),
            "photo_url": row.get("photo_url"),
            "new_photo": bool(row.get("new_photo")),
            "new_photo_url": row.get("new_photo_url"),
            "nobg_photo_url": row.get("nobg_photo_url"),
            "signature_path": row.get("signature_path"),
            "signature_url": row.get("signature_url"),
            "status": row.get("status") or "Reviewing",
            "date_last_modified": row.get("date_last_modified"),
            "id_generated": bool(row.get("id_generated")),
            "render_url": row.get("render_url"),
            "emergency_name": row.get("emergency_name"),
            "emergency_contact": row.get("emergency_contact"),
            "emergency_address": row.get("emergency_address"),
            # Field Officer specific fields
            "field_officer_type": row.get("field_officer_type"),
            "field_clearance": row.get("field_clearance"),
            "fo_division": row.get("fo_division"),
            "fo_department": row.get("fo_department"),
            "fo_campaign": row.get("fo_campaign")
        }

        return JSONResponse(content={"success": True, "employee": employee})

    except Exception as e:
        logger.error(f"Error fetching employee {employee_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/api/employees/{employee_id}/approve")
def api_approve_employee(employee_id: int, hr_session: str = Cookie(None)):
    """Approve an employee's ID application - Protected by org access"""
    session = get_session(hr_session)
    if not session:
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    
    # Verify org access on each request
    if session.get("auth_type") == "lark":
        from app.services.lark_auth_service import is_descendant_of_people_support
        open_id = session.get("lark_open_id")
        is_authorized, reason = is_descendant_of_people_support(open_id)
        
        if not is_authorized:
            logger.warning(f"API /api/employees/{employee_id}/approve: Org access denied - {reason}")
            return JSONResponse(status_code=403, content={
                "success": False, 
                "error": "Access denied. You are not authorized to access the HR Portal."
            })
    try:
        # Check if employee exists and is in Reviewing status
        row = get_employee_by_id(employee_id)

        if not row:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Employee not found"}
            )

        if row.get("status") != "Rendered":
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": f"Cannot approve. Current status: {row.get('status')}. Only 'Rendered' IDs can be approved."}
            )

        # Update status to Approved
        success = update_employee(employee_id, {
            "status": "Approved",
            "date_last_modified": datetime.now().isoformat()
        })

        if not success:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to update employee"}
            )

        # Sync status to Lark Bitable (one-way authoritative from HR side)
        lark_synced = False
        lark_error = None
        try:
            from app.services.lark_service import find_and_update_employee_status
            id_number = row.get("id_number")
            old_status = row.get("status")
            if id_number:
                logger.info(f"📤 Syncing status 'Approved' to Lark for id_number: {id_number}")
                lark_synced = find_and_update_employee_status(
                    id_number, 
                    "Approved",
                    old_status=old_status,
                    source="HR Approval"
                )
                if lark_synced:
                    logger.info(f"✅ Lark Bitable status synced to 'Approved' for employee {id_number}")
                else:
                    lark_error = "Lark update returned False - check logs for details"
                    logger.warning(f"⚠️ Failed to sync Lark Bitable status to 'Approved' for employee {id_number}")
            else:
                lark_error = "No id_number found for employee"
                logger.warning(f"⚠️ Cannot sync to Lark - employee {employee_id} has no id_number")
        except Exception as lark_e:
            lark_error = str(lark_e)
            logger.warning(f"⚠️ Could not sync status to Lark Bitable: {str(lark_e)}")

        logger.info(f"Employee {employee_id} approved (Lark synced: {lark_synced})")
        return JSONResponse(content={
            "success": True, 
            "message": "Application approved",
            "lark_synced": lark_synced,
            "lark_error": lark_error
        })

    except Exception as e:
        logger.error(f"Error approving employee {employee_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/api/employees/{employee_id}/send-to-poc")
def api_send_to_poc(employee_id: int, hr_session: str = Cookie(None)):
    """
    Send a single employee's ID card to nearest POC branch.
    Changes status from "Approved" to "Sent to POC".
    Uses haversine distance to find nearest POC.
    """
    session = get_session(hr_session)
    if not session:
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    
    # Verify org access on each request
    if session.get("auth_type") == "lark":
        from app.services.lark_auth_service import is_descendant_of_people_support
        open_id = session.get("lark_open_id")
        is_authorized, reason = is_descendant_of_people_support(open_id)
        
        if not is_authorized:
            logger.warning(f"API /api/employees/{employee_id}/send-to-poc: Org access denied - {reason}")
            return JSONResponse(status_code=403, content={
                "success": False, 
                "error": "Access denied. You are not authorized to access the HR Portal."
            })
    
    try:
        row = get_employee_by_id(employee_id)
        if not row:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Employee not found"}
            )
        
        current_status = row.get("status")
        if current_status != "Approved":
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": f"Cannot send to POC. Current status: {current_status}. Must be 'Approved'."}
            )
        
        # Compute nearest POC branch based on employee's location
        location_branch = row.get("location_branch", "")
        nearest_poc = compute_nearest_poc_branch(location_branch)
        
        # Update employee status via RPC (bypasses PostgREST schema cache)
        id_number = row.get("id_number")
        success = update_employee_status_rpc(employee_id, "Sent to POC")
        
        if not success:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to update employee status"}
            )
        
        # Sync status to Lark Bitable
        lark_synced = False
        try:
            from app.services.lark_service import find_and_update_employee_status
            if id_number:
                lark_synced = find_and_update_employee_status(
                    id_number,
                    "Sent to POC",
                    old_status=current_status,
                    source="HR Portal Send to POC"
                )
                if lark_synced:
                    logger.info(f"✅ Lark Bitable status synced to 'Sent to POC' for employee {id_number}")
                else:
                    logger.warning(f"⚠️ Failed to sync Lark Bitable status to 'Sent to POC' for employee {id_number}")
        except Exception as lark_e:
            logger.warning(f"⚠️ Could not sync status to Lark Bitable: {str(lark_e)}")
        
        # Send actual Lark message to POC (or test recipient if in test mode)
        message_sent = False
        email_sent_updated = False
        test_mode = False
        send_error = None
        try:
            from app.services.lark_service import send_to_poc, update_employee_email_sent, is_poc_test_mode
            from app.services.poc_routing_service import get_poc_email
            
            test_mode = is_poc_test_mode()
            poc_email = get_poc_email(nearest_poc)
            
            # Prepare employee data for message (include PDF URL from render_url field)
            employee_data = {
                "id_number": id_number,
                "employee_name": row.get("employee_name", ""),
                "position": row.get("position", ""),
                "location_branch": location_branch,
                "pdf_url": row.get("render_url", ""),  # Include PDF URL in the message
                "render_url": row.get("render_url", ""),
            }
            
            # Send the message
            send_result = send_to_poc(employee_data, nearest_poc, poc_email)
            
            if send_result.get("success"):
                message_sent = True
                logger.info(f"✅ POC message sent for employee {id_number} to {nearest_poc}" + 
                           (f" (TEST MODE - sent to {send_result.get('recipient', 'test recipient')})" if test_mode else ""))
                
                # Update email_sent in Lark Bitable
                try:
                    email_sent_updated = update_employee_email_sent(
                        id_number, 
                        email_sent=True,
                        resolved_printer_branch=nearest_poc
                    )
                    if email_sent_updated:
                        logger.info(f"✅ email_sent updated to True in Lark Bitable for {id_number}")
                    else:
                        logger.warning(f"⚠️ Failed to update email_sent in Lark Bitable for {id_number}")
                except Exception as email_e:
                    logger.warning(f"⚠️ Could not update email_sent in Lark Bitable: {str(email_e)}")
            else:
                send_error = send_result.get("error", "Unknown error")
                logger.warning(f"⚠️ Failed to send POC message for employee {id_number}: {send_error}")
        except Exception as msg_e:
            send_error = str(msg_e)
            logger.warning(f"⚠️ Could not send POC message: {send_error}")
        
        logger.info(f"Employee {employee_id} sent to POC '{nearest_poc}' (Lark synced: {lark_synced}, message sent: {message_sent})")
        return JSONResponse(content={
            "success": True,
            "message": f"Sent to POC: {nearest_poc}",
            "nearest_poc": nearest_poc,
            "lark_synced": lark_synced,
            "message_sent": message_sent,
            "email_sent_updated": email_sent_updated,
            "test_mode": test_mode,
            "send_error": send_error
        })
    
    except Exception as e:
        logger.error(f"Error sending employee {employee_id} to POC: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/api/send-all-to-pocs")
def api_send_all_to_pocs(hr_session: str = Cookie(None)):
    """
    Bulk send all "Approved" employees to their nearest POC branches.
    Changes status from "Approved" to "Sent to POC" for all applicable employees.
    Uses haversine distance to find nearest POC for each employee.
    """
    session = get_session(hr_session)
    if not session:
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    
    # Verify org access on each request
    if session.get("auth_type") == "lark":
        from app.services.lark_auth_service import is_descendant_of_people_support
        open_id = session.get("lark_open_id")
        is_authorized, reason = is_descendant_of_people_support(open_id)
        
        if not is_authorized:
            logger.warning(f"API /api/send-all-to-pocs: Org access denied - {reason}")
            return JSONResponse(status_code=403, content={
                "success": False, 
                "error": "Access denied. You are not authorized to access the HR Portal."
            })
    
    try:
        # Get all employees
        all_employees = get_all_employees()
        approved_employees = [emp for emp in all_employees if emp.get("status") == "Approved"]
        
        if not approved_employees:
            return JSONResponse(content={
                "success": True,
                "message": "No approved employees to send to POCs",
                "sent_count": 0
            })
        
        success_count = 0
        failed_count = 0
        message_sent_count = 0
        poc_routing = {}  # Track how many employees sent to each POC
        
        # Import messaging functions once
        from app.services.lark_service import find_and_update_employee_status, send_to_poc, update_employee_email_sent, is_poc_test_mode
        from app.services.poc_routing_service import get_poc_email
        test_mode = is_poc_test_mode()
        
        for emp in approved_employees:
            employee_id = emp.get("id")
            location_branch = emp.get("location_branch", "")
            id_number = emp.get("id_number")
            
            try:
                # Compute nearest POC
                nearest_poc = compute_nearest_poc_branch(location_branch)
                
                # Update employee status via RPC (bypasses PostgREST schema cache)
                success = update_employee_status_rpc(employee_id, "Sent to POC")
                
                if success:
                    success_count += 1
                    poc_routing[nearest_poc] = poc_routing.get(nearest_poc, 0) + 1
                    
                    # Sync to Lark Bitable
                    try:
                        if id_number:
                            find_and_update_employee_status(
                                id_number,
                                "Sent to POC",
                                old_status="Approved",
                                source="HR Portal Bulk Send to POCs"
                            )
                    except Exception as lark_e:
                        logger.warning(f"⚠️ Could not sync status to Lark for {id_number}: {str(lark_e)}")
                    
                    # Send actual Lark message to POC
                    try:
                        poc_email = get_poc_email(nearest_poc)
                        employee_data = {
                            "id_number": id_number,
                            "employee_name": emp.get("employee_name", ""),
                            "position": emp.get("position", ""),
                            "location_branch": location_branch,
                            "pdf_url": emp.get("render_url", ""),  # Include PDF URL in the message
                            "render_url": emp.get("render_url", ""),
                        }
                        send_result = send_to_poc(employee_data, nearest_poc, poc_email)
                        
                        if send_result.get("success"):
                            message_sent_count += 1
                            # Update email_sent in Lark Bitable
                            try:
                                update_employee_email_sent(id_number, email_sent=True, resolved_printer_branch=nearest_poc)
                            except Exception as email_e:
                                logger.warning(f"⚠️ Could not update email_sent for {id_number}: {str(email_e)}")
                        else:
                            logger.warning(f"⚠️ Failed to send POC message for {id_number}: {send_result.get('error')}")
                    except Exception as msg_e:
                        logger.warning(f"⚠️ Could not send POC message for {id_number}: {str(msg_e)}")
                else:
                    failed_count += 1
                    
            except Exception as emp_e:
                logger.error(f"Error sending employee {employee_id} to POC: {str(emp_e)}")
                failed_count += 1
        
        logger.info(f"Bulk send to POCs complete: {success_count} sent, {failed_count} failed")
        logger.info(f"POC routing breakdown: {poc_routing}")
        
        # Return appropriate response based on results
        # If ALL failed, return error (500). If some succeeded, return partial success (200).
        if success_count == 0 and failed_count > 0:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": f"All {failed_count} employee(s) failed to send to POC",
                    "sent_count": 0,
                    "failed_count": failed_count
                }
            )
        
        return JSONResponse(content={
            "success": success_count > 0,
            "message": f"Sent {success_count} employee(s) to POCs" + (f", {failed_count} failed" if failed_count > 0 else ""),
            "sent_count": success_count,
            "failed_count": failed_count,
            "message_sent_count": message_sent_count,
            "test_mode": test_mode,
            "poc_routing": poc_routing
        })
    
    except Exception as e:
        logger.error(f"Error in bulk send to POCs: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/api/employees/{employee_id}/render")
def api_render_employee(employee_id: int, hr_session: str = Cookie(None)):
    """Mark employee ID as Rendered (ready for Gallery review) - does NOT approve"""
    session = get_session(hr_session)
    if not session:
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    
    # Verify org access on each request
    if session.get("auth_type") == "lark":
        from app.services.lark_auth_service import is_descendant_of_people_support
        open_id = session.get("lark_open_id")
        is_authorized, reason = is_descendant_of_people_support(open_id)
        
        if not is_authorized:
            logger.warning(f"API /api/employees/{employee_id}/render: Org access denied - {reason}")
            return JSONResponse(status_code=403, content={
                "success": False, 
                "error": "Access denied. You are not authorized to access the HR Portal."
            })
    try:
        # Check if employee exists and is in an acceptable status
        row = get_employee_by_id(employee_id)

        if not row:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Employee not found"}
            )

        # Accept Reviewing, Pending, or Submitted status for rendering
        current_status = row.get("status")
        acceptable_statuses = ["Reviewing", "Pending", "Submitted"]
        
        if current_status not in acceptable_statuses:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": f"Cannot render. Current status: {current_status}. Must be one of: {', '.join(acceptable_statuses)}"}
            )

        # Update status to Rendered (NOT Approved - approval happens in Gallery)
        success = update_employee(employee_id, {
            "status": "Rendered",
            "date_last_modified": datetime.now().isoformat()
        })

        if not success:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to update employee"}
            )

        # Sync status to Lark Bitable
        lark_synced = False
        lark_error = None
        try:
            from app.services.lark_service import find_and_update_employee_status
            id_number = row.get("id_number")
            if id_number:
                logger.info(f"📤 Syncing status 'Rendered' to Lark for id_number: {id_number}")
                lark_synced = find_and_update_employee_status(
                    id_number, 
                    "Rendered",
                    old_status=current_status,
                    source="HR Render"
                )
                if lark_synced:
                    logger.info(f"✅ Lark Bitable status synced to 'Rendered' for employee {id_number}")
                else:
                    lark_error = "Lark update returned False - check logs for details"
                    logger.warning(f"⚠️ Failed to sync Lark Bitable status to 'Rendered' for employee {id_number}")
            else:
                lark_error = "No id_number found for employee"
                logger.warning(f"⚠️ Cannot sync to Lark - employee {employee_id} has no id_number")
        except Exception as lark_e:
            lark_error = str(lark_e)
            logger.warning(f"⚠️ Could not sync status to Lark Bitable: {str(lark_e)}")

        logger.info(f"Employee {employee_id} rendered (Lark synced: {lark_synced})")
        return JSONResponse(content={
            "success": True, 
            "message": "ID marked as Rendered - ready for Gallery approval",
            "lark_synced": lark_synced,
            "lark_error": lark_error
        })

    except Exception as e:
        logger.error(f"Error rendering employee {employee_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.delete("/api/employees/{employee_id}")
def api_delete_employee(employee_id: int, hr_session: str = Cookie(None)):
    """Mark employee application as Removed instead of deleting - Protected by org access"""
    session = get_session(hr_session)
    if not session:
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    
    # Verify org access on each request
    if session.get("auth_type") == "lark":
        from app.services.lark_auth_service import is_descendant_of_people_support
        open_id = session.get("lark_open_id")
        is_authorized, reason = is_descendant_of_people_support(open_id)
        
        if not is_authorized:
            logger.warning(f"API /api/employees/{employee_id} DELETE: Org access denied - {reason}")
            return JSONResponse(status_code=403, content={
                "success": False, 
                "error": "Access denied. You are not authorized to access the HR Portal."
            })
    try:
        # Check if employee exists
        row = get_employee_by_id(employee_id)

        if not row:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Employee not found"}
            )

        employee_name = row.get("employee_name")
        id_number = row.get("id_number")
        current_status = row.get("status")

        # Update status to Removed instead of deleting
        success = update_employee(employee_id, {
            "status": "Removed",
            "date_last_modified": datetime.now().isoformat()
        })
        
        if not success:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to remove employee"}
            )

        # Sync status to Lark Bitable
        lark_synced = False
        try:
            from app.services.lark_service import find_and_update_employee_status
            if id_number:
                lark_synced = find_and_update_employee_status(
                    id_number,
                    "Removed",
                    old_status=current_status,
                    source="HR Remove"
                )
                if lark_synced:
                    logger.info(f"✅ Lark Bitable status synced to 'Removed' for employee {id_number}")
                else:
                    logger.warning(f"⚠️ Failed to sync Lark Bitable status to 'Removed' for employee {id_number}")
        except Exception as lark_e:
            logger.warning(f"⚠️ Could not sync status to Lark Bitable: {str(lark_e)}")

        logger.info(f"Employee {employee_id} ({employee_name}) marked as Removed (Lark synced: {lark_synced})")
        return JSONResponse(content={"success": True, "message": f"Application for {employee_name} removed", "lark_synced": lark_synced})

    except Exception as e:
        logger.error(f"Error removing employee {employee_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/api/employees/{employee_id}/remove-background")
def api_remove_background(employee_id: int, hr_session: str = Cookie(None)):
    """Remove background from AI-generated photo and save the result - Protected by org access"""
    import traceback
    
    session = get_session(hr_session)
    if not session:
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    
    # Verify org access on each request
    if session.get("auth_type") == "lark":
        from app.services.lark_auth_service import is_descendant_of_people_support
        open_id = session.get("lark_open_id")
        is_authorized, reason = is_descendant_of_people_support(open_id)
        
        if not is_authorized:
            logger.warning(f"API /api/employees/{employee_id}/remove-background: Org access denied - {reason}")
            return JSONResponse(status_code=403, content={
                "success": False, 
                "error": "Access denied. You are not authorized to access the HR Portal."
            })
    
    logger.info(f"=== REMOVE BACKGROUND REQUEST for employee {employee_id} ===")
    
    try:
        # Get the employee's AI photo URL
        row = get_employee_by_id(employee_id)

        if not row:
            logger.error(f"Employee {employee_id} not found")
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Employee not found"}
            )

        logger.info(f"Employee found: id_number={row.get('id_number')}, new_photo_url={row.get('new_photo_url', '')[:50] if row.get('new_photo_url') else 'None'}...")

        if not row.get("new_photo_url"):
            logger.error(f"No AI photo available for employee {employee_id}")
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "No AI photo available to process"}
            )

        # If already has nobg photo, return it
        if row.get("nobg_photo_url"):
            logger.info(f"Employee {employee_id} already has nobg photo: {row.get('nobg_photo_url', '')[:50]}...")
            return JSONResponse(content={
                "success": True, 
                "nobg_photo_url": row.get("nobg_photo_url"),
                "message": "Background already removed"
            })

        ai_photo_url = row.get("new_photo_url")
        safe_id = row.get("id_number", "").replace(' ', '_').replace('/', '-').replace('\\', '-')

        logger.info(f"Starting background removal for employee {employee_id}...")
        logger.info(f"AI Photo URL: {ai_photo_url}")

        # Remove background using remove.bg API
        logger.info("Calling remove_background_from_url...")
        nobg_bytes, error = remove_background_from_url(ai_photo_url)
        
        if not nobg_bytes:
            logger.error(f"Background removal failed: {error}")
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": error or "Failed to remove background"}
            )

        logger.info(f"Background removed successfully, got {len(nobg_bytes)} bytes")

        # Upload to Cloudinary
        logger.info("Uploading to Cloudinary...")
        nobg_public_id = f"{safe_id}_nobg"
        nobg_url = upload_bytes_to_cloudinary(
            image_bytes=nobg_bytes,
            public_id=nobg_public_id,
            folder="employees"
        )

        if not nobg_url:
            logger.error("Cloudinary upload failed")
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to upload processed image"}
            )

        logger.info(f"Uploaded to Cloudinary: {nobg_url}")

        # Update database with nobg URL
        success = update_employee(employee_id, {
            "nobg_photo_url": nobg_url,
            "date_last_modified": datetime.now().isoformat()
        })

        if not success:
            logger.error("Failed to update employee with nobg URL")

        logger.info(f"=== BACKGROUND REMOVAL COMPLETE for employee {employee_id} ===")
        return JSONResponse(content={
            "success": True, 
            "nobg_photo_url": nobg_url,
            "message": "Background removed successfully"
        })

    except Exception as e:
        logger.error(f"Error removing background for employee {employee_id}: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/api/employees/{employee_id}/complete")
def api_complete_employee(employee_id: int, hr_session: str = Cookie(None)):
    """Mark an employee's ID as completed (after PDF download) - syncs to Larkbase"""
    if not get_session(hr_session):
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    try:
        # Check if employee exists and is Approved
        row = get_employee_by_id(employee_id)

        if not row:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Employee not found"}
            )

        old_status = row.get("status")
        if old_status not in ["Sent to POC", "Completed"]:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": f"Cannot mark as complete. Current status: {old_status}. Must be 'Sent to POC'."}
            )

        # Update status to Completed
        success = update_employee(employee_id, {
            "status": "Completed",
            "id_generated": 1,
            "date_last_modified": datetime.now().isoformat()
        })

        if not success:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to update employee"}
            )

        # Sync status to Lark Bitable (one-way authoritative from HR side)
        lark_synced = False
        try:
            from app.services.lark_service import find_and_update_employee_status
            id_number = row.get("id_number")
            if id_number:
                lark_synced = find_and_update_employee_status(
                    id_number, 
                    "Completed", 
                    old_status=old_status,
                    source="PDF Download"
                )
                if lark_synced:
                    logger.info(f"✅ Lark Bitable status synced to 'Completed' for employee {id_number}")
                else:
                    logger.warning(f"⚠️ Failed to sync Lark Bitable status to 'Completed' for employee {id_number}")
        except Exception as lark_e:
            logger.warning(f"⚠️ Could not sync status to Lark Bitable: {str(lark_e)}")

        logger.info(f"Employee {employee_id} marked as completed (Lark synced: {lark_synced})")
        return JSONResponse(content={
            "success": True, 
            "message": "ID marked as completed",
            "lark_synced": lark_synced
        })

    except Exception as e:
        logger.error(f"Error completing employee {employee_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/api/employees/{employee_id}/upload-pdf")
async def api_upload_pdf(employee_id: int, request: Request, hr_session: str = Cookie(None)):
    """
    Upload employee ID PDF to Cloudinary and save URL to LarkBase id_card column.
    
    This endpoint receives the PDF bytes from the frontend after generation,
    uploads it to Cloudinary, and updates the LarkBase id_card field with the URL.
    
    CRITICAL FLOW:
    1. Receive PDF bytes from frontend
    2. Upload to Cloudinary -> get secure URL
    3. Update LarkBase id_card field with attachment format
    4. Return success ONLY if both operations succeed
    5. Frontend triggers download ONLY after receiving success response
    
    Request body should be the raw PDF bytes (Content-Type: application/pdf).
    
    Returns:
        - success: True only if both Cloudinary upload AND LarkBase update succeed
        - pdf_url: The Cloudinary URL of the uploaded PDF
        - lark_synced: True if LarkBase id_card was updated successfully
        - error: Error message if any step failed
    """
    session = get_session(hr_session)
    if not session:
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    
    try:
        # Get employee data
        row = get_employee_by_id(employee_id)
        
        if not row:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Employee not found"}
            )
        
        # Accept Rendered, Approved, or Completed status (Rendered is new workflow)
        if row.get("status") not in ["Rendered", "Approved", "Completed"]:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "ID not ready for approval"}
            )
        
        # Read PDF bytes from request body
        pdf_bytes = await request.body()
        
        if not pdf_bytes or len(pdf_bytes) < 100:
            logger.error(f"Invalid PDF data received for employee {employee_id}: {len(pdf_bytes) if pdf_bytes else 0} bytes")
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Invalid or empty PDF data"}
            )
        
        logger.info(f"📥 Received PDF upload for employee {employee_id}: {len(pdf_bytes)} bytes")
        
        # Generate unique public_id for the PDF
        id_number = row.get("id_number", "")
        id_number_safe = id_number.replace(" ", "_").replace("/", "-").replace("\\", "-")
        employee_name = row.get("employee_name", "").replace(" ", "_")
        position = row.get("position", "")
        
        # Add timestamp to ensure uniqueness
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Determine suffix based on position
        suffix = "_dual_templates" if position == "Field Officer" else ""
        public_id = f"ID_{id_number_safe}_{employee_name}{suffix}_{timestamp}"
        
        # Step 1: Upload PDF to Cloudinary
        logger.info(f"📤 Uploading PDF to Cloudinary: {public_id}")
        from app.services.cloudinary_service import upload_pdf_to_cloudinary
        pdf_url = upload_pdf_to_cloudinary(pdf_bytes, public_id, folder="id_cards")
        
        if not pdf_url:
            logger.error(f"❌ Cloudinary upload failed for employee {employee_id}")
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to upload PDF to cloud storage"}
            )
        
        logger.info(f"✅ PDF uploaded to Cloudinary: {pdf_url}")
        
        # Step 1.5: Verify the URL is publicly accessible before saving to LarkBase
        # This prevents saving 401/403 URLs to the database
        import urllib.request
        import urllib.error
        try:
            logger.info(f"🔗 Verifying PDF URL accessibility: {pdf_url[:80]}...")
            req = urllib.request.Request(pdf_url, method='HEAD')
            req.add_header('User-Agent', 'Mozilla/5.0 (compatible; URLValidator/1.0)')
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    logger.info(f"✅ PDF URL is publicly accessible (HTTP {response.status})")
                else:
                    logger.warning(f"⚠️ PDF URL returned unexpected status: HTTP {response.status}")
        except urllib.error.HTTPError as http_err:
            logger.error(f"❌ PDF URL not accessible: HTTP {http_err.code} - {http_err.reason}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False, 
                    "error": f"PDF uploaded but URL not accessible (HTTP {http_err.code})",
                    "pdf_url": pdf_url,
                    "http_error": http_err.code
                }
            )
        except Exception as url_err:
            logger.warning(f"⚠️ Could not verify PDF URL accessibility: {str(url_err)}")
            # Continue anyway - some CDNs may block HEAD requests
        
        # Step 2: Update LarkBase id_card field with the URL
        # This is CRITICAL - the download should only proceed if this succeeds
        lark_synced = False
        lark_error = None
        try:
            from app.services.lark_service import update_employee_id_card
            lark_synced = update_employee_id_card(
                id_number,
                pdf_url,
                source="HR PDF Download"
            )
            if lark_synced:
                logger.info(f"✅ LarkBase id_card updated for employee {id_number}")
            else:
                lark_error = "LarkBase update returned False"
                logger.error(f"❌ LarkBase id_card update failed for employee {id_number}")
        except Exception as lark_e:
            lark_error = str(lark_e)
            logger.error(f"❌ LarkBase id_card update exception for {id_number}: {lark_error}")
        
        # If LarkBase update failed, return failure so frontend doesn't download
        if not lark_synced:
            logger.error(f"❌ LarkBase sync failed for {id_number}. PDF URL: {pdf_url}. Error: {lark_error}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False, 
                    "error": f"PDF uploaded to cloud but LarkBase update failed: {lark_error}",
                    "pdf_url": pdf_url,  # Include URL in case manual recovery is needed
                    "lark_synced": False
                }
            )
        
        # Step 3: Update local database with PDF URL and mark as generated
        success = update_employee(employee_id, {
            "render_url": pdf_url,
            "id_generated": 1,
            "date_last_modified": datetime.now().isoformat()
        })
        
        if not success:
            logger.warning(f"⚠️ Failed to update local database with PDF URL for employee {employee_id}")
        
        # NOTE: Status is NOT changed here. The workflow is:
        # Rendered -> Approved (via "Approve All Rendered" button)
        # Approved -> Sent to POC (via "Send All to POCs" button)
        # Sent to POC -> Completed (manually when POC receives ID cards)
        
        logger.info(f"✅ PDF upload complete for employee {employee_id} - LarkBase synced: {lark_synced}")
        
        # SUCCESS: Both Cloudinary upload and LarkBase update succeeded
        return JSONResponse(content={
            "success": True,
            "pdf_url": pdf_url,
            "lark_synced": lark_synced,
            "message": "PDF uploaded and LarkBase id_card updated successfully"
        })
        
    except Exception as e:
        logger.error(f"❌ Error uploading PDF for employee {employee_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/api/employees/{employee_id}/download-id")
def api_download_id(employee_id: int, hr_session: str = Cookie(None)):
    """
    Download employee ID as PDF
    Note: This is a placeholder - templated.io integration pending
    """
    if not get_session(hr_session):
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    try:
        row = get_employee_by_id(employee_id)

        if not row:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Employee not found"}
            )

        if row.get("status") not in ["Approved", "Completed"]:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "ID not yet approved"}
            )

        # TODO: Integrate with templated.io for dynamic PDF generation
        # For now, return a placeholder response
        return JSONResponse(
            status_code=501,
            content={
                "success": False,
                "error": "PDF generation coming soon. Templated.io integration pending.",
                "employee_data": {
                    "name": row.get("employee_name"),
                    "id_number": row.get("id_number"),
                    "position": row.get("position"),
                    "department": row.get("department"),
                    "email": row.get("email"),
                    "phone": row.get("personal_number")
                }
            }
        )

    except Exception as e:
        logger.error(f"Error downloading ID for employee {employee_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/api/sync-sheets")
def api_sync_sheets(hr_session: str = Cookie(None)):
    """Sync employee data to Google Sheets"""
    if not get_session(hr_session):
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    try:
        # Import Google Sheets service
        from app.services.google_sheets import sync_employees_to_sheets
        
        employees = get_all_employees()
        
        # Attempt to sync
        success = sync_employees_to_sheets(employees)
        
        if success:
            return JSONResponse(content={"success": True, "message": "Synced to Google Sheets"})
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to sync to Google Sheets"}
            )

    except ImportError:
        return JSONResponse(
            status_code=501,
            content={"success": False, "error": "Google Sheets integration not configured"}
        )
    except Exception as e:
        logger.error(f"Error syncing to Google Sheets: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/api/stats")
def api_get_stats(hr_session: str = Cookie(None)):
    """Get dashboard statistics"""
    if not get_session(hr_session):
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    try:
        # Get status breakdown using abstraction layer
        status_counts = get_status_breakdown()
        total = get_employee_count()

        return JSONResponse(content={
            "success": True,
            "stats": {
                "total": total,
                "reviewing": status_counts.get("Reviewing", 0),
                "approved": status_counts.get("Approved", 0),
                "completed": status_counts.get("Completed", 0)
            }
        })

    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


# ============================================
# Approved Export API (Bypasses Screenshot Protection)
# ============================================
@router.post("/api/export-approved")
def export_approved_id(request: Request, hr_session: str = Cookie(None)):
    """
    Approved export endpoint that bypasses screenshot/recording protection.
    
    This endpoint allows HR users to legitimately export ID cards as PDFs
    for official processing. Export is logged and includes watermarks
    for audit trail purposes.
    
    Security: 
    - Requires HR authentication
    - Logs export intent to security audit trail
    - Includes watermark with timestamp and HR user info
    - Only works for Approved/Completed status employees
    """
    # Authentication check
    session = get_session(hr_session)
    if not session:
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    
    hr_username = session.get("username", "unknown")
    
    try:
        # Parse request body
        body = None
        if request.method == "POST":
            # Get JSON or form data
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                import json
                body_bytes = request.body() if hasattr(request, 'body') else b"{}"
                body = json.loads(body_bytes) if body_bytes else {}
        
        employee_ids = body.get("employee_ids", []) if body else []
        export_format = body.get("format", "pdf").lower()
        
        if not employee_ids:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "No employee IDs provided"}
            )
        
        # Validate export format
        if export_format not in ["pdf", "zip"]:
            export_format = "pdf"
        
        # Log export intent to security audit
        from app.database import insert_security_event
        for emp_id in employee_ids:
            insert_security_event(
                event_type="approved_export",
                details=f"HR user {hr_username} approved export of employee ID {emp_id}",
                username=hr_username,
                url=f"/hr/api/export-approved",
            )
        
        # Prepare export data
        employees_to_export = []
        for emp_id in employee_ids:
            try:
                emp = get_employee_by_id(int(emp_id))
                if emp and emp.get("status") in ["Approved", "Completed"]:
                    employees_to_export.append(emp)
            except:
                pass
        
        if not employees_to_export:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "No approved employees found for export"}
            )
        
        # Log successful export
        logger.info(f"[HR EXPORT] User {hr_username} exported {len(employees_to_export)} employee ID(s) - Format: {export_format}")
        
        # Return metadata about export (actual PDF generation handled by frontend)
        return JSONResponse({
            "success": True,
            "message": f"Export approved for {len(employees_to_export)} employee(s)",
            "employee_count": len(employees_to_export),
            "export_format": export_format,
            "exported_by": hr_username,
            "timestamp": datetime.utcnow().isoformat(),
            "employees": [
                {
                    "id": emp.get("id"),
                    "employee_name": emp.get("employee_name"),
                    "id_number": emp.get("id_number"),
                    "status": emp.get("status"),
                    "photo_url": emp.get("nobg_photo_url") or emp.get("photo_url"),
                }
                for emp in employees_to_export
            ],
            "watermark": f"OFFICIAL EXPORT - {hr_username} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        })
        
    except Exception as e:
        logger.error(f"Error in approved export: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Export failed"}
        )


@router.get("/export-help")
def export_help_page(request: Request, hr_session: str = Cookie(None)):
    """
    Help page explaining approved export process.
    Shows how to legitimately export ID cards without screenshot warnings.
    """
    if not get_session(hr_session):
        return RedirectResponse(url="/hr/login", status_code=302)
    
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Approved ID Export</title>
        <link rel="stylesheet" href="/static/styles.css">
        <style>
            .export-help { padding: 2rem; max-width: 800px; margin: 0 auto; }
            .help-section { margin: 2rem 0; padding: 1.5rem; background: #f8f9fa; border-radius: 8px; }
            .help-section h3 { color: #2e7d32; margin-bottom: 1rem; }
            .help-section p { color: #666; line-height: 1.6; }
            .export-button { 
                display: inline-block;
                background: #2e7d32;
                color: white;
                padding: 0.75rem 1.5rem;
                border-radius: 4px;
                text-decoration: none;
                margin-top: 1rem;
            }
            .export-button:hover { background: #1b5e20; }
        </style>
    </head>
    <body>
        <div class="export-help">
            <h1>Approved ID Export</h1>
            
            <div class="help-section">
                <h3>Why am I seeing warning messages?</h3>
                <p>
                    This application includes protection against unauthorized screenshots and screen recording
                    to safeguard sensitive employee information. If you see warnings or content becoming blurred,
                    it may indicate detected screen recording attempts.
                </p>
            </div>
            
            <div class="help-section">
                <h3>How do I export ID cards officially?</h3>
                <p>
                    Use the <strong>Approved Export</strong> feature in the HR Dashboard. This is the authorized
                    method for HR users to download ID cards for official processing. Your exports are logged
                    and watermarked for audit purposes.
                </p>
            </div>
            
            <div class="help-section">
                <h3>What is on the exported PDF?</h3>
                <p>
                    Exported PDFs include:
                    <ul>
                        <li>Employee ID card (front and back)</li>
                        <li>Employee name and ID number</li>
                        <li>Official watermark with export timestamp</li>
                        <li>HR user who performed the export</li>
                    </ul>
                </p>
            </div>
            
            <div class="help-section">
                <h3>Can I print exported PDFs?</h3>
                <p>
                    Yes. Exported PDFs from the Approved Export feature are print-ready. Direct printing from
                    the dashboard may be blocked to prevent circumvention of data protection measures.
                </p>
            </div>
            
            <a href="/hr/dashboard" class="export-button">← Back to Dashboard</a>
        </div>
    </body>
    </html>
    """)

