from dataclasses import dataclass

from undercurrents.clustering import stats as clustering_stats
from undercurrents.orchestrator import facts
from undercurrents.orchestrator.intent import ClassifiedIntent, Intent
from undercurrents.prediction.agent import PredictionAgent
from undercurrents.storage import db


@dataclass(frozen=True)
class RetrievedFacts:
    intent: Intent
    data: dict


def retrieve(conn, classified: ClassifiedIntent) -> RetrievedFacts:
    if classified.intent == Intent.FACT:
        return _retrieve_fact(conn, classified.mentioned_song_name)
    if classified.intent == Intent.PREDICT:
        return _retrieve_prediction(conn)
    if classified.intent == Intent.CLUSTER:
        return _retrieve_cluster_summary(conn)
    return RetrievedFacts(Intent.CHAT, {})


def _retrieve_fact(conn, song_name: str | None) -> RetrievedFacts:
    data = {
        "total_shows": facts.total_show_count(conn),
        "date_range": facts.date_range(conn),
        "most_played_song": facts.most_played_song(conn),
    }
    if song_name is not None:
        song_id = db.get_song_id_by_name(conn, song_name)
        data["mentioned_song"] = song_name
        data["mentioned_song_last_played"] = (
            facts.last_played_date(conn, song_id) if song_id is not None else None
        )
    return RetrievedFacts(Intent.FACT, data)


def _retrieve_prediction(conn) -> RetrievedFacts:
    predictions = PredictionAgent().predict_next_show(conn)
    top = [
        {"song_name": p.song_name, "probability": p.probability} for p in predictions[:10]
    ]
    return RetrievedFacts(Intent.PREDICT, {"top_predictions": top})


def _retrieve_cluster_summary(conn) -> RetrievedFacts:
    summaries = clustering_stats.cluster_summary(conn)
    song_names = {row["id"]: row["name"] for row in db.get_all_songs(conn)}
    enriched = [
        {
            "cluster_id": summary["cluster_id"],
            "size": summary["size"],
            "date_start": summary["date_start"],
            "date_end": summary["date_end"],
            "top_songs": [song_names[song_id] for song_id in summary["top_song_ids"]],
        }
        for summary in summaries
    ]
    return RetrievedFacts(Intent.CLUSTER, {"clusters": enriched})
