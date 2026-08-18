import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app as fastapi_app

async def app(scope, receive, send):
    if scope["type"] == "http":
        raw_path = scope.get("raw_path", b"").decode("utf-8")
        if raw_path and not raw_path.startswith("/api/index"):
            # Strip query string from raw_path if present
            scope["path"] = raw_path.split("?")[0]
        elif scope.get("path") in ["/api/index.py", "/api/index"]:
            scope["path"] = "/"

    await fastapi_app(scope, receive, send)
