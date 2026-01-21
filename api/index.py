# Vercel serverless function entry point
# This file exposes the FastAPI app to Vercel's serverless environment

from app.main import app

# Vercel looks for 'app' in the handler file
# This re-export ensures it's available at the expected location
