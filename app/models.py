from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MediaType(StrEnum):
    MOVIE = "movie"
    SERIES = "series"


class RequestStatus(StrEnum):
    RECEIVED = "received"
    NEEDS_INFO = "needs_info"
    SEARCHING = "searching"
    REVIEW = "review"
    APPROVED = "approved"
    ADDED = "added"
    DUPLICATE = "duplicate"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class ParsedRequest:
    title: str | None
    year: int | None
    media_type: MediaType | None
    original_text: str
    confidence: float = 0.0

    @property
    def missing_fields(self) -> list[str]:
        missing: list[str] = []
        if not self.title:
            missing.append("title")
        if not self.year:
            missing.append("year")
        if not self.media_type:
            missing.append("type")
        return missing

    @property
    def is_complete(self) -> bool:
        return not self.missing_fields
