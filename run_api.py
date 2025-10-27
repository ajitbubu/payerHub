#!/usr/bin/env python3
"""
Simple script to run the PayerHub API Gateway
This version runs without heavy ML dependencies for quick testing
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment variables from .env if it exists
from dotenv import load_dotenv
load_dotenv()

# Set defaults if not in .env
os.environ.setdefault('DATABASE_URL', 'postgresql://payerhub_user:secure_password@localhost:5432/payerhub')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
os.environ.setdefault('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
os.environ.setdefault('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
os.environ.setdefault('USE_GPU', 'false')

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("PayerHub Integration API")
    print("=" * 60)
    print(f"Starting API server...")
    print(f"API will be available at: http://localhost:8001")
    print(f"API docs at: http://localhost:8001/docs")
    print(f"Health check at: http://localhost:8001/health")
    print("=" * 60)
    
    uvicorn.run(
        "src.api_gateway.gateway:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
