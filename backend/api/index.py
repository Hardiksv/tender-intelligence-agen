import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app as fastapi_app

async def app(scope, receive, send):
    if scope["type"] == "http":
        path = scope.get("path", "")
        # Vercel ASGI path normalization
        for prefix in ["/api/index.py", "/api/index"]:
            if path.startswith(prefix):
                scope["path"] = path[len(prefix):] or "/"
                break
    await fastapi_app(scope, receive, send)
