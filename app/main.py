"""
Employee ID Registration System - Main Application
Integrated from Code 1 (Employee Portal) and Code 2 (HR Portal)

Features:
- Employee registration with AI headshot generation
- HR dashboard with authentication
- Background removal for ID card photos
- Google Sheets and Lark Bitable integration
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from app.routes import employee, hr
from app.database import init_db
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

# Global exception handler - ALWAYS return JSON, never HTML
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc), "detail": "Internal server error"}
    )

# Get the directory where main.py is located
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Check if running on Vercel (serverless) or locally
IS_VERCEL = os.environ.get("VERCEL", False)

# Static files directory (exists in both environments)
static_dir = BASE_DIR / "static"

# Always initialize DB (uses /tmp on Vercel which is writable)
init_db()

if not IS_VERCEL:
    # Create local uploads directory (only works locally)
    # Vercel's serverless functions have a read-only filesystem except /tmp
    uploads_dir = static_dir / "uploads"
    static_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    # Mount uploads separately for local development
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# Always mount static files - CSS/JS are read-only and can be served in both environments
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Landing page route
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Landing page with options for Apply or HR Dashboard"""
    return templates.TemplateResponse("landing.html", {"request": request})


# Apply route - redirect to employee form
@app.get("/apply", response_class=HTMLResponse)
async def apply_page(request: Request):
    """Employee ID application form"""
    return templates.TemplateResponse("form.html", {"request": request})


# Routes
app.include_router(employee.router)
app.include_router(hr.router)
