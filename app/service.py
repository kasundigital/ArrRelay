from __future__ import annotations

import logging
from dataclasses import dataclass

from .arr_client import Match, RadarrClient, SonarrClient
from .config import Settings
from .database import Database
from .models import MediaType, ParsedRequest, RequestStatus
from .telegram_bot import TelegramReviewBot

log = logging.getLogger(__name__)


@dataclass(slots=True)
class PendingReview:
    request: ParsedRequest
    matches: list[Match]


class RequestService:
    def __init__(self, settings: Settings, db: Database, telegram: TelegramReviewBot):
        self.settings = settings
        self.db = db
        self.telegram = telegram
        self.radarr = RadarrClient(settings.radarr_url, settings.radarr_api_key)
        self.sonarr = SonarrClient(settings.sonarr_url, settings.sonarr_api_key)
        self.pending: dict[int, PendingReview] = {}
        telegram.set_review_handler(self.handle_telegram_review)

    async def close(self) -> None:
        await self.radarr.close()
        await self.sonarr.close()

    async def process(
        self,
        req: ParsedRequest,
        *,
        discord_message_id: str,
        discord_user_id: str,
        discord_channel_id: str,
        original_message: str,
    ) -> int | None:
        status = RequestStatus.RECEIVED if req.is_complete else RequestStatus.NEEDS_INFO
        request_id = await self.db.add_request(
            discord_message_id=discord_message_id,
            discord_user_id=discord_user_id,
            discord_channel_id=discord_channel_id,
            original_message=original_message,
            title=req.title,
            year=req.year,
            media_type=req.media_type.value if req.media_type else None,
            status=status.value,
            confidence=req.confidence,
        )
        if request_id is None or not req.is_complete:
            return request_id

        await self.db.update_status(request_id, RequestStatus.SEARCHING.value)
        try:
            matches = await self._lookup(req)
        except Exception as exc:
            log.exception("Lookup failed")
            await self.db.update_status(request_id, RequestStatus.FAILED.value, error=str(exc))
            await self.telegram.send_error(f"🔴 ArrRelay lookup error\n{req.media_type.value.title()}: {req.title} ({req.year})\n{exc}")
            return request_id

        if not matches:
            await self.db.update_status(request_id, RequestStatus.REVIEW.value)
            await self.telegram.send_error(f"⚠️ No match found\n{req.media_type.value.title()}: {req.title} ({req.year})")
            return request_id

        best = matches[0]
        if best.confidence >= self.settings.auto_approve_confidence:
            await self._approve(request_id, req, best)
            return request_id

        self.pending[request_id] = PendingReview(request=req, matches=matches[:5])
        await self.db.update_status(request_id, RequestStatus.REVIEW.value)
        summary = (
            "⚠️ ArrRelay review required\n\n"
            f"{req.media_type.value.title()}: {req.title} ({req.year})\n"
            f"Best confidence: {best.confidence:.0%}\n\n"
            "Select the correct result or cancel."
        )
        await self.telegram.send_review(request_id, summary, matches)
        return request_id

    async def handle_telegram_review(self, request_id: int, index: int | None) -> None:
        pending = self.pending.get(request_id)
        if not pending:
            await self.telegram.send_error(f"⚠️ Review {request_id} is no longer available in memory. Restart/recovery handling will be added next.")
            return
        if index is None:
            await self.db.update_status(request_id, RequestStatus.CANCELLED.value)
            self.pending.pop(request_id, None)
            return
        if index < 0 or index >= len(pending.matches):
            return
        await self._approve(request_id, pending.request, pending.matches[index])
        self.pending.pop(request_id, None)

    async def _lookup(self, req: ParsedRequest) -> list[Match]:
        assert req.title and req.year and req.media_type
        if req.media_type == MediaType.MOVIE:
            return await self.radarr.lookup(req.title, req.year)
        return await self.sonarr.lookup(req.title, req.year)

    async def _approve(self, request_id: int, req: ParsedRequest, match: Match) -> None:
        assert req.media_type
        try:
            if req.media_type == MediaType.MOVIE:
                key = int(match.item["tmdbId"])
                existing = await self.radarr.existing(key)
                if existing:
                    await self.db.update_status(request_id, RequestStatus.DUPLICATE.value, arr_id=str(existing.get("id")))
                    return
                if self.settings.dry_run:
                    await self.db.update_status(request_id, RequestStatus.APPROVED.value, arr_id=f"tmdb:{key}")
                    return
                added = await self.radarr.add(
                    match.item,
                    root_folder=self.settings.radarr_root_folder,
                    quality_profile_id=self.settings.radarr_quality_profile_id,
                )
            else:
                key = int(match.item["tvdbId"])
                existing = await self.sonarr.existing(key)
                if existing:
                    await self.db.update_status(request_id, RequestStatus.DUPLICATE.value, arr_id=str(existing.get("id")))
                    return
                if self.settings.dry_run:
                    await self.db.update_status(request_id, RequestStatus.APPROVED.value, arr_id=f"tvdb:{key}")
                    return
                added = await self.sonarr.add(
                    match.item,
                    root_folder=self.settings.sonarr_root_folder,
                    quality_profile_id=self.settings.sonarr_quality_profile_id,
                )
            await self.db.update_status(request_id, RequestStatus.ADDED.value, arr_id=str(added.get("id")))
        except Exception as exc:
            log.exception("Add failed")
            await self.db.update_status(request_id, RequestStatus.FAILED.value, error=str(exc))
            await self.telegram.send_error(f"🔴 ArrRelay add error\n{req.media_type.value.title()}: {req.title} ({req.year})\n{exc}")
