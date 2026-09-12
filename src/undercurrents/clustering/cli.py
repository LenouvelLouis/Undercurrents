import argparse
from pathlib import Path

from undercurrents.clustering import clusters, embeddings, features, title_resolution
from undercurrents.clustering.mbid_client import MusicBrainzClient
from undercurrents.storage import db

DEFAULT_DB_PATH = "data/undercurrents.db"


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="undercurrents-clustering")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--force-refresh", action="store_true")
    run_parser.add_argument("--db-path", default=DEFAULT_DB_PATH)

    args = parser.parse_args(argv)

    if args.command == "run":
        db_path = Path(args.db_path)
        conn = db.get_connection(db_path)
        db.initialize_schema(conn)

        client = MusicBrainzClient()
        title_resolution.resolve_song_titles(conn, client, force_refresh=args.force_refresh)

        setlist_ids, _, setlist_matrix = features.build_setlist_song_matrix(conn)
        setlist_embedding = embeddings.compute_2d_embedding(setlist_matrix)
        setlist_labels = clusters.compute_cluster_labels(setlist_embedding)
        clusters.store_setlist_clusters(conn, setlist_ids, setlist_embedding, setlist_labels)

        song_ids, cooccurrence_matrix = features.build_song_cooccurrence_matrix(conn)
        song_embedding = embeddings.compute_2d_embedding(cooccurrence_matrix)
        song_labels = clusters.compute_cluster_labels(song_embedding)
        clusters.store_song_clusters(conn, song_ids, song_embedding, song_labels)

        conn.close()

        n_setlist_clusters = len(set(setlist_labels) - {-1})
        n_song_clusters = len(set(song_labels) - {-1})
        print(
            f"Clustered {len(setlist_ids)} setlists into {n_setlist_clusters} clusters, "
            f"{len(song_ids)} songs into {n_song_clusters} clusters."
        )


if __name__ == "__main__":
    main()
