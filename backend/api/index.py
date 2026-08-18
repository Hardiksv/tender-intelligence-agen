import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app as fastapi_app

async def app(scope, receive, send):
    if scope["type"] == "http":
        headers = dict(scope.get("headers", []))
        
        # Extract requested path from Vercel headers
        forwarded = (
            headers.get(b"x-forwarded-uri", b"")
            or headers.get(b"x-matched-path", b"")
            or headers.get(b"x-now-route-matches", b"")
        ).decode("utf-8")
        
        if forwarded and not forwarded.startswith("/api/index"):
            scope["path"] = forwarded.split("?")[0]
        else:
            raw = scope.get("raw_path", b"").decode("utf-8")
            if raw and not raw.startswith("/api/index"):
                scope["path"] = raw.split("?")[0]
            elif scope.get("path") in ["/api/index.py", "/api/index"]:
                scope["path"] = "/"

    await fastapi_app(scope, receive, send)
