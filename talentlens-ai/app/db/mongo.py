from __future__ import annotations

from typing import Optional

from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.db.documents import CandidateDocument


_client: Optional[AsyncMongoClient] = None


async def init_mongo(uri: str, database: str) -> None:
    global _client
    _client = AsyncMongoClient(uri, tz_aware=True)
    await init_beanie(database=_client[database], document_models=[CandidateDocument])


async def close_mongo() -> None:
    global _client
    if _client is not None:
        await _client.close()
    _client = None
