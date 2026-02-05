#!/usr/bin/env python3
"""
Bulk ID Card Router - SPMC (Base Assistant / Bot Messaging)
===========================================================
Production-ready Python 3.10+ script that automates bulk ID card routing
using Lark Base (Bitable) as the data source and sends notifications via
Lark Bot messaging.

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
2. Resolve printer branch for each record (POC fallback logic)
3. Group records by resolved_printer_branch
4. Send ONE bot message per group with all ID card links
5. Update records: email_sent=true, batch_id, resolved_printer_branch

SAFETY FEATURES:
- DRY_RUN mode: Prints message content instead of sending
- Idempotent: Running multiple times won't resend messages
- Test mode: All messages go to TEST_RECIPIENT_EMAIL

USAGE:
    python scripts/bulk_card_router_bot.py              # DRY_RUN mode
    python scripts/bulk_card_router_bot.py --send       # Actually send messages
    python scripts/bulk_card_router_bot.py --verbose    # Debug logging
    python scripts/bulk_card_router_bot.py --help       # Show help

Author: SPMC IT Team
Python: 3.10+
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
    
    # Branch Routing Table (optional)
    ROUTING_TABLE_ID: str = field(default_factory=lambda: os.getenv('LARK_ROUTING_TABLE_ID', ''))
    
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
class BranchRouting:
    """Represents branch routing configuration."""
    branch: str
    has_poc: bool
    poc_email: str
    nearest_poc_branch: str


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
    
    logger.info(f"Fetching pending records...")
    logger.debug(f"Filter: {filter_formula}")
    
    all_records: list[IDCardRecord] = []
    page_token: Optional[str] = None
    
    while len(all_records) < config.MAX_RECORDS_PER_RUN:
        params = {
            "filter": filter_formula,
            "page_size": min(500, config.MAX_RECORDS_PER_RUN - len(all_records))
        }
        if page_token:
            params["page_token"] = page_token
        
        try:
            response = requests.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
                timeout=config.REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            data = response.json()
            
        except requests.RequestException as e:
            logger.error(f"Lark API request failed: {e}")
            break
        
        if data.get("code") != 0:
            logger.error(f"Lark Bitable read error (code {data.get('code')}): {data.get('msg')}")
            break
        
        # Safely get items
        response_data = data.get("data") or {}
        items = response_data.get("items") or []
        
        for item in items:
            record = IDCardRecord.from_lark_record(item)
            # Double-check criteria
            if (record.status == "Completed" and 
                not record.email_sent and 
                record.id_card):
                all_records.append(record)
        
        # Check for more pages
        page_token = response_data.get("page_token")
        if not page_token:
            break
    
    logger.info(f"Fetched {len(all_records)} pending records")
    return all_records


def fetch_branch_routing() -> dict[str, BranchRouting]:
    """
    Fetch branch routing configuration.
    
    Returns:
        Dict mapping branch names to BranchRouting objects
    """
    # If routing table is configured, fetch from Lark Base
    if config.ROUTING_TABLE_ID:
        return _fetch_routing_from_lark()
    
    # Fallback: Hardcoded routing configuration
    # TODO: Update with your actual branch routing data
    logger.warning("Using hardcoded branch routing (no ROUTING_TABLE_ID configured)")
    return {
        "Main Office": BranchRouting(
            branch="Main Office",
            has_poc=True,
            poc_email="mainoffice@spmadridlaw.com",
            nearest_poc_branch=""
        ),
        "Batangas": BranchRouting(
            branch="Batangas",
            has_poc=True,
            poc_email="batangas@spmadridlaw.com",
            nearest_poc_branch=""
        ),
        "Paranaque": BranchRouting(
            branch="Paranaque",
            has_poc=True,
            poc_email="paranaque@spmadridlaw.com",
            nearest_poc_branch=""
        ),
        # Add more branches as needed
    }


def _fetch_routing_from_lark() -> dict[str, BranchRouting]:
    """Fetch routing configuration from Lark Base routing table."""
    token = get_tenant_access_token()
    if not token:
        return {}
    
    url = f"{config.BITABLE_BASE_URL}/{config.BITABLE_APP_TOKEN}/tables/{config.ROUTING_TABLE_ID}/records"
    routing: dict[str, BranchRouting] = {}
    page_token: Optional[str] = None
    
    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        
        try:
            response = requests.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
                timeout=config.REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch routing table: {e}")
            break
        
        if data.get("code") != 0:
            logger.error(f"Routing table read error: {data.get('msg')}")
            break
        
        response_data = data.get("data") or {}
        items = response_data.get("items") or []
        
        for item in items:
            fields = item.get('fields', {})
            branch = str(fields.get('branch', ''))
            if branch:
                has_poc = fields.get('has_poc', False)
                if isinstance(has_poc, str):
                    has_poc = has_poc.lower() in ('true', 'yes', '1')
                
                routing[branch] = BranchRouting(
                    branch=branch,
                    has_poc=bool(has_poc),
                    poc_email=str(fields.get('poc_email', '')),
                    nearest_poc_branch=str(fields.get('nearest_poc_branch', ''))
                )
        
        page_token = response_data.get("page_token")
        if not page_token:
            break
    
    logger.info(f"Loaded {len(routing)} branch routing entries")
    return routing


def resolve_printer_branch(record: IDCardRecord, routing: dict[str, BranchRouting]) -> str:
    """
    Resolve the printer branch using POC fallback logic.
    
    Routing rules:
    - If has_poc == true → resolved_printer_branch = location_branch
    - If has_poc == false → resolved_printer_branch = nearest_poc_branch
    
    Args:
        record: The ID card record
        routing: Branch routing configuration
    
    Returns:
        Resolved printer branch name
    """
    location = record.location_branch
    
    if location in routing:
        branch_info = routing[location]
        if not branch_info.has_poc and branch_info.nearest_poc_branch:
            logger.debug(f"Routing {location} to {branch_info.nearest_poc_branch} (no POC)")
            return branch_info.nearest_poc_branch
    
    return location


def update_records(records: list[IDCardRecord], batch_id: str, 
                   resolved_branch: str) -> bool:
    """
    Update records in Lark Base after message is sent.
    
    Updates:
    - email_sent = True (CHECK the checkbox)
    - batch_id = generated UUID
    - resolved_printer_branch = computed branch
    
    Args:
        records: List of IDCardRecord objects to update
        batch_id: Unique batch identifier
        resolved_branch: The resolved printer branch
    
    Returns:
        True if all updates succeeded, False otherwise
    """
    if config.DRY_RUN:
        logger.info(f"[DRY_RUN] Would update {len(records)} records:")
        for record in records:
            logger.info(f"  - {record.record_id}: email_sent=True, batch_id={batch_id[:8]}...")
        return True
    
    token = get_tenant_access_token()
    if not token:
        logger.error("Failed to get Lark access token for updates")
        return False
    
    success_count = 0
    for record in records:
        url = (f"{config.BITABLE_BASE_URL}/{config.BITABLE_APP_TOKEN}"
               f"/tables/{config.ID_REQUESTS_TABLE_ID}/records/{record.record_id}")
        
        # CHECKBOX field: Send boolean True to check it
        update_fields = {
            "email_sent": True,
            "batch_id": batch_id,
            "resolved_printer_branch": resolved_branch
        }
        
        try:
            response = requests.put(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json={"fields": update_fields},
                timeout=config.REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 0:
                success_count += 1
                logger.debug(f"Updated record {record.record_id}")
            else:
                logger.error(f"Failed to update {record.record_id}: {data.get('msg')}")
                
        except requests.RequestException as e:
            logger.error(f"Failed to update {record.record_id}: {e}")
    
    logger.info(f"Updated {success_count}/{len(records)} records")
    return success_count == len(records)


# ============================================
# Bot Messaging Functions
# ============================================

def build_message_text(records: list[IDCardRecord], branch: str, batch_id: str) -> str:
    """
    Build plain text message content for a batch of ID cards.
    
    Format:
    ID Cards Ready for Printing – <BRANCH> (<COUNT> items)
    
    1) <employee_name> | <id_number> | <position>
       <id_card_url>
    
    Args:
        records: List of IDCardRecord objects
        branch: The resolved printer branch
        batch_id: Unique batch identifier
    
    Returns:
        Formatted message text
    """
    header = f"ID Cards Ready for Printing – {branch} ({len(records)} items)"
    
    lines = [header, ""]
    
    for i, record in enumerate(records, 1):
        name = record.employee_name or "Unknown"
        id_num = record.id_number or "N/A"
        position = record.position or "N/A"
        url = record.id_card
        
        lines.append(f"{i}) {name} | {id_num} | {position}")
        lines.append(f"   {url}")
        lines.append("")
    
    lines.append(f"Batch ID: {batch_id}")
    lines.append(f"Sent: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return "\n".join(lines)


def build_rich_message(records: list[IDCardRecord], branch: str, batch_id: str) -> dict:
    """
    Build a rich text (interactive card) message for Lark.
    
    Uses Lark's Interactive Card format for better formatting.
    
    Args:
        records: List of IDCardRecord objects
        branch: The resolved printer branch
        batch_id: Unique batch identifier
    
    Returns:
        Message card payload dict
    """
    # Build card elements
    elements = []
    
    # Header
    elements.append({
        "tag": "div",
        "text": {
            "tag": "plain_text",
            "content": f"📋 ID Cards Ready for Printing – {branch}"
        }
    })
    
    elements.append({
        "tag": "div",
        "text": {
            "tag": "plain_text",
            "content": f"Total: {len(records)} card(s)"
        }
    })
    
    elements.append({"tag": "hr"})
    
    # Card items
    for i, record in enumerate(records, 1):
        name = record.employee_name or "Unknown"
        id_num = record.id_number or "N/A"
        position = record.position or "N/A"
        
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**{i}. {name}**\n{id_num} | {position}"
            }
        })
        
        # Download button
        elements.append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": "📥 Download PDF"
                    },
                    "type": "primary",
                    "url": record.id_card
                }
            ]
        })
        
        elements.append({"tag": "hr"})
    
    # Footer
    elements.append({
        "tag": "note",
        "elements": [
            {
                "tag": "plain_text",
                "content": f"Batch: {batch_id[:8]}... | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            }
        ]
    })
    
    # Build card
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {
                "tag": "plain_text",
                "content": "🪪 SPMC ID Card Notification"
            },
            "template": "blue"
        },
        "elements": elements
    }
    
    return card


def send_base_assistant_message(user_id: str, message_text: str, 
                                  card: Optional[dict] = None) -> bool:
    """
    Send a message via Lark IM Bot API.
    
    This sends messages from the Lark App's bot, which is the standard
    way to send programmatic notifications in Lark.
    
    Args:
        user_id: Lark open_id of the recipient
        message_text: Plain text fallback message
        card: Optional interactive card payload
    
    Returns:
        True if message sent successfully, False otherwise
    """
    if config.DRY_RUN:
        logger.info("=" * 60)
        logger.info("[DRY_RUN] Would send bot message:")
        logger.info(f"  To user_id: {user_id[:10]}...")
        logger.info(f"  Message preview:")
        for line in message_text.split('\n')[:10]:
            logger.info(f"    {line}")
        if len(message_text.split('\n')) > 10:
            logger.info(f"    ... ({len(message_text.split(chr(10)))} total lines)")
        logger.info("=" * 60)
        return True
    
    token = get_tenant_access_token()
    if not token:
        logger.error("Failed to get Lark access token for messaging")
        return False
    
    # Use interactive card if provided, otherwise plain text
    if card:
        payload = {
            "receive_id": user_id,
            "msg_type": "interactive",
            "content": json.dumps(card)
        }
    else:
        payload = {
            "receive_id": user_id,
            "msg_type": "text",
            "content": json.dumps({"text": message_text})
        }
    
    try:
        response = requests.post(
            config.IM_MESSAGE_URL,
            headers={"Authorization": f"Bearer {token}"},
            params={"receive_id_type": "open_id"},
            json=payload,
            timeout=config.REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == 0:
            message_id = data.get("data", {}).get("message_id", "unknown")
            logger.info(f"✅ Message sent successfully (message_id: {message_id[:10]}...)")
            return True
        else:
            error_code = data.get("code")
            error_msg = data.get("msg", "Unknown error")
            logger.error(f"❌ Message send failed (code {error_code}): {error_msg}")
            return False
            
    except requests.RequestException as e:
        logger.error(f"❌ Message API request failed: {e}")
        return False


# ============================================
# Main Processing Logic
# ============================================

def process_pending_requests() -> dict[str, Any]:
    """
    Main processing function for bulk ID card routing.
    
    1. Fetch pending records
    2. Fetch branch routing
    3. Resolve printer branches
    4. Group by branch
    5. Send one bot message per branch
    6. Update records
    
    Returns:
        Summary dict with processing statistics
    """
    summary: dict[str, Any] = {
        'total_pending': 0,
        'total_processed': 0,
        'total_messages': 0,
        'branches_processed': [],
        'errors': [],
        'dry_run': config.DRY_RUN
    }
    
    logger.info("=" * 60)
    logger.info("SPMC Bulk ID Card Router (Bot Messaging)")
    logger.info(f"Mode: {'DRY_RUN (no messages sent)' if config.DRY_RUN else 'LIVE'}")
    logger.info(f"Test Mode: {'ON (all messages to ' + config.TEST_RECIPIENT_EMAIL + ')' if config.TEST_MODE else 'OFF'}")
    logger.info("=" * 60)
    
    # Step 1: Resolve test recipient user_id first
    logger.info("\n👤 Resolving test recipient...")
    test_user_id = resolve_user_for_base_assistant(config.TEST_RECIPIENT_EMAIL)
    if not test_user_id:
        logger.error(f"Cannot resolve test recipient: {config.TEST_RECIPIENT_EMAIL}")
        logger.error("Make sure this email exists in your Lark organization.")
        summary['errors'].append(f"Cannot resolve test recipient: {config.TEST_RECIPIENT_EMAIL}")
        return summary
    logger.info(f"Test recipient resolved: {test_user_id[:15]}...")
    
    # Step 2: Fetch pending records
    logger.info("\n📥 Fetching pending requests...")
    pending_records = fetch_pending_requests()
    summary['total_pending'] = len(pending_records)
    
    if not pending_records:
        logger.info("No pending records found. Nothing to process.")
        return summary
    
    logger.info(f"Found {len(pending_records)} pending records")
    
    # Step 3: Fetch branch routing
    logger.info("\n🗺️ Loading branch routing configuration...")
    routing = fetch_branch_routing()
    logger.info(f"Loaded {len(routing)} branch routing entries")
    
    # Step 4: Resolve printer branches and group
    logger.info("\n🔀 Resolving printer branches and grouping...")
    grouped_records: dict[str, list[IDCardRecord]] = defaultdict(list)
    
    for record in pending_records:
        resolved_branch = resolve_printer_branch(record, routing)
        if not resolved_branch:
            logger.warning(f"No branch resolved for {record.id_number}, skipping")
            summary['errors'].append(f"No branch for {record.id_number}")
            continue
        grouped_records[resolved_branch].append(record)
    
    logger.info(f"Grouped into {len(grouped_records)} branches:")
    for branch, records in grouped_records.items():
        logger.info(f"  - {branch}: {len(records)} cards")
    
    # Step 5: Send message per branch and update records
    logger.info("\n📨 Sending messages and updating records...")
    
    for branch, records in grouped_records.items():
        batch_id = str(uuid.uuid4())
        logger.info(f"\nProcessing branch: {branch} ({len(records)} cards)")
        logger.info(f"Batch ID: {batch_id}")
        
        # Build message
        message_text = build_message_text(records, branch, batch_id)
        card = build_rich_message(records, branch, batch_id)
        
        # Get recipient (test mode uses test user)
        recipient_id = test_user_id  # Always use test user in this version
        
        # Send message
        message_sent = send_base_assistant_message(recipient_id, message_text, card)
        
        if message_sent:
            summary['total_messages'] += 1
            summary['branches_processed'].append(branch)
            
            # Update records in Lark Base
            update_success = update_records(records, batch_id, branch)
            
            if update_success:
                summary['total_processed'] += len(records)
            else:
                summary['errors'].append(f"Failed to update records for {branch}")
        else:
            summary['errors'].append(f"Failed to send message for {branch}")
    
    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 PROCESSING SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total pending records: {summary['total_pending']}")
    logger.info(f"Total messages sent: {summary['total_messages']}")
    logger.info(f"Total records processed: {summary['total_processed']}")
    logger.info(f"Branches processed: {', '.join(summary['branches_processed']) or 'None'}")
    
    if summary['errors']:
        logger.warning(f"Errors encountered: {len(summary['errors'])}")
        for error in summary['errors']:
            logger.warning(f"  - {error}")
    
    if config.DRY_RUN:
        logger.info("\n⚠️  DRY_RUN mode - No messages sent, no records updated")
        logger.info("   Run with --send flag to send messages and update records")
    
    return summary


def main() -> None:
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description='SPMC Bulk ID Card Router (Bot Messaging)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/bulk_card_router_bot.py              # DRY_RUN mode
  python scripts/bulk_card_router_bot.py --send       # Send messages
  python scripts/bulk_card_router_bot.py --verbose    # Debug logging

NOTES:
  - Messages are sent via Lark IM Bot API (not Base Assistant directly)
  - Base Assistant is a built-in Lark feature with no public API
  - Bot messages appear from your Lark App's bot identity
  - This is the official, production-ready approach for notifications
        """
    )
    
    parser.add_argument(
        '--send', 
        action='store_true',
        help='Send messages and update records (disables DRY_RUN)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose debug logging'
    )
    
    parser.add_argument(
        '--test-email',
        type=str,
        default=config.TEST_RECIPIENT_EMAIL,
        help=f'Override test recipient email (default: {config.TEST_RECIPIENT_EMAIL})'
    )
    
    args = parser.parse_args()
    
    # Apply CLI arguments
    if args.send:
        config.DRY_RUN = False
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.test_email:
        config.TEST_RECIPIENT_EMAIL = args.test_email
    
    # Validate configuration
    if not config.validate():
        logger.error("Configuration validation failed. Exiting.")
        sys.exit(1)
    
    try:
        summary = process_pending_requests()
        
        # Exit with error code if there were failures
        if summary['errors']:
            sys.exit(1)
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)


# ============================================
# NOTES
# ============================================
"""
HOW BASE ASSISTANT DIFFERS FROM IM BOT MESSAGING:
-------------------------------------------------
"Base Assistant" is Lark's built-in notification system that sends automatic
updates for Base (Bitable) events like:
- Record creation/update/deletion
- @mentions in records
- Automation triggers

However, there is NO public API to send messages AS the Base Assistant.
The Base Assistant is a Lark-internal feature.

This script uses the Lark IM Bot API instead:
- Messages come from your Lark App's bot (with your app's name/icon)
- Full control over message content and formatting
- Can send to any Lark user via email resolution
- Supports rich text and interactive cards
- This is the official, production-ready approach for custom notifications

HOW TO SWITCH FROM TEST USER TO REAL BRANCH POC USERS:
------------------------------------------------------
1. Set `config.TEST_MODE = False` or modify the code
2. Update the routing data to include real `poc_email` values:
   - Either configure `LARK_ROUTING_TABLE_ID` and add POC emails to that table
   - Or update the hardcoded routing in `fetch_branch_routing()`
3. Modify `process_pending_requests()` to use the branch's POC email:
   
   Instead of:
       recipient_id = test_user_id
   
   Use:
       if config.TEST_MODE:
           recipient_id = test_user_id
       else:
           poc_email = routing[branch].poc_email if branch in routing else None
           if poc_email:
               recipient_id = resolve_user_for_base_assistant(poc_email)
           else:
               logger.warning(f"No POC email for {branch}")
               continue

4. Ensure all POC emails are valid Lark users in your organization.

CHECKBOX HANDLING:
-----------------
The `email_sent` field is a CHECKBOX type in Lark Base:
- Reading: Returns boolean True (checked) or False (unchecked)
- Writing: Send boolean True to check, False to uncheck
- Filtering: Use NOT(CurrentValue.[field]) instead of =FALSE (Lark quirk)
"""


if __name__ == "__main__":
    main()
