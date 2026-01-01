"""
WSGI entry point for Hostinger deployment
Production-ready configuration
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

# Import app
from app.main import app

# WSGI application entry point
application = app

# For local testing
if __name__ == "__main__":
    import uvicorn
    from app.config import settings
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level="info" if not settings.DEBUG else "debug"
    )

