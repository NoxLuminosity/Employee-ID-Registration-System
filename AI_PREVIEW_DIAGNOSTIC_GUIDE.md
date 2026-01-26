# AI Preview Unavailable - Comprehensive Diagnostic Guide

## Problem Overview
When users upload a photo on the Employee Registration form, the AI preview shows "AI preview unavailable" instead of generating a professional headshot.

---

## Root Causes & Solutions

### 🔴 **1. Missing Cookies in API Request (MOST LIKELY CAUSE)**

**Problem:** The `/generate-headshot` endpoint requires authentication via the `employee_session` cookie, but the JavaScript fetch request doesn't send cookies.

**Location:** `app/static/app.js` (Line ~313)

**Current Code:**
```javascript
const response = await fetch('/generate-headshot', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  credentials: 'include',  // ✅ This is ALREADY added
  body: JSON.stringify({ image: imageBase64 }),
  signal: state.aiGenerationController.signal
});
```

**Status:** ✅ **ALREADY FIXED** - The `credentials: 'include'` is already present in the code.

**Verification:** Check browser console:
- Open Developer Tools (F12)
- Go to Network tab
- Upload a photo
- Click on the `/generate-headshot` request
- Check "Request Headers" - should include `Cookie: employee_session=...`

---

### 🔴 **2. User Not Authenticated**

**Problem:** User hasn't logged in via Lark OAuth, so there's no valid `employee_session` cookie.

**How to Check:**
1. Open Developer Tools (F12) → Application → Cookies
2. Look for cookie named `employee_session`
3. If missing or expired, user needs to log in again

**Solution:**
```javascript
// The endpoint returns 401 if not authenticated
// User should see this error in console:
// "Authentication required. Please log in again."
```

**Fix:** User must:
1. Navigate to landing page (/)
2. Click "Get Started" → "I'm an Employee"
3. Complete Lark OAuth login
4. Return to registration form

---

### 🔴 **3. BytePlus API Key Issues**

**Problem:** Invalid, expired, or missing BytePlus API credentials.

**Location:** `.env` file (Lines 9-11)

**Current Configuration:**
```env
BYTEPLUS_API_KEY=ceee70c0-0dbe-4af0-8ee0-2b013b268a35
BYTEPLUS_MODEL=seedream-4-5-251128
BYTEPLUS_ENDPOINT=https://ark.ap-southeast.bytepluses.com/api/v3/images/generations
```

**How to Verify:**
1. Check server logs for error messages:
   ```
   ERROR: BytePlus Seedream API HTTP error 401: Unauthorized
   ERROR: BytePlus Seedream API HTTP error 403: Forbidden
   ```

2. Test the API key manually:
   ```bash
   curl -X POST https://ark.ap-southeast.bytepluses.com/api/v3/images/generations \
     -H "Authorization: Bearer ceee70c0-0dbe-4af0-8ee0-2b013b268a35" \
     -H "Content-Type: application/json" \
     -d '{"model":"seedream-4-5-251128","prompt":"test","image":"https://example.com/image.jpg"}'
   ```

**Solution:**
- Verify API key is active in BytePlus console
- Check billing/quota limits
- Regenerate API key if expired
- Update `.env` file with new credentials

---

### 🔴 **4. Cloudinary Upload Failure**

**Problem:** Original photo can't be uploaded to Cloudinary to get a public URL (BytePlus requires a URL, not base64).

**Location:** `.env` file (Lines 13-16)

**Current Configuration:**
```env
CLOUDINARY_CLOUD_NAME=diybtdlb6
CLOUDINARY_API_KEY=666642232116782
CLOUDINARY_API_SECRET=aGzyG9Lpb2Rq0UF-XN024UH2dw8
```

**How to Verify:**
1. Check server logs:
   ```
   ERROR: Failed to upload image to Cloudinary
   ERROR: Cloudinary API error uploading temp_preview_xxx
   ```

2. Test Cloudinary connection:
   ```python
   import cloudinary
   import cloudinary.uploader
   
   cloudinary.config(
       cloud_name="diybtdlb6",
       api_key="666642232116782",
       api_secret="aGzyG9Lpb2Rq0UF-XN024UH2dw8"
   )
   
   result = cloudinary.uploader.upload("test.jpg")
   print(result['secure_url'])
   ```

**Solution:**
- Verify Cloudinary credentials in dashboard
- Check storage quota limits
- Ensure API key has upload permissions

---

### 🔴 **5. File Size or Format Issues**

**Problem:** Uploaded file is too large or in an unsupported format.

**Current Validation:** `app/static/app.js` (Line ~251)
```javascript
if (file.size > 5 * 1024 * 1024) {
  showMessage('Photo size must be less than 5MB.', 'error');
  if (elements.photoInput) elements.photoInput.value = '';
  return;
}
```

**Supported Formats:**
- ✅ JPG/JPEG
- ✅ PNG
- ✅ WebP
- ❌ BMP (might work but not recommended)
- ❌ GIF (animated GIFs won't work)
- ❌ SVG (vector format not supported)

**Solution:**
- File must be under 5MB
- Use JPG or PNG format
- Ensure file is not corrupted

---

### 🔴 **6. Network/CORS Issues**

**Problem:** Browser blocking the API request due to CORS policy.

**How to Check:**
1. Open Developer Tools (F12) → Console
2. Look for errors like:
   ```
   Access to fetch at 'http://localhost:8000/generate-headshot' from origin 'http://localhost:8000' 
   has been blocked by CORS policy
   ```

**Current CORS Config:** `app/main.py`
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Should allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Solution:**
- CORS is already configured to allow all origins
- If issue persists, check if using different ports (e.g., 8000 vs 8001)
- Ensure `.env` redirect URIs match current port

---

### 🔴 **7. Server-Side Errors**

**Problem:** Python backend is crashing or returning 500 errors.

**How to Diagnose:**

1. **Check Server Logs:**
   ```powershell
   # Look for these patterns in terminal output:
   ERROR: Error in generate-headshot endpoint
   ERROR: Unexpected Seedream response format
   ERROR: API error: ...
   ```

2. **Check Error Response:**
   - Open Developer Tools (F12) → Network
   - Click on `/generate-headshot` request
   - Check "Response" tab for error details

3. **Common Error Messages:**
   ```json
   {"success": false, "error": "Authentication required. Please log in again."}
   // → User not logged in

   {"success": false, "error": "No image data provided"}
   // → Invalid request payload

   {"success": false, "error": "Failed to process image. Please try again."}
   // → Cloudinary upload failed

   {"success": false, "error": "Failed to generate headshot. Please try again."}
   // → BytePlus API failed

   {"success": false, "error": "AI service configuration error. Please contact support."}
   // → API key issues
   ```

---

## Step-by-Step Troubleshooting

### Step 1: Verify Authentication ✅

1. Open browser DevTools (F12) → Application → Cookies
2. Check if `employee_session` cookie exists
3. If missing:
   - Go to landing page → "Get Started" → "I'm an Employee"
   - Complete Lark OAuth login
   - Verify cookie appears after login

### Step 2: Check Browser Console 🔍

1. Open DevTools (F12) → Console tab
2. Clear console (trash icon)
3. Upload a photo
4. Look for error messages:
   - Red errors indicate JavaScript issues
   - Check Network tab for API failures

### Step 3: Inspect Network Request 🌐

1. DevTools (F12) → Network tab
2. Filter by "Fetch/XHR"
3. Upload a photo
4. Click on `/generate-headshot` request
5. Check:
   - **Status Code:** Should be 200 (OK)
     - 401 = Not authenticated
     - 500 = Server error
   - **Request Headers:** Should include `Cookie: employee_session=...`
   - **Response:** Should have `{"success": true, "generated_image": "..."}`

### Step 4: Check Server Logs 📋

1. Look at terminal running `uvicorn`
2. Search for error messages:
   ```
   ERROR: ...
   WARNING: ...
   ```
3. Common patterns:
   - `BYTEPLUS_API_KEY` → API key issue
   - `Cloudinary` → Image upload issue
   - `Authentication required` → Login issue

### Step 5: Verify Environment Variables 🔐

Run this diagnostic script:
```python
import os
print("BytePlus API Key:", "✅ SET" if os.getenv('BYTEPLUS_API_KEY') else "❌ MISSING")
print("BytePlus Model:", os.getenv('BYTEPLUS_MODEL'))
print("BytePlus Endpoint:", os.getenv('BYTEPLUS_ENDPOINT'))
print("Cloudinary Cloud:", "✅ SET" if os.getenv('CLOUDINARY_CLOUD_NAME') else "❌ MISSING")
print("Cloudinary API Key:", "✅ SET" if os.getenv('CLOUDINARY_API_KEY') else "❌ MISSING")
print("Cloudinary Secret:", "✅ SET" if os.getenv('CLOUDINARY_API_SECRET') else "❌ MISSING")
```

### Step 6: Test Individual Components 🧪

**Test Cloudinary Upload:**
```python
from app.services.cloudinary_service import upload_base64_to_cloudinary
url = upload_base64_to_cloudinary("data:image/png;base64,iVBORw0KGg...", "test_upload", "test")
print("Upload result:", url)
```

**Test BytePlus API:**
```python
from app.services.seedream_service import generate_headshot_from_url
url, error = generate_headshot_from_url("https://example.com/test.jpg")
print("Generation result:", url or error)
```

---

## Quick Fixes

### Fix 1: Restart Server with Correct Port
```powershell
# Stop any existing server
taskkill /F /IM python.exe

# Navigate to project directory
cd "C:\Users\DELL\Downloads\Employee-ID-Registration-System-9f5f443711e02cb3b226964df20ce09a0f8746ef (1)\Employee-ID-Registration-System-9f5f443711e02cb3b226964df20ce09a0f8746ef"

# Start server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Fix 2: Clear Cookies and Re-login
```javascript
// Open browser console and run:
document.cookie = "employee_session=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
// Then login again via Lark OAuth
```

### Fix 3: Check File Format
```javascript
// Before uploading, check file type:
const file = document.getElementById('photo').files[0];
console.log('File type:', file.type);
console.log('File size:', (file.size / 1024 / 1024).toFixed(2), 'MB');
// Should be: image/jpeg or image/png, under 5MB
```

---

## Expected Behavior (When Working Correctly)

1. **User uploads photo**
   - Left panel shows "Original Photo" immediately
   - Right panel shows loading spinner: "Generating AI headshot..."

2. **Backend processing** (takes 10-30 seconds):
   - Upload original to Cloudinary → Get public URL
   - Send URL to BytePlus Seedream → Get AI headshot
   - Upload AI image to Cloudinary with background removal → Get final URL

3. **Display result**:
   - Right panel shows "AI Enhanced Preview"
   - Image has transparent background
   - "Regenerate" button appears below AI preview

4. **ID Card Preview**:
   - Updates automatically with AI headshot
   - Shows transparent professional photo

---

## Prevention Checklist

Before deployment, verify:
- [ ] All environment variables are set in `.env`
- [ ] BytePlus API key is valid and has quota
- [ ] Cloudinary credentials are correct
- [ ] OAuth redirect URIs match deployment URL
- [ ] CORS is properly configured
- [ ] Server is running on correct port (8000)
- [ ] Cookies are enabled in browser
- [ ] File size validation is working (5MB limit)

---

## Contact Support

If issue persists after trying all solutions:

1. **Collect Information:**
   - Browser console errors (screenshot)
   - Network tab `/generate-headshot` response (screenshot)
   - Server logs (last 50 lines)
   - Environment variables (redact secrets)

2. **Check These Files:**
   - `app/static/app.js` (line ~313) - fetch request
   - `app/routes/employee.py` (line ~65) - endpoint authentication
   - `app/services/seedream_service.py` - BytePlus integration
   - `app/services/cloudinary_service.py` - Image uploads
   - `.env` - All credentials

3. **Common Questions:**
   - Is user authenticated? (Check cookie)
   - What's the exact error message? (Console/Network)
   - What happens in server logs? (Terminal output)
   - Can you manually test the APIs? (Postman/curl)

---

## Summary: Most Likely Issues

Based on the screenshot showing "AI preview unavailable":

1. ✅ **Authentication Issue** (Most likely)
   - User not logged in via Lark OAuth
   - Cookie not being sent with request (already fixed in code)
   - Session expired

2. 🔧 **BytePlus API Issue**
   - API key invalid/expired
   - Quota exceeded
   - API endpoint unreachable

3. 🔧 **Cloudinary Upload Issue**
   - Can't upload original photo
   - Can't get public URL for BytePlus
   - Storage quota exceeded

**Next Steps:**
1. Check if `employee_session` cookie exists
2. Open DevTools → Network → Upload photo → Check `/generate-headshot` status
3. Read server logs for specific error messages
4. Verify all environment variables are correct

---

**Document Version:** 1.0
**Last Updated:** January 26, 2026
**Author:** AI Assistant
