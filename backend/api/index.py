import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app as fastapi_app

async def app(scope, receive, send):
    if scope["type"] == "http":
        headers = dict(scope.get("headers", []))
        
        # Extract original requested path from Vercel headers
        forwarded_uri = (
            headers.get(b"x-forwarded-uri", b"")
            or headers.get(b"x-matched-path", b"")
            or headers.get(b"x-now-route-matches", b"")
        ).decode("utf-8")
        
        if forwarded_uri and not forwarded_uri.startswith("/api/index"):
            scope["path"] = forwarded_uri.split("?")[0]
        else:
            path = scope.get("path", "")
            for prefix in ["/api/index.py", "/api/index"]:
                if path.startswith(prefix):
                    scope["path"] = path[len(prefix):] or "/"
                    break

    await fastapi_app(scope, receive, send)
