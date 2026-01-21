"""
HR Authentication Module
Handles session-based authentication for HR dashboard access.
"""
import os
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status, Cookie, Request, Response
import bcrypt

# Configure logging
logger = logging.getLogger(__name__)

# In-memory session store (use Redis/database in production)
sessions = {}

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


def create_session(username: str, hours: int = 8) -> str:
    """Create a new session for an authenticated user"""
    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = {
        "username": username,
        "created": datetime.now(),
        "expires": datetime.now() + timedelta(hours=hours)
    }
    logger.info(f"Session created for user: {username}")
    return session_id


def get_session(session_id: str) -> Optional[dict]:
    """Get session data if valid and not expired"""
    if not session_id or session_id not in sessions:
        return None
    
    session = sessions[session_id]
    
    # Check expiration
    if datetime.now() > session["expires"]:
        del sessions[session_id]
        logger.info(f"Session expired for user: {session['username']}")
        return None
    
    return session


def delete_session(session_id: str) -> bool:
    """Delete a session (logout)"""
    if session_id in sessions:
        username = sessions[session_id].get("username", "unknown")
        del sessions[session_id]
        logger.info(f"Session deleted for user: {username}")
        return True
    return False


def verify_session(hr_session: str = Cookie(None)) -> str:
    """
    Dependency to verify HR session.
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
