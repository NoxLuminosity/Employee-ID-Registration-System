"""
Employee ID Registration System - Main Application
Integrated from Code 1 (Employee Portal) and Code 2 (HR Portal)

Features:
- Employee registration with AI headshot generation
- HR dashboard with authentication
- Background removal for ID card photos
- Google Sheets and Lark Bitable integration
- Mandatory Lark authentication for all access
"""
from fastapi import FastAPI, Request, Cookie
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from app.routes import employee, hr, auth
from app.database import init_db
from app.auth import get_session
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging to show in console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Employee ID Registration System")

# ============================================
# Security Headers Middleware
# ============================================
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    Prevents screenshot/recording tools, clickjacking, MIME sniffing.
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Clickjacking protection - prevent framing in iframes
        response.headers["X-Frame-Options"] = "DENY"
        
        # MIME sniffing protection - enforce content type
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Content Security Policy - strict enforcement
        # Blocks inline scripts (except for legitimate uses), restricts frame sources
        # VERCEL FIX: Added cdnjs.cloudflare.com for jsPDF and html2canvas libraries
        # BARCODE: barcodeapi.org is allowed via https: wildcard in img-src and connect-src
        # QR: quickchart.io added for QR code generation
        # SWAGGER/REDOC: cdn.jsdelivr.net added for FastAPI auto-generated docs
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https: blob:; "
            "connect-src 'self' https://api.cloudinary.com https://api.larksuite.com https://barcodeapi.org https://quickchart.io; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "upgrade-insecure-requests"
        )
        response.headers["Content-Security-Policy"] = csp
        
        # Referrer policy - limit referrer leakage
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy - disable unnecessary browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "accelerometer=(), "
            "gyroscope=(), "
            "magnetometer=()"
        )
        
        # Feature policy (legacy) for older browsers
        response.headers["Feature-Policy"] = (
            "geolocation 'none'; "
            "microphone 'none'; "
            "camera 'none'; "
            "payment 'none'; "
            "usb 'none'"
        )
        
        # XSS protection (legacy header for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Strict transport security (only for production HTTPS)
        if os.environ.get("VERCEL") == "1":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Additional hardening - disable DNS prefetch, prefetch
        response.headers["X-DNS-Prefetch-Control"] = "off"
        
        return response

# Register security middleware FIRST (before all routes)
app.add_middleware(SecurityHeadersMiddleware)

# Get the directory where main.py is located
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Check if running on Vercel (serverless) or locally
IS_VERCEL = os.environ.get("VERCEL", "0") == "1"

# Static files directory (exists in both environments)
static_dir = BASE_DIR / "static"

# Log paths for debugging
logging.info(f"BASE_DIR: {BASE_DIR}")
logging.info(f"Static dir: {static_dir}, exists: {static_dir.exists()}")
logging.info(f"Templates dir: {BASE_DIR / 'templates'}, exists: {(BASE_DIR / 'templates').exists()}")
logging.info(f"IS_VERCEL: {IS_VERCEL}")

# Always initialize DB (uses /tmp on Vercel which is writable)
init_db()

# Global exception handler - ALWAYS return JSON, never HTML
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc), "detail": "Internal server error"}
    )


# ============================================
# Authentication Helper
# ============================================
def check_employee_auth(employee_session: str) -> bool:
    """Check if employee is authenticated via Lark"""
    if not employee_session:
        return False
    session = get_session(employee_session)
    if not session:
        return False
    # Must be Lark authenticated
    return session.get("auth_type") == "lark"


# ============================================
# HTML Page Routes (define BEFORE static mount)
# ============================================

# Root landing page - shows sign-in for unauthenticated users
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request, employee_session: str = Cookie(None)):
    """
    Landing page - shows authentication prompt inline if not authenticated.
    Authenticated users can access Choose Your Path section.
    """
    authenticated = check_employee_auth(employee_session)
    return templates.TemplateResponse("landing.html", {
        "request": request, 
        "authenticated": authenticated
    })


# Logout route - clears session and returns to landing
@app.get("/logout", response_class=RedirectResponse)
async def logout():
    """Logout user - clear session and redirect to landing page"""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="employee_session")
    return response


# Apply route - protected, requires Lark authentication
@app.get("/apply", response_class=HTMLResponse)
async def apply_page(request: Request, employee_session: str = Cookie(None)):
    """Employee ID application form (SPMC) - requires Lark authentication"""
    if not check_employee_auth(employee_session):
        # Not authenticated - redirect to Lark login
        return RedirectResponse(url="/auth/lark/login", status_code=302)
    
    # Get session data for prefilling
    session = get_session(employee_session)
    
    # Parse name for prefilling
    full_name = session.get("lark_name") or session.get("username") or ""
    name_parts = parse_lark_name(full_name)
    
    return templates.TemplateResponse("form.html", {
        "request": request,
        "authenticated": True,
        "prefill": {
            "first_name": name_parts.get("first_name", ""),
            "middle_initial": name_parts.get("middle_initial", ""),
            "last_name": name_parts.get("last_name", ""),
            "email": session.get("lark_email", ""),
            "full_name": full_name,
            "employee_no": session.get("lark_employee_no", ""),  # Employee Number from Lark
            "personal_number": session.get("lark_mobile", ""),  # Personal Number from Lark
        },
        "user": {
            "name": session.get("lark_name"),
            "email": session.get("lark_email"),
            "avatar": session.get("lark_avatar"),
        }
    })


def parse_lark_name(full_name: str) -> dict:
    """Parse a full name into first, middle initial, and last name."""
    if not full_name:
        return {"first_name": "", "middle_initial": "", "last_name": ""}
    
    parts = full_name.strip().split()
    
    if len(parts) == 1:
        return {"first_name": parts[0], "middle_initial": "", "last_name": ""}
    elif len(parts) == 2:
        return {"first_name": parts[0], "middle_initial": "", "last_name": parts[1]}
    else:
        middle = parts[1]
        middle_initial = middle.replace(".", "")[0].upper() if middle else ""
        return {"first_name": parts[0], "middle_initial": middle_initial, "last_name": parts[-1]}


# ============================================
# API Routes (include routers BEFORE static mount)
# ============================================
app.include_router(auth.router)  # Auth routes (/auth/*)
app.include_router(employee.router)  # Employee routes
app.include_router(hr.router)  # HR routes (/hr/*)

# Import and register security routes
from app.routes import security
app.include_router(security.router)  # Security routes (/api/security/*)


# ============================================
# Static Files (mount LAST to avoid catching API routes)
# ============================================
if not IS_VERCEL:
    # Create local uploads directory (only works locally)
    # Vercel's serverless functions have a read-only filesystem except /tmp
    uploads_dir = static_dir / "uploads"
    static_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    # Mount uploads separately for local development
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# Mount static files for CSS/JS - these are bundled with the deployment
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    logging.info("Static files mounted successfully")
else:
    logging.error(f"Static directory does not exist: {static_dir}")
