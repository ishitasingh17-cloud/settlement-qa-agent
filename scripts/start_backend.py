#!/usr/bin/env python3
"""
scripts/start_backend.py

Clean backend launcher for PS-8 Settlement Q&A Agent.
Launches uvicorn server with settings from server.config.settings.
"""

import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from server.config.settings import settings

def main():
    print("=" * 80)
    print("PS-8 SETTLEMENT Q&A AGENT - BACKEND SERVER")
    print(f"Host: {settings.HOST}:{settings.PORT}")
    print(f"Environment: {settings.ENVIRONMENT}")
    print("API Documentation: http://127.0.0.1:8000/docs")
    print("Health Endpoint:   http://127.0.0.1:8000/api/health")
    print("=" * 80)
    
    import uvicorn
    uvicorn.run(
        "server.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
    )

if __name__ == "__main__":
    main()
