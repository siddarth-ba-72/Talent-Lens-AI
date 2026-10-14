from __future__ import annotations

import math
from typing import Generic, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class PageResponse(BaseModel, Generic[T]):
    content: list[T]
    totalElements: int
    totalPages: int
    page: int
    size: int

    @classmethod
    def of(cls, content: list[T], total: int, page: int, size: int) -> "PageResponse[T]":
        return cls(
            content=content,
            totalElements=total,
            totalPages=math.ceil(total / size) if size else 1,
            page=page,
            size=size,
        )
