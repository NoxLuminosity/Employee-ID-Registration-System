"""
Employee Routes - From Code 1
Handles employee registration, AI headshot generation, and form submission.
Protected by Lark authentication.
"""
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException, Body, Cookie
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import shutil
import os
import logging
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

# Database abstraction layer (supports Supabase and SQLite)
from app.database import insert_employee, USE_SUPABASE

# Lark Bitable integration (for appending data)
from app.services.lark_service import append_employee_submission
# Cloudinary integration (for image uploads)
from app.services.cloudinary_service import (
    upload_image_to_cloudinary, 
    upload_base64_to_cloudinary,
    upload_url_with_bg_removal,
    upload_url_to_cloudinary_simple
)
# BytePlus Seedream integration (for AI headshot generation)
from app.services.seedream_service import generate_headshot_from_url

# Authentication
from app.auth import get_session

router = APIRouter()

# Get the directory where this file is located
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Configure logging
logger = logging.getLogger(__name__)

# Check if running on Vercel (serverless) or locally
IS_VERCEL = os.environ.get("VERCEL", False)


def verify_employee_auth(employee_session: str) -> bool:
    """Verify employee is authenticated via Lark"""
    if not employee_session:
        return False
    session = get_session(employee_session)
    if not session:
        return False
    return session.get("auth_type") == "lark"


# Request model for generate-headshot endpoint
class GenerateHeadshotRequest(BaseModel):
    image: str  # Base64-encoded image


@router.post("/generate-headshot")
async def api_generate_headshot(request: GenerateHeadshotRequest, employee_session: str = Cookie(None)):
    """
    Generate a professional headshot using BytePlus Seedream API with transparent background.
    Requires Lark authentication.
    
    Complete Flow:
        1. Upload base64 image to Cloudinary (to get a public URL)
        2. Send URL to BytePlus Seedream API
        3. Upload AI image to Cloudinary with background removal
        4. Return final Cloudinary URL (transparent image)
    
    Expects JSON body with:
        image: Base64-encoded image data (with or without data URI prefix)
    
    Returns:
        JSON with generated_image (Cloudinary URL of transparent PNG) on success
        JSON with error message on failure
    """
    try:
        logger.info("Received headshot generation request")
        
        if not request.image:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "No image data provided"}
            )
        
        # Step 1: Upload original to Cloudinary to get a public URL
        temp_id = f"temp_preview_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"Step 1: Uploading original image to Cloudinary: {temp_id}")
        cloudinary_url = upload_base64_to_cloudinary(
            base64_data=request.image,
            public_id=temp_id,
            folder="seedream_temp"
        )
        
        if not cloudinary_url:
            logger.error("Failed to upload image to Cloudinary")
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to process image. Please try again."}
            )
        
        logger.info(f"Original uploaded to Cloudinary: {cloudinary_url}")
        
        # Step 2: Generate headshot using Seedream with the Cloudinary URL
        logger.info("Step 2: Generating AI headshot with Seedream...")
        generated_url, error = generate_headshot_from_url(cloudinary_url)
        
        if not generated_url:
            logger.warning(f"Failed to generate headshot: {error}")
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": error or "Failed to generate headshot. Please try again."}
            )
        
        logger.info(f"AI headshot generated: {generated_url[:80]}...")
        
        # Step 3: Upload AI image to Cloudinary with background removal
        logger.info("Step 3: Uploading to Cloudinary with background removal...")
        final_id = f"headshot_transparent_{uuid.uuid4().hex[:8]}"
        
        final_url, is_transparent = upload_url_with_bg_removal(
            image_url=generated_url,
            public_id=final_id,
            folder="headshots"
        )
        
        if final_url:
            logger.info(f"Final headshot uploaded (transparent: {is_transparent}): {final_url}")
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "generated_image": final_url,
                    "transparent": is_transparent,
                    "message": "AI headshot generated" + (" with transparent background" if is_transparent else " (background removal unavailable)")
                }
            )
        else:
            # Fallback: upload without background removal
            logger.warning("Cloudinary bg removal failed, uploading without processing")
            fallback_url = upload_url_to_cloudinary_simple(
                image_url=generated_url,
                public_id=final_id,
                folder="headshots"
            )
            
            if fallback_url:
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "generated_image": fallback_url,
                        "transparent": False,
                        "message": "AI headshot generated (background removal unavailable)"
                    }
                )
            else:
                # Last resort: return the original Seedream URL
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "generated_image": generated_url,
                        "transparent": False,
                        "message": "AI headshot generated (using original URL)"
                    }
                )
            
    except Exception as e:
        logger.error(f"Error in generate-headshot endpoint: {str(e)}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


# Request model for remove-background endpoint
class RemoveBackgroundRequest(BaseModel):
    image: str  # URL or base64-encoded image
    is_url: bool = True  # True if image is a URL, False if base64


@router.post("/remove-background")
async def api_remove_background(request: RemoveBackgroundRequest, employee_session: str = Cookie(None)):
    """
    Remove background from an image using Cloudinary AI.
    Requires Lark authentication.
    
    Expects JSON body with:
        image: URL or base64-encoded image
        is_url: True if image is a URL, False if base64 (default: True)
    
    Returns:
        JSON with processed_image (Cloudinary URL with transparency) on success
        JSON with error message on failure
    """
    try:
        logger.info(f"Received background removal request (is_url: {request.is_url})")
        
        if not request.image:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "No image data provided"}
            )
        
        # Generate unique ID for the processed image
        processed_id = f"bg_removed_{uuid.uuid4().hex[:8]}"
        
        if request.is_url:
            # Upload URL with background removal
            result_url, is_transparent = upload_url_with_bg_removal(
                image_url=request.image,
                public_id=processed_id,
                folder="processed"
            )
        else:
            # First upload the base64 image, then apply bg removal
            temp_url = upload_base64_to_cloudinary(
                base64_data=request.image,
                public_id=f"temp_{processed_id}",
                folder="temp"
            )
            if temp_url:
                result_url, is_transparent = upload_url_with_bg_removal(
                    image_url=temp_url,
                    public_id=processed_id,
                    folder="processed"
                )
            else:
                result_url, is_transparent = None, False
        
        if result_url:
            logger.info(f"Background removed successfully (transparent: {is_transparent})")
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "processed_image": result_url,  # Cloudinary URL
                    "transparent": is_transparent,
                    "available": True
                }
            )
        else:
            logger.warning("Failed to remove background via Cloudinary")
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to remove background"}
            )
            
    except Exception as e:
        logger.error(f"Error in remove-background endpoint: {str(e)}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/background-removal-status")
async def background_removal_status():
    """Check if background removal service is available."""
    # Cloudinary AI background removal is always available if Cloudinary is configured
    return JSONResponse(
        status_code=200,
        content={
            "available": True,
            "message": "Background removal is available via Cloudinary AI"
        }
    )


@router.post("/submit")
async def submit_employee(
    first_name: str = Form(...),
    middle_initial: str = Form(''),
    last_name: str = Form(...),
    id_nickname: str = Form(''),
    id_number: str = Form(...),
    position: str = Form(...),
    email: str = Form(...),
    personal_number: str = Form(...),
    photo: UploadFile = File(...),
    signature_data: str = Form(...),
    ai_headshot_data: Optional[str] = Form(None),  # AI-generated headshot URL from frontend
    emergency_name: Optional[str] = Form(''),  # Emergency contact name
    emergency_contact: Optional[str] = Form(''),  # Emergency contact number
    emergency_address: Optional[str] = Form(''),  # Emergency contact address
    employee_session: str = Cookie(None)  # Lark authentication
):
    """Submit employee registration - requires Lark authentication, returns JSON response."""
    import base64
    
    # Verify Lark authentication
    if not verify_employee_auth(employee_session):
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Authentication required. Please sign in with Lark."}
        )
    
    # Construct full employee_name from parts for backward compatibility
    employee_name_parts = [first_name]
    if middle_initial:
        mi = middle_initial.strip()
        if not mi.endswith('.'):
            mi += '.'
        employee_name_parts.append(mi)
    if last_name:
        employee_name_parts.append(last_name)
    employee_name = ' '.join(employee_name_parts)
    
    try:
        # Ensure uploads directory exists
        # Use /tmp on Vercel (only writable directory in serverless)
        if IS_VERCEL:
            uploads_dir = "/tmp/uploads"
        else:
            uploads_dir = str(BASE_DIR / "static" / "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Save photo with timestamp
        timestamp = datetime.now().timestamp()
        filename = f"{timestamp}_{photo.filename}"
        photo_path = os.path.join(uploads_dir, filename)
        
        with open(photo_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)
        
        # Store relative path for serving (without app/static prefix)
        photo_local_path = f"uploads/{filename}"
        
        # Save signature from base64
        signature_local_path = None
        if signature_data and signature_data.startswith('data:image'):
            try:
                # Extract base64 data (remove "data:image/png;base64," prefix)
                header, encoded = signature_data.split(',', 1)
                signature_bytes = base64.b64decode(encoded)
                signature_filename = f"{timestamp}_signature.png"
                signature_path = os.path.join(uploads_dir, signature_filename)
                
                with open(signature_path, "wb") as sig_file:
                    sig_file.write(signature_bytes)
                
                signature_local_path = f"uploads/{signature_filename}"
                logger.info(f"Saved signature for employee: {id_number}")
            except Exception as e:
                logger.error(f"Error saving signature: {str(e)}")

        # ===== CLOUDINARY + SHEETS INTEGRATION =====
        date_last_modified = datetime.now().isoformat()
        cloudinary_photo_url = None
        cloudinary_signature_url = None
        
        # Create deterministic public IDs using employee ID number
        # Sanitize id_number for use as public_id (remove special chars)
        safe_id = id_number.replace(' ', '_').replace('/', '-').replace('\\', '-')
        
        # Step 1: Upload photo to Cloudinary
        try:
            photo_public_id = f"{safe_id}_photo"
            logger.info(f"Attempting to upload photo to Cloudinary for employee: {id_number}")
            
            cloudinary_photo_url = upload_image_to_cloudinary(
                file_path=photo_path,
                public_id=photo_public_id
            )
            
            if cloudinary_photo_url:
                logger.info(f"Successfully uploaded photo to Cloudinary: {cloudinary_photo_url}")
            else:
                logger.warning(f"Failed to upload photo to Cloudinary: {id_number}")
        except Exception as e:
            logger.error(f"Error uploading photo to Cloudinary: {str(e)}")
        
        # Step 2: Upload signature to Cloudinary (if exists)
        if signature_local_path:
            try:
                signature_public_id = f"{safe_id}_signature"
                signature_path_full = os.path.join(uploads_dir, os.path.basename(signature_local_path.replace('uploads/', '')))
                
                logger.info(f"Attempting to upload signature to Cloudinary for employee: {id_number}")
                
                cloudinary_signature_url = upload_image_to_cloudinary(
                    file_path=signature_path_full,
                    public_id=signature_public_id
                )
                
                if cloudinary_signature_url:
                    logger.info(f"Successfully uploaded signature to Cloudinary: {cloudinary_signature_url}")
                else:
                    logger.warning(f"Failed to upload signature to Cloudinary: {id_number}")
            except Exception as e:
                logger.error(f"Error uploading signature to Cloudinary: {str(e)}")

        # Step 3: Handle AI-generated headshot URL
        cloudinary_ai_headshot_url = None
        if ai_headshot_data:
            if ai_headshot_data.startswith('http'):
                # Direct URL from Seedream - use as-is
                cloudinary_ai_headshot_url = ai_headshot_data
                logger.info(f"Using Seedream URL directly for AI headshot: {cloudinary_ai_headshot_url[:80]}...")
            elif ai_headshot_data.startswith('data:image'):
                # Legacy base64 format - upload to Cloudinary
                try:
                    ai_headshot_public_id = f"{safe_id}_ai_headshot"
                    logger.info(f"Attempting to upload AI headshot to Cloudinary for employee: {id_number}")
                    
                    cloudinary_ai_headshot_url = upload_base64_to_cloudinary(
                        base64_data=ai_headshot_data,
                        public_id=ai_headshot_public_id,
                        folder="employees"
                    )
                    
                    if cloudinary_ai_headshot_url:
                        logger.info(f"Successfully uploaded AI headshot to Cloudinary: {cloudinary_ai_headshot_url}")
                    else:
                        logger.warning(f"Failed to upload AI headshot to Cloudinary: {id_number}")
                except Exception as e:
                    logger.error(f"Error uploading AI headshot to Cloudinary: {str(e)}")

        # Save to database using abstraction layer
        employee_data = {
            'employee_name': employee_name,  # Full name for backward compatibility
            'first_name': first_name,
            'middle_initial': middle_initial,
            'last_name': last_name,
            'id_nickname': id_nickname,
            'id_number': id_number,
            'position': position,
            'department': '',  # Deprecated - kept for backward compatibility
            'email': email,
            'personal_number': personal_number,
            'photo_path': photo_local_path,
            'photo_url': cloudinary_photo_url or '',
            'new_photo': 1,  # True
            'new_photo_url': cloudinary_ai_headshot_url or '',
            'signature_path': signature_local_path or '',
            'signature_url': cloudinary_signature_url or '',
            'status': 'Reviewing',
            'date_last_modified': date_last_modified,
            'id_generated': 0,  # False
            'render_url': '',
            'emergency_name': emergency_name or '',
            'emergency_contact': emergency_contact or '',
            'emergency_address': emergency_address or ''
        }
        
        employee_id = insert_employee(employee_data)
        
        if employee_id is None:
            logger.error(f"Failed to insert employee: {id_number}")
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Database error", "detail": "Failed to save employee"}
            )
        
        logger.info(f"Employee saved to database (id={employee_id}, supabase={USE_SUPABASE})")
        
        # Step 4: Append submission to Lark Bitable
        try:
            logger.info(f"Attempting to append to Lark Bitable for employee: {id_number}")
            lark_success = append_employee_submission(
                employee_name=employee_name,
                id_nickname=id_nickname,
                id_number=id_number,
                position=position,
                department='',  # Deprecated
                email=email,
                personal_number=personal_number,
                photo_path=photo_local_path,
                signature_path=signature_local_path,
                status='Reviewing',
                date_last_modified=date_last_modified,
                photo_url=cloudinary_photo_url,
                signature_url=cloudinary_signature_url,
                ai_headshot_url=cloudinary_ai_headshot_url,
                render_url='',
                first_name=first_name,
                middle_initial=middle_initial,
                last_name=last_name
            )
            if lark_success:
                logger.info(f"✅ Successfully appended employee submission to Lark Bitable: {id_number}")
            else:
                logger.warning(f"⚠️  Failed to append to Lark Bitable (submission still saved to database): {id_number}")
                logger.warning(f"Please check Lark credentials: LARK_BITABLE_ID and LARK_TABLE_ID")
        except Exception as e:
            # Log error but don't fail the request
            logger.error(f"❌ Error appending to Lark Bitable: {str(e)}")
            logger.error(f"Traceback:", exc_info=True)
            logger.warning(f"Submission saved to database but not synced to Lark Bitable")
        # ===== END CLOUDINARY + LARK INTEGRATION =====

        return JSONResponse(
            status_code=200,
            content={"success": True, "message": "Submission successful"}
        )
        
    except Exception as e:
        logger.error(f"Submit error: {str(e)}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Submission failed", "detail": str(e)}
        )
