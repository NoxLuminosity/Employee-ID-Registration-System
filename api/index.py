# Vercel serverless function entry point
# This file exposes the FastAPI app to Vercel's serverless environment

import sys
import os

# Add the project root to Python path so 'app' module can be found
# Vercel runs this from the api/ directory, so we need to go up one level
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.main import app

# Vercel looks for 'app' in the handler file
# This re-export ensures it's available at the expected location
