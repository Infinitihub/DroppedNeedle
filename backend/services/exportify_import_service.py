"""Import playlists exported by Exportify."""

from __future__ import annotations

import asyncio
import csv
import hashlib
import io
from typing import Any

from infrastructure.queue.priority_queue import RequestPriority
from repositories.async_playlist_repository import AsyncPlaylistRepository
from repositories.musicbrainz_album import _pick_best_release_group
from repositories.musicbrainz_base import mb_api_get

MAX_EXPORT_SIZE = 10 * 1024 * 1024
MAX_TRACKS = 5000
_MB_CONCURRENCY = 4


class InvalidExportifyFileError(ValueError):
    pass


def _int_or_none(value: str) -> int | None:
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


def parse_exportify_csv(data: bytes) -> list[dict[str, Any]]:
    if len(data) > MAX_EXPORT_SIZE:
        raise InvalidExportifyFileError("Exportify CSV must be 10 MB or smaller")
    try:
        reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
        headers = {header.strip() for header in (reader.fieldnames or []) if header}
    except (UnicodeDecodeError, csv.Error) as exc:
        raise InvalidExportifyFileError("The file is not a valid UTF-8 CSV") from exc

    required = {"Track Name", "Artist Name(s)", "Album Name"}
    missing = required - headers
    if missing:
        missing_names = ", ".join(sorted(missing))
        raise InvalidExportifyFileError(f"Missing Exportify columns: {missing_names}")

    rows = []
    for row in reader:
        if not any((value or "").strip() for value in row.values()):
            continue
        if len(rows) >= MAX_TRACKS:
            raise InvalidExportifyFileError(f"Exportify CSV may contain at most {MAX_TRACKS} tracks")
        track_name = (row.get("Track Name") or "").strip()
        artist_name = (row.get("Artist Name(s)") or "").strip()
        album_name = (row.get("Album Name") or "").strip()
        if not track_name or not artist_name or not album_name:
            continue
        rows.append(
            {
                "track_name": track_name,
                "artist_name": artist_name,
                "album_name": album_name,
                "album_artist_name": (row.get("Album Artist Name(s)") or "").strip(),
                "isrc": (row.get("ISRC") or "").strip() or None,
                "album_image": (row.get("Album Image URL") or "").strip() or None,
                "track_number": _int_or_none((row.get("Track Number") or "").strip()),
                "disc_number": _int_or_none((row.get("Disc Number") or "").strip()),
                "duration": (
                    _int_or_none((row.get("Track Duration (ms)") or "").strip()) // 1000
                    if _int_or_none((row.get("Track Duration (ms)") or "").strip()) is not None
                    else None
                ),
            }
        )
    if not rows:
        raise InvalidExportifyFileError("The Exportify CSV contains no usable tracks")
    return rows


class ExportifyImportService:
    def __init__(
        self, playlist_repo, mb_repo, playlist_service, async_playlist_repo=None
    ) -> None:
        if async_playlist_repo is None and playlist_repo is None:
            raise ValueError("A playlist repository is required.")
        self._async_repo = (
            async_playlist_repo
            if async_playlist_repo is not None
            else AsyncPlaylistRepository(playlist_repo)
        )
        self._mb_repo = mb_repo
        self._playlist_service = playlist_service

    async def import_csv(self, user_id: str, name: str, data: bytes) -> str:
        rows = parse_exportify_csv(data)
        source_ref = f"exportify:{hashlib.sha256(data).hexdigest()}"
        existing = await self._playlist_service.get_by_source_ref(source_ref, user_id)
        if existing:
            playlist_id = existing.id
        else:
            playlist = await self._playlist_service.create_playlist(
                name.strip() or "Exportify Playlist",
                source_ref=source_ref,
                user_id=user_id,
            )
            playlist_id = playlist.id

        album_keys = {(r["artist_name"], r["album_name"]) for r in rows}
        semaphore = asyncio.Semaphore(_MB_CONCURRENCY)

        async def resolve(key: tuple[str, str]) -> tuple[tuple[str, str], str | None]:
            artist, album = key
            isrc = next((r["isrc"] for r in rows if (r["artist_name"], r["album_name"]) == key and r["isrc"]), None)
            async with semaphore:
                return key, await self._resolve_mbid(isrc, artist, album)

        resolved = dict(await asyncio.gather(*(resolve(key) for key in album_keys)))
        existing_tracks = await self._async_repo.get_tracks(playlist_id)
        if existing_tracks:
            await self._async_repo.remove_tracks(playlist_id, [track.id for track in existing_tracks])
        await self._async_repo.add_tracks(
            playlist_id,
            [
                {
                    **row,
                    "album_id": resolved.get((row["artist_name"], row["album_name"])) or "",
                    "source_type": "",
                    "cover_url": row["album_image"],
                }
                for row in rows
            ],
        )
        return playlist_id

    async def _resolve_mbid(self, isrc: str | None, artist: str, album: str) -> str | None:
        if isrc:
            try:
                data = await mb_api_get(f"/isrc/{isrc}", priority=RequestPriority.BACKGROUND_SYNC)
                recordings = data.get("recordings") or []
                if isinstance(recordings, dict):
                    recordings = [recordings]
                for recording in recordings:
                    recording_id = recording.get("id")
                    if recording_id:
                        mbid = await self._mb_repo.resolve_recording_to_release_group(recording_id)
                        if mbid:
                            return mbid
                releases = [release for recording in recordings for release in recording.get("releases") or []]
                best = _pick_best_release_group(releases)
                if best:
                    return best[0]
            except Exception:  # noqa: BLE001
                pass
        try:
            results = await self._mb_repo.search_release_groups(artist, album, limit=3, include_all_types=False)
            return results[0].musicbrainz_id if results else None
        except Exception:  # noqa: BLE001
            return None