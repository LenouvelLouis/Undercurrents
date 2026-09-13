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

        predicted_length = PredictionAgent().predict_setlist_length(conn, reference_date=reference_date)
        print(f"Predicted setlist length: {predicted_length:.1f} songs")

        print("Predicted position for the top 5 most likely songs:")
        for prediction in predictions[:5]:
            probabilities = PredictionAgent().predict_position_category(
                conn, prediction.song_id, reference_date=reference_date
            )
            top_category = max(probabilities, key=probabilities.get)
            print(f"  {prediction.song_name}: {top_category} ({probabilities[top_category]:.3f})")

        predicted_date = PredictionAgent().predict_next_show_date(conn, as_of_date=reference_date)
        print(f"Predicted next show date: {predicted_date.isoformat()}")

        country_predictions = PredictionAgent().predict_next_show_country(
            conn, reference_date=reference_date
        )
        print("Top 3 predicted countries:")
        for prediction in country_predictions[:3]:
            print(f"  {prediction.probability:.3f}  {prediction.country}")

    elif args.command == "evaluate":
        results = evaluate.backtest(conn, holdout_shows=args.holdout_shows)
        mean_accuracy = sum(r["top_n_accuracy"] for r in results) / len(results)
        print(f"Backtested on {len(results)} held-out shows, mean top-N accuracy: {mean_accuracy:.1%}")

        length_results = evaluate.backtest_setlist_length(conn, holdout_shows=args.holdout_shows)
        mae = sum(r["absolute_error"] for r in length_results) / len(length_results)
        mean_actual = sum(r["actual_length"] for r in length_results) / len(length_results)
        print(f"Setlist length MAE: {mae:.2f} songs (held-out shows averaged {mean_actual:.1f} songs)")

        position_results = evaluate.backtest_position_category(conn, holdout_shows=args.holdout_shows)
        summary = evaluate.summarize_position_backtest(position_results)
        recall_str = ", ".join(f"{cat}={r:.1%}" for cat, r in summary["recall_by_category"].items())
        print(
            f"Position category accuracy: {summary['overall_accuracy']:.1%} overall "
            f"(recall by category: {recall_str})"
        )

        date_results = evaluate.backtest_next_show_date(conn, holdout_shows=args.holdout_shows)
        date_summary = evaluate.summarize_next_show_date_backtest(date_results)
        print(
            f"Next show date MAE: {date_summary['mae_days']:.1f} days "
            f"(median: {date_summary['median_absolute_error_days']:.1f} days)"
        )

        country_results = evaluate.backtest_next_show_country(conn, holdout_shows=args.holdout_shows)
        country_summary = evaluate.summarize_next_show_country_backtest(country_results)
        print(
            f"Next show country accuracy: top-1={country_summary['top_1_accuracy']:.1%}, "
            f"top-3={country_summary['top_3_accuracy']:.1%}"
        )

    conn.close()


if __name__ == "__main__":
    main()
