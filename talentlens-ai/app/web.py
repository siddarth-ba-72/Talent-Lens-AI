"""Serves the built React UI from the same origin as the API."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles


logger = logging.getLogger(__name__)

# Never answered with the UI shell: an unknown API path must stay a JSON 404.
_RESERVED_PREFIXES = {"api", "ai", "assets", "docs", "redoc", "openapi.json"}

# The shell is tiny and names the hashed bundles, so it must always be revalidated.
# Its CSP only lets scripts from this origin run, which is the main defence
# against injected script reading the access token out of localStorage.
_INDEX_HEADERS = {
    "Cache-Control": "no-cache",
    "Content-Security-Policy": "; ".join(
        [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' data: https://fonts.gstatic.com",
            "img-src 'self' data: https:",
            "connect-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
        ]
    ),
}


class _HashedAssets(StaticFiles):
    """Vite fingerprints everything under /assets, so it can be cached forever."""

    def file_response(self, *args, **kwargs) -> Response:
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


def mount_ui(app: FastAPI, static_dir: Path) -> bool:
    """Mount the UI build. Must be called after every API route is registered."""
    root = static_dir.resolve()
    index_file = root / "index.html"
    if not index_file.is_file():
        logger.warning(
            "UI build not found at %s; serving the API only. Run `npm run build` in talentlens-client.", root
        )
        return False

    if (root / "assets").is_dir():
        app.mount("/assets", _HashedAssets(directory=root / "assets"), name="assets")

    @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    async def serve_ui(path: str) -> Response:
        if path.split("/", 1)[0] in _RESERVED_PREFIXES:
            raise HTTPException(status_code=404, detail="Not Found")

        if path:
            candidate = (root / path).resolve()
            if candidate.is_relative_to(root) and candidate.is_file():
                return FileResponse(candidate)

        # Client-side route (e.g. /searches/123): hand back the shell and let the router take over.
        return FileResponse(index_file, headers=_INDEX_HEADERS)

    return True
