import sys
import os
from urllib.parse import parse_qs

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app as fastapi_app

async def app(scope, receive, send):
    if scope["type"] == "http":
        qs = scope.get("query_string", b"").decode("utf-8")
        parsed = parse_qs(qs)
        if "__path__" in parsed and parsed["__path__"][0]:
            target_path = parsed["__path__"][0]
            while target_path.startswith("//"):
                target_path = target_path[1:]
            scope["path"] = target_path

    await fastapi_app(scope, receive, send)
