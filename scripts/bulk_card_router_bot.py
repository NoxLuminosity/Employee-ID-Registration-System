#!/usr/bin/env python3
"""
Bulk ID Card Router V2 - SPMC (Base Assistant / Bot Messaging)
================================================================
Production-ready Python 3.10+ script that processes ID Requests from
Lark Base and routes notifications to printing POCs using branch
proximity fallback logic with haversine distance calculation.

NOTE ON "BASE ASSISTANT":
The Lark "Base Assistant" is a built-in notification system that sends
automatic updates for Base (Bitable) events. There is NO public API to
send messages AS the Base Assistant directly.

This script uses the **Lark IM Bot API** instead, which:
- Sends messages from your Lark App's bot
- Supports rich text, links, and formatting
- Can reach any Lark user via email resolution
- Is the official, production-ready approach for notifications

WORKFLOW:
1. Fetch pending records (status=="Completed", email_sent=false, id_card not empty)
2. Resolve printer branch using haversine proximity fallback logic
3. Group records by resolved_printer_branch
4. Send ONE bot message per group with all ID card links
5. Update records: email_sent=true, batch_id, resolved_printer_branch

BRANCH PROXIMITY LOGIC:
- If location_branch is in POC_BRANCHES (and not Parañaque): use as-is
- Otherwise: compute nearest POC branch using haversine distance
- Parañaque is explicitly excluded and falls back to nearest

SAFETY FEATURES:
- DRY_RUN mode: Prints message content instead of sending
- Idempotent: Running multiple times won't resend messages
- Test mode: All messages go to TEST_RECIPIENT_EMAIL

USAGE:
    python scripts/bulk_card_router_bot.py              # DRY_RUN mode
    python scripts/bulk_card_router_bot.py --send       # Actually send messages
    python scripts/bulk_card_router_bot.py --verbose    # Debug logging
    python scripts/bulk_card_router_bot.py --test-email kzyrellyan@gmail.com
    python scripts/bulk_card_router_bot.py --help       # Show help

Author: SPMC IT Team
Python: 3.10+
Version: 2.0.0 (with haversine proximity)
"""
from __future__ import annotations

import os
import sys
import io
import json
import uuid
import time
import logging
import argparse
import math
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

# Fix encoding for Windows PowerShell
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library is required. Install with: pip install requests")
    sys.exit(1)

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# ============================================
# BRANCH COORDINATES AND POC CONFIGURATION
# ============================================

# List of valid POC branches (branches with printing POCs)
# NOTE: Parañaque has a real POC but MUST be excluded for now - uses fallback
POC_BRANCHES: set[str] = {
    "San Carlos",
    "Pagadian City",
    "Zamboanga City",
    "Malolos City",
    "San Fernando City",
    "Cagayan De Oro",
    "Tagum City",
    "Davao City",
    "Cebu City",
    "Batangas",
    "General Santos City",
    "Bacolod",
    "Ilo-Ilo",
    "Quezon City",
    "Calamba City",
}

# Branch coordinates mapping (latitude, longitude)
# TODO: Verify and update coordinates with actual office locations
# These are approximate city/municipality center coordinates
BRANCH_COORDS: dict[str, tuple[float, float]] = {
    # POC Branches (with printing capabilities)
    "San Carlos": (15.9290, 120.3510),           # Pangasinan
    "Pagadian City": (7.8242, 123.4375),         # Zamboanga del Sur
    "Zamboanga City": (6.9214, 122.0790),        # Zamboanga Peninsula
    "Malolos City": (14.8431, 120.8082),         # Bulacan
    "San Fernando City": (15.0286, 120.6851),    # Pampanga
    "Cagayan De Oro": (8.4542, 124.6319),        # Misamis Oriental
    "Tagum City": (7.4480, 125.8078),            # Davao del Norte
    "Davao City": (7.1907, 125.4553),            # Davao Region
    "Cebu City": (10.3157, 123.8854),            # Cebu
    "Batangas": (13.7565, 121.0583),             # Batangas City
    "General Santos City": (6.1164, 125.1716),   # South Cotabato
    "Bacolod": (10.6407, 122.9320),              # Negros Occidental
    "Ilo-Ilo": (10.7202, 122.5621),              # Iloilo City
    "Quezon City": (14.6760, 121.0437),          # NCR
    "Calamba City": (14.2112, 121.1654),         # Laguna
    
    # Non-POC Branches (need fallback to nearest POC)
    "Parañaque": (14.4793, 121.0198),            # Excluded - uses fallback
    "Manila": (14.5995, 120.9842),               # NCR
    "Makati": (14.5547, 121.0244),               # NCR
    "Pasig": (14.5764, 121.0851),                # NCR
    "Taguig": (14.5176, 121.0509),               # NCR
    "Mandaluyong": (14.5794, 121.0359),          # NCR
    "Pasay": (14.5378, 121.0014),                # NCR
    "Las Piñas": (14.4445, 120.9929),            # NCR
    "Muntinlupa": (14.4081, 121.0415),           # NCR
    "Marikina": (14.6507, 121.1029),             # NCR
    "San Juan": (14.6027, 121.0356),             # NCR
    "Valenzuela": (14.7004, 120.9830),           # NCR
    "Navotas": (14.6667, 120.9417),              # NCR
    "Pateros": (14.5456, 121.0673),              # NCR
    "Antipolo": (14.5860, 121.1761),             # Rizal
    "Cainta": (14.5779, 121.1222),               # Rizal
    "Taytay": (14.5594, 121.1354),               # Rizal
    "Angono": (14.5286, 121.1536),               # Rizal
    "Binangonan": (14.4655, 121.1996),           # Rizal
    "Rodriguez": (14.7467, 121.1392),            # Rizal (Montalban)
    "San Mateo": (14.6987, 121.1176),            # Rizal
    "Cavite City": (14.4791, 120.8961),          # Cavite
    "Bacoor": (14.4624, 120.9645),               # Cavite
    "Imus": (14.4297, 120.9367),                 # Cavite
    "Dasmariñas": (14.3294, 120.9367),           # Cavite
    "General Trias": (14.3874, 120.8814),        # Cavite
    "Tagaytay": (14.1153, 120.9621),             # Cavite
    "Santa Rosa": (14.3122, 121.1114),           # Laguna
    "Biñan": (14.3419, 121.0846),                # Laguna
    "San Pedro": (14.3595, 121.0476),            # Laguna
    "Los Baños": (14.1680, 121.2415),            # Laguna
    "Lipa City": (13.9411, 121.1635),            # Batangas
    "Tanauan": (14.0854, 121.1484),              # Batangas
    "Lucena City": (13.9316, 121.6170),          # Quezon Province
    "Naga City": (13.6218, 123.1948),            # Camarines Sur
    "Legazpi": (13.1391, 123.7438),              # Albay
    "Tacloban": (11.2543, 124.9631),             # Leyte
    "Ormoc": (11.0064, 124.6077),                # Leyte
    "Dumaguete": (9.3068, 123.3054),             # Negros Oriental
    "Baguio": (16.4023, 120.5960),               # Benguet
    "Dagupan": (16.0433, 120.3345),              # Pangasinan
    "Olongapo": (14.8292, 120.2830),             # Zambales
    "Angeles City": (15.1450, 120.5887),         # Pampanga
    "Tarlac City": (15.4755, 120.5963),          # Tarlac
    "Cabanatuan": (15.4869, 120.9699),           # Nueva Ecija
    "Puerto Princesa": (9.7489, 118.7464),       # Palawan
    "Butuan": (8.9475, 125.5406),                # Agusan del Norte
    "Surigao": (9.7896, 125.4988),               # Surigao del Norte
    "Dipolog": (8.5893, 123.3420),               # Zamboanga del Norte
    "Ozamiz": (8.1481, 123.8411),                # Misamis Occidental
    "Iligan": (8.2280, 124.2452),                # Lanao del Norte
    "Marawi": (7.9986, 124.2928),                # Lanao del Sur
    "Cotabato City": (7.2047, 124.2310),         # Maguindanao
    "Koronadal": (6.5027, 124.8467),             # South Cotabato
    "Kidapawan": (7.0084, 125.0894),             # Cotabato
}

# POC Labels for reference (not used for credentials/recipients)
# These are human-readable labels for documentation purposes only
POC_LABELS: dict[str, str] = {
    "San Carlos": "SPM - @Zacarias, Reynaldo Jr Mamaril(HR PITX)",
    "Pagadian City": "SPM @Melvin Calugay | PIF | GENSAN (PMCY)",
    "Zamboanga City": "SPM @Mira Mukim | PIF ZMB (QNAM)",
    "Malolos City": "SPM @Aeron Tasic | PIF |MAL |MAPT",
    "San Fernando City": "SPM @Jojo Salomon | PIF | PAM (MJSM)",
    "Cagayan De Oro": "SPM @Aldrin Bautista │ PIF │ CDO (QADB)",
    "Tagum City": "SPM @Kemy Revilla",
    "Davao City": "SPM @Rona Sindatoc(BNB-MSME NWOFF DAVAO)",
    "Cebu City": "SPM - @Jenemae Manila(HR Services Ceb)",
    "Batangas": "SPM @Queenie Caraulia | PIF |BATANGAS | PQGC",
    "General Santos City": "SPM @As-addah Maminasacan | PIF | GEN(GASM)",
    "Bacolod": "SPM @Nerio, Louie Rose Ponciano(PIF BACOLOD| BLON)",
    "Ilo-Ilo": "SPM @Maerci del Monte | PIF | ILOILO(MMDD)",
    "Quezon City": "SPM - @Queen Mary Bernaldez (HR QC)",
    "Calamba City": "SPM - @Cherrylyn Albis | PIF | CALAMBA (MCRA)",
}


# ============================================
# Configuration
# ============================================

@dataclass
class Config:
    """Configuration settings for the bulk card router."""
    
    # Lark App Credentials
    LARK_APP_ID: str = field(default_factory=lambda: os.getenv('LARK_APP_ID', ''))
    LARK_APP_SECRET: str = field(default_factory=lambda: os.getenv('LARK_APP_SECRET', ''))
    
    # Lark Base (Bitable) Configuration
    BITABLE_APP_TOKEN: str = field(default_factory=lambda: os.getenv('LARK_BITABLE_ID', ''))
    ID_REQUESTS_TABLE_ID: str = field(default_factory=lambda: os.getenv('LARK_TABLE_ID', ''))
    
    # Test Recipient (all messages go here in test mode)
    TEST_RECIPIENT_EMAIL: str = 'mmanuel@spmadridlaw.com'
    
    # Operation Modes
    DRY_RUN: bool = True  # Set to False to actually send messages
    TEST_MODE: bool = True  # All messages go to TEST_RECIPIENT_EMAIL when True
    
    # Request Settings
    REQUEST_TIMEOUT_SECONDS: int = 30
    MAX_RECORDS_PER_RUN: int = 500
    
    # Lark API Endpoints
    TOKEN_URL: str = 'https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal'
    BITABLE_BASE_URL: str = 'https://open.larksuite.com/open-apis/bitable/v1/apps'
    USER_BY_EMAIL_URL: str = 'https://open.larksuite.com/open-apis/contact/v3/users/batch_get_id'
    IM_MESSAGE_URL: str = 'https://open.larksuite.com/open-apis/im/v1/messages'
    
    def validate(self) -> bool:
        """Validate required configuration is present."""
        required = [
            ('LARK_APP_ID', self.LARK_APP_ID),
            ('LARK_APP_SECRET', self.LARK_APP_SECRET),
            ('BITABLE_APP_TOKEN', self.BITABLE_APP_TOKEN),
            ('ID_REQUESTS_TABLE_ID', self.ID_REQUESTS_TABLE_ID),
        ]
        
        missing = [name for name, value in required if not value]
        if missing:
            logger.error(f"Missing required config: {', '.join(missing)}")
            return False
        return True


# Initialize configuration
config = Config()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================
# Data Models
# ============================================

@dataclass
class IDCardRecord:
    """Represents an ID card record from Lark Base."""
    record_id: str
    employee_name: str
    id_number: str = ''
    position: str = ''
    location_branch: str = ''
    email: str = ''
    id_card: str = ''  # Cloudinary-hosted PDF URL
    
    # Automation fields
    email_sent: bool = False  # CHECKBOX field
    batch_id: str = ''
    resolved_printer_branch: str = ''
    status: str = ''
    
    @classmethod
    def from_lark_record(cls, record: dict[str, Any]) -> 'IDCardRecord':
        """
        Create IDCardRecord from Lark Bitable record.
        
        CHECKBOX HANDLING:
        - Lark Base returns checkbox values as boolean True/False
        - Some API versions may return string "true"/"false"
        - We normalize to Python boolean
        """
        fields = record.get('fields', {})
        
        def get_str(field_name: str, default: str = '') -> str:
            """Extract string value from field, handling URL field format."""
            value = fields.get(field_name, default)
            if isinstance(value, dict):
                # Lark URL field format: {"link": "...", "text": "..."}
                return value.get('link', '') or value.get('url', '') or value.get('text', '')
            return str(value) if value is not None else default
        
        def get_bool(field_name: str, default: bool = False) -> bool:
            """
            Extract boolean value from CHECKBOX field.
            
            Lark CHECKBOX fields can be:
            - True/False (boolean)
            - "true"/"false" (string in some API versions)
            """
            value = fields.get(field_name, default)
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', 'yes', '1', 'checked')
            if isinstance(value, (int, float)):
                return bool(value)
            return default
        
        return cls(
            record_id=record.get('record_id', ''),
            employee_name=get_str('employee_name'),
            id_number=get_str('id_number'),
            position=get_str('position'),
            location_branch=get_str('location_branch'),
            email=get_str('email'),
            id_card=get_str('id_card'),
            email_sent=get_bool('email_sent', False),
            batch_id=get_str('batch_id'),
            resolved_printer_branch=get_str('resolved_printer_branch'),
            status=get_str('status'),
        )


# ============================================
# Haversine Distance Calculation
# ============================================

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth
    using the Haversine formula.
    
    Args:
        lat1, lon1: Latitude and longitude of point 1 (in degrees)
        lat2, lon2: Latitude and longitude of point 2 (in degrees)
    
    Returns:
        Distance in kilometers
    """
    # Earth's radius in kilometers
    R = 6371.0
    
    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    # Haversine formula
    a = math.sin(delta_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


def compute_nearest_poc_branch(location_branch: str) -> str:
    """
    Compute the nearest POC branch for a given location.
    
    Algorithm:
    1. If location_branch is in POC_BRANCHES and NOT Parañaque: return as-is
    2. Otherwise: compute haversine distance to all POC branches and return nearest
    
    Args:
        location_branch: The employee's branch location
    
    Returns:
        The resolved printer branch (either same as input or nearest POC)
    """
    # Normalize input
    location_branch = location_branch.strip()
    
    # Rule 1: If in POC branches and NOT Parañaque, use as-is
    if location_branch in POC_BRANCHES and location_branch != "Parañaque":
        logger.debug(f"Branch '{location_branch}' is a POC branch - using as-is")
        return location_branch
    
    # Rule 2: Need to find nearest POC branch
    if location_branch not in BRANCH_COORDS:
        logger.warning(f"Branch '{location_branch}' not found in BRANCH_COORDS - defaulting to 'Quezon City'")
        # Default to Quezon City if coordinates unknown
        return "Quezon City"
    
    # Get source coordinates
    src_lat, src_lon = BRANCH_COORDS[location_branch]
    
    # Find nearest POC branch
    min_distance = float('inf')
    nearest_branch = "Quezon City"  # Default fallback
    
    for poc_branch in POC_BRANCHES:
        if poc_branch not in BRANCH_COORDS:
            continue
        
        poc_lat, poc_lon = BRANCH_COORDS[poc_branch]
        distance = haversine_distance(src_lat, src_lon, poc_lat, poc_lon)
        
        if distance < min_distance:
            min_distance = distance
            nearest_branch = poc_branch
    
    logger.info(f"Branch '{location_branch}' -> nearest POC: '{nearest_branch}' ({min_distance:.1f} km)")
    return nearest_branch


# ============================================
# Token Cache & User Resolution Cache
# ============================================

_cached_token: Optional[str] = None
_token_expiry: float = 0
_user_id_cache: dict[str, str] = {}  # email -> user_id


def get_tenant_access_token() -> Optional[str]:
    """
    Get Lark tenant access token with caching.
    
    Caches token and auto-refreshes 5 minutes before expiry.
    """
    global _cached_token, _token_expiry
    
    # Return cached token if still valid (with 5 min buffer)
    if _cached_token and time.time() < (_token_expiry - 300):
        return _cached_token
    
    try:
        response = requests.post(
            config.TOKEN_URL,
            json={
                "app_id": config.LARK_APP_ID,
                "app_secret": config.LARK_APP_SECRET
            },
            timeout=config.REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") != 0:
            logger.error(f"Lark token error: {data.get('msg')}")
            return None
        
        _cached_token = data.get("tenant_access_token")
        _token_expiry = time.time() + data.get("expire", 7200)
        
        logger.debug("Lark tenant access token obtained")
        return _cached_token
        
    except requests.RequestException as e:
        logger.error(f"Failed to get Lark access token: {e}")
        return None


def resolve_user_for_base_assistant(email: str) -> Optional[str]:
    """
    Resolve user email to Lark user_id for bot messaging.
    
    Uses the Lark Contact API to look up users by email.
    Caches results per run for efficiency.
    
    Args:
        email: User's email address (e.g., 'mmanuel@spmadridlaw.com')
    
    Returns:
        Lark user_id (open_id format) or None if not found
    """
    # Check cache first
    if email in _user_id_cache:
        logger.debug(f"User {email} found in cache")
        return _user_id_cache[email]
    
    token = get_tenant_access_token()
    if not token:
        return None
    
    try:
        # Use batch_get_id to resolve email to user_id
        response = requests.post(
            config.USER_BY_EMAIL_URL,
            headers={"Authorization": f"Bearer {token}"},
            params={"user_id_type": "open_id"},
            json={"emails": [email]},
            timeout=config.REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") != 0:
            logger.error(f"User lookup error: {data.get('msg')}")
            return None
        
        # Extract user_id from response
        user_list = data.get("data", {}).get("user_list", [])
        if user_list and user_list[0].get("user_id"):
            user_id = user_list[0]["user_id"]
            _user_id_cache[email] = user_id
            logger.debug(f"Resolved {email} to user_id: {user_id[:10]}...")
            return user_id
        else:
            logger.warning(f"User not found for email: {email}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Failed to resolve user {email}: {e}")
        return None


# ============================================
# Lark Base (Bitable) Functions
# ============================================

def fetch_pending_requests() -> list[IDCardRecord]:
    """
    Fetch pending ID card requests from Lark Base.
    
    Criteria:
    - status == "Completed"
    - email_sent == false (checkbox unchecked)
    - id_card is not empty
    
    Uses NOT() syntax for checkbox filtering (Lark quirk).
    
    Returns:
        List of IDCardRecord objects ready for message routing
    """
    token = get_tenant_access_token()
    if not token:
        logger.error("Failed to get Lark access token")
        return []
    
    # Build filter formula
    # CHECKBOX: Use NOT() instead of =FALSE (Lark quirk)
    # ID_CARD: Check it's not empty
    filter_formula = 'AND(CurrentValue.[status]="Completed",NOT(CurrentValue.[email_sent]),CurrentValue.[id_card]!="")'
    
    url = f"{config.BITABLE_BASE_URL}/{config.BITABLE_APP_TOKEN}/tables/{config.ID_REQUESTS_TABLE_ID}/records"
    
    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params={
                "filter": filter_formula,
                "page_size": config.MAX_RECORDS_PER_RUN
            },
            timeout=config.REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") != 0:
            logger.error(f"Bitable query error: {data.get('msg')}")
            return []
        
        # Handle Lark API returning null instead of empty array
        items = data.get("data", {}).get("items") or []
        
        records = [IDCardRecord.from_lark_record(item) for item in items]
        logger.info(f"Fetched {len(records)} pending ID card requests")
        
        return records
        
    except requests.RequestException as e:
        logger.error(f"Failed to fetch pending requests: {e}")
        return []


def update_records(records: list[IDCardRecord], updates: dict[str, Any]) -> bool:
    """
    Update multiple records in Lark Base with the same updates.
    
    Args:
        records: List of records to update
        updates: Dictionary of field updates to apply
    
    Returns:
        True if all updates successful, False otherwise
    """
    token = get_tenant_access_token()
    if not token:
        return False
    
    url = f"{config.BITABLE_BASE_URL}/{config.BITABLE_APP_TOKEN}/tables/{config.ID_REQUESTS_TABLE_ID}/records/batch_update"
    
    # Build batch update request
    records_data = []
    for record in records:
        records_data.append({
            "record_id": record.record_id,
            "fields": updates
        })
    
    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={"records": records_data},
            timeout=config.REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") != 0:
            logger.error(f"Batch update error: {data.get('msg')}")
            return False
        
        logger.info(f"Updated {len(records)} records successfully")
        return True
        
    except requests.RequestException as e:
        logger.error(f"Failed to update records: {e}")
        return False


# ============================================
# Bot Messaging Functions
# ============================================

def build_message_content(resolved_branch: str, records: list[IDCardRecord]) -> str:
    """
    Build message content for a group of records.
    
    Format:
    Header: "ID Cards Ready for Printing – <RESOLVED_BRANCH> (<COUNT> items)"
    Then numbered list:
    "1) <employee_name> | <id_number> | <position>"
    "   <id_card_url>"
    
    Args:
        resolved_branch: The resolved printer branch
        records: List of records in this group
    
    Returns:
        Formatted message text
    """
    lines = []
    
    # Header
    lines.append(f"🆔 ID Cards Ready for Printing – {resolved_branch} ({len(records)} items)")
    lines.append("")
    
    # Numbered list
    for i, record in enumerate(records, 1):
        lines.append(f"{i}) {record.employee_name} | {record.id_number} | {record.position}")
        lines.append(f"   📄 {record.id_card}")
        lines.append("")
    
    # Footer
    lines.append(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return "\n".join(lines)


def send_base_assistant_dm(recipient_id: str, message_text: str) -> bool:
    """
    Send a direct message via Lark IM Bot API.
    
    Args:
        recipient_id: Lark user_id (open_id format)
        message_text: The message content to send
    
    Returns:
        True if message sent successfully, False otherwise
    """
    token = get_tenant_access_token()
    if not token:
        return False
    
    # Build message payload - using text message type
    message_content = json.dumps({
        "text": message_text
    })
    
    try:
        response = requests.post(
            config.IM_MESSAGE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            params={"receive_id_type": "open_id"},
            json={
                "receive_id": recipient_id,
                "msg_type": "text",
                "content": message_content
            },
            timeout=config.REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") != 0:
            logger.error(f"Message send error: {data.get('msg')}")
            return False
        
        message_id = data.get("data", {}).get("message_id", "unknown")
        logger.info(f"Message sent successfully (message_id: {message_id[:10]}...)")
        return True
        
    except requests.RequestException as e:
        logger.error(f"Failed to send message: {e}")
        return False


# ============================================
# Main Processing Logic
# ============================================

def main():
    """
    Main entry point for the bulk card router.
    
    Processing flow:
    1. Validate configuration
    2. Resolve test recipient (if in test mode)
    3. Fetch pending records
    4. Compute resolved_printer_branch for each using haversine fallback
    5. Group by resolved_printer_branch
    6. Send ONE message per group
    7. Update records: email_sent=true, batch_id, resolved_printer_branch
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Bulk ID Card Router - Route ID cards to printing POCs via Lark Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/bulk_card_router_bot.py              # DRY_RUN mode (preview)
  python scripts/bulk_card_router_bot.py --send       # Actually send messages
  python scripts/bulk_card_router_bot.py --verbose    # Debug logging
  python scripts/bulk_card_router_bot.py --test-email someone@example.com
        """
    )
    parser.add_argument('--send', action='store_true',
                        help='Actually send messages (default is DRY_RUN mode)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose/debug logging')
    parser.add_argument('--test-email', type=str,
                        help=f'Override test recipient email (default: {config.TEST_RECIPIENT_EMAIL})')
    args = parser.parse_args()
    
    # Configure based on args
    if args.send:
        config.DRY_RUN = False
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
    if args.test_email:
        config.TEST_RECIPIENT_EMAIL = args.test_email
    
    # Print banner
    print("=" * 60)
    print("BULK ID CARD ROUTER V2 (Base Assistant / Bot Messaging)")
    print("=" * 60)
    print(f"Mode: {'DRY_RUN (preview only)' if config.DRY_RUN else '🚀 LIVE SEND'}")
    print(f"Test Mode: {config.TEST_MODE} (recipient: {config.TEST_RECIPIENT_EMAIL})")
    print(f"POC Branches: {len(POC_BRANCHES)} configured")
    print(f"Branch Coordinates: {len(BRANCH_COORDS)} mapped")
    print("=" * 60)
    print()
    
    # Validate configuration
    if not config.validate():
        print("ERROR: Configuration validation failed. Check .env file.")
        sys.exit(1)
    
    # Step 1: Resolve test recipient
    if config.TEST_MODE:
        print(f"[1/5] Resolving test recipient: {config.TEST_RECIPIENT_EMAIL}")
        test_user_id = resolve_user_for_base_assistant(config.TEST_RECIPIENT_EMAIL)
        if not test_user_id:
            print(f"ERROR: Could not resolve test recipient email: {config.TEST_RECIPIENT_EMAIL}")
            print("       Make sure this email is registered in your Lark organization.")
            sys.exit(1)
        print(f"       ✓ Resolved to user_id: {test_user_id[:20]}...")
        print()
    else:
        test_user_id = None
    
    # Step 2: Fetch pending requests
    print("[2/5] Fetching pending ID card requests from Lark Base...")
    records = fetch_pending_requests()
    
    if not records:
        print("       No pending records found. Nothing to process.")
        print()
        print("=" * 60)
        print("COMPLETED - 0 messages to send")
        print("=" * 60)
        return
    
    print(f"       ✓ Found {len(records)} pending records")
    print()
    
    # Step 3: Compute resolved_printer_branch for each record
    print("[3/5] Computing resolved printer branch for each record...")
    for record in records:
        record.resolved_printer_branch = compute_nearest_poc_branch(record.location_branch)
    print()
    
    # Step 4: Group by resolved_printer_branch
    print("[4/5] Grouping records by resolved printer branch...")
    groups: dict[str, list[IDCardRecord]] = defaultdict(list)
    for record in records:
        groups[record.resolved_printer_branch].append(record)
    
    print(f"       Grouped into {len(groups)} batches:")
    for branch, branch_records in groups.items():
        print(f"         - {branch}: {len(branch_records)} records")
    print()
    
    # Step 5: Send messages and update records
    print("[5/5] Processing batches...")
    print()
    
    batch_id = str(uuid.uuid4())
    total_sent = 0
    total_failed = 0
    
    for resolved_branch, branch_records in groups.items():
        print(f"--- Batch: {resolved_branch} ({len(branch_records)} records) ---")
        
        # Build message content
        message_text = build_message_content(resolved_branch, branch_records)
        
        # Display message preview
        print("Message Preview:")
        print("-" * 40)
        print(message_text)
        print("-" * 40)
        
        # Determine recipient
        if config.TEST_MODE:
            recipient_id = test_user_id
            recipient_label = f"{config.TEST_RECIPIENT_EMAIL} (test mode)"
        else:
            # TODO: Look up real POC email for this branch
            recipient_id = test_user_id  # Fallback to test for now
            recipient_label = f"{config.TEST_RECIPIENT_EMAIL} (POC lookup TODO)"
        
        print(f"Recipient: {recipient_label}")
        
        if config.DRY_RUN:
            print("Action: SKIPPED (DRY_RUN mode)")
            print()
            continue
        
        # Send message
        print("Sending message...")
        if send_base_assistant_dm(recipient_id, message_text):
            print("Action: ✓ MESSAGE SENT")
            
            # Prepare updates
            updates = {
                "email_sent": True,  # CHECKBOX: use boolean True, not string
                "batch_id": batch_id,
                "resolved_printer_branch": resolved_branch
            }
            
            # Update records
            print("Updating records...")
            if update_records(branch_records, updates):
                print("Action: ✓ RECORDS UPDATED")
                total_sent += len(branch_records)
            else:
                print("Action: ✗ RECORD UPDATE FAILED")
                total_failed += len(branch_records)
        else:
            print("Action: ✗ MESSAGE SEND FAILED")
            total_failed += len(branch_records)
        
        print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total Records Processed: {len(records)}")
    print(f"Batches: {len(groups)}")
    print(f"Batch ID: {batch_id}")
    print()
    
    if config.DRY_RUN:
        print("Mode: DRY_RUN (no messages sent, no records updated)")
        print("To actually send messages, run with --send flag")
    else:
        print(f"Records Successfully Sent: {total_sent}")
        print(f"Records Failed: {total_failed}")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
