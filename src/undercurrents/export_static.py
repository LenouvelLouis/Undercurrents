"""Export every API response the web app reads as static JSON files.

The front end only issues parameterless GETs, and the models are frozen, so each response is a
pure function of the database. Writing them all to disk lets the site be served as plain files
(Cloudflare Pages) with no Python server: `/api/shows/abc` becomes `<out>/shows/abc.json`.

Usage:
    uv run python -m undercurrents.export_static            # writes web/public/data
    uv run python -m undercurrents.export_static --out DIR
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

from undercurrents.api.app import app

PREFIX = "/api"

# Path parameter -> (listing endpoint that enumerates it, field holding the id).
ID_SOURCES: dict[str, tuple[str, str]] = {
    "song_id": ("/songs", "id"),
    "venue_id": ("/analysis/venues", "id"),
    "cluster_id": ("/analysis/clusters", "cluster_id"),
    "setlist_id": ("/shows", "id"),
}


def _templates() -> list[str]:
    """Every GET route under /api, without the prefix, read from the OpenAPI schema."""
    paths = app.openapi()["paths"]
    return [p[len(PREFIX):] for p, ops in paths.items() if p.startswith(PREFIX) and "get" in ops]


def _param(template: str) -> str | None:
    if "{" not in template:
        return None
    return template[template.index("{") + 1 : template.index("}")]


def export(out: Path) -> int:
    client = TestClient(app)
    templates = _templates()
    unknown = [t for t in templates if (p := _param(t)) and p not in ID_SOURCES]
    if unknown:
        raise SystemExit(f"No id source for route(s): {unknown}. Add them to ID_SOURCES.")

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    cache: dict[str, bytes] = {}

    def fetch(path: str) -> bytes | None:
        if path not in cache:
            response = client.get(PREFIX + path)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            cache[path] = response.content
        return cache[path]

    def write(path: str, body: bytes) -> None:
        target = out / f"{path.lstrip('/')}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)

    written = skipped = 0
    started = time.perf_counter()
    for template in templates:
        param = _param(template)
        if param is None:
            body = fetch(template)
            if body is None:
                raise SystemExit(f"{template} returned 404")
            write(template, body)
            written += 1
            continue

        listing, field = ID_SOURCES[param]
        items = json.loads(fetch(listing) or b"[]")
        for item in items:
            path = template.replace("{" + param + "}", str(item[field]))
            body = fetch(path)
            if body is None:
                skipped += 1
                continue
            write(path, body)
            written += 1
        print(f"  {template}: {len(items)} ids", file=sys.stderr)

    size = sum(f.stat().st_size for f in out.rglob("*.json"))
    print(
        f"Exported {written} files ({size / 1e6:.1f} MB) to {out} "
        f"in {time.perf_counter() - started:.1f}s, {skipped} ids without data skipped.",
        file=sys.stderr,
    )
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=Path("web/public/data"))
    export(parser.parse_args().out)


if __name__ == "__main__":
    main()
