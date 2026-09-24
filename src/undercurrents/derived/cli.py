import argparse
from pathlib import Path

from undercurrents.derived import features, show_format
from undercurrents.storage import db

DEFAULT_DB_PATH = "data/undercurrents.db"


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="undercurrents.derived.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="Recompute the derived feature tables")
    build.add_argument("--db-path", default=DEFAULT_DB_PATH)

    args = parser.parse_args(argv)
    if args.command == "build":
        conn = db.get_connection(Path(args.db_path))
        db.initialize_schema(conn)
        counts = features.rebuild(conn)
        print(f"song_features: {counts['songs']} rows")
        print(f"setlist_features: {counts['setlists']} rows")
        print(f"show_format: {show_format.rebuild(conn)}")
        conn.close()


if __name__ == "__main__":
    main()
