from undercurrents.orchestrator import cli
from undercurrents.storage import db


class FakeOllamaClient:
    def chat(self, messages):
        return "This is a test answer."


def _seed_db(db_path):
    conn = db.get_connection(db_path)
    db.initialize_schema(conn)
    db.ensure_songs_clustering_columns(conn)
    conn.close()


def test_ask_command_prints_answer(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "test.db"
    _seed_db(db_path)

    monkeypatch.setattr(cli, "OllamaClient", lambda: FakeOllamaClient())
    cli.main(["ask", "How many shows?", "--db-path", str(db_path)])

    captured = capsys.readouterr()
    assert "This is a test answer." in captured.out


def test_chat_command_processes_input_until_eof(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "test.db"
    _seed_db(db_path)

    monkeypatch.setattr(cli, "OllamaClient", lambda: FakeOllamaClient())

    responses = iter(["How many shows?"])

    def fake_input(prompt=""):
        try:
            return next(responses)
        except StopIteration:
            raise EOFError()

    monkeypatch.setattr("builtins.input", fake_input)

    cli.main(["chat", "--db-path", str(db_path)])

    captured = capsys.readouterr()
    assert "This is a test answer." in captured.out
