import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.main import app

# Vercel Serverless Python expects 'app' for ASGI frameworks like FastAPI
# Not 'handler' - that's for the old BaseHTTPRequestHandler style
