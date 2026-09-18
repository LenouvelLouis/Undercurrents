"""Bulk venue-capacity lookup over Wikidata's SPARQL endpoint.

Why this exists alongside `venue_capacity.py`: that module asks the search API about one
venue at a time, which for 556 venues is over a thousand requests. Wikimedia's edge answers
that volume with a 403 pointing at their robot policy, and it is right to. SPARQL is the
interface they document for bulk reads, so this asks the same question in batches of a
hundred labels, turning the whole job into a handful of requests.

Disambiguation follows the same conservative rule as the per-venue module: a name is only
accepted when it resolves to a single capacity within the venue's own country. "Olympia"
alone matches four different Wikidata entities with capacities from 10 to 16000, so a
label that stays ambiguous is left unset rather than guessed at.
"""

import logging
import ssl
import time

import httpx
import truststore

from undercurrents.clustering.venue_capacity import COUNTRY_QIDS
from undercurrents.clustering.wikidata_client import USER_AGENT
from undercurrents.storage import db

logger = logging.getLogger(__name__)

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
BATCH_SIZE = 100
TIMEOUT = 90.0
# The endpoint answers a burst of batches with 429. One second between them, and a short
# backoff when it still pushes back, keeps the whole job inside what it will serve.
BATCH_INTERVAL = 1.0
MAX_RETRIES = 3


def _escape(label: str) -> str:
    return label.replace("\\", "\\\\").replace('"', '\\"')


def _build_query(pairs: list[tuple[str, str]]) -> str:
    """Matches the venue name against both the entity's English label and its aliases.

    Label-only matching misses a large share of real venues, because Wikidata often files
    them under an official or renamed form ("AccorHotels Arena") while setlist.fm records
    the name in use ("Accor Arena"); the other spelling lives in `skos:altLabel`. The UNION
    is two separate graph patterns rather than one with an OPTIONAL, because a single
    pattern matching either property would also let an alias of one entity pair with the
    label of another."""
    values = " ".join(f'("{_escape(name)}"@en wd:{qid})' for name, qid in pairs)
    return f"""SELECT ?label ?country ?capacity WHERE {{
  VALUES (?label ?country) {{ {values} }}
  {{
    ?venue rdfs:label ?label ;
           wdt:P1083 ?capacity ;
           wdt:P17 ?country .
  }} UNION {{
    ?venue skos:altLabel ?label ;
           wdt:P1083 ?capacity ;
           wdt:P17 ?country .
  }}
}}"""


def _client() -> httpx.Client:
    # Same OS-trust-store setup the other clients use, for the corporate-CA case.
    return httpx.Client(timeout=TIMEOUT, verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT))


def fetch_capacities(pairs: list[tuple[str, str]], client: httpx.Client | None = None) -> dict[tuple[str, str], int]:
    """Returns {(label, country_qid): capacity} for names that resolve unambiguously."""
    owns_client = client is None
    client = client or _client()
    headers = {"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"}
    found: dict[tuple[str, str], set[int]] = {}

    try:
        for index, start in enumerate(range(0, len(pairs), BATCH_SIZE)):
            batch = pairs[start:start + BATCH_SIZE]
            if index > 0:
                time.sleep(BATCH_INTERVAL)

            response = None
            for attempt in range(MAX_RETRIES):
                response = client.get(
                    SPARQL_ENDPOINT,
                    params={"query": _build_query(batch), "format": "json"},
                    headers=headers,
                )
                if response.status_code != 429:
                    break
                backoff = 2 ** (attempt + 1)
                logger.info("SPARQL batch at %d rate-limited, waiting %ds", start, backoff)
                time.sleep(backoff)

            if response is None or response.status_code != 200:
                logger.warning(
                    "SPARQL batch starting at %d returned %s; those venues stay unset",
                    start,
                    response.status_code if response is not None else "no response",
                )
                continue
            for binding in response.json()["results"]["bindings"]:
                label = binding["label"]["value"]
                qid = binding["country"]["value"].rsplit("/", 1)[-1]
                try:
                    capacity = int(float(binding["capacity"]["value"]))
                except (TypeError, ValueError):
                    continue
                if capacity > 0:
                    found.setdefault((label, qid), set()).add(capacity)
    finally:
        if owns_client:
            client.close()

    # A single capacity for the name within that country, or nothing.
    return {key: next(iter(values)) for key, values in found.items() if len(values) == 1}


def enrich(conn, client: httpx.Client | None = None) -> dict[str, int]:
    db.ensure_venues_capacity_column(conn)
    venues = conn.execute(
        "SELECT id, name, country FROM venues WHERE capacity IS NULL AND name IS NOT NULL"
    ).fetchall()

    pairs: list[tuple[str, str]] = []
    by_pair: dict[tuple[str, str], list[str]] = {}
    skipped_country = 0
    for venue in venues:
        qid = COUNTRY_QIDS.get(venue["country"] or "")
        if qid is None:
            skipped_country += 1
            continue
        key = (venue["name"], qid)
        if key not in by_pair:
            pairs.append(key)
        by_pair.setdefault(key, []).append(venue["id"])

    capacities = fetch_capacities(pairs, client=client)

    updated = 0
    for key, capacity in capacities.items():
        for venue_id in by_pair.get(key, []):
            conn.execute("UPDATE venues SET capacity = ? WHERE id = ?", (capacity, venue_id))
            updated += 1
    conn.commit()

    return {
        "considered": len(venues),
        "queried": len(pairs),
        "matched": len(capacities),
        "venues_updated": updated,
        "skipped_unknown_country": skipped_country,
    }
