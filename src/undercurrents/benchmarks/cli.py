import argparse
from pathlib import Path

from undercurrents.benchmarks import data, runner
from undercurrents.storage import db

DEFAULT_DB_PATH = "data/undercurrents.db"


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="undercurrents.benchmarks.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run", help="Train every model and write the benchmark JSON")
    run_parser.add_argument("--db-path", default=DEFAULT_DB_PATH)
    run_parser.add_argument("--holdout-shows", type=int, default=data.DEFAULT_HOLDOUT_SHOWS)
    run_parser.add_argument("--output", default=str(runner.DEFAULT_OUTPUT))

    args = parser.parse_args(argv)
    if args.command == "run":
        conn = db.get_connection(Path(args.db_path))
        db.initialize_schema(conn)
        results = runner.run_all(conn, holdout_shows=args.holdout_shows)
        path = runner.write(results, Path(args.output))
        conn.close()

        seq = results["sequence"]
        print(f"wrote {path}")
        print(
            f"  sequence  baseline top-1 {seq['baseline']['top_1_accuracy']:.3f} | "
            f"GRU top-1 {seq['model']['top_1_accuracy']:.3f} -> {seq['winner']}"
        )
        tab = results.get("tabular", {})
        if "baseline" in tab:
            print(
                f"  tabular   baseline F1 {tab['baseline']['f1']:.3f} | "
                f"MLP F1 {tab['model']['f1']:.3f} -> {tab['winner']}"
            )
        print(f"  item2vec  {results['item2vec']['songs']} songs, {results['item2vec']['dimensions']}d")


if __name__ == "__main__":
    main()
