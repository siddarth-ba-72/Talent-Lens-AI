from __future__ import annotations

import logging

from fastapi import FastAPI

from app.api.jd_parser import router as jd_parser_router
from app.api.sourcing import router as sourcing_router
from app.config import get_settings


settings = get_settings()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TalentLens AI Service",
    version="0.1.0",
    description="Phase 2 AI service for JD parsing and candidate sourcing orchestration.",
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env, "provider": settings.llm_provider}


app.include_router(jd_parser_router)
app.include_router(sourcing_router)
