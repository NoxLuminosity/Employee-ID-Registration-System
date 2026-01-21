"""
BytePlus Seedream AI Image Generation Service
Handles generating professional headshots using BytePlus Seedream API.

Authentication: Uses BYTEPLUS_API_KEY environment variable.
This is production-safe for Vercel serverless functions.

Note: Seedream requires an image URL, so images are first uploaded to Cloudinary.
"""
import os
import json
import logging
from typing import Optional, Dict, Any, Tuple
import urllib.request
import urllib.error

# Configure logging
logger = logging.getLogger(__name__)

# BytePlus Seedream API endpoint - Use environment variable or default
SEEDREAM_API_URL = os.environ.get(
    'BYTEPLUS_ENDPOINT',
    "https://ark.ap-southeast.bytepluses.com/api/v3/images/generations"
)
SEEDREAM_MODEL = os.environ.get('BYTEPLUS_MODEL', "seedream-4-5-251128")

# Professional headshot prompt - Updated for brown suit with dark navy shirt
# This prompt generates consistent, professional ID card photos
HEADSHOT_PROMPT = """Use the uploaded image as the reference subject. Generate a centered, waist-up portrait of the person. The person is wearing a brown suit with a dark navy shirt, neatly styled, professional appearance. Studio portrait style with soft, even lighting and a neutral light grey background. Fully framed, 1:1 aspect ratio, no cropping, photorealistic, consistent composition and style across all images. Keep facial features and hairstyle similar to the reference image. No extra objects, no accessories other than the outfit specified."""


def generate_headshot_from_url(image_url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Generate a professional headshot using BytePlus Seedream API.
    
    Args:
        image_url: Public URL of the image to use as reference
    
    Returns:
        Tuple of (generated_image_url, None) on success, or (None, error_message) on failure
        The URL points to the generated image hosted by BytePlus
    """
    api_key = os.environ.get('BYTEPLUS_API_KEY')
    
    if not api_key:
        logger.error("BYTEPLUS_API_KEY environment variable not set")
        return None, "API key not configured"
    
    if not image_url:
        logger.error("No image URL provided")
        return None, "No image URL provided"
    
    try:
        # Prepare the request payload with updated settings
        payload = {
            "model": SEEDREAM_MODEL,
            "prompt": HEADSHOT_PROMPT,
            "image": image_url,  # Must be a public URL
            "sequential_image_generation": "disabled",
            "response_format": "url",  # Return URL instead of base64
            "size": "2K",  # High resolution 2K output
            "stream": False,
            "watermark": False  # No watermark on generated images
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        request_data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            SEEDREAM_API_URL, 
            data=request_data, 
            headers=headers, 
            method="POST"
        )
        
        logger.info(f"Sending request to BytePlus Seedream API with image URL: {image_url[:50]}...")
        
        with urllib.request.urlopen(req, timeout=120) as response:
            response_body = response.read().decode('utf-8')
            result = json.loads(response_body)
        
        logger.info(f"Seedream API response: {json.dumps(result)[:500]}...")
        
        # Extract generated image URL from response
        if 'data' in result and len(result['data']) > 0:
            generated_url = result['data'][0].get('url')
            if generated_url:
                logger.info(f"Successfully generated headshot with BytePlus Seedream: {generated_url[:80]}...")
                return generated_url, None
        
        logger.error(f"Unexpected Seedream response format: {result}")
        return None, "Unexpected response format from API"
        
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        logger.error(f"BytePlus Seedream API HTTP error {e.code}: {error_body}")
        return None, f"API error: {error_body[:100]}"
    except urllib.error.URLError as e:
        logger.error(f"BytePlus Seedream API URL error: {str(e)}")
        return None, f"Connection error: {str(e)}"
    except Exception as e:
        logger.error(f"Error generating headshot: {str(e)}")
        return None, str(e)
