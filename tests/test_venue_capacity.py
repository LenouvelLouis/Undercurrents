from undercurrents.clustering import venue_capacity
from undercurrents.clustering.wikidata_client import WikidataError
from undercurrents.ingestion.models import Venue
from undercurrents.storage import db

MSG_CLAIMS = {
    "P1083": [{"mainsnak": {"datavalue": {"value": {"amount": "+19812"}}}}],
    "P17": [{"mainsnak": {"datavalue": {"value": {"id": "Q30"}}}}],
}


def _search_response(candidates):
    return {"search": candidates}


def _entities_response(qid, claims):
    return {"entities": {qid: {"claims": claims}}}


class FakeWikidataClient:
    def __init__(self, search_response=None, entities_by_qid=None):
        self.search_response = search_response or {"search": []}
        self.entities_by_qid = entities_by_qid or {}
        self.calls = []

    def get(self, path, params):
        self.calls.append((path, dict(params)))
        if params.get("action") == "wbsearchentities":
            return 200, self.search_response
        if params.get("action") == "wbgetentities":
            qid = params["ids"]
            return 200, self.entities_by_qid.get(qid, {"entities": {qid: {"claims": {}}}})
        raise AssertionError(f"unexpected params: {params}")


def test_resolve_venue_capacity_returns_capacity_on_unambiguous_match(tmp_conn):
    client = FakeWikidataClient(
        search_response=_search_response(
            [{"id": "Q186125", "label": "Madison Square Garden", "description": "multi-purpose indoor arena"}]
        ),
        entities_by_qid={"Q186125": _entities_response("Q186125", MSG_CLAIMS)},
    )

    capacity = venue_capacity.resolve_venue_capacity(
        tmp_conn, client, "Madison Square Garden", "United States"
    )

    assert capacity == 19812


def test_resolve_venue_capacity_returns_none_for_unmapped_country(tmp_conn):
    client = FakeWikidataClient()

    capacity = venue_capacity.resolve_venue_capacity(tmp_conn, client, "Some Venue", "Atlantis")

    assert capacity is None
    assert client.calls == []  # never even queried — country isn't in our known QID mapping


def test_resolve_venue_capacity_returns_none_when_no_candidates_found(tmp_conn):
    client = FakeWikidataClient(search_response=_search_response([]))

    capacity = venue_capacity.resolve_venue_capacity(tmp_conn, client, "Unknown Venue", "United States")

    assert capacity is None


def test_resolve_venue_capacity_ignores_non_exact_label_matches(tmp_conn):
    client = FakeWikidataClient(
        search_response=_search_response(
            [{"id": "Q1", "label": "Madison Square Garden Arena", "description": "something"}]
        ),
    )

    capacity = venue_capacity.resolve_venue_capacity(
        tmp_conn, client, "Madison Square Garden", "United States"
    )

    assert capacity is None


def test_resolve_venue_capacity_filters_out_historical_descriptions(tmp_conn):
    client = FakeWikidataClient(
        search_response=_search_response(
            [
                {"id": "Q186125", "label": "Madison Square Garden", "description": "multi-purpose indoor arena"},
                {"id": "Q6728098", "label": "Madison Square Garden", "description": "arena that existed from 1925 to 1968"},
            ]
        ),
        entities_by_qid={"Q186125": _entities_response("Q186125", MSG_CLAIMS)},
    )

    capacity = venue_capacity.resolve_venue_capacity(
        tmp_conn, client, "Madison Square Garden", "United States"
    )

    assert capacity == 19812  # only the historical one was filtered, leaving one clean match


def test_resolve_venue_capacity_returns_none_when_multiple_valid_matches_are_ambiguous(tmp_conn):
    claims_a = {
        "P1083": [{"mainsnak": {"datavalue": {"value": {"amount": "+5000"}}}}],
        "P17": [{"mainsnak": {"datavalue": {"value": {"id": "Q30"}}}}],
    }
    claims_b = {
        "P1083": [{"mainsnak": {"datavalue": {"value": {"amount": "+7000"}}}}],
        "P17": [{"mainsnak": {"datavalue": {"value": {"id": "Q30"}}}}],
    }
    client = FakeWikidataClient(
        search_response=_search_response(
            [
                {"id": "QA", "label": "The Fillmore", "description": "a music venue"},
                {"id": "QB", "label": "The Fillmore", "description": "another music venue"},
            ]
        ),
        entities_by_qid={
            "QA": _entities_response("QA", claims_a),
            "QB": _entities_response("QB", claims_b),
        },
    )

    capacity = venue_capacity.resolve_venue_capacity(tmp_conn, client, "The Fillmore", "United States")

    assert capacity is None  # can't safely pick between two live candidates in the same country


def test_resolve_venue_capacity_returns_none_when_country_does_not_match(tmp_conn):
    claims_wrong_country = {
        "P1083": [{"mainsnak": {"datavalue": {"value": {"amount": "+5000"}}}}],
        "P17": [{"mainsnak": {"datavalue": {"value": {"id": "Q408"}}}}],  # Australia, not US
    }
    client = FakeWikidataClient(
        search_response=_search_response([{"id": "Q1", "label": "Some Venue", "description": "a venue"}]),
        entities_by_qid={"Q1": _entities_response("Q1", claims_wrong_country)},
    )

    capacity = venue_capacity.resolve_venue_capacity(tmp_conn, client, "Some Venue", "United States")

    assert capacity is None


def test_enrich_venue_capacities_sets_capacity_and_skips_already_set(tmp_conn):
    db.ensure_venues_capacity_column(tmp_conn)
    db.upsert_venue(tmp_conn, Venue(id="v1", name="Madison Square Garden", city="NYC", state=None, country="United States"))
    tmp_conn.commit()
    client = FakeWikidataClient(
        search_response=_search_response(
            [{"id": "Q186125", "label": "Madison Square Garden", "description": "multi-purpose indoor arena"}]
        ),
        entities_by_qid={"Q186125": _entities_response("Q186125", MSG_CLAIMS)},
    )

    venue_capacity.enrich_venue_capacities(tmp_conn, client)

    row = tmp_conn.execute("SELECT capacity FROM venues WHERE id = 'v1'").fetchone()
    assert row["capacity"] == 19812

    search_calls_before = len(client.calls)
    venue_capacity.enrich_venue_capacities(tmp_conn, client)  # already has capacity, must not requery
    assert len(client.calls) == search_calls_before


def test_enrich_venue_capacities_skips_venue_on_wikidata_error_and_continues(tmp_conn):
    db.ensure_venues_capacity_column(tmp_conn)
    db.upsert_venue(tmp_conn, Venue(id="v1", name="Venue A", city="C", state=None, country="United States"))
    db.upsert_venue(tmp_conn, Venue(id="v2", name="Venue B", city="C", state=None, country="United States"))
    tmp_conn.commit()

    class FlakyClient:
        def __init__(self):
            self.calls = 0

        def get(self, path, params):
            self.calls += 1
            if params.get("search") == "Venue A":
                raise WikidataError("busy")
            return 200, {"search": []}

    client = FlakyClient()

    venue_capacity.enrich_venue_capacities(tmp_conn, client)  # must not raise

    assert client.calls == 2
