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

# Multiple headshot prompts for different styles
# Each prompt generates a different professional look
# Updated: Smart casual attire options (4 per gender, replacing formal suits/tuxedos)

HEADSHOT_PROMPTS = {
    # Male 1 - Navy polo shirt, neat appearance
    "male_1": """Professional high-end corporate headshot based strictly on the provided reference image. Depict a Filipino person aged approximately 25-40 with a medium warm skin tone, smooth even natural complexion, and a well-groomed, polished appearance. Preserve the subject's original facial structure, proportions, hairstyle, hair texture, hair length, hairline, and grooming exactly as shown, with no identity alteration or stylization. The subject is posed in a 3/4 angle with the body turned approximately 20 degrees to the subject's left while the face looks directly at the camera, shoulders relaxed, posture upright, conveying quiet confidence and approachability with warm, engaged eyes. The subject's mouth should be closed with no teeth showing. Frame as a close-up shot cropped at the chest to the head, hands not visible, head slightly off-center following the rule of thirds with the eyes aligned along the upper third and balanced headroom. Outfit consists of a crisp navy blue polo shirt with a subtle collar, clean and smart casual style with no added accessories. Use soft, diffused studio lighting with a gentle key light at roughly 45 degrees to the face, even facial illumination, accurate skin tones, minimal shadows, and subtle rim lighting for clean subject separation. Achieve a professional full-frame portrait look (equivalent to Canon EOS R or Nikon Z6 style) using an 85mm lens aesthetic, shallow depth of field, sharp focus on the eyes, and studio-level clarity. Transparent Background with no white, gray, or colored backdrop and no environmental elements or props. The final image should project professionalism, confidence, and approachability, suitable for executive, corporate, and LinkedIn profile, full side-to-side shown and body from torso should be shown. Subject only, no background, transparent background.""",
    
    # Male 2 - Light blue collared shirt with smart casual cardigan
    "male_2": """Professional high-end corporate headshot based strictly on the provided reference image. Depict a Filipino person aged approximately 25-40 with a medium warm skin tone, smooth even natural complexion, and a well-groomed, polished appearance. Preserve the subject's original facial structure, proportions, hairstyle, hair texture, hair length, hairline, and grooming exactly as shown, with no identity alteration or stylization. The subject is posed in a 3/4 angle with the body turned approximately 20 degrees to the subject's left while the face looks directly at the camera, shoulders relaxed, posture upright, conveying quiet confidence and approachability with warm, engaged eyes. The subject's mouth should be closed with no teeth showing. Frame as a close-up shot cropped at the chest to the head, hands not visible, head slightly off-center following the rule of thirds with the eyes aligned along the upper third and balanced headroom. Outfit: a light blue collared dress shirt layered with a charcoal gray smart casual cardigan, clean modern look with no tie, smart casual professional style. Use soft, diffused studio lighting with a gentle key light at roughly 45 degrees to the face, even facial illumination, accurate skin tones, minimal shadows, and subtle rim lighting for clean subject separation. Achieve a professional full-frame portrait look (equivalent to Canon EOS R or Nikon Z6 style) using an 85mm lens aesthetic, shallow depth of field, sharp focus on the eyes, and studio-level clarity. Transparent Background with no white, gray, or colored backdrop and no environmental elements or props. The final image should project professionalism, confidence, and approachability, suitable for executive, corporate, and LinkedIn profile, full side-to-side shown and body from torso should be shown. Subject only, no background, transparent background.""",
    
    # Male 3 - White polo shirt, professional casual
    "male_3": """Professional high-end corporate headshot based strictly on the provided reference image. Depict a Filipino person aged approximately 25-40 with a medium warm skin tone, smooth even natural complexion, and a well-groomed, polished appearance. Preserve the subject's original facial structure, proportions, hairstyle, hair texture, hair length, hairline, and grooming exactly as shown, with no identity alteration or stylization. The subject is posed in a 3/4 angle with the body turned approximately 20 degrees to the subject's left while the face looks directly at the camera, shoulders relaxed, posture upright, conveying quiet confidence and approachability with warm, engaged eyes. The subject's mouth should be closed with no teeth showing. Frame as a close-up shot cropped at the chest to the head, hands not visible, head slightly off-center following the rule of thirds with the eyes aligned along the upper third and balanced headroom. Outfit consists of a clean white polo shirt with subtle texture, neat collar, professional smart casual style. Use soft, diffused studio lighting with a gentle key light at roughly 45 degrees to the face, even facial illumination, accurate skin tones, minimal shadows, and subtle rim lighting for clean subject separation. Achieve a professional full-frame portrait look (equivalent to Canon EOS R or Nikon Z6 style) using an 85mm lens aesthetic, shallow depth of field, sharp focus on the eyes, and studio-level clarity. Transparent Background with no white, gray, or colored backdrop and no environmental elements or props. The final image should project professionalism, confidence, and approachability, suitable for executive, corporate, and LinkedIn profile, full side-to-side shown and body from torso should be shown. Subject only, no background, transparent background.""",
    
    # Male 4 - Soft gray collared shirt, relaxed professional
    "male_4": """Professional high-end corporate headshot based strictly on the provided reference image. Depict a Filipino person aged approximately 25-40 with a medium warm skin tone, smooth even natural complexion, and a well-groomed, polished appearance. Preserve the subject's original facial structure, proportions, hairstyle, hair texture, hair length, hairline, and grooming exactly as shown, with no identity alteration or stylization. The subject is posed in a 3/4 angle with the body turned approximately 20 degrees to the subject's left while the face looks directly at the camera, shoulders relaxed, posture upright, conveying quiet confidence and approachability with warm, engaged eyes. The subject's mouth should be closed with no teeth showing. Frame as a close-up shot cropped at the chest to the head, hands not visible, head slightly off-center following the rule of thirds with the eyes aligned along the upper third and balanced headroom. Outfit: a soft gray collared dress shirt with neat appearance, top button casually open, clean smart casual professional aesthetic. Use soft, diffused studio lighting with a gentle key light at roughly 45 degrees to the face, even facial illumination, accurate skin tones, minimal shadows, and subtle rim lighting for clean subject separation. Achieve a professional full-frame portrait look (equivalent to Canon EOS R or Nikon Z6 style) using an 85mm lens aesthetic, shallow depth of field, sharp focus on the eyes, and studio-level clarity. Transparent Background with no white, gray, or colored backdrop and no environmental elements or props. The final image should project professionalism, confidence, and approachability, suitable for executive, corporate, and LinkedIn profile, full side-to-side shown and body from torso should be shown. Subject only, no background, transparent background.""",
    
    # Female 1 - Sage green blouse, professional smart casual
    "female_1": """Professional high-end corporate headshot based strictly on the provided reference image. Depict a Filipino woman aged approximately 25-40 with a medium warm skin tone, smooth even natural complexion, and a well-groomed, polished appearance. Preserve the subject's original facial structure, proportions, hairstyle, hair texture, hair length, hairline, and grooming exactly as shown, with no identity alteration or stylization. The subject is posed in a 3/4 angle with the body turned approximately 20 degrees to the subject's left while the face looks directly at the camera, shoulders relaxed, posture upright, conveying quiet confidence and approachability with warm, engaged eyes. The subject's mouth should be closed with no teeth showing. Frame as a close-up shot cropped at the chest to the head, hands not visible, head slightly off-center following the rule of thirds with the eyes aligned along the upper third and balanced headroom. Outfit: a soft sage green blouse with subtle neckline detail, clean and elegant smart casual style with minimal accessories (optionally small stud earrings), professional and polished. Use soft, diffused studio lighting with a gentle key light at roughly 45 degrees to the face, even facial illumination, accurate skin tones, minimal shadows, and subtle rim lighting for clean subject separation. Achieve a professional full-frame portrait look (equivalent to Canon EOS R or Nikon Z6 style) using an 85mm lens aesthetic, shallow depth of field, sharp focus on the eyes, and studio-level clarity. Transparent Background with no white, gray, or colored backdrop and no environmental elements or props. The final image should project professionalism, confidence, and approachability, suitable for executive, corporate, and LinkedIn profile, full side-to-side shown, and body from torso should be shown. Subject only, no background, transparent background.""",
    
    # Female 2 - Cream/ivory collared blouse, sophisticated casual
    "female_2": """Professional high-end corporate headshot based strictly on the provided reference image. Depict a Filipino woman aged approximately 25-40 with a medium warm skin tone, smooth even natural complexion, and a well-groomed, polished appearance. Preserve the subject's original facial structure, proportions, hairstyle, hair texture, hair length, hairline, and grooming exactly as shown, with no identity alteration or stylization. The subject is posed in a 3/4 angle with the body turned approximately 20 degrees to the subject's left while the face looks directly at the camera, shoulders relaxed, posture upright, conveying quiet confidence and approachability with warm, engaged eyes. The subject's mouth should be closed with no teeth showing. Frame as a close-up shot cropped at the chest to the head, hands not visible, head slightly off-center following the rule of thirds with the eyes aligned along the upper third and balanced headroom. Outfit: an elegant cream or ivory collared blouse with clean lines, sophisticated smart casual style. Minimal jewelry (optional delicate necklace or small studs). Modern professional aesthetic. Use soft, diffused studio lighting with a gentle key light at roughly 45 degrees to the face, even facial illumination, accurate skin tones, minimal shadows, and subtle rim lighting for clean subject separation. Achieve a professional full-frame portrait look (equivalent to Canon EOS R or Nikon Z6 style) using an 85mm lens aesthetic, shallow depth of field, sharp focus on the eyes, and studio-level clarity. Transparent Background with no white, gray, or colored backdrop and no environmental elements or props. The final image should project professionalism, confidence, and approachability, suitable for executive, corporate, and LinkedIn profile, full side-to-side shown, and body from torso should be shown. Subject only, no background, transparent background.""",
    
    # Female 3 - Dusty rose blouse with soft cardigan
    "female_3": """Professional high-end corporate headshot based strictly on the provided reference image. Depict a Filipino woman aged approximately 25-40 with a medium warm skin tone, smooth even natural complexion, and a well-groomed, polished appearance. Preserve the subject's original facial structure, proportions, hairstyle, hair texture, hair length, hairline, and grooming exactly as shown, with no identity alteration or stylization. The subject is posed in a 3/4 angle with the body turned approximately 20 degrees to the subject's left while the face looks directly at the camera, shoulders relaxed, posture upright, conveying quiet confidence and approachability with warm, engaged eyes. The subject's mouth should be closed with no teeth showing. Frame as a close-up shot cropped at the chest to the head, hands not visible, head slightly off-center following the rule of thirds with the eyes aligned along the upper third and balanced headroom. Outfit: a dusty rose or soft pink blouse layered with a light gray smart casual cardigan. Clean, elegant, professional with minimal accessories. Modern smart casual aesthetic. Use soft, diffused studio lighting with a gentle key light at roughly 45 degrees to the face, even facial illumination, accurate skin tones, minimal shadows, and subtle rim lighting for clean subject separation. Achieve a professional full-frame portrait look (equivalent to Canon EOS R or Nikon Z6 style) using an 85mm lens aesthetic, shallow depth of field, sharp focus on the eyes, and studio-level clarity. Transparent Background with no white, gray, or colored backdrop and no environmental elements or props. The final image should project professionalism, confidence, and approachability, suitable for executive, corporate, and LinkedIn profile, full side-to-side shown, and body from torso should be shown. Subject only, no background, transparent background.""",
    
    # Female 4 - Soft blue collared shirt, polished casual
    "female_4": """Professional high-end corporate headshot based strictly on the provided reference image. Depict a Filipino woman aged approximately 25-40 with a medium warm skin tone, smooth even natural complexion, and a well-groomed, polished appearance. Preserve the subject's original facial structure, proportions, hairstyle, hair texture, hair length, hairline, and grooming exactly as shown, with no identity alteration or stylization. The subject is posed in a 3/4 angle with the body turned approximately 20 degrees to the subject's left while the face looks directly at the camera, shoulders relaxed, posture upright, conveying quiet confidence and approachability with warm, engaged eyes. The subject's mouth should be closed with no teeth showing. Frame as a close-up shot cropped at the chest to the head, hands not visible, head slightly off-center following the rule of thirds with the eyes aligned along the upper third and balanced headroom. Outfit: a soft powder blue collared shirt with clean lines, neat and professional smart casual style. Optional small stud earrings. Polished yet relaxed professional aesthetic. Use soft, diffused studio lighting with a gentle key light at roughly 45 degrees to the face, even facial illumination, accurate skin tones, minimal shadows, and subtle rim lighting for clean subject separation. Achieve a professional full-frame portrait look (equivalent to Canon EOS R or Nikon Z6 style) using an 85mm lens aesthetic, shallow depth of field, sharp focus on the eyes, and studio-level clarity. Transparent Background with no white, gray, or colored backdrop and no environmental elements or props. The final image should project professionalism, confidence, and approachability, suitable for executive, corporate, and LinkedIn profile, full side-to-side shown, and body from torso should be shown. Subject only, no background, transparent background."""
}

# Default prompt (Male 1) - kept for backward compatibility
HEADSHOT_PROMPT = HEADSHOT_PROMPTS["male_1"]


def get_prompt_by_type(prompt_type: str = "male_1") -> str:
    """
    Get the headshot prompt by type.
    
    Args:
        prompt_type: One of 'male_1', 'male_2', 'male_3', 'male_4', 'female_1', 'female_2', 'female_3', 'female_4'
    
    Returns:
        The corresponding prompt string, or default (male_1) if not found
    """
    return HEADSHOT_PROMPTS.get(prompt_type, HEADSHOT_PROMPTS["male_1"])


def generate_headshot_from_url(image_url: str, prompt_type: str = "male_1") -> Tuple[Optional[str], Optional[str]]:
    """
    Generate a professional headshot using BytePlus Seedream API.
    
    Args:
        image_url: Public URL of the image to use as reference
        prompt_type: One of 'male_1', 'male_2', 'female_1', 'female_2' (default: male_1)
    
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
    
    # Get the appropriate prompt based on type
    selected_prompt = get_prompt_by_type(prompt_type)
    logger.info(f"Using prompt type: {prompt_type}")
    
    try:
        # Prepare the request payload with updated settings
        payload = {
            "model": SEEDREAM_MODEL,
            "prompt": selected_prompt,
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
