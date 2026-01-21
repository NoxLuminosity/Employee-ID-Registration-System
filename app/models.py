"""
Pydantic Models for API Request/Response
"""
from pydantic import BaseModel
from typing import Optional


class GenerateHeadshotRequest(BaseModel):
    """Request model for generate-headshot endpoint"""
    image: str  # Base64-encoded image


class RemoveBackgroundRequest(BaseModel):
    """Request model for remove-background endpoint"""
    image: str  # URL or base64-encoded image
    is_url: bool = True  # True if image is a URL, False if base64


class EmployeeBase(BaseModel):
    """Base employee model"""
    employee_name: str
    id_nickname: Optional[str] = None
    id_number: str
    position: str
    department: str
    email: Optional[str] = None
    personal_number: Optional[str] = None
    emergency_name: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_address: Optional[str] = None


class EmployeeResponse(EmployeeBase):
    """Employee response model with all fields"""
    id: int
    photo_path: Optional[str] = None
    photo_url: Optional[str] = None
    new_photo: bool = True
    new_photo_url: Optional[str] = None
    nobg_photo_url: Optional[str] = None
    signature_path: Optional[str] = None
    signature_url: Optional[str] = None
    status: str = "Reviewing"
    date_last_modified: Optional[str] = None
    id_generated: bool = False
    render_url: Optional[str] = None

    class Config:
        from_attributes = True
