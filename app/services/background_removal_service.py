"""
Background Removal Service
Handles removing backgrounds from images using remove.bg API.

This service is used to remove the background from AI-generated headshots
so they can be placed on ID card templates with custom backgrounds.

For Vercel deployment, we use the remove.bg API instead of local rembg
to avoid large dependencies and serverless function size limits.

Authentication: Uses REMOVEBG_API_KEY environment variable.
Get your API key at: https://www.remove.bg/api

FIX: Improved error handling and request formatting for reliable 
background removal in both local and Vercel environments.
"""
import os
import io
import logging
from typing import Optional, Tuple
import urllib.request
import urllib.error
import urllib.parse
import json
import base64

# Configure logging
logger = logging.getLogger(__name__)

# Remove.bg API endpoint
REMOVEBG_API_URL = "https://api.remove.bg/v1.0/removebg"


def remove_background_from_url(image_url: str) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Download an image from URL and remove its background using remove.bg API.
    
    FIX: Uses direct form data encoding with proper headers to ensure
    the API accepts the request in both local and Vercel environments.
    
    Args:
        image_url: Public URL of the image to process
    
    Returns:
        Tuple of (image_bytes_with_transparent_bg, None) on success,
        or (None, error_message) on failure
    """
    if not image_url:
        logger.error("remove_background_from_url: No image URL provided")
        return None, "No image URL provided"
    
    api_key = os.environ.get('REMOVEBG_API_KEY')
    
    if not api_key:
        logger.warning("REMOVEBG_API_KEY not set - background removal disabled")
        return None, "Background removal API not configured"
    
    logger.info(f"=== REMOVE.BG API REQUEST ===")
    logger.info(f"Image URL: {image_url[:100]}...")
    logger.info(f"API Key present: {bool(api_key)} (length: {len(api_key)})")
    
    try:
        # FIX: Use multipart form data which is more reliable than URL-encoded data
        # This format works consistently in both local and serverless environments
        boundary = '----PythonFormBoundary7MA4YWxkTrZu0gW'
        
        body_parts = [
            f'--{boundary}',
            'Content-Disposition: form-data; name="image_url"',
            '',
            image_url,
            f'--{boundary}',
            'Content-Disposition: form-data; name="size"',
            '',
            'auto',
            f'--{boundary}',
            'Content-Disposition: form-data; name="format"',
            '',
            'png',
            f'--{boundary}',
            'Content-Disposition: form-data; name="type"',
            '',
            'person',
            f'--{boundary}--',
            ''
        ]
        
        body = '\r\n'.join(body_parts).encode('utf-8')
        
        req = urllib.request.Request(
            REMOVEBG_API_URL,
            data=body,
            headers={
                'X-Api-Key': api_key,
                'Content-Type': f'multipart/form-data; boundary={boundary}'
            },
            method='POST'
        )
        
        logger.info("Sending request to remove.bg API...")
        
        with urllib.request.urlopen(req, timeout=120) as response:
            output_bytes = response.read()
            content_type = response.headers.get('Content-Type', '')
            
            logger.info(f"Response status: {response.status}")
            logger.info(f"Response Content-Type: {content_type}")
            logger.info(f"Response size: {len(output_bytes)} bytes")
        
        # Verify we got an image back (not JSON error)
        if content_type.startswith('application/json') or len(output_bytes) < 1000:
            try:
                error_data = json.loads(output_bytes.decode('utf-8'))
                error_msg = error_data.get('errors', [{}])[0].get('title', 'Unknown error')
                logger.error(f"remove.bg returned error: {error_msg}")
                return None, f"Background removal failed: {error_msg}"
            except:
                pass
        
        logger.info(f"=== BACKGROUND REMOVAL SUCCESS ===")
        logger.info(f"Output size: {len(output_bytes)} bytes")
        return output_bytes, None
        
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode('utf-8')
        except:
            error_body = str(e)
        
        logger.error(f"remove.bg API HTTP error {e.code}: {error_body[:500]}")
        
        # Parse error message if JSON
        try:
            error_json = json.loads(error_body)
            error_msg = error_json.get('errors', [{}])[0].get('title', error_body[:100])
        except:
            error_msg = f"HTTP {e.code}: {error_body[:100]}"
        
        return None, f"Background removal failed: {error_msg}"
    except urllib.error.URLError as e:
        logger.error(f"remove.bg API URL error: {str(e)}")
        return None, f"Connection error: {str(e)}"
    except Exception as e:
        logger.error(f"Error removing background: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None, str(e)


def remove_background_from_bytes(image_bytes: bytes) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Remove background from image bytes using remove.bg API.
    
    Args:
        image_bytes: Raw image bytes
    
    Returns:
        Tuple of (image_bytes_with_transparent_bg, None) on success,
        or (None, error_message) on failure
    """
    if not image_bytes:
        return None, "No image data provided"
    
    api_key = os.environ.get('REMOVEBG_API_KEY')
    
    if not api_key:
        logger.warning("REMOVEBG_API_KEY not set - background removal disabled")
        return None, "Background removal API not configured"
    
    try:
        logger.info(f"Removing background from {len(image_bytes)} bytes via remove.bg API...")
        
        import base64
        
        # Use base64 encoding for the image
        boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
        
        body = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="image_file_b64"\r\n\r\n'
            f'{base64.b64encode(image_bytes).decode()}\r\n'
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="size"\r\n\r\nauto\r\n'
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="format"\r\n\r\npng\r\n'
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="type"\r\n\r\nperson\r\n'
            f'--{boundary}--\r\n'
        ).encode('utf-8')
        
        req = urllib.request.Request(
            REMOVEBG_API_URL,
            data=body,
            headers={
                'X-Api-Key': api_key,
                'Content-Type': f'multipart/form-data; boundary={boundary}'
            },
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=120) as response:
            output_bytes = response.read()
        
        logger.info(f"Background removed successfully. Output size: {len(output_bytes)} bytes")
        return output_bytes, None
        
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        logger.error(f"remove.bg API HTTP error {e.code}: {error_body}")
        return None, f"Background removal failed: HTTP {e.code}"
    except Exception as e:
        logger.error(f"Error removing background: {str(e)}")
        return None, str(e)


def remove_background_from_file(input_path: str, output_path: str) -> bool:
    """
    Remove background from an image file and save to output path.
    
    Args:
        input_path: Path to input image file
        output_path: Path to save output PNG with transparent background
    
    Returns:
        True on success, False on failure
    """
    try:
        logger.info(f"Removing background from file: {input_path}")
        
        # Read input file
        with open(input_path, 'rb') as f:
            image_bytes = f.read()
        
        # Remove background
        result_bytes, error = remove_background_from_bytes(image_bytes)
        
        if not result_bytes:
            logger.error(f"Background removal failed: {error}")
            return False
        
        # Save output
        with open(output_path, 'wb') as f:
            f.write(result_bytes)
        
        logger.info(f"Background removed and saved to: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error removing background from file: {str(e)}")
        return False
