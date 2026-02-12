#!/usr/bin/env python3
"""
Test script for bulk_card_router_bot.py

Tests the haversine proximity calculation without any API calls.
Run this to verify the routing logic is correct before going live.

Usage:
    python scripts/test_routing_logic.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from the main script
from scripts.bulk_card_router_bot import (
    haversine_distance,
    compute_nearest_poc_branch,
    POC_BRANCHES,
    BRANCH_COORDS,
    PENDING_POC_BRANCHES,
)


def test_haversine():
    """Test haversine distance calculation."""
    print("=" * 60)
    print("TEST 1: Haversine Distance Calculation")
    print("=" * 60)
    
    # Manila to Quezon City should be ~10-15 km
    dist = haversine_distance(14.5995, 120.9842, 14.6760, 121.0437)
    print(f"Manila to Quezon City: {dist:.1f} km")
    assert 8 < dist < 20, f"Expected 8-20 km, got {dist}"
    print("✓ PASS")
    
    # Same location should be 0 km
    dist = haversine_distance(14.5, 121.0, 14.5, 121.0)
    print(f"Same location: {dist:.6f} km")
    assert dist < 0.001, f"Expected ~0 km, got {dist}"
    print("✓ PASS")
    
    # Davao to General Santos ~175 km
    dist = haversine_distance(7.1907, 125.4553, 6.1164, 125.1716)
    print(f"Davao to GenSan: {dist:.1f} km")
    assert 100 < dist < 200, f"Expected 100-200 km, got {dist}"
    print("✓ PASS")
    
    print()


def test_poc_branches():
    """Test POC branch recognition."""
    print("=" * 60)
    print("TEST 2: POC Branch Recognition")
    print("=" * 60)
    
    for branch in ["Batangas", "Davao City", "Quezon City", "Cebu City"]:
        result = compute_nearest_poc_branch(branch)
        print(f"{branch} -> {result}")
        assert result == branch, f"Expected {branch}, got {result}"
    print("✓ All POC branches recognized correctly")
    print()


def test_paranaque_exclusion():
    """Test that Parañaque is excluded and falls back."""
    print("=" * 60)
    print("TEST 3: Parañaque Exclusion")
    print("=" * 60)
    
    result = compute_nearest_poc_branch("Parañaque")
    print(f"Parañaque -> {result}")
    assert result != "Parañaque", "Parañaque should be excluded!"
    assert result in POC_BRANCHES, f"Result should be a POC branch, got {result}"
    print(f"✓ PASS - Parañaque correctly routes to {result}")
    print()


def test_fallback_routing():
    """Test fallback routing for non-POC branches."""
    print("=" * 60)
    print("TEST 4: Fallback Routing (Non-POC Branches)")
    print("=" * 60)
    
    test_cases = [
        ("Makati", "Makati"),            # Now an active POC branch
        ("Cavite", "Cavite"),            # Now an active POC branch
        ("Manila", None),                # NCR -> nearest active POC (haversine)
        ("Taguig", None),                # NCR -> nearest active POC (haversine)
        ("Calamba City", "Calamba City"), # Is a POC branch
        ("Lipa City", "Batangas"),       # Near Batangas
        ("Santa Rosa", "Calamba City"),  # Near Calamba
    ]
    
    for branch, expected in test_cases:
        result = compute_nearest_poc_branch(branch)
        if expected is None:
            # For non-POC branches, just verify it routes to *some* active POC
            status = "✓" if result in POC_BRANCHES else "✗"
            print(f"{status} {branch:20} -> {result:20} (haversine fallback, any active POC is valid)")
        else:
            status = "✓" if result == expected else "✗"
            print(f"{status} {branch:20} -> {result:20} (expected: {expected})")
    print()


def test_active_poc_branches_makati_cavite():
    """Test that Makati & Cavite are now active POC branches (route to themselves)."""
    print("=" * 60)
    print("TEST 5: Active POC Branches (Makati, Cavite)")
    print("=" * 60)
    
    # PENDING should be empty now
    assert len(PENDING_POC_BRANCHES) == 0, f"PENDING should be empty, got {PENDING_POC_BRANCHES}"
    print("✓ PENDING_POC_BRANCHES is empty (all branches activated)")
    
    for branch in ["Makati", "Cavite"]:
        assert branch in POC_BRANCHES, f"{branch} should be in POC_BRANCHES (active)"
        assert branch not in PENDING_POC_BRANCHES, f"{branch} should NOT be pending"
        assert branch in BRANCH_COORDS, f"{branch} should have coordinates in BRANCH_COORDS"
        
        result = compute_nearest_poc_branch(branch)
        assert result == branch, f"{branch} should route to ITSELF (active POC), got '{result}'"
        print(f"✓ {branch:20} -> {result:20} (active POC, routes to self)")
    
    print("✓ Makati & Cavite are active and route correctly")
    print()


def test_unknown_branch():
    """Test handling of unknown branches."""
    print("=" * 60)
    print("TEST 6: Unknown Branch Handling")
    print("=" * 60)
    
    result = compute_nearest_poc_branch("Unknown City XYZ")
    print(f"Unknown City XYZ -> {result}")
    assert result == "Quezon City", f"Expected Quezon City default, got {result}"
    print("✓ PASS - Unknown branches default to Quezon City")
    print()


def test_all_poc_branches_have_coords():
    """Verify all POC branches have coordinates."""
    print("=" * 60)
    print("TEST 7: POC Branch Coordinates")
    print("=" * 60)
    
    missing = []
    for branch in POC_BRANCHES:
        if branch not in BRANCH_COORDS:
            missing.append(branch)
    
    if missing:
        print(f"✗ FAIL - Missing coordinates for: {missing}")
    else:
        print(f"✓ PASS - All {len(POC_BRANCHES)} POC branches have coordinates")
    print()


def test_distance_table():
    """Print distance table for NCR branches to POCs."""
    print("=" * 60)
    print("REFERENCE: NCR Branch Distances to Nearest POCs")
    print("=" * 60)
    
    ncr_branches = [
        "Parañaque", "Makati", "Cavite", "Manila", "Taguig", "Pasig", 
        "Mandaluyong", "Quezon City", "Pasay", "Las Piñas", "Muntinlupa"
    ]
    
    print(f"{'Branch':<20} {'Nearest POC':<20} {'Distance':<10}")
    print("-" * 50)
    
    for branch in ncr_branches:
        if branch not in BRANCH_COORDS:
            print(f"{branch:<20} {'(no coords)':<20} {'-':<10}")
            continue
        
        result = compute_nearest_poc_branch(branch)
        
        # Calculate distance
        if result == branch:
            dist = 0
        else:
            src = BRANCH_COORDS[branch]
            dst = BRANCH_COORDS[result]
            dist = haversine_distance(src[0], src[1], dst[0], dst[1])
        
        dist_str = f"{dist:.1f} km" if dist > 0 else "is POC"
        print(f"{branch:<20} {result:<20} {dist_str:<10}")
    
    print()


def main():
    print("\n" + "=" * 60)
    print("BULK CARD ROUTER - ROUTING LOGIC TESTS")
    print("=" * 60 + "\n")
    
    test_haversine()
    test_poc_branches()
    test_paranaque_exclusion()
    test_fallback_routing()
    test_active_poc_branches_makati_cavite()
    test_unknown_branch()
    test_all_poc_branches_have_coords()
    test_distance_table()
    
    print("=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)
    print("\nTo run the actual script in DRY_RUN mode:")
    print("  python scripts/bulk_card_router_bot.py --verbose")
    print("\nTo send messages to YOUR email only:")
    print("  python scripts/bulk_card_router_bot.py --send --test-email your@email.com")


if __name__ == "__main__":
    main()
