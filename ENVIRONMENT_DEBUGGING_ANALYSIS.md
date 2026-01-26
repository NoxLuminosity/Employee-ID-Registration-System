# Environment-Specific Issue: Local vs. Vercel Debugging Analysis

**Date:** January 26, 2026  
**Issue:** Employee data fetch fails on Vercel (Production), but succeeds locally. PDF generation fails locally but likely exists on Vercel too.

---

## 🔍 Root Cause Analysis

### **PRIMARY ISSUE: Data Fetch Failure on Vercel**

#### 1. **Authentication Cookie Loss in Serverless Functions**
**Location:** `app/static/gallery.js` line 217-224

```javascript
const response = await fetch(apiUrl, {
  method: 'GET',
  credentials: 'include',  // ✅ CORRECT - but may not work on Vercel
  headers: {
    'Accept': 'application/json',
    'Cache-Control': 'no-cache'
  },
  signal: controller.signal
});
```

**Problem:**
- Vercel serverless functions have different cookie handling than traditional servers
- The `hr_session` cookie set by `/hr/lark-callback` may not be properly passed to `/hr/api/employees` in serverless context
- **CORS preflight requests** strip cookies on Vercel
- Session storage may be isolated between different function invocations

**Why it works locally:**
- Local development uses a persistent FastAPI process with session memory
- Cookies are naturally passed between requests in the same process
- No serverless isolation layer

---

#### 2. **Session Retrieval Failure in `get_session()`**
**Location:** `app/routes/hr.py` line 405-410

```python
@router.get("/api/employees")
def api_get_employees(hr_session: str = Cookie(None)):
    session = get_session(hr_session)
    if not session:
        logger.warning("API /api/employees: Unauthorized - no valid session")
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
```

**Problem:**
- On Vercel, `hr_session` cookie value may be `None` because:
  1. Cookie not transmitted from browser to Vercel function
  2. Session storage backend not accessible (if using in-memory storage)
  3. Cross-origin/same-site cookie policies in serverless

---

#### 3. **Session Storage Backend Issue**
**Key Question:** Where are sessions stored?

Need to check: `app/auth.py` - specifically:
- `get_session()` implementation
- `create_session()` implementation
- Session backend (in-memory dict, Redis, database, etc.)

**On Vercel (Potential Issue):**
- If sessions stored in memory → each serverless function invocation gets fresh memory
- If sessions stored in memory → sessions lost after request completes
- **Solution needed:** Use persistent backend (Redis, Supabase, database)

**On Local:**
- FastAPI instance runs continuously in memory
- Sessions survive across requests in same process

---

### **SECONDARY ISSUE: PDF Generation Failure (Locally)**

#### 4. **Missing Dependencies: `html2canvas` & `jsPDF`**
**Location:** `app/templates/gallery.html` line 170-171

```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
```

**Problem:**
- `html2canvas` library is NOT included in the template
- Only `jsPDF` is loaded, but `html2canvas` is required for rendering DOM to canvas

**Expected line (missing):**
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
```

**Local behavior:** Console errors in dev tools, PDF download fails silently

---

#### 5. **CORS & CSP Issues on PDF Download**
**Location:** `app/main.py` lines 40-80 (Content Security Policy)

```python
response.headers["Content-Security-Policy"] = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com; "
    "img-src 'self' data: https: blob:; "
    "connect-src 'self' https://api.cloudinary.com https://api.larksuite.com; "
    ...
)
```

**Problem:**
- CDN scripts not explicitly whitelisted (jsPDF, html2canvas)
- `blob:` URLs allowed for images but CSP may still block dynamic script execution

**Fix needed:**
- Add CDN domains to `script-src`
- Ensure `blob:` URLs work for PDF canvas rendering

---

## 📋 Checklist: What to Inspect

### **For Vercel (Production) - Employee Data Fetch**

- [ ] **Check Vercel logs:**
  ```bash
  vercel logs --tail
  ```
  Look for:
  - `API /api/employees: Unauthorized - no valid session`
  - Cookie presence/absence in request headers
  - `hr_session` value (should not be `None`)

- [ ] **Check Network tab (Browser DevTools):**
  1. Go to `/hr/dashboard`
  2. Open DevTools → Network tab
  3. Filter by `employees` requests
  4. Inspect:
     - Request headers → look for `Cookie: hr_session=...`
     - Response status (401 vs 200)
     - Response body (error vs employee data)

- [ ] **Check Supabase connection:**
  ```bash
  # Verify in Vercel Environment Variables:
  - SUPABASE_URL ✓
  - SUPABASE_KEY ✓
  - USE_SUPABASE should be True
  ```

- [ ] **Check session backend:**
  - Modify `app/auth.py` to log session retrieval attempts
  - Add: `logger.info(f"get_session called with token: {token[:20]}...")`

---

### **For Local (Development) - PDF Generation**

- [ ] **Check Console Errors:**
  1. Open DevTools → Console
  2. Generate PDF and look for:
     - `Uncaught ReferenceError: html2canvas is not defined`
     - CSP violations
     - CORS errors

- [ ] **Verify scripts loaded:**
  ```javascript
  // In browser console:
  console.log('html2canvas:', typeof html2canvas);
  console.log('jsPDF:', typeof window.jspdf);
  ```
  Both should be `object`, not `undefined`

- [ ] **Check CSP headers:**
  ```bash
  curl -i http://localhost:8000/hr/dashboard | grep -i "Content-Security-Policy"
  ```

- [ ] **Check image loading in PDF generation:**
  - Logos use relative paths: `/static/images/SPM%20Logo%201.png`
  - On localhost: Works if file exists at `app/static/images/`
  - May fail if CORS headers block image access

---

## 🛠️ Specific Code-Level Fixes

### **Fix #1: Add Missing `html2canvas` Script**
**File:** `app/templates/gallery.html`

**Before:**
```html
<!-- jsPDF library for PDF generation -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
```

**After:**
```html
<!-- html2canvas - for rendering DOM to canvas -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<!-- jsPDF library for PDF generation -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
```

---

### **Fix #2: Update CSP to Allow CDN Scripts**
**File:** `app/main.py` (SecurityHeadersMiddleware)

**Current:**
```python
"script-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
```

**Updated:**
```python
"script-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
```

---

### **Fix #3: Ensure Session Persistence on Vercel**
**File:** `app/auth.py` (Check implementation, then modify if needed)

**Current potential issue:**
```python
# If using in-memory storage:
_sessions = {}  # Lost on serverless restart!

def get_session(token):
    return _sessions.get(token)  # Returns None if process restarted
```

**Recommended fix:**
```python
# Use Redis or Supabase for persistent session storage
# OR: Use JWT tokens that don't require server-side storage

# JWT approach:
def create_session(username, hours=8, lark_data=None):
    import jwt
    from datetime import datetime, timedelta
    
    payload = {
        "username": username,
        "auth_type": "lark",
        "lark_data": lark_data,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=hours)
    }
    
    token = jwt.encode(payload, os.environ.get("JWT_SECRET"), algorithm="HS256")
    return token

def get_session(token):
    if not token:
        return None
    try:
        import jwt
        payload = jwt.decode(token, os.environ.get("JWT_SECRET"), algorithms=["HS256"])
        return payload
    except jwt.InvalidTokenError:
        return None
```

---

### **Fix #4: Improve Cookie Handling on Vercel**
**File:** `app/routes/hr.py` (Lark callback)

**Current:**
```python
response.set_cookie(
    key="hr_session",
    value=session_id,
    httponly=True,
    max_age=28800,
    samesite="lax",
    secure=is_production,  # True on Vercel
    path="/"
)
```

**Issue on Vercel:** `secure=True` + `samesite="lax"` can cause cookie loss on cross-domain requests

**Better fix:**
```python
is_production = IS_VERCEL or os.environ.get('VERCEL_ENV') == 'production'

response.set_cookie(
    key="hr_session",
    value=session_id,
    httponly=True,
    max_age=28800,
    samesite="strict",  # Changed from "lax"
    secure=is_production,
    path="/",
    domain=None  # Let browser auto-set to current domain
)

logger.info(f"Cookie set: secure={is_production}, samesite=strict, path=/")
```

---

### **Fix #5: Add Request Logging to Debug Cookie Issues**
**File:** `app/routes/hr.py` (api_get_employees function)

**Before:**
```python
@router.get("/api/employees")
def api_get_employees(hr_session: str = Cookie(None)):
    logger.info(f"API /api/employees called, hr_session present: {hr_session is not None}")
```

**After (Enhanced):**
```python
@router.get("/api/employees")
def api_get_employees(request: Request, hr_session: str = Cookie(None)):
    # Log full request details for debugging
    logger.info(f"=== API /api/employees ===")
    logger.info(f"Cookie value: {hr_session[:20] if hr_session else 'None'}...")
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"Client IP: {request.client.host if request.client else 'Unknown'}")
    logger.info(f"Environment: IS_VERCEL={IS_VERCEL}")
    
    session = get_session(hr_session)
    logger.info(f"Session found: {session is not None}")
    
    if not session:
        logger.warning("API /api/employees: Unauthorized - no valid session")
        logger.warning(f"Failed to deserialize session from token: {hr_session}")
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
```

---

## 🔬 Debugging Steps (In Order)

### **Step 1: Verify Environment Variables on Vercel**
```bash
vercel env pull  # Pull from Vercel
echo $SUPABASE_URL
echo $SUPABASE_KEY
```

### **Step 2: Check Vercel Logs for Cookie Issues**
```bash
vercel logs --tail --follow
# Navigate to HR dashboard and check logs
```

### **Step 3: Browser Network Inspection**
1. Open `/hr/login` → complete Lark OAuth
2. Open DevTools → Network tab
3. Navigate to `/hr/dashboard`
4. Click any action to fetch employees
5. Look for `/hr/api/employees` request:
   - **Request Headers:** Check `cookie: hr_session=...`
   - **Response Status:** 200 (success) or 401 (auth failure)
   - **Response Body:** Employee data or error

### **Step 4: Test Locally with Enhanced Logging**
```bash
# Add temporary debug logging
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level debug
```

### **Step 5: Test PDF Generation Locally**
```javascript
// In browser console:
console.log('html2canvas available:', typeof html2canvas !== 'undefined');
console.log('jsPDF available:', typeof window.jspdf !== 'undefined');
```

---

## 📝 Summary: What's Wrong vs. Expected

| Issue | Local | Vercel | Root Cause |
|-------|-------|--------|-----------|
| Employee fetch | ✅ Works | ❌ Fails (401) | Session cookie not sent to serverless function |
| PDF download | ❌ Fails | ❌ Likely fails | Missing `html2canvas` library |
| Session storage | ✅ In-memory works | ❌ Lost on restart | No persistent storage |
| Image loading | ✅ Works | ? | CORS/CSP may restrict CDN images |

---

## 🚀 Recommended Next Steps

1. **Immediate:** Add `html2canvas` script to fix PDF generation everywhere
2. **Priority 1:** Implement JWT-based session management for Vercel serverless compatibility
3. **Priority 2:** Update CSP headers to allow CDN resources
4. **Priority 3:** Add comprehensive request/response logging for troubleshooting
5. **Priority 4:** Test end-to-end on Vercel staging environment

---

## 💡 Key Insights

- **Local works for data but not PDFs:** Missing client-side library (`html2canvas`)
- **Vercel fails for data:** Session persistence problem in serverless architecture
- **Both may have PDF issues:** CSP headers may restrict PDF generation
- **Vercel needs:** Persistent session backend OR JWT tokens instead of server-side sessions
