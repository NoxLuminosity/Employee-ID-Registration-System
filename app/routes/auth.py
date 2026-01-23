"""
Authentication Routes - Employee Lark SSO
Handles Lark OAuth authentication for employee portal access.
Separate from HR authentication to maintain clear separation of concerns.
"""
from fastapi import APIRouter, Request, Query, Cookie
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import logging
from pathlib import Path

# Import Lark OAuth service
from app.services.lark_auth_service import (
    get_authorization_url,
    complete_oauth_flow,
    LARK_APP_ID
)

# Import session management
from app.auth import create_session, get_session

router = APIRouter(prefix="/auth")

# Get the directory where this file is located
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Configure logging
logger = logging.getLogger(__name__)

# Check if running on Vercel (serverless) or locally
IS_VERCEL = os.environ.get("VERCEL", "0") == "1" or os.environ.get("VERCEL_ENV") is not None


# ============================================
# Employee Lark Authentication Routes
# ============================================

@router.get("/login", response_class=HTMLResponse)
def employee_login_page(request: Request, employee_session: str = Cookie(None)):
    """
    Employee Login Page - Lark SSO only.
    Redirects to landing page if already authenticated.
    """
    # Check if already logged in
    session = get_session(employee_session)
    if session and session.get("auth_type") == "lark":
        # Redirect to Landing Page, not directly to Employee Form
        return RedirectResponse(url="/", status_code=302)
    
    return templates.TemplateResponse("lark_login.html", {"request": request})


@router.get("/lark/login")
def lark_login(request: Request):
    """
    Initiate Lark OAuth login flow for employees.
    Redirects user to Lark authorization page.
    """
    # Build redirect URI based on current request
    scheme = request.url.scheme
    host = request.headers.get('host', 'localhost:8000')
    
    # Normalize 127.0.0.1 to localhost for Lark compatibility
    if '127.0.0.1' in host:
        host = host.replace('127.0.0.1', 'localhost')
    
    # Use HTTPS in production (Vercel)
    if IS_VERCEL or os.environ.get('VERCEL_ENV') == 'production':
        scheme = 'https'
    
    redirect_uri = f"{scheme}://{host}/auth/lark/callback"
    
    # Override with environment variable if set
    env_redirect_uri = os.environ.get('LARK_EMPLOYEE_REDIRECT_URI')
    if env_redirect_uri:
        redirect_uri = env_redirect_uri
    
    logger.info(f"Initiating Employee Lark OAuth with redirect_uri: {redirect_uri}")
    
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
    Handle Lark OAuth callback for employees.
    Exchanges authorization code for tokens and creates session.
    """
    # Handle authorization denial
    if error:
        logger.warning(f"Employee Lark OAuth error: {error} - {error_description}")
        return templates.TemplateResponse("lark_login.html", {
            "request": request,
            "error": f"Lark login denied: {error_description or error}"
        })
    
    # Validate required parameters
    if not code:
        logger.error("Employee Lark callback missing authorization code")
        return templates.TemplateResponse("lark_login.html", {
            "request": request,
            "error": "Missing authorization code from Lark"
        })
    
    if not state:
        logger.error("Employee Lark callback missing state parameter")
        return templates.TemplateResponse("lark_login.html", {
            "request": request,
            "error": "Missing state parameter (security check failed)"
        })
    
    # Complete OAuth flow
    result = complete_oauth_flow(code, state)
    
    if not result.get("success"):
        error_msg = result.get("error", "Unknown error during Lark authentication")
        logger.error(f"Employee Lark OAuth flow failed: {error_msg}")
        return templates.TemplateResponse("lark_login.html", {
            "request": request,
            "error": f"Lark login failed: {error_msg}"
        })
    
    # Extract user info
    user = result.get("user", {})
    tokens = result.get("tokens", {})
    
    user_name = user.get("name") or user.get("email") or user.get("user_id")
    logger.info(f"Employee Lark OAuth successful for user: {user_name}")
    
    # Create session with Lark data (24 hours for employees)
    session_id = create_session(
        username=user_name,
        hours=24,  # Longer session for employees
        lark_data={
            "user_id": user.get("user_id"),
            "open_id": user.get("open_id"),
            "name": user.get("name"),
            "email": user.get("email"),
            "avatar_url": user.get("avatar_url"),
            "tenant_key": user.get("tenant_key"),
            "employee_no": user.get("employee_no"),  # Employee Number from Lark
            "mobile": user.get("mobile"),  # Personal Number from Lark
        }
    )
    
    # Create redirect response with session cookie
    # Redirect to Landing Page (not directly to Employee Form)
    response = RedirectResponse(url="/", status_code=302)
    
    is_production = IS_VERCEL or os.environ.get('VERCEL_ENV') == 'production'
    response.set_cookie(
        key="employee_session",
        value=session_id,
        httponly=True,
        max_age=86400,  # 24 hours
        samesite="lax",
        secure=is_production,
        path="/"
    )
    
    logger.info(f"Employee Lark user logged in: {user_name}")
    return response


@router.get("/logout")
def employee_logout():
    """Logout employee user"""
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie("employee_session")
    logger.info("Employee logged out")
    return response


@router.get("/me", response_class=JSONResponse)
def get_current_user(employee_session: str = Cookie(None)):
    """
    Get current authenticated user info.
    Used by frontend to prefill form fields.
    """
    session = get_session(employee_session)
    
    if not session:
        return JSONResponse(
            status_code=401,
            content={"authenticated": False, "error": "Not authenticated"}
        )
    
    # Parse Lark name into first/middle/last
    full_name = session.get("lark_name") or session.get("username") or ""
    name_parts = parse_lark_name(full_name)
    
    return JSONResponse(content={
        "authenticated": True,
        "auth_type": session.get("auth_type", "unknown"),
        "user": {
            "user_id": session.get("lark_user_id"),
            "open_id": session.get("lark_open_id"),
            "full_name": full_name,
            "first_name": name_parts.get("first_name", ""),
            "middle_initial": name_parts.get("middle_initial", ""),
            "last_name": name_parts.get("last_name", ""),
            "email": session.get("lark_email"),
            "avatar_url": session.get("lark_avatar"),
            "tenant_key": session.get("lark_tenant"),
            "employee_no": session.get("lark_employee_no"),  # Employee Number from Lark
            "mobile": session.get("lark_mobile"),  # Personal Number from Lark
        }
    })


def parse_lark_name(full_name: str) -> dict:
    """
    Parse a full name into first name, middle initial, and last name.
    Handles various name formats:
    - "John Doe" -> first: John, last: Doe
    - "John M. Doe" -> first: John, middle: M, last: Doe
    - "John Michael Doe" -> first: John, middle: M, last: Doe
    - "John" -> first: John
    """
    if not full_name:
        return {"first_name": "", "middle_initial": "", "last_name": ""}
    
    parts = full_name.strip().split()
    
    if len(parts) == 1:
        # Only first name
        return {
            "first_name": parts[0],
            "middle_initial": "",
            "last_name": ""
        }
    elif len(parts) == 2:
        # First and last name
        return {
            "first_name": parts[0],
            "middle_initial": "",
            "last_name": parts[1]
        }
    else:
        # First, middle(s), and last name
        # Take first part as first name, last part as last name
        # Middle initial from second part
        middle = parts[1]
        # Extract initial (first letter, removing any dots)
        middle_initial = middle.replace(".", "")[0].upper() if middle else ""
        
        return {
            "first_name": parts[0],
            "middle_initial": middle_initial,
            "last_name": parts[-1]
        }
