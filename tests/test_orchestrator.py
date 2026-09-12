from undercurrents.orchestrator.orchestrator import Orchestrator
from undercurrents.storage import db


class FakeOllamaClient:
    def chat(self, messages):
        return "canned response"


def test_ask_returns_answer_and_starts_history(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    orchestrator = Orchestrator(FakeOllamaClient())

    answer, history = orchestrator.ask(tmp_conn, "How many shows have they played?")

    assert answer == "canned response"
    assert history == [
        {"role": "user", "content": "How many shows have they played?"},
        {"role": "assistant", "content": "canned response"},
    ]


def test_ask_accumulates_history_across_calls(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    orchestrator = Orchestrator(FakeOllamaClient())

    _, history = orchestrator.ask(tmp_conn, "First question")
    _, history = orchestrator.ask(tmp_conn, "Second question", history=history)

    assert len(history) == 4
    assert history[0]["content"] == "First question"
    assert history[2]["content"] == "Second question"
