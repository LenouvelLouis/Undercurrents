import argparse
import os
import sys
from pathlib import Path

from undercurrents.ingestion.pipeline import (
    ArtistNotFoundError,
    fetch_and_store_all_setlists,
    resolve_artist_mbid,
)
from undercurrents.ingestion.setlistfm_client import SetlistFmClient, SetlistFmError
from undercurrents.storage import db

DEFAULT_DB_PATH = "data/undercurrents.db"


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="undercurrents-ingest")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch")
    fetch_parser.add_argument("--force-refresh", action="store_true")
    fetch_parser.add_argument("--db-path", default=DEFAULT_DB_PATH)

    args = parser.parse_args(argv)

    if args.command == "fetch":
        api_key = os.environ.get("SETLISTFM_API_KEY")
        if not api_key:
            parser.error("SETLISTFM_API_KEY environment variable is not set")

        db_path = Path(args.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = db.get_connection(db_path)
        try:
            db.initialize_schema(conn)
            db.ensure_setlists_info_column(conn)
            client = SetlistFmClient(api_key=api_key)

            artist_mbid = resolve_artist_mbid(conn, client, force_refresh=args.force_refresh)
            count = fetch_and_store_all_setlists(
                conn, client, artist_mbid, force_refresh=args.force_refresh
            )
        except (ArtistNotFoundError, SetlistFmError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        finally:
            conn.close()

        print(f"Stored {count} setlists.")


if __name__ == "__main__":
    main()
