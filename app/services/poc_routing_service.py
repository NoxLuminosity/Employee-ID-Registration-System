"""
POC (Point of Contact) Routing Service

Handles:
- Branch-to-POC routing using haversine distance
- POC contact mapping (branch → POC name/email)
- Nearest POC fallback for non-POC branches
"""

import logging
from math import radians, sin, cos, sqrt, atan2
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# List of valid POC branches (branches with printing POCs)
# This is the single authoritative source of truth for all POC branches.
POC_BRANCHES: set = {
    "Bacolod",
    "Batangas",
    "Cagayan De Oro",
    "Calamba City",
    "Cavite",
    "Cebu City",
    "Davao City",
    "General Santos City",
    "Ilo-Ilo",
    "Makati",
    "Malolos City",
    "Pagadian City",
    "Parañaque",
    "Quezon City",
    "San Carlos",
    "San Fernando City",
    "Tagum City",
    "Zamboanga City",
}

# Pending POC Branches — placeholder for future branches.
# To add a new pending branch:
#   1. Add entry here with status/reason/added_date
#   2. Add coordinates to BRANCH_COORDS
#   3. When details arrive: add to POC_CONTACTS + POC_BRANCHES, remove from here
# NOTE: Makati & Cavite were activated on 2026-02-11.
PENDING_POC_BRANCHES: dict = {}

# All recognized POC branches (active + pending)
ALL_POC_BRANCHES: set = POC_BRANCHES | set(PENDING_POC_BRANCHES.keys())

# POC Contact Mapping (Branch → Contact Info)
# Each entry has: name (display), email (for Lark user lookup)
# NOTE: Emails must be real Lark account emails for message delivery
POC_CONTACTS: dict = {
    "San Carlos": {
        "name": "Zacarias, Reynaldo Jr Mamaril (HR PITX)",
        "email": "reyzacarias922@gmail.com",
    },
    "Pagadian City": {
        "name": "Melvin Calugay | PIF | GENSAN (PMCY)",
        "email": "melvincalugay102096@gmail.com",
    },
    "Zamboanga City": {
        "name": "Mira Mukim | PIF ZMB (QNAM)",
        "email": "miramukim@gmail.com",
    },
    "Malolos City": {
        "name": "Aeron Tasic | PIF | MAL | MAPT",
        "email": "aeronjay1987@gmail.com",
    },
    "San Fernando City": {
        "name": "Jojo Salomon | PIF | PAM (MJSM)",
        "email": "jjsalomon2@gmail.com",
    },
    "Cagayan De Oro": {
        "name": "Aldrin Bautista | PIF | CDO (QADB)",
        "email": "aldrinbautista62@gmail.com",
    },
    "Tagum City": {
        "name": "Kemy Revilla",
        "email": "revillakemy@gmail.com",
    },
    "Davao City": {
        "name": "Rona Sindatoc (BNB-MSME NWOFF DAVAO)",
        "email": "Sindatoc07@gmail.com",
    },
    "Cebu City": {
        "name": "Jenemae Manila (HR Services Ceb)",
        "email": "manilajenemae@gmail.com",
    },
    "Batangas": {
        "name": "Queenie Caraulia | PIF | BATANGAS | PQGC",
        "email": "kkwen0312@gmail.com",
    },
    "General Santos City": {
        "name": "As-addah Maminasacan | PIF | GEN (GASM)",
        "email": "maminasacana@gmail.com",
    },
    "Bacolod": {
        "name": "Nerio, Louie Rose Ponciano (PIF BACOLOD | BLON)",
        "email": "nerio.louierose1b@gmail.com",
    },
    "Ilo-Ilo": {
        "name": "Maerci del Monte | PIF | ILOILO (MMDD)",
        "email": "mhayedelmonte02@gmail.com",
    },
    "Quezon City": {
        "name": "Queen Mary Bernaldez (HR QC)",
        "email": "bernaldezqueenmary24@gmail.com",
    },
    "Calamba City": {
        "name": "Cherrylyn Albis | PIF | CALAMBA (MCRA)",
        "email": "cherry0415lyn@gmail.com",
    },
    "Parañaque": {
        "name": "Ira Mackenzie Arahan (HR Employee Relations PITX)",
        "email": "mcknzzz2001@gmail.com",
    },
    "Cavite": {
        "name": "Cavite POC",
        "email": "contadofeangelica@gmail.com",
    },
    "Makati": {
        "name": "Makati POC",
        "email": "weannbundalan@gmail.com",
    },
}

# Branch coordinates mapping (latitude, longitude)
BRANCH_COORDS: dict = {
    # POC Branches (with printing capabilities)
    "San Carlos": (15.9290, 120.3510),
    "Pagadian City": (7.8242, 123.4375),
    "Zamboanga City": (6.9214, 122.0790),
    "Malolos City": (14.8431, 120.8082),
    "San Fernando City": (15.0286, 120.6851),
    "Cagayan De Oro": (8.4542, 124.6319),
    "Tagum City": (7.4480, 125.8078),
    "Davao City": (7.1907, 125.4553),
    "Cebu City": (10.3157, 123.8854),
    "Batangas": (13.7565, 121.0583),
    "General Santos City": (6.1164, 125.1716),
    "Bacolod": (10.6407, 122.9320),
    "Ilo-Ilo": (10.7202, 122.5621),
    "Quezon City": (14.6760, 121.0437),
    "Calamba City": (14.2112, 121.1654),
    
    "Makati": (14.5547, 121.0244),       # NCR
    "Cavite": (14.4791, 120.8961),       # Cavite Province
    
    # Non-POC Branches (need fallback to nearest POC)
    "Parañaque": (14.4793, 121.0198),
    "Paranaque": (14.4793, 121.0198),  # Alias without ñ
    "Manila": (14.5995, 120.9842),
    "Pasig": (14.5764, 121.0851),
    "Taguig": (14.5176, 121.0509),
    "Mandaluyong": (14.5794, 121.0359),
    "Pasay": (14.5378, 121.0014),
    "Las Piñas": (14.4445, 120.9929),
    "Muntinlupa": (14.4081, 121.0415),
    "Marikina": (14.6507, 121.1029),
    "San Juan": (14.6027, 121.0356),
    "Valenzuela": (14.7004, 120.9830),
    "Navotas": (14.6667, 120.9417),
    "Pateros": (14.5456, 121.0673),
    "Antipolo": (14.5860, 121.1761),
    "Cainta": (14.5779, 121.1222),
    "Taytay": (14.5594, 121.1354),
    "Angono": (14.5286, 121.1536),
    "Binangonan": (14.4655, 121.1996),
    "Rodriguez": (14.7467, 121.1392),
    "San Mateo": (14.6987, 121.1176),
    
    # Province names (will be aliased to their POC branches)
    "Bulacan": (14.8431, 120.8082),  # Maps to Malolos City
    "Laguna": (14.2112, 121.1654),    # Maps to Calamba City
    "Pampanga": (15.0286, 120.6851),  # Maps to San Fernando City
    "Bataan": (14.6417, 120.4658),    # Will use nearest POC (San Fernando)
    "Nueva Ecija": (15.5784, 121.1113),  # Will use nearest POC
    "Pangasinan": (15.8949, 120.2863),   # Will use nearest POC (San Carlos)
    "Zambales": (15.5082, 119.9698),     # Will use nearest POC (San Fernando)
    "Tarlac": (15.4755, 120.5963),       # Will use nearest POC
}

# Branch aliases: Province/Region names to their primary POC branch
# These override haversine distance calculation
BRANCH_ALIASES: dict = {
    # Province aliases
    "Bulacan": "Malolos City",
    "Laguna": "Calamba City", 
    "Pampanga": "San Fernando City",
    "Pangasinan": "San Carlos",
    "Rizal": "Quezon City",
    # City-name aliases
    "Cavite City": "Cavite",
    "Makati City": "Makati",
    # Short name aliases (backward compat for old form submissions)
    "Cebu": "Cebu City",
    "Davao": "Davao City",
    "General Santos": "General Santos City",
    "Iloilo": "Ilo-Ilo",
    "Paranaque": "Parañaque",
    "Pagadian": "Pagadian City",
    "Tagum": "Tagum City",
    "Zamboanga": "Zamboanga City",
}


def normalize_branch_name(branch: str) -> str:
    """
    Normalize a branch name: strip whitespace.
    Alias resolution is handled separately in compute_nearest_poc_branch.

    Args:
        branch: Raw branch name

    Returns:
        Normalized branch name
    """
    if not branch:
        return ""
    return branch.strip()


def is_pending_poc_branch(branch_name: str) -> bool:
    """
    Check if a branch is a pending POC branch (recognized but details not yet provided).

    Args:
        branch_name: Name of the branch

    Returns:
        True if branch is pending POC, False otherwise
    """
    return normalize_branch_name(branch_name) in PENDING_POC_BRANCHES


def _log_routing_decision(
    account_id: str,
    original_branch: str,
    resolved_branch: str,
    poc_used: str,
    reason: str,
) -> None:
    """
    Log a routing decision with full audit trail.

    Args:
        account_id: Employee account/ID for tracing
        original_branch: The branch as submitted
        resolved_branch: The branch after normalization/alias resolution
        poc_used: The final POC branch selected
        reason: Why this POC was selected
    """
    logger.info(
        f"[POC Routing] account={account_id} | "
        f"original_branch='{original_branch}' | "
        f"resolved_branch='{resolved_branch}' | "
        f"poc_used='{poc_used}' | "
        f"reason={reason}"
    )


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth
    using the Haversine formula.
    
    Args:
        lat1, lon1: Coordinates of point 1 (in degrees)
        lat2, lon2: Coordinates of point 2 (in degrees)
        
    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth's radius in kilometers
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


def get_branch_coords(branch_name: str) -> Optional[Tuple[float, float]]:
    """
    Get coordinates for a branch name.
    
    Args:
        branch_name: Name of the branch
        
    Returns:
        Tuple of (latitude, longitude) or None if not found
    """
    return BRANCH_COORDS.get(branch_name)


def is_valid_poc_branch(branch_name: str) -> bool:
    """
    Check if a branch is a valid POC branch (has printing capability).
    
    Args:
        branch_name: Name of the branch
        
    Returns:
        True if branch is a POC branch, False otherwise
    """
    return branch_name in POC_BRANCHES


def compute_nearest_poc_branch(employee_branch: str, context: Optional[dict] = None) -> str:
    """
    Find the correct POC branch for an employee's location.

    Routing algorithm (deterministic, ordered):
        1. Normalize branch name (strip whitespace)
        2. If branch is an active POC branch → return it directly
        3. Resolve branch aliases (e.g., Bulacan → Malolos City, Cebu → Cebu City)
           - If alias target is an active POC → return it
        4. GUARDRAIL: If the resolved name has a POC contact mapping → return it
           (catches data inconsistencies where POC_CONTACTS has entry but POC_BRANCHES doesn't)
        5. If branch is a pending POC → log warning, fall back to nearest active
        6. Compute nearest active POC by haversine distance
        7. If no coordinates found → default to Quezon City

    Guardrail: If the selected branch (or its alias) has a direct POC
    contact mapping, routing MUST use that exact mapping. Haversine
    fallback is ONLY used for branches with no POC mapping at all.

    Args:
        employee_branch: The employee's current location/branch
        context: Optional dict with 'account_id' for audit logging

    Returns:
        Name of the nearest active POC branch (guaranteed to have contact info)
    """
    ctx = context or {}
    account_id = ctx.get("account_id", "N/A")

    # Step 1: Normalize
    normalized = normalize_branch_name(employee_branch)
    if not normalized:
        logger.warning(
            f"[POC Routing] account={account_id} | Empty branch name — defaulting to Quezon City"
        )
        return "Quezon City"

    # Step 2: Direct match on active POC branches
    if normalized in POC_BRANCHES:
        _log_routing_decision(account_id, employee_branch, normalized, normalized, "direct_active_poc")
        return normalized

    # Step 3: Resolve aliases (e.g., Bulacan → Malolos City, Cebu → Cebu City)
    resolved = normalized
    if normalized in BRANCH_ALIASES:
        resolved = BRANCH_ALIASES[normalized]
        if resolved in POC_BRANCHES:
            _log_routing_decision(
                account_id, employee_branch, resolved, resolved,
                f"alias:{normalized}->{resolved}"
            )
            return resolved
        # Alias target is not in POC_BRANCHES — continue with resolved name
        logger.info(
            f"[POC Routing] account={account_id} | alias '{normalized}' -> '{resolved}' "
            f"(not in POC_BRANCHES, continuing to fallback)"
        )

    # Step 4: GUARDRAIL — if resolved name has a POC contact, use it directly
    # This catches cases where POC_CONTACTS has an entry but POC_BRANCHES
    # was not updated. Prevents silent misrouting.
    if resolved in POC_CONTACTS:
        logger.error(
            f"[POC Routing] GUARDRAIL TRIGGERED: account={account_id} | "
            f"branch='{employee_branch}' resolved to '{resolved}' which HAS a POC contact "
            f"but is NOT in POC_BRANCHES. Data inconsistency! Using POC contact directly."
        )
        _log_routing_decision(account_id, employee_branch, resolved, resolved, "guardrail_poc_contact_found")
        return resolved

    # Step 5: Check if this is a pending POC branch
    is_pending = resolved in PENDING_POC_BRANCHES
    if is_pending:
        pending_info = PENDING_POC_BRANCHES[resolved]
        logger.warning(
            f"[POC Routing] account={account_id} | branch='{employee_branch}' | "
            f"'{resolved}' is a PENDING POC branch: {pending_info['reason']} | "
            f"Falling back to nearest active POC with valid contact info"
        )

    # Step 6: Find nearest active POC by haversine distance
    # Only reaches here for branches with NO POC mapping at all
    emp_coords = get_branch_coords(resolved) or get_branch_coords(normalized)
    if not emp_coords:
        reason = "pending_poc_no_coords_default" if is_pending else "unknown_branch_no_coords_default"
        logger.warning(
            f"[POC Routing] account={account_id} | branch='{employee_branch}' | "
            f"No coordinates found for '{resolved}' — defaulting to Quezon City"
        )
        _log_routing_decision(account_id, employee_branch, resolved, "Quezon City", reason)
        return "Quezon City"

    emp_lat, emp_lon = emp_coords

    min_distance = float('inf')
    nearest_poc = "Quezon City"  # Default fallback

    for poc_branch in POC_BRANCHES:
        poc_coords = get_branch_coords(poc_branch)
        if not poc_coords:
            continue

        poc_lat, poc_lon = poc_coords
        distance = haversine_distance(emp_lat, emp_lon, poc_lat, poc_lon)

        if distance < min_distance:
            min_distance = distance
            nearest_poc = poc_branch

    # Build reason for audit log
    if is_pending:
        reason = f"pending_poc_fallback_to_nearest ({min_distance:.1f} km)"
    else:
        reason = f"haversine_nearest ({min_distance:.1f} km)"

    _log_routing_decision(account_id, employee_branch, resolved, nearest_poc, reason)
    return nearest_poc


def get_poc_contact(branch: str) -> Optional[dict]:
    """
    Get the POC contact info for a branch.

    Args:
        branch: Branch name

    Returns:
        Dict with 'name' and 'email', or None if not found or pending
    """
    contact = POC_CONTACTS.get(branch)
    if contact:
        return contact

    # Check if this is a pending POC branch
    if branch in PENDING_POC_BRANCHES:
        pending_info = PENDING_POC_BRANCHES[branch]
        logger.warning(
            f"[POC Contact] Branch '{branch}' is a PENDING POC — "
            f"no contact info available: {pending_info['reason']}"
        )

    return None


def get_poc_email(branch: str) -> Optional[str]:
    """
    Get the POC email for a branch.

    Args:
        branch: Branch name

    Returns:
        POC email address, or None if not configured or branch is pending
    """
    contact = get_poc_contact(branch)
    if contact:
        return contact.get("email")
    return None


def validate_poc_contacts() -> Tuple[list, list]:
    """
    Validate that all POC branches have contact info configured.
    Also reports pending POC branches.

    Returns:
        Tuple of (valid_branches, missing_branches)
        Note: Pending branches are included in missing_branches with a marker.
    """
    valid = []
    missing = []

    for branch in POC_BRANCHES:
        contact = POC_CONTACTS.get(branch)
        if contact and contact.get("email"):
            valid.append(branch)
        else:
            missing.append(branch)

    # Report pending POC branches
    for branch, info in PENDING_POC_BRANCHES.items():
        missing.append(f"{branch} (PENDING: {info['reason']})")

    return valid, missing
