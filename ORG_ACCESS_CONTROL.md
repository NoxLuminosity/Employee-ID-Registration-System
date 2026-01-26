# HR Portal Organization-Based Access Control

## Overview

This implementation restricts HR Portal access to users belonging to the **People Support** department within the Lark organization hierarchy. Only users who are direct members or descendants of this department can access the HR Portal.

**Organization Hierarchy:**
```
S.P. Madrid & Associates
└── Solutions Management
    └── People Development
        └── People Support  ← Only these 17 users can access HR Portal
```

## Implementation Details

### Architecture

- **Validation Method**: Department ID hierarchy validation (more reliable than string matching, survives org renames)
- **Re-validation**: Org access is verified on **every HR request** (not just login), catching org changes during sessions
- **Caching**: Department hierarchy validation results cached for 30 minutes to reduce API calls
- **Multiple Auth Types**: Both password-authenticated and Lark OAuth HR users are supported
  - Password users: Access allowed (no org data available to validate)
  - Lark users: Must belong to People Support department

## Configuration

### Required Environment Variable

Set this in your `.env` file or Vercel environment variables:

```bash
TARGET_LARK_DEPARTMENT_ID=<the_lark_department_id_for_people_support>
```

**How to find the People Support department ID:**
1. Go to Lark Developer Console
2. Navigate to your application
3. Use the Contact API to retrieve departments
4. Find "People Support" department and copy its `open_department_id`

Example using curl:
```bash
curl -X GET "https://open.larksuite.com/open-apis/contact/v3/departments?page_size=100" \
  -H "Authorization: Bearer <tenant_access_token>"
```

Look for department with `name: "People Support"` and get its `open_department_id` value.

### Optional Configuration

```bash
# Org validation cache TTL (default: 1800 seconds = 30 minutes)
# Reduces repeated API calls for same user during session
ORG_CACHE_EXPIRY_SECONDS=1800
```

## Files Modified

### 1. **app/services/lark_auth_service.py**
- Added `TARGET_LARK_DEPARTMENT_ID` environment variable configuration
- Added `_org_validation_cache` dictionary for caching validation results
- Added `_cleanup_org_validation_cache()` function to expire old cache entries
- **New function**: `is_descendant_of_people_support(open_id, tenant_token)` - Main validation logic
  - Checks if user's department ID is or is under the target People Support department
  - Uses parent department traversal for reliability
  - Returns tuple of (is_authorized: bool, reason: str)
  - Implements 30-minute caching
- Updated `validate_hr_portal_access()` to use new `is_descendant_of_people_support()` function
  - Primary validation via department IDs
  - Fallback to Bitable records for legacy support

### 2. **app/auth.py**
- **New function**: `verify_org_access(hr_session)` - Middleware for route protection
  - Verifies session is valid AND org access is granted
  - Re-validates org access on every request
  - Raises HTTPException 401 if not authenticated
  - Raises HTTPException 403 if org access denied
  - Allows password-authenticated users (no org data available)
  - For Lark users, calls `is_descendant_of_people_support()` for re-validation

### 3. **app/routes/hr.py**
- Updated import to include `verify_org_access` from auth module
- **Routes protected with org access check:**
  - `GET /hr/dashboard` - Redirects to login if unauthorized
  - `GET /hr/gallery` - Redirects to login if unauthorized
  - `GET /api/employees` - Returns 403 if org access denied
  - `GET /api/employees/{employee_id}` - Returns 403 if org access denied
  - `POST /api/employees/{employee_id}/approve` - Returns 403 if org access denied
  - `DELETE /api/employees/{employee_id}` - Returns 403 if org access denied
  - `POST /api/employees/{employee_id}/remove-background` - Returns 403 if org access denied

## Access Control Flow

### Login Flow (Lark OAuth)

```
1. User clicks "Login with Lark"
   ↓
2. Redirected to Lark authorization page
   ↓
3. User grants permission
   ↓
4. Callback received at /hr/lark/callback
   ↓
5. validate_hr_portal_access(open_id) called
   ├─→ is_descendant_of_people_support(open_id)
   │   ├─→ Check cache (30-min TTL)
   │   ├─→ Fetch user's department IDs from Lark Contact API
   │   ├─→ For each dept: traverse parents to check if TARGET_LARK_DEPARTMENT_ID found
   │   └─→ Return (is_authorized, reason) + cache result
   ├─→ If authorized: Create JWT session, redirect to /hr/dashboard
   └─→ If denied: Display access denied message on login page
   
6. User directed to HR Portal
```

### Login Flow (Password)

```
1. User enters username/password
   ↓
2. Credentials verified
   ↓
3. JWT session created (auth_type="password")
   ↓
4. Redirect to /hr/dashboard
```

### Every Request Flow (Re-validation)

```
1. User makes request to protected route
   ↓
2. Session JWT verified
   ↓
3. If Lark-authenticated (auth_type="lark"):
   ├─→ is_descendant_of_people_support(open_id) called
   │   ├─→ Check cache first (30-min TTL)
   │   ├─→ If cached, use cached result (fast)
   │   └─→ If not cached, fetch from Lark API + cache
   ├─→ If authorized: Allow request to proceed
   └─→ If denied: Return 403 Forbidden or redirect to login
   
4. If password-authenticated:
   └─→ Allow request (password users have implicit access)
```

## Response Codes

| Code | Scenario | Action |
|------|----------|--------|
| 200 | Auth successful, org access granted | Proceed to dashboard/API |
| 302 | Redirect after successful login | Navigate to /hr/dashboard |
| 401 | Session invalid or expired | Redirect to /hr/login |
| 403 | Session valid but org access denied | Display access denied message |

## Error Messages

### Login Page Error (Lark OAuth Denied)
```
Access denied. HR Portal access is restricted to People Support department members only. 
(User not in People Support department hierarchy)
```

### API Response (Org Access Denied)
```json
{
  "success": false,
  "error": "Access denied. You are not authorized to access the HR Portal."
}
```

## Lark Organization Fields Used

From Lark Contact API (retrieved via `get_user_department_info()`):
- **department_ids**: List of department IDs user belongs to
- **department_names**: Human-readable names (for logging)

From Department API (used for hierarchy traversal):
- **open_department_id**: Department's unique ID
- **parent_department_id**: Parent department's ID (or "0" for root)

## Key Design Decisions

### 1. Department ID vs. Name Validation
- **Chosen: Department ID** (e.g., `dept_abc123def456`)
- **Reason**: Names can change, department renames don't break access control
- Alternative rejected: String matching on "People Support" name (fragile)

### 2. Validation on Every Request
- **Chosen: Re-validate org on each request**
- **Reason**: Catches org changes during session (user moved to different dept)
- **Performance**: 30-minute cache reduces API calls
- Alternative rejected: Validate only at login (misses org changes)

### 3. Password User Handling
- **Chosen: Allow password users (no validation)**
- **Reason**: Password users are manual HR staff, assumed trustworthy
- **Alternative**: Could integrate password users with Lark lookup

### 4. Caching Strategy
- **TTL**: 30 minutes (balances freshness vs. API load)
- **Scope**: Per-user cache (user_id → validation result)
- **Expiry**: Automatic cleanup on cache check

### 5. Fallback Behavior
- **Primary**: Department ID validation
- **Fallback**: Bitable employee records lookup (legacy support)
- **Failure**: Access denied (fail-secure)

## Testing

### Test with Authorized User (People Support member)
```bash
1. Login with Lark account for user in People Support dept
2. Should see dashboard + gallery + employee list
3. API calls return 200 with data
4. Approval/deletion endpoints work (return 200)
```

### Test with Unauthorized User (Other department)
```bash
1. Login with Lark account for user NOT in People Support dept
2. Redirected to login with error: "Access denied..."
3. Cannot access dashboard/gallery (403 or redirect)
4. API calls return 403 "Access denied"
5. Approval/deletion endpoints return 403
```

### Test Org Change During Session
```bash
1. Login with authorized user (in People Support)
2. Access HR Portal (works)
3. Admin moves user to different department in Lark
4. User makes another API request
5. Org re-validation fails
6. User gets 403 or redirected to login
```

### Test Cache Functionality
```bash
1. Login with authorized user
2. Access dashboard (API call made, result cached)
3. Immediately access gallery (cached result used, no API call)
4. Wait 31+ minutes
5. Access dashboard again (cache expired, new API call made)
```

## Deployment Checklist

- [ ] Obtain "People Support" department ID from Lark Developer Console
- [ ] Set `TARGET_LARK_DEPARTMENT_ID` environment variable
  - Local: Add to `.env` file
  - Vercel: Add to project environment variables
- [ ] Test with 2-3 authorized users (People Support members)
- [ ] Test with 2-3 unauthorized users (other departments)
- [ ] Verify password authentication still works
- [ ] Test form submission with authorized users (submit button not gated by org, only by auth)
- [ ] Monitor logs for org validation results
- [ ] Verify access denied page/message displays clearly

## Logging

Key log messages to monitor:

```
# Org validation results
"Org validation result from cache for {open_id}: {result}"
"User {open_id} is directly in People Support department"
"User {open_id} is under People Support department"
"User {open_id} not in People Support department hierarchy"

# HR Portal access
"HR Portal access GRANTED via org validation"
"HR Portal access DENIED: {reason}"

# Re-validation on each request
"Org access re-validated for Lark user: {username}"
"Org access denied for Lark user {username}: {reason}"

# API calls
"API /api/employees: Org access denied - {reason}"
```

## Troubleshooting

### Issue: All Lark users getting "Access denied"
**Cause**: `TARGET_LARK_DEPARTMENT_ID` not set or wrong value
**Solution**: 
1. Verify env var is set: `echo $TARGET_LARK_DEPARTMENT_ID`
2. Get correct dept ID from Lark API
3. Restart application

### Issue: Specific user can't access despite being in People Support
**Cause**: User not properly in department hierarchy in Lark
**Solution**:
1. Check user's departments in Lark admin panel
2. Verify parent chain includes correct dept IDs
3. Check logs for which dept IDs user belongs to

### Issue: Slow API responses
**Cause**: Org validation cache expired or not working
**Solution**:
1. Check cache cleanup is running
2. Verify Lark API response times
3. Consider increasing cache TTL

## Future Enhancements

1. **Role-based access control (RBAC)**: Different permissions for different HR roles
2. **Department-level filtering**: Show only employees from user's department
3. **Audit logging**: Track all HR Portal access attempts
4. **Webhook integration**: Update access immediately when org changes (not wait 30 min)
5. **User sync**: Periodically sync authorized users from Lark
