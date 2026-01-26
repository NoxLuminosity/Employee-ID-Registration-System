"""
Security Routes - Screenshot & Recording Detection Logging
Provides API endpoints for logging detected screenshot/recording attempts.
"""

from fastapi import APIRouter, Request, HTTPException, Cookie
from fastapi.responses import JSONResponse
from datetime import datetime
import logging
from typing import Optional
from app.database import (
    insert_security_event, 
    get_security_events,
    init_sqlite_db
)
from app.auth import get_session

router = APIRouter(prefix="/api/security", tags=["security"])
logger = logging.getLogger(__name__)


@router.post("/log-attempt")
async def log_screenshot_attempt(request: Request, hr_session: Optional[str] = Cookie(None)):
    """
    Log screenshot or screen recording detection events.
    Called by client-side JavaScript when detection occurs.
    
    No authentication required (client-side initiated).
    Logs are created for audit trail and security analysis.
    """
    try:
        # Parse JSON body
        try:
            payload = await request.json()
        except:
            # If no JSON body, try to extract from query params
            payload = dict(request.query_params)
        
        event_type = payload.get("event_type", "unknown")
        details = payload.get("details", "")
        user_agent = payload.get("user_agent", request.headers.get("user-agent", ""))
        url = payload.get("url", request.url.path)
        screen_resolution = payload.get("screen_resolution", "unknown")
        timestamp_client = payload.get("timestamp", datetime.utcnow().isoformat())
        
        # Try to get user info from session if available
        user_id = None
        username = "anonymous"
        if hr_session:
            session = get_session(hr_session)
            if session:
                username = session.get("username", "anonymous")
                user_id = session.get("user_id")
        
        # Log to database
        event_id = insert_security_event(
            event_type=event_type,
            details=details,
            user_id=user_id,
            username=username,
            url=url,
            user_agent=user_agent,
            screen_resolution=screen_resolution,
            timestamp_client=timestamp_client,
        )
        
        logger.warning(
            f"[SECURITY EVENT] Type: {event_type} | User: {username} | "
            f"URL: {url} | Details: {details}"
        )
        
        return JSONResponse({
            "success": True,
            "message": "Event logged successfully",
            "event_id": event_id,
        })
        
    except Exception as e:
        logger.error(f"Error logging security event: {str(e)}")
        # Don't fail silently - return error but log occurred
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": str(e),
            }
        )


@router.get("/events")
async def get_security_audit_log(hr_session: str = Cookie(None), limit: int = 100, offset: int = 0):
    """
    Retrieve security event audit log.
    Only accessible to HR users with admin privileges.
    
    Query Parameters:
    - limit: Number of events to return (default: 100, max: 1000)
    - offset: Pagination offset (default: 0)
    """
    # Authentication check - only HR admins
    if not hr_session:
        raise HTTPException(status_code=401, detail="Unauthorized - HR session required")
    
    session = get_session(hr_session)
    if not session or session.get("auth_type") != "password":
        raise HTTPException(status_code=403, detail="Forbidden - HR admin privileges required")
    
    # Limit max results
    limit = min(int(limit), 1000)
    offset = max(int(offset), 0)
    
    try:
        events = get_security_events(limit=limit, offset=offset)
        
        return JSONResponse({
            "success": True,
            "total": len(events),
            "limit": limit,
            "offset": offset,
            "events": events,
        })
        
    except Exception as e:
        logger.error(f"Error retrieving security events: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve events")


@router.get("/events/by-user/{username}")
async def get_user_security_events(
    username: str,
    hr_session: str = Cookie(None),
    limit: int = 50,
):
    """
    Retrieve security events for a specific user.
    Only accessible to HR admins.
    """
    if not hr_session:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    session = get_session(hr_session)
    if not session or session.get("auth_type") != "password":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        events = get_security_events(username=username, limit=limit)
        
        return JSONResponse({
            "success": True,
            "username": username,
            "total": len(events),
            "events": events,
        })
        
    except Exception as e:
        logger.error(f"Error retrieving user security events: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve events")


@router.get("/stats")
async def get_security_statistics(hr_session: str = Cookie(None)):
    """
    Get aggregated security statistics.
    Only accessible to HR admins.
    """
    if not hr_session:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    session = get_session(hr_session)
    if not session or session.get("auth_type") != "password":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        from app.database import get_security_statistics as db_stats
        stats = db_stats()
        
        return JSONResponse({
            "success": True,
            "statistics": stats,
        })
        
    except Exception as e:
        logger.error(f"Error retrieving security statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")
