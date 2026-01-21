"""
HR Routes - From Code 2
Handles HR authentication, dashboard, gallery, and employee management.
Includes background removal functionality for AI-generated photos.
"""
from fastapi import APIRouter, Request, Depends, Cookie
from fastapi.responses import HTMLResponse, JSONResponse, Response, RedirectResponse
from fastapi.templating import Jinja2Templates
import sqlite3
import os
from pathlib import Path
from datetime import datetime
import logging
import json

# Import services for background removal
from app.services.background_removal_service import remove_background_from_url
from app.services.cloudinary_service import upload_bytes_to_cloudinary

# Import authentication
from app.auth import (
    verify_session, 
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
IS_VERCEL = os.environ.get("VERCEL", False)
DB_NAME = "/tmp/database.db" if IS_VERCEL else "database.db"


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


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
    """HR Dashboard page - Protected"""
    session = get_session(hr_session)
    if not session:
        return RedirectResponse(url="/hr/login", status_code=302)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "username": session["username"]
    })


@router.get("/gallery", response_class=HTMLResponse)
def id_gallery(request: Request, hr_session: str = Cookie(None)):
    """ID Gallery page - Protected"""
    session = get_session(hr_session)
    if not session:
        return RedirectResponse(url="/hr/login", status_code=302)
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


@router.get("/api/employees")
def api_get_employees(hr_session: str = Cookie(None)):
    """Get all employees for the dashboard"""
    if not get_session(hr_session):
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, employee_name, id_nickname, id_number, position, department,
                   email, personal_number, photo_path, photo_url, new_photo, new_photo_url,
                   nobg_photo_url, signature_path, signature_url, status, date_last_modified,
                   id_generated, render_url
            FROM employees
            ORDER BY date_last_modified DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()

        employees = []
        for row in rows:
            employees.append({
                "id": row["id"],
                "employee_name": row["employee_name"],
                "id_nickname": row["id_nickname"],
                "id_number": row["id_number"],
                "position": row["position"],
                "department": row["department"],
                "email": row["email"],
                "personal_number": row["personal_number"],
                "photo_path": row["photo_path"],
                "photo_url": row["photo_url"],
                "new_photo": bool(row["new_photo"]),
                "new_photo_url": row["new_photo_url"],
                "nobg_photo_url": row["nobg_photo_url"],
                "signature_path": row["signature_path"],
                "signature_url": row["signature_url"],
                "status": row["status"] or "Reviewing",
                "date_last_modified": row["date_last_modified"],
                "id_generated": bool(row["id_generated"]),
                "render_url": row["render_url"]
            })

        return JSONResponse(content={"success": True, "employees": employees})

    except Exception as e:
        logger.error(f"Error fetching employees: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/api/employees/{employee_id}")
def api_get_employee(employee_id: int, hr_session: str = Cookie(None)):
    """Get a single employee by ID"""
    if not get_session(hr_session):
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, employee_name, id_nickname, id_number, position, department,
                   email, personal_number, photo_path, photo_url, new_photo, new_photo_url,
                   nobg_photo_url, signature_path, signature_url, status, date_last_modified,
                   id_generated, render_url
            FROM employees
            WHERE id = ?
        """, (employee_id,))
        
        row = cursor.fetchone()
        conn.close()

        if not row:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Employee not found"}
            )

        employee = {
            "id": row["id"],
            "employee_name": row["employee_name"],
            "id_nickname": row["id_nickname"],
            "id_number": row["id_number"],
            "position": row["position"],
            "department": row["department"],
            "email": row["email"],
            "personal_number": row["personal_number"],
            "photo_path": row["photo_path"],
            "photo_url": row["photo_url"],
            "new_photo": bool(row["new_photo"]),
            "new_photo_url": row["new_photo_url"],
            "nobg_photo_url": row["nobg_photo_url"],
            "signature_path": row["signature_path"],
            "signature_url": row["signature_url"],
            "status": row["status"] or "Reviewing",
            "date_last_modified": row["date_last_modified"],
            "id_generated": bool(row["id_generated"]),
            "render_url": row["render_url"]
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
    """Approve an employee's ID application"""
    if not get_session(hr_session):
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if employee exists and is in Reviewing status
        cursor.execute("SELECT status FROM employees WHERE id = ?", (employee_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Employee not found"}
            )

        if row["status"] != "Reviewing":
            conn.close()
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": f"Cannot approve. Current status: {row['status']}"}
            )

        # Update status to Approved
        cursor.execute("""
            UPDATE employees 
            SET status = 'Approved', date_last_modified = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), employee_id))

        conn.commit()
        conn.close()

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
    """Delete an employee application"""
    if not get_session(hr_session):
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if employee exists
        cursor.execute("SELECT id, employee_name FROM employees WHERE id = ?", (employee_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Employee not found"}
            )

        employee_name = row["employee_name"]

        # Delete the employee
        cursor.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        conn.commit()
        conn.close()

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
    """Remove background from AI-generated photo and save the result"""
    import traceback
    
    if not get_session(hr_session):
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    
    logger.info(f"=== REMOVE BACKGROUND REQUEST for employee {employee_id} ===")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get the employee's AI photo URL
        cursor.execute("SELECT id_number, new_photo_url, nobg_photo_url FROM employees WHERE id = ?", (employee_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            logger.error(f"Employee {employee_id} not found")
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Employee not found"}
            )

        logger.info(f"Employee found: id_number={row['id_number']}, new_photo_url={row['new_photo_url'][:50] if row['new_photo_url'] else 'None'}...")

        if not row["new_photo_url"]:
            conn.close()
            logger.error(f"No AI photo available for employee {employee_id}")
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "No AI photo available to process"}
            )

        # If already has nobg photo, return it
        if row["nobg_photo_url"]:
            conn.close()
            logger.info(f"Employee {employee_id} already has nobg photo: {row['nobg_photo_url'][:50]}...")
            return JSONResponse(content={
                "success": True, 
                "nobg_photo_url": row["nobg_photo_url"],
                "message": "Background already removed"
            })

        ai_photo_url = row["new_photo_url"]
        safe_id = row["id_number"].replace(' ', '_').replace('/', '-').replace('\\', '-')

        logger.info(f"Starting background removal for employee {employee_id}...")
        logger.info(f"AI Photo URL: {ai_photo_url}")

        # Remove background using remove.bg API
        logger.info("Calling remove_background_from_url...")
        nobg_bytes, error = remove_background_from_url(ai_photo_url)
        
        if not nobg_bytes:
            conn.close()
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
            conn.close()
            logger.error("Cloudinary upload failed")
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to upload processed image"}
            )

        logger.info(f"Uploaded to Cloudinary: {nobg_url}")

        # Update database with nobg URL
        cursor.execute("""
            UPDATE employees 
            SET nobg_photo_url = ?, date_last_modified = ?
            WHERE id = ?
        """, (nobg_url, datetime.now().isoformat(), employee_id))

        conn.commit()
        conn.close()

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
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if employee exists and is Approved
        cursor.execute("SELECT status FROM employees WHERE id = ?", (employee_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Employee not found"}
            )

        if row["status"] not in ["Approved", "Completed"]:
            conn.close()
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": f"Cannot mark as complete. Current status: {row['status']}"}
            )

        # Update status to Completed
        cursor.execute("""
            UPDATE employees 
            SET status = 'Completed', id_generated = 1, date_last_modified = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), employee_id))

        conn.commit()
        conn.close()

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
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, employee_name, id_nickname, id_number, position, department,
                   email, personal_number, photo_url, signature_url, status
            FROM employees
            WHERE id = ?
        """, (employee_id,))
        
        row = cursor.fetchone()
        conn.close()

        if not row:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Employee not found"}
            )

        if row["status"] not in ["Approved", "Completed"]:
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
                    "name": row["employee_name"],
                    "id_number": row["id_number"],
                    "position": row["position"],
                    "department": row["department"],
                    "email": row["email"],
                    "phone": row["personal_number"]
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
        
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, employee_name, id_nickname, id_number, position, department,
                   email, personal_number, photo_url, signature_url, status, 
                   date_last_modified
            FROM employees
        """)
        
        rows = cursor.fetchall()
        conn.close()

        employees = [dict(row) for row in rows]
        
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
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get counts by status
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'Reviewing' THEN 1 ELSE 0 END) as reviewing,
                SUM(CASE WHEN status = 'Approved' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed
            FROM employees
        """)
        
        row = cursor.fetchone()
        conn.close()

        return JSONResponse(content={
            "success": True,
            "stats": {
                "total": row["total"] or 0,
                "reviewing": row["reviewing"] or 0,
                "approved": row["approved"] or 0,
                "completed": row["completed"] or 0
            }
        })

    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )
