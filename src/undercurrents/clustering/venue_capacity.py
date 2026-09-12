import json
import logging

from undercurrents.clustering.wikidata_client import WikidataError
from undercurrents.ingestion.setlistfm_client import params_hash
from undercurrents.storage import db

logger = logging.getLogger(__name__)

API_ENDPOINT = "/api.php"
CAPACITY_PROPERTY = "P1083"
COUNTRY_PROPERTY = "P17"
HISTORICAL_DESCRIPTION_KEYWORDS = ["defunct", "former", "demolished", "existed from", "closed in"]

# Verified against Wikidata (2026-09-12) for every country actually present in the real
# dataset. A country missing here is skipped entirely rather than guessed at — see
# `resolve_venue_capacity`.
COUNTRY_QIDS: dict[str, str] = {
    "United States": "Q30",
    "Canada": "Q16",
    "Mexico": "Q96",
    "Australia": "Q408",
    "New Zealand": "Q664",
    "United Kingdom": "Q145",
    "Germany": "Q183",
    "France": "Q142",
    "Spain": "Q29",
    "Netherlands": "Q55",
    "Italy": "Q38",
    "Belgium": "Q31",
    "Portugal": "Q45",
    "Denmark": "Q35",
    "Sweden": "Q34",
    "Ireland": "Q27",
    "Switzerland": "Q39",
    "Norway": "Q20",
    "Poland": "Q36",
    "Hungary": "Q28",
    "Finland": "Q33",
    "Czechia": "Q213",
    "Austria": "Q40",
    "Slovenia": "Q215",
    "Slovakia": "Q214",
    "Luxembourg": "Q32",
    "Croatia": "Q224",
    "Brazil": "Q155",
    "Argentina": "Q414",
    "Chile": "Q298",
    "Colombia": "Q739",
    "Peru": "Q419",
    "Paraguay": "Q733",
    "Japan": "Q17",
    "Singapore": "Q334",
    "Indonesia": "Q252",
    "Malaysia": "Q833",
    "Hong Kong SAR China": "Q8646",
    "Israel": "Q801",
}


def _cached_get(conn, client, params: dict, force_refresh: bool) -> dict:
    p_hash = params_hash(params)
    if not force_refresh:
        cached_payload = db.get_cached_response(conn, API_ENDPOINT, p_hash)
        if cached_payload is not None:
            return json.loads(cached_payload)

    status, payload = client.get(API_ENDPOINT, params)
    db.cache_response(conn, API_ENDPOINT, p_hash, status, json.dumps(payload))
    return payload


def _search_candidates(conn, client, venue_name: str, force_refresh: bool) -> list[dict]:
    payload = _cached_get(
        conn,
        client,
        {
            "action": "wbsearchentities",
            "search": venue_name,
            "language": "en",
            "format": "json",
            "type": "item",
            "limit": 10,
        },
        force_refresh,
    )
    candidates = payload.get("search", [])

    exact_label_matches = [
        candidate
        for candidate in candidates
        if candidate.get("label", "").lower() == venue_name.lower()
    ]
    return [
        candidate
        for candidate in exact_label_matches
        if not any(
            keyword in (candidate.get("description") or "").lower()
            for keyword in HISTORICAL_DESCRIPTION_KEYWORDS
        )
    ]


def _get_entity_claims(conn, client, qid: str, force_refresh: bool) -> dict:
    payload = _cached_get(
        conn, client, {"action": "wbgetentities", "ids": qid, "props": "claims", "format": "json"}, force_refresh
    )
    return payload.get("entities", {}).get(qid, {}).get("claims", {})


def _max_capacity(claims: dict) -> int | None:
    amounts = []
    for statement in claims.get(CAPACITY_PROPERTY, []):
        amount = statement.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("amount")
        if amount is not None:
            amounts.append(int(float(amount)))
    return max(amounts) if amounts else None


def _country_matches(claims: dict, expected_qid: str) -> bool:
    for statement in claims.get(COUNTRY_PROPERTY, []):
        value = statement.get("mainsnak", {}).get("datavalue", {}).get("value", {})
        if value.get("id") == expected_qid:
            return True
    return False


def resolve_venue_capacity(
    conn, client, venue_name: str, venue_country: str | None, force_refresh: bool = False
) -> int | None:
    """Returns the venue's capacity from Wikidata if — and only if — exactly one exact-label,
    non-historical-looking candidate is found whose country matches `venue_country`. Returns
    `None` on any ambiguity (zero or multiple such candidates) rather than guessing, and skips
    the lookup entirely for a country not in `COUNTRY_QIDS`."""
    expected_qid = COUNTRY_QIDS.get(venue_country)
    if expected_qid is None:
        return None

    candidates = _search_candidates(conn, client, venue_name, force_refresh)

    matching_capacities = []
    for candidate in candidates:
        claims = _get_entity_claims(conn, client, candidate["id"], force_refresh)
        if _country_matches(claims, expected_qid):
            capacity = _max_capacity(claims)
            if capacity is not None:
                matching_capacities.append(capacity)

    if len(matching_capacities) != 1:
        return None
    return matching_capacities[0]


def enrich_venue_capacities(conn, client, force_refresh: bool = False) -> None:
    db.ensure_venues_capacity_column(conn)

    if force_refresh:
        conn.execute("UPDATE venues SET capacity = NULL")
        conn.commit()

    for venue in db.get_venues_needing_capacity(conn):
        try:
            capacity = resolve_venue_capacity(
                conn, client, venue["name"], venue["country"], force_refresh
            )
        except WikidataError as exc:
            logger.warning(
                "Skipping capacity lookup for venue '%s' after a Wikidata error: %s. "
                "It stays unset and will be retried on the next run.",
                venue["name"],
                exc,
            )
            continue

        if capacity is not None:
            db.set_venue_capacity(conn, venue["id"], capacity)
