"""
Lark OAuth 2.0 Authentication Service
Handles Lark SSO login with PKCE flow for secure authentication.

This service provides:
- OAuth 2.0 authorization code flow with PKCE
- Token exchange and refresh
- User info retrieval
- Session management integration

Security Features:
- PKCE (Proof Key for Code Exchange) with S256 method
- State parameter for CSRF protection
- Secure token handling

Lark API Endpoints:
- Authorization: https://accounts.larksuite.com/open-apis/authen/v1/authorize
- Token Exchange: https://open.larksuite.com/open-apis/authen/v2/oauth/token
- User Info: https://open.larksuite.com/open-apis/authen/v1/user_info
"""
import os
import secrets
import hashlib
import base64
import json
import logging
import time
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlencode, quote
import urllib.request
import urllib.error
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)

# ============================================
# Lark OAuth Configuration
# ============================================
LARK_APP_ID = os.getenv('LARK_APP_ID', 'cli_a866185f1638502f')
LARK_APP_SECRET = os.getenv('LARK_APP_SECRET', 'zaduPnvOLTxcb7W8XHYIaggtYgzOUOI6')

# Redirect URI - will be set based on environment
# Must be registered in Lark Developer Console -> Security Settings -> Redirect URLs
IS_VERCEL = os.getenv("VERCEL", "0") == "1" or os.getenv("VERCEL_ENV") is not None
DEFAULT_REDIRECT_URI = os.getenv(
    'LARK_REDIRECT_URI',
    'http://localhost:8000/hr/lark/callback' if not IS_VERCEL else None
)

# Scopes to request (offline_access for refresh tokens)
LARK_SCOPES = os.getenv('LARK_SCOPES', '')

# Lark API Endpoints
AUTHORIZE_URL = "https://accounts.larksuite.com/open-apis/authen/v1/authorize"
TOKEN_URL = "https://open.larksuite.com/open-apis/authen/v2/oauth/token"
USER_INFO_URL = "https://open.larksuite.com/open-apis/authen/v1/user_info"
CONTACT_USER_URL = "https://open.larksuite.com/open-apis/contact/v3/users"

# In-memory storage for OAuth state (short-lived, used during OAuth flow)
# In production with multiple serverless instances, consider using Redis or database
_oauth_states: Dict[str, Dict[str, Any]] = {}
_STATE_EXPIRY_SECONDS = 600  # 10 minutes


def _cleanup_expired_states():
    """Remove expired OAuth states from memory"""
    current_time = time.time()
    expired_keys = [
        key for key, value in _oauth_states.items()
        if current_time - value.get('created_at', 0) > _STATE_EXPIRY_SECONDS
    ]
    for key in expired_keys:
        del _oauth_states[key]


def _make_request(url: str, method: str = "GET", headers: Dict = None, data: Dict = None) -> Dict[str, Any]:
    """Make HTTP request to Lark API using urllib (no external dependencies)"""
    if headers is None:
        headers = {}
    
    headers["Content-Type"] = "application/json; charset=utf-8"
    
    request_data = None
    if data:
        request_data = json.dumps(data).encode('utf-8')
    
    req = urllib.request.Request(url, data=request_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        logger.error(f"Lark API HTTP error {e.code}: {error_body}")
        try:
            return json.loads(error_body)
        except:
            return {"code": e.code, "error": error_body}
    except Exception as e:
        logger.error(f"Lark API request error: {str(e)}")
        return {"code": -1, "error": str(e)}


# ============================================
# PKCE Helper Functions
# ============================================
def generate_pkce() -> Tuple[str, str]:
    """
    Generate PKCE code_verifier and code_challenge (S256 method).
    
    Returns:
        Tuple of (code_verifier, code_challenge)
    """
    # code_verifier: 43-128 characters of URL-safe random string
    code_verifier = secrets.token_urlsafe(64)[:128]
    
    # code_challenge: SHA256 hash of code_verifier, base64url encoded
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    
    return code_verifier, code_challenge


# ============================================
# OAuth Flow Functions
# ============================================
def get_authorization_url(redirect_uri: str = None) -> Tuple[str, str]:
    """
    Generate Lark OAuth authorization URL with PKCE and state.
    
    Args:
        redirect_uri: OAuth callback URL (uses default if not provided)
    
    Returns:
        Tuple of (authorization_url, state_token)
    """
    _cleanup_expired_states()
    
    if redirect_uri is None:
        redirect_uri = DEFAULT_REDIRECT_URI
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Generate PKCE parameters
    code_verifier, code_challenge = generate_pkce()
    
    # Store state and code_verifier for callback verification
    _oauth_states[state] = {
        'code_verifier': code_verifier,
        'redirect_uri': redirect_uri,
        'created_at': time.time()
    }
    
    # Build authorization URL
    params = {
        "client_id": LARK_APP_ID,
        "redirect_uri": redirect_uri,
        "scope": LARK_SCOPES,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    
    auth_url = f"{AUTHORIZE_URL}?{urlencode(params, quote_via=quote)}"
    logger.info(f"Generated Lark authorization URL with state: {state[:10]}...")
    
    return auth_url, state


def validate_state(state: str) -> Optional[Dict[str, Any]]:
    """
    Validate OAuth state and return stored data.
    
    Args:
        state: State parameter from callback
    
    Returns:
        Stored OAuth state data or None if invalid/expired
    """
    _cleanup_expired_states()
    
    if state not in _oauth_states:
        logger.warning(f"Invalid OAuth state: {state[:10] if state else 'None'}...")
        return None
    
    state_data = _oauth_states.pop(state)  # Remove state after use (single-use)
    return state_data


def exchange_code_for_tokens(
    code: str,
    code_verifier: str,
    redirect_uri: str
) -> Dict[str, Any]:
    """
    Exchange authorization code for access and refresh tokens.
    
    Args:
        code: Authorization code from Lark callback
        code_verifier: PKCE code_verifier stored during authorization
        redirect_uri: Same redirect_uri used in authorization request
    
    Returns:
        Dict containing tokens or error information
    """
    token_data = {
        "grant_type": "authorization_code",
        "client_id": LARK_APP_ID,
        "client_secret": LARK_APP_SECRET,
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }
    
    logger.info("Exchanging authorization code for tokens...")
    response = _make_request(TOKEN_URL, method="POST", data=token_data)
    
    # Check for success (code 0 means success in Lark API)
    if str(response.get("code")) != "0":
        error_desc = response.get("error_description") or response.get("msg") or response.get("error") or "Unknown error"
        logger.error(f"Token exchange failed: {error_desc}")
        return {"success": False, "error": error_desc, "code": response.get("code")}
    
    logger.info("Token exchange successful")
    return {
        "success": True,
        "access_token": response.get("access_token"),
        "refresh_token": response.get("refresh_token"),
        "token_type": response.get("token_type"),
        "expires_in": response.get("expires_in"),
        "scope": response.get("scope")
    }


def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """
    Refresh access token using refresh token.
    
    Args:
        refresh_token: Refresh token from previous token exchange
    
    Returns:
        Dict containing new tokens or error information
    """
    token_data = {
        "grant_type": "refresh_token",
        "client_id": LARK_APP_ID,
        "client_secret": LARK_APP_SECRET,
        "refresh_token": refresh_token,
    }
    
    logger.info("Refreshing access token...")
    response = _make_request(TOKEN_URL, method="POST", data=token_data)
    
    if str(response.get("code")) != "0":
        error_desc = response.get("error_description") or response.get("msg") or "Unknown error"
        logger.error(f"Token refresh failed: {error_desc}")
        return {"success": False, "error": error_desc}
    
    logger.info("Token refresh successful")
    return {
        "success": True,
        "access_token": response.get("access_token"),
        "refresh_token": response.get("refresh_token"),  # New refresh token
        "expires_in": response.get("expires_in")
    }


def get_user_info(access_token: str) -> Dict[str, Any]:
    """
    Get authenticated user's information from Lark.
    
    Args:
        access_token: User access token from token exchange
    
    Returns:
        Dict containing user info or error information
    """
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    logger.info("Fetching Lark user info...")
    response = _make_request(USER_INFO_URL, method="GET", headers=headers)
    
    if response.get("code") != 0:
        error_desc = response.get("msg") or "Failed to get user info"
        logger.error(f"User info fetch failed: {error_desc}")
        return {"success": False, "error": error_desc}
    
    user_data = response.get("data", {})
    logger.info(f"User info retrieved: {user_data.get('name', 'Unknown')}")
    
    return {
        "success": True,
        "user_id": user_data.get("user_id") or user_data.get("open_id"),
        "open_id": user_data.get("open_id"),
        "union_id": user_data.get("union_id"),
        "name": user_data.get("name"),
        "en_name": user_data.get("en_name"),
        "email": user_data.get("email"),
        "mobile": user_data.get("mobile"),  # Personal/mobile number from Lark
        "employee_no": user_data.get("employee_no"),  # Employee number from Lark (may be None from this API)
        "avatar_url": user_data.get("avatar_url"),
        "avatar_thumb": user_data.get("avatar_thumb"),
        "avatar_middle": user_data.get("avatar_middle"),
        "avatar_big": user_data.get("avatar_big"),
        "tenant_key": user_data.get("tenant_key"),
    }


def get_employee_no_from_contact_api(open_id: str) -> Optional[str]:
    """
    Get employee_no from Lark Contact API using tenant_access_token.
    The basic user_info API doesn't return employee_no, so we need to call Contact API.
    
    Args:
        open_id: User's open_id from authentication
    
    Returns:
        Employee number string or None if not available
    """
    # Import here to avoid circular imports
    from app.services.lark_service import get_tenant_access_token
    
    tenant_token = get_tenant_access_token()
    if not tenant_token:
        logger.warning("Could not get tenant_access_token for Contact API")
        return None
    
    # Call Contact API to get user details including employee_no
    url = f"{CONTACT_USER_URL}/{open_id}?user_id_type=open_id"
    headers = {
        "Authorization": f"Bearer {tenant_token}"
    }
    
    logger.info(f"Fetching employee_no from Contact API for open_id: {open_id[:10]}...")
    response = _make_request(url, method="GET", headers=headers)
    
    if response.get("code") != 0:
        error_msg = response.get("msg") or "Unknown error"
        logger.warning(f"Contact API failed: {error_msg} (code: {response.get('code')})")
        return None
    
    user_data = response.get("data", {}).get("user", {})
    employee_no = user_data.get("employee_no")
    
    if employee_no:
        logger.info(f"Employee number retrieved from Contact API: {employee_no}")
    else:
        logger.warning("Employee number not found in Contact API response")
    
    return employee_no


# ============================================
# Complete OAuth Flow Helper
# ============================================
def complete_oauth_flow(code: str, state: str) -> Dict[str, Any]:
    """
    Complete the OAuth flow: validate state, exchange code, get user info.
    
    Args:
        code: Authorization code from callback
        state: State parameter from callback
    
    Returns:
        Dict containing user info and tokens, or error
    """
    # Validate state
    state_data = validate_state(state)
    if not state_data:
        return {"success": False, "error": "Invalid or expired state parameter (CSRF protection)"}
    
    code_verifier = state_data.get('code_verifier')
    redirect_uri = state_data.get('redirect_uri')
    
    # Exchange code for tokens
    token_result = exchange_code_for_tokens(code, code_verifier, redirect_uri)
    if not token_result.get("success"):
        return token_result
    
    # Get user info
    user_result = get_user_info(token_result["access_token"])
    if not user_result.get("success"):
        return user_result
    
    # Get employee_no from Contact API (basic user_info API doesn't return it)
    employee_no = user_result.get("employee_no")
    if not employee_no and user_result.get("open_id"):
        employee_no = get_employee_no_from_contact_api(user_result.get("open_id"))
    
    # Combine results
    return {
        "success": True,
        "user": {
            "user_id": user_result.get("user_id"),
            "open_id": user_result.get("open_id"),
            "name": user_result.get("name"),
            "email": user_result.get("email"),
            "avatar_url": user_result.get("avatar_url"),
            "tenant_key": user_result.get("tenant_key"),
            "employee_no": employee_no,  # Employee Number from Contact API
            "mobile": user_result.get("mobile"),  # Personal Number from Lark
        },
        "tokens": {
            "access_token": token_result.get("access_token"),
            "refresh_token": token_result.get("refresh_token"),
            "expires_in": token_result.get("expires_in"),
        }
    }


# ============================================
# Session Integration Helpers
# ============================================
def create_lark_session_data(user_info: Dict, tokens: Dict) -> Dict[str, Any]:
    """
    Create session data from Lark OAuth result.
    
    Args:
        user_info: User information from Lark
        tokens: OAuth tokens
    
    Returns:
        Session data dict for storage
    """
    return {
        "auth_type": "lark",
        "user_id": user_info.get("user_id"),
        "open_id": user_info.get("open_id"),
        "username": user_info.get("name") or user_info.get("email") or user_info.get("user_id"),
        "name": user_info.get("name"),
        "email": user_info.get("email"),
        "avatar_url": user_info.get("avatar_url"),
        "tenant_key": user_info.get("tenant_key"),
        "access_token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token"),
        "token_expires_in": tokens.get("expires_in"),
        "authenticated_at": time.time()
    }
