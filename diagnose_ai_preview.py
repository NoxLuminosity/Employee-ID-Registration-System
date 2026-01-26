"""
AI Preview Diagnostic Script
Run this to test individual components and identify the issue
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def check_env_vars():
    """Check if all required environment variables are set"""
    print("\n" + "="*60)
    print("CHECKING ENVIRONMENT VARIABLES")
    print("="*60)
    
    required_vars = {
        "BytePlus API": [
            "BYTEPLUS_API_KEY",
            "BYTEPLUS_MODEL",
            "BYTEPLUS_ENDPOINT"
        ],
        "Cloudinary": [
            "CLOUDINARY_CLOUD_NAME",
            "CLOUDINARY_API_KEY",
            "CLOUDINARY_API_SECRET"
        ],
        "Lark OAuth": [
            "LARK_APP_ID",
            "LARK_APP_SECRET",
            "LARK_EMPLOYEE_REDIRECT_URI"
        ]
    }
    
    all_good = True
    for category, vars_list in required_vars.items():
        print(f"\n{category}:")
        for var in vars_list:
            value = os.getenv(var)
            if value:
                # Mask sensitive values
                if "KEY" in var or "SECRET" in var:
                    display_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                else:
                    display_value = value
                print(f"  ✅ {var}: {display_value}")
            else:
                print(f"  ❌ {var}: NOT SET")
                all_good = False
    
    return all_good


def test_cloudinary():
    """Test Cloudinary connection"""
    print("\n" + "="*60)
    print("TESTING CLOUDINARY CONNECTION")
    print("="*60)
    
    try:
        from app.services.cloudinary_service import configure_cloudinary
        
        if configure_cloudinary():
            print("✅ Cloudinary configuration successful")
            
            # Try a test upload with a small base64 image
            try:
                from app.services.cloudinary_service import upload_base64_to_cloudinary
                
                # 1x1 red pixel PNG
                test_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
                
                print("\n  Testing upload...")
                result = upload_base64_to_cloudinary(test_image, "diagnostic_test", "test")
                
                if result:
                    print(f"  ✅ Upload successful: {result[:60]}...")
                    return True
                else:
                    print("  ❌ Upload failed: No URL returned")
                    return False
                    
            except Exception as e:
                print(f"  ⚠️ Upload test failed: {str(e)}")
                return False
        else:
            print("❌ Cloudinary configuration failed")
            return False
            
    except Exception as e:
        print(f"❌ Cloudinary test failed: {str(e)}")
        return False


def test_byteplus():
    """Test BytePlus API connection"""
    print("\n" + "="*60)
    print("TESTING BYTEPLUS API CONNECTION")
    print("="*60)
    
    try:
        from app.services.seedream_service import generate_headshot_from_url
        
        # Use a public test image URL
        test_url = "https://res.cloudinary.com/demo/image/upload/sample.jpg"
        
        print(f"\n  Testing with sample image: {test_url}")
        print("  ⏳ This may take 10-30 seconds...")
        
        result_url, error = generate_headshot_from_url(test_url)
        
        if result_url:
            print(f"  ✅ BytePlus API working: {result_url[:60]}...")
            return True
        else:
            print(f"  ❌ BytePlus API failed: {error}")
            return False
            
    except Exception as e:
        print(f"❌ BytePlus test failed: {str(e)}")
        return False


def test_authentication():
    """Test authentication functions"""
    print("\n" + "="*60)
    print("TESTING AUTHENTICATION")
    print("="*60)
    
    try:
        from app.auth import create_employee_session, verify_employee_auth
        
        # Create test session
        print("\n  Creating test session...")
        test_data = {
            "user_id": "test_user",
            "name": "Test User",
            "email": "test@example.com"
        }
        
        session_token = create_employee_session(test_data)
        print(f"  ✅ Session created: {session_token[:20]}...")
        
        # Verify session
        print("\n  Verifying session...")
        user_data = verify_employee_auth(session_token)
        
        if user_data:
            print(f"  ✅ Session valid: {user_data.get('name')}")
            return True
        else:
            print("  ❌ Session verification failed")
            return False
            
    except Exception as e:
        print(f"❌ Authentication test failed: {str(e)}")
        return False


def run_all_tests():
    """Run all diagnostic tests"""
    print("\n" + "="*60)
    print("AI PREVIEW DIAGNOSTIC TOOL")
    print("="*60)
    print("This script will test all components of the AI headshot generation system.")
    
    results = {}
    
    # Test 1: Environment variables
    results['env_vars'] = check_env_vars()
    
    # Test 2: Cloudinary
    if results['env_vars']:
        results['cloudinary'] = test_cloudinary()
    else:
        print("\n⚠️ Skipping Cloudinary test (missing env vars)")
        results['cloudinary'] = False
    
    # Test 3: BytePlus (only if Cloudinary works, since BytePlus needs URLs)
    if results['cloudinary']:
        results['byteplus'] = test_byteplus()
    else:
        print("\n⚠️ Skipping BytePlus test (Cloudinary not working)")
        results['byteplus'] = False
    
    # Test 4: Authentication
    results['auth'] = test_authentication()
    
    # Summary
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    
    all_passed = all(results.values())
    
    for component, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{component.upper():20} {status}")
    
    print("\n" + "="*60)
    
    if all_passed:
        print("✅ ALL TESTS PASSED - System should be working correctly")
        print("\nIf you're still seeing 'AI preview unavailable', check:")
        print("1. User is logged in via Lark OAuth (check cookies in browser)")
        print("2. Browser console for JavaScript errors")
        print("3. Network tab for API response details")
    else:
        print("❌ SOME TESTS FAILED - See details above")
        print("\nFocus on fixing the failed components first:")
        if not results['env_vars']:
            print("  → Set missing environment variables in .env file")
        if not results['cloudinary']:
            print("  → Verify Cloudinary credentials and quota")
        if not results['byteplus']:
            print("  → Verify BytePlus API key and quota")
        if not results['auth']:
            print("  → Check authentication implementation")
    
    print("="*60 + "\n")
    
    return all_passed


if __name__ == "__main__":
    try:
        # Load environment variables from .env file
        from dotenv import load_dotenv
        load_dotenv()
        
        # Run diagnostics
        success = run_all_tests()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Diagnostic interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
