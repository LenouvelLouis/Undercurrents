import argparse
from datetime import datetime
from pathlib import Path

from undercurrents.prediction import evaluate
from undercurrents.prediction.agent import PredictionAgent
from undercurrents.storage import db

DEFAULT_DB_PATH = "data/undercurrents.db"
DATE_FORMAT = "%Y-%m-%d"


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="undercurrents-prediction")
    subparsers = parser.add_subparsers(dest="command", required=True)

    predict_parser = subparsers.add_parser("predict")
    predict_parser.add_argument("--date")
    predict_parser.add_argument("--db-path", default=DEFAULT_DB_PATH)

    evaluate_parser = subparsers.add_parser("evaluate")
    evaluate_parser.add_argument("--holdout-shows", type=int, default=10)
    evaluate_parser.add_argument("--db-path", default=DEFAULT_DB_PATH)

    args = parser.parse_args(argv)
    conn = db.get_connection(Path(args.db_path))

    if args.command == "predict":
        reference_date = datetime.strptime(args.date, DATE_FORMAT).date() if args.date else None
        predictions = PredictionAgent().predict_next_show(conn, reference_date=reference_date)
        print(f"Top {min(20, len(predictions))} most likely songs:")
        for prediction in predictions[:20]:
            print(f"  {prediction.probability:.3f}  {prediction.song_name}")

    elif args.command == "evaluate":
        results = evaluate.backtest(conn, holdout_shows=args.holdout_shows)
        mean_accuracy = sum(r["top_n_accuracy"] for r in results) / len(results)
        print(f"Backtested on {len(results)} held-out shows, mean top-N accuracy: {mean_accuracy:.1%}")

    conn.close()


if __name__ == "__main__":
    main()
