import os
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import cloudinary.api
import io

# Load environment variables
load_dotenv()

# Configure Cloudinary with explicit parameters
CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME')
API_KEY = os.getenv('CLOUDINARY_API_KEY')
API_SECRET = os.getenv('CLOUDINARY_API_SECRET')

cloudinary.config(
    cloud_name=CLOUD_NAME,
    api_key=API_KEY,
    api_secret=API_SECRET,
    secure=True
)

print("🔧 Cloudinary Configuration:")
print(f"   Cloud Name: {CLOUD_NAME}")
print(f"   API Key: {API_KEY}")
print(f"   API Secret: {'*' * len(API_SECRET) if API_SECRET else 'NOT SET'}")
print()

# Verify env vars are loaded
if not CLOUD_NAME or not API_KEY or not API_SECRET:
    print("❌ ERROR: Missing Cloudinary credentials in .env file!")
    print(f"   CLOUDINARY_CLOUD_NAME: {CLOUD_NAME}")
    print(f"   CLOUDINARY_API_KEY: {API_KEY}")
    print(f"   CLOUDINARY_API_SECRET: {API_SECRET}")
    exit(1)

# Test 1: Simple upload test (doesn't require API authentication)
print("📡 Testing Cloudinary upload connection...")
try:
    # Create a tiny test PDF file
    test_data = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 2\n0000000000 65535 f\n0000000009 00000 n\ntrailer\n<< /Size 2 /Root 1 0 R >>\nstartxref\n74\n%%EOF"
    test_file = io.BytesIO(test_data)
    
    result = cloudinary.uploader.upload(
        test_file,
        resource_type="raw",
        folder="employee_ids/test",
        public_id=f"connection_test_{os.urandom(4).hex()}",
        overwrite=True
    )
    
    print(f"✅ Upload successful!")
    print(f"   URL: {result['secure_url']}")
    print(f"   Public ID: {result['public_id']}")
    print(f"   File Size: {result['bytes']} bytes")
    
    # Test 2: Verify the uploaded file is accessible
    print("\n🔗 Testing URL accessibility...")
    import urllib.request
    try:
        urllib.request.urlopen(result['secure_url'], timeout=5)
        print(f"✅ File is accessible at: {result['secure_url']}")
    except Exception as url_error:
        print(f"⚠️  URL test failed: {str(url_error)}")
    
    # Clean up test file
    print("\n🧹 Cleaning up test file...")
    cloudinary.uploader.destroy(result['public_id'], resource_type="raw")
    print(f"✅ Cleanup successful")
    
except Exception as e:
    print(f"❌ Upload failed: {str(e)}")
    print(f"   Error type: {type(e).__name__}")
    print(f"\n💡 Troubleshooting:")
    print(f"   - Verify credentials at: https://console.cloudinary.com/settings/c/{CLOUD_NAME}/credentials")
    print(f"   - Check upload limits: https://console.cloudinary.com/console/usage")
    print(f"   - Test in browser: https://console.cloudinary.com/console/media_library")
    exit(1)

print("\n✅ All Cloudinary tests passed!")
print(f"\n📊 Your Cloudinary account is ready for PDF uploads:")
print(f"   Cloud Name: {CLOUD_NAME}")
print(f"   Folder: employee_ids/")