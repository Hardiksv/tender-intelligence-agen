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
        
        # 1. Check Vercel regex match parameter '1' (from $1 rewrite)
        if "1" in parsed and parsed["1"][0]:
            target_path = "/" + unquote(parsed["1"][0]).lstrip("/")
        # 2. Check custom __path__ parameter
        elif "__path__" in parsed and parsed["__path__"][0]:
            target_path = "/" + unquote(parsed["__path__"][0]).lstrip("/")
        # 3. Check Vercel headers
        else:
            headers = dict(scope.get("headers", []))
            for h_name in [b"x-now-route-matches", b"x-forwarded-uri", b"x-matched-path"]:
                val = headers.get(h_name, b"").decode("utf-8")
                if val:
                    # x-now-route-matches format: "1=api%2Ftenders"
                    if "1=" in val:
                        match_part = val.split("1=")[-1].split("&")[0]
                        target_path = "/" + unquote(match_part).lstrip("/")
                        break
                    elif not val.startswith("/api/index"):
                        target_path = "/" + val.split("?")[0].lstrip("/")
                        break

        if target_path and target_path != "/api/index.py" and target_path != "/api/index":
            scope["path"] = target_path
            scope["raw_path"] = target_path.encode("utf-8")
        elif scope.get("path") in ["/api/index.py", "/api/index"]:
            scope["path"] = "/"
            scope["raw_path"] = b"/"

    await fastapi_app(scope, receive, send)
