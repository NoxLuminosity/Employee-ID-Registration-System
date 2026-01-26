# Configuration Guide - HR Portal Organization Access Control

## Quick Setup (5 minutes)

### Step 1: Find the People Support Department ID (from Lark)

**Via Lark Developer Console:**
1. Log in to [Lark Developer Console](https://open.larksuite.com)
2. Select your application
3. Navigate to **API Documentation** > **Contact API** > **Departments**
4. Test the API endpoint or use the Lark CLI

**Via cURL (requires tenant_access_token):**
```bash
curl -X GET "https://open.larksuite.com/open-apis/contact/v3/departments?page_size=50" \
  -H "Authorization: Bearer YOUR_TENANT_ACCESS_TOKEN"
```

**Response format (find "People Support" in the list):**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "has_more": false,
    "page_token": "",
    "items": [
      {
        "name": "People Support",
        "open_department_id": "od_12345abcde67890",  // ← THIS IS WHAT YOU NEED
        "parent_department_id": "od_98765fedcba321",
        "department_id": "12345",
        ...
      },
      ...
    ]
  }
}
```

**Look for**: The entry where `"name": "People Support"` and copy the `open_department_id` value.

### Step 2: Set Environment Variable

#### For Local Development

Edit your `.env` file in the project root:
```bash
# .env
TARGET_LARK_DEPARTMENT_ID=od_12345abcde67890
```

Replace `od_12345abcde67890` with the actual department ID you found above.

#### For Vercel Deployment

1. Go to your Vercel project
2. Click **Settings** → **Environment Variables**
3. Add new variable:
   - **Name**: `TARGET_LARK_DEPARTMENT_ID`
   - **Value**: `od_12345abcde67890` (the department ID from Lark)
   - **Select Environment**: Production / Preview / Development (as needed)
4. Click **Save**
5. Redeploy the application

**Vercel Environment Variable Screenshot Example:**
```
Name: TARGET_LARK_DEPARTMENT_ID
Value: od_12345abcde67890
Environments: ✓ Production ✓ Preview ✓ Development
```

### Step 3: Restart Application

**Local:**
```bash
# Stop the app (Ctrl+C)
# Then restart
python -m uvicorn app.main:app --reload
```

**Vercel:**
- Auto-redeployment when environment variables change
- Or manually redeploy from Vercel dashboard

### Step 4: Verify Configuration

**Check logs for configuration:**
```bash
# Should NOT see this warning:
# "TARGET_LARK_DEPARTMENT_ID environment variable not set"

# Should see this in logs:
# "Org validation result from cache for {user}: True/False"
```

**Test with authorized user:**
1. Login with a Lark account that belongs to People Support department
2. Should access dashboard/gallery successfully
3. Check logs: `"HR Portal access GRANTED via org validation"`

**Test with unauthorized user:**
1. Login with a Lark account NOT in People Support
2. Should see error: "Access denied. HR Portal access is restricted to People Support department members only."
3. Check logs: `"HR Portal access DENIED: User not in People Support department hierarchy"`

---

## Verification Checklist

### ✅ Configuration Verification

```bash
# Verify env var is set (local)
echo $TARGET_LARK_DEPARTMENT_ID
# Should print: od_xxxxxxxxxx (not empty)

# Verify env var is set (Vercel)
# Check in Vercel project Settings > Environment Variables
# Should see TARGET_LARK_DEPARTMENT_ID with value
```

### ✅ Access Control Verification

| Test | Expected Result | How to Verify |
|------|-----------------|---------------|
| Authorized user login | Access dashboard | Logs: "access GRANTED" |
| Unauthorized user login | See error message | Logs: "access DENIED" |
| API call (authorized) | Returns 200 with data | Network tab shows 200 |
| API call (unauthorized) | Returns 403 | Network tab shows 403 |
| Cache working | Second request is fast | Logs: "from cache" |

### ✅ Form Submission Verification

```bash
# Employee form submission should still work
# (This is not gated by HR Portal org control)

1. Navigate to /apply (or form page)
2. Fill and submit form as employee
3. Should upload to Lark/database successfully
4. Org access control only affects HR Portal (/hr/*)
```

---

## Common Issues & Solutions

### Issue 1: "Department ID not set" warning in logs

**Symptom:**
```
WARNING: TARGET_LARK_DEPARTMENT_ID environment variable not set
```

**Solution:**
1. Verify env var is set: `echo $TARGET_LARK_DEPARTMENT_ID`
2. Check `.env` file exists in project root
3. Restart application after adding env var
4. For Vercel: Check environment variables in project settings

### Issue 2: All Lark users getting "Access denied"

**Symptom:**
- Every Lark login attempt shows access denied error
- Logs show: `"User not in People Support department hierarchy"`

**Solutions:**

A) **Department ID is wrong**
   - Get correct ID from Lark again (verify it's for "People Support")
   - Update environment variable
   - Restart app

B) **User not actually in People Support**
   - Check in Lark admin panel: Is user in People Support department?
   - Check org hierarchy: Should be under Solutions Management, People Development
   - Add test user to People Support department

C) **Lark API not accessible**
   - Check Lark app has correct permissions
   - Verify tenant_access_token is valid
   - Check network connectivity to open.larksuite.com

### Issue 3: Some users can't access despite being in People Support

**Symptom:**
- One user from People Support can access
- Another user from same department cannot

**Solutions:**

A) **Check Lark org hierarchy**
   - Both users should have People Support dept in their parent chain
   - Use Lark Contact API to verify user's departments
   - Check `parent_department_id` chain goes to root

B) **Cache might be stale**
   - Clear browser cookies
   - Logout and login again
   - Cache expires after 30 minutes automatically

C) **Different department with same name**
   - Make sure it's the correct "People Support" (Lark dept ID)
   - Not a different dept with similar name
   - Verify with dept ID, not just name

### Issue 4: Performance - Slow login/API calls

**Symptom:**
- First request takes 500ms+ longer than normal
- Subsequent requests are fast

**Explanation:**
- First request: Makes Lark API call for org validation (network delay)
- Cached requests: Instant (from cache)
- Cache TTL: 30 minutes

**Solution:**
- This is normal behavior
- Cache significantly improves performance after first request
- If consistently slow, check Lark API response times

### Issue 5: Can't find "People Support" department

**Symptom:**
- Listed departments don't include "People Support"
- Or multiple departments with that name

**Solutions:**

A) **Check org structure in Lark**
   - Login to Lark
   - Go to Admin Console
   - Check organization structure
   - Verify hierarchy matches: S.P. Madrid & Associates > Solutions Management > People Development > People Support

B) **Use correct filter in API**
   ```bash
   # Make sure to include these params:
   department_id_type=open_department_id
   
   curl "https://open.larksuite.com/open-apis/contact/v3/departments?page_size=100" \
     -H "Authorization: Bearer TOKEN"
   ```

C) **Check API response for hierarchy**
   - Look at `parent_department_id` field
   - Trace the parent chain to verify structure

---

## Testing Script (Manual Verification)

Save as `test_org_access.sh`:

```bash
#!/bin/bash

# Test HR Portal Org Access Control

echo "=== HR Portal Org Access Control Test ==="
echo ""

# Check environment variable
echo "[1] Checking environment variable..."
DEPT_ID=$TARGET_LARK_DEPARTMENT_ID
if [ -z "$DEPT_ID" ]; then
    echo "❌ TARGET_LARK_DEPARTMENT_ID is not set!"
    exit 1
else
    echo "✅ TARGET_LARK_DEPARTMENT_ID = $DEPT_ID"
fi

echo ""
echo "[2] Testing API endpoint (authorized user)..."
# Replace with actual auth cookie from authorized user
COOKIE="hr_session=YOUR_JWT_TOKEN_HERE"
curl -i -H "Cookie: $COOKIE" http://localhost:8000/hr/api/employees

echo ""
echo "[3] Testing API endpoint (no auth)..."
curl -i http://localhost:8000/hr/api/employees

echo ""
echo "[4] Checking application logs..."
echo "Look for these log messages:"
echo "  ✓ 'Org validation result from cache'"
echo "  ✓ 'HR Portal access GRANTED'"
echo "  ✓ 'HR Portal access DENIED'"

echo ""
echo "=== Test Complete ==="
```

Run with:
```bash
chmod +x test_org_access.sh
./test_org_access.sh
```

---

## Monitoring & Logs

### Key Log Patterns to Watch

**Successful org validation:**
```
INFO: Org validation result from cache for xxxxxx: True
INFO: HR Portal access GRANTED via org validation: User in People Support department
INFO: Org access re-validated for Lark user: john.doe
```

**Failed org validation:**
```
WARNING: HR Portal access DENIED: User not in People Support department hierarchy
WARNING: Org access denied for dashboard: john.doe - User not in...
WARNING: API /api/employees: Org access denied - User not in...
```

**Configuration issues:**
```
WARNING: TARGET_LARK_DEPARTMENT_ID environment variable not set
WARNING: TARGET_LARK_DEPARTMENT_ID not configured. Cannot validate org access.
```

### Setting Up Log Monitoring

**Local Development:**
```bash
# Tail application logs
tail -f logs/app.log | grep "HR Portal"
```

**Vercel:**
1. Go to project dashboard
2. Click **Deployments** → select deployment
3. Click **Runtime Logs**
4. Search for: `HR Portal`, `Org validation`, `access GRANTED`

---

## Deployment Checklist

- [ ] Department ID obtained from Lark (People Support)
- [ ] `TARGET_LARK_DEPARTMENT_ID` environment variable set (local)
- [ ] `TARGET_LARK_DEPARTMENT_ID` environment variable set (Vercel)
- [ ] Application restarted after env var change
- [ ] Test with authorized user (People Support member) - should work
- [ ] Test with unauthorized user (other dept) - should be denied
- [ ] Test password-based HR login - should work
- [ ] Verify employee form submission still works (not affected by org control)
- [ ] Check application logs for org validation messages
- [ ] Monitor logs for access patterns during first day

---

## Rollback (If Needed)

To disable org access control:

**Option 1: Remove env var**
```bash
# .env
# Delete or comment out:
# TARGET_LARK_DEPARTMENT_ID=od_xxxxx
```

**Option 2: Set to empty string**
```bash
TARGET_LARK_DEPARTMENT_ID=
```

**Option 3: Set to invalid value (all users denied)**
```bash
TARGET_LARK_DEPARTMENT_ID=invalid
```

Then restart application.

**Result after disabling:**
- Org validation will fail for everyone
- If using fallback Bitable check, those users might still get access
- All other authenticated users can still access HR Portal (if using password auth)

---

## Support Resources

- **Lark Contact API**: https://open.larksuite.com/document/server-docs/contact-v3/
- **Lark Department API**: https://open.larksuite.com/document/server-docs/contact-v3/department/
- **Application Logs**: Check `app/routes/hr.py` and `app/services/lark_auth_service.py` for logging
- **Troubleshooting**: See IMPLEMENTATION_SUMMARY.md for detailed architecture

---

## Quick Reference

| Item | Value |
|------|-------|
| Environment Variable Name | `TARGET_LARK_DEPARTMENT_ID` |
| Example Value | `od_12345abcde67890` |
| Lark API for Finding ID | `GET /open-apis/contact/v3/departments` |
| Cache Duration | 30 minutes |
| Re-validation Frequency | Every request (to HR Portal) |
| Authorized Users | Members of People Support department |
| Total Authorized | ~17 users (as per your org) |
| Unauthorized Response | 403 Forbidden or redirect to login |
| Error Message | "Access denied. HR Portal access is restricted to People Support department members only." |
