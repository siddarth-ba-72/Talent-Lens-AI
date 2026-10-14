from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.api.auth import router as auth_router
from app.api.candidates import router as candidates_router
from app.api.jd_parser import router as jd_parser_router
from app.api.searches import router as searches_router
from app.api.share_requests import router as share_requests_router
from app.api.sourcing import router as sourcing_router
from app.config import get_settings
from app.db.mongo import close_mongo, init_mongo
from app.db.postgres import create_schema, dispose_engine, init_engine
from app.errors import error_response, register_exception_handlers
from app.services import sourcing_service
from app.web import mount_ui


settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Largest request body accepted (the JD upload limit plus multipart overhead).
MAX_REQUEST_BYTES = 10 * 1024 * 1024


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_engine(settings.database_url)
    await create_schema()
    await init_mongo(settings.mongodb_uri, settings.mongodb_database)

    orphaned = await sourcing_service.fail_orphaned_tasks()
    if orphaned:
        logger.warning("Marked %d interrupted sourcing task(s) as failed", orphaned)

    yield

    await close_mongo()
    await dispose_engine()


app = FastAPI(
    title="TalentLens",
    version="0.2.0",
    description="TalentLens API: auth, searches, candidate sourcing and scoring. Also serves the web UI.",
    lifespan=lifespan,
    docs_url="/docs" if settings.expose_docs else None,
    redoc_url="/redoc" if settings.expose_docs else None,
    openapi_url="/openapi.json" if settings.expose_docs else None,
)

register_exception_handlers(app)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=True,
    )


@app.middleware("http")
async def harden_http(request: Request, call_next) -> Response:
    declared_length = request.headers.get("content-length")
    if declared_length and declared_length.isdigit() and int(declared_length) > MAX_REQUEST_BYTES:
        return error_response(request, 413, "FILE_TOO_LARGE", "Request body is too large")

    response = await call_next(request)

    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if settings.use_secure_cookies:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    if request.url.path.startswith(("/api/", "/ai/")):
        # Responses carry tokens and personal data; keep them out of shared caches.
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env, "provider": settings.llm_provider}


app.include_router(auth_router)
app.include_router(searches_router)
app.include_router(candidates_router)
app.include_router(share_requests_router)
app.include_router(jd_parser_router)
app.include_router(sourcing_router)

# Last: the UI catch-all must not shadow any API route.
mount_ui(app, settings.static_dir)
