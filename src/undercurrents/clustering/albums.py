"""Which record each song belongs to, from MusicBrainz.

Rather than looking songs up one by one, this browses the artist's own official releases
(with their track listings) and builds a title index: every studio track points at the
record it first appeared on. Albums and EPs compete on date, so a song from the 2008 EP stays
an EP song even though a later album also carries it; a single only counts when no album or
EP holds the song, so a lead single does not steal a track from its album. Only the original
editions of each record are read (the releases dated exactly on the record's first release
date, which covers same-day regional and format variants): Japanese editions, collector's
editions and reissues append live versions and older songs as bonus tracks and would
otherwise pull them into the wrong era. Recordings MusicBrainz marks as live, demo or remix
are skipped wherever they appear. Live albums,
compilations, remixes and demos are skipped for the same reason. A song found only on a
later edition (a B-side added as a bonus track) is kept as a fallback, typed "Bonus", so it
is not mistaken for an unreleased song either. A song on the site is matched by its
recording MBID when it has one, otherwise by normalised title. Songs that match nothing are
left without an album and are counted, not guessed: most are covers of other artists.
"""

from __future__ import annotations

import re
import unicodedata

from undercurrents.clustering.mbid_client import MusicBrainzClient

ARTIST_MBID = "63aa26c3-d59b-4da4-84ac-716b54f1ef4d"  # Tame Impala
TYPE_RANK = {"Album": 0, "EP": 1, "Single": 2, "Bonus": 3}
PAGE_SIZE = 100
NOT_STUDIO = re.compile(r"\b(live|demo|remix|rehearsal)\b", re.IGNORECASE)


def normalize_title(title: str) -> str:
    # apostrophes vanish rather than split a word: MusicBrainz writes "Won’t", setlist.fm "Won't"
    title = re.sub("[\u2018\u2019'`]", "", title)
    text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    text = text.lower().replace("&", "and")
    text = re.sub(r"[\(\[].*?[\)\]]", " ", text)  # "(Edit)", "[Live]"
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def ensure_album_columns(conn) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(songs)")}
    for column in ("album", "album_type", "album_date", "album_mbid"):
        if column not in existing:
            conn.execute(f"ALTER TABLE songs ADD COLUMN {column} TEXT")
    conn.commit()


def fetch_releases(client, artist_mbid: str = ARTIST_MBID) -> list[dict]:
    releases: list[dict] = []
    offset = 0
    while True:
        _, payload = client.get(
            "/release",
            {
                "artist": artist_mbid,
                "status": "official",
                "type": "album|ep|single",
                "inc": "recordings+release-groups",
                "limit": PAGE_SIZE,
                "offset": offset,
                "fmt": "json",
            },
        )
        page = payload.get("releases") or []
        releases.extend(page)
        offset += len(page)
        if not page or offset >= payload.get("release-count", 0):
            return releases


def build_index(releases: list[dict]) -> tuple[dict[str, dict], dict[str, dict]]:
    """(title -> best candidate, recording mbid -> best candidate)."""
    by_title: dict[str, dict] = {}
    by_recording: dict[str, dict] = {}
    bonus_title: dict[str, dict] = {}
    bonus_recording: dict[str, dict] = {}

    def key(candidate: dict) -> tuple:
        return (
            candidate["album_type"] == "Single",
            candidate["album_date"] or "9999",
            TYPE_RANK[candidate["album_type"]],
        )

    def better(new: dict, old: dict | None) -> bool:
        return old is None or key(new) < key(old)

    # the date of each record's original editions: its first-release-date when some release
    # carries exactly that date, otherwise the earliest date among its releases
    dates_by_group: dict[str, set[str]] = {}
    for release in releases:
        group_id = (release.get("release-group") or {}).get("id")
        if group_id and release.get("date"):
            dates_by_group.setdefault(group_id, set()).add(release["date"])

    def is_original_edition(release: dict, group: dict) -> bool:
        dates = dates_by_group.get(group.get("id"), set())
        if not dates or not release.get("date"):
            return True
        first = group.get("first-release-date")
        original = first if first in dates else min(dates)
        return release["date"] == original

    for release in releases:
        group = release.get("release-group") or {}
        primary = group.get("primary-type")
        if primary not in TYPE_RANK or group.get("secondary-types"):
            continue
        original = is_original_edition(release, group)
        candidate = {
            "album": group.get("title") or release.get("title"),
            "album_type": primary if original else "Bonus",
            "album_date": group.get("first-release-date") or release.get("date") or None,
            "album_mbid": group.get("id"),
        }
        titles, recordings = (by_title, by_recording) if original else (bonus_title, bonus_recording)
        for medium in release.get("media") or []:
            for track in medium.get("tracks") or []:
                recording = track.get("recording") or {}
                if NOT_STUDIO.search(recording.get("disambiguation") or ""):
                    continue
                title = normalize_title(recording.get("title") or track.get("title") or "")
                if title and better(candidate, titles.get(title)):
                    titles[title] = candidate
                rid = recording.get("id")
                if rid and better(candidate, recordings.get(rid)):
                    recordings[rid] = candidate
    for title, candidate in bonus_title.items():
        by_title.setdefault(title, candidate)
    for rid, candidate in bonus_recording.items():
        by_recording.setdefault(rid, candidate)
    return by_title, by_recording


def assign_albums(conn, client=None, releases: list[dict] | None = None) -> dict:
    ensure_album_columns(conn)
    if releases is None:
        releases = fetch_releases(client or MusicBrainzClient())
    by_title, by_recording = build_index(releases)

    matched_mbid = matched_title = unmatched = 0
    filled_dates = 0
    for song in conn.execute("SELECT id, name, mbid, release_date FROM songs").fetchall():
        candidate = by_recording.get(song["mbid"]) if song["mbid"] else None
        if candidate:
            matched_mbid += 1
        else:
            candidate = by_title.get(normalize_title(song["name"]))
            if candidate:
                matched_title += 1
        if not candidate:
            unmatched += 1
            continue
        conn.execute(
            "UPDATE songs SET album = ?, album_type = ?, album_date = ?, album_mbid = ? WHERE id = ?",
            (candidate["album"], candidate["album_type"], candidate["album_date"], candidate["album_mbid"], song["id"]),
        )
        if song["release_date"] is None and candidate["album_date"] and candidate["album_type"] != "Bonus":
            conn.execute("UPDATE songs SET release_date = ? WHERE id = ?", (candidate["album_date"], song["id"]))
            filled_dates += 1
    conn.commit()
    return {
        "releases_scanned": len(releases),
        "matched_by_mbid": matched_mbid,
        "matched_by_title": matched_title,
        "unmatched": unmatched,
        "release_dates_filled": filled_dates,
    }


if __name__ == "__main__":
    import sqlite3
    import sys

    connection = sqlite3.connect(sys.argv[1] if len(sys.argv) > 1 else "data/undercurrents.db")
    connection.row_factory = sqlite3.Row
    print(assign_albums(connection))
