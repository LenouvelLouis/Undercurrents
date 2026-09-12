import httpx
import pytest
import respx

from undercurrents.ingestion import cli
from tests.helpers import make_raw_setlist_dict


@respx.mock
def test_fetch_command_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SETLISTFM_API_KEY", "test-key")
    respx.get("https://api.setlist.fm/rest/1.0/search/artists").mock(
        return_value=httpx.Response(
            200,
            json={
                "type": "artists", "itemsPerPage": 30, "page": 1, "total": 1,
                "artist": [{"mbid": "tame-impala-mbid-fake", "name": "Tame Impala"}],
            },
        )
    )
    respx.get("https://api.setlist.fm/rest/1.0/artist/tame-impala-mbid-fake/setlists").mock(
        return_value=httpx.Response(
            200,
            json={
                "type": "setlists", "itemsPerPage": 20, "page": 1, "total": 1,
                "setlist": [make_raw_setlist_dict()],
            },
        )
    )

    db_path = tmp_path / "test.db"
    cli.main(["fetch", "--db-path", str(db_path)])

    captured = capsys.readouterr()
    assert "Stored 1 setlists." in captured.out
    assert db_path.exists()


def test_fetch_command_requires_api_key(monkeypatch, tmp_path):
    monkeypatch.delenv("SETLISTFM_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        cli.main(["fetch", "--db-path", str(tmp_path / "test.db")])


@respx.mock
def test_fetch_command_reports_pipeline_errors_gracefully(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SETLISTFM_API_KEY", "test-key")
    respx.get("https://api.setlist.fm/rest/1.0/search/artists").mock(
        return_value=httpx.Response(
            200,
            json={"type": "artists", "itemsPerPage": 30, "page": 1, "total": 0, "artist": []},
        )
    )

    db_path = tmp_path / "test.db"
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["fetch", "--db-path", str(db_path)])

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error" in captured.err
