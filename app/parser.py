from __future__ import annotations

import re

from .models import MediaType, ParsedRequest

YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")
TYPE_PREFIX_RE = re.compile(r"^\s*(movie|film|series|tv|show)\s*[:\-]\s*", re.I)
TYPE_SUFFIX_RE = re.compile(r"\s*[-–—]\s*(movie|film|series|tv|show)\s*$", re.I)

# Lines that are often commentary rather than a title.
COMMENT_PREFIXES = (
    "please ",
    "follow up",
    "also ",
    "thank ",
    "thanks",
    "request to add",
)


def _map_media_type(value: str | None) -> MediaType | None:
    if not value:
        return None
    value = value.lower()
    if value in {"movie", "film"}:
        return MediaType.MOVIE
    if value in {"series", "tv", "show"}:
        return MediaType.SERIES
    return None


def parse_line(line: str) -> ParsedRequest | None:
    raw = line.strip()
    if not raw:
        return None

    media_type: MediaType | None = None

    m = TYPE_PREFIX_RE.search(raw)
    if m:
        media_type = _map_media_type(m.group(1))
        raw = TYPE_PREFIX_RE.sub("", raw).strip()

    m = TYPE_SUFFIX_RE.search(raw)
    if m:
        media_type = media_type or _map_media_type(m.group(1))
        raw = TYPE_SUFFIX_RE.sub("", raw).strip()

    year_match = YEAR_RE.search(raw)
    year = int(year_match.group(1)) if year_match else None

    title = raw
    if year_match:
        title = (raw[: year_match.start()] + raw[year_match.end() :]).strip()
    title = re.sub(r"[()\[\]{}]+", " ", title)
    title = re.sub(r"\s+", " ", title).strip(" :-–—,.")

    if not title or title.lower().startswith(COMMENT_PREFIXES):
        return None

    confidence = 0.35
    if title:
        confidence += 0.2
    if year:
        confidence += 0.2
    if media_type:
        confidence += 0.25

    return ParsedRequest(
        title=title or None,
        year=year,
        media_type=media_type,
        original_text=line.strip(),
        confidence=min(confidence, 1.0),
    )


def parse_message(text: str) -> list[ParsedRequest]:
    """Parse one Discord message into independent media requests.

    We intentionally stay conservative: type and year are required before
    any automatic add. Commentary is ignored where possible.
    """
    results: list[ParsedRequest] = []
    for line in text.splitlines():
        parsed = parse_line(line)
        if parsed:
            results.append(parsed)
    return results


def missing_info_reply(requests: list[ParsedRequest]) -> str:
    lines = []
    for req in requests:
        if not req.is_complete:
            missing = ", ".join(req.missing_fields)
            label = req.title or req.original_text
            lines.append(f"• {label}: missing {missing}")

    if not lines:
        return ""

    return (
        "I need a little more information before I can process this request.\n\n"
        + "\n".join(lines)
        + "\n\nPlease use: `Movie: Title (Year)` or `Series: Title (Year)`."
    )
