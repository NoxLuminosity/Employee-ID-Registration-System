"""
HR Authentication Module
Handles JWT-based authentication for HR dashboard access.

VERCEL FIX: In-memory sessions don't work in serverless environments because
each function invocation creates a new instance. JWT tokens are stateless
and work perfectly in serverless - the token itself contains all session info
and is verified by signature, not by server-side storage.
"""
import os
import secrets
import logging
import json
import base64
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status, Cookie, Request, Response
import bcrypt

# Configure logging
logger = logging.getLogger(__name__)

# JWT Secret - use environment variable or generate a secure default
# IMPORTANT: Set JWT_SECRET in Vercel environment variables for production security
JWT_SECRET = os.environ.get('JWT_SECRET', 'hr-dashboard-jwt-secret-key-2026-change-in-production')

# Cache for hashed passwords to avoid rehashing on every request
_hr_users_cache = None


def _truncate_password(password: str) -> bytes:
    """Truncate password to 72 bytes for bcrypt compatibility and return bytes"""
    if not password:
        return b""
    # Encode to bytes to check byte-length (bcrypt limit is 72 bytes)
    encoded = password.encode('utf-8')
    return encoded[:72]


def _hash_password(password: str) -> str:
    """Hash a password with direct bcrypt"""
    truncated = _truncate_password(password)
    # bcrypt.hashpw expects bytes and returns bytes
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(truncated, salt)
    return hashed.decode('utf-8')


def get_hr_users():
    """Get HR users from environment or use defaults"""
    global _hr_users_cache
    
    # Return cached users if available
    if _hr_users_cache is not None:
        return _hr_users_cache
    
    users = {}
    
    # Check for environment variable HR_USERS (format: "user1:pass1,user2:pass2")
    env_users = os.environ.get('HR_USERS')
    if env_users:
        for pair in env_users.split(','):
            if ':' in pair:
                username, password = pair.split(':', 1)
                username = username.strip()
                password = password.strip()
                try:
                    users[username] = _hash_password(password)
                except Exception as e:
                    logger.error(f"Error hashing password for user {username}: {e}")
    
    # Default users if none configured
    if not users:
        try:
            users = {
                "hradmin": _hash_password("HR@2026"),
            }
            logger.info("Using default HR credentials (hradmin)")
        except Exception as e:
            logger.error(f"Critical error hashing default password: {e}")
            # Fallback (though _hash_password with short string shouldn't fail)
            users = {"hradmin": "FAILED_TO_HASH"}
    
    _hr_users_cache = users
    return users


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash using direct bcrypt"""
    try:
        if not hashed_password or hashed_password == "FAILED_TO_HASH":
            return False
            
        truncated = _truncate_password(plain_password)
        # Ensure hashed_password is bytes for bcrypt
        if isinstance(hashed_password, str):
            hashed_bytes = hashed_password.encode('utf-8')
        else:
            hashed_bytes = hashed_password
            
        return bcrypt.checkpw(truncated, hashed_bytes)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


# ============================================
# JWT Token Functions (Serverless Compatible)
# ============================================
# These functions replace in-memory sessions with stateless JWT tokens
# that work correctly in Vercel's serverless environment.

def _base64url_encode(data: bytes) -> str:
    """Base64 URL-safe encoding without padding"""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def _base64url_decode(data: str) -> bytes:
    """Base64 URL-safe decoding with padding restoration"""
    padding = 4 - len(data) % 4
    if padding != 4:
        data += '=' * padding
    return base64.urlsafe_b64decode(data)


def create_session(username: str, hours: int = 8) -> str:
    """
    Create a JWT token for an authenticated user.
    
    VERCEL FIX: Instead of storing session in memory (which is lost between
    function invocations), we create a signed JWT token. The token contains
    all session info and is verified by its HMAC signature.
    """
    # JWT Header
    header = {"alg": "HS256", "typ": "JWT"}
    
    # JWT Payload with expiration
    now = datetime.utcnow()
    payload = {
        "sub": username,  # Subject (username)
        "iat": int(now.timestamp()),  # Issued at
        "exp": int((now + timedelta(hours=hours)).timestamp()),  # Expiration
    }
    
    # Encode header and payload
    header_b64 = _base64url_encode(json.dumps(header).encode('utf-8'))
    payload_b64 = _base64url_encode(json.dumps(payload).encode('utf-8'))
    
    # Create signature
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        JWT_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    signature_b64 = _base64url_encode(signature)
    
    token = f"{header_b64}.{payload_b64}.{signature_b64}"
    logger.info(f"JWT token created for user: {username}")
    return token


def get_session(token: str) -> Optional[dict]:
    """
    Verify JWT token and return session data if valid.
    
    VERCEL FIX: This verifies the token signature and expiration without
    needing any server-side storage. Works perfectly in serverless.
    """
    if not token:
        return None
    
    try:
        # Split token into parts
        parts = token.split('.')
        if len(parts) != 3:
            logger.warning("Invalid JWT format: wrong number of parts")
            return None
        
        header_b64, payload_b64, signature_b64 = parts
        
        # Verify signature
        message = f"{header_b64}.{payload_b64}"
        expected_signature = hmac.new(
            JWT_SECRET.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        actual_signature = _base64url_decode(signature_b64)
        
        if not hmac.compare_digest(expected_signature, actual_signature):
            logger.warning("Invalid JWT signature")
            return None
        
        # Decode payload
        payload = json.loads(_base64url_decode(payload_b64).decode('utf-8'))
        
        # Check expiration
        exp = payload.get('exp', 0)
        if datetime.utcnow().timestamp() > exp:
            logger.info(f"JWT token expired for user: {payload.get('sub', 'unknown')}")
            return None
        
        # Return session-like dict for compatibility
        return {
            "username": payload.get('sub'),
            "created": datetime.fromtimestamp(payload.get('iat', 0)),
            "expires": datetime.fromtimestamp(exp)
        }
        
    except Exception as e:
        logger.error(f"JWT verification error: {e}")
        return None


def delete_session(token: str) -> bool:
    """
    'Delete' a session - for JWT, this is handled client-side by removing the cookie.
    This function exists for API compatibility but doesn't need to do anything server-side.
    """
    # JWT tokens are stateless - deletion happens by removing the cookie
    logger.info("Session deletion requested (client will remove cookie)")
    return True


def verify_session(hr_session: str = Cookie(None)) -> str:
    """
    Dependency to verify HR session (JWT token).
    Use with Depends() to protect routes.
    
    Returns username if valid, raises HTTPException if not.
    """
    session = get_session(hr_session)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please login.",
            headers={"Location": "/hr/login"}
        )
    
    return session["username"]


def verify_session_optional(hr_session: str = Cookie(None)) -> Optional[str]:
    """
    Optional session verification - returns None instead of raising exception.
    Use for routes that work differently for authenticated vs anonymous users.
    """
    session = get_session(hr_session)
    return session["username"] if session else None


def authenticate_user(username: str, password: str) -> bool:
    """Authenticate a user with username and password"""
    hr_users = get_hr_users()
    
    if username not in hr_users:
        logger.warning(f"Login attempt with unknown username: {username}")
        return False
    
    if not verify_password(password, hr_users[username]):
        logger.warning(f"Failed login attempt for user: {username}")
        return False
    
    logger.info(f"User authenticated: {username}")
    return True


def clear_user_cache():
    """Clear the cached HR users (useful for testing or reloading)"""
    global _hr_users_cache
    _hr_users_cache = None
