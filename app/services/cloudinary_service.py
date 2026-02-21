"""
Cloudinary Image Upload Service
Handles uploading images to Cloudinary for the Employee ID Registration System.

Authentication: Uses environment variables (no files required).
This is production-safe for Vercel serverless functions.

Includes Cloudinary AI background removal as an alternative to rembg.
Includes rollback support for ACID transaction management.
"""
import os
import logging
import base64
import urllib.request
from typing import Optional, Tuple, List

import cloudinary
import cloudinary.uploader

# Configure logging
logger = logging.getLogger(__name__)

# Track if Cloudinary has been configured
_cloudinary_configured = False


def configure_cloudinary() -> bool:
    """
    Configure Cloudinary using environment variables.
    
    Required env vars:
        CLOUDINARY_CLOUD_NAME
        CLOUDINARY_API_KEY
        CLOUDINARY_API_SECRET
    
    Returns True if configured successfully, False otherwise.
    """
    global _cloudinary_configured
    
    if _cloudinary_configured:
        return True
    
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
    api_key = os.environ.get('CLOUDINARY_API_KEY')
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')
    
    if not cloud_name:
        logger.error("CLOUDINARY_CLOUD_NAME environment variable not set")
        return False
    if not api_key:
        logger.error("CLOUDINARY_API_KEY environment variable not set")
        return False
    if not api_secret:
        logger.error("CLOUDINARY_API_SECRET environment variable not set")
        return False
    
    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True
    )
    
    _cloudinary_configured = True
    logger.info(f"Cloudinary configured successfully (cloud: {cloud_name})")
    return True


def upload_image_to_cloudinary(
    file_path: str,
    public_id: str,
    folder: Optional[str] = None
) -> Optional[str]:
    """
    Upload an image file to Cloudinary and return the secure URL.
    
    Args:
        file_path: Path to the local image file to upload
        public_id: Unique identifier for the image (e.g., "EMP001_photo")
        folder: Optional folder name in Cloudinary (defaults to CLOUDINARY_FOLDER env var or "employees")
    
    Returns:
        Secure HTTPS URL if successful, None otherwise
    """
    try:
        # Ensure Cloudinary is configured
        if not configure_cloudinary():
            logger.warning("Cloudinary not configured. Skipping image upload.")
            return None
        
        # Validate file exists
        if not os.path.exists(file_path):
            logger.error(f"Local file not found: {file_path}")
            return None
        
        # Use folder from parameter, env var, or default
        if folder is None:
            folder = os.environ.get('CLOUDINARY_FOLDER', 'employees')
        
        # Full public_id includes folder
        full_public_id = f"{folder}/{public_id}"
        
        logger.info(f"Upload started: {public_id} to Cloudinary folder '{folder}'")
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            file_path,
            public_id=full_public_id,
            overwrite=True,  # Replace if exists (same employee re-submitting)
            resource_type="image"
        )
        
        secure_url = result.get('secure_url')
        
        if secure_url:
            logger.info(f"Upload successful: {public_id} -> {secure_url}")
            return secure_url
        else:
            logger.error(f"Upload failed: No secure_url in response for {public_id}")
            return None
            
    except cloudinary.exceptions.Error as e:
        logger.error(f"Cloudinary API error uploading {public_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Upload failed for {public_id}: {str(e)}")
        return None


def upload_base64_to_cloudinary(
    base64_data: str,
    public_id: str,
    folder: Optional[str] = None
) -> Optional[str]:
    """
    Upload a base64-encoded image to Cloudinary and return the secure URL.
    
    Args:
        base64_data: Base64-encoded image data (with or without data URI prefix)
        public_id: Unique identifier for the image
        folder: Optional folder name in Cloudinary
    
    Returns:
        Secure HTTPS URL if successful, None otherwise
    """
    try:
        # Ensure Cloudinary is configured
        if not configure_cloudinary():
            logger.warning("Cloudinary not configured. Skipping image upload.")
            return None
        
        # Ensure data URI prefix exists for Cloudinary
        if not base64_data.startswith('data:'):
            base64_data = f"data:image/png;base64,{base64_data}"
        
        # Use folder from parameter, env var, or default
        if folder is None:
            folder = os.environ.get('CLOUDINARY_FOLDER', 'employees')
        
        # Full public_id includes folder
        full_public_id = f"{folder}/{public_id}"
        
        logger.info(f"Upload base64 started: {public_id} to Cloudinary folder '{folder}'")
        
        # Upload to Cloudinary directly from base64
        result = cloudinary.uploader.upload(
            base64_data,
            public_id=full_public_id,
            overwrite=True,
            resource_type="image"
        )
        
        secure_url = result.get('secure_url')
        
        if secure_url:
            logger.info(f"Base64 upload successful: {public_id} -> {secure_url}")
            return secure_url
        else:
            logger.error(f"Base64 upload failed: No secure_url in response for {public_id}")
            return None
            
    except cloudinary.exceptions.Error as e:
        logger.error(f"Cloudinary API error uploading base64 {public_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Base64 upload failed for {public_id}: {str(e)}")
        return None


def upload_url_with_bg_removal(
    image_url: str,
    public_id: str,
    folder: Optional[str] = None
) -> Tuple[Optional[str], bool]:
    """
    Download image from URL, upload to Cloudinary with background removal.
    Uses Cloudinary's AI background removal transformation.
    
    Args:
        image_url: URL of the image to process
        public_id: Unique identifier for the image
        folder: Optional folder name in Cloudinary
    
    Returns:
        Tuple of (secure_url, is_transparent) where is_transparent indicates
        if background removal was successful
    """
    try:
        # Ensure Cloudinary is configured
        if not configure_cloudinary():
            logger.warning("Cloudinary not configured. Skipping upload with bg removal.")
            return None, False
        
        # Use folder from parameter, env var, or default
        if folder is None:
            folder = os.environ.get('CLOUDINARY_FOLDER', 'employees')
        
        # Full public_id includes folder
        full_public_id = f"{folder}/{public_id}"
        
        logger.info(f"Upload with BG removal started: {public_id} from URL")
        
        # Upload from URL with background removal transformation
        # This uses Cloudinary's AI background removal add-on
        result = cloudinary.uploader.upload(
            image_url,
            public_id=full_public_id,
            overwrite=True,
            resource_type="image",
            format="png",  # PNG supports transparency
            background_removal="cloudinary_ai"  # Use Cloudinary AI for bg removal
        )
        
        secure_url = result.get('secure_url')
        
        if secure_url:
            logger.info(f"Upload with BG removal successful: {public_id} -> {secure_url}")
            return secure_url, True
        else:
            logger.error(f"Upload with BG removal failed: No secure_url for {public_id}")
            return None, False
            
    except cloudinary.exceptions.Error as e:
        error_str = str(e)
        logger.warning(f"Cloudinary BG removal failed: {error_str}")
        
        # Fallback: Try upload without background removal
        if "background_removal" in error_str.lower() or "add-on" in error_str.lower():
            logger.info("Attempting fallback upload without background removal...")
            return upload_url_to_cloudinary_simple(image_url, public_id, folder), False
        
        return None, False
    except Exception as e:
        logger.error(f"Upload with BG removal failed for {public_id}: {str(e)}")
        return None, False


def upload_url_to_cloudinary_simple(
    image_url: str,
    public_id: str,
    folder: Optional[str] = None
) -> Optional[str]:
    """
    Upload an image from URL to Cloudinary without any transformations.
    
    Args:
        image_url: URL of the image to upload
        public_id: Unique identifier for the image
        folder: Optional folder name in Cloudinary
    
    Returns:
        Secure HTTPS URL if successful, None otherwise
    """
    try:
        # Ensure Cloudinary is configured
        if not configure_cloudinary():
            logger.warning("Cloudinary not configured. Skipping simple URL upload.")
            return None
        
        # Use folder from parameter, env var, or default
        if folder is None:
            folder = os.environ.get('CLOUDINARY_FOLDER', 'employees')
        
        # Full public_id includes folder
        full_public_id = f"{folder}/{public_id}"
        
        logger.info(f"Simple URL upload started: {public_id}")
        
        # Upload from URL without transformations
        result = cloudinary.uploader.upload(
            image_url,
            public_id=full_public_id,
            overwrite=True,
            resource_type="image"
        )
        
        secure_url = result.get('secure_url')
        
        if secure_url:
            logger.info(f"Simple URL upload successful: {public_id} -> {secure_url}")
            return secure_url
        else:
            logger.error(f"Simple URL upload failed: No secure_url for {public_id}")
            return None
            
    except Exception as e:
        logger.error(f"Simple URL upload failed for {public_id}: {str(e)}")
        return None


def upload_bytes_to_cloudinary(
    image_bytes: bytes,
    public_id: str,
    folder: Optional[str] = None
) -> Optional[str]:
    """
    Upload raw image bytes to Cloudinary.
    
    Args:
        image_bytes: Raw image bytes
        public_id: Unique identifier for the image
        folder: Optional folder name in Cloudinary
    
    Returns:
        Secure HTTPS URL if successful, None otherwise
    """
    try:
        # Ensure Cloudinary is configured
        if not configure_cloudinary():
            logger.warning("Cloudinary not configured. Skipping bytes upload.")
            return None
        
        # Use folder from parameter, env var, or default
        if folder is None:
            folder = os.environ.get('CLOUDINARY_FOLDER', 'employees')
        
        # Full public_id includes folder
        full_public_id = f"{folder}/{public_id}"
        
        logger.info(f"Bytes upload started: {public_id} ({len(image_bytes)} bytes)")
        
        # Convert bytes to base64 data URI
        base64_data = base64.b64encode(image_bytes).decode('utf-8')
        data_uri = f"data:image/png;base64,{base64_data}"
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            data_uri,
            public_id=full_public_id,
            overwrite=True,
            resource_type="image"
        )
        
        secure_url = result.get('secure_url')
        
        if secure_url:
            logger.info(f"Bytes upload successful: {public_id} -> {secure_url}")
            return secure_url
        else:
            logger.error(f"Bytes upload failed: No secure_url for {public_id}")
            return None
            
    except Exception as e:
        logger.error(f"Bytes upload failed for {public_id}: {str(e)}")
        return None


def upload_card_image_png(
    image_bytes: bytes,
    public_id: str,
    folder: Optional[str] = None
) -> Optional[str]:
    """
    Upload a high-quality PNG card image to Cloudinary for direct bot message delivery.
    
    Unlike PDF-based uploads, this stores the image natively as PNG in Cloudinary's
    image namespace, avoiding the PDF→PNG conversion quality loss.
    
    Optimized for HR-quality output:
    - Lossless PNG format (no JPEG compression artifacts)
    - No format conversion or re-encoding
    - Direct delivery URL without on-the-fly transformations
    
    Args:
        image_bytes: Raw PNG image bytes (high-resolution, lossless)
        public_id: Unique identifier (e.g., "ID_EMP001_front")
        folder: Cloudinary folder (defaults to 'id_card_images')
    
    Returns:
        Secure HTTPS URL if successful, None otherwise
    """
    try:
        if not configure_cloudinary():
            logger.warning("Cloudinary not configured. Skipping card image upload.")
            return None
        
        if folder is None:
            folder = 'id_card_images'
        
        full_public_id = f"{folder}/{public_id}"
        
        file_size_mb = len(image_bytes) / (1024 * 1024)
        logger.info(f"Card image PNG upload: {public_id} ({len(image_bytes)} bytes / {file_size_mb:.2f} MB)")
        
        if file_size_mb > 10:
            logger.error(f"Card image too large: {file_size_mb:.2f} MB (limit: 10 MB)")
            return None
        
        # Convert bytes to base64 data URI
        base64_data = base64.b64encode(image_bytes).decode('utf-8')
        data_uri = f"data:image/png;base64,{base64_data}"
        
        # Upload as native image (PNG) — no format conversion
        result = cloudinary.uploader.upload(
            data_uri,
            public_id=full_public_id,
            overwrite=True,
            resource_type="image",
            format="png",
            type="upload",
            access_mode="public",
            # Preserve quality — no auto-optimization
            quality="auto:best"
        )
        
        secure_url = result.get('secure_url')
        
        if secure_url:
            logger.info(f"Card image PNG uploaded: {public_id} -> {secure_url}")
            return secure_url
        else:
            logger.error(f"Card image PNG upload failed: No secure_url for {public_id}")
            return None
            
    except cloudinary.exceptions.Error as e:
        logger.error(f"Cloudinary API error uploading card image {public_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Card image PNG upload failed for {public_id}: {str(e)}")
        return None


def upload_pdf_to_cloudinary(
    pdf_bytes: bytes,
    public_id: str,
    folder: Optional[str] = None
) -> Optional[str]:
    """
    Upload a PDF file to Cloudinary and return the secure URL.
    
    Args:
        pdf_bytes: Raw PDF bytes
        public_id: Unique identifier for the PDF (e.g., "ID_EMP001")
        folder: Optional folder name in Cloudinary (defaults to 'id_cards')
    
    Returns:
        Secure HTTPS URL if successful, None otherwise
    """
    try:
        # Ensure Cloudinary is configured
        if not configure_cloudinary():
            logger.warning("Cloudinary not configured. Skipping PDF upload.")
            return None
        
        # Use folder from parameter or default to 'id_cards'
        if folder is None:
            folder = os.environ.get('CLOUDINARY_PDF_FOLDER', 'id_cards')
        
        # Full public_id includes folder
        full_public_id = f"{folder}/{public_id}"
        
        # Check file size - Cloudinary free tier limit is 10MB
        file_size_mb = len(pdf_bytes) / (1024 * 1024)
        logger.info(f"PDF upload started: {public_id} ({len(pdf_bytes)} bytes / {file_size_mb:.2f} MB)")
        
        if file_size_mb > 10:
            logger.error(f"PDF too large: {file_size_mb:.2f} MB (Cloudinary limit: 10 MB)")
            return None
        
        # Convert bytes to base64 data URI for PDF
        base64_data = base64.b64encode(pdf_bytes).decode('utf-8')
        data_uri = f"data:application/pdf;base64,{base64_data}"
        
        # Upload to Cloudinary as raw resource type for PDFs
        # IMPORTANT: Set access_mode to "public" to ensure URL is accessible without authentication
        result = cloudinary.uploader.upload(
            data_uri,
            public_id=full_public_id,
            overwrite=True,
            resource_type="raw",  # Use 'raw' for non-image files like PDFs
            format="pdf",
            type="upload",  # Ensure it's a standard upload (publicly accessible)
            access_mode="public"  # Make the file publicly accessible
        )
        
        secure_url = result.get('secure_url')
        
        if secure_url:
            logger.info(f"PDF upload successful: {public_id} -> {secure_url}")
            return secure_url
        else:
            logger.error(f"PDF upload failed: No secure_url for {public_id}")
            return None
            
    except cloudinary.exceptions.Error as e:
        error_msg = str(e)
        logger.error(f"Cloudinary API error uploading PDF {public_id}: {error_msg}")
        # Re-raise with specific message for file size errors
        if "File size too large" in error_msg:
            logger.error("❌ File exceeds Cloudinary 10MB limit. Reduce PDF quality or page count.")
        return None
    except Exception as e:
        logger.error(f"PDF upload failed for {public_id}: {str(e)}")
        return None


def upload_pdf_image_preview(
    pdf_bytes: bytes,
    public_id: str,
    folder: Optional[str] = None
) -> Optional[str]:
    """
    Upload PDF to Cloudinary as image type for multi-page preview.
    
    Stores the PDF in Cloudinary's image namespace WITHOUT format conversion,
    preserving all pages. Individual pages can be accessed on-the-fly via
    URL transformations (pg_N, f_jpg).
    
    Example delivery URLs after upload:
    - Page 1 as JPG: .../image/upload/f_jpg/folder/file.pdf
    - Page 2 as JPG: .../image/upload/pg_2,f_jpg/folder/file.pdf
    
    Args:
        pdf_bytes: Raw PDF bytes (same as used for PDF upload)
        public_id: Same public_id used for the raw PDF upload
        folder: Optional folder name (defaults to 'id_cards')
    
    Returns:
        Secure HTTPS URL of the image resource, or None on failure
    """
    try:
        if not configure_cloudinary():
            logger.warning("Cloudinary not configured. Skipping image preview upload.")
            return None
        
        if folder is None:
            folder = os.environ.get('CLOUDINARY_PDF_FOLDER', 'id_cards')
        
        full_public_id = f"{folder}/{public_id}"
        
        logger.info(f"Uploading PDF as image resource: {public_id}")
        
        base64_data = base64.b64encode(pdf_bytes).decode('utf-8')
        data_uri = f"data:application/pdf;base64,{base64_data}"
        
        result = cloudinary.uploader.upload(
            data_uri,
            public_id=full_public_id,
            overwrite=True,
            resource_type="image",
            type="upload",
            access_mode="public"
        )
        
        secure_url = result.get('secure_url')
        
        if secure_url:
            logger.info(f"PDF image resource uploaded: {public_id} -> {secure_url}")
            return secure_url
        else:
            logger.error(f"PDF image resource upload failed: No secure_url for {public_id}")
            return None
            
    except cloudinary.exceptions.Error as e:
        logger.error(f"Cloudinary API error uploading image resource {public_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"PDF image resource upload failed for {public_id}: {str(e)}")
        return None


# =============================================================================
# Rollback Utilities for ACID Transaction Support
# =============================================================================

def delete_from_cloudinary(secure_url: str) -> bool:
    """
    Delete an asset from Cloudinary by its secure URL.
    Used as a rollback action in TransactionManager.

    Extracts the public_id from the URL and destroys the resource.

    Args:
        secure_url: The Cloudinary secure URL to delete

    Returns:
        True if deletion succeeded, False otherwise
    """
    if not secure_url:
        return False

    try:
        if not configure_cloudinary():
            logger.warning("Cloudinary not configured. Cannot rollback.")
            return False

        # Extract public_id from Cloudinary URL
        # URL format: https://res.cloudinary.com/{cloud}/image/upload/v{version}/{folder}/{public_id}.{ext}
        # or: https://res.cloudinary.com/{cloud}/raw/upload/v{version}/{folder}/{public_id}.{ext}
        public_id = _extract_public_id(secure_url)
        if not public_id:
            logger.warning(f"Could not extract public_id from URL: {secure_url}")
            return False

        # Determine resource type from URL
        resource_type = "image"
        if "/raw/upload/" in secure_url:
            resource_type = "raw"

        result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
        if result.get("result") == "ok":
            logger.info(f"🗑️ Cloudinary rollback: deleted {public_id}")
            return True
        else:
            logger.warning(f"Cloudinary rollback: destroy returned {result} for {public_id}")
            return False

    except Exception as e:
        logger.error(f"Cloudinary rollback failed for {secure_url}: {e}")
        return False


def _extract_public_id(secure_url: str) -> Optional[str]:
    """
    Extract the Cloudinary public_id from a secure URL.

    Handles various URL formats:
    - https://res.cloudinary.com/cloud/image/upload/v123/folder/file.jpg
    - https://res.cloudinary.com/cloud/raw/upload/v123/folder/file.pdf

    Returns:
        The public_id string (e.g., 'folder/file') or None
    """
    try:
        import re
        # Match the path after /upload/ and optional version
        match = re.search(r'/upload/(?:v\d+/)?(.+?)(?:\.[^.]+)?$', secure_url)
        if match:
            return match.group(1)
        return None
    except Exception:
        return None

