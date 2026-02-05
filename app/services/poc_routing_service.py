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
# NOTE: Parañaque has a real POC but MUST be excluded for now - uses fallback
POC_BRANCHES: set = {
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

# POC Contact Mapping (Branch → Contact Info)
# Each entry has: name (display), email (for Lark user lookup)
# NOTE: Emails must be real Lark account emails for message delivery
POC_CONTACTS: dict = {
    "San Carlos": {
        "name": "Zacarias, Reynaldo Jr Mamaril (HR PITX)",
        "email": "rezacarias@spmadridlaw.com",
    },
    "Pagadian City": {
        "name": "Melvin Calugay | PIF | GENSAN (PMCY)",
        "email": "mecalugay@spmadridlaw.com",
    },
    "Zamboanga City": {
        "name": "Mira Mukim | PIF ZMB (QNAM)",
        "email": "nmukim@spmadridlaw.com",
    },
    "Malolos City": {
        "name": "Aeron Tasic | PIF | MAL | MAPT",
        "email": "aptasic@spmadridlaw.com",
    },
    "San Fernando City": {
        "name": "Jojo Salomon | PIF | PAM (MJSM)",
        "email": "jmsalomon@spmadridlaw.com",
    },
    "Cagayan De Oro": {
        "name": "Aldrin Bautista | PIF | CDO (QADB)",
        "email": "asbautista@spmadridlaw.com",
    },
    "Tagum City": {
        "name": "Kemy Revilla",
        "email": "kvrevilla@spmadridlaw.com",
    },
    "Davao City": {
        "name": "Rona Sindatoc (BNB-MSME NWOFF DAVAO)",
        "email": "rona@spmadridlaw.com",
    },
    "Cebu City": {
        "name": "Jenemae Manila (HR Services Ceb)",
        "email": "jfmanila@spmadridlaw.com",
    },
    "Batangas": {
        "name": "Queenie Caraulia | PIF | BATANGAS | PQGC",
        "email": "qgcaraulia@spmadridlaw.com",
    },
    "General Santos City": {
        "name": "As-addah Maminasacan | PIF | GEN (GASM)",
        "email": "aamaminasacan@spmadridlaw.com",
    },
    "Bacolod": {
        "name": "Nerio, Louie Rose Ponciano (PIF BACOLOD | BLON)",
        "email": "lpnerio@spmadridlaw.com",
    },
    "Ilo-Ilo": {
        "name": "Maerci del Monte | PIF | ILOILO (MMDD)",
        "email": "mdelmonte@spmadridlaw.com",
    },
    "Quezon City": {
        "name": "Queen Mary Bernaldez (HR QC)",
        "email": "qrbernaldez@spmadridlaw.com",
    },
    "Calamba City": {
        "name": "Cherrylyn Albis | PIF | CALAMBA (MCRA)",
        "email": "cralbis@spmadridlaw.com",
    },
    # Special case: Parañaque (not in POC_BRANCHES but has its own POC)
    "Parañaque": {
        "name": "Ira Mackenzie Arahan (HR Employee Relations PITX)",
        "email": "icarahan@spmadridlaw.com",
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
    
    # Non-POC Branches (need fallback to nearest POC)
    "Parañaque": (14.4793, 121.0198),
    "Paranaque": (14.4793, 121.0198),  # Alias without ñ
    "Manila": (14.5995, 120.9842),
    "Makati": (14.5547, 121.0244),
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
}


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


def compute_nearest_poc_branch(employee_branch: str) -> str:
    """
    Find the nearest POC branch to an employee's location.
    
    If the employee is already at a POC branch, returns that branch.
    Otherwise, finds the nearest POC branch using haversine distance.
    
    Args:
        employee_branch: The employee's current location/branch
        
    Returns:
        Name of the nearest POC branch
    """
    # If already at a POC branch, return it
    if employee_branch in POC_BRANCHES:
        return employee_branch
    
    # Get employee's coordinates
    emp_coords = get_branch_coords(employee_branch)
    if not emp_coords:
        # Unknown branch - default to Quezon City
        logger.warning(f"Unknown branch '{employee_branch}' - defaulting to Quezon City")
        return "Quezon City"
    
    emp_lat, emp_lon = emp_coords
    
    # Find nearest POC branch
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
    
    logger.info(f"Resolved branch '{employee_branch}' -> nearest POC '{nearest_poc}' (distance: {min_distance:.1f} km)")
    return nearest_poc


def get_poc_contact(branch: str) -> Optional[dict]:
    """
    Get the POC contact info for a branch.
    
    Args:
        branch: Branch name
        
    Returns:
        Dict with 'name' and 'email' or None if not found
    """
    return POC_CONTACTS.get(branch)


def get_poc_email(branch: str) -> Optional[str]:
    """
    Get the POC email for a branch.
    
    Args:
        branch: Branch name
        
    Returns:
        POC email address or None if not configured
    """
    contact = get_poc_contact(branch)
    if contact:
        return contact.get("email")
    return None


def validate_poc_contacts() -> Tuple[list, list]:
    """
    Validate that all POC branches have contact info configured.
    
    Returns:
        Tuple of (valid_branches, missing_branches)
    """
    valid = []
    missing = []
    
    for branch in POC_BRANCHES:
        contact = get_poc_contact(branch)
        if contact and contact.get("email"):
            valid.append(branch)
        else:
            missing.append(branch)
    
    return valid, missing
