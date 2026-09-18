from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

import httpx


@dataclass(slots=True)
class Match:
    item: dict[str, Any]
    confidence: float
    label: str


class ArrClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 20.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=timeout, headers={"X-Api-Key": api_key})

    async def close(self) -> None:
        await self.client.aclose()

    @staticmethod
    def score(title: str, year: int, candidate_title: str, candidate_year: int | None) -> float:
        title_score = SequenceMatcher(None, title.casefold(), candidate_title.casefold()).ratio()
        year_score = 1.0 if candidate_year == year else 0.0
        return round((title_score * 0.75) + (year_score * 0.25), 4)


class RadarrClient(ArrClient):
    async def lookup(self, title: str, year: int) -> list[Match]:
        r = await self.client.get(f"{self.base_url}/api/v3/movie/lookup", params={"term": f"{title} {year}"})
        r.raise_for_status()
        matches = []
        for item in r.json():
            score = self.score(title, year, item.get("title", ""), item.get("year"))
            matches.append(Match(item=item, confidence=score, label=f"{item.get('title')} ({item.get('year')})"))
        return sorted(matches, key=lambda x: x.confidence, reverse=True)

    async def existing(self, tmdb_id: int) -> dict[str, Any] | None:
        r = await self.client.get(f"{self.base_url}/api/v3/movie")
        r.raise_for_status()
        return next((m for m in r.json() if m.get("tmdbId") == tmdb_id), None)

    async def add(self, item: dict[str, Any], *, root_folder: str, quality_profile_id: int) -> dict[str, Any]:
        payload = {
            "title": item["title"],
            "qualityProfileId": quality_profile_id,
            "titleSlug": item.get("titleSlug"),
            "images": item.get("images", []),
            "tmdbId": item["tmdbId"],
            "year": item.get("year"),
            "rootFolderPath": root_folder,
            "monitored": True,
            "minimumAvailability": "released",
            "addOptions": {"searchForMovie": True},
        }
        r = await self.client.post(f"{self.base_url}/api/v3/movie", json=payload)
        r.raise_for_status()
        return r.json()


class SonarrClient(ArrClient):
    async def lookup(self, title: str, year: int) -> list[Match]:
        r = await self.client.get(f"{self.base_url}/api/v3/series/lookup", params={"term": f"{title} {year}"})
        r.raise_for_status()
        matches = []
        for item in r.json():
            candidate_year = item.get("year")
            if not candidate_year and item.get("firstAired"):
                try:
                    candidate_year = int(item["firstAired"][:4])
                except Exception:
                    candidate_year = None
            score = self.score(title, year, item.get("title", ""), candidate_year)
            matches.append(Match(item=item, confidence=score, label=f"{item.get('title')} ({candidate_year or 'unknown'})"))
        return sorted(matches, key=lambda x: x.confidence, reverse=True)

    async def existing(self, tvdb_id: int) -> dict[str, Any] | None:
        r = await self.client.get(f"{self.base_url}/api/v3/series")
        r.raise_for_status()
        return next((s for s in r.json() if s.get("tvdbId") == tvdb_id), None)

    async def add(self, item: dict[str, Any], *, root_folder: str, quality_profile_id: int) -> dict[str, Any]:
        payload = {
            "title": item["title"],
            "qualityProfileId": quality_profile_id,
            "titleSlug": item.get("titleSlug"),
            "images": item.get("images", []),
            "tvdbId": item["tvdbId"],
            "year": item.get("year"),
            "rootFolderPath": root_folder,
            "monitored": True,
            "seasonFolder": True,
            "addOptions": {"monitor": "all", "searchForMissingEpisodes": True},
        }
        r = await self.client.post(f"{self.base_url}/api/v3/series", json=payload)
        r.raise_for_status()
        return r.json()

async def radarr_library_stats(base_url: str, api_key: str) -> dict[str, int]:
    if not base_url or not api_key:
        return {"total": 0, "downloaded": 0}
    async with httpx.AsyncClient(timeout=10, headers={"X-Api-Key": api_key}) as client:
        r = await client.get(f"{base_url.rstrip('/')}/api/v3/movie")
        r.raise_for_status()
        items = r.json()
        return {"total": len(items), "downloaded": sum(1 for x in items if x.get("hasFile"))}


async def sonarr_library_stats(base_url: str, api_key: str) -> dict[str, int]:
    if not base_url or not api_key:
        return {"series_total": 0, "episodes_downloaded": 0, "episodes_total": 0}
    async with httpx.AsyncClient(timeout=10, headers={"X-Api-Key": api_key}) as client:
        r = await client.get(f"{base_url.rstrip('/')}/api/v3/series")
        r.raise_for_status()
        items = r.json()
        downloaded = 0
        total = 0
        for s in items:
            stats = s.get("statistics") or {}
            downloaded += int(stats.get("episodeFileCount") or 0)
            total += int(stats.get("totalEpisodeCount") or 0)
        return {"series_total": len(items), "episodes_downloaded": downloaded, "episodes_total": total}
