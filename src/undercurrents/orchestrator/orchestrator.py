from undercurrents.orchestrator import intent as intent_module
from undercurrents.orchestrator import narrative, retrieval
from undercurrents.storage import db


class Orchestrator:
    def __init__(self, ollama_client):
        self._client = ollama_client

    def ask(
        self, conn, question: str, history: list[dict] | None = None
    ) -> tuple[str, list[dict]]:
        if history is None:
            history = []

        known_song_names = _canonical_song_names(conn)
        classified = intent_module.classify(question, known_song_names)
        retrieved = retrieval.retrieve(conn, classified)
        answer = narrative.generate_response(self._client, question, retrieved, history)

        updated_history = history + [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ]
        return answer, updated_history


def _canonical_song_names(conn) -> list[str]:
    return [
        row["name"]
        for row in db.get_all_songs(conn)
        if row["excluded_from_clustering"] == 0 and row["canonical_song_id"] is None
    ]
