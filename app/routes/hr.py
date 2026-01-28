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
                "emergency_address": row.get("emergency_address")
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
            "id_nickname": row.get("id_nickname"),
            "id_number": row.get("id_number"),
            "position": row.get("position"),
            "department": row.get("department"),
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
            "emergency_address": row.get("emergency_address")
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

        if row.get("status") != "Reviewing":
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": f"Cannot approve. Current status: {row.get('status')}"}
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

        logger.info(f"Employee {employee_id} approved")
        return JSONResponse(content={"success": True, "message": "Application approved"})

    except Exception as e:
        logger.error(f"Error approving employee {employee_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.delete("/api/employees/{employee_id}")
def api_delete_employee(employee_id: int, hr_session: str = Cookie(None)):
    """Delete an employee application - Protected by org access"""
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

        # Delete the employee
        success = delete_employee(employee_id)
        
        if not success:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to delete employee"}
            )

        logger.info(f"Employee {employee_id} ({employee_name}) deleted")
        return JSONResponse(content={"success": True, "message": f"Application for {employee_name} removed"})

    except Exception as e:
        logger.error(f"Error deleting employee {employee_id}: {str(e)}")
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
    """Mark an employee's ID as completed (after download)"""
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

        if row.get("status") not in ["Approved", "Completed"]:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": f"Cannot mark as complete. Current status: {row.get('status')}"}
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

        logger.info(f"Employee {employee_id} marked as completed")
        return JSONResponse(content={"success": True, "message": "ID marked as completed"})

    except Exception as e:
        logger.error(f"Error completing employee {employee_id}: {str(e)}")
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

