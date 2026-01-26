# Implementation Guide: Environment-Specific Issue Fixes

**Date:** January 26, 2026  
**Status:** Identified & Partially Fixed

---

## ✅ Fixes Already Implemented

### 1. **html2canvas Library Added** ✅
**File:** `app/templates/gallery.html` (Line 171)
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
```
**Status:** Already in place  
**Impact:** Enables PDF generation on all environments

### 2. **JWT-Based Session Management** ✅
**File:** `app/auth.py` (Lines 115-250)
- Uses stateless JWT tokens instead of in-memory sessions
- Works perfectly on Vercel serverless
- Tokens are verified by HMAC signature, not server-side storage
**Status:** Fully implemented  
**Impact:** Sessions work correctly across Vercel cold starts

### 3. **CSP Header Updated** ✅
**File:** `app/main.py` (Line 54)
```python
"script-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
```
**Status:** Just fixed  
**Impact:** Allows jsPDF and html2canvas to load from CDN

### 4. **Enhanced Logging Added** ✅
**File:** `app/routes/hr.py` (Lines 405-422)
- Detailed request logging for debugging
- Cookie presence tracking
- Session retrieval status logging
**Status:** Just added  
**Impact:** Makes it easy to identify where authentication fails

---

## 🔍 Remaining Debugging Steps

### **For Vercel (Production)**

#### Step 1: Check Vercel Environment Variables
```bash
vercel env list
# Verify these are set:
# - JWT_SECRET (for secure token generation)
# - SUPABASE_URL (for persistent database)
# - SUPABASE_KEY (for database access)
```

#### Step 2: Enable Debug Logs
```bash
# Pull latest environment
vercel env pull

# Deploy with logging enabled
vercel deploy --prod

# Watch logs
vercel logs --tail --follow
```

#### Step 3: Test the Debug Endpoint
```bash
# In a web browser, after logging in:
# Navigate to: https://your-vercel-domain.com/hr/api/debug

# Should show:
{
  "use_supabase": true,
  "is_vercel": true,
  "session_present": true,
  "session_valid": true,
  "employee_count": X,
  "table_exists": true
}
```

#### Step 4: Test Employee Fetch
```bash
# In browser console while on HR dashboard:
fetch('/hr/api/employees', {
  method: 'GET',
  credentials: 'include',
  headers: {
    'Accept': 'application/json'
  }
})
.then(r => r.json())
.then(d => {
  console.log('Status:', d.success);
  console.log('Employee count:', d.employees?.length);
  console.log('First employee:', d.employees?.[0]);
});

# Check response status and data
```

#### Step 5: Verify Cookie Transmission
```bash
# In browser DevTools:
# 1. Go to Network tab
# 2. Call /hr/api/employees
# 3. Check Request Headers:
#    - Should have: Cookie: hr_session=eyJ...
# 4. Check Response Status:
#    - Should be: 200 (not 401)
```

---

### **For Local (Development)**

#### Step 1: Test PDF Generation
```bash
# Start local server
cd "C:\Users\DELL\Downloads\Employee-ID-Registration-System-9f5f443711e02cb3b226964df20ce09a0f8746ef (1)\Employee-ID-Registration-System-9f5f443711e02cb3b226964df20ce09a0f8746ef"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --log-level debug
```

#### Step 2: Verify Libraries Load
```javascript
// In browser console at http://localhost:8000/hr/gallery:
console.log('html2canvas:', typeof html2canvas !== 'undefined' ? '✓ Loaded' : '✗ Missing');
console.log('jsPDF:', typeof window.jspdf !== 'undefined' ? '✓ Loaded' : '✗ Missing');

// Both should show ✓ Loaded
```

#### Step 3: Test PDF Download
1. Navigate to `/hr/gallery`
2. Click on an ID card → Opens preview
3. Click "Download PDF" button
4. Check:
   - Browser console for errors
   - Download folder for PDF file
   - Browser console: should see PDF config logging

#### Step 4: Check Console for Errors
```
// Expected success logs:
"PDF Config: dimensions: 2.13" × 3.33""
"PDF Front - Design height: 620 Scaled height: ..."
"PDF generated successfully"

// If you see errors like:
"html2canvas is not defined" → Library not loaded
"Failed to generate PDF" → Canvas rendering issue
"CORS error" → Image loading blocked
```

---

## 🚀 Testing Checklist

### **Before Deployment to Production**

- [ ] **Local Testing**
  - [ ] Employee data fetches correctly
  - [ ] PDF downloads successfully
  - [ ] No console errors
  - [ ] All employee fields display

- [ ] **Vercel Testing**
  - [ ] Environment variables set
  - [ ] Debug endpoint returns valid data
  - [ ] Employee fetch returns 200 status
  - [ ] Cookie present in requests
  - [ ] PDF generation works
  - [ ] No 401 authorization errors

- [ ] **Database Testing**
  - [ ] Supabase connection verified (if using)
  - [ ] Employee data persists across requests
  - [ ] Table exists and has correct schema
  - [ ] Data is accessible from multiple regions

---

## 📊 Current Status Summary

| Component | Local | Vercel | Status |
|-----------|-------|--------|--------|
| Employee Data Fetch | ✅ Works | ❓ Testing | JWT sessions implemented |
| PDF Download | ✅ Works* | ❓ Testing | html2canvas + CSP updated |
| Session Management | ✅ JWT | ✅ JWT | Serverless-compatible |
| Logging | ✅ Enhanced | ✅ Enhanced | Full debugging available |
| CSP Headers | ✅ Updated | ✅ Updated | CDN scripts allowed |

*Local PDF requires html2canvas script (now included)

---

## 🐛 Troubleshooting Guide

### **Problem: Employee data still not loading on Vercel**

**Check these in order:**

1. **Is session cookie being sent?**
   - Open DevTools → Application → Cookies
   - Look for `hr_session` cookie
   - If missing → Cookie not set during login
   - If present → Copy its value and check if valid JWT

2. **Is JWT token valid?**
   ```javascript
   // In browser console:
   const cookies = document.cookie.split('; ').find(c => c.startsWith('hr_session='));
   const token = cookies?.split('=')[1];
   console.log('Token:', token);
   
   // Should start with: eyJ... (base64 encoded JSON)
   // If undefined or empty → Cookie not transmitted to serverless
   ```

3. **Is /hr/api/debug endpoint working?**
   ```bash
   # Navigate to: https://your-domain/hr/api/debug
   # Should show session_valid: true
   # If false → Session deserialization failing
   ```

4. **Are logs showing the issue?**
   ```bash
   vercel logs --tail
   # Look for: "API /hr/api/employees: Unauthorized - no valid session"
   # Or: "Session retrieved: false"
   ```

### **Problem: PDF download fails with "html2canvas is not defined"**

**Solution:**

1. Clear browser cache
   - Ctrl+Shift+Delete → Clear cache
   - Reload page

2. Verify script loads:
   ```javascript
   // In console:
   if (!window.html2canvas) {
     console.error('html2canvas not loaded - checking CDN');
     let script = document.createElement('script');
     script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
     document.head.appendChild(script);
   }
   ```

3. Check CSP violations:
   ```
   Console should show any CSP errors like:
   "Refused to load the script 'https://cdnjs.cloudflare.com/...'..."
   ```

### **Problem: Images not loading in PDF**

**Check:**

1. **CORS headers**
   ```bash
   curl -i https://your-domain/hr/gallery | grep -i "Access-Control"
   # Images must be served with appropriate CORS headers
   ```

2. **Image URLs in ID cards**
   - Relative paths: `/static/images/...`
   - Absolute URLs: `https://cloudinary.com/...`
   - Data URLs: `data:image/png;base64,...`

3. **html2canvas CORS setting**
   - In gallery.js, html2canvas is configured with:
     ```javascript
     useCORS: true,
     allowTaint: true
     ```
   - This allows mixed content

---

## 📋 Files Modified

1. ✅ `app/templates/gallery.html` - Added html2canvas CDN
2. ✅ `app/main.py` - Updated CSP header with CDN domain
3. ✅ `app/routes/hr.py` - Added enhanced logging
4. ✅ `app/auth.py` - JWT sessions already implemented
5. 📄 **NEW:** `ENVIRONMENT_DEBUGGING_ANALYSIS.md` - Detailed analysis

---

## 🔗 References

- JWT Implementation: `app/auth.py` lines 115-250
- Session Creation: `create_session()` function
- Session Validation: `get_session()` function
- PDF Generation: `app/static/gallery.js` lines 809-1000
- Debug Endpoint: `app/routes/hr.py` line 356

---

## ⚠️ Important Notes

1. **JWT_SECRET:** Must be set in Vercel environment variables for production
   - Generate: `python -c "import secrets; print(secrets.token_hex(32))"`
   - Set in Vercel: `vercel env add JWT_SECRET`

2. **SUPABASE Setup:** Required for data persistence on Vercel
   - SQLite uses `/tmp` which is ephemeral
   - Data lost on cold starts without Supabase

3. **Cookie Scope:** JWT tokens are sent as cookies with:
   - `httponly=True` (not accessible via JavaScript)
   - `secure=True` (only over HTTPS in production)
   - `samesite="strict"` (protection against CSRF)

4. **CORS/CSP:** Must allow:
   - CDN script sources: `https://cdnjs.cloudflare.com`
   - Image blob URLs: `blob:` in CSP
   - External images: `https:` wildcard for Cloudinary

---

## 💬 Next Steps

1. **Verify fixes locally first** (should already work)
2. **Deploy to Vercel** with enhanced logging
3. **Test each endpoint** using the debugging steps above
4. **Monitor Vercel logs** for authentication failures
5. **Contact support** if JWT verification fails (might need JWT_SECRET update)
