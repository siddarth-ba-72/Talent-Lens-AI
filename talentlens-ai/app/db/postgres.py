from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Optional

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def normalize_database_url(url: str) -> str:
    """Accept the URL forms hosting providers hand out and select the psycopg driver.

    psycopg understands libpq query options (sslmode, channel_binding, ...) as-is,
    so only the scheme needs rewriting.
    """
    parsed = make_url(url.strip())
    if parsed.drivername in {"postgres", "postgresql", "postgresql+psycopg"}:
        return parsed.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)
    raise ValueError("DATABASE_URL must be a postgresql:// URL")


def init_engine(database_url: str) -> AsyncEngine:
    global _engine, _session_factory
    _engine = create_async_engine(normalize_database_url(database_url), pool_pre_ping=True)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Postgres engine is not initialised")
    return _session_factory


async def create_schema() -> None:
    # Imported for its side effect of registering the tables on Base.metadata.
    from app.db import models  # noqa: F401

    if _engine is None:
        raise RuntimeError("Postgres engine is not initialised")
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory()() as session:
        yield session
