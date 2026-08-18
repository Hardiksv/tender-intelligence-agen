import sys
import os
from urllib.parse import parse_qs, unquote

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app as fastapi_app

async def app(scope, receive, send):
    if scope["type"] == "http":
        qs = scope.get("query_string", b"").decode("utf-8")
        parsed = parse_qs(qs)
        
        target_path = None
        if "__path__" in parsed and parsed["__path__"][0]:
            target_path = unquote(parsed["__path__"][0])
        
        if not target_path or target_path in ["/api/index.py", "/api/index", "/"]:
            headers = dict(scope.get("headers", []))
            for h_name in [b"x-forwarded-uri", b"x-now-route-matches", b"x-matched-path"]:
                val = headers.get(h_name, b"").decode("utf-8")
                if val and not val.startswith("/api/index"):
                    target_path = val.split("?")[0]
                    break

        if target_path:
            while target_path.startswith("//"):
                target_path = target_path[1:]
            scope["path"] = target_path

    await fastapi_app(scope, receive, send)
