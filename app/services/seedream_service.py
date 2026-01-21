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

# Professional headshot prompt - Updated for corporate executive portrait
# This prompt generates consistent, professional ID card photos
HEADSHOT_PROMPT = """Professional high-end corporate headshot based strictly on the provided reference image. Depict a Filipino male aged approximately 25–40 with a medium warm skin tone, smooth even natural complexion, and a well-groomed, polished appearance. Preserve the subject's original facial structure, proportions, hairstyle, hair texture, hair length, hairline, and grooming exactly as shown, with no identity alteration or stylization. The subject is posed in a 3/4 angle with the body turned approximately 20° to the subject's left while the face looks directly at the camera, shoulders relaxed, posture upright, conveying quiet confidence and approachability with warm, engaged eyes. Frame as a medium close-up cropped at the upper torso, hands not visible, head slightly off-center following the rule of thirds with the eyes aligned along the upper third and balanced headroom. Outfit consists of a navy blazer, crisp white dress shirt, and burgundy silk tie, clean and modern with no added or removed accessories. Use soft, diffused studio lighting with a gentle key light at roughly 45 degrees to the face, even facial illumination, accurate skin tones, minimal shadows, and subtle rim lighting for clean subject separation. Achieve a professional full-frame portrait look (Canon EOS R or Nikon Z6 style) using an 85mm lens aesthetic, shallow depth of field, sharp focus on the eyes, and studio-level clarity. Transparent Background—no white, gray, or colored backdrop—and no environmental elements or props. The final image should project professionalism, confidence, and approachability, suitable for executive, corporate, and LinkedIn profile, full side to side shown and body from torso should be shown."""


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
