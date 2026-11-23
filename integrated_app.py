"""Serve Ashrath's site and the V3 API from one origin."""
import os
from pathlib import Path
from starlette.staticfiles import StaticFiles
from backend.main import app

public = Path(os.getenv("MS_PUBLIC_DIR", "dist"))
# Register after all API routes. Only the built public directory is served.
app.mount("/", StaticFiles(directory=public, html=True), name="playground")

@app.middleware("http")
async def site_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path not in {"/docs", "/redoc", "/docs/oauth2-redirect"}:
        response.headers["Content-Security-Policy"] = "default-src 'self'; base-uri 'none'; frame-ancestors 'none'"
    return response
